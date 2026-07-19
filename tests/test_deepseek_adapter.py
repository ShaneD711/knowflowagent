from knowflow_agent.deepseek_adapter import DeepSeekAdapter


def test_deepseek_adapter_converts_response_text_to_action() -> None:
    """确保模型适配层能把 API 返回的 JSON 文本转换成 Agent 动作。"""

    # 准备：用普通函数模拟网络请求，避免测试依赖 API Key。
    def fake_request(
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return '{"tool": "list_files"}'

    adapter = DeepSeekAdapter(request=fake_request)

    # 执行：适配层构造提示文本，并把响应文本解析成 Python 字典。
    action = adapter.decide(
        task="查看项目文件",
        observations=[],
    )

    # 验证：返回的数据结构符合 Agent 核心的 Model 接口。
    assert action == {"tool": "list_files"}


def test_deepseek_adapter_builds_prompts_from_agent_data() -> None:
    """确保适配层把 Agent 数据转换成发送给 DeepSeek 的提示文本。"""

    # 准备：记录适配层交给请求函数的数据，不发送真实网络请求。
    received_prompts: list[tuple[str, str]] = []

    def fake_request(
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        received_prompts.append((system_prompt, user_prompt))
        return '{"tool": "finish", "summary": "完成"}'

    adapter = DeepSeekAdapter(request=fake_request)
    observations = [
        {
            "ok": True,
            "tool": "list_files",
            "result": ["calculator.py"],
        }
    ]

    # 执行：把 Agent 的任务和观察记录交给适配层。
    adapter.decide(
        task="查看项目文件",
        observations=observations,
    )

    # 验证：请求函数收到的是提示文本，不是原始 observations 对象。
    system_prompt, user_prompt = received_prompts[0]

    assert "list_files" in system_prompt
    assert isinstance(user_prompt, str)
    assert "任务：查看项目文件" in user_prompt
    assert '"result": ["calculator.py"]' in user_prompt
