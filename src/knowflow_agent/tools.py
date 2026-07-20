import subprocess
import sys
from pathlib import Path


def list_files(workspace: Path) -> list[str]:
    """列出工作区内可供 Agent 观察的所有文件。

    Args:
        workspace: 需要遍历的工作区根目录。

    Returns:
        按名称排序的相对文件路径列表，路径分隔符统一为 ``/``。
    """
    return sorted(
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    )


def read_file(workspace: Path, relative_path: str) -> str:
    """读取工作区内指定 UTF-8 文件的完整内容。

    Args:
        workspace: 目标文件所在的工作区根目录。
        relative_path: 目标文件相对于工作区的路径。

    Returns:
        文件中的完整文本。

    Raises:
        FileNotFoundError: 目标文件不存在。
        UnicodeDecodeError: 目标文件不是有效的 UTF-8 文本。
    """
    file_path = workspace / relative_path
    return file_path.read_text(encoding="utf-8")


def write_file(
    workspace: Path,
    relative_path: str,
    content: str,
) -> None:
    """使用 UTF-8 编码替换工作区内指定文件的内容。

    Args:
        workspace: 目标文件所在的工作区根目录。
        relative_path: 目标文件相对于工作区的路径。
        content: 需要保存到目标文件的完整文本。

    Returns:
        None。
    """
    file_path = workspace / relative_path
    file_path.write_text(content, encoding="utf-8")


def run_tests(workspace: Path) -> tuple[int, str]:
    """在工作区中运行固定的 pytest 命令并收集结果。

    Args:
        workspace: 需要运行测试的工作区根目录。

    Returns:
        二元组 ``(exit_code, output)``。``exit_code`` 是 pytest 退出码，
        ``output`` 合并了标准输出和标准错误。
    """
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    return result.returncode, output
