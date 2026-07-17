from pathlib import Path

import pytest

from knowflow_agent.permissions import (
    resolve_workspace_path,
    resolve_writable_python_path,
)


def test_resolve_workspace_path_rejects_escape(tmp_path: Path) -> None:
    """确保模型不能使用相对路径逃离工作区。"""

    # 准备：模拟模型提交一个指向工作区外部的路径。
    unsafe_path = "../outside.py"

    # 执行并验证：权限检查必须拒绝这个路径。
    with pytest.raises(PermissionError, match="工作区以外"):
        resolve_workspace_path(tmp_path, unsafe_path)


def test_resolve_workspace_path_allows_inside_path(tmp_path: Path) -> None:
    """确保工作区内部的正常路径能够通过权限检查。"""
    # 准备：在临时工作区中创建一个正常代码文件。
    folder = tmp_path / "folder"
    folder.mkdir()
    file_path = folder / "hello.py"
    file_path.write_text("", encoding="utf-8")

    # 执行：权限模块解析工作区内部的相对路径。
    resolved_path = resolve_workspace_path(tmp_path, "folder/hello.py")

    # 验证：返回结果就是工作区内部文件的真实路径。
    assert resolved_path == file_path.resolve()


def test_resolve_writable_python_path_rejects_non_python_file(
    tmp_path: Path,
) -> None:
    """确保模型不能修改非 Python 文件。"""

    # 准备：模拟模型请求修改一个普通文本文件。
    unsafe_path = "notes.txt"

    # 执行并验证：写入权限必须拒绝非 Python 文件。
    with pytest.raises(PermissionError, match="Python 文件"):
        resolve_writable_python_path(tmp_path, unsafe_path)


def test_resolve_writable_python_path_allows_python_file(
    tmp_path: Path,
) -> None:
    """确保工作区内的 Python 文件可以通过写入权限检查。"""
    # 准备：创建一个允许模型修改的 Python 文件。
    file_path = tmp_path / "hello.py"
    file_path.write_text("", encoding="utf-8")

    # 执行：权限模块检查这个 Python 文件。
    resolved_path = resolve_writable_python_path(tmp_path, "hello.py")

    # 验证：返回结果就是允许写入的文件真实路径。
    assert resolved_path == file_path.resolve()
