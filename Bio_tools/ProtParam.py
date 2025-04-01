from Bio.SeqUtils.ProtParam import ProteinAnalysis
from Bio.SeqUtils import molecular_weight
import logging
import re

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_molecular_weight(sequence):
    try:
        # 检测序列类型 (DNA, RNA 或蛋白质)
        sequence = sequence.upper().replace(" ", "")
        
        # 序列类型检测
        dna_pattern = re.compile(r'^[ATGC]+$')
        rna_pattern = re.compile(r'^[AUGC]+$')
        
        if dna_pattern.match(sequence):
            # 处理DNA序列
            logger.info(f"检测到DNA序列，长度: {len(sequence)}")
            weight = molecular_weight(sequence, seq_type='DNA')
            
            # 计算碱基组成百分比
            base_composition = {
                'A': sequence.count('A') / len(sequence) * 100,
                'T': sequence.count('T') / len(sequence) * 100,
                'G': sequence.count('G') / len(sequence) * 100,
                'C': sequence.count('C') / len(sequence) * 100
            }
            
            return {
                "sequence": sequence,
                "molecular_weight": f"{weight:.2f}",
                "amino_acid_composition": {k:f"{v:.2f}%" for k,v in base_composition.items()},
                "sequence_type": "DNA"
            }
            
        elif rna_pattern.match(sequence):
            # 处理RNA序列
            logger.info(f"检测到RNA序列，长度: {len(sequence)}")
            weight = molecular_weight(sequence, seq_type='RNA')
            
            # 计算碱基组成百分比
            base_composition = {
                'A': sequence.count('A') / len(sequence) * 100,
                'U': sequence.count('U') / len(sequence) * 100,
                'G': sequence.count('G') / len(sequence) * 100,
                'C': sequence.count('C') / len(sequence) * 100
            }
            
            return {
                "sequence": sequence,
                "molecular_weight": f"{weight:.2f}",
                "amino_acid_composition": {k:f"{v:.2f}%" for k,v in base_composition.items()},
                "sequence_type": "RNA"
            }
            
        else:
            # 假设是蛋白质序列，使用原来的处理方式
            logger.info(f"假设为蛋白质序列，长度: {len(sequence)}")
            analysis = ProteinAnalysis(sequence)
            
            # 获取氨基酸组成（百分比）
            aa_composition = analysis.amino_acids_percent
            
            # 计算分子量
            molecular_weight_value = analysis.molecular_weight()
            
            return {
                "sequence": sequence,
                "molecular_weight": f"{molecular_weight_value:.2f}",
                "amino_acid_composition": {k:f"{v:.2f}%" for k,v in aa_composition.items()},
                "sequence_type": "protein"
            }
        
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
