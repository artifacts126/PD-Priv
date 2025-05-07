#!/usr/bin/env python3

import sys

from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade, consistency_transform, \
	contract_migration, get_all_values_to_upgrade
from dynamiczk.zkay_interface import zkay_tool
from zkay.zkay_frontend import transaction_benchmark_ctx
import pickle, os

# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	sender_addr, receiver_addr = g.create_dummy_accounts(2)

	sender = g.deploy(user=sender_addr)
	receiver = g.connect(sender.address, user=receiver_addr)

	sender.buy(wei_amount=1000)
	# sender.transfer(100, receiver_addr)
	# receiver.sell(40)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([sender, receiver])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	zkay_tool.enable_migration = True
	get_all_values_to_upgrade(sys.argv[3])

	sender = g.deploy(user=sender_addr)
	receiver = g.connect(sender.address, user=receiver_addr)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'rb') as file:
		params = pickle.load(file)

	contract_migration(sender, sys.argv[3])
	consistency_transform(sender, params, sys.argv[3])

	# sender.initialize()
	# sender.buy(wei_amount=1000)
	sender.transfer(100, receiver_addr)
	receiver.sell(40)
