#!/usr/bin/env python3
import sys

from dynamiczk.zkay_interface import zkay_tool
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade, consistency_transform, \
	contract_migration, get_all_values_to_upgrade
import pickle, os

# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	sender_addr, receiver_addr = g.create_dummy_accounts(2)

	sender = g.deploy(user=sender_addr)
	receiver = g.connect(sender.address, user=receiver_addr)

	sender.fund(wei_amount=1000)
	sender.transfer(receiver_addr, 100)
	receiver.into_vault(45)
	# receiver.burn(55)
	# receiver.from_vault(45)

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

	# sender.fund(wei_amount=1000)
	# sender.transfer(receiver_addr, 100)
	# receiver.into_vault(45)
	receiver.burn(55)
	receiver.from_vault(45)