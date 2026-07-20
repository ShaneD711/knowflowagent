from pathlib import Path

import pytest

from knowflow_agent.agent import execute_action, run_agent


def test_execute_action_runs_list_files(tmp_path: Path) -> None:
    """验证执行器把 ``list_files`` 动作分派给文件列表工具。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    (tmp_path / "hello.py").write_text("", encoding="utf-8")
    action = {"tool": "list_files"}

    observation = execute_action(tmp_path, action)

    # execute_action 的返回值会成为 run_agent 传回模型的观察结果。
    assert observation == ["hello.py"]


def test_execute_action_rejects_unknown_tool(tmp_path: Path) -> None:
    """验证执行器拒绝不在工具白名单中的动作。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    action = {"tool": "delete_file"}

    with pytest.raises(PermissionError, match="不允许执行工具"):
        execute_action(tmp_path, action)


def test_execute_action_runs_write_file(tmp_path: Path) -> None:
    """验证执行器通过权限检查后写入 Python 文件。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('旧代码')", encoding="utf-8")
    action = {
        "tool": "write_file",
        "path": "hello.py",
        "content": "print('新代码')",
    }

    observation = execute_action(tmp_path, action)

    # 同时检查磁盘状态和返回给 Agent 的观察文本。
    assert file_path.read_text(encoding="utf-8") == "print('新代码')"
    assert observation == "已写入文件：hello.py"


def test_execute_action_rejects_non_python_write(tmp_path: Path) -> None:
    """验证执行器拒绝修改非 Python 文件且不破坏原内容。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    file_path = tmp_path / "notes.txt"
    file_path.write_text("原有内容", encoding="utf-8")
    action = {
        "tool": "write_file",
        "path": "notes.txt",
        "content": "模型生成的新内容",
    }

    with pytest.raises(PermissionError, match="Python 文件"):
        execute_action(tmp_path, action)

    # 权限错误必须发生在写入之前。
    assert file_path.read_text(encoding="utf-8") == "原有内容"


def test_execute_action_runs_read_file(tmp_path: Path) -> None:
    """验证执行器通过路径检查后返回工作区文件内容。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('你好')", encoding="utf-8")
    action = {
        "tool": "read_file",
        "path": "hello.py",
    }

    observation = execute_action(tmp_path, action)

    # 读取到的文本会作为观察结果供模型继续决策。
    assert observation == "print('你好')"


def test_execute_action_runs_tests(tmp_path: Path) -> None:
    """验证执行器返回 pytest 的退出码和输出文本。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "def test_example():\n" "    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )
    action = {"tool": "run_tests"}

    observation = execute_action(tmp_path, action)

    # run_tests 的两个返回值共同构成模型看到的测试观察结果。
    exit_code, output = observation
    assert exit_code == 0
    assert "1 passed" in output


class FakeModel:
    """提供可预测决策，用于验证观察结果能否回传给模型。"""

    def __init__(self) -> None:
        # 保存每次调用收到的独立快照，避免后续列表修改影响断言。
        self.received_observations: list[list[dict[str, object]]] = []

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """根据观察历史返回列文件动作或结束动作。

        Args:
            task: Agent 当前处理的任务描述。
            observations: 此前工具执行产生的结构化观察记录。

        Returns:
            首次决策返回 ``list_files``，收到观察记录后返回 ``finish``。
        """
        self.received_observations.append(observations.copy())

        if not observations:
            return {"tool": "list_files"}

        return {
            "tool": "finish",
            "summary": "已经看到项目文件",
        }


def test_run_agent_returns_observation_to_model(tmp_path: Path) -> None:
    """验证 Agent 把工具结果加入历史后再次请求模型决策。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    (tmp_path / "hello.py").write_text("", encoding="utf-8")
    model = FakeModel()

    summary = run_agent(
        workspace=tmp_path,
        task="查看项目中有哪些文件",
        model=model,
        max_steps=2,
    )

    # 两次快照展示了“空历史 -> 工具结果写入历史”的完整数据流。
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


def test_run_agent_shows_action_and_observation(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """验证 Agent 可以把每轮动作和观察结果输出到终端。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
        capsys: pytest 提供的终端输出捕获器。
    """
    (tmp_path / "hello.py").write_text("", encoding="utf-8")

    run_agent(
        workspace=tmp_path,
        task="查看项目文件",
        model=FakeModel(),
        max_steps=2,
        show_steps=True,
    )

    output = capsys.readouterr().out

    assert "动作：" in output
    assert "list_files" in output
    assert "观察：" in output
    assert "hello.py" in output


class ForbiddenToolFakeModel:
    """请求未授权工具，用于验证权限错误的反馈数据流。"""

    def __init__(self) -> None:
        self.received_observations: list[list[dict[str, object]]] = []

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """根据观察历史返回未授权动作或结束动作。

        Args:
            task: Agent 当前处理的任务描述。
            observations: 此前动作产生的结构化观察记录。

        Returns:
            首次决策返回 ``delete_file``，收到错误记录后返回 ``finish``。
        """
        self.received_observations.append(observations.copy())

        if not observations:
            return {"tool": "delete_file"}

        return {
            "tool": "finish",
            "summary": "已经看到权限错误",
        }


def test_run_agent_returns_permission_error_to_model(tmp_path: Path) -> None:
    """验证 Agent 将权限异常转换为模型可读取的错误观察记录。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    model = ForbiddenToolFakeModel()

    summary = run_agent(
        workspace=tmp_path,
        task="删除文件",
        model=model,
        max_steps=2,
    )

    # 权限异常不会终止循环，而会以失败记录进入下一次决策。
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
    """持续返回工具动作，用于验证 Agent 的最大步数限制。"""

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """始终返回列文件动作。

        Args:
            task: Agent 当前处理的任务描述。
            observations: 此前工具执行产生的结构化观察记录。

        Returns:
            不包含结束信号的 ``list_files`` 动作。
        """
        return {"tool": "list_files"}


def test_run_agent_stops_at_max_steps(tmp_path: Path) -> None:
    """验证模型不返回结束动作时 Agent 在最大步数后报错。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    model = NeverFinishFakeModel()

    with pytest.raises(RuntimeError, match="最大步数"):
        run_agent(
            workspace=tmp_path,
            task="一直查看文件",
            model=model,
            max_steps=2,
        )


class RepairFakeModel:
    """按固定修复流程解释观察记录并选择下一步工具。"""

    def __init__(self) -> None:
        self.received_observations: list[list[dict[str, object]]] = []

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """根据最近一次观察结果推进修复流程。

        Args:
            task: Agent 当前处理的修复任务描述。
            observations: 此前工具执行产生的结构化观察记录。

        Returns:
            当前修复阶段对应的工具动作或结束动作。
        """
        self.received_observations.append(observations.copy())

        # 空历史表示尚未观察项目，修复流程从获取文件列表开始。
        if not observations:
            return {"tool": "list_files"}

        # 每个后续动作只依赖最近一次工具执行结果。
        last_observation = observations[-1]
        last_tool = last_observation["tool"]

        if last_tool == "list_files":
            return {
                "tool": "read_file",
                "path": "calculator.py",
            }

        if last_tool == "read_file":
            return {
                "tool": "write_file",
                "path": "calculator.py",
                "content": (
                    "def multiply(a: int, b: int) -> int:\n" "    return a * b\n"
                ),
            }

        if last_tool == "write_file":
            return {"tool": "run_tests"}

        # run_tests 返回 ``(退出码, 输出文本)``；退出码决定最终总结。
        test_result = last_observation["result"]

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
    """验证 Agent 完成读取、修改、测试和结束的完整修复循环。

    Args:
        tmp_path: pytest 提供的临时项目路径。
    """
    # 临时项目中的实现故意错误，配套测试定义了期望行为。
    calculator_path = tmp_path / "calculator.py"
    calculator_path.write_text(
        "def multiply(a: int, b: int) -> int:\n" "    return a / b\n",
        encoding="utf-8",
    )
    test_path = tmp_path / "test_calculator.py"
    test_path.write_text(
        "from calculator import multiply\n\n"
        "def test_multiply() -> None:\n"
        "    assert multiply(2, 3) == 6\n",
        encoding="utf-8",
    )

    model = RepairFakeModel()

    summary = run_agent(
        workspace=tmp_path,
        task="修复计算器，使测试通过",
        model=model,
        max_steps=5,
    )

    # 磁盘内容验证写入动作真实生效，而不是只返回成功文本。
    assert calculator_path.read_text(encoding="utf-8") == (
        "def multiply(a: int, b: int) -> int:\n" "    return a * b\n"
    )

    assert summary == "已修复代码并通过测试"

    # 最后一条观察记录连接了真实 pytest 结果和模型的结束决策。
    last_observation = model.received_observations[-1][-1]
    assert last_observation["tool"] == "run_tests"

    test_result = last_observation["result"]
    assert isinstance(test_result, tuple)
    assert test_result[0] == 0
    assert "1 passed" in test_result[1]
