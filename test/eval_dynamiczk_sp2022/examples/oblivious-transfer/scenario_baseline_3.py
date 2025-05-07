#!/usr/bin/env python3
import sys
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade
import pickle, os
from dynamiczk.zkay_interface import zkay_tool
zkay_tool.enable_proxy = True
# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	receiver_addr, sender_addr = g.create_dummy_accounts(2)

	receiver = g.deploy(user=receiver_addr)
	sender = g.connect(receiver.address, user=sender_addr)

	receiver.initialize()

	receiver.prepare(0, 1)
	sender.send(24, 59)

	# receiver.prepare(1, 0)
	# sender.send(42, 18)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([receiver, sender])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	receiver = g.deploy(user=receiver_addr)
	sender = g.connect(receiver.address, user=sender_addr)

	# receiver.prepare(0, 1)
	# sender.send(24, 59)

	receiver.consistency_transformation()
	receiver.prepare(1, 0)
	sender.send(42, 18)
