import json
import operator

# 假设你的 JSON 数据已经保存在一个字符串变量 data 中
dataFileName = './coverage_test.json'

# 将 JSON 数据解析为 Python 字典
# 读取文件并使用 json.load() 转换为字典
with open(dataFileName, 'r') as f:
    coverage_data = json.load(f)

# 获取 files 部分
files = coverage_data['files']
solution_tuple_list = [] #放三元组 然后用lambda函数进行排序
for solution in files.keys():
    solution_result = files[solution]
    solution_index = solution.split('_')[-1].split('.')[0]
    # 都自己计算吧 coverage库给出的只保留了一位小数
    solution_line_cov_percent = int(solution_result['summary']['covered_lines'])/int(solution_result['summary']['num_statements'])
    # 按覆盖的分支数百分比来排序更具有说服力
    solution_branch_cov_percent = int(solution_result['summary']['covered_branches'])/int(solution_result['summary']['num_branches'])
    solution_tuple_list.append((int(solution_index),solution_line_cov_percent,solution_branch_cov_percent))

#排序
# cmp参数接受一个比较两个项的函数。如果函数返回True，则第一个参数应该排在第二个参数之前
def index_tuple_compare(x):
    # 先比较第二项行覆盖率 再比较第三项分支覆盖率 最后比较第一项index自然排序
    return x[1],x[2],-x[0]
solution_index_rank_list = sorted(solution_tuple_list,key = lambda x: index_tuple_compare(x), reverse=True)
print(solution_index_rank_list)
#将id转为solution_id
solution_id_rank_list = []
# for item in solution_index_rank_list:
#     solution_id_rank_list = temp_index_to_solution_id_dict[item[0]]
#读出total
total_consensus_cov = coverage_data['totals']
consensus_line_cov_percent = float(total_consensus_cov['percent_covered'])
consensus_branch_cov_percent = float(total_consensus_cov['covered_branches'])/int(total_consensus_cov['num_branches'])
print(consensus_branch_cov_percent)
print(consensus_line_cov_percent)



#最后也全部写入一个json文件里面
#格式为
#   Meta:  dataSetName:
#          modelParamsName:
#   tasks:
#         task_id:
#               consensus_0:
#                         caseset: list
#                         solution_id_rank_list: list
#                         consensus_line_cov_percent: float
#                         consensus_branch_cov_percent: float
#               consensus_1:
#
#
#
#





# # 假设你想要降序排序（最高的覆盖率排在前面）
# sorted_files = dict(sorted(files.items(), key=operator.itemgetter('summary')['percent_covered']), reverse=True))
#
# # 将排序后的 files 数据放回 coverage_data 中
# coverage_data['files'] = sorted_files
#
# # 将排序后的字典转换回 JSON 字符串
# sorted_data = json.dumps(coverage_data, indent=4)
#
# # 打印排序后的 JSON 数据
# print(sorted_data)