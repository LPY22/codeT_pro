
from collections import defaultdict
#
# from src.io_utils import Tools
# test_predictions = Tools.load_jsonl("E:\PycharmProjects\CodeT\CodeT\data\generated_data\MBPP_incoder6B_temp0.8_topp0.95_num100_max300_test_case.jsonl")
# print("------------------test----------------")
# print(type(test_predictions))
#
# print(type(test_predictions[0]))
# print(test_predictions[0].keys())
# print(test_predictions[0])
# print("------------------solution----------------")
# solution_prediction = Tools.load_jsonl("E:\PycharmProjects\CodeT\CodeT\data\generated_data\MBPP_incoder6B_temp0.8_topp0.95_num100_max300_code_solution.jsonl")
# print(type(test_predictions))
#
# print(type(test_predictions[0]))
# print(test_predictions[0].keys())
# print(test_predictions[0])
# #不管是生成的测试还是被测函数都只有 prompt 和 sample 两个属性

import multiprocessing
import time

# def worker(d, key, value):
#     d[key] = value
#
# if __name__ == '__main__':
#     mgr = multiprocessing.Manager()
#     d = mgr.dict()
#     jobs = [ multiprocessing.Process(target=worker, args=(d, i, i*2))
#              for i in range(10)
#              ]
#     for j in jobs:
#         j.start()
#     for j in jobs:
#         j.join()
#     print ('Results:' )

# 创建字典项
consensus1 = {
    "rankList": [1, 2, 3],
    "cov_percent": 0.75,
    "cov_3":0.8
}

consensus2 = {
    "rankList": [4, 5],
    "cov_percent": 0.85,
    "cov_3":0.9
}

# 创建字典并添加项
myDict = {
    "consensus1": consensus1,
    "consensus2": consensus2
}

# 打印字典
print(myDict)
rankList = sorted(myDict.values(),key=lambda x: (x['cov_percent'],x['cov_3']),reverse=True)
print(rankList)