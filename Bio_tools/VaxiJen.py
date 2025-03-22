import requests
import re
from bs4 import BeautifulSoup
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_vaxijen_result(protein_sequence):
    try:
        # 正确的表单提交URL
        form_action = "https://ddg-pharmfac.net/vaxijen/scripts/VaxiJen_scripts/VaxiJen3.pl"

        # 准备表单数据 - 使用您提供的实际字段名称
        form_data = {
            'seq': protein_sequence.strip(),  # 添加蛋白序列
            'uploaded_file': '',
            'Verbose': 'A',
            'SequenceOnOff': 'A',
            'SummaryMode': 'A',
            'threshold': '0.4',  # 设置阈值
            'submit': 'Submit',
            'Target': 'bacteria'
        }

        # 将表单数据转换为multipart/form-data格式
        files = {}
        for key, value in form_data.items():
            files[key] = (None, value)

        # 添加适当的请求头
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Referer": "https://ddg-pharmfac.net/vaxijen/VaxiJen/VaxiJen.html"
        }

        # 发送POST请求，设置30秒超时
        response = requests.post(form_action, files=files, headers=headers, timeout=30)

        # 保存响应以便调试
        #with open("temp/VaxiJen_response.html", "w", encoding="utf-8") as f:
        #    f.write(response.text)
        
        # 打印调试日志
        logger.info(f"VaxiJen响应状态码: {response.status_code}")
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # 方法2: 使用正则表达式从整个HTML中提取概率值
        # 修改正则表达式，调整匹配模式
        prob_match = re.search(r"Overall Prediction for the Protective Antigen =<b>\s*([-+]?\d*\.?\d+)\s*</b>", response.text, re.IGNORECASE)
        result_match = re.search(r"<FONT COLOR=\"#0000FF\">(NON-ANTIGEN|ANTIGEN)</font>", response.text, re.IGNORECASE)

        if prob_match and result_match:
            probability = prob_match.group(1).strip()
            result = result_match.group(1)
            logger.info(f"通过正则表达式1找到 - 概率: {probability}, 结果: {result}")
            return result, probability

        # 方法3: 尝试不同的正则表达式
        prob_match = re.search(r"Overall Prediction for the Protective Antigen =.+?<b>\s*([-+]?\d*\.?\d+)\s*</b>", response.text, re.DOTALL | re.IGNORECASE)
        result_match = re.search(r"<FONT COLOR=\"#0000FF\">(NON-ANTIGEN|ANTIGEN)</FONT>", response.text, re.IGNORECASE)
        
        if prob_match and result_match:
            probability = prob_match.group(1).strip()
            result = result_match.group(1)
            logger.info(f"通过正则表达式2找到 - 概率: {probability}, 结果: {result}")
            return result, probability

        # 方法4: 尝试使用BeautifulSoup查找元素
        b_tags = soup.find_all('b')
        for b in b_tags:
            text = b.get_text().strip()
            if re.match(r"^[-+]?\d*\.?\d+$", text):
                probability = text
                # 查找结果
                font_tags = soup.find_all('font', {'color': re.compile(r'#0000FF', re.IGNORECASE)})
                for font in font_tags:
                    font_text = font.get_text().strip().upper()
                    if font_text in ["ANTIGEN", "NON-ANTIGEN"]:
                        result = font_text
                        logger.info(f"通过BeautifulSoup找到 - 概率: {probability}, 结果: {result}")
                        return result, probability

        # 记录未能提取数据的信息
        logger.error("无法从响应中提取数据")
        # 保存响应内容以供调试
        with open("temp/VaxiJen_error_response.html", "w", encoding="utf-8") as f:
            f.write(response.text)
        
        return None, None

    except requests.exceptions.Timeout:
        logger.error("VaxiJen请求超时")
        return None, None
    except requests.exceptions.ConnectionError:
        logger.error("VaxiJen连接错误")
        return None, None
    except Exception as e:
        logger.error(f"VaxiJen分析发生错误: {str(e)}")
        return None, None


def main():
    protein_sequence = input("请输入蛋白序列: ")
    result, probability = get_vaxijen_result(protein_sequence)

    if result and probability:
        print(f"Overall Prediction for the Protective Antigen: {probability}")
        print(f"结果: {result}")
    else:
        print("未能获取有效结果。")


if __name__ == "__main__":
    main()
    #https://www.ddg-pharmfac.net/vaxiien/Vaxien/Vaxien.html