from Bio.SeqUtils.ProtParam import ProteinAnalysis
from Bio.SeqUtils import ProtParamData
from Bio import SeqIO
from Bio.Seq import Seq
import re
import logging
import argparse
import sys

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sequence_annotation(sequence):
    """
    对蛋白质序列进行功能注释和特征预测
    
    参数:
        sequence (str): 需要注释的蛋白质序列
    
    返回:
        dict: 包含序列注释和特征预测结果的字典
    """
    try:
        # 移除空格和换行符，并转换为大写
        sequence = sequence.replace(" ", "").replace("\n", "").upper()
        
        # 验证序列是否为有效的蛋白质序列
        if not is_valid_protein(sequence):
            return {"error": "无效的蛋白质序列，请检查输入"}
        
        # 创建ProteinAnalysis对象进行分析
        analysis = ProteinAnalysis(sequence)
        
        # 基本物理化学特性分析
        molecular_weight = analysis.molecular_weight()
        aromaticity = analysis.aromaticity()
        instability_index = analysis.instability_index()
        isoelectric_point = analysis.isoelectric_point()
        gravy = analysis.gravy()
        
        # 氨基酸组成分析
        aa_count = analysis.count_amino_acids()
        aa_percent = analysis.get_amino_acids_percent()
        
        # 二级结构预测
        secondary_structure = analysis.secondary_structure_fraction()
        
        # 功能域预测（简化版，基于常见模式）
        domains = predict_domains(sequence)
        
        # 信号肽预测（简化版，基于N端特征）
        signal_peptide = predict_signal_peptide(sequence)
        
        # 跨膜区预测（简化版，基于疏水性）
        transmembrane = predict_transmembrane_regions(sequence, analysis)
        
        # 整合所有结果
        result = {
            "sequence": sequence,
            "length": len(sequence),
            "molecular_weight": round(molecular_weight, 2),
            "isoelectric_point": round(isoelectric_point, 2),
            "instability_index": round(instability_index, 2),
            "stability": "不稳定" if instability_index > 40 else "稳定",
            "aromaticity": round(aromaticity, 4),
            "gravy": round(gravy, 4),
            "hydrophobicity": "亲水性" if gravy < 0 else "疏水性",
            "amino_acid_composition": {k: round(v, 2) for k, v in aa_percent.items()},
            "secondary_structure": {
                "helix": round(secondary_structure[0] * 100, 2),
                "turn": round(secondary_structure[1] * 100, 2),
                "sheet": round(secondary_structure[2] * 100, 2)
            },
            "domains": domains,
            "signal_peptide": signal_peptide,
            "transmembrane_regions": transmembrane
        }
        
        return result
        
    except Exception as e:
        logger.error(f"序列注释过程中出错: {str(e)}")
        return {"error": f"处理错误: {str(e)}"}

def is_valid_protein(sequence):
    """
    检查序列是否为有效的蛋白质序列
    
    参数:
        sequence (str): 需要检查的序列
    
    返回:
        bool: 如果序列只包含有效的氨基酸字符则返回True
    """
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
    return all(aa in valid_aa for aa in sequence)

def predict_domains(sequence):
    """
    基于常见模式预测蛋白质功能域（简化版）
    
    参数:
        sequence (str): 蛋白质序列
    
    返回:
        list: 预测的功能域列表
    """
    domains = []
    
    # 定义一些常见的功能域模式（简化版）
    domain_patterns = {
        "DNA结合域": r"[KR]{3,}[A-Z]{1,5}[KR]{2,}",
        "锌指结构域": r"C[A-Z]{2,4}C[A-Z]{3}[LIVMFYWC][A-Z]{8}H[A-Z]{3,5}H",
        "ATP结合位点": r"[AG][A-Z]{4}GK[ST]",
        "蛋白激酶域": r"[LIVMFYC]x[HY]x[LIVMFYC]{2}[LIVMFYC][LIVMFYC]xD[LIVMFYC]K[LIVMFYC]{2}N",
        "SH3域": r"[PVILSACGTM][VILACFYWTM][VILACWFYTM][VILAFYCWM][DE][VILASFCYGM][VILASFCYGMT][VILASFCYGMT]",
        "跨膜螺旋": r"[LIVMFWSTAG]{15,}"
    }
    
    for domain_name, pattern in domain_patterns.items():
        matches = re.finditer(pattern, sequence)
        for match in matches:
            start, end = match.span()
            domains.append({
                "name": domain_name,
                "start": start + 1,  # 1-based indexing
                "end": end,
                "sequence": sequence[start:end]
            })
    
    return domains

def predict_signal_peptide(sequence):
    """
    预测信号肽（简化版，基于N端特征）
    
    参数:
        sequence (str): 蛋白质序列
    
    返回:
        dict: 信号肽预测结果
    """
    # 简化版信号肽预测，仅基于N端特征
    # 真实的信号肽预测需要更复杂的算法
    
    # 检查序列长度
    if len(sequence) < 15:
        return {"predicted": False, "probability": 0.0}
    
    # 获取N端序列（前30个氨基酸）
    n_term = sequence[:min(30, len(sequence))]
    
    # 信号肽特征：N端通常有带正电荷的氨基酸，中间有疏水性氨基酸段
    hydrophobic_aa = set("AVILMFYW")
    charged_aa = set("KR")
    
    # 检查N端是否有带正电荷的氨基酸
    has_charged = any(aa in charged_aa for aa in n_term[:10])
    
    # 检查是否有连续的疏水性氨基酸段
    hydrophobic_stretch = False
    hydrophobic_count = 0
    max_hydrophobic = 0
    
    for aa in n_term[10:25]:
        if aa in hydrophobic_aa:
            hydrophobic_count += 1
            max_hydrophobic = max(max_hydrophobic, hydrophobic_count)
        else:
            hydrophobic_count = 0
    
    hydrophobic_stretch = max_hydrophobic >= 6
    
    # 计算概率分数（简化版）
    probability = 0.0
    if has_charged:
        probability += 0.3
    if hydrophobic_stretch:
        probability += 0.5
    
    # 预测结果
    predicted = probability > 0.5
    
    return {
        "predicted": predicted,
        "probability": round(probability, 2),
        "cleavage_site": n_term.find("A", 15) + 1 if predicted else None
    }

def predict_transmembrane_regions(sequence, analysis=None):
    """
    预测跨膜区域（简化版，基于疏水性窗口扫描）
    
    参数:
        sequence (str): 蛋白质序列
        analysis (ProteinAnalysis, optional): 蛋白质分析对象
    
    返回:
        list: 预测的跨膜区域列表
    """
    # 如果没有提供分析对象，创建一个新的
    if analysis is None:
        analysis = ProteinAnalysis(sequence)
    
    # 获取氨基酸疏水性值
    hydrophobicity = ProtParamData.kd  # Kyte & Doolittle疏水性值
    
    # 窗口大小（典型跨膜区域约为20个氨基酸）
    window_size = 19
    threshold = 1.6  # 疏水性阈值
    
    # 存储预测的跨膜区域
    tm_regions = []
    
    # 如果序列太短，无法进行预测
    if len(sequence) < window_size:
        return tm_regions
    
    # 计算滑动窗口的平均疏水性
    hydropathy_scores = []
    for i in range(len(sequence) - window_size + 1):
        window = sequence[i:i+window_size]
        score = sum(hydrophobicity.get(aa, 0) for aa in window) / window_size
        hydropathy_scores.append(score)
    
    # 识别连续高疏水性区域作为潜在的跨膜区域
    in_tm_region = False
    start = 0
    
    for i, score in enumerate(hydropathy_scores):
        if score > threshold and not in_tm_region:
            in_tm_region = True
            start = i
        elif score <= threshold and in_tm_region:
            in_tm_region = False
            # 只考虑足够长的区域（至少15个氨基酸）
            if i - start >= 15:
                tm_regions.append({
                    "start": start + 1,  # 1-based indexing
                    "end": i + window_size,
                    "sequence": sequence[start:i+window_size],
                    "avg_hydrophobicity": round(sum(hydropathy_scores[start:i]) / (i - start), 2)
                })
    
    # 检查最后一个区域
    if in_tm_region and len(hydropathy_scores) - start >= 15:
        tm_regions.append({
            "start": start + 1,  # 1-based indexing
            "end": len(sequence),
            "sequence": sequence[start:],
            "avg_hydrophobicity": round(sum(hydropathy_scores[start:]) / (len(hydropathy_scores) - start), 2)
        })
    
    return tm_regions

if __name__ == "__main__":
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="蛋白质序列注释工具")
    parser.add_argument("-s", "--sequence", type=str, help="需要注释的蛋白质序列")
    parser.add_argument("-f", "--file", type=str, help="包含蛋白质序列的FASTA文件")
    
    args = parser.parse_args()
    
    # 获取序列
    sequence = None
    if args.sequence:
        sequence = args.sequence
    elif args.file:
        try:
            # 从FASTA文件读取第一个序列
            with open(args.file, "r") as f:
                for record in SeqIO.parse(f, "fasta"):
                    sequence = str(record.seq)
                    break
            if not sequence:
                print("错误: 无法从文件中读取序列")
                sys.exit(1)
        except Exception as e:
            print(f"错误: 读取文件时出错: {str(e)}")
            sys.exit(1)
    else:
        print("=== 蛋白质序列注释工具 ===\n")
        sequence = input("请输入蛋白质序列: ").strip()
        if not sequence:
            print("错误: 序列不能为空")
            sys.exit(1)
    
    # 进行序列注释
    result = sequence_annotation(sequence)
    
    # 输出结果
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    else:
        print("\n=== 序列注释结果 ===\n")
        print(f"序列长度: {result['length']} 氨基酸")
        print(f"分子量: {result['molecular_weight']} Da")
        print(f"等电点: {result['isoelectric_point']}")
        print(f"不稳定指数: {result['instability_index']} ({result['stability']})")
        print(f"芳香族氨基酸比例: {result['aromaticity']}")
        print(f"平均疏水性(GRAVY): {result['gravy']} ({result['hydrophobicity']})")
        
        print("\n二级结构预测:")
        print(f"  α-螺旋: {result['secondary_structure']['helix']}%")
        print(f"  β-折叠: {result['secondary_structure']['sheet']}%")
        print(f"  β-转角: {result['secondary_structure']['turn']}%")
        
        print("\n氨基酸组成:")
        for aa, percent in result['amino_acid_composition'].items():
            print(f"  {aa}: {percent}%")
        
        print("\n信号肽预测:")
        if result['signal_peptide']['predicted']:
            print(f"  预测为含有信号肽 (概率: {result['signal_peptide']['probability']})")
            print(f"  可能的切割位点: {result['signal_peptide']['cleavage_site']}")
        else:
            print(f"  预测为不含信号肽 (概率: {result['signal_peptide']['probability']})")
        
        print("\n跨膜区域预测:")
        if result['transmembrane_regions']:
            for i, tm in enumerate(result['transmembrane_regions'], 1):
                print(f"  区域 {i}: 位置 {tm['start']}-{tm['end']} (平均疏水性: {tm['avg_hydrophobicity']})")
                print(f"    序列: {tm['sequence']}")
        else:
            print("  未检测到明显的跨膜区域")
        
        print("\n功能域预测:")
        if result['domains']:
            for i, domain in enumerate(result['domains'], 1):
                print(f"  域 {i}: {domain['name']} (位置 {domain['start']}-{domain['end']})")
                print(f"    序列: {domain['sequence']}")
        else:
            print("  未检测到已知功能域")
        
        sys.exit(0)