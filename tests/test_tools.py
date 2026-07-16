from pathlib import Path

from knowflow_agent.tools import list_files, read_file


def test_list_files_returns_sorted_relative_paths(tmp_path: Path) -> None:
    """确保 list_files 能给 Agent 提供准确、稳定的文件清单。"""
    # 准备：在临时工作区创建两个文件和一个文件夹。
    (tmp_path / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    (tmp_path / "folder" / "a.py").write_text("", encoding="utf-8")

    # 执行：让工具观察临时工作区。
    actual_files = list_files(tmp_path)

    # 验证：输出只包含文件，使用相对路径，并且顺序固定。
    assert actual_files == ["b.py", "folder/a.py"]


def test_read_file_returns_content(tmp_path: Path) -> None:
    """确保 read_file 返回的内容与 Agent 选择的文件完全一致。"""
    # 准备：创建一个临时文件，模拟 Agent 要读取的代码文件。
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('你好')", encoding="utf-8")

    # 执行：让工具读取指定文件。
    actual_content = read_file(tmp_path, "hello.py")

    # 验证：工具返回的文本与文件中的文本完全相同。
    assert actual_content == "print('你好')"
