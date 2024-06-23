# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import argparse
import logging
import os
import meta
from src.postprocess import PostProcessor
from src.execution import evaluate_with_test_code, evaluate_with_test_cases
from src.io_utils import Tools
from src.agreement import DataManager, DualAgreement
from src.evaluation import pass_at_K, get_result_of_sorted_solutions
from src.optimize import excludeAllpassTest

logging.basicConfig(
    format="SystemLog: [%(asctime)s][%(name)s][%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--source_path_for_solution", type=str, help="model input file in .jsonl format")
    parser.add_argument("--predict_path_for_solution", type=str, help="model output file in .jsonl format")
    parser.add_argument("--source_path_for_test", type=str, help="model input file in .jsonl format")
    parser.add_argument("--predict_path_for_test", type=str, help="model output file in .jsonl format")
    parser.add_argument("--cache_dir", type=str, help="the directory to store the cache files")
    parser.add_argument("--timeout", type=float, default=0.1, help="how many seconds to wait during execution for each test case")
    parser.add_argument("--test_case_limit", type=int, default=5, help="first n test cases per sample")
    # 通过命令行赋值
    # args = parser.parse_args()
    # 在代码中手动为 args 赋值
    source_solution_path={"HumanEval":"./data/dataset/HumanEval_for_code_generation.jsonl",
                          "MBPP":"./data/dataset/mbpp_sanitized_for_code_generation.jsonl",
                          "APPS":"./data/dataset/APPS_zeroshot_for_code_generation.jsonl",
                          "CodeContests":"./data/dataset/CodeContests_zeroshot_for_code_generation.jsonl"}
    source_test_path={"HumanEval":"./data/dataset/HumanEval_for_test_case_generation.jsonl",
                          "MBPP":"./data/dataset/mbpp_sanitized_for_test_case_generation.jsonl",
                          "APPS":"./data/dataset/APPS_zeroshot_for_test_case_generation.jsonl",
                          "CodeContests":"./data/dataset/CodeContests_zeroshot_for_test_case_generation.jsonl"}

    # predict_solution_path={}
    # predict_test_path={}
    datasetName=meta.datasetName
    modelParamsName = meta.modelParamsName
    # modelParamsName = "incoder6B_temp0.8_topp0.95_num100_max300"
    # modelParamsName = "MBPP_davinci002_temp0.8_topp0.95_num100_max300_code_solution.jsonl"
    # logger.info(datasetName+"\t"+modelParamsName)
    logger.info(f"datasetName:{datasetName}\tmodelParamsName:{modelParamsName}")
    args = argparse.Namespace(
        source_path_for_solution=source_solution_path[datasetName],
        #{
        #  task_id:
        #  prompt:
        #  entry_point:
        #  canonical_solution:
        #  test:
        # }
        predict_path_for_solution="./data/generated_data/"+datasetName+"_"+modelParamsName+"_"+"code_solution.jsonl",
        source_path_for_test=source_test_path[datasetName],
        # {
        #  task_id:
        #  prompt:
        #  entry_point:
        #  canonical_solution:
        #  test:
        # }
        predict_path_for_test="./data/generated_data/"+datasetName+"_"+modelParamsName+"_"+"test_case.jsonl",
        cache_dir="./cache_dir",
        timeout=0.1,
        test_case_limit=5
    )
    logger.info(args.predict_path_for_solution)
    logger.info(args.predict_path_for_test)
    logger.info(args.source_path_for_test)
    logger.info(args.source_path_for_solution)

    #抽样区间
    sample_section = [200,-1] #从头取的话不要填0，填-1表示没有左边界  HumanEval
    # sample_section = [-1,200] #MBPP codegen incoder
    # sample_section = [600,-1] #MBPP davince
    handled_solutions, task_count = PostProcessor.map_task_id_for_solution(args.predict_path_for_solution, args.source_path_for_solution,sample_section)
    #handled_solutions solution的字典列表 task_count有多少个task
    # {
    #     'task_id': task['task_id'],
    #     'prompt': pre['prompt'],
    #     'test': task['test'],
    #     'entry_point': task['entry_point'],
    #     'completion': processed_code
    # }
    handled_test_cases = PostProcessor.map_task_id_for_test_case(args.predict_path_for_test, args.source_path_for_test,sample_section)
    # 返回test_case的defaultdict key是taskid value是列表
    directory = os.path.join(args.cache_dir, datasetName, modelParamsName)
    if not os.path.exists(directory):
        os.makedirs(directory)
    ground_truth_exec_result = evaluate_with_test_code(handled_solutions, timeout=args.timeout)#得到一个字典列表，比handled_solution 多了两个属性passed 和 result
    Tools.dump_pickle(os.path.join(directory,'ground_truth_exec_result.pkl'), ground_truth_exec_result)#中间结果序列化

    dual_exec_result = evaluate_with_test_cases(handled_solutions, handled_test_cases, timeout=args.timeout, limit=args.test_case_limit)#得到每个solution用对应生成的test运行的结果字典
    # #得到了两部字典列表
    Tools.dump_pickle(os.path.join(directory,'dual_exec_result.pkl'), dual_exec_result)

    ground_truth_exec_result = Tools.load_pickle(os.path.join(args.cache_dir,datasetName,modelParamsName,'ground_truth_exec_result.pkl'))
    dual_exec_result = Tools.load_pickle(os.path.join(args.cache_dir,datasetName,modelParamsName,'dual_exec_result.pkl'))

    # dual_exec_result,handled_test_cases = excludeAllpassTest(dual_exec_result,handled_test_cases,handled_solutions)

    data_manager = DataManager(dual_exec_result, handled_solutions, handled_test_cases, args.test_case_limit,directory)#传入了testcase的运行结果，solution和testcase的字典列表，还有限制
    #构造函数初始化data_mamager
    set_consistency = DualAgreement(data_manager)
    # 初识化DualAgreement
    ranked_result = set_consistency.get_sorted_solutions_without_iter()
    # ranked_result = set_consistency.get_cross_sorted_solutions_without_iter()
    # ranked_result = set_consistency.get_cov_sorted_solutions_without_iter()
    #得到一个字典 {task_id1:[([solution_str1,solution_str2,,],score1),([],score2),([],score3)] #在一个列表里面的solution_str属于一个共识集，能通过相同的测试用例集分数也自然相同
    #            task_id2:[([],score1),([],score2),([],score3)]}

    logger.info('pass rates of ranked solutions')
    get_result_of_sorted_solutions(ground_truth_exec_result, ranked_result)
    logger.info('pass rates of random solutions')
    pass_at_K(ground_truth_exec_result)