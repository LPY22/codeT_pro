import os.path
import subprocess

# 指定工作目录并执行命令
filepath = os.path.abspath(__file__)
projectpath = os.path.dirname(os.path.dirname(filepath))
testpath = 'data/HumanEval_davinci002_temp0.8_topp0.95_num100_max300_Consensus/HumanEval_0/consensus_0'
cwd = os.path.join(projectpath,testpath)
print(cwd)
result = subprocess.run(['coverage','run','--branch','--source=solutions','all_test.py'], capture_output=False, cwd=cwd)
result = subprocess.run(['coverage','json','--pretty-print','-q','-o','../../../../src/coverage_test.json'], capture_output=False, cwd=cwd)
# 打印命令输出
# print(result.stdout)