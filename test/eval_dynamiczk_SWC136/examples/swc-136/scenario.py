#!/usr/bin/env python3
import sys
from zkay.zkay_frontend import transaction_benchmark_ctx

# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	odd_even_addr, p1_addr, p2_addr = g.create_dummy_accounts(3)

	odd_even = g.deploy(user=odd_even_addr)
	p1 = g.connect(odd_even.address, user=p1_addr)
	p2 = g.connect(odd_even.address, user=p2_addr)

	p1.buy(wei_amount=1000)
	p2.buy(wei_amount=1000)
	p1.transfer(100, p2_addr)

	odd_even.start(5)
	p1.play(3)
	p2.play(7)

	odd_even._test_advance_time()
	odd_even.select_winner()
	p1.sell(899)
	p2.sell(1101)
