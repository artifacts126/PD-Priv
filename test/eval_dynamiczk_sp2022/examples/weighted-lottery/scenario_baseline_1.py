#!/usr/bin/env python3
import sys

from dynamiczk.zkay_interface import zkay_tool
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade, consistency_transform, \
	contract_migration, get_all_values_to_upgrade
import pickle, os

# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	lottery_addr, b1_addr, b2_addr = g.create_dummy_accounts(3)

	lottery = g.deploy(user=lottery_addr)
	b1 = g.connect(lottery.address, user=b1_addr)
	b2 = g.connect(lottery.address, user=b2_addr)

	b1.buy(wei_amount=1000)
	b2.buy(wei_amount=1000)
	lottery.start(193775903028374)
	b1.bet(193775903028370, 100)
	b2.bet(20483, 20)

	# lottery._test_advance_time()
	# lottery.add_winner(b1_addr)
	# lottery.publish()
	#
	# lottery._test_advance_time()
	# b1.win()
	# b1.sell(1020)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([lottery, b1, b2])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	zkay_tool.enable_migration = True
	get_all_values_to_upgrade(sys.argv[3])

	lottery = g.deploy(user=lottery_addr)
	b1 = g.connect(lottery.address, user=b1_addr)
	b2 = g.connect(lottery.address, user=b2_addr)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'rb') as file:
		params = pickle.load(file)

	contract_migration(lottery, sys.argv[3])
	consistency_transform(lottery, params, sys.argv[3])

	# b1.buy(wei_amount=1000)
	# b2.buy(wei_amount=1000)
	# lottery.start(193775903028374)
	# b1.bet(193775903028370, 100)
	# b2.bet(20483, 20)

	lottery._test_advance_time()
	lottery.add_winner(b1_addr)
	lottery.publish()

	lottery._test_advance_time()
	b1.win()
	b1.sell(1020)
