# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from collections import defaultdict, Counter
import logging
import math
import src.optimize


logging.basicConfig(
    format="SystemLog: [%(asctime)s][%(name)s][%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# data_manager = DataManager(dual_exec_result, handled_solutions, handled_test_cases,args.test_case_limit)  # 传入了testcase的运行结果，solution和testcase的字典列表，还有限制


class DataManager:
    def __init__(self, dual_exec_results, sampled_code_by_task, sampled_test_case_by_task, limit):
        logger.info('handling dual exec results')
        self.dual_exec_results = dual_exec_results
        self.sampled_code_by_task = sampled_code_by_task
        self.sampled_test_case_by_task = sampled_test_case_by_task
        self.limit = limit
        
        self.solution_frequency_by_task = defaultdict(Counter)# 默认value类型是Counter #每个task的回答数
        self.test_case_frequency_by_task = dict()  #每个task的test case数
        self.passed_unique_solutions_by_task = defaultdict(set) #每个task运行成功的solution
        self.passed_unique_test_cases_by_task = defaultdict(set) #每个task运行成功的test_cases
        self.passed_solution_test_case_pairs_by_task = defaultdict(set) #每个task运行成功的的solution test_case对
        self.solution_string_to_id_range_by_task = dict() #每个任务给solution 排序 string : id id应该是序号
        self.test_case_string_to_id_range_by_task = dict() #每个任务给test_case排序 string : id id应该是序号
        self.solution_id_to_string_by_task = dict() # 相反的用id 取 solution代码字符串的字典
        self.test_case_id_to_string_by_task = dict() # 同上
        
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
        self.dual_exec_results_by_task = data_manager.expanded_passed_solution_test_case_pairs_by_task #dual_exec_results_by_task 可重复的id对
        self.solution_id_to_string_by_task = data_manager.solution_id_to_string_by_task
        
        self.solution_passed_cases_by_task = defaultdict(defaultdict)#两层的嵌套字典
        self.caseset_passed_solutions_by_task = defaultdict(defaultdict)

        self.caseset_crossScore_by_task = defaultdict(defaultdict)
        
        self._get_solution_passed_case_set()
        logger.info('got solution passed case sets')




        logger.info('排除全通过测试中...')
        # self._excludeAllpassTest()
        src.optimize.excludeAllpassTest(self)
        logger.info('excluded allPass testcase...')


        self._get_caseset_passed_solutions()
        logger.info('got case set passed solutions')
        #除去每个task中那些通过了所有solution的testcase

        self._get_caseset_crossScore2()
        logger.info('计算测试集cross分数2')


    def _excludeAllpassTest(self):
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
            print(f"task{task_id}中排除了{allPassTestNum}个全通过用例")


    
    def _get_solution_passed_case_set(self):#以solution为key value是能通过的testcase 列表 这个task有几个solution对应字典里面就有几个key
        for task_id in self.dual_exec_results_by_task: #这里dual_exec_results_by_task是之前data_manager中计算出的 带重复的id对
            for solution, test_case in self.dual_exec_results_by_task[task_id]: #这里的solution test_case 也都是序号
                if solution in self.solution_passed_cases_by_task[task_id]:
                    self.solution_passed_cases_by_task[task_id][solution].append(test_case)
                else:
                    self.solution_passed_cases_by_task[task_id][solution] = [test_case]

    def _get_caseset_passed_solutions(self):#以testcase为key value是能通过的solution列表 这个task有几个testcase对应字典里面有几个key
        for task_id in self.solution_passed_cases_by_task.keys():
            for solution in self.solution_passed_cases_by_task[task_id].keys():
                case_set = tuple(sorted(self.solution_passed_cases_by_task[task_id][solution]))  # case_set: set of (test_case)
                if case_set in self.caseset_passed_solutions_by_task[task_id]:
                    self.caseset_passed_solutions_by_task[task_id][case_set].append(solution)
                else:
                    self.caseset_passed_solutions_by_task[task_id][case_set] = [solution]

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
