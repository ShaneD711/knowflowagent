from pathlib import Path


def resolve_workspace_path(
    workspace: Path,
    relative_path: str,
) -> Path:
    """解析并检查模型提交的工作区路径。

    作用：在工具执行前，阻止模型访问工作区以外的文件。
    输入：工作区目录和模型提交的文件路径。
    处理：计算工作区和目标文件的真实绝对路径，再判断包含关系。
    输出：确认安全的目标文件绝对路径。
    """
    resolved_workspace = workspace.resolve()
    resolved_path = (resolved_workspace / relative_path).resolve()

    if not resolved_path.is_relative_to(resolved_workspace):
        raise PermissionError("不能访问工作区以外的路径")

    return resolved_path


def resolve_writable_python_path(
    workspace: Path,
    relative_path: str,
) -> Path:
    """解析并检查模型准备写入的 Python 文件路径。

    作用：确保模型只能修改工作区内部的 Python 文件，其他类型的文件不能修改。
    输入：工作区目录和模型准备写入的文件路径。
    处理：先检查路径没有逃出工作区，再检查扩展名是否为 .py。
    输出：确认允许写入的目标文件绝对路径。
    """
    resolved_path = resolve_workspace_path(workspace, relative_path)

    if resolved_path.suffix != ".py":
        raise PermissionError("只允许修改 Python 文件（.py）")

    return resolved_path
