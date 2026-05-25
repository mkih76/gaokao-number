"""
Hermes AI 网关客户端
支持 OpenAI 兼容格式，多用户 Session 隔离
"""
import requests
from typing import Optional


class HermesError(Exception):
    """Hermes API 错误"""
    pass


class HermesClient:
    """Hermes AI 网关客户端"""

    def __init__(
        self,
        base_url: str = "http://23.94.206.159:8642",
        api_key: str = "hermes2024",
        model: str = "gpt-4o-mini",
        timeout: int = 60,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def chat(
        self,
        messages: list[dict],
        user_id: str = "anonymous",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> dict:
        """
        发送对话请求

        Args:
            messages: [{"role": "user", "content": "..."}]
            user_id: 用户ID（用于 Hermes Session 隔离）
            temperature: 创造性参数
            max_tokens: 最大 token 数

        Returns:
            {"content": str, "usage": dict, ...}
        """
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"你是公考数量关系的AI学习助手，用户ID：{user_id}。"},
                *messages,
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        try:
            resp = self._session.post(
                f"{self.base_url}/v1/chat/completions",
                json=payload,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()

            return {
                "content": data["choices"][0]["message"]["content"],
                "usage": data.get("usage", {}),
                "model": data.get("model", self.model),
            }
        except requests.exceptions.Timeout:
            raise HermesError("请求超时，请稍后重试")
        except requests.exceptions.HTTPError as e:
            raise HermesError(f"API错误: {e.response.status_code} {e.response.text}")
        except (KeyError, IndexError) as e:
            raise HermesError(f"响应格式错误: {e}")

    def ask_math(
        self,
        question: str,
        user_id: str = "anonymous",
        mode: str = "teach",
    ) -> dict:
        """
        询问数学问题

        Args:
            question: 用户问题
            user_id: 用户ID
            mode: "teach" 教学模式, "speed" 考场速解, "debug" 错题解析

        Returns:
            {"answer": str, "method": str, "speed_tips": str}
        """
        system_prompt = {
            "teach": "你是一位公考数量关系专家，擅长讲解解题思路和方法。",
            "speed": "你是一位公考行测数量关系专家，擅长考场上的快速解题技巧。",
            "debug": "你是一位公考数量关系专家，擅长分析错题原因并给出正确解法。",
        }.get(mode, "teach")

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ]

        result = self.chat(messages, user_id=user_id)
        return {
            "answer": result["content"],
            "mode": mode,
        }

    def health_check(self) -> bool:
        """检查 Hermes 服务是否可用"""
        try:
            resp = self._session.get(
                f"{self.base_url}/health",
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False


# 全局单例
_hermes_client: Optional[HermesClient] = None


def get_hermes() -> HermesClient:
    """获取全局 Hermes 客户端实例"""
    global _hermes_client
    if _hermes_client is None:
        _hermes_client = HermesClient()
    return _hermes_client


def set_hermes(client: HermesClient):
    """设置全局 Hermes 客户端"""
    global _hermes_client
    _hermes_client = client
