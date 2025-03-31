from Bio.Seq import Seq
from Bio import Restriction
from Bio.Restriction import RestrictionBatch
import logging
import sys
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_valid_dna(sequence):
    """检查序列是否为有效的DNA序列 (允许N)"""
    valid_bases = set("ATCGN")
    return all(base.upper() in valid_bases for base in sequence)

def find_all_cutting_enzymes(dna_sequence):
    """
    找出 Biopython 库中所有能够切割给定 DNA 序列的限制酶。

    参数:
        dna_sequence (str): 需要分析的 DNA 序列。

    返回:
        dict: 包含结果的字典，其中 'cutting_enzymes' 是一个列表，
              列出了所有找到切割位点的酶的名称及其切割次数和位点。
              或包含 'error' 键的字典。
    """
    try:
        dna_sequence = dna_sequence.replace(" ", "").replace("\n", "").upper()
        if not dna_sequence:
            return {"error": "输入DNA序列不能为空"}
        if not is_valid_dna(dna_sequence):
             logger.warning("序列包含非标准DNA碱基 (ATCGN之外)。")
             # 允许继续

        seq_obj = Seq(dna_sequence)
        logger.info(f"开始在长度为 {len(seq_obj)} 的序列中搜索所有已知限制酶的切点...")

        # 创建包含所有已知酶的批次
        # 使用 try-except 捕获可能的 RestrictionBatch 初始化错误
        try:
            all_enzymes_batch = RestrictionBatch(Restriction.AllEnzymes)
        except Exception as batch_err:
            logger.error(f"创建 RestrictionBatch 时出错: {batch_err}", exc_info=True)
            return {"error": f"初始化限制酶列表时出错: {batch_err}"}


        # 执行搜索
        start_time = time.time()
        # 使用 try-except 包装 search，因为对于某些序列和酶组合可能出现内部错误
        try:
            analysis_result = all_enzymes_batch.search(seq_obj)
        except Exception as search_err:
             logger.error(f"Biopython Restriction.search 执行时出错: {search_err}", exc_info=True)
             return {"error": f"酶切搜索过程中出错: {search_err}"}

        duration = time.time() - start_time
        logger.info(f"搜索完成，耗时: {duration:.2f} 秒。")

        # 提取找到切点的酶
        cutting_enzymes_info = []
        for enzyme, sites in analysis_result.items():
            if sites: # 确保确实有切点
                cutting_enzymes_info.append({
                    "name": str(enzyme),
                    "site_count": len(sites),
                    "cut_positions": sorted([s - 1 for s in sites]) # 0-based
                })

        # 按酶名称排序结果
        cutting_enzymes_info.sort(key=lambda x: x['name'])

        logger.info(f"共找到 {len(cutting_enzymes_info)} 种酶可以切割该序列。")

        return {
            "sequence": str(seq_obj),  # 添加原始序列
            "sequence_length": len(seq_obj),
            "cutting_enzymes": cutting_enzymes_info,
            "search_duration_seconds": round(duration, 2),
            "success": True # 添加成功标记
        }

    except Exception as e:
        logger.error(f"查找所有切割酶过程中发生错误: {str(e)}", exc_info=True)
        return {"error": f"处理错误: {str(e)}"}

def main():
    """主函数：提供命令行界面进行酶谱分析 (仅交互式输入)"""
    # --- 直接获取交互式输入 --- 
    print("请输入DNA序列，按两次Enter键结束输入：")
    lines = []
    try:
        while True:
            line = input()
            if line:
                lines.append(line.strip())
            else:
                break
    except EOFError:
        pass # 处理管道输入结束等情况
    
    sequence_to_analyze = "".join(lines).replace(" ", "")
    source = "用户交互式输入"

    if not sequence_to_analyze:
        # parser.print_help() # 不再需要打印帮助
        print("\n错误: 未提供序列。")
        sys.exit(1)
    print(f"获取到用户输入的序列, 长度: {len(sequence_to_analyze)}")

    print(f"\n开始分析来自 '{source}' 的序列，查找所有切割酶...")

    result = find_all_cutting_enzymes(sequence_to_analyze)

    if "error" in result:
        print(f"\n分析失败: {result['error']}")
        sys.exit(1)

    # --- 打印结果到控制台 ---
    print("\n=== 酶谱分析结果 ===")
    print(f"序列长度: {result.get('sequence_length', 'N/A')}")
    print(f"搜索耗时: {result.get('search_duration_seconds', 'N/A')} 秒")

    cutting_enzymes = result.get('cutting_enzymes', [])
    print(f"\n找到 {len(cutting_enzymes)} 种切割酶:")
    if cutting_enzymes:
        print("酶名称 -> 切割次数 -> 切割位点 (0-based, 最多显示10个)")
        # 直接遍历所有找到的酶
        for enzyme_info in cutting_enzymes: # Iterate over the full list
            # 确保 cut_positions 是列表
            cut_positions = enzyme_info.get('cut_positions', [])
            pos_str = ', '.join(map(str, cut_positions[:10]))
            if len(cut_positions) > 10:
                pos_str += "..."
            print(f"  - {enzyme_info.get('name', '未知酶')} -> {enzyme_info.get('site_count', 0)} -> [{pos_str}]")
    else:
        print("  未找到任何已知限制酶可以切割此序列。")

    print("\n分析完成。")


if __name__ == "__main__":
    main()
