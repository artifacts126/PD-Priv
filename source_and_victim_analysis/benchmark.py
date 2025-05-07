import os
import pickle

from dynamiczk.source_and_victim_analysis.symbolic_execute.instrumentation import instrumentation_for_symbolic_analysis
from dynamiczk.source_and_victim_analysis.victim_and_source_variables import analyse_contract

apps = ['index-funds', 'inheritance', 'inner-product', 'member-card', 'oblivious-transfer', 'reviews',
            'shared-prod', 'token', 'voting', 'weighted-lottery', 'zether-confidential', 'zether-large']
            
def analyse_all_contract():

    output_file = 'victim_and_source_vars.txt'
    open(output_file, 'w').close()

    output_pkl = 'victim_and_source_vars.pkl'
    result = {}

    for app in apps:
        file_dir = os.path.realpath(os.path.dirname(__file__))
        file_zkay = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_sp2022/examples/{app}/{app}.zkay')
        contract_result = analyse_contract(file_zkay, output_file)
        result[app] = contract_result

    file_dir = os.path.realpath(os.path.dirname(__file__))
    swc_file_zkay = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_SWC136/examples/swc-136/Odd_Even.zkay')
    contract_result = analyse_contract(swc_file_zkay, output_file)
    result['Odd_Even'] = contract_result

    with open(output_pkl, 'wb') as file:
        pickle.dump(result, file)

def instrumentation():
    victim_and_source_file = 'victim_and_source_vars.pkl'

    candidates = ['final', 'non_final', 'without_final']

    for app in apps:
        file_dir = os.path.realpath(os.path.dirname(__file__))
        contract_state = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_sp2022/examples/{app}/state_dict.pkl')
        zkay_file = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_sp2022/examples/{app}/{app}.zkay')
        original_zkay_file = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_sp2022/examples/{app}/original_{app}.zkay')
        output_dir = os.path.join(file_dir, f'symbolic_execute/eval_dynamiczk_sp2022/examples/{app}')
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        for user in candidates:
            instrumentation_for_symbolic_analysis(app, user, victim_and_source_file, contract_state, original_zkay_file, zkay_file, output_dir)

    file_dir = os.path.realpath(os.path.dirname(__file__))
    contract_state = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_SWC136/examples/swc-136/state_dict.pkl')
    zkay_file = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_SWC136/examples/swc-136/Odd_Even.zkay')
    original_zkay_file = os.path.join(os.path.dirname(file_dir), f'test/eval_dynamiczk_SWC136/examples/swc-136/original_Odd_Even.zkay')
    output_dir = os.path.join(file_dir, f'symbolic_execute/eval_dynamiczk_SWC136/examples/swc-136')
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    for user in candidates:
        instrumentation_for_symbolic_analysis('Odd_Even', user, victim_and_source_file, contract_state, original_zkay_file, zkay_file, output_dir)

def run_all_scripts():


    for app in apps:
        file_dir = os.path.realpath(os.path.dirname(__file__))
        output_dir = os.path.join(file_dir, f'symbolic_execute/eval_dynamiczk_sp2022/examples/{app}')
        for filename in os.listdir(output_dir):
            if filename.endswith('.py'):
                file_path = os.path.join(output_dir, filename)
                os.system(f"python '{file_path}' ")

    file_dir = os.path.realpath(os.path.dirname(__file__))
    output_dir = os.path.join(file_dir, f'symbolic_execute/eval_dynamiczk_SWC136/examples/swc-136')
    for filename in os.listdir(output_dir):
        if filename.endswith('.py'):
            file_path = os.path.join(output_dir, filename)
            os.system(f"python '{file_path}' ")

if __name__ == '__main__':
    analyse_all_contract()
    instrumentation()
    run_all_scripts()

