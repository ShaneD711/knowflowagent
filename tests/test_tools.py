from pathlib import Path

from knowflow_agent import tools


def test_list_files_returns_sorted_relative_paths(tmp_path: Path) -> None:
    """确保 list_files 能给 Agent 提供准确、稳定的文件清单。"""
    # 准备：在临时工作区创建两个文件和一个文件夹。
    (tmp_path / "b.py").write_text("", encoding="utf-8")
    (tmp_path / "folder").mkdir()
    (tmp_path / "folder" / "a.py").write_text("", encoding="utf-8")

    # 执行：让工具观察临时工作区。
    actual_files = tools.list_files(tmp_path)

    # 验证：输出只包含文件，使用相对路径，并且顺序固定。
    assert actual_files == ["b.py", "folder/a.py"]


def test_read_file_returns_content(tmp_path: Path) -> None:
    """确保 read_file 返回的内容与 Agent 选择的文件完全一致。"""
    # 准备：创建一个临时文件，模拟 Agent 要读取的代码文件。
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('你好')", encoding="utf-8")

    # 执行：让工具读取指定文件。
    actual_content = tools.read_file(tmp_path, "hello.py")

    # 验证：工具返回的文本与文件中的文本完全相同。
    assert actual_content == "print('你好')"


def test_write_file_replaces_content(tmp_path: Path) -> None:
    """确保 write_file 把 Agent 生成的新代码保存到指定文件。"""
    # 准备：创建一个包含旧代码的临时文件。
    file_path = tmp_path / "hello.py"
    file_path.write_text("print('旧内容')", encoding="utf-8")
    new_content = "print('新内容')"

    # 执行：把新代码交给 write_file。
    tools.write_file(tmp_path, "hello.py", new_content)

    # 验证：磁盘中的文件已经变成新代码。
    actual_content = file_path.read_text(encoding="utf-8")
    assert actual_content == new_content


def test_run_tests_returns_passing_result(tmp_path: Path) -> None:
    """确保 run_tests 能把测试结果返回给 Agent。"""
    # 准备：创建一个必定通过的临时测试。
    test_file = tmp_path / "test_example.py"
    test_file.write_text(
        "def test_example():\n"
        "    assert 1 + 1 == 2\n",
        encoding="utf-8",
    )

    # 执行：让工具在临时工作区运行测试。
    exit_code, output = tools.run_tests(tmp_path)

    # 验证：退出码表示成功，输出也说明测试已经通过。
    assert exit_code == 0
    assert "1 passed" in output
