from Bio.Seq import Seq
from Bio.Data import CodonTable
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def translate_dna(sequence, table_id=1, to_stop=False, cds=False):
    """
    将DNA序列翻译为蛋白质序列
    
    参数:
        sequence (str): 需要翻译的DNA序列
        table_id (int): 遗传密码表ID，默认为1（标准密码表）
        to_stop (bool): 是否在第一个终止密码子处停止翻译
        cds (bool): 是否将序列视为完整的编码序列（检查起始/终止密码子）
    
    返回:
        dict: 包含原始序列和翻译结果的字典
    """
    try:
        # 移除空格和换行符
        sequence = sequence.replace(" ", "").replace("\n", "").upper()
        
        # 创建Seq对象
        seq = Seq(sequence)
        
        # 获取密码表
        table = CodonTable.unambiguous_dna_by_id[table_id]
        
        # 翻译序列
        if cds:
            protein = seq.translate(table=table_id, cds=True)
        else:
            protein = seq.translate(table=table_id, to_stop=to_stop)
        
        return {
            "original_sequence": sequence,
            "translated_sequence": str(protein),
            "translation_table": table.id,
            "translation_table_name": table.names[0]
        }
        
    except Exception as e:
        logger.error(f"翻译过程中出错: {str(e)}")
        return {"error": f"翻译错误: {str(e)}"}

def translate_rna(sequence, table_id=1, to_stop=False, cds=False):
    """
    将RNA序列翻译为蛋白质序列
    
    参数:
        sequence (str): 需要翻译的RNA序列
        table_id (int): 遗传密码表ID，默认为1（标准密码表）
        to_stop (bool): 是否在第一个终止密码子处停止翻译
        cds (bool): 是否将序列视为完整的编码序列（检查起始/终止密码子）
    
    返回:
        dict: 包含原始序列和翻译结果的字典
    """
    try:
        # 移除空格和换行符
        sequence = sequence.replace(" ", "").replace("\n", "").upper()
        
        # 创建Seq对象
        seq = Seq(sequence)
        
        # 获取密码表
        table = CodonTable.unambiguous_rna_by_id[table_id]
        
        # 翻译序列
        if cds:
            protein = seq.translate(table=table_id, cds=True)
        else:
            protein = seq.translate(table=table_id, to_stop=to_stop)
        
        return {
            "original_sequence": sequence,
            "translated_sequence": str(protein),
            "translation_table": table.id,
            "translation_table_name": table.names[0]
        }
        
    except Exception as e:
        logger.error(f"翻译过程中出错: {str(e)}")
        return {"error": f"翻译错误: {str(e)}"}

def get_available_tables():
    """
    获取所有可用的遗传密码表
    
    返回:
        dict: 密码表ID和名称的字典
    """
    tables = {}
    for table_id in CodonTable.unambiguous_dna_by_id:
        table = CodonTable.unambiguous_dna_by_id[table_id]
        tables[table_id] = table.names[0]
    return tables

def translate_sequence(sequence, seq_type=None, table_id=1, to_stop=False, cds=False):
    """
    自动检测并翻译DNA或RNA序列为蛋白质序列，适用于网页调用
    
    参数:
        sequence (str): 需要翻译的序列
        seq_type (str, optional): 序列类型，可以是'dna'或'rna'，如果为None则自动检测
        table_id (int): 遗传密码表ID，默认为1（标准密码表）
        to_stop (bool): 是否在第一个终止密码子处停止翻译
        cds (bool): 是否将序列视为完整的编码序列（检查起始/终止密码子）
    
    返回:
        dict: 包含原始序列和翻译结果的字典
    """
    # 移除空格和换行符
    sequence = sequence.replace(" ", "").replace("\n", "").upper()
    
    # 如果序列为空，返回错误
    if not sequence:
        return {"error": "序列不能为空"}
    
    # 自动检测序列类型（如果未指定）
    if seq_type is None:
        # 如果序列中包含'U'或'u'，则认为是RNA
        if 'U' in sequence:
            seq_type = 'rna'
        else:
            seq_type = 'dna'
    
    # 根据序列类型调用相应的翻译函数
    if seq_type.lower() == 'rna':
        return translate_rna(sequence, table_id, to_stop, cds)
    else:  # 默认为DNA
        return translate_dna(sequence, table_id, to_stop, cds)

if __name__ == "__main__":
    import argparse
    import sys
    
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description="DNA/RNA序列翻译工具")
    parser.add_argument("-s", "--sequence", type=str, help="需要翻译的DNA或RNA序列")
    parser.add_argument("-t", "--type", type=str, choices=["dna", "rna"], help="序列类型，可选'dna'或'rna'，默认自动检测")
    parser.add_argument("-i", "--table_id", type=int, default=1, help="遗传密码表ID，默认为1（标准密码表）")
    parser.add_argument("--to_stop", action="store_true", help="在第一个终止密码子处停止翻译")
    parser.add_argument("--cds", action="store_true", help="将序列视为完整的编码序列（检查起始/终止密码子）")
    parser.add_argument("-l", "--list_tables", action="store_true", help="列出所有可用的遗传密码表")
    
    args = parser.parse_args()
    
    # 列出所有可用的遗传密码表
    if args.list_tables:
        print("=== 可用的遗传密码表 ===")
        tables = get_available_tables()
        for table_id, name in tables.items():
            print(f"ID {table_id}: {name}")
        sys.exit(0)
    
    # 如果没有提供序列，则提示用户输入
    if not args.sequence:
        print("=== DNA/RNA序列翻译工具 ===")
        sequence = input("请输入DNA或RNA序列: ").strip()
        if not sequence:
            print("错误: 序列不能为空")
            sys.exit(1)
        args.sequence = sequence
    
    # 翻译序列
    result = translate_sequence(args.sequence, args.type, args.table_id, args.to_stop, args.cds)
    
    # 输出结果
    if "error" in result:
        print(f"错误: {result['error']}")
        sys.exit(1)
    else:
        print("\n=== 翻译结果 ===")
        print(f"原始序列: {result['original_sequence']}")
        print(f"翻译结果: {result['translated_sequence']}")
        print(f"使用密码表: {result['translation_table_name']} (ID: {result['translation_table']})")
        sys.exit(0)