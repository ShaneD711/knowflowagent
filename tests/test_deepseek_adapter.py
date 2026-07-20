from knowflow_agent.deepseek_adapter import DeepSeekAdapter


def test_deepseek_adapter_converts_response_text_to_action() -> None:
    """验证适配层将 DeepSeek 的 JSON 响应解析为 Agent 动作。"""

    # 准备：使用返回固定 JSON 的假请求隔离真实网络和 API Key。
    def fake_request(
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        return '{"tool": "list_files"}'

    adapter = DeepSeekAdapter(request=fake_request)

    # 执行：让适配层完成提示构造、请求调用和响应解析。
    action = adapter.decide(
        task="查看项目文件",
        observations=[],
    )

    # 验证：解析结果是 Agent 核心能够执行的动作字典。
    assert action == {"tool": "list_files"}


def test_deepseek_adapter_builds_prompts_from_agent_data() -> None:
    """验证适配层将任务和观察记录转换为 DeepSeek 提示文本。"""

    # 准备：使用假请求记录收到的提示文本，避免发送真实网络请求。
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

    # 执行：将 Agent 的任务和观察记录交给适配层处理。
    adapter.decide(
        task="查看项目文件",
        observations=observations,
    )

    # 验证：请求层收到系统提示和序列化后的用户提示，而非原始对象。
    system_prompt, user_prompt = received_prompts[0]

    assert "list_files" in system_prompt
    assert isinstance(user_prompt, str)
    assert "任务：查看项目文件" in user_prompt
    assert '"result": ["calculator.py"]' in user_prompt
