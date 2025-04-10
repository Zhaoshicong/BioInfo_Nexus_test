"""
FASTA格式序列转换工具

该模块提供将FASTA格式序列转换为纯序列的功能。
FASTA格式通常包含以'>'开头的描述行，后面跟着序列行。
该工具会移除描述行和所有空白字符，只保留序列本身。

函数:
    extract_sequence_from_fasta: 将FASTA格式文本转换为纯序列
    read_fasta_file: 从FASTA文件读取并返回序列字典
    write_pure_sequence: 将纯序列写入文件
    transform_fasta: 主函数，作为API调用入口

命令行用法:
    python Transform.py input.fasta [output.txt] [--format] [--line-length=60]
"""

import os
import re
import sys
import argparse

def extract_sequence_from_fasta(fasta_text):
    """
    将FASTA格式文本转换为纯序列。
    
    参数:
        fasta_text (str): FASTA格式的文本
        
    返回:
        dict: 包含序列ID和序列的字典，格式为 {sequence_id: sequence}
    """
    sequences = {}
    if not fasta_text or not fasta_text.strip():
        return sequences
    
    # 分割文本为不同的序列记录
    # 以'>'开头的行作为分隔点
    fasta_entries = re.split(r'>(\S+)[^\n]*\n', fasta_text)
    
    # 移除第一个空条目(如果存在)
    if fasta_entries and not fasta_entries[0].strip():
        fasta_entries = fasta_entries[1:]
    
    # 处理分组后的结果
    for i in range(0, len(fasta_entries), 2):
        if i + 1 < len(fasta_entries):
            seq_id = fasta_entries[i]
            seq = fasta_entries[i + 1].replace('\n', '').replace(' ', '')
            sequences[seq_id] = seq
    
    return sequences

def extract_sequence_from_fasta_simple(fasta_text):
    """
    将FASTA格式文本转换为单个纯序列。
    只返回第一个找到的序列，忽略ID和其他序列。
    适用于只关心序列内容而不关心序列ID的场景。
    
    参数:
        fasta_text (str): FASTA格式的文本
        
    返回:
        str: 提取的纯序列
    """
    if not fasta_text:
        return ""
    
    # 移除所有注释行(以'>'开头的行)
    sequence = re.sub(r'>.*?\n', '', fasta_text)
    
    # 移除所有空白字符(空格、换行、制表符等)
    sequence = re.sub(r'\s', '', sequence)
    
    return sequence

def read_fasta_file(file_path):
    """
    从FASTA文件读取序列。
    
    参数:
        file_path (str): FASTA文件的路径
        
    返回:
        dict: 包含序列ID和序列的字典
        
    异常:
        FileNotFoundError: 当文件不存在时抛出
        IOError: 当读取文件出错时抛出
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件未找到: {file_path}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            fasta_text = f.read()
        return extract_sequence_from_fasta(fasta_text)
    except IOError as e:
        raise IOError(f"读取文件时出错: {str(e)}")

def write_pure_sequence(sequence, output_file):
    """
    将纯序列写入文件。
    
    参数:
        sequence (str): 要写入的序列
        output_file (str): 输出文件的路径
        
    返回:
        bool: 写入成功返回True，否则返回False
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(sequence)
        return True
    except Exception as e:
        print(f"写入文件时出错: {str(e)}")
        return False

def format_sequence(sequence):
    """
    将序列中的空白字符移除。
    
    参数:
        sequence (str): 要处理的序列
        
    返回:
        str: 移除了空白字符的序列
    """
    if not sequence:
        return ""
    
    # 移除所有空白字符
    sequence = re.sub(r'\s', '', sequence)
    
    # 直接返回无换行的序列
    return sequence

def is_fasta_format(text):
    """
    检查文本是否为FASTA格式。
    
    参数:
        text (str): 要检查的文本
        
    返回:
        bool: 如果是FASTA格式返回True，否则返回False
    """
    if not text:
        return False
    
    # 检查是否以'>'开头
    if text.strip().startswith('>'):
        return True
    
    return False

def transform_fasta(input_data, options=None):
    """
    FASTA格式转换的主函数，作为后端API调用入口。
    
    参数:
        input_data (str or dict): 输入数据，可以是FASTA格式字符串或包含参数的字典
        options (dict, optional): 转换选项，包括:
            - format_output (bool): 是否移除空白字符，默认True (现在不再控制换行)
            - return_all (bool): 是否返回所有序列，默认False
            - output_file (str): 输出文件路径，如不指定则不保存到文件
    
    返回:
        dict: 包含转换结果的字典，格式为:
            成功时:
            {
                'success': True,
                'sequence': str,  # 当return_all=False时
                'sequences': dict,  # 当return_all=True时
                'count': int,  # 当return_all=True时，表示序列数量
                'length': int,  # 当return_all=False时，表示序列长度
                'saved_to_file': bool  # 是否已保存到文件
            }
            
            失败时:
            {
                'success': False,
                'error': str  # 错误信息
            }
    """
    # 初始化默认选项 (移除 line_length)
    default_options = {
        'format_output': True,
        'return_all': False,
        'output_file': None
    }
    
    # 如果input_data是字典，则可能包含序列和选项
    if isinstance(input_data, dict):
        fasta_text = input_data.get('sequence', '')
        # 合并输入选项和默认选项 (移除 line_length 处理)
        if options is None:
            options = {}
        for key in default_options:
            if key in input_data and key not in options:
                options[key] = input_data[key]
        # Ensure options not passed in input_data still get defaults
        for key, value in default_options.items():
            if key not in options:
                options[key] = value
                
    else: # input_data is just the fasta string
        fasta_text = input_data
        # 确保options字典存在并填充默认值
        if options is None:
            options = default_options.copy()
        else:
            temp_options = default_options.copy()
            temp_options.update(options)
            options = temp_options


    # 验证输入
    if not fasta_text or not isinstance(fasta_text, str):
        return {'success': False, 'error': '无效的FASTA格式序列'}
    
    try:
        # 根据选项处理序列
        if options.get('return_all', False):
            # 提取所有序列
            sequences = extract_sequence_from_fasta(fasta_text)
            
            if not sequences:
                return {'success': False, 'error': '无法解析FASTA格式，或输入不是有效的FASTA格式'}
            
            result = {
                'success': True,
                'sequences': {},
                'count': len(sequences)
            }
            
            # 格式化每个序列（如果需要，现在只移除空白）
            for seq_id, seq in sequences.items():
                if options.get('format_output', True):
                    result['sequences'][seq_id] = format_sequence(seq) # 不再传递 line_length
                else:
                    # If not formatting, keep original whitespace?
                    # Let's assume format_output=False means keep original sequence including whitespace.
                    # However, extract_sequence_from_fasta already removes whitespace. 
                    # For consistency, let's always call format_sequence if format_output is true,
                    # otherwise return the already whitespace-removed sequence.
                    result['sequences'][seq_id] = seq # seq from extract already has whitespace removed
            
            # 如果指定了输出文件，保存第一个序列
            if options.get('output_file') and sequences:
                first_seq = list(sequences.values())[0] # Already whitespace-removed
                # format_output true means whitespace removed (done), false means keep original (not possible here)
                # Let's simplify: save the whitespace-removed sequence regardless of format_output for file saving
                success = write_pure_sequence(first_seq, options['output_file'])
                result['saved_to_file'] = success
            
            return result
        else:
            # 只提取第一个序列
            pure_sequence = extract_sequence_from_fasta_simple(fasta_text) # Removes whitespace
            if not pure_sequence: return {'success': False, 'error': '无法解析FASTA格式，或输入不是有效的FASTA格式'}
            
            # If format_output is false, should we return the original sequence WITH whitespace?
            # The simple extractor already removed it. Let's redefine format_output slightly:
            # True = remove whitespace (always done by extractors now)
            # False = try to preserve original? This is hard. Let's stick to: it controls formatting (now non-existent)
            # Let's just return the whitespace-removed sequence.
            formatted_sequence = pure_sequence # Always whitespace-removed
            
            result = {
                'success': True,
                'sequence': formatted_sequence,
                'length': len(pure_sequence)
            }
            
            # 如果指定了输出文件，保存序列
            if options.get('output_file'):
                success = write_pure_sequence(formatted_sequence, options['output_file'])
                result['saved_to_file'] = success
            
            return result
    
    except Exception as e:
        # Log the error for debugging
        # import traceback
        # print(f"Error in transform_fasta: {str(e)}\n{traceback.format_exc()}")
        return {'success': False, 'error': f'转换过程发生错误: {str(e)}'}

# 命令行接口
def main():
    """命令行接口主函数"""
    parser = argparse.ArgumentParser(description='将FASTA格式序列转换为纯序列')
    parser.add_argument('input_file', help='输入的FASTA文件路径')
    parser.add_argument('output_file', nargs='?', help='输出的纯序列文件路径（可选）')
    parser.add_argument('--format', action='store_true', help='是否格式化输出（移除空白，默认是）') # 更新帮助文本
    parser.add_argument('--no-format', action='store_true', help='不格式化输出（保留原始空白，如果可能）') # 更新帮助文本
    parser.add_argument('--all', action='store_true', help='处理所有序列，而不仅仅是第一个')
    
    args = parser.parse_args()
    
    # 检查输入文件是否存在
    if not os.path.exists(args.input_file):
        print(f"错误: 输入文件 '{args.input_file}' 不存在")
        return 1
    
    try:
        # 读取输入文件
        with open(args.input_file, 'r', encoding='utf-8') as f:
            fasta_text = f.read()
        
        # 设置选项 (移除 line_length)
        options = {
            'format_output': not args.no_format,
            'return_all': args.all
        }
        
        # 如果指定了输出文件，添加到选项中
        if args.output_file:
            options['output_file'] = args.output_file
        
        # 调用主函数转换序列
        result = transform_fasta(fasta_text, options)
        
        # 处理结果
        if result['success']:
            if 'sequences' in result:
                print(f"找到 {result['count']} 个序列")
                if not args.output_file:
                    for seq_id, seq in result['sequences'].items():
                        print(f"\n序列 ID: {seq_id}")
                        print(seq[:100] + "..." if len(seq) > 100 else seq)
            else:
                print(f"提取的序列长度: {result['length']}")
                if not args.output_file:
                    seq = result['sequence']
                    print(seq[:100] + "..." if len(seq) > 100 else seq)
            
            if args.output_file:
                print(f"结果已保存到: {args.output_file}")
            
            return 0
        else:
            print(f"错误: {result['error']}")
            return 1
    
    except Exception as e:
        print(f"发生错误: {str(e)}")
        return 1

# 示例使用
if __name__ == "__main__":
    # 如果直接运行脚本且有命令行参数，则执行命令行接口
    if len(sys.argv) > 1:
        sys.exit(main())
    
    # 否则运行示例代码
    fasta_example = """>sp|P01308|INS_HUMAN Insulin [Homo sapiens]
MALWMRLLPLLALLALWGPDPAAAFVNQHLCGSHLVEALYLVCGERGFFYTPKTRREAEDLQVGQVEL
GGGPGAGSLQPLALEGSLQKRGIVEQCCTSICSLYQLENYCN
>another_sequence
ACGTACGTACGT"""
    
    print("FASTA格式示例:")
    print(fasta_example)
    
    # 使用主函数转换
    result = transform_fasta(fasta_example, {'return_all': True})
    
    if result['success']:
        print("\n转换成功!")
        if 'sequences' in result:
            print(f"找到 {result['count']} 个序列:")
            for seq_id, seq in result['sequences'].items():
                print(f"\nID: {seq_id}")
                print(f"序列: \n{seq}")
        else:
            print(f"\n提取的序列 (长度: {result['length']}):")
            print(result['sequence'])
    else:
        print(f"\n转换失败: {result['error']}")
