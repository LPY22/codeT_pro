source_solution_path = {"HumanEval": "./data/dataset/HumanEval_for_code_generation.jsonl",
                        "MBPP": "./data/dataset/mbpp_sanitized_for_code_generation.jsonl",
                        "APPS": "./data/dataset/APPS_zeroshot_for_code_generation.jsonl",
                        "CodeContests": "./data/dataset/CodeContests_zeroshot_for_code_generation.jsonl"}
source_test_path = {"HumanEval": "./data/dataset/HumanEval_for_test_case_generation.jsonl",
                    "MBPP": "./data/dataset/mbpp_sanitized_for_test_case_generation.jsonl",
                    "APPS": "./data/dataset/APPS_zeroshot_for_test_case_generation.jsonl",
                    "CodeContests": "./data/dataset/CodeContests_zeroshot_for_test_case_generation.jsonl"}

# predict_solution_path={}
# predict_test_path={}
# datasetName = "HumanEval"
datasetName = "MBPP"
modelParamsName = "davinci002_temp0.8_topp0.95_num100_max300"
# modelParamsName = "incoder6B_temp0.8_topp0.95_num100_max300"
# modelParamsName = "codegen16B_temp0.8_topp0.95_num100_max300"
# modelParamsName = "MBPP_davinci002_temp0.8_topp0.95_num100_max300_code_solution.jsonl"
# logger.info(datasetName+"\t"+modelParamsName)