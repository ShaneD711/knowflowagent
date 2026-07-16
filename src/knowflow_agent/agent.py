from pathlib import Path

from knowflow_agent import tools


def execute_action(
    workspace: Path,
    action: dict[str, str],
) -> object:
    """让 Agent 执行经过允许的工具动作。

    作用：接收模型给出的动作，并交给对应的工具执行。
    输入：工作区目录，以及包含工具名称的动作。
    处理：读取动作中的工具名称，判断它是否是允许的工具。
    输出：工具执行后产生的观察结果。
    """
    tool_name = action["tool"]

    if tool_name == "list_files":
        return tools.list_files(workspace)

    raise ValueError(f"不允许执行工具：{tool_name}")
