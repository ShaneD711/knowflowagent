from pathlib import Path

import pytest

from knowflow_agent.permissions import (
    resolve_workspace_path,
    resolve_writable_python_path,
)


def test_resolve_workspace_path_rejects_escape(tmp_path: Path) -> None:
    """验证工作区路径检查拒绝指向外部的相对路径。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    # 准备：构造一个通过父目录跳出工作区的相对路径。
    unsafe_path = "../outside.py"

    # 执行并验证：路径解析必须以权限错误拒绝越界访问。
    with pytest.raises(PermissionError, match="工作区以外"):
        resolve_workspace_path(tmp_path, unsafe_path)


def test_resolve_workspace_path_allows_inside_path(tmp_path: Path) -> None:
    """验证工作区路径检查接受内部文件路径。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    # 准备：在工作区子目录中创建一个目标文件。
    folder = tmp_path / "folder"
    folder.mkdir()
    file_path = folder / "hello.py"
    file_path.write_text("", encoding="utf-8")

    # 执行：解析指向该文件的工作区相对路径。
    resolved_path = resolve_workspace_path(tmp_path, "folder/hello.py")

    # 验证：解析结果是目标文件的规范化绝对路径。
    assert resolved_path == file_path.resolve()


def test_resolve_writable_python_path_rejects_non_python_file(
    tmp_path: Path,
) -> None:
    """验证可写路径检查拒绝非 Python 文件。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    # 准备：构造一个工作区内的普通文本文件路径。
    unsafe_path = "notes.txt"

    # 执行并验证：可写路径检查必须以权限错误拒绝该扩展名。
    with pytest.raises(PermissionError, match="Python 文件"):
        resolve_writable_python_path(tmp_path, unsafe_path)


def test_resolve_writable_python_path_allows_python_file(
    tmp_path: Path,
) -> None:
    """验证可写路径检查接受工作区内的 Python 文件。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    # 准备：在工作区创建一个 Python 文件。
    file_path = tmp_path / "hello.py"
    file_path.write_text("", encoding="utf-8")

    # 执行：解析并检查该文件的工作区相对路径。
    resolved_path = resolve_writable_python_path(tmp_path, "hello.py")

    # 验证：检查结果是允许写入文件的规范化绝对路径。
    assert resolved_path == file_path.resolve()
