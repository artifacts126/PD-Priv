import re

from dynamiczk.transform_zkay_for_consistency.code_transform import dump_to_output, get_code

from zkay.compiler.solidity.fake_solidity_generator import WS_PATTERN, ID_PATTERN
from zkay.zkay_ast.ast import CodeVisitor


def enable_upgradeable(input_file_path: str, output_file_path: str):
    code = get_code(input_file_path)

    code = re.sub(r'\s{4}constructor[\s\S]*?\n\s{4}}', r'', code)
    code = re.sub(r'\s{4}function _zk__constructor[\s\S]*?\n\s{4}}', r'', code)
    code = re.sub(r'\n\n\n+', r'\n\n', code)

    code = re.sub(f'(function{WS_PATTERN}*initialize.*?public){WS_PATTERN}*({{)', r'\1 initializer \2', code)

    code = re.sub(f'msg.sender.transfer', f'payable(msg.sender).transfer', code)


    code = re.sub(f'(contract{WS_PATTERN}*{ID_PATTERN}){WS_PATTERN}*({{)',r'\1 is UUPSUpgradeable \2', code)
    code = re.sub(r'(pragma.*?\n)', r'\1\nimport "node_modules/@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";\n', code)

    with open(output_file_path, 'w') as f:
        f.write(code)


if __name__ == '__main__':
    input_file_path = '/home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_zkay_transform/not_zkay/contract.sol'
    output_file_path = '/home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_zkay_transform/not_zkay/contract_debug.sol'
    enable_upgradeable(input_file_path, output_file_path)