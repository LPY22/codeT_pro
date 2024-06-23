import os
import json
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter


def collect_summaries(root_dir, output_file):
    summaries = []

    # 遍历 HumanEval_0 到 HumanEval_163 文件夹
    for i in range(164):
        human_eval_dir = os.path.join(root_dir, f'HumanEval_{i}')
        print(human_eval_dir)
        if os.path.isdir(human_eval_dir):
            # 遍历 consensus_i 文件夹
            for consensus_dir in os.listdir(human_eval_dir):
                consensus_path = os.path.join(human_eval_dir, consensus_dir)
                # print(consensus_path)
                if os.path.isdir(consensus_path):
                    # 查找 coverage.json 文件
                    coverage_file = os.path.join(consensus_path, 'coverage.json')
                    if os.path.isfile(coverage_file):
                        try:
                            # 读取 coverage.json 文件
                            with open(coverage_file, 'r') as f:
                                data = json.load(f)
                                # print(data)
                                # 收集 files 属性中的 summary 属性
                                solutions = data['files']
                                for file_entry in solutions:
                                    # print(file_entry)
                                    # print('summary' in file_entry)
                                    # if 'summary' in file_entry:
                                    #     print(file_entry['summary'])
                                    summaries.append(solutions[file_entry]['summary'])
                        except Exception as e:
                            print(f"Error reading {coverage_file}: {e}")

    # 将 summaries 列表写入输出文件
    with open(output_file, 'w') as f:
        json.dump(summaries, f, indent=4)


def read_summaries(input_file):
    percent_covered_list = []

    # 读取 summaries.json 文件
    try:
        with open(input_file, 'r') as f:
            summaries = json.load(f)

            # 提取每项中的 percent_covered 属性
            for summary in summaries:
                if 'percent_covered' in summary:
                    percent_covered_list.append(summary['percent_covered'])
                else:
                    print(f"Warning: 'percent_covered' not found in summary: {summary}")
    except Exception as e:
        print(f"Error reading {input_file}: {e}")

    return percent_covered_list


def remove_values_from_list(input_list, value, count):
    # 使用列表推导式和条件语句删除指定数量的值
    output_list = []
    value_removed_count = 0

    for item in input_list:
        if item == value and value_removed_count < count:
            value_removed_count += 1
        else:
            output_list.append(item)

    return output_list
if __name__ == "__main__":
    # filepath = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # dataPath = os.path.join(os.path.join(filepath,'data'),'HumanEval_davinci002_temp0.8_topp0.95_num100_max300_Consensus')
    # root_dir = dataPath  # 替换为 HumanEval 文件夹的实际路径
    # # print(root_dir)
    # output_file = 'summaries.json'
    # collect_summaries(root_dir, output_file)
    # print(f"Summaries have been written to {output_file}")

    fileName = 'summaries.json'
    coverage_list = read_summaries(fileName)

    # 输出 percent_covered_list 或进行进一步处理
    print(f"Percent Covered List: {coverage_list}")
    coverage_list=remove_values_from_list(coverage_list,100.0,6000)
    # plt.figure(figsize=(10, 6))
    #
    # # 绘制直方图
    # plt.hist(coverage_list, bins=20, edgecolor='black', alpha=0.7)
    #
    # # 设置标题和标签
    # plt.title('Coverage Distribution')
    # plt.xlabel('Coverage Percentage')
    # plt.ylabel('Frequency')
    #
    # # 显示网格
    # plt.grid(True)
    #
    # # 显示图表
    # plt.show()
    plt.figure(figsize=(10, 6))

    # # 绘制概率密度直方图
    # counts, bins, patches = plt.hist(coverage_list, bins=20, edgecolor='black', alpha=0.7, density=True)
    #
    # # 将频率转换为百分比
    # counts = counts * np.diff(bins)
    #
    # # 设置标题和标签
    # # plt.title('Coverage Distribution')
    # plt.xlabel('code solutions line coverage',fontsize=14)
    # plt.ylabel('Percentage',fontsize = 14)
    #
    # # 设置纵坐标为百分比格式
    # plt.gca().yaxis.set_major_formatter(PercentFormatter(xmax=1))
    #
    # # 显示网格
    # plt.grid(True)
    #
    # # 显示图表
    # plt.savefig("solutions_cov.pdf",format='pdf')
    # plt.show()
    # 定义区间的边界
    bins = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95 ,100]

    plt.figure(figsize=(10, 6))

    counts, _ = np.histogram(coverage_list, bins=bins)

    # 计算总数并将计数转换为百分比
    total_counts = sum(counts)
    counts_percentage = (counts / total_counts) * 100

    # 设置条形宽度和间隔
    bar_width = 4.7
    bin_centers =[ (item1+item2)/2 for item1,item2 in zip(bins[:-1],bins[1:])]
    print(bin_centers)

    plt.figure(figsize=(10, 6))

    # 绘制条形图
    bars = plt.bar(bin_centers, counts_percentage, width=bar_width, edgecolor='black', alpha=0.7)

    # 设置标题和标签
    plt.xlabel('Code Solutions Line Coverage', fontsize=14)
    plt.ylabel('Percentage', fontsize=14)

    # 设置纵坐标为百分比格式
    plt.gca().yaxis.set_major_formatter(PercentFormatter())

    # 设置横坐标刻度
    plt.xticks(bins)

    # 在每个条形上方显示数值
    for bar, count in zip(bars, counts_percentage):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width() / 2., height, f'{count:.1f}%', ha='center', va='bottom', fontsize=10)

    # 显示网格
    plt.grid(True)
    plt.savefig('solution_cov.pdf',format='pdf')
    # 显示图表
    plt.show()