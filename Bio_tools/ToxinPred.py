import requests
from bs4 import BeautifulSoup
import re
import time
import os
import logging
import random
import string
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 确保临时目录存在
os.makedirs('temp', exist_ok=True)

def generate_session_id():
    """生成随机的PHP会话ID"""
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(26))

def follow_meta_refresh(response, session, headers, base_url="https://webs.iiitd.edu.in/raghava/toxinpred/"):
    """跟随HTML meta刷新重定向"""
    soup = BeautifulSoup(response.text, 'html.parser')
    meta_refresh = soup.find('meta', attrs={'http-equiv': re.compile(r'refresh', re.I)})
    
    if meta_refresh:
        content = meta_refresh.get('content', '')
        # 提取重定向URL
        match = re.search(r'url=([^"\']+)', content, re.I)
        if match:
            redirect_url = match.group(1).strip()
            # 如果是相对URL，则构建完整URL
            if not redirect_url.startswith(('http://', 'https://')):
                redirect_url = base_url + redirect_url
            
            logger.info(f"跟随meta刷新重定向到: {redirect_url}")
            # 发送GET请求到重定向URL
            time.sleep(1)  # 稍微等待一下，避免请求过于频繁
            return session.get(redirect_url, headers=headers, timeout=30)
    
    return response

def predict_toxin(sequence, verbose=True):
    """
    使用ToxinPred预测序列的毒性
    
    Args:
        sequence (str): 需要预测的氨基酸序列
        verbose (bool): 是否显示详细日志
        
    Returns:
        dict: 预测结果
    """
    # 设置日志级别
    if not verbose:
        logger.setLevel(logging.WARNING)
    else:
        logger.setLevel(logging.INFO)
        
    # 清理序列（去除FASTA头）
    if sequence.startswith(">"):
        lines = sequence.split("\n")
        seq_id = lines[0][1:].strip()  # 获取序列ID
        sequence = "\n".join(lines[1:]).strip()
    else:
        seq_id = "seq1"  # 默认序列ID
    
    # 替换非标准字符和空白
    sequence = sequence.strip().replace(' ', '').replace('\n', '').replace('\r', '')
    
    if verbose:
        logger.info(f"开始预测序列: {sequence}")
    
    # 设置请求头，模拟浏览器
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0"
    }
    
    # 创建会话
    session = requests.Session()
    
    # 设置Cookie
    session.cookies.set("PHPSESSID", generate_session_id(), domain="webs.iiitd.edu.in")
    
    try:
        # 1. 首先访问主页获取必要的Cookie和会话
        if verbose:
            logger.info("访问ToxinPred主页...")
        base_url = "https://webs.iiitd.edu.in/raghava/toxinpred/"
        main_page = session.get(base_url, headers=headers, timeout=30)
        if main_page.status_code != 200:
            logger.error(f"访问主页失败，状态码: {main_page.status_code}")
            return {"success": False, "error": f"访问主页失败，状态码: {main_page.status_code}"}
        
        # 2. 访问提交页面
        if verbose:
            logger.info("访问提交页面...")
        submit_page_url = base_url + "multi_submit.php"
        submit_page = session.get(submit_page_url, headers=headers, timeout=30)
        if submit_page.status_code != 200:
            logger.error(f"访问提交页面失败，状态码: {submit_page.status_code}")
            return {"success": False, "error": f"访问提交页面失败，状态码: {submit_page.status_code}"}
        
        # 3. 构建POST请求数据
        # 准备FASTA格式的序列
        fasta_sequences = f">{seq_id}\n{sequence}"
        
        # 定义POST数据
        form_data = {
            "seq": fasta_sequences,  # 使用seq字段而不是SEQPASTE
            "method": "1",  # SVM (Swiss-Prot) based
            "thval": "0.0",  # 默认阈值
            "field[]": ["4", "7", "9", "11", "13"],  # 选择一些物理化学特性
            "checkAll": "all"
        }
        
        if verbose:
            logger.info(f"提交数据: {form_data}")
        
        # 4. 发送POST请求到表单目标URL (multiple_test.php)
        if verbose:
            logger.info("提交序列预测请求...")
        post_url = base_url + "multiple_test.php"
        response = session.post(post_url, data=form_data, headers=headers, timeout=60)
        
        # 5. 跟随meta刷新重定向
        if verbose:
            logger.info("检查是否有meta刷新重定向...")
        response = follow_meta_refresh(response, session, headers, base_url)
        
        # 检查是否需要多次跟随重定向
        max_redirects = 5
        redirect_count = 1
        
        while redirect_count < max_redirects:
            soup = BeautifulSoup(response.text, 'html.parser')
            meta_refresh = soup.find('meta', attrs={'http-equiv': re.compile(r'refresh', re.I)})
            
            if meta_refresh:
                if verbose:
                    logger.info(f"发现第 {redirect_count+1} 个重定向...")
                response = follow_meta_refresh(response, session, headers, base_url)
                redirect_count += 1
            else:
                break
                
        if verbose:
            logger.info(f"完成了 {redirect_count} 次重定向")
        
        # 6. 解析响应
        if response.status_code != 200:
            logger.error(f"获取结果失败，状态码: {response.status_code}")
            return {"success": False, "error": f"获取结果失败，状态码: {response.status_code}"}
        
        if verbose:
            logger.info("开始解析响应结果...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找结果表格（正则表达式匹配表格ID，因为可能是table, tableTwo或其他）
        results_table = None
        for table in soup.find_all('table'):
            table_id = table.get('id', '')
            if re.search(r'table', table_id, re.I):
                results_table = table
                if verbose:
                    logger.info(f"找到结果表格，ID: {table_id}")
                break
        
        # 如果没有找到带ID的表格，尝试查找所有表格
        if not results_table:
            tables = soup.find_all('table')
            for i, table in enumerate(tables):
                # 查找表格中是否包含"Peptide ID"或"Sequence"等关键词
                table_text = table.text.lower()
                if any(keyword in table_text for keyword in ["peptide id", "sequence", "svm score", "prediction"]):
                    results_table = table
                    if verbose:
                        logger.info(f"通过关键词找到疑似结果表格 (第{i+1}个表格)")
                    break
        
        if not results_table and tables:
            # 如果仍然没找到，但有表格存在，使用第一个表格
            results_table = tables[0]
            if verbose:
                logger.info(f"未能通过ID或关键词找到表格，使用第一个表格")
        
        if not results_table:
            logger.error("未找到任何表格，检查HTML源码...")
            # 检查是否有错误消息
            error_msg = soup.find(string=re.compile(r'[Ee]rror|[Ff]ailed|[Ii]nvalid'))
            if error_msg:
                logger.error(f"可能的错误信息: {error_msg}")
                return {"success": False, "error": f"服务器返回错误: {error_msg}"}
            return {"success": False, "error": "未找到结果表格"}
        
        # 尝试提取表头和结果数据
        try:
            # 首先尝试查找表头行
            if results_table.find('thead'):
                headers_row = results_table.find('thead').find_all('tr')[-1]
            else:
                # 如果没有thead，尝试找第一行作为表头
                headers_row = results_table.find_all('tr')[0]
            
            # 提取表头
            headers = []
            for th in headers_row.find_all(['th', 'td']):
                header_text = th.text.strip()
                if header_text:
                    headers.append(header_text)
            
            if verbose:
                logger.info(f"提取到表头: {headers}")
            
            # 如果表头为空，尝试使用一些默认表头
            if not headers:
                headers = ["Peptide ID", "Peptide Sequence", "SVM Score", "Prediction"]
                logger.warning(f"未找到表头，使用默认表头: {headers}")
            
            # 提取结果行
            results = []
            # 查找tbody或直接处理表格中的行
            rows = results_table.find('tbody').find_all('tr') if results_table.find('tbody') else results_table.find_all('tr')[1:]
            
            for row in rows:
                cells = row.find_all('td')
                if not cells:
                    continue
                
                result = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        header_name = headers[i].replace('\n', ' ').strip()
                        result[header_name] = cell.text.strip()
                    else:
                        # 如果单元格数量超过表头数量，使用索引作为键
                        result[f"Column_{i}"] = cell.text.strip()
                
                if result:  # 只添加非空结果
                    results.append(result)
            
            if verbose:
                logger.info(f"提取到 {len(results)} 个结果")
            
            # 提取Job ID
            job_id = None
            job_id_text = soup.find(string=re.compile(r'Your job id is \d+'))
            if job_id_text:
                job_id_match = re.search(r'Your job id is (\d+)', job_id_text)
                if job_id_match:
                    job_id = job_id_match.group(1)
                    if verbose:
                        logger.info(f"找到Job ID: {job_id}")
            
            # 查找与输入序列匹配的结果
            matching_results = []
            for r in results:
                result_seq = r.get('Peptide Sequence', '')
                # 清理序列中的空白
                result_seq = result_seq.strip().replace(' ', '')
                if sequence == result_seq:
                    matching_results.append(r)
                    
            if matching_results:
                target_results = matching_results
                if verbose:
                    logger.info(f"找到匹配序列的结果: {len(matching_results)}个")
            else:
                target_results = results
                logger.warning(f"未找到与输入序列完全匹配的结果，返回所有结果: {len(results)}个")
            
            return {
                "success": True,
                "job_id": job_id,
                "results": target_results,
                "all_results": results
            }
        except Exception as e:
            logger.error(f"解析表格时出错: {str(e)}", exc_info=True)
            return {"success": False, "error": f"解析表格时出错: {str(e)}"}
        
    except Exception as e:
        logger.error(f"预测过程中出错: {str(e)}", exc_info=True)
        return {"success": False, "error": f"预测过程中出错: {str(e)}"}

def format_results(results):
    """格式化结果输出"""
    if not results.get("success"):
        return f"预测失败: {results.get('error', '未知错误')}"
    
    output = []
    output.append(f"Job ID: {results.get('job_id', 'N/A')}")
    output.append("\n预测结果:")
    
    for i, result in enumerate(results.get("results", [])):
        output.append(f"\n结果 {i+1}:")
        for key, value in result.items():
            if key and value:  # 只显示非空值
                output.append(f"  {key}: {value}")
    
    return "\n".join(output)

def read_fasta(file_path):
    """读取FASTA文件"""
    sequences = []
    current_seq = None
    current_id = None
    
    with open(file_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('>'):
                # 如果已经有一个序列在处理中，保存它
                if current_seq and current_id:
                    sequences.append((current_id, current_seq))
                
                # 开始一个新序列
                current_id = line[1:]
                current_seq = ""
            else:
                # 将行添加到当前序列
                if current_seq is not None:
                    current_seq += line
    
    # 添加最后一个序列
    if current_seq and current_id:
        sequences.append((current_id, current_seq))
    
    return sequences

def predict_batch(sequences, output_file=None, num_workers=3, verbose=False):
    """批量预测多个序列"""
    results = []
    failed = []
    
    # 使用多线程提高效率
    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        future_to_seq = {executor.submit(predict_toxin, seq, verbose): (seq_id, seq) for seq_id, seq in sequences}
        
        for future in as_completed(future_to_seq):
            seq_id, seq = future_to_seq[future]
            try:
                result = future.result()
                if result.get("success"):
                    print(f"序列 {seq_id} 预测成功")
                    # 添加序列ID到结果中
                    result["sequence_id"] = seq_id
                    results.append(result)
                else:
                    print(f"序列 {seq_id} 预测失败: {result.get('error')}")
                    failed.append((seq_id, seq, result.get('error')))
            except Exception as e:
                print(f"处理序列 {seq_id} 时出错: {str(e)}")
                failed.append((seq_id, seq, str(e)))
    
    # 保存结果到文件
    if output_file:
        save_results_to_file(results, failed, output_file)
    
    return results, failed

def save_results_to_file(results, failed, output_file):
    """保存结果到文件"""
    with open(output_file, 'w') as f:
        f.write("序列ID\t肽序列\tSVM得分\t预测结果\t其他特性\n")
        
        for result in results:
            for res in result.get("results", []):
                row = [
                    result.get("sequence_id", "unknown"),
                    res.get("Peptide Sequence", ""),
                    res.get("SVM Score", ""),
                    res.get("Prediction", "")
                ]
                
                # 添加其他特性
                other_props = []
                for key, value in res.items():
                    if key not in ["Peptide ID", "Peptide Sequence", "SVM Score", "Prediction"]:
                        other_props.append(f"{key}:{value}")
                
                row.append("; ".join(other_props))
                f.write("\t".join(row) + "\n")
        
        if failed:
            f.write("\n\n失败的序列:\n")
            f.write("序列ID\t序列\t错误原因\n")
            for seq_id, seq, error in failed:
                f.write(f"{seq_id}\t{seq}\t{error}\n")

def predict_toxicity(sequence):
    """预测肽序列的毒性，返回结果和特征"""
    try:
        logger.info(f"开始预测序列的毒性: {sequence}")
        logger.info("尝试使用主要预测函数...")
        result = predict_toxin(sequence, verbose=True)
        logger.info(f"主要预测函数返回: {result}")

        if result and result.get('success'):
            logger.info(f"主要预测成功，提取结果")
            first_result = result['results'][0]
            prediction = first_result.get('Prediction', 'Unknown')
            svm_score = first_result.get('SVM Score', '0.0')
            
            try:
                svm_score = float(svm_score)
            except (ValueError, TypeError):
                svm_score = 0.0
                
            # 修复is_toxin的逻辑判断
            is_toxin = prediction.lower() == "toxin" or "toxin" in prediction.lower()
            
            # 不要将Non-Toxin判断为Toxin
            if "non-toxin" in prediction.lower():
                is_toxin = False
                
            return {
                'svm_score': svm_score,
                'result': prediction,
                'is_toxin': is_toxin,
                'features': {
                    'Hydrophobicity': first_result.get('Hydrophobicity', 'N/A'),
                    'Hydropathicity': first_result.get('Hydropathicity', 'N/A'),
                    'Hydrophilicity': first_result.get('Hydrophilicity', 'N/A'),
                    'Charge': first_result.get('Charge', 'N/A'),
                    'Mol wt': first_result.get('Mol wt', 'N/A')
                }
            }
        else:
            logger.warning("主要预测失败，尝试备用方法")
            # ... 其余代码保持不变 ...
    except Exception as e:
        logger.error(f"预测过程中出错: {str(e)}")
        return None

if __name__ == "__main__":
    # 简化版本，直接提示用户输入序列
    print("\n欢迎使用ToxinPred肽序列毒性预测工具！")
    print("=======================================")
    print("请输入氨基酸序列:")
    
    user_input = input("\n> ").strip()
    
    if not user_input:
        print("序列不能为空，程序退出。")
    else:
        print(f"\n开始预测序列: {user_input}")
        results = predict_toxin(user_input, verbose=True)
        formatted_output = format_results(results)
        print(formatted_output)
    
    print("\n预测完成，程序已退出。")
