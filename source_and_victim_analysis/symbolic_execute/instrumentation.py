import os
import pickle
import re

from zkay import my_logging
from zkay.compiler.solidity.compiler import check_compilation
from zkay.utils.helpers import read_file, lines_of_code
from zkay.zkay_ast.process_ast import get_processed_ast
from zkay.zkay_ast.visitor.solidity_visitor import to_solidity

from zkay.zkay_ast.ast import AnnotatedTypeName, StateVariableDeclaration, Identifier, TypeName, \
    ConstructorOrFunctionDefinition, Block, Parameter, MeExpr, AllExpr, RequireStatement, IdentifierExpr, \
    ReclassifyExpr, AssignmentStatement, CodeVisitor, NumberLiteralExpr, VariableDeclarationStatement, \
    VariableDeclaration, PrimitiveCastExpr, Array, FunctionCallExpr, BuiltinFunction, ForStatement, IfStatement, \
    Comment, CipherText, BooleanLiteralExpr, AddressTypeName, IndexExpr
from zkay.zkay_ast.ast import Mapping

from eth_utils import to_checksum_address


from dynamiczk.source_and_victim_analysis.victim_and_source_variables import get_function_code, get_function_privacy_params

def clone_type_name_to_public(type_name: TypeName):
    if isinstance(type_name, Mapping):
        return Mapping(type_name.key_type, None, AnnotatedTypeName(clone_type_name_to_public(type_name.value_type.type_name)))
    else:
        return type_name.clone()

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

def dump_to_output(content: str, output_dir: str, filename: str, dryrun_solc=False) -> str:

    path = os.path.join(output_dir, filename)
    with open(path, 'w') as f:
        f.write(content)
    if dryrun_solc:
        check_compilation(path, show_errors=False)
    return content

def variable_type(zkay_ast, var_name):
    for var in zkay_ast.contracts[0].state_variable_declarations:
        if var.idf.name == var_name:
            return var.annotated_type.type_name

def collect_address_appears_in_state(State_Dict):
    addresses = set()
    for keys, value in State_Dict.items():
        for key in keys[1:]:
            if not isinstance(key, int) and not isinstance(key, bool):
                addresses.add(key)
        if not isinstance(value, int) and not isinstance(value, bool):
            addresses.add(value)
    return addresses

def collect_idf_in_rhs(expr, idfs):
    if isinstance(expr, FunctionCallExpr):
        for arg in expr.args:
            collect_idf_in_rhs(arg, idfs)
    if isinstance(expr, IdentifierExpr):
        idfs.add(expr.idf.name)
    if isinstance(expr, IndexExpr):
        idfs.add(idf_in_lhs(expr))

def idf_in_lhs(expr):
    if isinstance(expr, IdentifierExpr):
        return expr.idf.name
    # elif has_label:
    #     if isinstance(expr.key, MeExpr):
    #         return idf_in_lhs(expr.arr)
    else:
        return idf_in_lhs(expr.arr)

def generate_script(user, source_vars, output_dir):
    number_of_sources = len(source_vars)
    if number_of_sources == 0:
        return
    code = read_file('example_symbolic_analysis.py')

    code = code.replace('contract_with_instrumentation.sol', f'{user}_contract_with_instrumentation.sol')
    code = code.replace('time.txt', f'{user}_time.txt')

    if user == 'non_final':
        code = code.replace('caller=p,', 'caller=p1,')
    else:
        code = code.replace('caller=p,', 'caller=p0,')

    for i in range(1, number_of_sources+1):
        code = code.replace(f'#contract_account.priv{i}_(caller=p0)',
                     f'contract_account.priv_{source_vars[i-1]}(caller=p0)')
        code = code.replace(f'#last_return{i} = state.platform.transactions[-{i}].return_data',
                     f'last_return{i} = state.platform.transactions[-{i}].return_data')
        code = code.replace(f'#last_return{i} = Operators.CONCAT(256, *last_return{i})',
                     f'last_return{i} = Operators.CONCAT(256, *last_return{i})')
        code = code.replace(f'#state.constrain(0 == last_return{i})',
                     f'state.constrain(0 == last_return{i})')

    with open(os.path.join(output_dir, f'{user}_symbolic_analysis.py'), 'w') as file:
        file.write(code)

def instrumentation_for_symbolic_analysis(app, user, victim_and_source_file, contract_state, original_zkay_file, zkay_file, output_dir):

    code = get_code(original_zkay_file)
    original_zkay_ast = get_processed_ast(code)

    code = get_code(zkay_file)
    zkay_ast = get_processed_ast(code)

    statements = []

    #########   declarations of addresses  ################

    p0 = '0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF'
    p1 = '0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69'
    p2 = '0x1efF47bc3a10a45D4B230B5d10E37751FE6AA718'
    p3 = '0xe1AB8145F7E55DC933d51a18c793F901A3A0b276'

    dummy_accounts = [p0, p1, p2, p3]

    with open(contract_state, 'rb') as file:
        State_Dict = pickle.load(file)

    accounts = collect_address_appears_in_state(State_Dict)

    for account in accounts:
        address = to_checksum_address(account)
        account_index = dummy_accounts.index(address)
        statement = VariableDeclarationStatement(
            variable_declaration=VariableDeclaration([], AnnotatedTypeName(TypeName.address_type()),
                                                     Identifier(f'p{account_index}')),
            expr=PrimitiveCastExpr(elem_type=TypeName.address_type(), expr=NumberLiteralExpr(int(address, 16), True, True),
                                   is_implicit=True))
        statements.append(statement)

    #########   state migration  ################

    for keys, value in State_Dict.items():
        var_name = keys[0]
        var_type = variable_type(original_zkay_ast, var_name)

        if isinstance(value, int):
            rhs_expr = PrimitiveCastExpr(elem_type=TypeName.uint_type(), expr=NumberLiteralExpr(value), is_implicit=True)
        elif isinstance(value, bool):
            rhs_expr = PrimitiveCastExpr(elem_type=TypeName.bool_type(), expr=BooleanLiteralExpr(value),
                                                 is_implicit=True)
        else:
            addr = to_checksum_address(value)
            account_index = dummy_accounts.index(addr)
            rhs_expr = IdentifierExpr(Identifier(f'p{account_index}'))

        left_expr = IdentifierExpr(Identifier(var_name), AnnotatedTypeName(clone_type_name_to_public(var_type)))

        if isinstance(var_type, Mapping):
            for k in range(1, len(keys)):
                if not isinstance(keys[k], int):
                    addr = to_checksum_address(keys[k])
                    account_index = dummy_accounts.index(addr)
                    param = IdentifierExpr(Identifier(f'p{account_index}'))
                    left_expr = left_expr.index(param)
                else:
                    param = NumberLiteralExpr(keys[k])
                    left_expr = left_expr.index(param)

        statement = AssignmentStatement(left_expr, rhs_expr)
        statements.append(statement)

    #########   introduce private property  ################

    with open(victim_and_source_file, 'rb') as file:
        victim_and_source_vars = pickle.load(file)

    contract_result = victim_and_source_vars[app]

    if user == 'final':
        if 'source_vars_self_is_final' in contract_result and len(contract_result['source_vars_self_is_final']) > 0:
            own_vars = contract_result['all_own_vars_self_is_final_with_secret']
            source_vars = contract_result['source_vars_self_is_final']
        else:
            return
    elif user == 'non_final':
        if 'source_vars_self_is_not_final' in contract_result and len(contract_result['source_vars_self_is_not_final']) > 0:
            own_vars = contract_result['all_own_vars_self_is_not_final_with_secret']
            source_vars = contract_result['source_vars_self_is_not_final']
        else:
            return
    else:
        if 'source_vars_without_final' in contract_result and len(contract_result['source_vars_without_final']) > 0:
            own_vars = contract_result['all_own_vars_without_final_with_secret']
            source_vars = contract_result['source_vars_without_final']
        else:
            return

    for own_var in own_vars:
        state_variable = StateVariableDeclaration(
            AnnotatedTypeName(TypeName.uint_type()),
            ['public'],
            Identifier('priv_' + own_var),
            NumberLiteralExpr(1))

        original_zkay_ast.contracts[0].state_variable_declarations.append(state_variable)

    #########   limit input address  ################

    for func in original_zkay_ast.contracts[0].function_definitions:

        if 'public' not in func.modifiers:
            continue

        require_statements = []

        for param in func.parameters:
            if isinstance(param.annotated_type.type_name, AddressTypeName):
                require_statement = RequireStatement(FunctionCallExpr(BuiltinFunction('!='),
                                                                  [MeExpr(), IdentifierExpr(Identifier(param.idf.name))]))
                require_statements.append(require_statement)

                temp_expr = None
                for account in accounts:
                    address = to_checksum_address(account)
                    if temp_expr == None:
                        temp_expr = FunctionCallExpr(BuiltinFunction('=='),
                                         [PrimitiveCastExpr(elem_type=TypeName.address_type(),
                                                expr=NumberLiteralExpr(int(address, 16), True,True), is_implicit=True),
                                          IdentifierExpr(Identifier(param.idf.name))])
                    else:
                        temp_expr = FunctionCallExpr(BuiltinFunction('||'),
                                                                       [temp_expr,
                                                                        FunctionCallExpr(BuiltinFunction('=='),
                                                                                         [PrimitiveCastExpr(
                                                                                             elem_type=TypeName.address_type(),
                                                                                             expr=NumberLiteralExpr(
                                                                                                 int(address, 16), True,
                                                                                                 True),
                                                                                             is_implicit=True),
                                                                                          IdentifierExpr(Identifier(
                                                                                              param.idf.name))])
                                                                    ])

                if len(accounts) == 1:
                    temp_expr = FunctionCallExpr(BuiltinFunction('||'),
                                                 [temp_expr,
                                                  FunctionCallExpr(BuiltinFunction('=='),
                                                                   [PrimitiveCastExpr(
                                                                       elem_type=TypeName.address_type(),
                                                                       expr=NumberLiteralExpr(
                                                                           int(p1, 16), True,
                                                                           True),
                                                                       is_implicit=True),
                                                                       IdentifierExpr(Identifier(
                                                                           param.idf.name))])
                                                  ])

                if temp_expr:
                    require_statements.append(RequireStatement(temp_expr))

        func.body.statements = require_statements + func.body.statements

    #########   follow private property  ################

    zkay_code = read_file(zkay_file)

    for func in original_zkay_ast.contracts[0].function_definitions:
        if 'public' not in func.modifiers:
            continue
        function_code = get_function_code(zkay_code, func.name)
        private_params = get_function_privacy_params(zkay_ast, func.name, function_code)
        private_statements = []
        private_statements_index = []
        for i in range(len(func.body.statements)):
            statement = func.body.statements[i]
            if isinstance(statement, AssignmentStatement) and isinstance(statement.lhs, (IndexExpr, IdentifierExpr)):
                lhs_idf_name = idf_in_lhs(statement.lhs)

                if lhs_idf_name in own_vars:

                    label = False
                    for state_var in zkay_ast.contracts[0].state_variable_declarations:
                        if state_var.idf.name == lhs_idf_name and isinstance(state_var.annotated_type.type_name, Mapping):
                            if state_var.annotated_type.type_name.has_key_label:
                                label = True

                    owned_lhs_idf = True

                    if label:
                        owned_lhs_idf = False
                        temp = statement.lhs
                        while isinstance(temp, IndexExpr):
                            if isinstance(temp.key, MeExpr):
                                owned_lhs_idf = True
                                break
                            temp = temp.arr

                    if not owned_lhs_idf:
                        continue

                    idfs = set()
                    collect_idf_in_rhs(statement.rhs, idfs)
                    lhs = IdentifierExpr(Identifier('priv_' + lhs_idf_name))
                    rhs = None
                    if len(idfs) == 0:
                        rhs = NumberLiteralExpr(1)
                    else:
                        for idf in idfs:
                            if rhs == None:
                                if idf in private_params:
                                    rhs = NumberLiteralExpr(0)
                                elif idf in own_vars:
                                    rhs = IdentifierExpr(Identifier('priv_' + idf))
                                else:
                                    rhs = NumberLiteralExpr(1)
                            else:
                                if idf in private_params:
                                    rhs = FunctionCallExpr(BuiltinFunction('*'), [rhs, NumberLiteralExpr(0)])
                                elif idf in own_vars:
                                    rhs = FunctionCallExpr(BuiltinFunction('*'), [rhs, IdentifierExpr(Identifier('priv_' + idf))])
                                else:
                                    rhs = FunctionCallExpr(BuiltinFunction('*'), [rhs, NumberLiteralExpr(1)])

                    if rhs:
                        private_statements.append(AssignmentStatement(lhs, rhs))
                        private_statements_index.append(i)

        count = 0
        for index in private_statements_index:
            func.body.statements.insert(index + count, private_statements[count])
            count += 1

    constructor_function = ConstructorOrFunctionDefinition(None, [], [], None, Block(statements))
    constructor_function.modifiers.append('payable')
    original_zkay_ast.contracts[0].constructor_definitions = [constructor_function]

    result_code = to_solidity(original_zkay_ast)
    result_code = re.sub(f'msg.sender.transfer', f'payable(msg.sender).transfer', result_code)

    dump_to_output(result_code, output_dir, f'{user}_contract_with_instrumentation.sol')

    generate_script(user, list(source_vars), output_dir)

# if __name__ == '__main__':