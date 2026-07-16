from pathlib import Path

from knowflow_agent.tools import list_files, read_file


def test_list_files_returns_sorted_relative_paths(tmp_path: Path) -> None:
    (tmp_path / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    (tmp_path / "folder" / "a.py").write_text("", encoding="utf-8")

    assert list_files(tmp_path) == ["b.py", "folder/a.py"]


def test_read_file_returns_content(tmp_path: Path) -> None:
    # 创建一个临时文件，模拟 Agent 要读取的代码文件。
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('你好')", encoding="utf-8")

    assert read_file(tmp_path, "hello.py") == "print('你好')"
