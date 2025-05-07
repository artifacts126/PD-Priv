#!/usr/bin/env python3
# usage ./benchmark.py [example_dir]
# (example_dir contains subdirectories with example sol/zkay and scenario files)

# requires installed memory-profiler and zkay packages

import os
import datetime
import sys
import shutil
from enum import Enum
import json

from dynamiczk.transform_zkay_for_consistency.params_transform import local_var_supplement
from dynamiczk.transform_zkay_for_consistency.upgrade_transform import enable_upgradeable
from dynamiczk.transform_zkay_for_consistency.code_transform import transform_zkay, TransformationType


class BaselineType(Enum):
    MIGRATE = 1
    PROXY = 2
    TOOL = 3

file_dir = os.path.realpath(os.path.dirname(__file__))
base_dir = os.path.join(file_dir, 'examples')
result_log = os.path.join(file_dir, 'result.log')

def contain_keyword(keyword, context):
    for c in context:
        if keyword in c:
            return True
    else:
        return False
def analyze_log(baseline_type: Enum, all_baseline_log, disable_verification=False):
    for dirname in os.listdir(base_dir):

        all_log = {}

        all_public_deploy = []
        all_public_init = []
        all_public_stage_1 = []
        all_public_average_trans = []
        all_public_stage_2 = []
        all_privacy_deploy_libs = []
        all_privacy_deploy_self = []
        all_privacy_stage_3_1 = []
        all_data_migration = []
        all_privacy_transformation = []
        all_privacy_stage_3_2 = []
        all_privacy_stage_3 = []
        all_privacy_average_trans = []
        all_privacy_stage_4 = []
        all_stage = []

        all_privacy_transformation_time = []

        all_log['public_deploy'] = all_public_deploy
        all_log['public_init'] = all_public_init
        all_log['public_stage_1'] = all_public_stage_1
        all_log['public_average_trans'] = all_public_average_trans
        all_log['public_stage_2'] = all_public_stage_2
        all_log['privacy_deploy_libs'] = all_privacy_deploy_libs
        all_log['privacy_deploy_self '] = all_privacy_deploy_self
        all_log['privacy_stage_3_1'] = all_privacy_stage_3_1
        all_log['data_migration'] = all_data_migration
        all_log['privacy_transformation'] = all_privacy_transformation
        all_log['privacy_stage_3_2'] = all_privacy_stage_3_2
        all_log['privacy_stage_3'] = all_privacy_stage_3
        all_log['privacy_average_trans'] = all_privacy_average_trans
        all_log['privacy_stage_4'] = all_privacy_stage_4
        all_log['all_stage'] = all_stage

        all_log['privacy_transformation_time'] = all_privacy_transformation_time

        p = os.path.join(base_dir, dirname)
        if os.path.isdir(p):
            if baseline_type == BaselineType.MIGRATE:
                log_name = 'log_migration'
                if 'migration' not in all_baseline_log:
                    all_baseline_log['migration'] = {}
                all_baseline_log['migration'][dirname] = all_log
            elif baseline_type == BaselineType.PROXY:
                log_name = 'log_proxy'
                if 'proxy' not in all_baseline_log:
                    all_baseline_log['proxy'] = {}
                all_baseline_log['proxy'][dirname] = all_log
            else:
                log_name = 'log_tool'
                if 'tool' not in all_baseline_log:
                    all_baseline_log['tool'] = {}
                all_baseline_log['tool'][dirname] = all_log

            if disable_verification:
                log_name = log_name + '_no_verification'

            log_name = log_name + '_data.log'

            original_log = os.path.join(p, 'compiled_original', log_name)
            meta_original_data = []
            with open(original_log, 'r') as file:
                for line in file.readlines():
                    data = json.loads(line.strip())
                    meta_original_data.append(data)

            public_deploy = 0
            public_init = 0
            public_trans = 0
            public_trans_number = 0

            for data in meta_original_data:
                if 'gas' == data['key']:
                    if (contain_keyword('constructor', data['context'])) or len(data['context']) == 0:
                        public_deploy += data['value']
                    elif contain_keyword('initialize', data['context']):
                        public_init += data['value']
                    else:
                        public_trans += data['value']
                        public_trans_number += 1

            all_public_deploy.append(public_deploy)
            all_public_init.append(public_init)
            all_public_stage_1.append(public_deploy + public_init)
            all_public_average_trans.append(int(public_trans/public_trans_number))
            all_public_stage_2.append(public_trans)

            updated_log = os.path.join(p, 'compiled', log_name)
            meta_updated_data = []
            with open(updated_log, 'r') as file:
                for line in file.readlines():
                    data = json.loads(line.strip())
                    meta_updated_data.append(data)

            privacy_deploy_libs = 0
            privacy_deploy_self = 0
            data_migration = 0
            privacy_transformation = 0
            privacy_trans = 0
            privacy_trans_number = 0

            privacy_transformation_time = 0

            for data in meta_updated_data:
                if 'gas' == data['key']:
                    if contain_keyword('deploy_pki', data['context']) or \
                            contain_keyword('zk__Verify', data['context']) or \
                            contain_keyword('announcePk', data['context']):
                        privacy_deploy_libs += data['value']
                    elif contain_keyword('constructor', data['context']):
                        privacy_deploy_self += data['value']
                    elif contain_keyword('migration', data['context']):
                        data_migration += data['value']
                    elif contain_keyword('consistency', data['context']):
                        privacy_transformation += data['value']
                    else:
                        privacy_trans += data['value']
                        privacy_trans_number += 1

                if 'time_transaction_full' == data['key']:
                    if contain_keyword('consistency', data['context']):
                        privacy_transformation_time += data['value']


            all_privacy_deploy_libs.append(privacy_deploy_libs)
            all_privacy_deploy_self.append(privacy_deploy_self)
            all_privacy_stage_3_1.append(privacy_deploy_libs + privacy_deploy_self)
            all_data_migration.append(data_migration)
            all_privacy_transformation.append(privacy_transformation)
            all_privacy_stage_3_2.append(data_migration + privacy_transformation)
            all_privacy_stage_3.append(privacy_deploy_libs + privacy_deploy_self + data_migration + privacy_transformation)
            all_privacy_average_trans.append(int(privacy_trans/privacy_trans_number))
            all_privacy_stage_4.append(privacy_trans)
            gas_all = public_deploy + public_init + public_trans + privacy_deploy_libs + privacy_deploy_self + data_migration + privacy_transformation + privacy_trans
            all_stage.append(gas_all)

            all_privacy_transformation_time.append(privacy_transformation_time)



def analyze_all_baseline_logs():
    analyze_data_result = {}
    analyze_log(BaselineType.MIGRATE, analyze_data_result)
    analyze_log(BaselineType.PROXY, analyze_data_result)
    analyze_log(BaselineType.TOOL, analyze_data_result)
    with open(result_log, 'w') as file:
        json.dump(analyze_data_result, file, indent=4)

analyze_all_baseline_logs()