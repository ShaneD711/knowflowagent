import json
from collections.abc import Callable

# 请求函数接收两段已经准备好的提示文本，返回 DeepSeek 响应文本。
DeepSeekRequest = Callable[[str, str], str]


class DeepSeekAdapter:
    """在 Agent 数据和 DeepSeek 文本之间完成格式转换。

    作用：隔开 Agent 核心与 DeepSeek 请求格式，使 run_agent 只依赖 Model 接口。
    输入：初始化时接收请求函数；决策时接收任务描述和观察记录。
    处理：把观察记录转换成 JSON，构造提示文本，调用请求函数，
    再把响应中的 JSON 文本解析成 Python 动作字典。
    输出：符合 Model 接口的动作字典，交给 run_agent 执行。
    """

    # 构造时只保存 request 函数；调用 decide 时才会真正发送请求。
    def __init__(self, request: DeepSeekRequest) -> None:
        """保存负责发送 DeepSeek 请求的函数。"""
        self.request = request

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """把 Agent 数据转换成提示文本，再把响应文本转换成动作字典。"""

        # 把 Python 观察记录转换成能够放进提示词的 JSON 文本。
        observation_text = json.dumps(observations, ensure_ascii=False)

        # 系统提示词告诉 DeepSeek 可以选择哪些动作以及输出格式。
        system_prompt = (
            "你是一个最小 SWE Agent。"
            "可用动作只有 list_files 和 finish。"
            "当观察历史为空时，必须先使用 list_files。"
            "当观察历史中已经有文件列表时，使用 finish。"
            'list_files 格式：{"tool": "list_files"}。'
            'finish 格式：{"tool": "finish", "summary": "任务总结"}。'
            "你必须只输出一个 JSON 对象，不要输出解释。"
        )

        # 用户提示词携带本次任务和 Agent 已经获得的真实观察记录。
        user_prompt = (
            f"任务：{task}\n" f"观察历史：{observation_text}\n" "请选择下一步工具。"
        )

        # 请求函数现在只接收准备完成的提示文本。
        response_text = self.request(system_prompt, user_prompt)

        # 把 DeepSeek 返回的 JSON 文本转换成 run_agent 能处理的动作字典。
        return json.loads(response_text)
