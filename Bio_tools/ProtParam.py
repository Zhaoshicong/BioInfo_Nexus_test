import requests
from bs4 import BeautifulSoup  # 导入BeautifulSoup而不是bs4模块
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_molecular_weight(sequence):
    try:
        # ProtParam网址
        url = "https://web.expasy.org/cgi-bin/protparam/protparam"
        
        # 准备POST请求数据
        data = {
            "sequence": sequence
        }
        
        # 发送POST请求，设置30秒超时
        response = requests.post(url, data=data, timeout=30)
        response.raise_for_status()
        
        # 使用BeautifulSoup解析返回的HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 查找分子量信息
        molecular_weight = None
        pre_tags = soup.find_all('pre')
        for pre in pre_tags:
            if "Molecular weight" in pre.text:
                # 提取分子量数值
                mw_line = [line for line in pre.text.split('\n') if "Molecular weight" in line][0]
                molecular_weight = mw_line.split()[-1].strip()
                break
        
        if molecular_weight:
            return {
                "sequence": sequence,
                "molecular_weight": molecular_weight
            }
        else:
            logger.error("无法获取分子量信息")
            return {"error": "无法获取分子量信息"}
        
    except requests.exceptions.Timeout:
        logger.error("ProtParam请求超时")
        return {"error": "请求超时，请稍后重试"}
    except requests.exceptions.ConnectionError:
        logger.error("ProtParam连接错误")
        return {"error": "网络连接错误，请检查您的网络连接"}
    except requests.exceptions.RequestException as e:
        logger.error(f"ProtParam请求错误: {str(e)}")
        return {"error": f"请求错误: {str(e)}"}
    except Exception as e:
        logger.error(f"ProtParam处理错误: {str(e)}")
        return {"error": f"处理错误: {str(e)}"}

if __name__ == "__main__":
    # 测试用例
    sequence = "MAEGEITTFTALTEKFNLPPGNYKKPKLLYCSNG"
    result = get_molecular_weight(sequence)
    print(result)
