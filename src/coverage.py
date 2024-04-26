#测算每个共识集的覆盖率，并按照覆盖率高低对共识集排序 对里面的solution也要按每个回答的覆盖率排序 得到的结果用一种文件存起来，之后可以用来读取
import coverage

cov = coverage.cov()


class CoverageRank:  # set_consistency = DualAgreement(data_manager)
    def __init__(self, dual_agreement):
        self.dual_agreement = dual_agreement
        self.dual_exec_results_by_task = dual_agreement.expanded_passed_solution_test_case_pairs_by_task  # dual_exec_results_by_task 可重复的id对
        self.solution_id_to_string_by_task = dual_agreement.solution_id_to_string_by_task
        self.test_case_id_to_string_by_task = dual_agreement.test_case_id_to_string_by_task
        self.task_id_to_entrypoint_prompt = dual_agreement.task_id_to_entrypoint_prompt

        self.solution_passed_cases_by_task = dual_agreement.solution_passed_cases_by_task  # 两层的嵌套字典
        self.caseset_passed_solutions_by_task = dual_agreement.caseset_passed_solution_by_task

        self.caseset_crossScore_by_task = dual_agreement.caseset_crossScore_by_task
        self.sample_list = []  # 采样器列表， 里面每一项都是caseset_passed_solutins_by_task

        self._get_solution_passed_case_set()
    # def _get_consensus_rank(self):
