from pathlib import Path

import pytest

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


def test_execute_action_rejects_unknown_tool(tmp_path: Path) -> None:
    """确保 Agent 拒绝执行白名单以外的工具。"""
    # 准备：模拟模型请求一个没有获得授权的删除工具。
    action = {"tool": "delete_file"}

    # 执行并验证：执行器必须把它识别为权限错误。
    with pytest.raises(PermissionError, match="不允许执行工具"):
        execute_action(tmp_path, action)


def test_execute_action_runs_write_file(tmp_path: Path) -> None:
    """确保 Agent 检查权限后才能写入 Python 文件。"""
    # 准备：创建旧代码，并模拟模型给出的写入动作。
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('旧代码')", encoding="utf-8")
    action = {
        "tool": "write_file",
        "path": "hello.py",
        "content": "print('新代码')",
    }

    # 执行：Agent 检查权限，再调用写入工具。
    observation = execute_action(tmp_path, action)

    # 验证：文件已经修改，并且 Agent 获得成功结果。
    assert file_path.read_text(encoding="utf-8") == "print('新代码')"
    assert observation == "已写入文件：hello.py"


def test_execute_action_rejects_non_python_write(tmp_path: Path) -> None:
    """确保 Agent 拒绝写入非 Python 文件，并保留原有内容。"""
    # 准备：创建一个不允许模型修改的文本文件。
    file_path = tmp_path / "notes.txt"
    file_path.write_text("原有内容", encoding="utf-8")
    action = {
        "tool": "write_file",
        "path": "notes.txt",
        "content": "模型生成的新内容",
    }

    # 执行并验证：权限检查必须阻止这次写入。
    with pytest.raises(PermissionError, match="Python 文件"):
        execute_action(tmp_path, action)

    # 验证：被拒绝后，磁盘中的原有内容没有改变。
    assert file_path.read_text(encoding="utf-8") == "原有内容"


def test_execute_action_runs_read_file(tmp_path: Path) -> None:
    """确保 Agent 检查路径后能够读取工作区内的文件。"""
    # 准备：创建代码文件，并模拟模型给出的读取动作。
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('你好')", encoding="utf-8")
    action = {
        "tool": "read_file",
        "path": "hello.py",
    }

    # 执行：Agent 接收动作并读取目标文件。
    observation = execute_action(tmp_path, action)

    # 验证：文件内容作为观察结果返回给 Agent。
    assert observation == "print('你好')"


def test_execute_action_runs_tests(tmp_path: Path) -> None:
    """确保 Agent 能运行测试并获得测试结果。"""
    # 准备：创建一个必定通过的临时测试。
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "def test_example():\n"
        "    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )
    action = {"tool": "run_tests"}

    # 执行：Agent 接收动作，并调用固定的测试工具。
    observation = execute_action(tmp_path, action)

    # 验证：观察结果中包含成功退出码和测试输出。
    exit_code, output = observation
    assert exit_code == 0
    assert "1 passed" in output
