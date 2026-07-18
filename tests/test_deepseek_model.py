from knowflow_agent.deepseek_adapter import DeepSeekAdapter


def test_deepseek_adapter_converts_response_text_to_action() -> None:
    """确保模型适配层能把 API 返回的 JSON 文本转换成 Agent 动作。"""

    # 准备：用普通函数模拟 DeepSeek API，避免测试依赖网络和 API Key。
    def fake_request(
        task: str,
        observations: list[dict[str, object]],
    ) -> str:
        return '{"tool": "list_files"}'

    model = DeepSeekAdapter(request=fake_request)

    # 执行：适配层取得响应文本，并把 JSON 文本解析成 Python 字典。
    action = model.decide(
        task="查看项目文件",
        observations=[],
    )

    # 验证：返回的数据结构符合 Agent 核心的 Model 接口。
    assert action == {"tool": "list_files"}
