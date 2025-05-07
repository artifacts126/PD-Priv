#!/usr/bin/env python3
import sys
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade, consistency_transform
import pickle, os
from dynamiczk.zkay_interface import zkay_tool
zkay_tool.enable_proxy = True
# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	owner_addr, other_addr = g.create_dummy_accounts(2)

	owner = g.deploy(user=owner_addr)
	other = g.connect(owner.address, user=other_addr)

	owner.initialize()

	owner.set_entry(0, 2)
	owner.set_entry(1, 3)
	# owner.set_entry(2, 9)
	# other.compute(6, 3, 0)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([owner, other])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	owner = g.deploy(user=owner_addr)
	other = g.connect(owner.address, user=other_addr)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'rb') as file:
		params = pickle.load(file)

	consistency_transform(owner, params, sys.argv[3])

	# owner.set_entry(0, 2)
	# owner.set_entry(1, 3)
	owner.set_entry(2, 9)
	other.compute(6, 3, 0)
