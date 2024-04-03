# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

# import ctypes
# libgcc_s = ctypes.CDLL('libgcc_s.so.1')

from collections import defaultdict
from concurrent.futures import as_completed, ProcessPoolExecutor
import logging

from src._execution import check_correctness, check_correctness_with_test_cases

logging.basicConfig(
    format="SystemLog: [%(asctime)s][%(name)s][%(levelname)s] - %(message)s", #日志的输出格式：时间戳asctime 日志名称name 级别名称levelname message日志内容
    datefmt="%Y-%m-%d %H:%M:%S", #输出格式：年-月-日 时：分：秒
    level=logging.INFO, #级别info级别以上输出
)

logger = logging.getLogger(__name__)
#__name__ 表示当前模块的名称，通常在模块中使用该方法可以创建一个与当前模块名称相关联的日志记录器对象，
def evaluate_with_test_code(
    samples,
    timeout
):
    logger.info(f'Start evaluation with test code, timeout={timeout}')
    # Check the generated samples against test suites.
    with ProcessPoolExecutor() as executor: #创建进程池执行器

        futures = []
        existed_completion = defaultdict(set) #默认value是set的字典
        results = defaultdict(defaultdict)

        for sample in samples: #现将字典里面的信息读出来
            task_id = sample["task_id"]
            prompt = sample['prompt']
            test = sample['test']
            entry_point = sample['entry_point']
            completion = sample["completion"]
            if completion in existed_completion[task_id]:
                continue #如果集合中已经有这个回答了直接进入下一次循环
            existed_completion[task_id].add(completion)#将回答加入集合中
            args = (task_id, prompt, completion, test, entry_point, timeout)
            future = executor.submit(check_correctness, *args)
            #使用 *args 的形式对元组 args 进行解包，意味着将元组中的各个元素作为参数传递给check_correctness
            futures.append(future)#future是个对象类型，可以.result()方法查看传入方法的返回结果 可以用as_completed(futures)按执行完成顺序排列
        logger.info(f'{len(futures)} execution requests are submitted')
        
        for idx, future in enumerate(as_completed(futures)):
            logger.info('[{}/{}] execution completed'.format(idx+1, len(futures))) #打印执行结果
            result = future.result()
            results[result["task_id"]][result["completion"]] = result #results是个两层字典 第一层是task_id 每个task_id 对应key为result["completion"]的字典

    logger.info('execution finished! start parsing results')
    samples_with_result = []
    for sample in samples:
        task_id = sample["task_id"]
        completion = sample["completion"]
        result = results[task_id][completion]
        sample["result"] = result["result"]#在原来的sample字典中加了两个属性 result 和passed
        sample["passed"] = result["passed"]
        samples_with_result.append(sample) #再重新放回列表中

    assert len(samples_with_result) == len(samples), "Some problems are not attempted."

    return samples_with_result

def evaluate_with_test_cases(
    solutions,
    test_cases_dict,
    timeout,
    limit
):
    logger.info(f'Start evaluation with test cases, timeout={timeout}, limit={limit}')
    # Check the generated solutions against test suites.
    with ProcessPoolExecutor() as executor:
        futures = []
        results_list = []
        existed_completion = defaultdict(set)

        for solution in solutions:
            task_id = solution['task_id']
            prompt = solution['prompt']
            completion = solution['completion']
            if completion in existed_completion[task_id]:
                continue
            existed_completion[task_id].add(completion)
            task_test_cases = test_cases_dict[task_id] #读出来的是该问题的测试用例的列表
            # 测试
            # print(type(task_test_cases))
            # print(task_test_cases[0])
            # print(task_test_cases[0][0])

            if not task_test_cases:
                continue
            # get limited test cases
            limited_task_test_cases = [cases_per_sample[:limit] for cases_per_sample in task_test_cases] #这里是限制了每个测试用例的长度，而不是限制的总测试样例的个数
            limited_task_test_cases = sum(limited_task_test_cases, []) #这里是把测试样例变成
            #todo ？？？这里为什么不是 limit_task_test_cases = task_test_cases[:limit]
            args = (task_id, prompt, completion, list(set(limited_task_test_cases)), timeout)
            future = executor.submit(check_correctness_with_test_cases, *args)
            futures.append(future)

        logger.info(f'{len(futures)} execution requests are submitted')
        for idx, future in enumerate(as_completed(futures)):
            logger.info('[{}/{}] execution completed'.format(idx+1, len(futures)))
            result = future.result()
            results_list.append(result)#这时传入的solution字典列表中。已经有了result 和passed 属性了不过是用标准测试测的

    logger.info('execution finished!')
    return results_list

