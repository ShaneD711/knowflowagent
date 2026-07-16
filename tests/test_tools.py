from pathlib import Path

from knowflow_agent.tools import list_files


def test_list_files_returns_sorted_relative_paths(tmp_path: Path) -> None:
    (tmp_path / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    (tmp_path / "folder" / "a.py").write_text("", encoding="utf-8")

    assert list_files(tmp_path) == ["b.py", "folder/a.py"]
