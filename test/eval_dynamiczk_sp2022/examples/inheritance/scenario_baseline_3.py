#!/usr/bin/env python3
import sys
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade
import pickle, os
from dynamiczk.zkay_interface import zkay_tool
zkay_tool.enable_proxy = True
# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	a_addr, b_addr, c_addr = g.create_dummy_accounts(3)

	a = g.deploy(user=a_addr)
	b = g.connect(a.address, user=b_addr)
	c = g.connect(a.address, user=c_addr)

	a.initialize()

	a.buy(wei_amount=1000)
	b.buy(wei_amount=100)
	c.buy(wei_amount=100)
	a.pledge_inheritance(b_addr, 50)
	a.pledge_inheritance(c_addr, 20)

	a.sell(10)
	a.transfer(20, b_addr)

	# a._test_advance_time()
	# b.claim_inheritance(a_addr)
	# c.claim_inheritance(a_addr)
	#
	# b.sell(170)
	# c.sell(120)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([a, b, c])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	a = g.deploy(user=a_addr)
	b = g.connect(a.address, user=b_addr)
	c = g.connect(a.address, user=c_addr)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'rb') as file:
		params = pickle.load(file)

	# a.buy(wei_amount=100)
	# b.buy(wei_amount=100)
	# c.buy(wei_amount=100)
	# a.pledge_inheritance(b_addr, 50)
	# a.pledge_inheritance(c_addr, 20)
	#
	# a.sell(10)
	# a.transfer(20, b_addr)

	a.consistency_transformation()
	a.pledge_inheritance(b_addr, 0)
	a.transfer(0, b_addr)
	a.transfer(100, b_addr)

	a._test_advance_time()
	b.claim_inheritance(a_addr)
	c.claim_inheritance(a_addr)

	b.sell(170)
	c.sell(120)
