from pathlib import Path

import pytest

from knowflow_agent.agent import execute_action, run_agent


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


class FakeModel:
    """按照固定顺序返回动作，用来测试 Agent 循环。"""

    def __init__(self) -> None:
        # 记录模型每次决策时收到的观察历史，供测试验证数据回传。
        self.received_observations: list[list[dict[str, object]]] = []

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """第一次要求列文件，获得观察结果后结束。"""
        # 保存本次收到的观察历史，便于测试检查模型看到的数据。
        self.received_observations.append(observations.copy())

        # 没有观察结果时，先要求 Agent 查看工作区文件。
        if not observations:
            return {"tool": "list_files"}

        # 收到文件列表后，返回 finish 结束这个最小反馈循环。
        return {
            "tool": "finish",
            "summary": "已经看到项目文件",
        }


def test_run_agent_returns_observation_to_model(tmp_path: Path) -> None:
    """确保 Agent 把工具结果返回给模型，再让模型继续决策。"""
    # 准备：创建临时项目和一个可预测的假模型。
    (tmp_path / "hello.py").write_text("", encoding="utf-8")
    model = FakeModel()

    # 执行：Agent 应该经历“决策、执行、观察、再决策”。
    summary = run_agent(
        workspace=tmp_path,
        task="查看项目中有哪些文件",
        model=model,
        max_steps=2,
    )

    # 验证：模型第二次决策时已经看到了 list_files 的执行结果。
    assert summary == "已经看到项目文件"
    assert model.received_observations == [
        [],
        [
            {
                "ok": True,
                "tool": "list_files",
                "result": ["hello.py"],
            }
        ],
    ]


class ForbiddenToolFakeModel:
    """第一次请求禁止工具，收到错误观察后结束。"""

    def __init__(self) -> None:
        self.received_observations: list[list[dict[str, object]]] = []

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """根据是否收到错误观察结果选择下一步动作。"""
        self.received_observations.append(observations.copy())

        # 第一次没有观察结果时，故意请求一个未授权工具。
        if not observations:
            return {"tool": "delete_file"}

        return {
            "tool": "finish",
            "summary": "已经看到权限错误",
        }


def test_run_agent_returns_permission_error_to_model(tmp_path: Path) -> None:
    """当模型请求了禁止执行的工具，Agent 不应该直接崩溃，而应该把权限错误整理成观察结果，再交回模型。"""
    # 准备：使用一个会请求禁止工具的假模型。
    # 它第一次会请求 delete_file，
    # 第二次看到错误结果后会返回 finish。
    model = ForbiddenToolFakeModel()

    # 执行：Agent 应该接住权限错误，再让模型继续决策。
    summary = run_agent(
        workspace=tmp_path,
        task="删除文件",
        model=model,
        max_steps=2,
    )

    # 验证：模型第二次决策时已经看到了结构化错误。
    assert summary == "已经看到权限错误"
    assert model.received_observations == [
        [],
        [
            {
                "ok": False,
                "tool": "delete_file",
                "error": "不允许执行工具：delete_file",
            }
        ],
    ]


class NeverFinishFakeModel:
    """始终请求列出文件，用来验证 Agent 不会无限循环。"""

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """每次都返回工具动作，永远不主动结束。"""
        return {"tool": "list_files"}


def test_run_agent_stops_at_max_steps(tmp_path: Path) -> None:
    """确保模型一直不结束时，Agent 会在最大步数处停止。"""
    # 准备：创建一个永远不会返回 finish 的假模型。
    model = NeverFinishFakeModel()

    # 执行并验证：达到两步后必须抛出明确错误，不能无限循环。
    with pytest.raises(RuntimeError, match="最大步数"):
        run_agent(
            workspace=tmp_path,
            task="一直查看文件",
            model=model,
            max_steps=2,
        )


class RepairFakeModel:
    """根据 Agent 返回的观察结果选择下一步修复动作。"""

    def __init__(self) -> None:
        self.received_observations: list[list[dict[str, object]]] = []

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """观察上一个工具的结果，再决定下一个工具。"""
        self.received_observations.append(observations.copy())

        # 第一次还没有观察结果，先要求 Agent 查看工作区有哪些文件。
        if not observations:
            return {"tool": "list_files"}

        # observations[-1] 表示取列表中的最后一项。
        # 也就是获取“最近一次工具执行结果”。
        last_observation = observations[-1]
        last_tool = last_observation["tool"]

        # 看到文件列表后，读取需要修复的代码。
        if last_tool == "list_files":
            return {
                "tool": "read_file",
                "path": "calculator.py",
            }

        # 看到错误代码后，生成修复后的代码。
        if last_tool == "read_file":
            return {
                "tool": "write_file",
                "path": "calculator.py",
                "content": (
                    "def multiply(a: int, b: int) -> int:\n"
                    "    return a * b\n"
                ),
            }

        # 代码写入完成后，运行测试确认修改是否正确。
        if last_tool == "write_file":
            return {"tool": "run_tests"}

        # 最后根据 pytest 的退出码判断测试是否通过。
        test_result = last_observation["result"]

        # 检查 test_result 是否为元组 tuple，并且元组中的第一个值是否为 0。
        # 测试进程的退出码为 0 表示通过，非 0 表示失败或发生错误。
        if isinstance(test_result, tuple) and test_result[0] == 0:
            return {
                "tool": "finish",
                "summary": "已修复代码并通过测试",
            }

        return {
            "tool": "finish",
            "summary": "修改完成，但测试仍然失败",
        }


def test_run_agent_repairs_project_and_passes_tests(tmp_path: Path) -> None:
    """确保 Agent 能修复错误代码，并根据测试结果结束任务。"""
    # 准备：创建包含错误代码和真实失败测试的临时项目。
    # 向 calculator.py 中写入错误代码。
    calculator_path = tmp_path / "calculator.py"
    calculator_path.write_text(
        "def multiply(a: int, b: int) -> int:\n"
        "    return a / b\n",
        encoding="utf-8",
    )
    # 创建与错误代码对应的测试文件。
    test_path = tmp_path / "test_calculator.py"
    test_path.write_text(
        "from calculator import multiply\n\n"
        "def test_multiply() -> None:\n"
        "    assert multiply(2, 3) == 6\n",
        encoding="utf-8",
    )

    model = RepairFakeModel()

    # 执行：假模型根据每次观察结果选择下一个工具。
    summary = run_agent(
        workspace=tmp_path,
        task="修复计算器，使测试通过",
        model=model,
        max_steps=5,
    )

    # 验证：错误代码已经被替换成正确代码。
    assert calculator_path.read_text(encoding="utf-8") == (
        "def multiply(a: int, b: int) -> int:\n"
        "    return a * b\n"
    )

    # 验证：Agent 根据测试成功结果结束了任务。
    assert summary == "已修复代码并通过测试"

    # 检查模型最后看到的工具结果是否为 run_tests。
    last_observation = model.received_observations[-1][-1]
    assert last_observation["tool"] == "run_tests"

    # 检查 pytest 的退出码和输出文本。
    test_result = last_observation["result"]
    assert isinstance(test_result, tuple)
    assert test_result[0] == 0
    assert "1 passed" in test_result[1]
