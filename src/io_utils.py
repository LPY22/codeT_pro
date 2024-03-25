# Copyright (c) Microsoft Corporation.
# Licensed under the MIT license.

import json
import pickle

class Tools:
    @staticmethod
    def load_jsonl(file_path):#把jsonl文件（每一行是一个json对象）读成字典列表
        json_objects = []
        with open(file_path, 'r', encoding='utf8') as f:
            for line in f:
                json_objects.append(json.loads(line.strip()))
        return json_objects
    
    @staticmethod
    def load_tasks(task_path):
        result = dict()
        lines = Tools.load_jsonl(task_path)#lines是字典列表，带task_id说明是source文件才调用load_tasks
        for line in lines:
            result[line['task_id']] = line #再套一层map key是对应数据集的task_id
        return result
    
    @staticmethod
    def dump_pickle(path, content):#pickle用于python对象的序列化和反序列化（用于配置文，模型文件，数据集文件的保存和读取），dump是序列化成二进制写入（‘wb’)
        with open(path, 'wb') as f:
            pickle.dump(content, f)
    
    @staticmethod
    def load_pickle(path):#load是加载二进制
        with open(path, 'rb') as f:
            return pickle.load(f)
        
    @staticmethod
    def write_file(path, content):#把content写到path文件里面
        with open(path, 'w', encoding='utf8') as f:
            f.write(content)