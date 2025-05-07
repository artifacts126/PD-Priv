#!/usr/bin/env python3
import sys

from dynamiczk.zkay_interface import zkay_tool
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade, consistency_transform, \
	contract_migration, get_all_values_to_upgrade
import pickle, os

# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	a_addr, b_addr, c_addr, owner_addr = g.create_dummy_accounts(4)

	owner = g.deploy(user=owner_addr)
	a = g.connect(owner.address, user=a_addr)
	b = g.connect(owner.address, user=b_addr)
	c = g.connect(owner.address, user=c_addr)

	a.vote(0)
	b.vote(1)
	# c.vote(1)
	# owner.declareWinner()

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([owner, a, b, c])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	zkay_tool.enable_migration = True
	get_all_values_to_upgrade(sys.argv[3])

	owner = g.deploy(user=owner_addr)
	a = g.connect(owner.address, user=a_addr)
	b = g.connect(owner.address, user=b_addr)
	c = g.connect(owner.address, user=c_addr)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'rb') as file:
		params = pickle.load(file)

	contract_migration(owner, sys.argv[3])
	consistency_transform(owner, params, sys.argv[3])

	# a.vote(0)
	# b.vote(1)
	c.vote(1)
	owner.declareWinner()
