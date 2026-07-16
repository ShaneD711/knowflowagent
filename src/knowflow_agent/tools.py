from pathlib import Path


def list_files(workspace: Path) -> list[str]:
    """列出工作区中的文件路径。

    数据流：工作区 -> 找到所有内容 -> 只保留文件 -> 相对路径列表。
    """
    return sorted(
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    )


def read_file(workspace: Path, relative_path: str) -> str:
    """读取工作区中的 UTF-8 文本文件。

    数据流：工作区 + 相对路径 -> 文件路径 -> 文件文本。
    """
    # 先定位要读取的文件，再把文件内容作为观察结果返回给 Agent。
    file_path = workspace / relative_path
    return file_path.read_text(encoding="utf-8")
