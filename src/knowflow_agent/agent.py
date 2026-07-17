from pathlib import Path

from knowflow_agent import permissions, tools


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
