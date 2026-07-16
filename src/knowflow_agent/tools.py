from pathlib import Path


def list_files(workspace: Path) -> list[str]:
    """让 Agent 获取工作区内可查看的文件清单。

    作用：Agent 先用这个工具了解项目中有哪些文件，再决定读取哪个文件。
    输入：允许 Agent 观察的工作区目录。
    处理：找到工作区中的所有内容，排除文件夹，并转换成相对路径。
    输出：经过排序的文件路径字符串列表。
    """
    return sorted(
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    )


def read_file(workspace: Path, relative_path: str) -> str:
    """让 Agent 获取工作区内指定文件的文本内容。

    作用：Agent 从文件清单中选择一个文件后，用这个工具查看代码内容。
    输入：工作区目录和要读取的相对文件路径。
    处理：拼接出文件路径，再使用 UTF-8 编码读取文件。
    输出：文件中的完整文本。
    """
    # 先定位要读取的文件，再把文件内容作为观察结果返回给 Agent。
    file_path = workspace / relative_path
    return file_path.read_text(encoding="utf-8")
