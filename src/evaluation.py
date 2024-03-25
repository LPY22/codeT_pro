# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import statistics
import numpy as np
from collections import defaultdict
import logging
from typing import List, Union
import itertools

logging.basicConfig(
    format="SystemLog: [%(asctime)s][%(name)s][%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

def _dictionized_ground_truth_results(ground_truth_exec_results):
    ground_truth_results_by_task_and_solution = defaultdict(defaultdict) #key分别是是task_id 和 solution的双重字典
    for result in ground_truth_exec_results:
        ground_truth_results_by_task_and_solution[result['task_id']][result['completion']] = result['passed']  #value是代表是否通过的true/false
    return ground_truth_results_by_task_and_solution

def _turn_solution_scores_into_choose_count(sorted_solution_scores, topk):
    # sorted_solution_scores: list of (solution, score) 传入的排序列表 _turn_solution_scores_into_choose_count(sorted_solutions_by_task[task_id], topk)取过task_id了
    # if wrapped, sorted_solution_scores is list of ([solutions], score)
    # return list of (solution, choose_count)
    wrapped = True if type(sorted_solution_scores[0][0]) == list else False
    result = []
    if wrapped:
        last_score = sorted_solution_scores[0][1] #先取出了最高分
        merged_solutions_and_score = [sorted_solution_scores[0]] #为啥要带括号[()]
        for solutions, score in sorted_solution_scores[1:]:#对于第二个及以后的元组
            if score == last_score:
                last_solutions = merged_solutions_and_score[-1][0]
                merged_solutions_and_score[-1] = (last_solutions + solutions, score) #如果分数一样，就把两个共识集里面的solution合并，等于是完全按照分数score来排列
            else:
                merged_solutions_and_score.append((solutions, score)) #不同就直接往后append,然后把last_score往后传递
                last_score = score
        for solutions_and_score in merged_solutions_and_score:
            result.append((solutions_and_score[0], 1))  # choose one from solutions_and_score （每个分数的solutions集合，1），应该为了后面的操作
    else:#todo sorted_solution_scores[0][0]不是列表 难道就是只有一个solution??
        topk_scores = sorted(list(set([i[1] for i in sorted_solution_scores])), reverse=True)#i[1]是取分数 现将分数取集合去重然后转列表list在排序 可以直接sorted(set)对集合排序，结果直接是列表
        for score in topk_scores:
            solutions = [s[0] for s in sorted_solution_scores if s[1] == score] #重新按照分数 构造solutions集合
            result.append((solutions, 1)) #构建result列表

    if len(result) >= topk:
        return result[:topk] #如果多了截断前topk个 chooose_count = 1
    else:
        intial_choose_count = [1]*len(result)
        for i in range(topk-len(result)): #按分数顺序，依次增加被选择数choose_count
            intial_choose_count[i%len(result)] += 1
        for i, choose_count in enumerate(intial_choose_count):
            result[i] = (result[i][0], choose_count) #更新每个solutions集的choose_count 似的总数满足topk
        return result
    

def get_result_of_sorted_solutions(ground_truth_results_list, sorted_solutions_by_task, topks=[1,2,10]):
    # sorted_solutions_by_task {task_id: [([solutions], score), ...]}
    def _count_correct(solutions: list, ground_truth_results: dict) -> int:
        return sum([ground_truth_results[s] for s in solutions])
    
    ground_truth_results = _dictionized_ground_truth_results(ground_truth_results_list) #转成更方便的双重字典{ task_id1 ：{solution1 ：是否通过(只有一个值因为只有一个标准测试)}}
    topk_results = dict()
    for topk in topks: #[1,2,10]
        random_pass_at_k_by_task = pass_at_K_by_task(ground_truth_results_list, k=topk) #得到一个字典，算出每个task_id的pass #ground_truth_result_list对应的solution只有标准测试通不通过的结果
        pass_rates = []
        for task_id in ground_truth_results.keys():
            all_wrong_probability = 1
            if task_id in sorted_solutions_by_task and sorted_solutions_by_task[task_id]: #验证存在和非空
                solutions_and_probability = _turn_solution_scores_into_choose_count(sorted_solutions_by_task[task_id], topk)
                for solutions, choose_count in solutions_and_probability:
                    current_wrong_prob = _estimator(len(solutions), _count_correct(solutions, ground_truth_results[task_id]), 1)
                    repeat_current_wrong_prob = pow(current_wrong_prob, choose_count)
                    all_wrong_probability *= repeat_current_wrong_prob
                pass_rates.append(1-all_wrong_probability)
            else:
                pass_rates.append(random_pass_at_k_by_task[task_id])
        
        # the avg rate of all tasks
        topk_results[f'pass@{topk}'] = round(statistics.mean(pass_rates), 4)
    logger.info(topk_results)

def pass_at_K_by_task(results, k): #result 字典列表 k int
    result_dict = defaultdict(list)
    for line in results:
        result_dict[line['task_id']].append(line['passed']) #result_dict 把每个task_id的通过和不通过放在一个列表里
    result = dict()
    for task_id in result_dict.keys():
        total = len(result_dict[task_id]) #每个task_id有的测试数
        correct = sum(result_dict[task_id]) #求sum 每个task_id通过的测试数
        score = _estimate_pass_at_k(total, [correct], k)[0] #算出这个task_id对应的pass@k分数 本来应该是可以所有的放进去一起算的
        result[task_id] = score
    return result

def pass_at_K(results, k = [1, 10, 100]):
    def _turn_list_into_dict(result_lines):#result_lines是字典列表 如果是ground_truth_exec_result就是一个问题一个测试
        result_dict = defaultdict(list)
        for line in result_lines:  #取出每个字典
            result_dict[line['task_id']].append(line['passed'])
        return result_dict #key: task_id value passed对应的true或者false列表

    # Calculate pass@k.
    total, correct = [], []
    for passed in _turn_list_into_dict(results).values(): #。values()获取测试数列表[true,false,,,,] total求len对应每个问题的测试数 correct求和sum对应每个问题通过的测试数
        total.append(len(passed))
        correct.append(sum(passed)) #收集true的数量++

    total = np.array(total) #数组 对应每个回答的测试数int 如果是标测就是1*回答的采样数 因为是用task_id收集的
    correct = np.array(correct)#数组 对应每个回答的通过数int 如果是标测就是1/0

    ks = k
    pass_at_k = {f"pass@{k}": round(_estimate_pass_at_k(total, correct, k).mean(), 4)#保留四位小数 。mean()返回平均值
                 for k in ks if (total >= k).all()} #np.ndarray .all()方法对应矩阵里面的每个元素都要为true
    logger.info(pass_at_k)

def _estimator(n: int, c: int, k: int) -> float: #求一个组合数，后面求pass@k时候采样要用到 沛= 1-C(n-c,k)/c(n-k) 1-抽到的回答全不pass
    """
    Calculates comb(n - c, k) / comb(n, k).
    """
    if n - c < k:
        return 0
    return np.prod(1.0 - k / np.arange(n - c + 1, n + 1))

def _estimate_pass_at_k(
    num_samples: Union[int, List[int], np.ndarray],
    num_correct: Union[List[int], np.ndarray],
    k: int
) -> np.ndarray:  #Union[]表示参数类型可以取列表里面的任一类型
    """
    Estimates pass@k of each problem and returns them in an array.
    """
    if isinstance(num_samples, int):
        num_samples_it = itertools.repeat(num_samples, len(num_correct))
    # itertools.repeat(object,time) 函数会生成一个迭代器，该迭代器会持续地返回指定的 object 值，直到达到指定的 times 次数为止。
    # 如果未指定 times 参数，itertools.repeat 会无限地产生指定的 object。
    else:
        assert len(num_samples) == len(num_correct)
        num_samples_it = iter(num_samples)

    return np.array([1.0 - _estimator(int(n), int(c), k) for n, c in zip(num_samples_it, num_correct)])