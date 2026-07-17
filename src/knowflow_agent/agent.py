from pathlib import Path
from typing import Protocol

from knowflow_agent import permissions, tools


class Model(Protocol):
    """定义 Agent 核心依赖的模型接口。

    作用：让假模型和未来的 DeepSeek 都能被同一个 Agent 循环调用。
    输入：用户任务和前面步骤累积的观察结果。
    处理：具体模型分析当前状态并选择下一步动作。
    输出：包含工具名称和参数的动作字典。
    """

    def decide(
        self,
        task: str,
        observations: list[dict[str, object]],
    ) -> dict[str, str]:
        """根据任务和已有观察结果返回下一步动作。"""
        ...

def execute_action(
    workspace: Path,
    action: dict[str, str],
) -> object:
    """把模型给出的动作转换成受控制的工具调用。

    作用：连接模型决策和工具执行。模型只能提出动作，不能直接操作文件。
    输入：允许操作的工作区，以及包含工具名称和参数的动作字典。
    处理：根据工具名称选择白名单工具；访问文件前必须先经过权限检查。
    输出：把工具执行结果返回给 Agent，作为下一次决策的观察结果。
    拒绝：工具不在白名单中时停止执行，不让请求进入工具层。
    """
    # 模型只提供工具名称；真正调用哪个 Python 函数由执行器决定。
    tool_name = action["tool"]

    if tool_name == "list_files":
        return tools.list_files(workspace)

    if tool_name == "read_file":
        relative_path = action["path"]

        # 读取前先确认目标文件仍然位于工作区内。
        permissions.resolve_workspace_path(workspace, relative_path)

        return tools.read_file(workspace, relative_path)

    if tool_name == "write_file":
        relative_path = action["path"]

        # 写入会改变磁盘，必须先确认路径和文件类型都符合权限规则。
        permissions.resolve_writable_python_path(workspace, relative_path)

        tools.write_file(
            workspace,
            relative_path,
            action["content"],
        )
        return f"已写入文件：{relative_path}"

    if tool_name == "run_tests":
        # 模型只能触发固定测试命令，不能提供任意 Shell 命令。
        return tools.run_tests(workspace)

    # 没有明确加入白名单的工具，不能进入真正执行操作的工具层。
    raise PermissionError(f"不允许执行工具：{tool_name}")


def run_agent(
    workspace: Path,
    task: str,
    model: Model,
    max_steps: int = 5,
) -> str:
    """运行最小 Agent 反馈循环。

    作用：让模型根据工具结果持续选择下一步动作，直到模型决定结束。
    输入：工作区、用户任务、模型和允许执行的最大步数。
    处理：请求模型决策，把执行结果或权限错误保存为观察结果，再次请求决策。
    输出：模型结束任务时提供的总结文本。
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
