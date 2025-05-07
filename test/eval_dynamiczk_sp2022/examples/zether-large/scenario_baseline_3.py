#!/usr/bin/env python3
import sys
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade
import pickle, os
from dynamiczk.zkay_interface import zkay_tool
zkay_tool.enable_proxy = True
# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	sender_addr, receiver_addr = g.create_dummy_accounts(2)

	sender = g.deploy(user=sender_addr)
	receiver = g.connect(sender.address, user=receiver_addr)

	sender.initialize()

	sender.fund(wei_amount=1000)
	sender.transfer(receiver_addr, 100)
	receiver.into_vault(45)
	# receiver.burn(55)
	# receiver.from_vault(45)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([sender, receiver])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	sender = g.deploy(user=sender_addr)
	receiver = g.connect(sender.address, user=receiver_addr)

	# sender.fund(wei_amount=1000)
	# sender.transfer(receiver_addr, 100)
	# receiver.into_vault(45)
	sender.consistency_transformation()
	sender.transfer(receiver_addr, 0)
	receiver.burn(55)
	receiver.from_vault(45)