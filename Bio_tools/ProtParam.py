from Bio.SeqUtils.ProtParam import ProteinAnalysis
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_molecular_weight(sequence):
    try:
        # 使用BioPython进行本地计算
        analysis = ProteinAnalysis(sequence)
        
        # 获取氨基酸组成（百分比）
        aa_composition = analysis.amino_acids_percent
        
        # 计算分子量
        molecular_weight = analysis.molecular_weight()
        
        return {
            "sequence": sequence,
            "molecular_weight": f"{molecular_weight:.2f}",
            "amino_acid_composition": {k:f"{v:.2%}" for k,v in aa_composition.items()}
        }
        
    except ValueError as e:
        logger.error(f"无效氨基酸序列: {str(e)}")
        return {"error": f"无效氨基酸序列: {sequence} 包含非法字符"}
    except KeyError as e:
        logger.error(f"序列格式错误: {str(e)}")
        return {"error": "序列包含未识别的氨基酸符号"}
    except Exception as e:
        logger.error(f"ProtParam处理错误: {str(e)}")
        return {"error": f"处理错误: {str(e)}"}

if __name__ == "__main__":
    # 测试用例
    sequence = "MAEGEITTFTALTEKFNLPPGNYKKPKLLYCSNG"
    result = get_molecular_weight(sequence)
    print("分子量:", result["molecular_weight"])
    print("\n氨基酸组成：")
    for aa, percent in result["amino_acid_composition"].items():
        print(f"{aa}: {percent}")
