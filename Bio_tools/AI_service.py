"""
Bio_tools/AI_service.py
集成阿里云通义千问API来处理多个工具分析结果，根据用户的自然语言需求生成定制化报告
"""

import os
import json
import logging
import threading
import time
import hashlib
import pickle
from concurrent.futures import ThreadPoolExecutor, TimeoutError, as_completed, Future
from typing import Dict, List, Any, Union, Optional, Callable
from dotenv import load_dotenv
import requests
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
        
        # 初始化线程池
        self.max_workers = 5  # 最大5个并发AI请求
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # 初始化缓存系统
        self.cache = {}
        self.cache_expiry = {}
        self.cache_ttl = 3600  # 缓存1小时
        self.cache_lock = threading.Lock()
        
        # 并发控制
        self.active_requests = 0
        self.max_concurrent_requests = 10
        self.request_lock = threading.Lock()
        
        # 请求取消支持
        self.active_futures = {}
        self.request_counter = 0
        
        # 异步任务存储（文件系统，支持多进程共享）
        self.tasks_dir = "/tmp/bioinfo_ai_tasks"
        os.makedirs(self.tasks_dir, exist_ok=True)
        
        # 初始化OpenAI客户端，使用通义千问的兼容接口
        try:
            # 尝试标准方式初始化
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=90.0  # 90秒超时
            )
            logger.info(f"成功初始化AI客户端，使用模型: {self.api_model}")
        except TypeError as e:
            error_msg = str(e).lower()
            if "proxies" in error_msg or "unexpected keyword argument" in error_msg:
                # 如果是参数兼容性问题，尝试不同的初始化方式
                logger.warning(f"检测到参数兼容性问题，尝试备用初始化方法: {e}")
                
                # 尝试方法1：只使用必要参数
                try:
                    self.client = OpenAI(
                        api_key=self.api_key,
                        base_url=self.base_url
                    )
                    logger.info(f"使用基础参数初始化成功，使用模型: {self.api_model}")
                except Exception as e1:
                    logger.warning(f"基础参数初始化失败: {e1}")
                    
                    # 尝试方法2：使用httpx客户端
                    try:
                        import httpx
                        http_client = httpx.Client(timeout=90.0)
                        self.client = OpenAI(
                            api_key=self.api_key,
                            base_url=self.base_url,
                            http_client=http_client
                        )
                        logger.info(f"使用httpx客户端初始化成功，使用模型: {self.api_model}")
                    except Exception as e2:
                        logger.error(f"所有初始化方法都失败了: {e2}")
                        self.client = None
            else:
                logger.error(f"初始化AI客户端失败: {str(e)}")
                self.client = None
        except Exception as e:
            logger.error(f"初始化AI客户端失败: {str(e)}")
            self.client = None
    
    def _get_cache_key(self, tools_results: Dict[str, Any], user_query: str) -> str:
        """生成缓存键"""
        content = json.dumps(tools_results, sort_keys=True) + user_query
        return hashlib.md5(content.encode()).hexdigest()
    
    def _get_cached_result(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """获取缓存结果"""
        with self.cache_lock:
            if cache_key in self.cache:
                expiry_time = self.cache_expiry.get(cache_key, 0)
                if time.time() < expiry_time:
                    logger.info(f"使用缓存结果: {cache_key[:8]}...")
                    return self.cache[cache_key]
                else:
                    # 缓存过期，清理
                    del self.cache[cache_key]
                    del self.cache_expiry[cache_key]
            return None
    
    def _cache_result(self, cache_key: str, result: Dict[str, Any]) -> None:
        """缓存结果"""
        with self.cache_lock:
            self.cache[cache_key] = result
            self.cache_expiry[cache_key] = time.time() + self.cache_ttl
            
    def _can_accept_request(self) -> bool:
        """检查是否可以接受新请求"""
        with self.request_lock:
            return self.active_requests < self.max_concurrent_requests
    
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
        
        # 检查并发限制
        if not self._can_accept_request():
            return {"success": False, "error": "服务器忙碌，请稍后重试"}
        
        # 检查缓存
        cache_key = self._get_cache_key(tools_results, user_query)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            return cached_result
        
        with self.request_lock:
            self.active_requests += 1
        
        try:
            # 准备发送给AI的消息
            messages = self._prepare_messages(tools_results, user_query)
            
            # 调用AI API
            response = self._call_ai_api(messages)
            
            # 处理AI响应
            result = {
                "success": True,
                "report": response,
                "original_results": tools_results,
                "user_query": user_query
            }
            
            # 缓存结果
            self._cache_result(cache_key, result)
            
            return result
            
        except Exception as e:
            logger.error(f"AI处理分析结果时出错: {str(e)}")
            return {
                "success": False,
                "error": f"AI处理失败: {str(e)}",
                "original_results": tools_results
            }
        finally:
            with self.request_lock:
                self.active_requests -= 1
    
    def process_analysis_results_async(self, tools_results: Dict[str, Any], user_query: str, 
                                     timeout: int = 90, progress_callback: Optional[Callable] = None) -> str:
        """
        异步处理多个工具的分析结果，生成定制化报告（支持多进程）
        
        参数:
            tools_results (Dict[str, Any]): 多个工具的分析结果字典
            user_query (str): 用户的自然语言查询/需求
            timeout (int): 超时时间（秒）
            progress_callback (Callable): 进度回调函数
            
        返回:
            str: 请求ID，用于后续查询和取消
        """
        if not self.api_key or not self.client:
            raise Exception("未配置阿里云通义千问API密钥或客户端初始化失败")
        
        # 检查并发限制
        if not self._can_accept_request():
            raise Exception("服务器忙碌，请稍后重试")
        
        # 清理过期任务
        self._cleanup_old_tasks()
        
        # 生成请求ID
        self.request_counter += 1
        request_id = f"ai_req_{self.request_counter}_{int(time.time())}"
        
        # 立即保存初始状态
        initial_state = {
            "status": "created",
            "completed": False,
            "created_time": time.time(),
            "tools_results": tools_results,
            "user_query": user_query,
            "timeout": timeout
        }
        self._save_task_state(request_id, initial_state)
        
        # 检查缓存
        cache_key = self._get_cache_key(tools_results, user_query)
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            # 创建一个已完成的future来存储缓存结果
            future = Future()
            future.set_result(cached_result)
            self.active_futures[request_id] = future
            
            # 保存缓存结果状态
            cached_state = {
                "status": "completed",
                "completed": True,
                "result": cached_result,
                "created_time": time.time(),
                "from_cache": True
            }
            self._save_task_state(request_id, cached_state)
            
            if progress_callback:
                progress_callback("analysis_complete", 100, cached_result)
            return request_id
        
        # 更新状态为运行中
        running_state = {
            "status": "running",
            "completed": False,
            "created_time": time.time(),
            "tools_results": tools_results,
            "user_query": user_query,
            "timeout": timeout
        }
        self._save_task_state(request_id, running_state)
        
        # 提交异步任务
        future = self.executor.submit(self._process_async_task, 
                                    tools_results, user_query, cache_key, 
                                    timeout, progress_callback, request_id)
        
        self.active_futures[request_id] = future
        
        return request_id
    
    def _process_async_task(self, tools_results: Dict[str, Any], user_query: str, 
                          cache_key: str, timeout: int, progress_callback: Optional[Callable], request_id: str) -> Dict[str, Any]:
        """异步任务处理函数"""
        with self.request_lock:
            self.active_requests += 1
        
        try:
            if progress_callback:
                progress_callback("preparing", 10)
            
            # 准备发送给AI的消息
            messages = self._prepare_messages(tools_results, user_query)
            
            if progress_callback:
                progress_callback("analyzing", 30)
            
            # 调用AI API
            response = self._call_ai_api(messages, timeout)
            
            if progress_callback:
                progress_callback("processing", 80)
            
            # 处理AI响应
            result = {
                "success": True,
                "report": response,
                "original_results": tools_results,
                "user_query": user_query
            }
            
            # 缓存结果
            self._cache_result(cache_key, result)
            
            if progress_callback:
                progress_callback("analysis_complete", 100, result)
            
            # 保存结果到文件系统
            task_state = {
                "status": "completed",
                "completed": True,
                "result": result,
                "created_time": time.time()
            }
            self._save_task_state(request_id, task_state)
            
            return result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": f"AI处理失败: {str(e)}",
                "original_results": tools_results
            }
            
            # 保存错误状态到文件系统
            error_state = {
                "status": "error",
                "completed": True,
                "error": str(e),
                "created_time": time.time()
            }
            self._save_task_state(request_id, error_state)
            
            if progress_callback:
                progress_callback("error", 0, error_result)
            return error_result
        finally:
            with self.request_lock:
                self.active_requests -= 1
    
    def cancel_request(self, request_id: str) -> bool:
        """取消异步请求（支持多进程）"""
        # 尝试取消本地future
        if request_id in self.active_futures:
            future = self.active_futures[request_id]
            cancelled = future.cancel()
            if cancelled:
                del self.active_futures[request_id]
                
                # 保存取消状态
                cancelled_state = {
                    "status": "cancelled",
                    "completed": True,
                    "cancelled_time": time.time()
                }
                self._save_task_state(request_id, cancelled_state)
                return True
        
        # 检查文件系统中的任务
        task_state = self._load_task_state(request_id)
        if task_state and task_state.get("status") == "running":
            # 标记为取消（实际任务可能已经在运行，但告诉前端已取消）
            cancelled_state = {
                "status": "cancelled",
                "completed": True,
                "cancelled_time": time.time()
            }
            self._save_task_state(request_id, cancelled_state)
            return True
        
        return False
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "active_requests": self.active_requests,
            "max_concurrent_requests": self.max_concurrent_requests,
            "cache_size": len(self.cache),
            "active_futures": len(self.active_futures),
            "available": self.api_key is not None and self.client is not None
        }
    
    def _save_task_state(self, request_id: str, state: Dict[str, Any]) -> None:
        """保存任务状态到文件系统"""
        try:
            task_file = os.path.join(self.tasks_dir, f"{request_id}.json")
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务状态失败: {e}")
    
    def _load_task_state(self, request_id: str) -> Optional[Dict[str, Any]]:
        """从文件系统加载任务状态"""
        try:
            task_file = os.path.join(self.tasks_dir, f"{request_id}.json")
            if os.path.exists(task_file):
                with open(task_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"加载任务状态失败: {e}")
        return None
    
    def _delete_task_state(self, request_id: str) -> None:
        """删除任务状态文件"""
        try:
            task_file = os.path.join(self.tasks_dir, f"{request_id}.json")
            if os.path.exists(task_file):
                os.remove(task_file)
        except Exception as e:
            logger.error(f"删除任务状态失败: {e}")
    
    def _cleanup_old_tasks(self, max_age_hours: int = 24) -> None:
        """清理过期的任务文件"""
        try:
            current_time = time.time()
            for filename in os.listdir(self.tasks_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.tasks_dir, filename)
                    file_age = current_time - os.path.getmtime(file_path)
                    if file_age > max_age_hours * 3600:  # 转换为秒
                        os.remove(file_path)
                        logger.info(f"清理过期任务文件: {filename}")
        except Exception as e:
            logger.error(f"清理过期任务失败: {e}")
    
    def get_request_result(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取异步请求的结果（支持多进程）"""
        logger.info(f"查询请求结果: {request_id}")
        
        # 首先检查本地futures（当前进程创建的任务）
        if request_id in self.active_futures:
        future = self.active_futures[request_id]
            logger.info(f"找到本地future，是否完成: {future.done()}")
        
        if not future.done():
                # 更新任务状态为运行中
                self._save_task_state(request_id, {
                    "status": "running",
                    "completed": False,
                    "created_time": time.time()
                })
            return {
                "status": "running",
                "completed": False
            }
        
        try:
            result = future.result()
                logger.info(f"获取到本地结果: {type(result)}")
                
                # 保存结果到文件系统
                task_state = {
                    "status": "completed",
                    "completed": True,
                    "result": result,
                    "created_time": time.time()
                }
                self._save_task_state(request_id, task_state)
                
                # 延迟清理本地future
                if not hasattr(future, '_result_retrieved'):
                    future._result_retrieved = True
                    threading.Timer(30.0, lambda: self.active_futures.pop(request_id, None)).start()
            
            return {
                "status": "completed",
                "completed": True,
                "result": result
            }
        except Exception as e:
                logger.error(f"获取本地异步结果时出错: {str(e)}")
                error_state = {
                "status": "error", 
                "completed": True,
                    "error": str(e),
                    "created_time": time.time()
            }
                self._save_task_state(request_id, error_state)
                self.active_futures.pop(request_id, None)
                return error_state
        
        # 检查文件系统中的任务状态（其他进程创建的任务）
        task_state = self._load_task_state(request_id)
        if task_state:
            logger.info(f"从文件系统找到任务状态: {task_state.get('status')}")
            return task_state
        
        # 任务不存在
        logger.warning(f"请求ID {request_id} 不存在")
        return None
    
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
7. 禁止使用markdown格式输出，纯文本输出
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
    
    def _call_ai_api(self, messages: List[Dict[str, str]], timeout: int = 90) -> str:
        """
        调用阿里云通义千问API
        
        参数:
            messages (List[Dict[str, str]]): 消息列表
            timeout (int): 超时时间
            
        返回:
            str: AI生成的响应文本
        """
        try:
            # 使用OpenAI客户端兼容接口调用通义千问
            completion = self.client.chat.completions.create(
                model=self.api_model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                timeout=timeout
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

def generate_report_async(tools_results: Dict[str, Any], user_query: str, 
                         timeout: int = 90, progress_callback: Optional[Callable] = None) -> str:
    """
    异步生成报告的便捷函数，供外部调用
    
    参数:
        tools_results (Dict[str, Any]): 多个工具的分析结果
        user_query (str): 用户查询
        timeout (int): 超时时间
        progress_callback (Callable): 进度回调函数
        
    返回:
        str: 请求ID
    """
    return ai_service.process_analysis_results_async(tools_results, user_query, timeout, progress_callback)

def cancel_ai_request(request_id: str) -> bool:
    """取消AI请求"""
    return ai_service.cancel_request(request_id)

def get_ai_service_status() -> Dict[str, Any]:
    """获取AI服务状态"""
    return ai_service.get_service_status()

def get_ai_request_result(request_id: str) -> Optional[Dict[str, Any]]:
    """
    获取异步请求结果的便捷函数，供外部调用
    
    参数:
        request_id (str): 请求ID
        
    返回:
        Optional[Dict[str, Any]]: 请求状态和结果，如果请求不存在返回None
    """
    return ai_service.get_request_result(request_id) 