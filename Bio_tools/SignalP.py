import requests
from bs4 import BeautifulSoup
import re
import time
import webbrowser
import logging
import os
import shutil
import uuid

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 全局变量，控制是否生成调试文件
DEBUG_MODE = False  # 设置为False以减少调试文件的生成

def submit_sequence(sequence):
    """提交氨基酸序列到SignalP服务并返回JobID"""
    # 确保temp目录存在
    os.makedirs('temp', exist_ok=True)
    
    url = "https://services.healthtech.dtu.dk/services/SignalP-4.1/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    try:
        session = requests.Session()
        initial_response = session.get(url, headers=headers, timeout=30)

        # 只在调试模式下保存初始响应
        if DEBUG_MODE:
            with open('temp/initial_response.html', 'w', encoding='utf-8') as f:
                f.write(initial_response.text)
            logger.info("已保存初始响应页面")

        soup = BeautifulSoup(initial_response.text, 'html.parser')
        form = soup.find('form')

        if not form:
            logger.error("无法找到表单！")
            return None, None

        form_data = {}
        for input_tag in form.find_all(['input', 'select']):
            name = input_tag.get('name')
            if name:
                if input_tag.name == 'select':
                    selected_option = input_tag.find('option', selected=True)
                    value = selected_option.get('value', '') if selected_option else ''
                else:
                    value = input_tag.get('value', '')
                form_data[name] = value

        if sequence.startswith(">"):
            # 如果序列包含FASTA头，去掉头并保留纯序列
            sequence = "\n".join(sequence.split("\n")[1:]).strip()

        form_data['SEQPASTE'] = sequence
        form_data['orgtype'] = 'euk'
        form_data['method'] = 'best'
        form_data['format'] = 'long'

        # 记录表单数据
        logger.info(f"表单数据: {form_data}")

        submit_url = url
        form_action = form.get('action', '')
        if form_action:
            if form_action.startswith('/'):
                submit_url = f"https://services.healthtech.dtu.dk{form_action}"
            elif not form_action.startswith('http'):
                submit_url = f"{url.rsplit('/', 1)[0]}/{form_action}"
            else:
                submit_url = form_action

        logger.info(f"提交URL: {submit_url}")
        response = session.post(submit_url, data=form_data, headers=headers, allow_redirects=True, timeout=30)

        # 只在调试模式下保存提交响应
        if DEBUG_MODE:
            with open('temp/submit_response.html', 'w', encoding='utf-8') as f:
                f.write(response.text)
            logger.info(f"已保存提交响应页面，URL: {response.url}")

        jobid = None
        if 'jobid=' in response.url:
            jobid_match = re.search(r'jobid=([A-F0-9]+)', response.url)
            if jobid_match:
                jobid = jobid_match.group(1)
                logger.info(f"从URL中提取到JobID: {jobid}")

        if not jobid:
            jobid_pattern = re.compile(r'jobid=([A-F0-9]+)')
            for match in jobid_pattern.finditer(response.text):
                jobid = match.group(1)
                logger.info(f"从响应文本中提取到JobID: {jobid}")
                break

        if not jobid:
            logger.error("无法获取JobID")
            return None, None

        return jobid, session
    except Exception as e:
        logger.error(f"提交序列时发生错误: {str(e)}")
        return None, None

def extract_and_parse_results(jobid, session):
    """从结果页面提取并解析预测结果，并下载图像"""
    # 创建临时目录（如果不存在）
    os.makedirs('temp', exist_ok=True)
    
    # 使用与独立脚本相同的方法
    result_url = f"https://services.healthtech.dtu.dk/cgi-bin/webface2.cgi?jobid={jobid}&wait=20"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    }

    logger.info(f"访问结果页面: {result_url}")
    
    # 初始等待
    logger.info("等待10秒让服务器处理请求...")
    time.sleep(10)  # 设置为10秒
    
    # 尝试获取结果
    max_attempts = 15  # 增加尝试次数
    attempt = 1
    
    while attempt <= max_attempts:
        try:
            logger.info(f"尝试 {attempt}/{max_attempts} 获取结果")
            response = session.get(result_url, headers=headers, timeout=30)
            
            # 检查是否仍在处理
            if "Please wait" in response.text or "Job in progress" in response.text:
                logger.info("任务仍在处理中，等待10秒...")  # 减少等待时间
                time.sleep(10)
                attempt += 1
                continue
                
            # 只在调试模式下保存响应内容
            if DEBUG_MODE:
                debug_file = f"temp/signalp_response_{jobid}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(response.text)
                logger.info(f"已保存响应内容到 {debug_file}")
            
            # 提取预测结果文本
            soup = BeautifulSoup(response.text, 'html.parser')
            result_signal = None
            
            # 查找预测结果文本 - 使用多种方法
            # 方法1: 查找pre标签
            pre_tags = soup.find_all('pre')
            for pre in pre_tags:
                if 'Name=Sequence' in pre.text:
                    result_signal = pre.text.strip()
                    logger.info(f"方法1找到预测结果文本: {result_signal[:50]}...")
                    break
            
            # 方法2: 直接从HTML中提取包含"Name=Sequence"的文本
            if not result_signal:
                logger.info("尝试方法2提取预测结果文本...")
                pattern = r'Name=Sequence\s+SP=\'[^\']+\'\s+D=[0-9.]+\s+D-cutoff=[0-9.]+\s+Networks=[^\s]+'
                match = re.search(pattern, response.text)
                if match:
                    result_signal = match.group(0)
                    logger.info(f"方法2找到预测结果文本: {result_signal}")
            
            # 方法3: 提取整个包含预测结果的部分
            if not result_signal:
                logger.info("尝试方法3提取预测结果文本...")
                pattern = r'# pos\s+aa\s+C\s+S\s+Y[\s\S]+?Name=Sequence\s+SP=\'[^\']+\'\s+D=[0-9.]+'
                match = re.search(pattern, response.text)
                if match:
                    result_signal = match.group(0)
                    logger.info(f"方法3找到预测结果文本: {result_signal[:50]}...")
            
            # 查找图像URL - 使用从成功示例中学到的方法
            img_url = None
            
            # 方法1: 从响应文本中提取临时目录ID
            temp_dir_match = re.search(r'tmp/(\d+)/Sequence\.png', response.text)
            if temp_dir_match:
                temp_dir = temp_dir_match.group(1)
                img_url = f"https://services.healthtech.dtu.dk/services/SignalP-4.1/tmp/{temp_dir}/Sequence.png"
                logger.info(f"方法1找到图像URL: {img_url}")
            
            # 方法2: 直接查找图像标签
            if not img_url:
                logger.info("尝试方法2查找图像URL...")
                img_tags = soup.find_all('img')
                for img in img_tags:
                    src = img.get('src', '')
                    if src and ('.png' in src.lower() or '.gif' in src.lower()):
                        # 构建完整URL
                        if src.startswith('/'):
                            img_url = f"https://services.healthtech.dtu.dk{src}"
                        elif src.startswith('http'):
                            img_url = src
                        else:
                            img_url = f"https://services.healthtech.dtu.dk/services/SignalP-4.1/{src}"
                        
                        logger.info(f"方法2找到图像URL: {img_url}")
                        break
            
            # 方法3: 从响应文本中提取图像URL
            if not img_url:
                logger.info("尝试方法3查找图像URL...")
                img_patterns = [
                    r'src="([^"]*\.png)"',
                    r'src="([^"]*\.gif)"',
                    r'src="(/services/SignalP[^"]*)"',
                    r'src="(/tmp/[^"]*)"'
                ]
                
                for pattern in img_patterns:
                    matches = re.findall(pattern, response.text)
                    if matches:
                        for match in matches:
                            if match.startswith('/'):
                                img_url = f"https://services.healthtech.dtu.dk{match}"
                            elif match.startswith('http'):
                                img_url = match
                            else:
                                img_url = f"https://services.healthtech.dtu.dk/services/SignalP-4.1/{match}"
                            logger.info(f"方法3找到图像URL: {img_url}")
                            break
                        if img_url:
                            break
            
            # 如果找到图像URL，尝试下载图像
            if img_url:
                try:
                    logger.info(f"尝试下载图像: {img_url}")
                    img_response = session.get(img_url, headers=headers, timeout=30)
                    
                    if img_response.status_code == 200:
                        # 检查内容类型
                        content_type = img_response.headers.get('Content-Type', '')
                        logger.info(f"图像内容类型: {content_type}")
                        
                        if content_type.startswith('image/') or len(img_response.content) > 1000:
                            # 保存图像 - 只保存到temp目录，不再额外保存到当前目录
                            img_filename = f"temp/Sequence_{jobid}.png"
                            with open(img_filename, "wb") as f:
                                f.write(img_response.content)
                            logger.info(f"图像已保存为 {img_filename}")
                            
                            # 返回成功结果
                            return {
                                "success": True,
                                "image_path": img_filename,
                                "result_text": result_signal or "无详细预测文本"
                            }
                        else:
                            logger.warning(f"下载的内容不是图像: {content_type}")
                    else:
                        logger.error(f"图像下载失败，状态码: {img_response.status_code}")
                except Exception as e:
                    logger.error(f"下载图像失败: {str(e)}")
            
            # 如果没有找到有效图像，但找到了预测结果文本，也返回成功
            if result_signal:
                logger.info("找到预测结果文本，但未找到图像，仍返回成功")
                return {
                    "success": True,
                    "image_path": None,
                    "result_text": result_signal
                }
            
            # 如果没有找到有效图像和预测结果，尝试下一次
            logger.warning("未找到有效图像和预测结果，等待10秒后重试...")
            time.sleep(10)
            attempt += 1
            
        except Exception as e:
            logger.error(f"获取结果时出错: {str(e)}")
            time.sleep(10)
            attempt += 1
    
    # 如果所有尝试都失败，返回错误信息
    return {
        "success": False,
        "error": "无法获取预测结果，请稍后重试"
    }

# 独立运行时的主程序
if __name__ == "__main__":
    # 在独立运行时启用调试模式
    DEBUG_MODE = True
    
    sequence = input("请输入氨基酸序列:\n").strip()
    
    print("正在提交序列...")
    jobid, session = submit_sequence(sequence)
    
    if jobid:
        print(f"获取到JobID: {jobid}")
        print("等待服务器处理序列...")
        
        result = extract_and_parse_results(jobid, session)
        
        if result["success"]:
            if result["image_path"]:
                print(f"分析成功! 图像已保存为: {result['image_path']}")
            else:
                print("分析成功，但未能获取图像")
            print(f"预测结果: {result['result_text']}")
        else:
            print(f"分析失败: {result['error']}")
            
            # 提供手动选项
            result_url = f"https://services.healthtech.dtu.dk/cgi-bin/webface2.cgi?jobid={jobid}&wait=20"
            open_browser = input("\n是否在浏览器中打开结果页面? (y/n): ").strip().lower()
            if open_browser == 'y':
                print("正在打开浏览器...")
                webbrowser.open(result_url)
    else:
        print("获取JobID失败，无法继续。")