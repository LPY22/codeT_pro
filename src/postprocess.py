# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

from collections import defaultdict

from src.io_utils import Tools

STOP_TOKEN = ['\nclass', '\ndef', '\n#', '\nif', '\nprint']

class PostProcessor:
    @staticmethod
    def map_task_id_for_solution(predict_path, source_path,sample_section):#source代表原始的文件 就是只有prompt那些 predict表示有采样的samples
        database = dict()
        left = sample_section[0]
        right = sample_section[1] if sample_section[1]!=-1 else 65535
        sample = right or left
        raw_problems = Tools.load_tasks(source_path)#按行加载原始文件（一行是一个问题），从json变成字典，key是task_id
        for task_id in raw_problems.keys():
            # print(task_id)
            # print(type(task_id))
            database[raw_problems[task_id]['prompt']] = raw_problems[task_id] #database 放prompt,source_solution键值对，用于之后对齐predict

        result = []
        predictions = Tools.load_jsonl(predict_path)#加载预测文件（带模型采样输出）预测文件每一行只有prompt和samples两个属性，prompt是字符串类型，samples是列表
        for pre in predictions:
            task = database[pre['prompt']]#先找到prompt属性对齐
            #todo 对于MBPP数据集抽样了 if int(task['task_id'].split('/')[-1])<600: continue
            # number = int(task['task_id'].split('/')[-1])
            # if number<left or number>right: continue
            if not pre['samples']:
                result.append({
                    'task_id': task['task_id'],
                    'prompt': pre['prompt'],
                    'test': task['test'],
                    'entry_point': task['entry_point'],
                    'completion': 'empty solution here, execution will fail'
                })
            for sample in pre['samples']:#每个问题的采样都放在了一个列表里面，以字典的格式，只有"completion"属性是不同的
                processed_code = PostProcessor.solution_extract(sample) #用停词得到每个采样的结果
                result.append({
                    'task_id': task['task_id'],
                    'prompt': pre['prompt'],
                    'test': task['test'],
                    'entry_point': task['entry_point'],
                    'completion': processed_code
                })#没有像predict一样把相同问题的solution放在一个列表里，而是每个都单开了一个字典,这里不是很理解，因为只有completion代码完成这个属性是不同的
        return result, len(raw_problems)

    @staticmethod
    def map_task_id_for_test_case(predict_path, source_path,sample_section):
        database = dict()
        left = sample_section[0]
        right = sample_section[1] if sample_section[1]!=-1 else 65535
        raw_problems = Tools.load_tasks(source_path)
        for task_id in raw_problems.keys():
            database[raw_problems[task_id]['prompt']] = raw_problems[task_id]

        test_cases_by_task = defaultdict(list) #构建默认value是空列表[]的字典，方便之后归类字典中相同key,不同value的元素到一个字典当中。
        predictions = Tools.load_jsonl(predict_path)
        for pre in predictions:
            task = database[pre['prompt']]#这里因为测试用例生成不是最终目标，最终目标是solution的相关指标。所以这里没有对test_predict的samples判空
            #todo 对于MBPP抽样了 davinci if int(task['task_id'].split('/')[-1])<600: continue
            # number = int(task['task_id'].split('/')[-1])
            # if number<left or number>right: continue
            for sample in pre['samples']:
                test_cases = PostProcessor.test_case_extract(sample, task['entry_point'])#停词抽取
                test_cases_by_task[task['task_id']].append(test_cases)#而且这里没有用list,而是用字典归类了，用【】列表来存储同一个问题的test
        return test_cases_by_task

    @staticmethod
    def solution_extract(content):#根据停用词抽取回答
        for identifier in STOP_TOKEN:
            if identifier in content:
                content = content.split(identifier)[0]
        return content
    
    @staticmethod
    def test_case_extract(content, entry_point):
        def _truncate(content):#截断
            for identifier in STOP_TOKEN:
                if identifier in content:
                    content = content.split(identifier)[0]
            return content.strip()
        #f'assert {content} 因为prompt的结尾是assert 所以这里split之前先不一个  entry_point是函数名
        split_by_assert = [f'assert {part}'.strip() for part in f'assert {content}'.split('assert ') if (entry_point.strip() in part) and len(part.strip()) > 0]
        truncated_test_cases = [_truncate(i) for i in split_by_assert]#对所有断言做停词截断
        checked_assertions = [i for i in truncated_test_cases if PostProcessor._check_test_case_validation(i)]#过滤所有的断言
        return checked_assertions

    @staticmethod
    def _check_test_case_validation(test_case):#检查测试用例可靠性（过滤函数）
        if len(test_case.strip()) < 1:
            return False
        if 'assert' not in test_case:
            return False
        try:
            multi_line_test_case = test_case.replace("\n", "\n    ")#try后面代码应该带缩进，把换行替换成带缩进的换行
            assert_in_a_block = f'try:\n    {multi_line_test_case}\nexcept:\n    pass\n'
            compile(assert_in_a_block, '', 'exec')#assert_in_a_block 包含python代码的字符串 第二个参数是文件名，一般用‘’  第三个exec表示编译成可执行文件 compileCode = compile(... , 'exec')之后可以接exec(compileCode)
            return True
        except Exception:
            return False