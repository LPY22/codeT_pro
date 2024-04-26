from collections import Counter

#排除全通过测试样例
def excludeAllpassTest(self):
    for task_id in self.solution_passed_cases_by_task.keys():
        test_case_counter = Counter()
        for solution in self.solution_passed_cases_by_task[task_id]:
            test_case_counter += Counter(self.solution_passed_cases_by_task[task_id][solution])
        totolSolutionNum = len(self.solution_passed_cases_by_task[task_id])
        allPassTestNum = 0
        for test_case in test_case_counter:
            if (test_case_counter[test_case] == totolSolutionNum):
                allPassTestNum += 1
                for solution in self.solution_passed_cases_by_task[task_id]:
                    self.solution_passed_cases_by_task[task_id][solution] = [test for test in
                                                                             self.solution_passed_cases_by_task[
                                                                                 task_id][solution] if
                                                                             test != test_case]
        print(f"task{task_id}中排除了{allPassTestNum}个全通过用例")
#选横跨度最大的共识集
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
#todo:集成学习 采样投票器
# 对所有测试用例采样m个，采样n次，得到n组排序，取每组前十的solution集合，按solution出现次数排序

#todo：直接对每个共识集执行算覆盖率来选

#todo: 通过静态代码分析工具试试（其他论文的