from pathlib import Path


def list_files(workspace: Path) -> list[str]:
    """列出工作区中的文件路径。"""
    return sorted(
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    )
