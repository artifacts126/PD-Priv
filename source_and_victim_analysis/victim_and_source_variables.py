import os
import pickle
import re
from copy import deepcopy

from dynamiczk.transform_zkay_for_consistency.code_transform import get_code, is_privacy_var
from zkay.utils.helpers import get_contract_names, read_file
from zkay.zkay_ast.ast import AssignmentStatement, IndexExpr, MeExpr, IdentifierExpr, ConstructorOrFunctionDefinition, \
    Mapping, AllExpr, AddressTypeName
from zkay.zkay_ast.process_ast import get_processed_ast
from slither import Slither

WS_PATTERN = r'[ \t\r\n\u000C]'
ID_PATTERN = r'[a-zA-Z\$_][a-zA-Z0-9\$_]*'
REVEAL_START_PATTERN = re.compile(f'(?:^|(?<=[^\\w]))reveal{WS_PATTERN}*(?=\\()')

def get_private_vars(zkay_ast):
    privacy_vars = []
    for c in zkay_ast.contracts:
        for var in c.state_variable_declarations:
            if is_privacy_var(var.annotated_type):
                privacy_vars.append(var.idf.name)
    return privacy_vars

def strip_uups(code: str):
    code = re.sub(f'(contract{WS_PATTERN}*{ID_PATTERN}){WS_PATTERN}*is{WS_PATTERN}*UUPSUpgradeable{WS_PATTERN}*({{)', r'\1 \2', code)
    code = re.sub(r'\nimport "node_modules/@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";\n',r'\n',  code)
    code = re.sub(f'(function{WS_PATTERN}*initialize.*?public){WS_PATTERN}*initializer{WS_PATTERN}*({{)', r'\1 \2', code)
    return code

def find_matching_parenthesis(code: str, open_parens_loc: int) -> int:
    """
    Get index of matching parenthesis/bracket/brace.

    :param code: code in which to search
    :param open_parens_loc: index of the opening parenthesis within code
    :return: index of the matching closing parenthesis
    """

    # Determine parenthesis characters
    open_sym = code[open_parens_loc]
    if open_sym == '(':
        close_sym = ')'
    elif open_sym == '{':
        close_sym = '}'
    elif open_sym == '[':
        close_sym = ']'
    else:
        raise ValueError('Unsupported parenthesis type')

    pattern = re.compile(f'[{open_sym}{close_sym}]')
    idx = open_parens_loc + 1
    open = 1
    while open > 0:
        cstr = code[idx:]
        idx += re.search(pattern, cstr).start()
        open += 1 if code[idx] == open_sym else -1
        idx += 1
    return idx - 1

def ids_in_reveal_other(code):
    ids = set()
    other = None

    matches = re.finditer(REVEAL_START_PATTERN, code)
    for m in matches:
        reveal_open_parens_loc = m.end()
        # Find matching closing parenthesis
        reveal_close_parens_loc = find_matching_parenthesis(code, reveal_open_parens_loc)

        # Go backwards to find comma before owner tag
        last_comma_loc = code[:reveal_close_parens_loc].rfind(',')

        all_tag_loc = code[last_comma_loc:reveal_close_parens_loc].rfind('all')
        me_tag_loc = code[last_comma_loc:reveal_close_parens_loc].rfind('me')
        if (all_tag_loc == -1) and (me_tag_loc == -1):

            reveal_body = code[reveal_open_parens_loc:last_comma_loc]
            matches_id = re.finditer(ID_PATTERN, reveal_body)

            for id in matches_id:
                if reveal_body[id.start()-1] != '[':
                    ids.add(id.group())

            reveal_target = code[last_comma_loc:reveal_close_parens_loc]
            matches_target = re.finditer(ID_PATTERN, reveal_target)

            for target in matches_target:
                if not other:
                    other = target.group()
                else:
                    assert other == target.group()

    return other, ids

def ids_in_reveal_all(code):
    ids = set()

    matches = re.finditer(REVEAL_START_PATTERN, code)
    for m in matches:
        reveal_open_parens_loc = m.end()
        # Find matching closing parenthesis
        reveal_close_parens_loc = find_matching_parenthesis(code, reveal_open_parens_loc)

        # Go backwards to find comma before owner tag
        last_comma_loc = code[:reveal_close_parens_loc].rfind(',')

        all_tag_loc = code[last_comma_loc:reveal_close_parens_loc].rfind('all')
        if all_tag_loc == -1:
            continue

        reveal_body = code[reveal_open_parens_loc:last_comma_loc]
        matches_id = re.finditer(ID_PATTERN, reveal_body)

        for id in matches_id:
            if reveal_body[id.start()-1] != '[':
                ids.add(id.group())

    return ids

def get_function_code(code, function):
    function_start_pattern = re.compile(f'function{WS_PATTERN}*{function}{WS_PATTERN}*\\(.*?\\){WS_PATTERN}*public.*?(?=[{{])')
    matches = re.finditer(function_start_pattern, code)
    for m in matches:
        function_open_parens_loc = m.end()
        function_close_parens_loc = find_matching_parenthesis(code, function_open_parens_loc)
        function_code = code[function_open_parens_loc+1:function_close_parens_loc]
        return function_code

def read_ids_in_function(code, function):
    """
        Get ids in reveal( , all) in function

        :param code: zkay code in which to search
        :param function: function to be called
    """

    function = get_function_code(code, function)
    ids = ids_in_reveal_all(function)
    return ids

def get_function_privacy_params(zkay_ast, func_name, code):
    params = []
    contract = zkay_ast.contracts[0]
    function_definition = None
    for func in contract.function_definitions:
        if func.name == func_name:
            function_definition = func
    for param in function_definition.parameters:
        if (f'reveal({param.idf.name}, all)' not in code) and (param.annotated_type.had_privacy_annotation):
            params.append(param.idf.name)
    return params

def analyse_homo_encrp(id_name, function_ast):
    for s in function_ast.body.statements:
        if isinstance(s, AssignmentStatement):
            lhs_id_name = get_lhs_idf_name(s.lhs)
            if lhs_id_name == id_name:
                rhs_code = s.rhs.code()
                if 'reveal' in rhs_code:
                    target, ids = ids_in_reveal_other(rhs_code)
                    return target, ids, rhs_code.startswith('reveal')
    return None, set(), False

def get_vars_to_process_in_function(own_vars, function_ast: ConstructorOrFunctionDefinition, state_var_declaration,
                                    private_vars_slither, target_function_slither, private_vars_names,
                                    privacy_params, private_vars_in_initial_state, self_is_caller):
    source_vars = set()
    victim_vars = set()
    num_of_situations = 0

    for id_name in own_vars:
        id_can_be_written = True
        rhs_to_process = set()

        # first check if the id_name after written is in initial state
        if self_is_caller:
            can_be_written = False
            for p_var in private_vars_slither:
                if p_var.name == id_name:
                    context_dict = target_function_slither.context

                    skip1 = False
                    for s in function_ast.body.statements:
                        if isinstance(s, AssignmentStatement):
                            if (get_lhs_idf_name(s.lhs) == id_name) and (s.op == '') and (id_name not in s.rhs.code()):
                                skip1 = True

                    skip2 = False
                    for decl in state_var_declaration:
                        if (decl.idf.name == id_name) and isinstance(decl.annotated_type.type_name, Mapping):
                            skip2 = True

                    for dep_var in context_dict['DATA_DEPENDENCY'][p_var]:
                        if skip1 and skip2 and (dep_var.name == id_name):
                            continue
                        if 'TMP' not in dep_var.name and 'REF' not in dep_var.name:
                            if dep_var.name in private_vars_names or dep_var.name in privacy_params:
                                if dep_var.name not in private_vars_in_initial_state:
                                    can_be_written = True
                                    break
                                elif dep_var.name in private_vars_names:
                                    rhs_to_process.add(dep_var.name)
                    break

            if not can_be_written:
                id_can_be_written = False
                if (id_name in rhs_to_process) and (len(rhs_to_process) > 1):
                    rhs_to_process = {id_name}

        # then check if the id_name after written can be manipulated by homomorphic encryption
        else:
            rhs_to_process = set()
            homo_target, reveal_vars_in_homo_right, rhs_start_with_reveal = analyse_homo_encrp(id_name, function_ast)
            if homo_target:
                process_homo = False
                for p_var in private_vars_slither:
                    if p_var.name == id_name:
                        context_dict = target_function_slither.context

                        skip1 = False
                        for s in function_ast.body.statements:
                            if isinstance(s, AssignmentStatement):
                                if (get_lhs_idf_name(s.lhs) == id_name) and (s.op == '') and (id_name not in s.rhs.code()):
                                    skip1 = True

                        skip2 = False
                        for decl in state_var_declaration:
                            if (decl.idf.name == id_name) and isinstance(decl.annotated_type.type_name, Mapping):
                                skip2 = True

                        for dep_var in context_dict['DATA_DEPENDENCY'][p_var]:
                            if skip1 and skip2 and (dep_var.name == id_name):
                                continue
                            # if dep_var.name not in all_own_vars:
                            #     continue
                            if ('TMP' not in dep_var.name) and ('REF' not in dep_var.name) and (dep_var.name not in reveal_vars_in_homo_right) and (not rhs_start_with_reveal):
                                if dep_var.name in private_vars_names or dep_var.name in privacy_params:
                                    if dep_var.name in private_vars_in_initial_state:
                                        process_homo = True
                                        rhs_to_process.add(dep_var.name)
                        break

                if process_homo:
                    id_can_be_written = False
                    if len(rhs_to_process) > 1:
                        if id_name in rhs_to_process:
                            rhs_to_process = {id_name}

        if not id_can_be_written:
            source_vars = source_vars.union(rhs_to_process)
            if len(rhs_to_process) > 0:
                victim_vars.add(id_name)
            num_of_situations += 1

    return source_vars, victim_vars, num_of_situations

def get_lhs_idf_name(lhs):
    if isinstance(lhs, IdentifierExpr):
        id_name = lhs.idf.name
    else:
        temp = lhs
        while isinstance(temp, IndexExpr):
            temp = temp.arr
        assert isinstance(temp, IdentifierExpr)
        id_name = temp.idf.name

    return id_name

def get_own_vars(function_ast: ConstructorOrFunctionDefinition, state_var_declaration, private_vars_names, self_is_caller, user_final_addr = None):
    own_vars = set()

    if user_final_addr:
        for s in function_ast.body.statements:
            if isinstance(s, AssignmentStatement):
                id_name = get_lhs_idf_name(s.lhs)
                if id_name in private_vars_names:
                    if isinstance(s.lhs, IdentifierExpr):
                        if not isinstance(s.lhs.annotated_type.privacy_annotation, AllExpr):
                            privacy_ann = s.lhs.annotated_type.privacy_annotation.idf.name
                            if (id_name in private_vars_names) and (privacy_ann == user_final_addr):
                                own_vars.add(id_name)

                    if isinstance(s.lhs, IndexExpr):
                        temp = s.lhs
                        if temp.annotated_type.had_privacy_annotation:
                            target = temp.annotated_type.privacy_annotation.idf.name
                            if target == user_final_addr:
                                own_vars.add(id_name)

    # judge ones own var with mapping type that has label
    for s in function_ast.body.statements:
        if isinstance(s, AssignmentStatement):
            # get identifier name id_name
            id_name = get_lhs_idf_name(s.lhs)
            if id_name in private_vars_names:

                if isinstance(s.lhs, IndexExpr):

                    # get the label name of the private vars (id_name)
                    specific_label_number = -1
                    mapping_depth = -1
                    if id_name in private_vars_names:
                        for decl in state_var_declaration:
                            if (decl.idf.name == id_name) and isinstance(decl.annotated_type.type_name, Mapping):
                                temp_type = decl.annotated_type.type_name

                                mapping_depth = 0
                                if temp_type.has_key_label:
                                    specific_label_number = mapping_depth
                                while isinstance(temp_type.value_type.type_name, Mapping):
                                    temp_type = temp_type.value_type.type_name
                                    mapping_depth += 1
                                    if temp_type.has_key_label:
                                        specific_label_number = mapping_depth
                                break

                    # judge ones own var according to whether self is caller
                    temp = s.lhs
                    current_label_number = 0
                    while isinstance(temp, IndexExpr):
                        if (mapping_depth - current_label_number) == specific_label_number:
                            if (not isinstance(temp.key, MeExpr)) and (not self_is_caller):
                                own_vars.add(id_name)
                            elif (isinstance(temp.key, MeExpr)) and self_is_caller:
                                own_vars.add(id_name)
                            break
                        temp = temp.arr
                        current_label_number += 1

    return own_vars



def check_caller_legitimacy(function_code, contract_final_addr, user_addr=None):
    """
        check the legitimacy of caller

        :param function_code: zkay function code in which to search
        :param contract_final_addr: the final addr of contract
        :param user_addr: the addr of user, None presents anyone
    """

    # first check require statement
    require_pattern = re.compile(f'require\\({WS_PATTERN}*me{WS_PATTERN}*=={WS_PATTERN}*({ID_PATTERN}){WS_PATTERN}*(\\));')
    matches = re.finditer(require_pattern, function_code)
    for m in matches:
        addr = m.group(1)
        if (addr != contract_final_addr) and (contract_final_addr != user_addr):
            return True
        else:
            return user_addr == addr

    require_pattern = re.compile(
        f'require\\({WS_PATTERN}*({ID_PATTERN}){WS_PATTERN}*=={WS_PATTERN}*me{WS_PATTERN}*(\\));')
    matches = re.finditer(require_pattern, function_code)
    for m in matches:
        addr = m.group(1)
        if (addr != contract_final_addr) and (contract_final_addr != user_addr):
            return True
        else:
            return user_addr == addr

    # then check homo encryption
    reveal_pattern = re.compile(f'reveal\\(.*?,{WS_PATTERN}*({ID_PATTERN}){WS_PATTERN}*(\\));')
    matches = re.finditer(reveal_pattern, function_code)
    for m in matches:
        addr = m.group(1)
        if addr != 'all':
            return not (user_addr == addr)

    return True

def get_user_vars_with_secret_data(zkay_ast, zkay_code, private_vars_names, contract_final_addr, user_final_addr=None):
    """
        get all user's vars with secret data of user

        :param function_code: zkay function code in which to search
        :param contract_final_addr: the final addr of contract
        :param user_final_addr: the final addr of user, None presents anyone
    """

    own_vars_with_secret = set()

    temp = set()

    for func in zkay_ast.contracts[0].function_definitions:
        function_name = func.idf.name
        if 'consistency' in function_name:
            continue
        function_code = get_function_code(zkay_code, function_name)
        if not function_code:
            continue

        if contract_final_addr == None or check_caller_legitimacy(function_code, contract_final_addr, user_final_addr):
            privacy_params = get_function_privacy_params(zkay_ast, function_name, function_code)
            own_vars_in_func = get_own_vars(func, zkay_ast.contracts[0].state_variable_declarations,
                                    private_vars_names, True, user_final_addr)
            for s in func.body.statements:
                if isinstance(s, AssignmentStatement):
                    # get identifier name id_name
                    id_name = get_lhs_idf_name(s.lhs)
                    if id_name in own_vars_in_func:
                        from zkay.zkay_ast.visitor.solidity_visitor import to_solidity
                        assignment_statement = to_solidity(s)
                        for p in privacy_params:
                            if p in assignment_statement:
                                temp.add(id_name)
                                break
            own_vars_in_func = get_own_vars(func, zkay_ast.contracts[0].state_variable_declarations,
                                            private_vars_names, False, user_final_addr)

    for func in zkay_ast.contracts[0].function_definitions:
        function_name = func.idf.name
        if 'consistency' in function_name:
            continue
        function_code = get_function_code(zkay_code, function_name)
        if not function_code:
            continue
        if contract_final_addr == None or check_caller_legitimacy(function_code, contract_final_addr, None):
            own_vars_in_func = get_own_vars(func, zkay_ast.contracts[0].state_variable_declarations, private_vars_names, False, user_final_addr)
            for s in func.body.statements:
                if isinstance(s, AssignmentStatement):
                    # get identifier name id_name
                    id_name = get_lhs_idf_name(s.lhs)
                    if id_name in own_vars_in_func:
                        from zkay.zkay_ast.visitor.solidity_visitor import to_solidity
                        assignment_statement = to_solidity(s)
                        #for decl in zkay_ast.contracts[0].state_variable_declarations:
                        for var in temp:
                            if var in assignment_statement:
                                own_vars_with_secret.add(id_name)
                                break

    own_vars_with_secret |= temp
    return own_vars_with_secret

def get_victim_and_source_vars_in_contract(zkay_ast, zkay_code, functions_slither, private_vars_names,
                                    private_vars_in_initial_state, private_vars_slither, contract_name, output_file):

    # judge whether the contract has final address
    contract_has_final = False
    final_addr = None

    for state in zkay_ast.contracts[0].state_variable_declarations:
        if state.is_final and isinstance(state.annotated_type.type_name, AddressTypeName):
            contract_has_final = True
            final_addr = state.idf.name

    all_own_vars_self_is_final = set()
    all_own_vars_self_is_not_final = set()
    all_own_vars_without_final = set()

    all_own_vars_self_is_final_with_secret = set()
    all_own_vars_self_is_not_final_with_secret = set()
    all_own_vars_without_final_with_secret = set()

    if contract_has_final:
        all_own_vars_self_is_final_with_secret |= get_user_vars_with_secret_data(zkay_ast, zkay_code,
                                                                                private_vars_names, final_addr,
                                                                                final_addr)

        all_own_vars_self_is_not_final_with_secret |= get_user_vars_with_secret_data(zkay_ast, zkay_code,
                                                                                    private_vars_names, final_addr,
                                                                                    None)
    else:
        all_own_vars_without_final_with_secret |= get_user_vars_with_secret_data(zkay_ast, zkay_code,
                                                                            private_vars_names, None,
                                                                            None)

    victim_and_source_vars_in_each_func = {}

    for func in zkay_ast.contracts[0].function_definitions:
        function_name = func.idf.name
        if 'consistency' in function_name:
            continue
        function_code = get_function_code(zkay_code, function_name)
        if not function_code:
            continue

        privacy_params = get_function_privacy_params(zkay_ast, function_name, function_code)

        target_function_slither = None
        for f in functions_slither:
            if f.name == function_name:
                target_function_slither = f

        source_vars_self_is_final = set()
        victim_vars_self_is_final = set()

        source_vars_self_is_not_final = set()
        victim_vars_self_is_not_final = set()

        source_vars_without_final = set()
        victim_vars_without_final = set()

        # contract has final, the user may have final address or not
        if contract_has_final:
            # 1. first assume self is final address
            #  1.1 first discuss the case in which user is caller
            if check_caller_legitimacy(function_code, final_addr, final_addr):
                # risk of reading, (self is caller)
                ids_to_be_read = ids_in_reveal_all(function_code)

                privacy_ids = set()
                for id in ids_to_be_read:
                    if (id in private_vars_names) or (id in privacy_params):
                        privacy_ids.add(id)
                if privacy_ids.issubset(private_vars_in_initial_state):
                    privacy_ids &= all_own_vars_self_is_final_with_secret
                    source_vars_self_is_final = source_vars_self_is_final.union(privacy_ids)
                    victim_vars_self_is_final |= privacy_ids

                # risk of writing, self is caller
                own_vars = get_own_vars(func, zkay_ast.contracts[0].state_variable_declarations,
                                        private_vars_names, True, final_addr)

                all_own_vars_self_is_final = all_own_vars_self_is_final.union(own_vars)

                own_vars &= all_own_vars_self_is_final_with_secret

                source_vars, victim_vars, num_of_situations = get_vars_to_process_in_function(own_vars, func, zkay_ast.contracts[0].state_variable_declarations, private_vars_slither,
                                                                              target_function_slither,
                                                                              private_vars_names, privacy_params,
                                                                              private_vars_in_initial_state, True)
                source_vars_self_is_final = source_vars_self_is_final.union(source_vars)
                victim_vars_self_is_final |= victim_vars

            #  1.2 then discuss the case in which user is not caller
            if check_caller_legitimacy(function_code, final_addr, None):
                # risk of writing, self is not caller
                own_vars = get_own_vars(func, zkay_ast.contracts[0].state_variable_declarations,
                                        private_vars_names, False, final_addr)

                all_own_vars_self_is_final = all_own_vars_self_is_final.union(own_vars)

                own_vars &= all_own_vars_self_is_final_with_secret

                source_vars, victim_vars, num_of_situations = get_vars_to_process_in_function(own_vars, func, zkay_ast.contracts[0].state_variable_declarations, private_vars_slither,
                                                                              target_function_slither,
                                                                              private_vars_names, privacy_params,
                                                                              private_vars_in_initial_state, False)
                source_vars_self_is_final = source_vars_self_is_final.union(source_vars)
                victim_vars_self_is_final |= victim_vars

            # 2. then assume self is not final address
            #  2.1 first discuss the case in which user is caller
            if check_caller_legitimacy(function_code, final_addr, None):
                # risk of reading, (self is caller)
                ids_to_be_read = ids_in_reveal_all(function_code)
                privacy_ids = set()
                for id in ids_to_be_read:
                    if (id in private_vars_names) or (id in privacy_params):
                        privacy_ids.add(id)
                if privacy_ids.issubset(private_vars_in_initial_state):
                    privacy_ids &= all_own_vars_self_is_not_final_with_secret
                    source_vars_self_is_not_final = source_vars_self_is_not_final.union(privacy_ids)
                    victim_vars_self_is_not_final |= privacy_ids

                # risk of writing, user is caller
                own_vars = get_own_vars(func, zkay_ast.contracts[0].state_variable_declarations,
                                        private_vars_names, True)

                all_own_vars_self_is_not_final = all_own_vars_self_is_not_final.union(own_vars)

                own_vars &= all_own_vars_self_is_not_final_with_secret

                source_vars, victim_vars, num_of_situations = get_vars_to_process_in_function(own_vars, func, zkay_ast.contracts[0].state_variable_declarations, private_vars_slither,
                                                                              target_function_slither,
                                                                              private_vars_names, privacy_params,
                                                                              private_vars_in_initial_state, True)
                source_vars_self_is_not_final = source_vars_self_is_not_final.union(source_vars)
                victim_vars_self_is_not_final |= victim_vars

            #  2.2 then discuss the case in which self is not caller, it should be legitimacy when final_addr/anyone is caller

            # risk of writing, self is not caller, final_addr/anyone is caller
            own_vars = get_own_vars(func, zkay_ast.contracts[0].state_variable_declarations,
                                    private_vars_names, False)

            all_own_vars_self_is_not_final = all_own_vars_self_is_not_final.union(own_vars)

            own_vars &= all_own_vars_self_is_not_final_with_secret

            source_vars, victim_vars, num_of_situations = get_vars_to_process_in_function(own_vars, func, zkay_ast.contracts[0].state_variable_declarations, private_vars_slither,
                                                                          target_function_slither,
                                                                          private_vars_names, privacy_params,
                                                                          private_vars_in_initial_state, False)
            source_vars_self_is_not_final = source_vars_self_is_not_final.union(source_vars)
            victim_vars_self_is_not_final |= victim_vars

            # print('function_name', function_name)
            # print('vars_to_process_self_is_final', vars_to_process_self_is_final)
            # print('vars_to_process_self_is_not_final', vars_to_process_self_is_not_final)

            victim_and_source_vars_in_each_func[function_name] = {}
            victim_and_source_vars_in_each_func[function_name]['source_vars_self_is_final'] = source_vars_self_is_final
            victim_and_source_vars_in_each_func[function_name]['victim_vars_self_is_final'] = victim_vars_self_is_final
            #victim_and_source_vars_in_each_func[function_name]['num_of_situations_self_is_final'] = num_of_situations_self_is_final
            victim_and_source_vars_in_each_func[function_name]['source_vars_self_is_not_final'] = source_vars_self_is_not_final
            victim_and_source_vars_in_each_func[function_name]['victim_vars_self_is_not_final'] = victim_vars_self_is_not_final
            #victim_and_source_vars_in_each_func[function_name]['num_of_situations_self_is_not_final'] = num_of_situations_self_is_not_final

        else:
            # there is no final address
            #  first discuss the case in which self is caller
            # risk of reading, (self is caller)
            ids_to_be_read = ids_in_reveal_all(function_code)
            privacy_ids = set()
            for id in ids_to_be_read:
                if (id in private_vars_names) or (id in privacy_params):
                    privacy_ids.add(id)
            if privacy_ids.issubset(private_vars_in_initial_state):
                privacy_ids &= all_own_vars_without_final_with_secret
                source_vars_without_final = source_vars_without_final.union(privacy_ids)
                victim_vars_without_final |= privacy_ids

            # risk of writing, self is caller
            own_vars = get_own_vars(func, zkay_ast.contracts[0].state_variable_declarations,
                                    private_vars_names, True)

            all_own_vars_without_final = all_own_vars_without_final.union(own_vars)

            own_vars &= all_own_vars_without_final_with_secret

            source_vars, victim_vars, num_of_situations = get_vars_to_process_in_function(own_vars, func, zkay_ast.contracts[0].state_variable_declarations, private_vars_slither,
                                                                          target_function_slither,
                                                                          private_vars_names, privacy_params,
                                                                          private_vars_in_initial_state, True)
            source_vars_without_final = source_vars_without_final.union(source_vars)
            victim_vars_without_final |= victim_vars

            # then discuss the case in which self is not caller
            # risk of writing, self is not caller
            own_vars = get_own_vars(func, zkay_ast.contracts[0].state_variable_declarations,
                                    private_vars_names, False)

            all_own_vars_without_final = all_own_vars_without_final.union(own_vars)

            own_vars &= all_own_vars_without_final_with_secret

            source_vars, victim_vars, num_of_situations = get_vars_to_process_in_function(own_vars, func, zkay_ast.contracts[0].state_variable_declarations, private_vars_slither,
                                                                          target_function_slither,
                                                                          private_vars_names, privacy_params,
                                                                          private_vars_in_initial_state, False)
            source_vars_without_final = source_vars_without_final.union(source_vars)
            victim_vars_without_final |= victim_vars

            # print('function_name', function_name)
            # print('vars_to_process_without_final', vars_to_process_without_final)

            victim_and_source_vars_in_each_func[function_name] = {}
            victim_and_source_vars_in_each_func[function_name]['source_vars_without_final'] = source_vars_without_final
            victim_and_source_vars_in_each_func[function_name]['victim_vars_without_final'] = victim_vars_without_final
            #victim_and_source_vars_in_each_func[function_name]['num_of_situations_without_final'] = num_of_situations_without_final

    #print(victim_and_source_vars_in_each_func)
    #print('###########   result:   ##########')

    victim_and_source_vars_in_contract = {}
    # victim_and_source_vars_in_contract['source_vars_self_is_final'] = set()
    # victim_and_source_vars_in_contract['source_vars_self_is_not_final'] = set()
    # victim_and_source_vars_in_contract['source_vars_without_final'] = set()
    # victim_and_source_vars_in_contract['victim_vars_self_is_final'] = set()
    # victim_and_source_vars_in_contract['victim_vars_self_is_not_final'] = set()
    # victim_and_source_vars_in_contract['victim_vars_without_final'] = set()

    for f in victim_and_source_vars_in_each_func:
        #print('function_name', f)
        for process_case in victim_and_source_vars_in_each_func[f]:
            if process_case not in victim_and_source_vars_in_contract:
                victim_and_source_vars_in_contract[process_case] = set()
            if process_case == 'source_vars_self_is_final':
                victim_and_source_vars_in_each_func[f][process_case] = all_own_vars_self_is_final & victim_and_source_vars_in_each_func[f][process_case]
                victim_and_source_vars_in_contract[process_case] |= victim_and_source_vars_in_each_func[f][process_case]
                #print('vars_to_process_self_is_final', victim_and_source_vars_in_each_func[f][process_case])
            if process_case == 'source_vars_self_is_not_final':
                victim_and_source_vars_in_each_func[f][process_case] = all_own_vars_self_is_not_final & victim_and_source_vars_in_each_func[f][process_case]
                victim_and_source_vars_in_contract[process_case] |= victim_and_source_vars_in_each_func[f][process_case]
                #print('vars_to_process_self_is_not_final', victim_and_source_vars_in_each_func[f][process_case])
            if process_case == 'source_vars_without_final':
                victim_and_source_vars_in_each_func[f][process_case] = all_own_vars_without_final & victim_and_source_vars_in_each_func[f][process_case]
                victim_and_source_vars_in_contract[process_case] |= victim_and_source_vars_in_each_func[f][process_case]
                #print('vars_to_process_without_final', victim_and_source_vars_in_each_func[f][process_case])
            if process_case == 'victim_vars_self_is_final':
                victim_and_source_vars_in_each_func[f][process_case] = all_own_vars_self_is_final & victim_and_source_vars_in_each_func[f][process_case]
                victim_and_source_vars_in_contract[process_case] |= victim_and_source_vars_in_each_func[f][process_case]
                #print('vars_to_process_self_is_final', victim_and_source_vars_in_each_func[f][process_case])
            if process_case == 'victim_vars_self_is_not_final':
                victim_and_source_vars_in_each_func[f][process_case] = all_own_vars_self_is_not_final & victim_and_source_vars_in_each_func[f][process_case]
                victim_and_source_vars_in_contract[process_case] |= victim_and_source_vars_in_each_func[f][process_case]
                #print('vars_to_process_self_is_not_final', victim_and_source_vars_in_each_func[f][process_case])
            if process_case == 'victim_vars_without_final':
                victim_and_source_vars_in_each_func[f][process_case] = all_own_vars_without_final & victim_and_source_vars_in_each_func[f][process_case]
                victim_and_source_vars_in_contract[process_case] |= victim_and_source_vars_in_each_func[f][process_case]

    #print('###########   summarize:   ##########')
    with open(output_file, 'a') as f:
        f.write('\n\n###########    contract name :  ' + contract_name + '     ############')
        if contract_has_final:
            f.write('\nWhen one has a final address,')
            f.write('\n\tthe own variables include : ' + str(all_own_vars_self_is_final))
            f.write('\n\tthe own variables with secret include : ' + str(all_own_vars_self_is_final_with_secret))
            victim_and_source_vars_in_contract['all_own_vars_self_is_final_with_secret'] = all_own_vars_self_is_final_with_secret
            f.write('\n\tthe victim variables include : ' + str(victim_and_source_vars_in_contract['victim_vars_self_is_final']))
            f.write('\n\tthe source variables include : ' + str(victim_and_source_vars_in_contract['source_vars_self_is_final']))
            f.write('\nWhen one has not a final address,')
            f.write('\n\tthe own variables include : ' + str(all_own_vars_self_is_not_final))
            f.write('\n\tthe own variables with secret include : ' + str(all_own_vars_self_is_not_final_with_secret))
            victim_and_source_vars_in_contract['all_own_vars_self_is_not_final_with_secret'] = all_own_vars_self_is_not_final_with_secret
            f.write('\n\tthe victim variables include : ' + str(victim_and_source_vars_in_contract['victim_vars_self_is_not_final']))
            f.write('\n\tthe source variables include : ' + str(victim_and_source_vars_in_contract['source_vars_self_is_not_final']))
        else:
            f.write('\nWhen there is no final address,')
            f.write('\n\tthe own variables include : ' + str(all_own_vars_without_final))
            f.write('\n\tthe own variables with secret include : ' + str(all_own_vars_without_final_with_secret))
            victim_and_source_vars_in_contract['all_own_vars_without_final_with_secret'] = all_own_vars_without_final_with_secret
            f.write('\n\tthe victim variables include : ' + str(victim_and_source_vars_in_contract['victim_vars_without_final']))
            f.write('\n\tthe source variables include : ' + str(victim_and_source_vars_in_contract['source_vars_without_final']))

    return victim_and_source_vars_in_contract

def analyse_contract(file_zkay, output_file):

    zkay_code = read_file(file_zkay)
    zkay_ast = get_processed_ast(zkay_code)

    private_vars_names = get_private_vars(zkay_ast)
    private_vars_in_initial_state = set(deepcopy(private_vars_names))

    # prepare slither data dependency
    original_sol_file = os.path.join(os.path.dirname(file_zkay), 'compiled_original/contract.sol')
    original_code = read_file(original_sol_file)
    temp_original_file = 'temp_contract.sol'
    with open(temp_original_file, 'w') as f:
        original_code = strip_uups(original_code)
        f.write(original_code)

    slither = Slither(temp_original_file)
    contract_name = get_contract_names(temp_original_file)[0]
    os.remove(temp_original_file)

    contracts = slither.get_contract_from_name(contract_name)
    assert len(contracts) == 1
    contract = contracts[0]
    functions_slither = contract.functions

    private_vars_slither = set()
    for private_var in private_vars_names:
        p_var = contract.get_state_variable_from_name(private_var)
        private_vars_slither.add(p_var)

    contract_result = get_victim_and_source_vars_in_contract(zkay_ast, zkay_code, functions_slither, private_vars_names,
                                           private_vars_in_initial_state, private_vars_slither, contract_name, output_file)

    return contract_result




if __name__ == '__main__':

    output_file = 'victim_and_source_vars.txt'
    open(output_file, 'w').close()

    output_pkl = 'victim_and_source_vars.pkl'
    result = {}

    apps = ['index-funds', 'inheritance', 'inner-product', 'member-card', 'oblivious-transfer', 'reviews',
            'shared-prod', 'token', 'voting', 'weighted-lottery', 'zether-confidential', 'zether-large']

    for app in apps:
    #app = 'inheritance'
        file_dir = os.path.realpath(os.path.dirname(__file__))
        # file_original = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_sp2022/examples/{app}/original_{app}.zkay')
        file_zkay = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_sp2022/examples/{app}/{app}.zkay')
        contract_result = analyse_contract(file_zkay, output_file)
        result[app] = contract_result

    file_dir = os.path.realpath(os.path.dirname(__file__))
    swc_file_zkay = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_SWC136/examples/swc-136/Odd_Even.zkay')
    contract_result = analyse_contract(swc_file_zkay, output_file)
    result['Odd_Even'] = contract_result

    with open(output_pkl, 'wb') as file:
        pickle.dump(result, file)

    # apps = ['index-funds', 'inheritance', 'inner-product', 'member-card', 'oblivious-transfer', 'reviews',
    #         'shared-prod', 'token', 'voting', 'weighted-lottery', 'zether-confidential', 'zether-large']
    #
    # for app in apps:
    #
    #     file_dir = os.path.realpath(os.path.dirname(__file__))
    #     file_zkay = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_sp2022/examples/{app}/{app}.zkay')
    #     recommended_transaction_order(file_zkay)

