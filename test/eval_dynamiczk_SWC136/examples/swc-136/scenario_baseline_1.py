#!/usr/bin/env python3
import sys

from dynamiczk.zkay_interface import zkay_tool
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade, consistency_transform, \
	contract_migration, get_all_values_to_upgrade
import pickle, os

# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	odd_even_addr, p1_addr, p2_addr = g.create_dummy_accounts(4)

	odd_even = g.deploy(user=odd_even_addr)
	p1 = g.connect(odd_even.address, user=p1_addr)
	p2 = g.connect(odd_even.address, user=p2_addr)

	odd_even.buy(wei_amount=1000)
	p1.buy(wei_amount=1000)
	p2.buy(wei_amount=1000)

	odd_even.start(4)
	p1.play(3)
	p2.play(7)

	odd_even._test_advance_time()
	odd_even.select_winner()

	odd_even.start(4)
	p1.play(3)

	odd_even._test_advance_time()

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([odd_even, p1, p2])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	zkay_tool.enable_migration = True
	get_all_values_to_upgrade(sys.argv[3])

	odd_even = g.deploy(user=odd_even_addr)
	p1 = g.connect(odd_even.address, user=p1_addr)
	p2 = g.connect(odd_even.address, user=p2_addr)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'rb') as file:
		restored_params = pickle.load(file)

	contract_migration(odd_even, sys.argv[3])
	consistency_transform(odd_even, restored_params, sys.argv[3])

	odd_even.transfer(100, p2_addr)
	p1.transfer(100, p2_addr)
	p2.transfer(100, p1_addr)

	odd_even.start(7)
	p1.play(4)
	p2.play(2)

	odd_even._test_advance_time()
	odd_even.select_winner()
