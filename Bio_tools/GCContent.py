# 创建新文件: Bio_tools/GCContent.py
import logging
import sys
from Bio.Seq import Seq
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils import MeltingTemp as mt # 导入熔解温度模块

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def is_valid_sequence(sequence):
    """检查序列是否只包含 ATCGUN"""
    # 允许大小写，并在检查前转为大写
    valid_bases = set("ATCGUN")
    return all(base.upper() in valid_bases for base in sequence)

def GC(seq):
    """兼容 Biopython 不同版本的 GC 计算，返回百分比"""
    try:
        # Biopython gc_fraction 处理空序列会返回 0
        return gc_fraction(seq) * 100
    except Exception as e:
        logger.warning(f"GC calculation error for seq '{seq[:10]}...': {e}")
        return 0.0 # 返回 0.0 作为错误情况下的默认值

def analyze_nucleic_acid_properties(sequence):
    """
    计算DNA或RNA序列的基本物理化学性质。

    参数:
        sequence (str): 需要分析的DNA或RNA序列。

    返回:
        dict: 包含计算结果的字典 (GC含量, Tm, 密度估算)，或包含 'error' 键的字典。
    """
    try:
        sequence_cleaned = sequence.replace(" ", "").replace("\n", "").upper()
        if not sequence_cleaned:
            return {"error": "输入序列不能为空"}
        
        # 转换为 Bio.Seq 对象，方便后续计算
        try:
             seq_obj = Seq(sequence_cleaned)
        except ValueError as e:
             return {"error": f"序列格式无效: {e}"}

        # 验证序列 (允许 U 和 N)
        if not is_valid_sequence(str(seq_obj)):
             logger.warning("序列包含非标准碱基 (ATCGUN之外)，某些计算可能受影响。")

        seq_len = len(seq_obj)
        results = {
            "sequence": str(seq_obj),
            "sequence_length": seq_len,
            "is_rna": "U" in seq_obj and "T" not in seq_obj # 简单判断是否为 RNA
        }

        # --- 1. 计算整体 GC 含量 ---
        overall_gc = GC(seq_obj)
        results["overall_gc"] = round(overall_gc, 2)
        gc_frac = overall_gc / 100.0 # 获取小数形式用于其他计算

        # --- 2. 估算熔解温度 (Tm) ---
        # 使用简单的 GC 方法
        try:
            # Tm_GC 假设为 DNA，如果需要 RNA Tm 需用其他方法或参数
            tm_gc_simple = mt.Tm_GC(seq_obj, strict=False) # strict=False 允许非标准碱基
            results["tm_gc_simple"] = round(tm_gc_simple, 2)
        except ValueError as e:
             logger.warning(f"无法计算 Tm_GC: {e}")
             results["tm_gc_simple"] = "N/A"
             
        # 使用更精确的最近邻方法 (Nearest Neighbor, NN)
        # 需要设定一些默认的离子浓度等条件
        # 注意：Tm_NN 主要为 DNA 设计，虽然可以接受含 U 的序列
        # 默认参数： Check=True, strict=False
        # 标准盐浓度 (例如 50 mM Na+, 0 mM K+, 0 mM Mg++)
        try:
            tm_nn_standard = mt.Tm_NN(seq_obj, Na=50, K=0, Mg=0, dNTPs=0, saltcorr=7)
            results["tm_nn_standard"] = round(tm_nn_standard, 2)
        except ValueError as e:
             logger.warning(f"无法计算 Tm_NN (可能序列过短或含非标准碱基过多): {e}")
             results["tm_nn_standard"] = "N/A"

        # --- 3. 估算浮力密度 (Buoyant Density) ---
        # 使用 Schildkraut 公式 (适用于双链 DNA 在 CsCl 梯度中)
        if not results["is_rna"]: # 公式主要用于 DNA
            try:
                # 确保 gc_frac 在 0 到 1 之间
                gc_frac_clamped = max(0.0, min(1.0, gc_frac))
                density_cscl = 1.660 + 0.098 * gc_frac_clamped
                results["estimated_density_cscl"] = round(density_cscl, 3)
            except Exception as e:
                 logger.warning(f"无法估算密度: {e}")
                 results["estimated_density_cscl"] = "N/A"
        else:
             results["estimated_density_cscl"] = "N/A (公式适用于DNA)"


        logger.info(f"计算了序列属性: GC={results['overall_gc']}%, Tm_NN={results['tm_nn_standard']}C, Density={results.get('estimated_density_cscl', 'N/A')}")

        return results

    except Exception as e:
        logger.error(f"属性计算过程中发生意外错误: {str(e)}", exc_info=True)
        return {"error": f"处理错误: {str(e)}"}

def main():
    """主函数：提供交互式界面进行核酸序列属性计算"""
    
    # --- 获取序列输入 ---
    print("请输入DNA/RNA序列，按两次Enter键结束输入：")
    lines = []
    try:
        while True:
            line = input()
            if line:
                lines.append(line.strip())
            else:
                break
    except EOFError:
        pass
    sequence_to_analyze = "".join(lines).replace(" ", "")
    source = "用户交互式输入"
    
    if not sequence_to_analyze:
        print("\n错误: 未提供序列。")
        sys.exit(1)
        
    print(f"获取到用户输入的序列, 长度: {len(sequence_to_analyze)}")

    # --- 直接进行计算 ---
    print(f"\n开始计算来自 '{source}' 的序列的基本物理化学性质...")

    result = analyze_nucleic_acid_properties(sequence_to_analyze)

    if "error" in result:
        print(f"\n计算失败: {result['error']}")
        sys.exit(1)

    # --- 打印结果到控制台 ---
    print("\n=== 序列物理化学性质结果 ===")
    print(f"序列长度: {result.get('sequence_length', 'N/A')}")
    print(f"类型: {'RNA' if result.get('is_rna') else 'DNA'}")
    print(f"GC 含量: {result.get('overall_gc', 'N/A')}%")
    print("\n熔解温度 (Tm) 估算:")
    print(f"  - 基于 GC 含量 (简单方法): {result.get('tm_gc_simple', 'N/A')} °C")
    print(f"  - 最近邻模型 (标准条件*): {result.get('tm_nn_standard', 'N/A')} °C")
    print("    (*标准条件近似为: 50mM Na+, 0mM K+, 0mM Mg++)")
    print("\n浮力密度 (Buoyant Density) 估算:")
    print(f"  - 在 CsCl 梯度中 (Schildkraut 公式**): {result.get('estimated_density_cscl', 'N/A')} g/cm³")
    print("    (**公式主要适用于双链DNA)")
    
    print("\n计算完成。")


if __name__ == "__main__":
    main()