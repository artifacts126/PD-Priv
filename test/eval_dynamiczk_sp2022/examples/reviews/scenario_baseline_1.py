#!/usr/bin/env python3
import sys

from dynamiczk.zkay_interface import zkay_tool
from zkay.zkay_frontend import transaction_benchmark_ctx
from dynamiczk.transform_zkay_for_consistency.params_transform import get_all_params_to_upgrade, consistency_transform, \
	contract_migration, get_all_values_to_upgrade
import pickle, os

# Scenario
with transaction_benchmark_ctx(sys.argv[1], log_filename=sys.argv[2]) as g:
	pc_addr, r1_addr, r2_addr, author_addr = g.create_dummy_accounts(4)

	pc = g.deploy(user=pc_addr)
	r1 = g.connect(pc.address, user=r1_addr)
	r2 = g.connect(pc.address, user=r2_addr)
	author = g.connect(pc.address, user=author_addr)

	pc.registerReviewer(r1_addr)
	pc.registerReviewer(r2_addr)
	author.registerPaper(1234)
	# r1.recordReview(1234, 3)
	# r2.recordReview(1234, 2)
	# pc.decideAcceptance(author_addr)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'wb') as file:
		pickle.dump(list(get_all_params_to_upgrade([pc, r1, r2, author])), file)

with transaction_benchmark_ctx(sys.argv[3], log_filename=sys.argv[4]) as g:
	zkay_tool.enable_migration = True
	get_all_values_to_upgrade(sys.argv[3])

	pc = g.deploy(user=pc_addr)
	r1 = g.connect(pc.address, user=r1_addr)
	r2 = g.connect(pc.address, user=r2_addr)
	author = g.connect(pc.address, user=author_addr)

	with open(os.path.join(os.path.dirname(sys.argv[1]), 'params.pkl'), 'rb') as file:
		params = pickle.load(file)

	contract_migration(pc, sys.argv[3])
	consistency_transform(pc, params, sys.argv[3])

	# pc.registerReviewer(r1_addr)
	# pc.registerReviewer(r2_addr)
	# author.registerPaper(1234)
	r1.recordReview(1234, 3)
	r2.recordReview(1234, 2)
	pc.decideAcceptance(author_addr)
