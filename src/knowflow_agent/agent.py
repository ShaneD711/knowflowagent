from pathlib import Path
from typing import Protocol

from knowflow_agent import permissions, tools


class Model(Protocol):
    """定义 Agent 核心依赖的模型决策接口。

    任何模型或模型适配器只要实现 ``decide``，就可以交给
    ``run_agent`` 使用。Agent 核心因此不需要了解具体模型或网络 API。
    """

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """根据任务和已有观察记录选择下一步动作。

        Args:
            task: 用户希望 Agent 完成的任务。
            observations: 之前每一步工具执行成功或失败的结构化记录。

        Returns:
            包含工具名称及其参数的动作字典。
        """
        ...

def execute_action(
    workspace: Path,
    action: dict[str, str],
) -> object:
    """验证模型动作，并调用白名单中的对应工具。

    该函数是模型决策与真实文件操作之间的执行边界。读取和写入文件前
    会先检查路径权限；未列入白名单的工具不会进入工具层。

    Args:
        workspace: 本次任务允许访问的工作区根目录。
        action: 模型返回的动作，包含工具名称及该工具需要的参数。

    Returns:
        工具产生的结果，例如文件列表、文件内容或测试结果。

    Raises:
        PermissionError: 请求的工具未获授权，或目标路径不符合权限规则。
    """
    # 模型只选择工具名；执行器负责把它映射到经过授权的 Python 函数。
    tool_name = action["tool"]

    if tool_name == "list_files":
        return tools.list_files(workspace)

    if tool_name == "read_file":
        relative_path = action["path"]

        # 文件读取前先收紧路径范围，避免模型观察工作区外的内容。
        permissions.resolve_workspace_path(workspace, relative_path)

        return tools.read_file(workspace, relative_path)

    if tool_name == "write_file":
        relative_path = action["path"]

        # 文件写入前同时检查工作区边界和允许修改的文件类型。
        permissions.resolve_writable_python_path(workspace, relative_path)

        tools.write_file(
            workspace,
            relative_path,
            action["content"],
        )
        return f"已写入文件：{relative_path}"

    if tool_name == "run_tests":
        # 只开放固定的 pytest 命令，不接受模型生成的任意 Shell 命令。
        return tools.run_tests(workspace)

    # 默认拒绝白名单之外的工具，防止模型扩张自己的执行权限。
    raise PermissionError(f"不允许执行工具：{tool_name}")


def run_agent(
    workspace: Path,
    task: str,
    model: Model,
    max_steps: int = 5,
) -> str:
    """运行 Agent 的“决策、执行、观察、再决策”反馈循环。

    每轮先把任务和已有观察记录交给模型。模型可以结束任务，也可以选择
    一个工具。工具结果或权限错误会被整理成新的观察记录，供下一轮决策
    使用。

    Args:
        workspace: Agent 可以观察和操作的工作区根目录。
        task: 用户交给 Agent 的任务描述。
        model: 实现 ``Model`` 接口的模型或模型适配器。
        max_steps: 最多允许模型进行的决策轮数。

    Returns:
        模型通过 ``finish`` 动作提供的任务总结。

    Raises:
        RuntimeError: 达到最大决策轮数后模型仍未结束任务。
    """
    observations: list[dict[str, object]] = []

    for _ in range(max_steps):
        action = model.decide(task, observations)

        if action["tool"] == "finish":
            return action["summary"]

        try:
            result = execute_action(workspace, action)

            observation = {
                "ok": True,
                "tool": action["tool"],
                "result": result,
            }
        except PermissionError as error:
            observation = {
                "ok": False,
                "tool": action["tool"],
                "error": str(error),
            }

        observations.append(observation)

    raise RuntimeError("Agent 达到最大步数仍未结束")
