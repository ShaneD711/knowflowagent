from calculator import divide


def test_divide_six_by_two() -> None:
    """验证除法结果，作为 Agent 判断修复是否成功的标准。"""
    assert divide(6, 2) == 3
