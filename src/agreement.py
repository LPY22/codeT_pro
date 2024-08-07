# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.
import json
import os
import random
import subprocess
from collections import defaultdict, Counter
import logging
import math
import src.optimize
from meta import datasetName,modelParamsName

logging.basicConfig(
    format="SystemLog: [%(asctime)s][%(name)s][%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)


# # 关闭文件处理器
# file_handler.close()

logger = logging.getLogger(__name__)

# data_manager = DataManager(dual_exec_result, handled_solutions, handled_test_cases,args.test_case_limit)  # 传入了testcase的运行结果，solution和testcase的字典列表，还有限制


class DataManager:
    def __init__(self, dual_exec_results, sampled_code_by_task, sampled_test_case_by_task, limit,data_filePath):
        logger.info('handling dual exec results')
        self.dual_exec_results = dual_exec_results
        self.sampled_code_by_task = sampled_code_by_task
        self.sampled_test_case_by_task = sampled_test_case_by_task
        self.limit = limit
        self.data_filePath = data_filePath
        
        self.solution_frequency_by_task = defaultdict(Counter)# 默认value类型是Counter #每个task的回答数
        self.test_case_frequency_by_task = dict()  #每个task的test case数
        self.passed_unique_solutions_by_task = defaultdict(set) #每个task运行成功的solution
        self.passed_unique_test_cases_by_task = defaultdict(set) #每个task运行成功的test_cases
        self.passed_solution_test_case_pairs_by_task = defaultdict(set) #每个task运行成功的的solution test_case对
        self.solution_string_to_id_range_by_task = dict() #每个任务给solution 排序 string : id id应该是序号
        self.test_case_string_to_id_range_by_task = dict() #每个任务给test_case排序 string : id id应该是序号
        self.solution_id_to_string_by_task = dict() # 相反的用id 取 solution代码字符串的字典
        self.test_case_id_to_string_by_task = dict() # 同上

        self.task_id_to_entrypoint_prompt = dict() # taskid:函数名的字典

        
        self.expanded_passed_solution_test_case_pairs_by_task = defaultdict(list) #扩展的solution-test case对，应该和共识集有关

        #get函数赋值
        self._get_solution_frequency()
        logger.info('got solution frequency')
        self._get_test_case_frequency()
        logger.info('got test case frequency')
        self._get_passed_solution_test_case_pairs_by_task()
        #passed_unique_solutions_by_task
        #passed_unique_test_cases_by_task
        #passed_solution_test_case_pairs_by_task
        logger.info('got passed solution test case pairs by task')

        self._get_solution_and_test_case_ids()
        logger.info('got solution and test case ids')
        #solution_string_to_id_range_by_task
        #test_case_string_to_id_range_by_task
        #solution_id_to_string_by_task
        #test_case_id_to_string_by_task
        self._get_expanded_dual_exec_result()
        logger.info('got expanded dual exec results')
        
    def _get_solution_frequency(self):
        for sample in self.sampled_code_by_task:
            task_id = sample['task_id']
            completion = sample['completion']
            entry_point = sample['entry_point']
            prompt = sample['prompt']
            if task_id not in self.task_id_to_entrypoint_prompt.keys():
                self.task_id_to_entrypoint_prompt[task_id] = (entry_point,prompt)
            self.solution_frequency_by_task[task_id][completion] += 1# defaultdict(Counter)

    def _get_test_case_frequency(self):
        for task_id in self.sampled_test_case_by_task.keys():
            task_test_cases = [
                cases_per_sample[:self.limit] for cases_per_sample in self.sampled_test_case_by_task[task_id]
            ]
            task_test_cases = sum(task_test_cases, []) #脱一层列表 其实可以task_test_cases = task_test_cases[0]
            self.test_case_frequency_by_task[task_id] = Counter(task_test_cases)  #dict()
    
    def _get_passed_solution_test_case_pairs_by_task(self):
        for result in self.dual_exec_results:#passed为true代表运行成功了，result['result']是一个列表
            if not result['passed']:
                continue
            for idx, test_case in enumerate(result['test_cases']):
                if result['result'][idx] != True:
                    continue
                if test_case not in self.test_case_frequency_by_task[result['task_id']]:
                    continue
                self.passed_solution_test_case_pairs_by_task[result['task_id']].add((result['completion'], test_case)) #defaultdict(set)
                self.passed_unique_solutions_by_task[result['task_id']].add(result['completion']) #defaultdict(set) key:id ,value:passed solution set
                self.passed_unique_test_cases_by_task[result['task_id']].add(test_case) #defaultdict(set) key:id ,value :passed testcases set

    def _build_string_to_id_range(self, frequency_dict, limited_values): #frequency_dict 是一个Counter对象 表示一个task 下的solution 计数器
        id_ranges = dict() #字典初识化可以是{} 集合初识化必须set()
        start_id = 0
        for key, value in frequency_dict.items(): #key是solution/testcase value是次数
            if key not in limited_values:
                continue
            id_ranges[key] = range(start_id, start_id + value) #方便后面的遍历
            start_id += value
        return id_ranges
    
    def _build_id_to_string(self, str_to_id_range):
        id_to_string = dict()
        for string in str_to_id_range.keys():
            for idx in str_to_id_range[string]:#获得range对象进行便利
                id_to_string[idx] = string
        return id_to_string
    
    def _get_solution_and_test_case_ids(self):
        for task_id in self.solution_frequency_by_task.keys():
            self.solution_string_to_id_range_by_task[task_id] = self._build_string_to_id_range(self.solution_frequency_by_task[task_id], self.passed_unique_solutions_by_task[task_id])
            #返回一个字典 key是solution value是个range(对象）[都是通过的solution]
            self.test_case_string_to_id_range_by_task[task_id] = self._build_string_to_id_range(self.test_case_frequency_by_task[task_id], self.passed_unique_test_cases_by_task[task_id])
            #返回一个字典 key是testcase value是一个range对[都是通过的testcase]
            self.solution_id_to_string_by_task[task_id] = self._build_id_to_string(self.solution_string_to_id_range_by_task[task_id])
            #转成key为0开始的id value为solution 的字典，自然排序
            self.test_case_id_to_string_by_task[task_id] = self._build_id_to_string(self.test_case_string_to_id_range_by_task[task_id])
            #转成key为0开始的id value为testcase 的字典，自然排序
    
    def _get_expanded_by_id_range(self, solution_id_range, test_case_id_range):
        result = list()
        for solution_id in solution_id_range:
            for test_case_id in test_case_id_range:
                result.append((solution_id, test_case_id))
        return result
    
    def _get_expanded_dual_exec_result(self):
        for task_id in self.passed_solution_test_case_pairs_by_task.keys():
            for solution_str, test_case_str in self.passed_solution_test_case_pairs_by_task[task_id]:
                solution_id_range = self.solution_string_to_id_range_by_task[task_id][solution_str]
                test_case_id_range = self.test_case_string_to_id_range_by_task[task_id][test_case_str]
                self.expanded_passed_solution_test_case_pairs_by_task[task_id] += self._get_expanded_by_id_range(solution_id_range, test_case_id_range)
                #expanded_passed_solution_test_case_pairs_by_task 的value是元组列表[(),(),()]元组是solution_id,test_case_id对子，就是这些对子都是能运行通过的 只是有solution/testcase是一样的


class DualAgreement:#set_consistency = DualAgreement(data_manager)
    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.data_filePath = data_manager.data_filePath
        self.dual_exec_results_by_task = data_manager.expanded_passed_solution_test_case_pairs_by_task #dual_exec_results_by_task 可重复的id对
        self.solution_id_to_string_by_task = data_manager.solution_id_to_string_by_task
        self.test_case_id_to_string_by_task = data_manager.test_case_id_to_string_by_task
        self.task_id_to_entrypoint_prompt = data_manager.task_id_to_entrypoint_prompt
        
        self.solution_passed_cases_by_task = defaultdict(defaultdict)#两层的嵌套字典
        self.caseset_passed_solutions_by_task = defaultdict(defaultdict)

        self.caseset_crossScore_by_task = defaultdict(defaultdict)
        self.sample_list = [] # 采样器列表， 里面每一项都是caseset_passed_solutins_by_task
        self.dataset_covfile_rootpath = ''

        self._get_solution_passed_case_set()
        logger.info('got solution passed case sets')




        logger.info('排除全通过测试中...')
        self._excludeAllpassTest()
        # src.optimize.excludeAllpassTest(self)
        logger.info('excluded allPass testcase...')


        self._get_caseset_passed_solutions()
        logger.info('got case set passed solutions')

        #获得存放数据集覆盖率文件的目录地址
        # self._get_dataset_covfile_rootpath()

        #除去每个task中那些通过了所有solution的testcase
        #
        # logger.info("写入共识集文件中...")
        # self._writeConsensusFile()

        self._get_caseset_crossScore2()
        logger.info('计算测试集cross分数2')
    def _get_dataset_covfile_rootpath(self):
        filepath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        filepath = os.path.join(filepath, "data")
        rootfilepath = os.path.join(filepath, datasetName + "_" + modelParamsName + "_Consensus")
        self.dataset_covfile_rootpath = rootfilepath
    def _writeConsensusFile(self):
    #  在data 目录下创建对应的文件夹
        rootfilepath = self.dataset_covfile_rootpath
        os.makedirs(rootfilepath, exist_ok=True)
        dataset_dict  =  dict() #准备好转为json格式的python字典
        dataset_dict['datasetName'] = datasetName
        dataset_dict['modelParamsName'] = modelParamsName
        dataset_dict['tasks'] = dict()
        for task_id in list(self.caseset_passed_solutions_by_task.keys()):
            task_dict = dict()
            filepath1 = os.path.join(rootfilepath,task_id.replace('/','_'))
            os.makedirs(filepath1,exist_ok=True)
            entry_point = self.task_id_to_entrypoint_prompt[task_id][0]#取entrypoint
            prompt = self.task_id_to_entrypoint_prompt[task_id][1]
            # 写测试文件内容，一个共识集的测试语全部放在一起
            for idx,caseset in enumerate(self.caseset_passed_solutions_by_task[task_id].keys()):
                solutionNum = len(self.caseset_passed_solutions_by_task[task_id][caseset])
                solutionPrefix = task_id.replace('/','_')+'_'+'solution'
                packageName = f'consensus_{idx}'
                task_dict[packageName] = dict()
                consensus_dict = task_dict[packageName]
                consensus_dict['caseset'] = caseset
                caseset_str = [self.test_case_id_to_string_by_task[task_id][id] for id in caseset]
                if len(caseset_str)==0:
                    continue
                testFileContent = self.getCasesetContent(caseset_str,entry_point,solutionNum,solutionPrefix,packageName)
                filepath2 = os.path.join(filepath1, packageName)
                os.makedirs(filepath2,exist_ok=True)
                fileName = os.path.join(filepath2,"all_test.py")
                # 在目录中创建文件并将字符串写入
                with open(fileName, "w") as file:
                    file.write(testFileContent)
                # 写共识集里所有方法的文件，每个方法（函数）单独一个文件
                temp_index_to_solution_id_dict = {}
                for index,solution_id in enumerate(self.caseset_passed_solutions_by_task[task_id][caseset]):
                    temp_index_to_solution_id_dict[index] = solution_id
                    solution_str = self.solution_id_to_string_by_task[task_id][solution_id]
                    solutionContent = prompt + solution_str + "\n"
                    filepath = os.path.join(filepath2,'solutions')
                    os.makedirs(filepath,exist_ok=True)
                    fileName = os.path.join(filepath,f'{solutionPrefix}_{index}.py')
                    with open(fileName,"w") as file:
                        file.write(solutionContent)
                #共识集里的文件已经写好了，直接算覆盖率 每个task下面的每个consensus文件夹下有一个文件
                # -HumanEval
                #    -task_0
                #       -consensus_0
                #           -solutions
                #           -all_test.py
                #           -.coverage
                #           -coverage.json
                #    -task_1


                #执行coverage run 和 coverage json 命令 在filepath2目录下 对应consensus一级目录
                # 指定工作目录并执行命令
                # testpath = 'data/HumanEval_davinci002_temp0.8_topp0.95_num100_max300_Consensus/HumanEval_0/consensus_0'
                # cwd = os.path.join(projectpath, testpath)
                # print(cwd)
                cwd = filepath2
                warn_output = subprocess.PIPE
                result = subprocess.run(['coverage', 'run', '--branch', '--source=solutions', 'all_test.py'],
                                        stderr=warn_output, cwd=cwd)
                if result.returncode != 0:
                    print(f'检查all_test文件{cwd}')
                    print(caseset_str)
                    # print(result.stderr.decode())
                result = subprocess.run(
                    ['coverage', 'json', '--pretty-print', '-q', '-o', 'coverage.json'],
                    capture_output=False, cwd=cwd)
                #这时候每个共识集的coverage 文件已经得到了 接下俩就是按每个共识集的json 文件对共识集内部的solutions进行排序 得到solution_id由覆盖率排序的结果
                solution_id_rank_list,consensus_line_cov_percent,consensus_branch_cov_percent=self.getSolutionRankInConsensusByCov(temp_index_to_solution_id_dict,dataFileName=os.path.join(cwd,'coverage.json'),task_id=task_id)
                consensus_dict['solution_id_rank_list'] = solution_id_rank_list
                consensus_dict['consensus_line_cov_percent'] =consensus_line_cov_percent
                consensus_dict['consensus_branch_cov_percent'] = consensus_branch_cov_percent
            #按照json文件total的顺序 对每个共识集进行排序-》决定先不排序 先用字典形式存下来
            dataset_dict['tasks'][task_id] = task_dict
        with open(os.path.join(rootfilepath,"dataset_cov.json"), "w") as json_file:
            json.dump(dataset_dict, json_file,indent=4,separators=(',',': '))

    def getSolutionRankInConsensusByCov(self,temp_index_to_solution_id_dict,dataFileName,task_id):
        # dataFileName = './coverage_test.json'

        # 将 JSON 数据解析为 Python 字典
        # 读取文件并使用 json.load() 转换为字典
        with open(dataFileName, 'r') as f:
            coverage_data = json.load(f)

        # 获取 files 部分
        files = coverage_data['files']
        solution_tuple_list = []  # 放三元组 然后用lambda函数进行排序
        for solution in files.keys():
            solution_result = files[solution]
            solution_index = int(solution.split('_')[-1].split('.')[0])
            # 都自己计算吧 coverage库给出的只保留了一位小数
            solution_line_cov_percent = float(solution_result['summary']['covered_lines']) / int(solution_result['summary']['num_statements']) if int(solution_result['summary']['num_statements'])!=0 else 0
            # 按覆盖的分支数百分比来排序更具有说服力
            solution_branch_cov_percent = float(solution_result['summary']['covered_branches']) / int(solution_result['summary']['num_branches']) if int(solution_result['summary']['num_branches'])!=0 else 0
            solution_tuple_list.append((solution_index, solution_line_cov_percent, solution_branch_cov_percent))

        # 排序
        # cmp参数接受一个比较两个项的函数。如果函数返回True，则第一个参数应该排在第二个参数之前
        def index_tuple_compare(x):
            # 先比较第二项行覆盖率 再比较第三项分支覆盖率 最后比较第一项index自然排序
            return x[1], x[2], -x[0]

        solution_index_rank_list = sorted(solution_tuple_list, key=lambda x: index_tuple_compare(x), reverse=True)
        # print(solution_index_rank_list)
        # 将id转为solution_id
        solution_id_rank_list = []
        for item in solution_index_rank_list:
            solution_id_rank_list.append(temp_index_to_solution_id_dict[item[0]])
        # 读出total
        total_consensus_cov = coverage_data['totals']
        consensus_line_cov_percent = float(total_consensus_cov['percent_covered'])
        def log(consensusName,task_id):
            warnlogger = logging.getLogger("warn_logger")
            datasetPath = os.path.dirname(os.path.dirname(os.path.dirname(dataFileName)))
            FileHandlerPath = os.path.join(datasetPath,'logfile.txt')
            file_handler = logging.FileHandler(FileHandlerPath)
            warnlogger.addHandler(file_handler)
            warnlogger.warning(f"数据集中task：{task_id}的共识集：{consensusName}的total_num_branches为零，请注意")
            return 0
        consensus_branch_cov_percent = float(total_consensus_cov['covered_branches']) / int(total_consensus_cov['num_branches']) if int(total_consensus_cov['num_branches'])!=0 else log(os.path.basename(os.path.dirname(dataFileName)),task_id)
        return solution_id_rank_list,consensus_line_cov_percent,consensus_branch_cov_percent
    def getCasesetContent(self,caseset,entrypoint,solutionNum,solutionPrefix,packageName):
        blank_4 = ' ' * 4
        blank_8 = ' ' * 8
        blank_12 = ' ' * 12
        importPart = f''
        invokePart = f''
        for i in range(solutionNum):
            importStatement = f'from solutions.{solutionPrefix}_{i} import {entrypoint} as solution_{i}\n'
            # importStatement = f'from {packageName}.{solutionPrefix}_{i} import {entrypoint} as solution_{i}\n'
            invokeStatement = f'check(solution_{i})\n'
            importPart += importStatement
            invokePart += invokeStatement
        content =importPart + f'def check(candidate):\n'
        for idx, tc in enumerate(caseset):
            tc = tc.replace(entrypoint,"candidate")
            multi_line_assertion = tc.strip().replace('\n', f'\n{blank_8}')
            content += f'\n{blank_4}try:\n{blank_8}{multi_line_assertion}\
                              \n{blank_4}except Exception as e:\n{blank_8}pass\n'
        content += invokePart
        return content

    def _excludeAllpassTest(self):
        data_dict = {}
        for task_id in self.solution_passed_cases_by_task.keys():
            test_case_counter = Counter()
            for solution in self.solution_passed_cases_by_task[task_id]:
                test_case_counter += Counter(self.solution_passed_cases_by_task[task_id][solution])
            totolSolutionNum = len(self.solution_passed_cases_by_task[task_id])
            allPassTestNum = 0
            for test_case in test_case_counter:
                if(test_case_counter[test_case] == totolSolutionNum):
                    allPassTestNum+=1
                    for solution in self.solution_passed_cases_by_task[task_id]:
                        self.solution_passed_cases_by_task[task_id][solution] = [ test for test in self.solution_passed_cases_by_task[task_id][solution] if test!=test_case]
            data_dict[task_id] = allPassTestNum
            print(f"task{task_id}中排除了{allPassTestNum}个全通过用例")
        # 将字典转换为JSON字符串并写入文件
        with open(os.path.join(self.data_filePath,'AllpassTest.json'), 'w') as file:
            json.dump(data_dict, file)
    #n是随机抽样的大小 0<n<1
    def _get_sample_testcase_solution(self,n=0.7):
        caseset_sample_passed_solutions_by_task = defaultdict(defaultdict)
        solution_sample_passed_solutions_by_task = defaultdict(defaultdict)
        for task_id in self.caseset_passed_solutions_by_task.keys():
            test_cases = self.caseset_passed_solutions_by_task[task_id].keys();
            # 计算需要选择的元素数量
            num_select = int(len(test_cases) * n)
            # 随机选择num_select个元素放入新列表
            selected_cases = random.sample(test_cases, num_select)
            for case in selected_cases:
                caseset_sample_passed_solutions_by_task[task_id][case] = self.caseset_passed_solutions_by_task[task_id][case]
            for solution in self.solution_passed_cases_by_task[task_id]:
                solution_sample_passed_solutions_by_task[task_id][solution] = [ testcase for testcase in self.solution_passed_cases_by_task[task_id][solution] if testcase in selected_cases ]
        return caseset_sample_passed_solutions_by_task,solution_sample_passed_solutions_by_task

    def _get_sampler_caseset_voting_result(self,m,n,k):
        # m表示采样出多少个来投票 n表示每次采样的百分比
        # m个投票器用 列表存储[(caseset_pass,solutions_pass),m对。。。]
        # k表示每次抽样得到的testset solution结果取分数排名前k的共识集
        def get_top_k(sample_list_item,k):
            ranked_solutions_by_task = defaultdict(list)
            sample_solution_passed_case_set,sample_caseset_passed_solution =  sample_list_item
            for task_id in sample_caseset_passed_solution.keys():
                flatted_case_set_passed_solutions = []
                for case_set in sample_caseset_passed_solution[task_id].keys():  # keys是test_case_set 算法就是把能通过的相同的test_case的solution放在一起作为一个共识集
                    solution_set = sample_caseset_passed_solution[task_id][case_set]
                    solution_set_score = math.sqrt(len(solution_set))  # 对于solution集合取sqrt 削弱影响
                    case_set_score = len(case_set)
                    solution_str_set = [self.solution_id_to_string_by_task[task_id][solution] for solution in
                                        solution_set]  # 这里把序号转成字符串 放到solution_str_set列表中
                    flatted_case_set_passed_solutions.append((solution_str_set,
                                                              case_set_score * solution_set_score))  # 结构是  [([],score1),([],score2),([],score3)]
                ranked_solutions_by_task[task_id] = sorted(flatted_case_set_passed_solutions, key=lambda x: x[1],
                                                           reverse=True)[:k]  # 降序排列，分数高的排在前面 key=x[1] 表示按分数case_set_score*solution_set_score来排
            return ranked_solutions_by_task
        for i in range(m):# 对所有测试用例采样m个，采样n次，得到n组排序，取每组前十的solution集合，按solution出现次数排序
            sample_solution_passed_case_set  = self._get_sample_solution_passed_case_set(n)
            self.sample_list.append(sample_solution_passed_case_set,self._get_sample_caseset_passed_solution(sample_solution_passed_case_set))



    
    def _get_solution_passed_case_set(self):#以solution为key value是能通过的testcase 列表 这个task有几个solution对应字典里面就有几个key
        for task_id in self.dual_exec_results_by_task: #这里dual_exec_results_by_task是之前data_manager中计算出的 带重复的id对
            for solution, test_case in self.dual_exec_results_by_task[task_id]: #这里的solution test_case 也都是序号
                if solution in self.solution_passed_cases_by_task[task_id]:
                    self.solution_passed_cases_by_task[task_id][solution].append(test_case)
                else:
                    self.solution_passed_cases_by_task[task_id][solution] = [test_case]
    def _get_sample_solution_passed_case_set(self,n):
        sample_solution_passed_cases_by_task  = defaultdict(defaultdict)
        for task_id in self.dual_exec_results_by_task:
            test_case_id_by_task = set()
            for _, test_case in self.dual_exec_results_by_task[task_id]:
                test_case_id_by_task.add(test_case)
            num_selected = int(n*len(test_case_id_by_task))
            selected_testcase = random.sample(list(test_case_id_by_task),num_selected)
            for solution, test_case in self.solution_passed_cases_by_task[task_id]:
                if solution in sample_solution_passed_cases_by_task[task_id]:
                    sample_solution_passed_cases_by_task[task_id][solution].append(test_case)
                else:
                    sample_solution_passed_cases_by_task[task_id][solution] = [test_case]
        return sample_solution_passed_cases_by_task


    def _get_caseset_passed_solutions(self):#以testcase为key value是能通过的solution列表 这个task有几个testcase对应字典里面有几个key
        for task_id in self.solution_passed_cases_by_task.keys():
            for solution in self.solution_passed_cases_by_task[task_id].keys():
                case_set = tuple(sorted(self.solution_passed_cases_by_task[task_id][solution]))  # case_set: set of (test_case)
                if case_set in self.caseset_passed_solutions_by_task[task_id]:
                    self.caseset_passed_solutions_by_task[task_id][case_set].append(solution)
                else:
                    self.caseset_passed_solutions_by_task[task_id][case_set] = [solution]
    def _get_sample_caseset_passed_solution(self,sample_solution_passed_cases_by_task):
        sample_caseset_passed_solution_by_task= defaultdict(defaultdict)
        for task_id in sample_solution_passed_cases_by_task.keys():
            for solution  in sample_solution_passed_cases_by_task[task_id].keys():
                case_set = tuple(sorted(sample_solution_passed_cases_by_task[task_id][solution]))
                if case_set in sample_caseset_passed_solution_by_task[task_id]:
                    sample_caseset_passed_solution_by_task[task_id][case_set].append(solution)
                else:
                    sample_caseset_passed_solution_by_task[task_id][case_set] = [solution]
        return sample_caseset_passed_solution_by_task
    def _get_caseset_crossScore(self):#通过测试集的跨度来计算分数 最后的分数用len(solutions)*crossScore
        for task_id in self.caseset_passed_solutions_by_task.keys():
            length = len(self.caseset_passed_solutions_by_task[task_id].keys())
            scoreList_by_task = []
            for caseset in self.caseset_passed_solutions_by_task[task_id].keys():
                crossList = Counter()
                for caseset_j in self.caseset_passed_solutions_by_task[task_id].keys():
                    if not set(caseset).isdisjoint(set(caseset_j)):
                        crossList[caseset_j]=1
                self.caseset_crossScore_by_task[task_id][caseset] = len(crossList)/length
                scoreList_by_task.append(len(crossList)/length)
            # print(f'task_id:{task_id},crossScore:{scoreList_by_task}')
    def _get_caseset_crossScore2(self):#通过测试集的跨度来计算分数 最后的分数用len(solutions)*crossScore
        for task_id in self.caseset_passed_solutions_by_task.keys():
            length = len(self.caseset_passed_solutions_by_task[task_id].keys())
            scoreList_by_task = []
            for caseset in self.caseset_passed_solutions_by_task[task_id].keys():
                crossList = Counter()
                for caseset_j in self.caseset_passed_solutions_by_task[task_id].keys():
                    intersection = len(set(caseset).intersection(set(caseset_j)))
                    if intersection>0:
                        crossList[caseset_j]=len(self.caseset_passed_solutions_by_task[task_id][caseset_j])*intersection
                self.caseset_crossScore_by_task[task_id][caseset] = len(list(crossList.elements()))/length
                scoreList_by_task.append(len(crossList)/length)
            # print(f'task_id:{task_id},crossScore:{scoreList_by_task}')
    
    def get_sorted_solutions_without_iter(self):
        logger.info('Start to get sorted solutions without iter')
        # caseset_passed_solutions = {task_id: {case_set: [solution]}}
        ranked_solutions_by_task = defaultdict(list)#最后的目标就是得到solution的排序 应该key是task_id value是对应solution的排序列表
        for task_id in self.caseset_passed_solutions_by_task.keys():
            flatted_case_set_passed_solutions = []
            for case_set in self.caseset_passed_solutions_by_task[task_id].keys():#keys是test_case_set 算法就是把能通过的相同的test_case的solution放在一起作为一个共识集
                solution_set = self.caseset_passed_solutions_by_task[task_id][case_set]
                solution_set_score = math.sqrt(len(solution_set)) #对于solution集合取sqrt 削弱影响
                case_set_score = len(case_set)
                solution_str_set = [self.solution_id_to_string_by_task[task_id][solution] for solution in solution_set] #这里把序号转成字符串 放到solution_str_set列表中
                flatted_case_set_passed_solutions.append((solution_str_set, case_set_score*solution_set_score)) #结构是  [([],score1),([],score2),([],score3)]
            ranked_solutions_by_task[task_id] = sorted(flatted_case_set_passed_solutions, key=lambda x: x[1], reverse=True) #降序排列，分数高的排在前面 key=x[1] 表示按分数case_set_score*solution_set_score来排
        return ranked_solutions_by_task

    def get_cross_sorted_solutions_without_iter(self):
        logger.info('start to get cross sorted solution without iter')
        ranked_solutions_by_task = defaultdict(list)
        for task_id in self.caseset_passed_solutions_by_task.keys():
            flatted_case_set_passed_solutions = []
            for case_set in self.caseset_passed_solutions_by_task[task_id].keys():
                solution_set = self.caseset_passed_solutions_by_task[task_id][case_set]
                solution_set_score = len(solution_set)
                # solution_set_score = math.sqrt(len(solution_set))
                case_set_score = self.caseset_crossScore_by_task[task_id][case_set]
                solution_str_set = [self.solution_id_to_string_by_task[task_id][solution] for solution in solution_set]
                flatted_case_set_passed_solutions.append((solution_str_set,case_set_score))
            ranked_solutions_by_task[task_id] = sorted(flatted_case_set_passed_solutions,key = lambda x:x[1],reverse=True)
        return ranked_solutions_by_task
    def get_cross_sorted_solutions_by_voting_without_iter(self):
        logger.info('start to get cross sorted solution by voting without iter')
        ranked_solutions_by_task = defaultdict(list)
        for task_id in self.caseset_passed_solutions_by_task.keys():
            flatted_case_set_passed_solutions = []
            for case_set in self.caseset_passed_solutions_by_task[task_id].keys():
                solution_set = self.caseset_passed_solutions_by_task[task_id][case_set]
                solution_set_score = len(solution_set)
                # solution_set_score = math.sqrt(len(solution_set))
                case_set_score = self.caseset_crossScore_by_task[task_id][case_set]
                solution_str_set = [self.solution_id_to_string_by_task[task_id][solution] for solution in solution_set]
                flatted_case_set_passed_solutions.append((solution_str_set,case_set_score))
            ranked_solutions_by_task[task_id] = sorted(flatted_case_set_passed_solutions,key = lambda x:x[1],reverse=True)
        return ranked_solutions_by_task

    def get_cov_sorted_solutions_without_iter(self):
        logger.info('start to get sorted solution by coverage without iter')
        ranked_solutions_by_task = defaultdict(dict)
        #先找到 数据集对应的文件地址
        dataset_cov_json = os.path.join(self.dataset_covfile_rootpath,'dataset_cov.json')
        with open(dataset_cov_json,'r') as f:
            dataset_cov_data = json.load(f)
        tasks = dataset_cov_data['tasks']
        for task_id in tasks.keys():
            flatted_case_set_passed_solutions = []
            # print(list(tasks[task_id].values())[0]['consensus_line_cov_percent'])
            consensus_iter = tasks[task_id].values()
            # consensus_iter =
            sorted_consensus_list = sorted(list(consensus_iter), key=lambda x: (x.get('consensus_line_cov_percent',int(0))*len(),x.get('consensus_branch_cov_percent',int(0))), reverse=True)
            for consensus in sorted_consensus_list:
                if 'solution_id_rank_list' in consensus.keys():
                    solution_str_set = [self.solution_id_to_string_by_task[task_id][solution] for solution in consensus['solution_id_rank_list']]
                    # 用两个覆盖率指标相加作为分数， 但其实排序还是优先行覆盖率再分支覆盖率的 不用相加了，用三元组算了
                    flatted_case_set_passed_solutions.append((solution_str_set,consensus['consensus_line_cov_percent'],consensus['consensus_branch_cov_percent']))
            ranked_solutions_by_task[task_id] = flatted_case_set_passed_solutions#不用排序了，已经是排好的了
        return ranked_solutions_by_task