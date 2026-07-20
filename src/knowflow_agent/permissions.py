from pathlib import Path


def resolve_workspace_path(
    workspace: Path,
    relative_path: str,
) -> Path:
    """解析工作区内的相对路径，并阻止路径越界。

    Args:
        workspace: Agent 获准访问的工作区根目录。
        relative_path: 模型提交的工作区相对路径。

    Returns:
        位于工作区内部的目标绝对路径。

    Raises:
        PermissionError: 解析后的目标路径位于工作区之外。
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
    """验证模型准备写入的是工作区内的 Python 文件。

    Args:
        workspace: Agent 获准操作的工作区根目录。
        relative_path: 模型准备写入的工作区相对路径。

    Returns:
        通过工作区边界和文件类型检查的目标绝对路径。

    Raises:
        PermissionError: 目标位于工作区外，或文件扩展名不是 ``.py``。
    """
    resolved_path = resolve_workspace_path(workspace, relative_path)

    if resolved_path.suffix != ".py":
        raise PermissionError("只允许修改 Python 文件（.py）")

    return resolved_path
