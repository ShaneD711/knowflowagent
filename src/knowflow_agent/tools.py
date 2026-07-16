import subprocess
import sys
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


def write_file(
    workspace: Path,
    relative_path: str,
    content: str,
) -> None:
    """让 Agent 把生成的新代码保存到指定文件。

    作用：Agent 读取并分析代码后，用这个工具把修改结果写回工作区。
    输入：工作区目录、目标文件的相对路径、要保存的新代码。
    处理：定位目标文件，再使用 UTF-8 编码覆盖原有内容。
    结果：目标文件中的旧代码被替换为新代码。
    """
    file_path = workspace / relative_path
    file_path.write_text(content, encoding="utf-8")


def run_tests(workspace: Path) -> tuple[int, str]:
    """让 Agent 运行工作区测试并获得测试结果。

    作用：Agent 写入代码后，用这个工具判断修改是否正确。
    输入：需要运行测试的工作区目录。
    处理：在工作区中运行固定的 pytest 命令，并收集测试结果。
    输出：pytest 的退出码和完整输出文本。
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
