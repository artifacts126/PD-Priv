from zkay.__main__ import main

enable_proxy = False
enable_migration = False
def zkay_interface():
    main()

if __name__ == '__main__':
    # compile med-stats.zkay -o compiled
    # compile /home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_someone/med-state_v8-2/med-stats_updatable_init.zkay -o /home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_someone/med-state_v8-2/compiled_updatable_init
    # compile /home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_someone/med-state_v8-2/transformed_zkay_for_consistency.sol -o /home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/test_someone/med-state_v8-2/compiled_updatable_init
    # compile /home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/eval_dynamiczk_SWC136/examples/swc-136/Odd_Even.zkay -o /home/wtq/PycharmProjects/DynamicZk/dynamiczk/test/eval_dynamiczk_SWC136/examples/swc-136/compiled
    main()