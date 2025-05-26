# llm_interface.py
import requests
import os
import json
from openai import OpenAI, APIConnectionError, RateLimitError, APIStatusError # openai >= 1.0.0
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

class LLMInterface:
    # LLM 统一接口类
    # 目标: 解耦业务逻辑与具体的LLM实现。
    # 上层应用都通过一个统一的接口进行调用。

    def __init__(self, 
                 llm_type: str = "ollama", 
                 ollama_base_url: str = "http://localhost:11434", 
                 ollama_model: str = "qwen3:4b", # 更新了 ollama 默认模型
                 deepseek_model: str = "deepseek-chat",
                 qwen_model: str = "qwen-plus"
                 ):
        # 初始化LLM接口。
        # :param llm_type: 指定使用的LLM类型 ("ollama", "deepseek", "qwen", "placeholder")
        # :param ollama_base_url: Ollama服务的基础URL。可以被 OLLAMA_BASE_URL 环境变量覆盖。
        # :param ollama_model: 要使用的Ollama模型名称。
        # :param deepseek_model: 要使用的DeepSeek模型名称。
        # :param qwen_model: 要使用的Qwen模型名称 (例如 "qwen-plus", "qwen-turbo", "qwen-max")。
        self.llm_type = llm_type
        
        if self.llm_type == "ollama":
            self.ollama_base_url = os.getenv('OLLAMA_BASE_URL', ollama_base_url).strip('/')
            self.ollama_model = ollama_model
            self.ollama_api_url = f"{self.ollama_base_url}/api/generate"
            print(f"LLM接口初始化为Ollama模式: URL='{self.ollama_api_url}', 模型='{self.ollama_model}'")
        
        elif self.llm_type == "deepseek":
            self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
            if not self.deepseek_api_key:
                print("警告: 未找到 DEEPSEEK_API_KEY 环境变量。DeepSeek后端将不可用。")
            self.deepseek_client = OpenAI(api_key=self.deepseek_api_key, base_url="https://api.deepseek.com")
            self.deepseek_model = deepseek_model
            print(f"LLM接口初始化为DeepSeek模式: 模型='{self.deepseek_model}'")

        elif self.llm_type == "qwen":
            self.qwen_api_key = os.getenv('QWEN_API_KEY')
            if not self.qwen_api_key:
                print("警告: 未找到 QWEN_API_KEY 环境变量。Qwen后端将不可用。")
            # DashScope的兼容OpenAI的base_url
            self.qwen_client = OpenAI(api_key=self.qwen_api_key, base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")
            self.qwen_model = qwen_model 
            print(f"LLM接口初始化为Qwen模式: 模型='{self.qwen_model}'")

        elif self.llm_type == "placeholder":
            print("LLM接口初始化为占位符模式。")
        else:
            raise ValueError(f"不支持的LLM类型: '{llm_type}'。支持的类型为 'ollama', 'deepseek', 'qwen', 'placeholder'。")

    def generate_text(self, prompt: str, system_prompt: str = "你是一个专业的中医药知识助手", max_tokens=2048, temperature=0.7) -> str:
        # 生成文本的核心方法。
        # :param prompt: 输入给LLM的用户提示词。
        # :param system_prompt: 系统提示词。
        # :param max_tokens: 生成文本的最大长度（对于OpenAI兼容API）。
        # :param temperature: 生成文本的温度（对于OpenAI兼容API）。
        # :return: LLM生成的文本结果，或在发生错误时返回对用户友好的错误信息字符串。

        if self.llm_type == "ollama":
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": { # Ollama 支持通过 options 传递类似 max_tokens 和 temperature 的参数
                    "num_predict": max_tokens, # num_predict 通常对应 max_tokens
                    "temperature": temperature
                }
            }
            headers = {"Content-Type": "application/json"}
            print(f"向Ollama发送请求: URL='{self.ollama_api_url}', 模型='{self.ollama_model}'")
            response = None
            try:
                response = requests.post(self.ollama_api_url, json=payload, headers=headers, timeout=60)
                response.raise_for_status()
                response_data = response.json()
                generated_text = response_data.get("response", "")
                return generated_text.strip()
            except requests.exceptions.Timeout:
                print(f"错误: 请求Ollama超时 (URL: {self.ollama_api_url})。")
                return "错误：请求LLM超时，请稍后重试或检查网络连接。"
            except requests.exceptions.HTTPError as e:
                error_message = f"错误: 请求Ollama时发生HTTP错误: {e.response.status_code} {e.response.reason}。"
                try:
                    error_details = e.response.json()
                    error_message += f" 详细信息: {error_details.get('error', e.response.text)}"
                except json.JSONDecodeError:
                    error_message += f" 响应内容非JSON: {e.response.text}"
                print(error_message)
                return f"错误：请求LLM时发生HTTP错误 (状态码: {e.response.status_code})，请检查Ollama服务状态或请求参数。"
            except requests.exceptions.RequestException as e:
                print(f"错误: 请求Ollama时发生网络错误: {e} (URL: {self.ollama_api_url})。")
                return f"错误：请求LLM时发生网络问题 ({e})，请检查Ollama服务是否正在运行以及网络连接。"
            except json.JSONDecodeError as e_json:
                response_text_for_error = response.text if response is not None else "无有效响应对象"
                print(f"错误: 解析Ollama响应时发生JSON解码错误。响应状态码: {response.status_code if response is not None else 'N/A'}。响应内容: '{response_text_for_error[:500]}...'。错误详情: {e_json}")
                return "错误：无法解析LLM的响应，响应格式不正确。"
            except Exception as e:
                print(f"错误: 调用Ollama LLM时发生未知错误: {e}")
                return f"错误：调用LLM时发生未知内部问题 ({e})。"

        elif self.llm_type == "deepseek":
            if not hasattr(self, 'deepseek_api_key') or not self.deepseek_api_key:
                print("错误: DeepSeek API密钥未在初始化时配置或环境变量缺失。")
                return "错误：DeepSeek API密钥未配置，无法使用此模型。"
            try:
                print(f"向DeepSeek发送请求: 模型='{self.deepseek_model}'")
                messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
                response = self.deepseek_client.chat.completions.create(
                    model=self.deepseek_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response.choices[0].message.content.strip()
            except APIConnectionError as e:
                print(f"错误：无法连接到DeepSeek API: {e}")
                return f"错误：无法连接到DeepSeek API - {e}"
            except RateLimitError as e:
                print(f"错误：DeepSeek API请求超过速率限制: {e}")
                return f"错误：DeepSeek API请求超过速率限制 - {e}"
            except APIStatusError as e:
                print(f"错误：DeepSeek API返回错误状态码 {e.status_code}: {e.response}")
                return f"错误：DeepSeek API错误 (状态码 {e.status_code}) - {e.response}"
            except Exception as e: # openai.APIError 是所有 client-side errors 的基类
                print(f"错误: 调用DeepSeek LLM时发生OpenAI库相关错误: {e}")
                return f"错误：调用DeepSeek时发生API相关问题 - {e}"

        elif self.llm_type == "qwen":
            if not hasattr(self, 'qwen_api_key') or not self.qwen_api_key:
                print("错误: Qwen (DashScope) API密钥未在初始化时配置或环境变量缺失。")
                return "错误：Qwen API密钥未配置，无法使用此模型。"
            try:
                print(f"向Qwen (DashScope)发送请求: 模型='{self.qwen_model}'")
                messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]
                # Qwen (DashScope) specific: extra_body={"enable_thinking": False}
                # 根据llm_hub.py, Qwen似乎不需要extra_body, 直接用标准OpenAI调用
                response = self.qwen_client.chat.completions.create(
                    model=self.qwen_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                return response.choices[0].message.content.strip()
            except APIConnectionError as e:
                print(f"错误：无法连接到Qwen (DashScope) API: {e}")
                return f"错误：无法连接到Qwen (DashScope) API - {e}"
            except RateLimitError as e:
                print(f"错误：Qwen (DashScope) API请求超过速率限制: {e}")
                return f"错误：Qwen (DashScope) API请求超过速率限制 - {e}"
            except APIStatusError as e:
                print(f"错误：Qwen (DashScope) API返回错误状态码 {e.status_code}: {e.response}")
                return f"错误：Qwen (DashScope) API错误 (状态码 {e.status_code}) - {e.response}"
            except Exception as e: # openai.APIError 是所有 client-side errors 的基类
                print(f"错误: 调用Qwen (DashScope) LLM时发生OpenAI库相关错误: {e}")
                return f"错误：调用Qwen (DashScope)时发生API相关问题 - {e}"
            
        elif self.llm_type == "placeholder":
            print(f"LLM占位符模式接收到提示词 (最长100字符): {prompt[:100]}...")
            print(f"  模拟参数: max_tokens={max_tokens}, temperature={temperature}")
            return f"LLM模拟响应 (占位符): 这是对'{prompt[:50]}...'的回复。"
        
        else: 
            print(f"错误: LLM类型 '{self.llm_type}' 未正确配置或不被支持。")
            return "错误: LLM类型未正确配置。"
