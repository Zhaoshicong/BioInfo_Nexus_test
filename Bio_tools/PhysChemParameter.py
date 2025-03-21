import requests
from bs4 import BeautifulSoup
import logging
import re
import time
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_PhysChemParameter(sequence, max_retries=3):
    """
    获取蛋白质序列的物理化学参数
    
    Args:
        sequence: 氨基酸序列
        max_retries: 最大重试次数
        
    Returns:
        dict: 包含物理化学参数的字典
    """
    # 如果序列为空，直接返回错误
    if not sequence or not sequence.strip():
        return {"error": "序列不能为空"}
    
    sequence = sequence.strip()
    
    # 检查序列是否只包含有效的氨基酸字符
    valid_aa = set("ACDEFGHIKLMNPQRSTVWY")
    if not all(aa.upper() in valid_aa for aa in sequence):
        logger.warning(f"序列包含非标准氨基酸字符: {sequence}")
    
    retry_count = 0
    while retry_count < max_retries:
        try:
            session = requests.Session()
            url = "https://web.expasy.org/cgi-bin/protparam/protparam"
            
            # 准备POST请求数据
            data = {
                "sequence": sequence
            }

            # 设置请求头
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Content-Type": "application/x-www-form-urlencoded"
            }
            
            logger.info(f"正在发送请求到 {url}")
            response = session.post(url, data=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"请求成功，状态码: {response.status_code}")
            
            # 解析返回的HTML并提取结果
            results = extract_protparam_results(response.text)
            
            if not results:
                if retry_count < max_retries - 1:
                    retry_count += 1
                    logger.info(f"正在进行第 {retry_count} 次重试...")
                    time.sleep(2)
                    continue
                return {"error": "未能从响应中提取到结果"}
            
            return results
            
        except (requests.exceptions.RequestException, Exception) as e:
            logger.error(f"请求错误: {str(e)}")
            if retry_count < max_retries - 1:
                retry_count += 1
                logger.info(f"正在进行第 {retry_count} 次重试...")
                time.sleep(2)
                continue
            return {"error": f"请求错误: {str(e)}"}
            
        finally:
            session.close()

def extract_protparam_results(html_content):
    """从ProtParam结果HTML中提取所有分析数据"""
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        results = {}
        
        # 查找包含结果的<pre>标签
        pre_blocks = soup.find_all('pre')
        if not pre_blocks:
            return {}
            
        main_pre = pre_blocks[-1]
        main_results = main_pre.get_text()
        
        # 提取基本信息
        patterns = {
            'amino_acid_count': r'Number of amino acids:\s*(\d+)',
            'molecular_weight': r'Molecular weight:\s*([\d\.]+)',
            'theoretical_pi': r'Theoretical pI:\s*([\d\.]+)',
            'negative_residues': r'negatively charged residues \(Asp \+ Glu\):\s*(\d+)',
            'positive_residues': r'positively charged residues \(Arg \+ Lys\):\s*(\d+)',
            'instability_index': r'The instability index \(II\) is computed to be\s*([\d\.]+)',
            'aliphatic_index': r'Aliphatic index:\s*([\d\.]+)',
            'gravy': r'Grand average of hydropathicity \(GRAVY\):\s*([-\d\.]+)'
        }
        
        for key, pattern in patterns.items():
            match = re.search(pattern, main_results)
            if match:
                results[key] = float(match.group(1))
        
        # 提取氨基酸组成
        aa_comp = {}
        aa_section = re.search(r'Amino acid composition:(.*?)Total number', main_results, re.DOTALL)
        if aa_section:
            aa_lines = aa_section.group(1).strip().split('\n')
            for line in aa_lines:
                match = re.match(r'([A-Za-z]+)\s+\(([A-Z])\)\s+(\d+)\s+([\d\.]+)', line)
                if match:
                    aa_name = f"{match.group(1)} ({match.group(2)})"
                    aa_count = int(match.group(3))
                    aa_percent = float(match.group(4))
                    aa_comp[aa_name] = {'count': aa_count, 'percent': aa_percent}
        results['amino_acid_composition'] = aa_comp

        # 提取消光系数
        extinction_coefficients = {}
        ext_section = re.search(r'Extinction coefficients:(.*?)Estimated half-life:', main_results, re.DOTALL)
        if ext_section:
            ext_text = ext_section.group(1)
            # 提取带有二硫键的系数
            cystine_match = re.search(r'Ext. coefficient\s+(\d+)[^>]+Abs 0.1%[^=]*=\s*([\d\.]+)', ext_text)
            if cystine_match:
                extinction_coefficients['cystines'] = {
                    'coefficient': float(cystine_match.group(1)),
                    'abs_01': float(cystine_match.group(2))
                }
            # 提取还原态的系数
            reduced_match = re.search(r'assuming all Cys residues are reduced(.*?)Ext. coefficient\s+(\d+)[^>]+Abs 0.1%[^=]*=\s*([\d\.]+)', ext_text, re.DOTALL)
            if reduced_match:
                extinction_coefficients['reduced'] = {
                    'coefficient': float(reduced_match.group(2)),
                    'abs_01': float(reduced_match.group(3))
                }
        results['extinction_coefficients'] = extinction_coefficients
        
        # 提取稳定性分类
        stability_match = re.search(r'This classifies the protein as\s*(\w+)', main_results)
        if stability_match:
            results['stability_classification'] = stability_match.group(1)
        
        # 提取半衰期
        half_life = {}
        half_life_section = re.search(r'Estimated half-life:(.*?)(?=\n\n)', main_results, re.DOTALL)
        if half_life_section:
            hl_text = half_life_section.group(1)
            # 提取N末端氨基酸
            n_term_match = re.search(r'The N-terminal of the sequence considered is ([A-Z])\s*\(([A-Za-z]+)\)', hl_text)
            if n_term_match:
                half_life['n_terminal'] = f"{n_term_match.group(1)} ({n_term_match.group(2)})"
            
            mammalian = re.search(r'(\d+|\>\d+)\s+hours\s*\(mammalian', hl_text)
            yeast = re.search(r'(\d+|\>\d+)\s+hours\s*\(yeast', hl_text)
            ecoli = re.search(r'(\d+|\>\d+)\s+hours\s*\(Escherichia', hl_text)
            
            if mammalian: half_life['mammalian'] = f"{mammalian.group(1)} hours"
            if yeast: half_life['yeast'] = f"{yeast.group(1)} hours"
            if ecoli: half_life['ecoli'] = f"{ecoli.group(1)} hours"
            
            if half_life:
                results['half_life'] = half_life
        
        return results
        
    except Exception as e:
        logger.error(f"解析HTML时出错: {str(e)}")
        return {}

def main():
    """主函数：提供交互式界面进行蛋白质序列分析"""
    print("\n=== 蛋白质物理化学参数分析工具 ===")
    '''print("请输入氨基酸序列，或输入 'q' 退出程序")'''
    print("示例序列: MKWVTFISLLFLFSSAYSRG")
    
    while True:
        sequence = input("\n请输入氨基酸序列: ").strip()
        
        '''if sequence.lower() == 'q':
            print("程序已退出")
            break'''
            
        if not sequence:
            print("序列不能为空，请重新输入")
            continue
            
        print("\n正在分析序列...")
        result = get_PhysChemParameter(sequence)
        
        if "error" in result:
            print(f"错误: {result['error']}")
            continue
            
        print("\n=== 分析结果 ===")
        print("基本信息:")
        print(f"  氨基酸数量: {result.get('amino_acid_count', '未知')}")
        print(f"  分子量: {result.get('molecular_weight', '未知'):.2f}")
        print(f"  理论等电点: {result.get('theoretical_pi', '未知'):.2f}")
        
        print("\n氨基酸组成:")
        if 'amino_acid_composition' in result:
            for aa, data in result['amino_acid_composition'].items():
                print(f"  {aa}: {data['count']} ({data['percent']}%)")
        
        print(f"\n带负电荷残基数量 (Asp + Glu): {result.get('negative_residues', '未知')}")
        print(f"带正电荷残基数量 (Arg + Lys): {result.get('positive_residues', '未知')}")
        
        if 'extinction_coefficients' in result:
            print("\n消光系数:")
            ext_coef = result['extinction_coefficients']
            if 'cystines' in ext_coef:
                print(f"  cystines: {ext_coef['cystines']['coefficient']} M⁻¹cm⁻¹ (Abs 0.1% = {ext_coef['cystines']['abs_01']})")
            if 'reduced' in ext_coef:
                print(f"  reduced: {ext_coef['reduced']['coefficient']} M⁻¹cm⁻¹ (Abs 0.1% = {ext_coef['reduced']['abs_01']})")
        
        if 'half_life' in result:
            print("\n估计半衰期:")
            half_life = result['half_life']
            if 'n_terminal' in half_life:
                print(f"  N末端氨基酸: {half_life['n_terminal']}")
            if 'mammalian' in half_life:
                print(f"  哺乳动物网织红细胞 (体外): {half_life['mammalian']}")
            if 'yeast' in half_life:
                print(f"  酵母 (体内): {half_life['yeast']}")
            if 'ecoli' in half_life:
                print(f"  大肠杆菌 (体内): {half_life['ecoli']}")
        
        if 'instability_index' in result:
            print(f"\n不稳定指数: {result['instability_index']:.2f}")
            print(f"蛋白质分类为: {result.get('stability_classification', '未知')}")
        
        if 'aliphatic_index' in result:
            print(f"脂肪族指数: {result['aliphatic_index']:.2f}")
        
        if 'gravy' in result:
            print(f"疏水性平均值 (GRAVY): {result['gravy']:.3f}")

if __name__ == "__main__":
    main()

