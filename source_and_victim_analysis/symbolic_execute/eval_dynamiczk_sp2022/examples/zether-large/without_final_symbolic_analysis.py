import os

from manticore.ethereum import ManticoreEVM
from manticore.core.smtlib import Operators
from manticore.core.smtlib.solver import Z3Solver

import datetime

def symbolic_execute_with_tx_no(contract_path, tx_no, tx_send_ether):

    m = ManticoreEVM()  # initiate the blockchain
    with open(contract_path) as f:
        source_code = f.read()

    # Generate the accounts
    p0 = m.create_account(balance=10 ** 10, address=0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF)
    p1 = m.create_account(balance=10 ** 10, address=0x6813Eb9362372EEF6200f3b1dbC3f819671cBA69)

    contract_account = m.solidity_create_contract(
        source_code, owner=p0, balance=1000000
    )

    solver = Z3Solver.instance()

    CHECK = False

    for _ in range(tx_no):

        symbolic_data = m.make_symbolic_buffer(320)
        if tx_send_ether:
            value = m.make_symbolic_value()
        else:
            value = 0

        m.transaction(
            caller=p0,
            address=contract_account,
            data=symbolic_data,
            value=value
        )

    contract_account.priv_balance(caller=p0)
    #contract_account.priv2_(caller=p0)

    for state in m.ready_states:
        last_return1 = state.platform.transactions[-1].return_data
        last_return1 = Operators.CONCAT(256, *last_return1)
        state.constrain(0 == last_return1)

        #last_return2 = state.platform.transactions[-2].return_data
        #last_return2 = Operators.CONCAT(256, *last_return2)
        #state.constrain(0 == last_return2)

        if solver.check(state.constraints):
            print("Solution found! see {}".format(m.workspace))
            m.generate_testcase(state, "PD-Priv")
            CHECK = True

    return CHECK

def symbolic_execute(contract_path, tx_send_ether=False, tx_no_limit=3):

    tx_no = 0
    while tx_no <= tx_no_limit:
        tx_no += 1
        print("The number of total transactions: ", tx_no)
        if symbolic_execute_with_tx_no(contract_path, tx_no, tx_send_ether):
            break

if __name__ == '__main__':
    file_dir = os.path.realpath(os.path.dirname(__file__))
    contract_path = os.path.join(file_dir, "without_final_contract_with_instrumentation.sol")
    starttime = datetime.datetime.now()
    symbolic_execute(contract_path)
    endtime = datetime.datetime.now()
    with open('without_final_time.txt', 'w') as file:
        file.write(str((endtime - starttime).seconds))