from Bio.Seq import Seq
from Bio import Restriction
from Bio.Restriction import RestrictionBatch
import logging
import sys
import re
from difflib import get_close_matches

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_valid_dna(sequence):
    """检查序列是否为有效的DNA序列 (允许N)"""
    valid_bases = set("ATCGN")
    return all(base.upper() in valid_bases for base in sequence)

def find_matching_enzymes(query, all_enzymes, max_matches=5, fuzzy_match=True):
    """
    查找与查询字符串匹配的限制性内切酶名称。
    
    参数:
        query (str): 用户输入的酶名查询
        all_enzymes (list): 所有可用酶名列表
        max_matches (int): 返回的最大匹配数量
        fuzzy_match (bool): 是否进行模糊匹配
        
    返回:
        tuple: (精确匹配列表, 模糊匹配列表)
    """
    # 移除特殊字符并标准化查询
    clean_query = query.strip()
    
    # 检查是否是精确匹配
    exact_matches = []
    if clean_query in all_enzymes:
        exact_matches.append(clean_query)
        return exact_matches, []
    
    # 大小写不敏感的精确匹配检查
    for enzyme in all_enzymes:
        if enzyme.lower() == clean_query.lower():
            exact_matches.append(enzyme)
            return exact_matches, []
    
    # 若无精确匹配且允许模糊匹配，进行模糊匹配
    fuzzy_matches = []
    if fuzzy_match:
        # 1. 以查询开头的匹配（如 "Eco" 匹配 "EcoRI", "EcoRV" 等）
        prefix_matches = [e for e in all_enzymes if e.lower().startswith(clean_query.lower())]
        
        # 2. 包含查询的匹配（如 "III" 匹配 "BamHI", "EcoRIII" 等）
        contains_matches = [e for e in all_enzymes if clean_query.lower() in e.lower() 
                           and e not in prefix_matches]
        
        # 3. 使用difflib进行相似度匹配
        similar_matches = get_close_matches(clean_query, all_enzymes, n=max_matches, cutoff=0.6)
        similar_matches = [m for m in similar_matches if m not in prefix_matches and m not in contains_matches]
        
        # 组合所有匹配结果，优先级: 前缀匹配 > 包含匹配 > 相似度匹配
        fuzzy_matches = prefix_matches + contains_matches + similar_matches
        
        # 限制返回数量
        fuzzy_matches = fuzzy_matches[:max_matches]
    
    return exact_matches, fuzzy_matches

def analyze_restriction(dna_sequence, enzyme_names):
    """
    分析DNA序列上的限制性内切酶切割位点。

    参数:
        dna_sequence (str): 需要分析的DNA序列。
        enzyme_names (list): 包含限制酶名称的列表 (例如 ['EcoRI', 'BamHI'])。

    返回:
        dict: 包含分析结果的字典，包括酶列表、每个酶的切割位点、片段信息，
              或包含 'error' 键的字典。
    """
    try:
        # --- 输入验证 ---
        dna_sequence = dna_sequence.replace(" ", "").replace("\n", "").upper()
        if not dna_sequence:
            return {"error": "输入DNA序列不能为空"}
        if not is_valid_dna(dna_sequence):
             logger.warning("序列包含非标准DNA碱基 (ATCGN之外)。")
             # 可以选择返回错误或继续处理，这里选择继续但记录警告

        if not enzyme_names:
            return {"error": "需要提供至少一个限制酶名称"}

        # --- 创建酶批次并验证酶名称 ---
        try:
            # 创建一个包含所有已知酶的列表，用于验证和模糊匹配
            all_enzymes_list = [str(e) for e in Restriction.AllEnzymes]
            all_enzymes_set = set(all_enzymes_list)
            
            valid_enzyme_names = []
            invalid_enzyme_names = []
            fuzzy_matched = {}  # 存储模糊匹配的结果
            
            for name in enzyme_names:
                # 首先尝试精确匹配
                exact_name = name.strip()
                potential_name = exact_name.capitalize()
                
                # 检查精确匹配
                if exact_name in all_enzymes_set:
                    valid_enzyme_names.append(exact_name)
                elif potential_name in all_enzymes_set:
                    valid_enzyme_names.append(potential_name)
                else:
                    # 如果没有精确匹配，尝试模糊匹配
                    exact_matches, fuzzy_matches = find_matching_enzymes(exact_name, all_enzymes_list)
                    
                    if exact_matches:  # 如果有精确匹配（不区分大小写）
                        valid_enzyme_names.extend(exact_matches)
                    elif fuzzy_matches:  # 如果有模糊匹配
                        # 记录模糊匹配的结果，但暂时不添加到有效酶列表
                        fuzzy_matched[exact_name] = fuzzy_matches
                        invalid_enzyme_names.append(f"{exact_name} (可能是: {', '.join(fuzzy_matches)})")
                    else:
                        invalid_enzyme_names.append(exact_name)

            # 如果所有酶名都无效，并且有模糊匹配结果，自动使用第一个模糊匹配
            if not valid_enzyme_names and fuzzy_matched:
                for original, matches in fuzzy_matched.items():
                    if matches:  # 如果有模糊匹配
                        best_match = matches[0]  # 使用第一个（最佳）匹配
                        valid_enzyme_names.append(best_match)
                        logger.info(f"自动使用模糊匹配: '{original}' -> '{best_match}'")
                        # 更新无效酶列表，移除已自动匹配的
                        filtered_invalid = []
                        for inv in invalid_enzyme_names:
                            if not inv.startswith(f"{original} (可能是:"):
                                filtered_invalid.append(inv)
                        invalid_enzyme_names = filtered_invalid
            
            if not valid_enzyme_names:
                 return {"error": "提供的所有酶名称均无效或未知，未找到匹配酶。" + 
                        (f" 可能的匹配: {', '.join([m for sublist in fuzzy_matched.values() for m in sublist])}" 
                         if fuzzy_matched else "")}

            batch = RestrictionBatch(valid_enzyme_names)
        except ValueError as e:
            # RestrictionBatch 初始化时如果名称无效也可能抛出错误
            logger.error(f"创建 RestrictionBatch 时出错: {e}")
            return {"error": f"处理酶名称时出错: {e}"}


        # --- 执行酶切分析 ---
        seq_obj = Seq(dna_sequence)
        analysis_result = batch.search(seq_obj) # 返回一个字典 {enzyme: [cut_sites]}

        # --- 格式化结果 ---
        formatted_results = {
            "sequence": dna_sequence,  # 添加原始序列
            "sequence_length": len(seq_obj),
            "enzymes_used": [str(e) for e in batch], # 列出实际使用的有效酶
            "invalid_enzymes_skipped": invalid_enzyme_names,
            "fuzzy_matched": {k: v[0] for k, v in fuzzy_matched.items() if v and k not in invalid_enzyme_names},  # 记录成功的模糊匹配
            "analysis": {}, # 存储每个酶的详细结果
            "summary": {} # 存储所有酶切割的汇总信息
        }

        all_cut_sites = set() # 存储所有切割位点，用于计算片段

        for enzyme, sites in analysis_result.items():
            enzyme_name = str(enzyme)
            formatted_results["analysis"][enzyme_name] = {
                "site_count": len(sites),
                "cut_positions": sorted([s - 1 for s in sites]) # 转换为 0-based
            }
            all_cut_sites.update(s - 1 for s in sites) # 使用 0-based

        # --- 计算片段 ---
        # 将所有切割位点排序
        sorted_sites = sorted(list(all_cut_sites))

        fragments = []
        start = 0
        for site in sorted_sites:
            # Biopython Restriction search 返回的是切割点 *之后* 的位置 (1-based)
            # 所以 site-1 是切割点碱基的索引 (0-based)
            # 片段是从上一个切割点之后到当前切割点
            if site >= start: # 避免因重叠位点导致负长度
                 fragment_len = site - start + 1 # 片段长度
                 fragments.append({
                     "start": start, # 0-based
                     "end": site,    # 0-based (inclusive)
                     "length": fragment_len
                 })
                 start = site + 1

        # 添加最后一个片段 (从最后一个切割点到序列末尾)
        if start < len(seq_obj):
            fragments.append({
                "start": start,
                "end": len(seq_obj) - 1,
                "length": len(seq_obj) - start
            })
        elif not sorted_sites: # 如果没有切割位点，整个序列是一个片段
             fragments.append({
                "start": 0,
                "end": len(seq_obj) - 1,
                "length": len(seq_obj)
            })


        formatted_results["summary"] = {
            "total_cuts": len(all_cut_sites),
            "cut_sites_all": sorted_sites, # 所有独特的切割位点 (0-based)
            "fragment_count": len(fragments),
            "fragments": fragments # 片段列表
        }

        logger.info(f"限制性内切酶分析完成，序列长度 {len(seq_obj)}, 使用了 {len(batch)} 种酶, 找到 {len(all_cut_sites)} 个切割位点。")

        return formatted_results

    except Exception as e:
        logger.error(f"限制性内切酶分析过程中发生意外错误: {str(e)}", exc_info=True)
        return {"error": f"处理错误: {str(e)}"}

def main():
    """主函数：提供命令行界面进行限制性内切酶分析 (单行输入)"""
    # --- 获取单行交互式输入 (序列 + 酶) --- 
    print("请输入DNA序列，然后用空格隔开输入一个或多个限制酶名称：")
    print("例如: ATGCGAATTCG BamHI EcoRI")
    print("提示: 酶名支持模糊匹配，例如输入'Eco'可匹配'EcoRI'等")
    
    try:
        line = input().strip()
    except EOFError:
        print("\n错误: 未接收到输入。")
        sys.exit(1)
        
    if not line:
        print("\n错误: 输入不能为空。")
        sys.exit(1)
        
    # 按空格分割输入
    parts = line.split() # Split by any whitespace
    
    # 验证输入是否足够
    if len(parts) < 2:
        print("\n错误: 输入格式不正确。需要至少包含序列和一个酶名称，用空格隔开。")
        sys.exit(1)
        
    # 分配序列和酶列表
    dna_sequence_to_analyze = parts[0]
    enzyme_names = parts[1:]
    source = "用户交互式输入"
    
    # (可选) 可以在这里添加对 dna_sequence_to_analyze 的更严格验证
    if not is_valid_dna(dna_sequence_to_analyze):
        # 如果希望严格要求纯DNA序列，可以在这里报错退出
        print("\n警告: 输入的序列部分似乎包含非DNA字符。")
        # 或者根据需要决定是否退出
        # sys.exit(1)
        
    print(f"\n获取到序列 (长度: {len(dna_sequence_to_analyze)}) 和酶: {', '.join(enzyme_names)}")
    print(f"开始分析来自 '{source}' 的序列...")

    result = analyze_restriction(dna_sequence_to_analyze, enzyme_names)

    if "error" in result:
        print(f"\n分析失败: {result['error']}")
        sys.exit(1)

    # --- 打印结果到控制台 ---
    print("\n=== 分析结果 ===")
    print(f"序列长度: {result.get('sequence_length', 'N/A')}")
    print(f"有效酶: {', '.join(result.get('enzymes_used', []))}")
    
    # 显示成功的模糊匹配
    if result.get('fuzzy_matched'):
        for original, matched in result.get('fuzzy_matched', {}).items():
            print(f"模糊匹配: '{original}' -> '{matched}'")
    
    if result.get('invalid_enzymes_skipped'):
        print(f"跳过的无效酶: {', '.join(result['invalid_enzymes_skipped'])}")

    print("\n--- 各酶切割详情 (0-based 索引) ---")
    analysis = result.get('analysis', {})
    if analysis:
        for enzyme, data in analysis.items():
            print(f"  - {enzyme}:")
            if data.get('site_count', 0) > 0:
                print(f"    - 切割次数: {data.get('site_count', 0)}")
                print(f"    - 切割位置: {data.get('cut_positions', [])}")
            else:
                print(f"    - 无切割位点")
    else:
        print("  无切割详情")

    print("\n--- 序列片段分析 ---")
    summary = result.get('summary', {})
    print(f"总切割位点数: {summary.get('total_cuts', 0)}")
    print(f"片段数: {summary.get('fragment_count', 0)}")
    
    fragments = summary.get('fragments', [])
    if fragments:
        print("\n片段详情 (start-end, 长度):")
        for i, frag in enumerate(fragments):
            print(f"  片段 {i+1}: {frag.get('start', 'N/A')}-{frag.get('end', 'N/A')}, 长度={frag.get('length', 'N/A')}")
    else:
        print("无片段详情")

if __name__ == "__main__":
    main()