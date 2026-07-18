import json
from collections.abc import Callable


# 请求函数接收任务和观察历史，返回 DeepSeek 响应中的文本。
DeepSeekRequest = Callable[[str, list[dict[str, object]]], str]


class DeepSeekAdapter:
    """把 DeepSeek 的响应文本转换成 Agent 能理解的动作。

    作用：隔开 DeepSeek API 和 Agent 核心，避免 Agent 核心依赖具体网络实现。
    输入：一个负责发送请求的函数；决策时还会接收任务和观察历史。
    处理：调用请求函数取得 JSON 文本，再把文本解析成 Python 字典。
    输出：符合 Model 接口的动作字典，交给 run_agent 继续处理。
    """

    def __init__(self, request: DeepSeekRequest) -> None:
        """保存负责发送 DeepSeek 请求的函数。"""
        self.request = request

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """请求模型决策，并把响应中的 JSON 文本解析成动作字典。"""
        response_text = self.request(task, observations)
        return json.loads(response_text)
