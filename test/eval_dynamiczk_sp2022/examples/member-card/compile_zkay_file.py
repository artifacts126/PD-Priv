from dynamiczk.transform_zkay_for_consistency.params_transform import local_var_supplement
from dynamiczk.transform_zkay_for_consistency.upgrade_transform import enable_upgradeable
from zkay.__main__ import main
import os

if __name__ == '__main__':
    # compile med-stats.zkay -o compiled
    # compile /home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_someone/med-state_v8-2/med-stats_updatable_init.zkay -o /home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_someone/med-state_v8-2/compiled_updatable_init
    # compile /home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/eval_dynamiczk_sp2022/examples/member-card/member-card.zkay -o /home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/eval_dynamiczk_sp2022/examples/member-card/compiled
    main()
    # onchain_file = os.path.join('/home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_someone/inheritance/compiled', 'contract.sol')
    # enable_upgradeable(onchain_file, onchain_file)
    # interface_file = os.path.join('/home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_someone/inheritance/compiled',
    #                             'contract.py')
    # local_var_supplement(interface_file, interface_file)