#!/usr/bin/env python3
import sys

from dynamiczk.zkay_interface import zkay_tool
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade, consistency_transform, \
	contract_migration, get_all_values_to_upgrade
import pickle, os

# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	receiver_addr, sender_addr = g.create_dummy_accounts(2)

	receiver = g.deploy(user=receiver_addr)
	sender = g.connect(receiver.address, user=sender_addr)

	receiver.prepare(0, 1)
	sender.send(24, 59)

	# receiver.prepare(1, 0)
	# sender.send(42, 18)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([receiver, sender])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	zkay_tool.enable_migration = True
	get_all_values_to_upgrade(sys.argv[3])

	receiver = g.deploy(user=receiver_addr)
	sender = g.connect(receiver.address, user=sender_addr)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'rb') as file:
		params = pickle.load(file)

	contract_migration(receiver, sys.argv[3])
	consistency_transform(receiver, params, sys.argv[3])

	# receiver.prepare(0, 1)
	# sender.send(24, 59)

	receiver.prepare(1, 0)
	sender.send(42, 18)
