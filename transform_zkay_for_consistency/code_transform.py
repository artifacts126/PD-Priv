"""
This module exposes functionality to compile and package zkay code
"""
import importlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from copy import deepcopy
from enum import Enum
from typing import Tuple, List, Type, Dict, Union, Optional, Any, ContextManager

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
from zkay.utils.helpers import read_file, lines_of_code, without_extension
from zkay.utils.progress_printer import print_step
from zkay.utils.timer import time_measure
from zkay.zkay_ast.homomorphism import Homomorphism
from zkay.zkay_ast.process_ast import get_processed_ast, get_verification_contract_names
from zkay.zkay_ast.visitor.solidity_visitor import to_solidity

from zkay.zkay_ast.ast import AnnotatedTypeName, StateVariableDeclaration, Identifier, TypeName, \
    ConstructorOrFunctionDefinition, Block, Parameter, MeExpr, AllExpr, RequireStatement, IdentifierExpr, \
    ReclassifyExpr, AssignmentStatement, CodeVisitor, NumberLiteralExpr, VariableDeclarationStatement, \
    VariableDeclaration, PrimitiveCastExpr, Array, FunctionCallExpr, BuiltinFunction, ForStatement, IfStatement, \
    Comment, CipherText
from zkay.zkay_ast.ast import Mapping

from zkay.zkay_ast.pointers.parent_setter import set_parents
from zkay.zkay_ast.pointers.symbol_table import link_identifiers


class TransformationType(Enum):
    INIT = 1
    CONSISTENCY = 2
    CONSISTENCY_OPTIMIZED = 3
    MIGRATION = 4

def is_privacy_var(annotated_type: AnnotatedTypeName):
    if annotated_type.had_privacy_annotation or isinstance(annotated_type.type_name, CipherText):
        return True
    elif isinstance(annotated_type.type_name, Mapping):
        return is_privacy_var(annotated_type.type_name.value_type)
    else:
        return False

def clone_type_name_to_public(type_name: TypeName):
    if isinstance(type_name, Mapping):
        return Mapping(type_name.key_type, None, AnnotatedTypeName(clone_type_name_to_public(type_name.value_type.type_name)))
    else:
        return type_name.clone()

def append_mapping_params(params: List, type_name: Mapping, count: int):
    annotated_type = AnnotatedTypeName(type_name.key_type)
    params.append(Parameter([], annotated_type, Identifier("param" + str(count))))
    if isinstance(type_name.value_type.type_name, Mapping):
        append_mapping_params(params, type_name.value_type.type_name, count + 1)
    else:
        # annotated_type = AnnotatedTypeName(clone_type_name_to_public(type_name.value_type.type_name), MeExpr())
        # params.append(Parameter([], annotated_type, Identifier("toUpdate")))
        pass


def get_params_for_update(var: StateVariableDeclaration):
    params = []
    if isinstance(var.annotated_type.type_name, Mapping):
        append_mapping_params(params, var.annotated_type.type_name, 1)
    else:
        #annotated_type = AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name), MeExpr(), var.annotated_type.homomorphism)
        #params.append(Parameter([], annotated_type, Identifier("toUpdate")))
        pass
    return params

# get the list of restored_params for a privacy variable
def get_restored_params_for_update(all_restored_params: List, var: StateVariableDeclaration):
    params = []
    if isinstance(var.annotated_type.type_name, Mapping):
        for restored_param in all_restored_params:
            if restored_param[0] == var.idf.name:
                params.append(restored_param[1:])
    else:
        pass
    return params

def combine_params_without_to_update(idf_name: str, params: List[Parameter], annotated_type: AnnotatedTypeName):
    if len(params) == 0:
        return IdentifierExpr(idf_name, annotated_type)
    else:
        assert isinstance(annotated_type.type_name, Mapping)
        expr = IdentifierExpr(idf_name, annotated_type)
        for param in params:
            expr = expr.index(param.idf)
        return expr

def combine_restored_param(idf_name: str, restored_param: List[str], annotated_type: AnnotatedTypeName):
    if len(restored_param) == 0:
        return IdentifierExpr(idf_name, annotated_type)
    else:
        assert isinstance(annotated_type.type_name, Mapping)
        expr = IdentifierExpr(idf_name, annotated_type)
        for param in restored_param:
            expr = expr.index(Identifier(param))
        return expr

def get_mapping_types(annotated_type: AnnotatedTypeName):
    assert isinstance(annotated_type.type_name, Mapping)
    types = []
    temp_type = annotated_type.type_name
    types.append(temp_type.key_type)
    while isinstance(temp_type.value_type.type_name, Mapping):
        temp_type = temp_type.value_type.type_name
        types.append(temp_type.key_type)
    v_type = temp_type.value_type
    v_type.had_privacy_annotation = False
    types.append(temp_type.value_type)
    return types


# When performing a consistency transformation, to whom should the new variable be private
def privacy_to_someone(params: List[Parameter], annotated_type: AnnotatedTypeName):
    if len(params) == 0:
        return annotated_type.privacy_annotation
    else:
        assert isinstance(annotated_type.type_name, Mapping)

        count = 0
        temp_type = annotated_type.type_name
        while not temp_type.has_key_label:
            if not isinstance(temp_type.value_type.type_name, Mapping):
                privacy_annotation = temp_type.value_type.privacy_annotation
                return privacy_annotation
            temp_type = temp_type.value_type.type_name
            count += 1

        return IdentifierExpr(params[count].idf)

def privacy_to_someone_optimized(restored_param, params: List[Parameter], annotated_type: AnnotatedTypeName):
    temp_privacy_annotation = privacy_to_someone(params, annotated_type)
    if 'param' in temp_privacy_annotation.idf.name:
        index = int(temp_privacy_annotation.idf.name[-1]) - 1
        local_var_name = restored_param[index]
        return IdentifierExpr(local_var_name)
    else:
        return temp_privacy_annotation

def restored_param_to_local_var(local_vars, restored_param):
    new_restored_param = []
    for param in restored_param:
        if not isinstance(param, int):
            from eth_utils import to_checksum_address
            param = to_checksum_address(param)
        local_var_name = list(local_vars.keys())[list(local_vars.values()).index(param)]
        new_restored_param.append(local_var_name)
    return new_restored_param

def get_code(input_file_path: str):
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

    return code

def whether_simple_var_in_constructor(public_vars):
    number_of_simple_var = 0
    for var in public_vars:
        if (not var.is_final) and (not isinstance(var.annotated_type.type_name, Mapping)):
            number_of_simple_var += 1

    if number_of_simple_var > 3:
        return False
    else:
        return True

def transform_zkay_for_migration(zkay_ast):
    # zkay_ast = transform_zkay_for_consistency(zkay_ast)
    public_vars = []

    for c in zkay_ast.contracts:
        for var in reversed(c.state_variable_declarations):
            if isinstance(var, Comment):
                break
            if not is_privacy_var(var.annotated_type):
                public_vars.append(var)

    public_vars = public_vars[::-1]

    if len(zkay_ast.contracts[0].constructor_definitions) != 0:
        constructor_function = zkay_ast.contracts[0].constructor_definitions[0]
    else:
        constructor_function = ConstructorOrFunctionDefinition(None, [], [], None, Block([]))
        zkay_ast.contracts[0].constructor_definitions.append(constructor_function)

    constructor_function.modifiers.append('payable')

    in_constructor = whether_simple_var_in_constructor(public_vars)


    for var in public_vars:
        if not var.is_final:
            if isinstance(var.annotated_type.type_name, Mapping):
                statements = []
                parameters = []
                types = get_mapping_types(var.annotated_type)
                params_number = len(types) - 1
                mapping_params = []
                for i in range(params_number):
                    parameters.append(Parameter([], AnnotatedTypeName(Array(types[i])), Identifier(f"key{i + 1}_" + var.idf.name), 'calldata'))
                    statement = RequireStatement(FunctionCallExpr(BuiltinFunction('=='),
                                                                  [IdentifierExpr(Identifier(f"key{i + 1}_" + var.idf.name)).dot('length'),
                                                                   IdentifierExpr(Identifier(f"value_" + var.idf.name)).dot('length')]))
                    statements.append(statement)
                    mapping_params.append(IdentifierExpr(Identifier(f"key{i + 1}_" + var.idf.name), AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name))).index(IdentifierExpr(Identifier('i'))))
                parameters.append(Parameter([], AnnotatedTypeName(Array(AnnotatedTypeName(clone_type_name_to_public(types[-1])))), Identifier(f"value_" + var.idf.name), 'calldata'))


                statement = VariableDeclarationStatement(
                                variable_declaration=VariableDeclaration([], AnnotatedTypeName(TypeName.uint_type()), Identifier('i')))
                statements.append(statement)

                body_identifier_expr = IdentifierExpr(Identifier(var.idf.name), AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name)))
                for p in mapping_params:
                    body_identifier_expr = body_identifier_expr.index(p)

                statement = ForStatement(
                    init=AssignmentStatement(IdentifierExpr(Identifier('i')), NumberLiteralExpr(0)),
                    condition=FunctionCallExpr(BuiltinFunction('<'),
                                          [IdentifierExpr(Identifier('i')),
                                           IdentifierExpr(Identifier(f"value_" + var.idf.name)).dot('length')]),
                    update=AssignmentStatement(IdentifierExpr(Identifier('i')),
                                               FunctionCallExpr(BuiltinFunction('+'),
                                                                [IdentifierExpr(Identifier('i')), NumberLiteralExpr(1)])),

                    body=Block([AssignmentStatement(
                        body_identifier_expr,
                        IdentifierExpr(Identifier(f"value_" + var.idf.name), AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name))).index(IdentifierExpr(Identifier('i')))
                    )])
                )
                statements.append(statement)

                new_function = ConstructorOrFunctionDefinition(Identifier("migration_" + var.idf.name),
                                                               parameters, ['external'], None, Block(statements))
                zkay_ast.contracts[0].function_definitions.append(new_function)

            elif in_constructor:
                constructor_function.add_param(AnnotatedTypeName(TypeName.bool_type()), Identifier("migrate_" + var.idf.name))
                constructor_function.add_param(AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name)), Identifier("value_" + var.idf.name))
                statement = IfStatement(
                    condition=IdentifierExpr(Identifier("migrate_" + var.idf.name)),
                    then_branch=Block([AssignmentStatement(
                        IdentifierExpr(Identifier(var.idf.name), AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name))),
                        IdentifierExpr(Identifier("value_" + var.idf.name), AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name)))
                    )]),
                    else_branch=False
                )
                constructor_function.body.statements.append(statement)
            else:
                parameters = [Parameter([], AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name)), Identifier("value_" + var.idf.name))]
                statement = AssignmentStatement(
                        IdentifierExpr(Identifier(var.idf.name), AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name))),
                        IdentifierExpr(Identifier("value_" + var.idf.name), AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name)))
                    )
                new_function = ConstructorOrFunctionDefinition(Identifier("migration_" + var.idf.name),
                                                               parameters, ['external'], None, Block([statement]))
                zkay_ast.contracts[0].function_definitions.append(new_function)

    return zkay_ast
def transform_zkay_for_init(zkay_ast):
    for c in zkay_ast.contracts:
        if len(c.constructor_definitions) != 0:
            constructor_function = c.constructor_definitions[0]

            init_states = []
            for state in c.state_variable_declarations:
                if state.expr is not None:
                    init_states.append(state)

            init_assign_statements = []
            for state in init_states:
                statement = AssignmentStatement(IdentifierExpr(state.idf.name, state.annotated_type),
                                                deepcopy(state.expr))
                init_assign_statements.append(statement)
                state.expr = None

            init_function = ConstructorOrFunctionDefinition(
                Identifier('initialize'),
                constructor_function.parameters,
                ['public'],
                None,
                Block(constructor_function.body.statements + init_assign_statements))
            c.constructor_definitions = []
            c.function_definitions.append(init_function)

    return zkay_ast
def transform_zkay_for_consistency(zkay_ast):
    public_vars = []
    privacy_vars = []
    temp_public_vars = []
    for c in zkay_ast.contracts:
        for var in c.state_variable_declarations:
            if is_privacy_var(var.annotated_type):
                privacy_vars.append(var)
                state_variable = StateVariableDeclaration(
                    AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name)),
                    [],
                    Identifier(var.idf.name + "_original"),
                    var.expr)
                public_vars.append(state_variable)
                temp_public_vars.append(state_variable)
            else:
                public_vars.append(var)

    new_functions_for_update = []
    for var1, var2 in zip(privacy_vars, temp_public_vars):
        params = get_params_for_update(var1)
        stmts = []
        # privacy_annotation2, homomorphism2 = privacy_to_someone(params, var2.annotated_type)
        # statement1 = RequireStatement(combine_params_without_to_update(var2.idf.name, params, var2.annotated_type).binop('==', ReclassifyExpr(IdentifierExpr("toUpdate"), AllExpr(), homomorphism2)))
        # stmts.append(statement1)
        privacy_annotation = privacy_to_someone(params, var1.annotated_type)
        statement2 = AssignmentStatement(combine_params_without_to_update(var1.idf.name, params, var1.annotated_type),
                                         ReclassifyExpr(combine_params_without_to_update(var2.idf.name, params,
                                                                                         var2.annotated_type),
                                                        privacy_annotation, None))
        stmts.append(statement2)
        new_f = ConstructorOrFunctionDefinition(
            Identifier("consistency_" + var1.idf.name),
            params,
            ['public'],
            None,
            Block(stmts))
        new_functions_for_update.append(new_f)

    zkay_ast.contracts[0].state_variable_declarations = public_vars + privacy_vars
    zkay_ast.contracts[0].function_definitions += new_functions_for_update

    return zkay_ast

def transform_zkay_for_consistency_optimized(zkay_ast, params_path: str):
    public_vars = []
    privacy_vars = []
    temp_public_vars = []
    for c in zkay_ast.contracts:
        for var in c.state_variable_declarations:
            if is_privacy_var(var.annotated_type):
                privacy_vars.append(var)
                state_variable = StateVariableDeclaration(
                    AnnotatedTypeName(clone_type_name_to_public(var.annotated_type.type_name)),
                    [],
                    Identifier(var.idf.name + "_original"),
                    var.expr)
                public_vars.append(state_variable)
                temp_public_vars.append(state_variable)
            else:
                public_vars.append(var)

    new_functions_for_update = []
    import pickle
    with open(params_path, 'rb') as file:
        all_restored_params = pickle.load(file)

    local_vars = {}
    stmts = []
    for var1, var2 in zip(privacy_vars, temp_public_vars):
        params = get_params_for_update(var1)
        restored_params = get_restored_params_for_update(all_restored_params, var1)

        var_number = len(local_vars) + 1
        if len(restored_params) > 0:
            for restored_param in restored_params:
                # write local vars
                for param in restored_param:
                    if not isinstance(param, int):
                        from eth_utils import to_checksum_address
                        param = to_checksum_address(param)
                        if param not in local_vars.values():
                            local_vars[f'local_var_{var_number}'] = param
                            statement1 = VariableDeclarationStatement(
                                variable_declaration=VariableDeclaration([], AnnotatedTypeName(TypeName.address_type()), Identifier(f'local_var_{var_number}')),
                                expr=PrimitiveCastExpr(elem_type=TypeName.address_type(), expr=NumberLiteralExpr(int(param, 16), True, True), is_implicit=True))
                            stmts.append(statement1)
                            var_number += 1
                    else:
                        if param not in local_vars.values():
                            local_vars[f'local_var_{var_number}'] = param
                            statement1 = VariableDeclarationStatement(
                                variable_declaration=VariableDeclaration([], AnnotatedTypeName(TypeName.uint_type()), Identifier(f'local_var_{var_number}')),
                                expr=PrimitiveCastExpr(elem_type=TypeName.uint_type(), expr=NumberLiteralExpr(param), is_implicit=True))
                            stmts.append(statement1)
                            var_number += 1
                # write ReclassifyExpr
                restored_param = restored_param_to_local_var(local_vars, restored_param)
                privacy_annotation = privacy_to_someone_optimized(restored_param, params, var1.annotated_type)
                statement2 = AssignmentStatement(
                    combine_restored_param(var1.idf.name, restored_param, var1.annotated_type),
                    ReclassifyExpr(combine_restored_param(var2.idf.name, restored_param, var2.annotated_type),
                                   privacy_annotation, None))
                stmts.append(statement2)


        else:
            if not isinstance(var1.annotated_type.type_name, Mapping):
                privacy_annotation = privacy_to_someone(params, var1.annotated_type)
                statement2 = AssignmentStatement(combine_restored_param(var1.idf.name, restored_params, var1.annotated_type),
                                                 ReclassifyExpr(combine_restored_param(var2.idf.name, restored_params, var2.annotated_type),
                                                                privacy_annotation, None))
                stmts.append(statement2)

    if len(stmts) > 0:
        new_f = ConstructorOrFunctionDefinition(
            Identifier("consistency_transformation"),
            [],
            ['public'],
            None,
            Block(stmts))
        new_functions_for_update.append(new_f)

    zkay_ast.contracts[0].state_variable_declarations = public_vars + privacy_vars
    zkay_ast.contracts[0].function_definitions += new_functions_for_update

    return zkay_ast

def dump_to_output(content: str, output_dir: str, filename: str, dryrun_solc=False) -> str:
    """
    Dump 'content' into file 'output_dir/filename' and optionally check if it compiles error-free with solc.

    :raise SolcException: if dryrun_solc is True and there are compilation errors
    :return: dumped content as string
    """

    path = os.path.join(output_dir, filename)
    with open(path, 'w') as f:
        f.write(content)
    if dryrun_solc:
        check_compilation(path, show_errors=False)
    return content


def transform_zkay(transformation_type: Enum, input_file_path: str, output_dir: str, output_filename: str = 'transformed_zkay_for_consistency.sol'):
    code = get_code(input_file_path)
    zkay_ast = get_processed_ast(code)

    if transformation_type == TransformationType.INIT:
        zkay_ast = transform_zkay_for_init(zkay_ast)

    elif transformation_type == TransformationType.CONSISTENCY:
        zkay_ast = transform_zkay_for_consistency(zkay_ast)

    elif transformation_type == TransformationType.CONSISTENCY_OPTIMIZED:
        params_path = os.path.join(os.path.dirname(input_file_path), 'params.pkl')
        zkay_ast = transform_zkay_for_consistency_optimized(zkay_ast, params_path)

    else:
        zkay_ast = transform_zkay_for_migration(zkay_ast)

    c = CodeVisitor(True)
    dump_to_output(c.visit(zkay_ast), output_dir, output_filename)

if __name__ == '__main__':
    #app = 'inner-product'
    #app = 'index-funds'
    app = 'inheritance'
    #app = 'reviews'
    input_file_path = f'/home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/eval_dynamiczk_sp2022/examples/{app}/{app}.zkay'
    output_dir = f'/home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/eval_dynamiczk_sp2022/examples/{app}'
    #params_path = f'/home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/eval_dynamiczk_sp2022/examples/{app}/params.pkl'
    transform_zkay(TransformationType.MIGRATION, input_file_path, output_dir)
