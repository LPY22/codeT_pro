
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

def worker(d, key, value):
    d[key] = value

if __name__ == '__main__':
    mgr = multiprocessing.Manager()
    d = mgr.dict()
    jobs = [ multiprocessing.Process(target=worker, args=(d, i, i*2))
             for i in range(10)
             ]
    for j in jobs:
        j.start()
    for j in jobs:
        j.join()
    print ('Results:' )
