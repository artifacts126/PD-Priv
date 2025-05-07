#!/usr/bin/env python3
# usage ./benchmark.py [example_dir]
# (example_dir contains subdirectories with example sol/zkay and scenario files)

# requires installed memory-profiler and zkay packages

import os
import datetime
import sys
import shutil

from dynamiczk.transform_zkay_for_consistency.upgrade_transform import enable_upgradeable

clean=False
node_clean = False
from dynamiczk.transform_zkay_for_consistency.code_transform import transform_zkay_for_consistency
from dynamiczk.zkay_interface.zkay_tool import zkay_interface

file_dir = os.path.realpath(os.path.dirname(__file__))
zkay_interface_file = '/home/wtq/PycharmProjects/DynamicZk/dynamiczk/zkay_interface/zkay_tool.py'
node_modules_example_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(file_dir))), 'node_modules_example')

zkay_files = []
for filename in os.listdir(file_dir):
    if filename.endswith(('.sol', '.zkay')) and 'transformed' not in filename:
        file = os.path.join(file_dir, filename)
        zkay_files.append(file)

out_dir_original = None
out_dir_upgrade = None

# transform and compile zkay files
for zkay_file in zkay_files:
    if os.path.basename(zkay_file).startswith('original'):
        output_filename = 'original_transformed.zkay'
        transform_zkay_for_consistency(zkay_file, file_dir, True, output_filename)
        out_dir = os.path.join(file_dir, 'compiled_original')
        out_dir_original = out_dir
    else:
        output_filename = 'transformed.zkay'
        transform_zkay_for_consistency(zkay_file, file_dir, False, output_filename)
        out_dir = os.path.join(file_dir, 'compiled')
        out_dir_upgrade = out_dir

    if clean and os.path.exists(out_dir):
        shutil.rmtree(out_dir)
    os.makedirs(out_dir, exist_ok=True)
    transformed_file = os.path.join(file_dir, output_filename)

    print(f'compiling {zkay_file}, at {datetime.datetime.utcnow()}')
    os.system(f"python '{zkay_interface_file}' compile '{transformed_file}' --verbosity 0 --opt-hash-threshold 0 -o '{out_dir}' --log --log-dir '{out_dir}'")

    onchain_file = os.path.join(out_dir, 'contract.sol')
    enable_upgradeable(onchain_file, onchain_file)
    node_modules_dst = os.path.join(out_dir, 'node_modules')
    if node_clean and os.path.exists(node_modules_dst):
        shutil.rmtree(out_dir)
    if not os.path.exists(node_modules_dst):
        shutil.copytree(node_modules_example_path, node_modules_dst)


# for dirname in os.listdir(file_dir):
#     p = os.path.join(base_dir, dirname)
#     if os.path.isdir(p):
#         file = None
#         for filename in os.listdir(p):
#             if filename.endswith(('.sol', '.zkay')):
#                 file = os.path.join(p, filename)
#                 break
#         if file is not None:
#             out_dir = os.path.join(p, f'out_{backend}')
#
#             os.makedirs(out_dir, exist_ok=True)
#             print(f'compiling {file}, at {datetime.datetime.utcnow()}')
#             os.system(f"mprof run --include-children --nopython -o '{out_dir}/mprof_compile.dat' zkay compile '{file}' --verbosity 0 --crypto-backend {backend} --opt-hash-threshold 0 -o '{out_dir}' --log --log-dir '{out_dir}'")
#
#             scenario_file = os.path.join(p, 'scenario.py')
#             if os.path.exists(scenario_file):
#                 print(f'running {scenario_file}, at {datetime.datetime.utcnow()}')
#                 os.system(f"mprof run --include-children --nopython -o '{out_dir}/mprof_run.dat' python '{scenario_file}' '{out_dir}'")
