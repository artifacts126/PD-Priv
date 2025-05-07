#!/usr/bin/env python3
# usage ./benchmark.py [example_dir]
# (example_dir contains subdirectories with example sol/zkay and scenario files)

# requires installed memory-profiler and zkay packages

import os
import datetime
import sys
import shutil
from enum import Enum

from dynamiczk.transform_zkay_for_consistency.params_transform import local_var_supplement
from dynamiczk.transform_zkay_for_consistency.upgrade_transform import enable_upgradeable
from dynamiczk.transform_zkay_for_consistency.code_transform import transform_zkay, TransformationType


class BaselineType(Enum):
    MIGRATE = 1
    PROXY = 2
    TOOL = 3

file_dir = os.path.realpath(os.path.dirname(__file__))
base_dir = os.path.join(file_dir, 'examples')

zkay_interface_file =  os.path.join(os.path.dirname(os.path.dirname(file_dir)), 'zkay_interface/zkay_tool.py')
node_modules_example_path = os.path.join(os.path.dirname(file_dir), 'node_modules_example')

def run_benchmark(baseline_type: Enum, compile: bool, run: bool, disable_verification: bool=False, clean: bool=False, node_clean: bool=False):
    for dirname in os.listdir(base_dir):
        if dirname not in ['inheritance']:
            continue
        p = os.path.join(base_dir, dirname)
        if os.path.isdir(p):
            zkay_files = []
            for filename in os.listdir(p):
                if filename.endswith(('.sol', '.zkay')) and 'transformed' not in filename:
                    file = os.path.join(p, filename)
                    zkay_files.append(file)

            out_dir_original = None
            out_dir_upgrade = None

            # transform and compile zkay files
            for zkay_file in zkay_files:
                if os.path.basename(zkay_file).startswith('original'):
                    if baseline_type == BaselineType.PROXY or baseline_type == BaselineType.TOOL:
                        output_filename = 'transformed_init.zkay'
                        transform_zkay(TransformationType.INIT, zkay_file, p, output_filename)
                    else:
                        output_filename = os.path.basename(zkay_file)
                    out_dir = os.path.join(p, 'compiled_original')
                    out_dir_original = out_dir
                else:
                    if baseline_type == BaselineType.PROXY:
                        output_filename = 'transformed.zkay'
                        transform_zkay(TransformationType.CONSISTENCY, zkay_file, p, output_filename)
                    elif baseline_type == BaselineType.MIGRATE:
                        output_filename = 'transformed_migration.zkay'
                        transform_zkay(TransformationType.CONSISTENCY, zkay_file, p, output_filename)
                    elif baseline_type == BaselineType.TOOL:
                        output_filename = 'transformed_optimized.zkay'
                        transform_zkay(TransformationType.CONSISTENCY_OPTIMIZED, zkay_file, p, output_filename)
                    else:
                        exit(1)
                    out_dir = os.path.join(p, 'compiled')
                    out_dir_upgrade = out_dir

                if clean and os.path.exists(out_dir):
                    shutil.rmtree(out_dir)
                os.makedirs(out_dir, exist_ok=True)
                transformed_file = os.path.join(p, output_filename)

                if compile:
                    compile_args = f"--verbosity 0 --opt-hash-threshold 0 -o '{out_dir}'"
                    if not disable_verification:
                        print(f'compiling {zkay_file}, at {datetime.datetime.utcnow()}')
                        os.system(f"python '{zkay_interface_file}' compile '{transformed_file}' {compile_args} --log --log-dir '{out_dir}'")
                    else:
                        print(f'compiling {zkay_file} with disabled verification, at {datetime.datetime.utcnow()}')
                        os.system(f"python '{zkay_interface_file}' compile '{transformed_file}' {compile_args} --disable-verification")

                    if baseline_type == BaselineType.PROXY or baseline_type == BaselineType.TOOL:
                        onchain_file = os.path.join(out_dir, 'contract.sol')
                        enable_upgradeable(onchain_file, onchain_file)
                        if baseline_type == BaselineType.TOOL:
                            interface_file = os.path.join(out_dir, 'contract.py')
                            local_var_supplement(interface_file, interface_file)

                    node_modules_dst = os.path.join(out_dir, 'node_modules')
                    if node_clean and os.path.exists(node_modules_dst):
                        shutil.rmtree(out_dir)
                    if not os.path.exists(node_modules_dst):
                        shutil.copytree(node_modules_example_path, node_modules_dst)

            if run:
                if baseline_type == BaselineType.MIGRATE:
                    scenario_file = os.path.join(p, 'scenario_baseline_1.py')
                    log_name = 'log_migration'
                elif baseline_type == BaselineType.PROXY:
                    scenario_file = os.path.join(p, 'scenario_baseline_2.py')
                    log_name = 'log_proxy'
                else:
                    scenario_file = os.path.join(p, 'scenario_baseline_3.py')
                    log_name = 'log_tool'

                if disable_verification:
                    log_name = log_name + '_no_verification'

                if os.path.exists(scenario_file):
                    os.system(f"python '{scenario_file}' '{out_dir_original}' '{log_name}' '{out_dir_upgrade}' '{log_name}'")

def get_logging():
    for dirname in os.listdir(base_dir):
        baseline_dir = os.path.join(file_dir, 'baseline_examples')
        baseline_p = os.path.join(baseline_dir, dirname)
        if not os.path.exists(baseline_p):
            os.mkdir(baseline_p)

        p = os.path.join(base_dir, dirname)
        out_dir = os.path.join(p, 'compiled')
        for filename in os.listdir(out_dir):
            if filename in ['compile_data.log', 'log_data.log', 'log_no_verification_data.log']:
                file = os.path.join(out_dir, filename)
                target = os.path.join(baseline_p, 'compiled')
                if not os.path.exists(target):
                    os.mkdir(target)
                shutil.copy(file, target)

        out_dir = os.path.join(p, 'compiled_original')
        for filename in os.listdir(out_dir):
            if filename in ['compile_data.log', 'log_data.log', 'log_no_verification_data.log']:
                file = os.path.join(out_dir, filename)
                target = os.path.join(baseline_p, 'compiled_original')
                if not os.path.exists(target):
                    os.mkdir(target)
                shutil.copy(file, target)

#get_logging()
run_benchmark(baseline_type=BaselineType.TOOL, compile=False, run=True)