from pathlib import Path


def list_files(workspace: Path) -> list[str]:
    """列出工作区中的文件路径。"""
    # 定义一个叫 list_files 的函数。
    # workspace: Path：参数应该是一个 Path 对象
    # -> list[str]：函数返回一个字符串列表
    # rglob("*") 找到所有路径
    # if path.is_file() 排除文件夹
    # relative_to() 转成相对路径
    # as_posix() 统一使用 /
    # sorted() 排序
    # 返回 list[str]
    return sorted(
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    )


def read_file(workspace: Path, relative_path: str) -> str:
    """读取工作区中的 UTF-8 文本文件。"""
    # 定义读取文件内容的工具。
    # workspace: Path：工作区路径
    # relative_path: str：相对于工作区的文件路径
    # -> str：返回文件中的文本
    file_path = workspace / relative_path
    return file_path.read_text(encoding="utf-8")
