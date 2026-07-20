import json
from collections.abc import Callable

# 网络请求函数的统一签名：接收系统提示词和用户提示词，返回响应文本。
DeepSeekRequest = Callable[[str, str], str]


class DeepSeekAdapter:
    """在 Agent 数据结构与 DeepSeek 文本接口之间转换数据。

    适配器把任务和观察记录构造成提示词，再把 DeepSeek 返回的 JSON 文本
    解析为 ``run_agent`` 可以执行的动作字典。具体网络请求由外部注入，
    因此适配器不依赖某个固定的 SDK。
    """

    def __init__(self, request: DeepSeekRequest) -> None:
        """保存负责访问 DeepSeek API 的请求函数。

        Args:
            request: 接收系统提示词和用户提示词、返回响应文本的函数。
        """
        self.request = request

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """根据 Agent 当前状态请求 DeepSeek 选择下一步动作。

        Args:
            task: 用户交给 Agent 的任务描述。
            observations: Agent 已经获得的工具结果或权限错误记录。

        Returns:
            从 DeepSeek 响应 JSON 中解析出的动作字典。

        Raises:
            json.JSONDecodeError: DeepSeek 返回的文本不是有效 JSON。
        """

        # 将结构化观察记录序列化，保留中文并嵌入用户提示词。
        observation_text = json.dumps(observations, ensure_ascii=False)

        # 系统提示词定义工具白名单、决策顺序和动作 JSON 格式。
        system_prompt = (
            "你是一个最小 SWE Agent。"
            "你必须根据任务和观察历史，每次只选择一个动作。"
            "可用动作只有 list_files、read_file、write_file、run_tests 和 finish。"
            "当观察历史为空时，必须先使用 list_files。"
            "先读取相关文件，确认问题后才能写入代码。"
            "写入代码后必须运行测试。"
            "测试通过后使用 finish；测试失败时根据测试输出继续处理。"
            'list_files 格式：{"tool": "list_files"}。'
            'read_file 格式：{"tool": "read_file", "path": "文件路径"}。'
            'write_file 格式：{"tool": "write_file", "path": "文件路径", '
            '"content": "完整的新代码"}。'
            'run_tests 格式：{"tool": "run_tests"}。'
            'finish 格式：{"tool": "finish", "summary": "任务总结"}。'
            "你必须只输出一个 JSON 对象，不要输出解释。"
        )

        # 用户提示词提供本次任务和每轮真实执行后积累的观察记录。
        user_prompt = (
            f"任务：{task}\n" f"观察历史：{observation_text}\n" "请选择下一步工具。"
        )

        # 注入的请求函数负责网络通信，适配器不直接依赖 OpenAI SDK。
        response_text = self.request(system_prompt, user_prompt)

        # 将供应商返回的文本统一转换为 Agent 核心使用的动作字典。
        return json.loads(response_text)
