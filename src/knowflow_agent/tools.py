from pathlib import Path


# 定义一个叫 list_files 的函数。
# workspace: Path：参数应该是一个 Path 对象
# -> list[str]：函数返回一个字符串列表
def list_files(workspace: Path) -> list[str]:
    """列出工作区中的文件路径。"""
    # rglob("*") 找到所有路径
    # if path.is_file() 排除文件夹
    # relative_to() 转成相对路径
    # as_posix() 统一使用 /
    # sorted() 排序
    # 返回 list[str]
    return sorted(
        path.relative_to(workspace).as_posix()
        for path in workspace.rglob("*")
        if path.is_file()
    )
