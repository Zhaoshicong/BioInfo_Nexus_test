from Bio.SeqUtils.ProtParam import ProteinAnalysis
from Bio.SeqUtils import molecular_weight
import logging
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def _approximate_dna_weight(sequence):
    """对包含简并碱基的DNA序列进行近似分子量计算"""
    # 简并碱基的平均分子量（基于可能的碱基）
    base_weights = {
        'A': 331.2, 'T': 322.2, 'G': 347.2, 'C': 307.2,
        'N': 327.0,  # 平均值
        'R': 339.2,  # A或G的平均值
        'Y': 314.7,  # C或T的平均值
        'S': 327.2,  # G或C的平均值
        'W': 326.7,  # A或T的平均值
        'K': 334.7,  # G或T的平均值
        'M': 319.2,  # A或C的平均值
        'B': 325.5,  # C、G或T的平均值
        'D': 333.5,  # A、G或T的平均值
        'H': 320.2,  # A、C或T的平均值
        'V': 328.5   # A、C或G的平均值
    }
    
    total_weight = sum(base_weights.get(base, 327.0) for base in sequence)
    # 减去水分子的重量（n-1个磷酸二酯键）
    if len(sequence) > 1:
        total_weight -= (len(sequence) - 1) * 18.015
    
    return total_weight

def _approximate_rna_weight(sequence):
    """对包含简并碱基的RNA序列进行近似分子量计算"""
    # RNA碱基的分子量
    base_weights = {
        'A': 347.2, 'U': 324.2, 'G': 363.2, 'C': 323.2,
        'N': 339.5,  # 平均值
        'R': 355.2,  # A或G的平均值
        'Y': 323.7,  # C或U的平均值
        'S': 343.2,  # G或C的平均值
        'W': 335.7,  # A或U的平均值
        'K': 343.7,  # G或U的平均值
        'M': 335.2,  # A或C的平均值
        'B': 336.9,  # C、G或U的平均值
        'D': 344.9,  # A、G或U的平均值
        'H': 331.5,  # A、C或U的平均值
        'V': 344.5   # A、C或G的平均值
    }
    
    total_weight = sum(base_weights.get(base, 339.5) for base in sequence)
    # 减去水分子的重量（n-1个磷酸二酯键）
    if len(sequence) > 1:
        total_weight -= (len(sequence) - 1) * 18.015
    
    return total_weight

def _is_valid_protein_sequence(sequence):
    """验证是否为有效的蛋白质序列"""
    # 标准20个氨基酸
    standard_aa = set('ACDEFGHIKLMNPQRSTVWY')
    # 扩展氨基酸（不包括*终止密码子）
    extended_aa = set('XBZJOUN')
    
    standard_count = sum(1 for c in sequence if c in standard_aa)
    extended_count = sum(1 for c in sequence if c in extended_aa)
    
    # 如果标准氨基酸比例低于70%，可能不是有效的蛋白质序列
    if len(sequence) > 0:
        standard_ratio = standard_count / len(sequence)
        # 对于全是N的序列，特殊处理（N在蛋白质中是天冬酰胺）
        if sequence.count('N') == len(sequence):
            return True  # 全N序列是有效的蛋白质序列
        return standard_ratio >= 0.7
    
    return False

def get_molecular_weight(sequence):
    try:
        # 检测序列类型 (DNA, RNA 或蛋白质)
        sequence = sequence.upper().replace(" ", "").replace("\n", "").replace("\r", "")
        
        if not sequence:
            return {"error": "序列不能为空"}
        
        # 改进的序列类型检测 - 支持简并碱基
        # DNA: 支持标准碱基 + 常见简并碱基
        dna_pattern = re.compile(r'^[ATGCNRYSWKMBDHV]+$')
        # RNA: 支持标准碱基 + 常见简并碱基  
        rna_pattern = re.compile(r'^[AUGCNRYSWKMBDHV]+$')
        # 蛋白质: 标准20个氨基酸 + 常见扩展字符（不包括*）
        protein_pattern = re.compile(r'^[ACDEFGHIKLMNPQRSTVWYXBZJOU]+$')
        
        # 检查是否包含T和U（不能同时存在）
        has_t = 'T' in sequence
        has_u = 'U' in sequence
        
        if has_t and has_u:
            return {"error": "序列不能同时包含T和U碱基"}
        
        # 计算各类型字符的比例来辅助判断
        dna_chars = set('ATGC')
        rna_chars = set('AUGC') 
        protein_chars = set('ACDEFGHIKLMNPQRSTVWY')
        
        dna_ratio = sum(1 for c in sequence if c in dna_chars) / len(sequence)
        rna_ratio = sum(1 for c in sequence if c in rna_chars) / len(sequence)
        protein_ratio = sum(1 for c in sequence if c in protein_chars) / len(sequence)
        
        # 序列类型判断逻辑
        # 检查是否为模糊序列（既可以是DNA也可以是蛋白质）
        is_ambiguous = (len(sequence) <= 20 and 
                       dna_ratio == 1.0 and 
                       protein_ratio == 1.0 and 
                       not has_u and 
                       all(c in 'ACGT' for c in sequence))
        
        # 对于全是简并碱基的序列，需要特殊处理
        if sequence.count('N') == len(sequence) and len(sequence) <= 20:
            # 短的全N序列更可能是蛋白质（天冬酰胺）
            pass  # 继续到蛋白质检测
        elif dna_pattern.match(sequence) and not has_u and (dna_ratio > 0.8 or len(sequence) > 30):
            # 处理DNA序列
            logger.info(f"检测到DNA序列，长度: {len(sequence)}")
            try:
                weight = molecular_weight(sequence, seq_type='DNA')
            except Exception as e:
                logger.warning(f"DNA分子量计算警告: {str(e)}")
                # 对于包含简并碱基的序列，使用近似计算
                weight = _approximate_dna_weight(sequence)
            
            # 计算碱基组成百分比
            base_composition = {}
            for base in ['A', 'T', 'G', 'C']:
                count = sequence.count(base)
                if count > 0:
                    base_composition[base] = count / len(sequence) * 100
            
            # 添加简并碱基统计
            other_bases = len(sequence) - sum(sequence.count(b) for b in 'ATGC')
            if other_bases > 0:
                base_composition['其他'] = other_bases / len(sequence) * 100
            
            result = {
                "sequence": sequence,
                "molecular_weight": round(weight, 2),  # 返回数字格式
                "amino_acid_composition": {k: f"{v:.2f}%" for k, v in base_composition.items()},
                "sequence_type": "DNA"
            }
            
            # 如果是模糊序列，添加提示信息
            if is_ambiguous:
                result["note"] = f"注意：此序列既可解释为DNA（{weight:.2f} Da）也可解释为蛋白质。如需蛋白质分析，请使用'物理化学参数分析'工具。"
            
            return result
            
        elif rna_pattern.match(sequence) and not has_t and (rna_ratio > 0.8 or len(sequence) > 30):
            # 处理RNA序列
            logger.info(f"检测到RNA序列，长度: {len(sequence)}")
            try:
                weight = molecular_weight(sequence, seq_type='RNA')
            except Exception as e:
                logger.warning(f"RNA分子量计算警告: {str(e)}")
                # 对于包含简并碱基的序列，使用近似计算
                weight = _approximate_rna_weight(sequence)
            
            # 计算碱基组成百分比
            base_composition = {}
            for base in ['A', 'U', 'G', 'C']:
                count = sequence.count(base)
                if count > 0:
                    base_composition[base] = count / len(sequence) * 100
            
            # 添加简并碱基统计
            other_bases = len(sequence) - sum(sequence.count(b) for b in 'AUGC')
            if other_bases > 0:
                base_composition['其他'] = other_bases / len(sequence) * 100
            
            return {
                "sequence": sequence,
                "molecular_weight": round(weight, 2),  # 返回数字格式
                "amino_acid_composition": {k: f"{v:.2f}%" for k, v in base_composition.items()},
                "sequence_type": "RNA"
            }
            
        elif protein_pattern.match(sequence):
            # 处理蛋白质序列
            logger.info(f"检测到蛋白质序列，长度: {len(sequence)}")
            
            # 验证是否为有效的蛋白质序列
            if not _is_valid_protein_sequence(sequence):
                return {"error": "无效的蛋白质序列，包含过多非标准氨基酸"}
            
            # 处理包含非标准氨基酸的序列
            try:
                analysis = ProteinAnalysis(sequence)
            except ValueError as e:
                # 如果包含BioPython不支持的字符，尝试清理序列
                cleaned_sequence = ''.join(c for c in sequence if c in 'ACDEFGHIKLMNPQRSTVWY')
                if len(cleaned_sequence) < len(sequence) * 0.5:
                    return {"error": f"序列包含过多无效字符: {str(e)}"}
                analysis = ProteinAnalysis(cleaned_sequence)
                sequence = cleaned_sequence  # 使用清理后的序列
            
            # 获取氨基酸组成（百分比）
            aa_composition = analysis.amino_acids_percent
            
            # 计算分子量
            molecular_weight_value = analysis.molecular_weight()
            
            return {
                "sequence": sequence,
                "molecular_weight": round(molecular_weight_value, 2),  # 返回数字格式
                "amino_acid_composition": {k: f"{v:.2f}%" for k, v in aa_composition.items()},
                "sequence_type": "protein"
            }
        else:
            # 无法识别的序列类型
            return {"error": f"无法识别的序列类型。序列可能包含无效字符或格式不正确。"}
        
    except ValueError as e:
        logger.error(f"无效序列: {str(e)}")
        return {"error": f"无效序列: {sequence} 包含非法字符"}
    except KeyError as e:
        logger.error(f"序列格式错误: {str(e)}")
        return {"error": "序列包含未识别的字符"}
    except Exception as e:
        logger.error(f"序列处理错误: {str(e)}")
        return {"error": f"处理错误: {str(e)}"}

if __name__ == "__main__":
    # 测试用例
    protein_sequence = "MAEGEITTFTALTEKFNLPPGNYKKPKLLYCSNG"
    dna_sequence = "ATGCATGCATGCATGC"
    rna_sequence = "AUGCAUGCAUGCAUGC"
    
    protein_result = get_molecular_weight(protein_sequence)
    dna_result = get_molecular_weight(dna_sequence)
    rna_result = get_molecular_weight(rna_sequence)
    
    print("蛋白质分子量:", protein_result["molecular_weight"])
    print("DNA分子量:", dna_result["molecular_weight"])
    print("RNA分子量:", rna_result["molecular_weight"])
    
    print("\n蛋白质氨基酸组成：")
    for aa, percent in protein_result["amino_acid_composition"].items():
        print(f"{aa}: {percent}")
        
    print("\nDNA碱基组成：")
    for base, percent in dna_result["amino_acid_composition"].items():
        print(f"{base}: {percent}")
