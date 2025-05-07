#!/usr/bin/env python3
import sys
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade
import pickle, os
from dynamiczk.zkay_interface import zkay_tool
zkay_tool.enable_proxy = True
# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	admin_addr, user_addr, stock_1_addr, stock_2_addr = g.create_dummy_accounts(4)

	admin = g.deploy(user=admin_addr)
	user = g.connect(admin.address, user=user_addr)
	stock_1 = g.connect(admin.address, user=stock_1_addr)
	stock_2 = g.connect(admin.address, user=stock_2_addr)

	admin.initialize()

	admin.add_stocks_to_funds(stock_1_addr, 1, 10)
	admin.add_stocks_to_funds(stock_2_addr, 3, 5)

	user.pay_into(wei_amount=250)
	user.buy_shares(10)

	# stock_2.report_new_stock_price(2)
	# user.sell_shares(5)
	# user.pay_out(50)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([admin, user, stock_1, stock_2])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	admin = g.deploy(user=admin_addr)
	user = g.connect(admin.address, user=user_addr)
	stock_1 = g.connect(admin.address, user=stock_1_addr)
	stock_2 = g.connect(admin.address, user=stock_2_addr)

	# admin.add_stocks_to_funds(stock_1_addr, 1, 10)
	# admin.add_stocks_to_funds(stock_2_addr, 3, 5)
	#
	# user.pay_into(wei_amount=250)
	# user.buy_shares(10)

	admin.consistency_transformation()
	stock_2.report_new_stock_price(2)
	user.sell_shares(0)
	user.sell_shares(5)
	user.pay_out(50)
