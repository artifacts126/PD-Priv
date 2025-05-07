import importlib
import json
import os
import pickle
import re
import shutil
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from copy import deepcopy
from typing import Tuple, List, Type, Dict, Optional, Any, ContextManager

from dynamiczk.transform_zkay_for_consistency.code_transform import is_privacy_var, get_code, \
    whether_simple_var_in_constructor
from zkay import my_logging
from zkay.compiler.privacy import library_contracts
from zkay.compiler.privacy.circuit_generation.backends.jsnark_generator import JsnarkGenerator
from zkay.compiler.privacy.circuit_generation.circuit_generator import CircuitGenerator
from zkay.compiler.privacy.circuit_generation.circuit_helper import CircuitHelper
from zkay.compiler.privacy.manifest import Manifest
from zkay.compiler.privacy.offchain_compiler import PythonOffchainVisitor
from zkay.compiler.privacy.proving_scheme.backends.gm17 import ProvingSchemeGm17
from zkay.compiler.privacy.proving_scheme.backends.groth16 import ProvingSchemeGroth16
from zkay.compiler.privacy.proving_scheme.proving_scheme import ProvingScheme
from zkay.compiler.privacy.transformation.zkay_contract_transformer import transform_ast
from zkay.compiler.solidity.compiler import check_compilation
from zkay.config import cfg
from zkay.transaction.offchain import StateDict
from zkay.utils.helpers import read_file, lines_of_code, without_extension
from zkay.utils.progress_printer import print_step
from zkay.utils.timer import time_measure
from zkay.zkay_ast.homomorphism import Homomorphism
from zkay.zkay_ast.process_ast import get_processed_ast, get_verification_contract_names
from zkay.zkay_ast.visitor.solidity_visitor import to_solidity

from zkay.zkay_ast.ast import Mapping, BoolTypeName, UintTypeName, AddressTypeName

def get_all_params_to_upgrade(members):
	params = set()
	for member in members:
		state = member.state.get_set_params()
		params = params.union(state)
	return params

dict_values = None
def get_all_values_to_upgrade(dir):
    global dict_values
    if not dict_values:
        dict_values = deepcopy(StateDict.dict_values)
    with open(os.path.join(os.path.dirname(dir), 'state_dict.pkl'), 'wb') as file:
        pickle.dump(dict_values, file)

def consistency_transform(caller, params, zkay_file_dir):
	zkay_file_path = os.path.join(zkay_file_dir, 'contract.zkay')
	priv_vars = privacy_params_to_transform(zkay_file_path)
	for var, type in priv_vars.items():
		if type:
			for param in params:
				if param[0] == var:
					getattr(caller, 'consistency_'+var)(*param[1:])
		else:
			getattr(caller, 'consistency_'+var)()

def privacy_params_to_transform(input_file_path: str):
    code = read_file(input_file_path)

    # log specific features of compiled program
    my_logging.data('originalLoc', lines_of_code(code))
    m = re.search(r'\/\/ Description: (.*)', code)
    if m:
        my_logging.data('description', m.group(1))
    m = re.search(r'\/\/ Domain: (.*)', code)
    if m:
        my_logging.data('domain', m.group(1))
    _, filename = os.path.split(input_file_path)

    # Type checking
    zkay_ast = get_processed_ast(code)

    privacy_vars_with_type = {}
    for c in zkay_ast.contracts:
        for var in c.state_variable_declarations:
            if is_privacy_var(var.annotated_type):
                privacy_vars_with_type[var.idf.name] = isinstance(var.annotated_type.type_name, Mapping)

    return privacy_vars_with_type

def public_params_to_migration(input_file_path: str):
    code = read_file(input_file_path)

    # log specific features of compiled program
    my_logging.data('originalLoc', lines_of_code(code))
    m = re.search(r'\/\/ Description: (.*)', code)
    if m:
        my_logging.data('description', m.group(1))
    m = re.search(r'\/\/ Domain: (.*)', code)
    if m:
        my_logging.data('domain', m.group(1))
    _, filename = os.path.split(input_file_path)

    # Type checking
    zkay_ast = get_processed_ast(code)

    public_vars_with_type = {}
    public_vars = []
    for c in zkay_ast.contracts:
        for var in c.state_variable_declarations:
            if not is_privacy_var(var.annotated_type) and not var.is_final:
                public_vars_with_type[var.idf.name] = var.annotated_type.type_name
                public_vars.append(var)

    return public_vars_with_type, public_vars

def patch_constructor_args_for_migration(args, should_encrypt, zkay_file_dir):
    global dict_values
    zkay_file_path = os.path.join(zkay_file_dir, 'contract.zkay')
    public_vars_with_type, public_vars = public_params_to_migration(zkay_file_path)

    in_constructor = whether_simple_var_in_constructor(public_vars)
    if not in_constructor:
        return

    for var_original, type in public_vars_with_type.items():
        if not isinstance(type, Mapping):
            if 'original' in var_original:
                var = var_original[0:-9]
            else:
                var = var_original
            if (var,) in dict_values:
                value = dict_values[(var,)]
                args.append(True)
                should_encrypt.append(False)
                args.append(value)
                should_encrypt.append(False)
            else:
                args.append(False)
                should_encrypt.append(False)
                if isinstance(type, BoolTypeName):
                    args.append(False)
                elif isinstance(type, UintTypeName):
                    args.append(0)
                elif isinstance(type, AddressTypeName):
                    args.append('0x0')
                else:
                    exit(1)
                should_encrypt.append(False)

def contract_migration(caller, zkay_file_dir):
    global dict_values
    zkay_file_path = os.path.join(zkay_file_dir, 'contract.zkay')
    public_vars_with_type, public_vars = public_params_to_migration(zkay_file_path)
    in_constructor = whether_simple_var_in_constructor(public_vars)

    for var_original, type in public_vars_with_type.items():
        if isinstance(type, Mapping):
            actual_params = []
            for key in dict_values.keys():
                if key[0] + '_original' == var_original or key[0] == var_original:
                    if len(actual_params) == 0:
                        p_len = len(key)
                        for _ in range(p_len):
                            actual_params.append([])
                    for i in range(1, len(actual_params)):
                        actual_params[i-1].append(key[i])
                    actual_params[-1].append(dict_values[key])

            if len(actual_params) > 0:
                with caller._function_ctx(name='migration_' + var_original) as zk__is_ext:
                    assert zk__is_ext == True
                    with time_measure("transaction_full", skip=False):
                        should_encrypt = [False] * len(actual_params)
                        caller.api.transact('migration_' + var_original, actual_params, should_encrypt)

        elif not in_constructor:
            if 'original' in var_original:
                var = var_original[0:-9]
            else:
                var = var_original
            if (var,) in dict_values:
                value = dict_values[(var,)]
                with caller._function_ctx(name='migration_' + var_original) as zk__is_ext:
                    assert zk__is_ext == True
                    with time_measure("transaction_full", skip=False):
                        should_encrypt = [False]
                        caller.api.transact('migration_' + var_original, [value], should_encrypt)



def local_var_supplement(input_file_path: str, output_file_path: str):
    code = get_code(input_file_path)
    code = re.sub(r'(([^\S\r\n]*)self\.locals\.decl\("(local_var.*)",\s(.*)\)\n)',
                  r'\1\n\2\3 = \4\n',
                  code)
    with open(output_file_path, 'w') as f:
        f.write(code)

local_var_supplement('/home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_someone/inheritance/compiled/contract.py',
                     '/home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_someone/inheritance/compiled/contract.py')