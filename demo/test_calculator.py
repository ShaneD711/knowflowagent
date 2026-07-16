from calculator import divide


def test_divide_six_by_two() -> None:
    # assert 的意思是：断言这个条件必须成立，否则测试失败。
    assert divide(6, 2) == 3
