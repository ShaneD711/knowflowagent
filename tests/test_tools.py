from pathlib import Path

from knowflow_agent import tools


def test_list_files_returns_sorted_relative_paths(tmp_path: Path) -> None:
    """验证文件清单只包含排序后的工作区相对路径。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    # 准备：构造包含根目录文件、子目录和子目录文件的工作区。
    (tmp_path / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    (tmp_path / "folder" / "a.py").write_text("", encoding="utf-8")

    # 执行：收集工作区内的文件路径。
    actual_files = tools.list_files(tmp_path)

    # 验证：目录被排除，文件以稳定排序的相对路径返回。
    assert actual_files == ["b.py", "folder/a.py"]


def test_read_file_returns_content(tmp_path: Path) -> None:
    """验证读取工具返回目标文件的 UTF-8 文本。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    # 准备：在工作区写入内容已知的 Python 文件。
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('你好')", encoding="utf-8")

    # 执行：通过工作区和相对路径读取目标文件。
    actual_content = tools.read_file(tmp_path, "hello.py")

    # 验证：读取结果与磁盘中的原始文本一致。
    assert actual_content == "print('你好')"


def test_write_file_replaces_content(tmp_path: Path) -> None:
    """验证写入工具使用新内容替换目标文件。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    # 准备：创建包含旧内容的目标文件，并准备替换内容。
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('旧内容')", encoding="utf-8")
    new_content = "print('新内容')"

    # 执行：将替换内容写入工作区中的目标文件。
    tools.write_file(tmp_path, "hello.py", new_content)

    # 验证：重新读取磁盘文件，确认替换内容已经持久化。
    actual_content = file_path.read_text(encoding="utf-8")
    assert actual_content == new_content


def test_run_tests_returns_passing_result(tmp_path: Path) -> None:
    """验证测试工具返回成功退出码和 pytest 输出。

    Args:
        tmp_path: pytest 提供的临时工作区路径。
    """
    # 准备：在临时工作区创建一个确定能够通过的测试。
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "def test_example():\n"
        "    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )

    # 执行：在该工作区运行 pytest 并收集退出码和输出文本。
    exit_code, output = tools.run_tests(tmp_path)

    # 验证：退出码和输出文本共同表明测试通过。
    assert exit_code == 0
    assert "1 passed" in output
