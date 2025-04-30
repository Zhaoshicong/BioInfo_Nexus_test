"""
Bio_tools/AI_service.py
集成阿里云通义千问API来处理多个工具分析结果，根据用户的自然语言需求生成定制化报告
"""

import os
import json
import logging
from dotenv import load_dotenv
import requests
from typing import Dict, List, Any, Union
from openai import OpenAI

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载环境变量
load_dotenv()

class AIService:
    """AI服务类，用于处理生物信息学工具的分析结果并生成定制化报告"""
    
    def __init__(self):
        """初始化AI服务"""
        # 从环境变量获取API密钥
        self.api_key = os.environ.get("DASHSCOPE_API_KEY")
        self.base_url = os.environ.get("DASHSCOPE_BASE_URL")
        self.api_model = os.environ.get("DASHSCOPE_MODEL")
        
        if not self.api_key:
            logger.warning("未找到阿里云通义千问API密钥，AI服务将无法正常工作")
        
        # 初始化OpenAI客户端，使用通义千问的兼容接口
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"成功初始化AI客户端，使用模型: {self.api_model}")
        except Exception as e:
            logger.error(f"初始化AI客户端失败: {str(e)}")
            self.client = None
    
    def process_analysis_results(self, tools_results: Dict[str, Any], user_query: str) -> Dict[str, Any]:
        """
        处理多个工具的分析结果，生成定制化报告
        
        参数:
            tools_results (Dict[str, Any]): 多个工具的分析结果字典，键为工具名，值为工具的分析结果
            user_query (str): 用户的自然语言查询/需求
            
        返回:
            Dict[str, Any]: 包含AI生成报告的结果字典
        """
        if not self.api_key or not self.client:
            return {"success": False, "error": "未配置阿里云通义千问API密钥或客户端初始化失败"}
        
        try:
            # 准备发送给AI的消息
            messages = self._prepare_messages(tools_results, user_query)
            
            # 调用AI API
            response = self._call_ai_api(messages)
            
            # 处理AI响应
            return {
                "success": True,
                "report": response,
                "original_results": tools_results,
                "user_query": user_query
            }
            
        except Exception as e:
            logger.error(f"AI处理分析结果时出错: {str(e)}")
            return {
                "success": False,
                "error": f"AI处理失败: {str(e)}",
                "original_results": tools_results
            }
    
    def _prepare_messages(self, tools_results: Dict[str, Any], user_query: str) -> List[Dict[str, str]]:
        """
        准备发送给AI API的messages
        
        参数:
            tools_results (Dict[str, Any]): 多个工具的分析结果
            user_query (str): 用户查询
            
        返回:
            List[Dict[str, str]]: AI API所需的消息格式
        """
        # 将工具结果转为JSON字符串
        tools_results_json = json.dumps(tools_results, ensure_ascii=False, indent=2)
        
        # 构建系统提示
        system_prompt = """
你是一位专业的生物信息学分析助手，需要基于提供的各种生物信息学工具的分析结果，根据用户的特定需求生成定制报告。
请分析所有提供的结果数据，理解其中的关联，并以专业、连贯且易于理解的方式呈现关键发现。

遵循以下指南：
1. 保持科学准确性，只基于提供的数据做出结论
2. 以专业但清晰的语言解释发现
3. 根据用户的具体需求组织信息，突出相关内容
4. 使用结构化格式提高可读性
5. 提供专业的解释和背景知识
6. 如果数据不足以回答用户的特定问题，请明确指出
7. 禁止使用markdown格式输出
8. 采用分级标题，关键数据用数字编号条目呈现段落间空一行保持间距
9. 总是用中文回答
"""

        # 构建用户指令
        user_prompt = f"""
用户需求: {user_query}

分析工具结果:
```json
{tools_results_json}
```

请根据以上分析结果和用户需求，生成一份专业、全面的分析报告。
"""

        # 返回消息列表
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def _call_ai_api(self, messages: List[Dict[str, str]]) -> str:
        """
        调用阿里云通义千问API
        
        参数:
            messages (List[Dict[str, str]]): 消息列表
            
        返回:
            str: AI生成的响应文本
        """
        try:
            # 使用OpenAI客户端兼容接口调用通义千问
            completion = self.client.chat.completions.create(
                model=self.api_model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000
            )
            
            # 从响应中提取生成的文本
            response_text = completion.choices[0].message.content
            logger.info("AI API调用成功")
            return response_text
            
        except Exception as e:
            logger.error(f"调用AI API失败: {str(e)}")
            raise Exception(f"API请求异常: {str(e)}")


# 创建服务实例
ai_service = AIService()


def generate_report(tools_results: Dict[str, Any], user_query: str) -> Dict[str, Any]:
    """
    生成报告的便捷函数，供外部调用
    
    参数:
        tools_results (Dict[str, Any]): 多个工具的分析结果
        user_query (str): 用户查询
        
    返回:
        Dict[str, Any]: 包含AI生成报告的结果
    """
    return ai_service.process_analysis_results(tools_results, user_query) 