import os
from typing import List, Dict, Union, Optional
from openai import OpenAI
import tiktoken
from dotenv import load_dotenv

load_dotenv()


class LLMServiceHub:
    def __init__(self):
        # DeepSeek 客户端
        self.deepseek_client = OpenAI(
            api_key=os.getenv('DEEPSEEK_API_KEY', ''),
            base_url="https://api.deepseek.com"
        )

        # Qwen 客户端
        self.qwen_client = OpenAI(
            api_key=os.getenv('QWEN_API_KEY', ''),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
        )

        # 令牌计数器
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

    def _count_tokens(self, text: str) -> int:
        """计算文本的 token 数量"""
        return len(self.tokenizer.encode(text))

    def infer(self,
              model_id: str,
              prompt: str,
              parameters: Optional[Dict] = None
              ) -> Dict[str, Union[str, Dict]]:
        """
        通用推理接口，支持不同模型

        :param model_id: 模型标识
        :param prompt: 输入文本
        :param parameters: 模型参数
        :return: 推理结果
        """
        parameters = parameters or {}
        max_tokens = parameters.get('max_tokens', 100)
        temperature = parameters.get('temperature', 0.7)

        try:
            if model_id.startswith('deepseek'):
                response = self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "你是一个专业的中医药知识助手"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature
                )
                result_text = response.choices[0].message.content

            elif model_id.startswith('qwen'):
                response = self.qwen_client.chat.completions.create(
                    model="qwen-plus",
                    messages=[
                        {"role": "system", "content": "你是一个专业的中医药知识助手"},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    extra_body={"enable_thinking": False}
                )
                result_text = response.choices[0].message.content

            else:
                raise ValueError(f"不支持的模型: {model_id}")

            return {
                "model_id": model_id,
                "result_text": result_text,
                "usage_stats": {
                    "prompt_tokens": self._count_tokens(prompt),
                    "completion_tokens": self._count_tokens(result_text)
                }
            }

        except Exception as e:
            return {
                "model_id": model_id,
                "error": str(e)
            }

    def embed(self,
              model_id: str,
              texts: List[str],
              dimensions: Optional[int] = None
              ) -> Dict[str, Union[str, List[List[float]]]]:
        """
        文本嵌入接口

        :param model_id: 嵌入模型标识
        :param texts: 待嵌入的文本列表
        :param dimensions: 向量维度（可选）
        :return: 文本向量
        """
        try:
            # 使用 Qwen 客户端进行文本嵌入
            response = self.qwen_client.embeddings.create(
                model="text-embedding-v3",
                input=texts,
                dimensions=dimensions or 1024,  # 默认1024维度
                encoding_format="float"
            )

            embeddings = [item.embedding for item in response.data]

            return {
                "model_id": model_id,
                "embeddings": embeddings,
                "usage_stats": {
                    "total_tokens": sum(self._count_tokens(text) for text in texts),
                    "dimensions": len(embeddings[0]) if embeddings else 0
                }
            }

        except Exception as e:
            return {
                "model_id": model_id,
                "error": str(e)
            }


# 使用示例
def main():
    llm_service = LLMServiceHub()

    # 推理示例
    infer_result = llm_service.infer(
        model_id="deepseek-chat",
        prompt="解释中医'肝火'的概念",
        parameters={"max_tokens": 200, "temperature": 0.7}
    )
    print("推理结果:", infer_result)

    # 嵌入示例
    embed_result = llm_service.embed(
        model_id="text-embedding-v3",
        texts=["麻黄发汗解表", "桂枝温通经脉"]
    )
    print("嵌入结果:", embed_result)


if __name__ == "__main__":
    main()
