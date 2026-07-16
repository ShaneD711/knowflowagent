from pathlib import Path

from knowflow_agent.agent import execute_action


def test_execute_action_runs_list_files(tmp_path: Path) -> None:
    """确保 Agent 能执行经过允许的 list_files 动作。"""
    # 准备：创建临时工作区，并模拟 DeepSeek 给出的动作。
    (tmp_path / "hello.py").write_text("", encoding="utf-8")
    action = {"tool": "list_files"}

    # 执行：Agent 接收动作，再调用对应工具观察工作区。
    observation = execute_action(tmp_path, action)

    # 验证：工具执行结果被作为观察结果返回给 Agent。
    assert observation == ["hello.py"]
