#!/usr/bin/env python3
import sys
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade
import pickle, os
from dynamiczk.zkay_interface import zkay_tool
zkay_tool.enable_proxy = True
# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	lottery_addr, b1_addr, b2_addr = g.create_dummy_accounts(3)

	lottery = g.deploy(user=lottery_addr)
	b1 = g.connect(lottery.address, user=b1_addr)
	b2 = g.connect(lottery.address, user=b2_addr)

	lottery.initialize()

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
	lottery = g.deploy(user=lottery_addr)
	b1 = g.connect(lottery.address, user=b1_addr)
	b2 = g.connect(lottery.address, user=b2_addr)

	# b1.buy(wei_amount=1000)
	# b2.buy(wei_amount=1000)
	# lottery.start(193775903028374)
	# b1.bet(193775903028370, 100)
	# b2.bet(20483, 20)
	#
	lottery.consistency_transformation()
	b1.bet(338958310939602478766429100696605293569, 0)
	b2.bet(338958310939602478766429100696605293569, 0)
	lottery._test_advance_time()
	lottery._test_advance_time()
	lottery._test_advance_time()
	lottery.start(193775903028374)
