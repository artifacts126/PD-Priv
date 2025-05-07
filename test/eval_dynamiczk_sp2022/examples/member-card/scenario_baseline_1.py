#!/usr/bin/env python3
import sys

from dynamiczk.zkay_interface import zkay_tool
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade, consistency_transform, \
	contract_migration, get_all_values_to_upgrade
import pickle, os

# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	issuer_addr, owner_addr = g.create_dummy_accounts(2)

	issuer = g.deploy(owner_addr, user=issuer_addr)
	owner = g.connect(issuer.address, user=owner_addr)

	issuer.updateBalance(59, wei_amount=100)
	# issuer.updateBalance(48, wei_amount=100)
	# owner.redeemBonus()

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([issuer, owner])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	zkay_tool.enable_migration = True
	get_all_values_to_upgrade(sys.argv[3])

	issuer = g.deploy(owner_addr, user=issuer_addr)
	owner = g.connect(issuer.address, user=owner_addr)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'rb') as file:
		params = pickle.load(file)

	contract_migration(issuer, sys.argv[3])
	consistency_transform(issuer, params, sys.argv[3])

	# issuer.updateBalance(59, wei_amount=100)
	issuer.updateBalance(48, wei_amount=100)
	owner.redeemBonus()
