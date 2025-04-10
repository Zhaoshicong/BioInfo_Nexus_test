# Bio_tools/codon_analyzer.py
# -*- coding: utf-8 -*-
"""
密码子分析工具模块
提供一个主函数 analyze_sequence_codons 来执行完整的密码子优化分析。
依赖于预先下载到 data/codon_tables/ 目录下的密码子频率 JSON 文件。
"""

import os
import json
import re
from math import log, exp
from Bio.Data import CodonTable # 需要 biopython
import glob # Needed for file searching, although os.listdir is also fine

# --- 内部辅助函数 ---

def _load_host_frequencies(host_id, genetic_code_id, data_dir):
    """
    从本地JSON文件加载指定宿主的密码子频率。
    优先查找精确的 [ID].json，如果找不到，则查找 [ID].*.json。
    """
    # 1. 尝试精确匹配: [ID].json
    numeric_filename = f"{host_id}.json"
    numeric_filepath = os.path.join(data_dir, numeric_filename)

    if os.path.exists(numeric_filepath):
        # print(f"找到精确匹配文件: {numeric_filename}") # 调试信息
        filepath_to_load = numeric_filepath
        filename_loaded = numeric_filename
    else:
        # 2. 精确匹配未找到，尝试查找替代文件: [ID].*.json
        print(f"警告: 未找到精确文件 {numeric_filename}，尝试查找替代文件如 {host_id}.*.json ...")
        filepath_to_load = None
        filename_loaded = None
        try:
            # 查找所有以 "[ID]." 开头并以 ".json" 结尾的文件
            pattern = f"{host_id}.*.json"
            # 使用 os.listdir 和 startswith/endswith
            found_alternatives = []
            for f in os.listdir(data_dir):
                if f.startswith(f"{host_id}.") and f.endswith(".json"):
                     found_alternatives.append(f)

            # # 或者使用 glob (更简洁)
            # search_pattern = os.path.join(data_dir, f"{host_id}.*.json")
            # found_alternatives = [os.path.basename(p) for p in glob.glob(search_pattern)]

            if found_alternatives:
                # 找到了一个或多个替代文件，选择第一个
                filename_loaded = found_alternatives[0]
                filepath_to_load = os.path.join(data_dir, filename_loaded)
                print(f"找到并使用替代文件: {filename_loaded}")
            else:
                # 替代文件也未找到
                 print(f"错误: 在目录 {data_dir} 中也未找到任何以 {host_id}. 开头的 .json 文件。")
                 return None # 明确返回 None

        except OSError as e:
             print(f"错误: 搜索替代文件时访问目录 {data_dir} 出错: {e}")
             return None # 目录访问错误

    # 3. 如果找到了要加载的文件 (精确或替代)
    if filepath_to_load:
        try:
            with open(filepath_to_load, 'r', encoding='utf-8') as f:
                frequencies = json.load(f)
            # 基本验证
            if isinstance(frequencies, dict) and frequencies:
                _ensure_all_codons_have_values(frequencies, genetic_code_id)
                return frequencies
            else:
                print(f"错误: 文件 {filename_loaded} 格式无效或为空。")
                return None
        except (json.JSONDecodeError, IOError, TypeError) as e:
            print(f"错误: 读取文件 {filename_loaded} 失败: {e}")
            return None
    else:
         # 这部分理论上不应该执行到，因为上面已经处理了找不到文件的情况
         print(f"错误: 未能确定要为宿主 {host_id} 加载的文件。")
         return None

def _ensure_all_codons_have_values(frequencies, genetic_code_id):
    """(内部辅助) 确保频率字典包含所有相关密码子"""
    if not frequencies: return
    try:
        codon_table = CodonTable.unambiguous_rna_by_id[genetic_code_id]
    except KeyError:
        genetic_code_id = 1 # Fallback to standard
        codon_table = CodonTable.unambiguous_rna_by_id[genetic_code_id]

    all_codons = set(codon_table.forward_table.keys()) | set(codon_table.stop_codons)
    for codon in all_codons:
        if codon not in frequencies:
            frequencies[codon] = 0.0

def _calculate_rscu(sequence, genetic_code_id=1):
    """(内部辅助) 计算RSCU"""
    sequence = sequence.upper().replace('T', 'U')
    codon_counts = {}
    total_codons = 0
    for i in range(0, len(sequence) - (len(sequence) % 3), 3):
        codon = sequence[i:i+3]
        if len(codon) == 3:
            codon_counts[codon] = codon_counts.get(codon, 0) + 1
            total_codons += 1
    if total_codons == 0: return {}
    try:
        codon_table = CodonTable.unambiguous_rna_by_id[genetic_code_id]
    except KeyError:
        genetic_code_id = 1
        codon_table = CodonTable.unambiguous_rna_by_id[genetic_code_id]

    synonymous_codons = {}
    for codon, aa in codon_table.forward_table.items():
        if aa not in synonymous_codons: synonymous_codons[aa] = []
        synonymous_codons[aa].append(codon)
    if '*' not in synonymous_codons: synonymous_codons['*'] = []
    for stop_codon in codon_table.stop_codons:
         if stop_codon not in synonymous_codons['*']: synonymous_codons['*'].append(stop_codon)

    rscu_values = {}
    for aa, codons in synonymous_codons.items():
        if not codons: continue
        total_syn_codon_count = sum(codon_counts.get(c, 0) for c in codons)
        num_syn_codons = len(codons)
        if total_syn_codon_count == 0:
            for codon in codons: rscu_values[codon] = 0.0
            continue
        if num_syn_codons == 1:
            codon = codons[0]
            rscu_values[codon] = 1.0 if codon_counts.get(codon, 0) > 0 else 0.0
        else:
            expected_count = total_syn_codon_count / num_syn_codons
            for codon in codons:
                observed_count = codon_counts.get(codon, 0)
                if expected_count > 0: rscu_values[codon] = observed_count / expected_count
                else: rscu_values[codon] = 0.0

    all_codons_in_table = set(codon_table.forward_table.keys()) | set(codon_table.stop_codons)
    for c in all_codons_in_table:
        if c not in rscu_values: rscu_values[c] = 0.0
    return rscu_values

def _identify_rare_codons(sequence, host_codon_frequencies, threshold=0.05, genetic_code_id=1):
    """(内部辅助) 识别稀有密码子"""
    sequence = sequence.upper().replace('T', 'U')
    rare_codons_found = []
    position = 0
    try:
        codon_table = CodonTable.unambiguous_rna_by_id[genetic_code_id]
    except KeyError:
        codon_table = CodonTable.standard_rna_table

    for i in range(0, len(sequence) - (len(sequence) % 3), 3):
        codon = sequence[i:i+3]
        if len(codon) == 3 and codon in codon_table.forward_table:
            host_freq = host_codon_frequencies.get(codon, 0)
            if 0 < host_freq < threshold:
                 rare_codons_found.append((codon, position, host_freq))
        position += 1
    return rare_codons_found

def _generate_standard_w_values(frequencies, genetic_code_id=1):
    """(内部辅助) 从频率计算CAI w值"""
    if not frequencies: return {}
    try:
        codon_table = CodonTable.unambiguous_rna_by_id[genetic_code_id]
    except KeyError:
        genetic_code_id = 1
        codon_table = CodonTable.unambiguous_rna_by_id[genetic_code_id]

    aa_to_codons = {}
    for codon, aa in codon_table.forward_table.items():
        if aa not in aa_to_codons: aa_to_codons[aa] = []
        aa_to_codons[aa].append(codon)

    aa_max_freq = {}
    for aa, codons in aa_to_codons.items():
        syn_freqs = [frequencies.get(codon, 0.0) for codon in codons]
        if syn_freqs:
             max_freq = max(syn_freqs)
             if max_freq > 0: aa_max_freq[aa] = max_freq

    w_values = {}
    all_codons_in_table = set(codon_table.forward_table.keys()) | set(codon_table.stop_codons)
    for codon in all_codons_in_table:
        if codon in codon_table.stop_codons:
             w_values[codon] = 0.0
             continue
        aa = codon_table.forward_table.get(codon)
        if not aa:
             w_values[codon] = 0.0
             continue
        if aa == 'M' or aa == 'W':
            w_values[codon] = 1.0
            continue
        freq = frequencies.get(codon, 0.0)
        if aa in aa_max_freq:
            max_f = aa_max_freq[aa]
            if max_f > 0: w_values[codon] = freq / max_f
            else: w_values[codon] = 0.0
        else: w_values[codon] = 0.0

    # 再次确保所有密码子都有值
    for c in all_codons_in_table:
        if c not in w_values: w_values[c] = 0.0
    return w_values

# 内置CAI计算函数，替代使用CodonUsage模块
def _calculate_cai(sequence, w_values):
    """计算密码子适应性指数(CAI)"""
    sequence = sequence.upper().replace('T', 'U')
    length = len(sequence)
    sequence = sequence[:length - (length % 3)]
    if not sequence: return 0.0
    
    log_sum = 0.0
    valid_codon_count = 0
    standard_table = CodonTable.standard_rna_table
    
    for i in range(0, len(sequence), 3):
        codon = sequence[i:i+3]
        if len(codon) == 3:
            if codon in w_values:
                aa = standard_table.forward_table.get(codon)
                if aa and aa != 'M' and aa != 'W':
                    w = w_values.get(codon)
                    if w is not None and w > 0:
                        log_sum += log(w)
                        valid_codon_count += 1
    
    if valid_codon_count == 0: return 0.0
    cai_value = exp(log_sum / valid_codon_count)
    return cai_value

# --- 主分析函数 ---
def analyze_sequence_codons(sequence, host_id, genetic_code_id=1, rarity_threshold=0.05):
    """
    对给定序列进行密码子优化分析。

    Args:
        sequence (str): 要分析的 DNA 或 RNA 序列。
        host_id (str): 宿主物种的 ID。
        genetic_code_id (int, optional): 使用的遗传密码表 ID. Defaults to 1 (标准密码表).
        rarity_threshold (float, optional): 定义稀有密码子的频率阈值. Defaults to 0.05.

    Returns:
        dict: 包含分析结果的字典。
              如果发生错误（如找不到数据文件），则返回包含 'status': 'error' 的字典。
    """
    # 确定数据目录的路径 (相对于当前脚本文件)
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        script_dir = os.getcwd() # Fallback for interactive use
    data_dir = os.path.join(script_dir, "data", "codon_tables")

    # 1. 加载宿主频率数据
    #print(f"分析器: 正在加载宿主 {host_id} (Code: {genetic_code_id}) 的频率数据...")
    host_freqs = _load_host_frequencies(host_id, genetic_code_id, data_dir)
    if not host_freqs:
        return {
            "status": "error",
            "message": f"数据库里没有找到宿主 {host_id} 的密码子频率数据。"
        }
    #print("分析器: 宿主频率数据加载成功。")

    # 2. 计算 RSCU
    #print("分析器: 正在计算 RSCU...")
    seq_rscu = _calculate_rscu(sequence, genetic_code_id)
    # 过滤掉值为0的密码子，使结果更简洁
    filtered_rscu = {k: round(v, 3) for k, v in seq_rscu.items() if v > 0}
    #print("分析器: RSCU 计算完成。")

    # 3. 计算 CAI
    #print("分析器: 正在生成 CAI w 值...")
    host_w_values = _generate_standard_w_values(host_freqs, genetic_code_id)
    cai_value_result = "计算失败" # 默认值
    if host_w_values:
        #print("分析器: 正在计算 CAI...")
        try:
             cai_value = _calculate_cai(sequence, host_w_values)
             cai_value_result = round(cai_value, 3)
             #print(f"分析器: CAI 计算完成 ({cai_value_result})。")
        except ValueError as e:
             #print(f"分析器错误: CAI 计算失败 - {e}")
             cai_value_result = f"Error: {e}"
        except Exception as e:
             print(f"分析器错误: CAI 计算时发生未知错误 - {e}")
             cai_value_result = f"Error: {e}"
    else:
         print("分析器错误: 无法生成 CAI w 值。")

    # 4. 识别稀有密码子
    #print("分析器: 正在识别稀有密码子...")
    rare_codons = _identify_rare_codons(sequence, host_freqs, threshold=rarity_threshold, genetic_code_id=genetic_code_id)
    rare_codons_list = [
        {"codon": c, "position_1_based": p + 1, "host_frequency": round(f, 4)}
        for c, p, f in rare_codons
    ]
    #print(f"分析器: 找到 {len(rare_codons_list)} 个稀有密码子。")

    # 5. 组装结果
    #print("分析器: 正在组装结果...")
    # 直接使用物种ID作为名称
    species_name = f"物种ID: {host_id}"
    
    analysis_result = {
        "status": "success",
        "input_sequence_preview": sequence[:60] + ("..." if len(sequence) > 60 else ""),
        "host_id": host_id,
        "host_name": species_name,
        "genetic_code_id": genetic_code_id,
        "analysis": {
            "rscu_values": filtered_rscu,
            "cai_value": cai_value_result,
            "rare_codon_threshold": rarity_threshold,
            "rare_codons_found": rare_codons_list
        },
         "summary": {
            "optimization_potential": "高" if rare_codons_list else "低"
        }
    }
    #print("分析器: 分析完成。")
    return analysis_result

# --- 简单的测试代码 ---
if __name__ == "__main__":
    print("*"*10 + " 测试 codon_analyzer.py " + "*"*10)
    # 测试序列
    test_sequence = "ATGGCTAGCGTGTACGGTCGTGAGAAAATCGGTTACGAGCGTAAATTCAACCTTGGTATCGGTGAGGCTACTATCTCTGGTGGTGAAGGTTACGGTGCTTAA" # 加了终止密码子
    test_host = "83333" # E. coli K12 ID
    test_code = 1      # 标准遗传密码表

    print(f"\n测试序列: {test_sequence}")
    print(f"测试宿主 ID: {test_host}, 遗传密码: {test_code}")

    results = analyze_sequence_codons(test_sequence, test_host, test_code)

    print("\n--- 分析结果 (JSON) ---")
    # 使用 try-except 块处理可能的 JSON 序列化错误
    try:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    except TypeError as e:
        print(f"无法序列化结果为 JSON: {e}")
        print("原始结果字典:", results)

    # 测试找不到文件的情况
    print("\n--- 测试找不到数据文件 ---")
    results_not_found = analyze_sequence_codons(test_sequence, "00000", 1) # 一个不存在的ID
    print(json.dumps(results_not_found, indent=2, ensure_ascii=False))
