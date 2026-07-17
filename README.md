# KnowFlow Agent

## 当前进度

- [x] 准备包含错误和失败测试的示例项目
- [x] 实现并测试列出文件、读取文件、写入文件和运行测试四个工具
- [x] 阻止越出工作区的路径
- [x] 限制模型只能写入工作区内的 Python 文件
- [x] 拒绝白名单以外的工具
- [ ] 把读取文件和运行测试接入动作执行器
- [ ] 使用假模型完成 Agent 反馈循环
- [ ] 接入 DeepSeek
- [ ] 让 Agent 自动修复示例项目

## 项目结构

```text
demo/
├── calculator.py          # 包含真实错误的示例代码
└── test_calculator.py     # 用来描述正确结果的示例测试

src/knowflow_agent/
├── tools.py               # 执行列文件、读文件、写文件和运行测试
├── permissions.py         # 检查路径和允许写入的文件类型
└── agent.py               # 把模型动作交给经过允许的工具执行

tests/
├── test_tools.py          # 验证每个底层工具
├── test_permissions.py    # 验证允许和拒绝规则
└── test_agent.py          # 验证动作、权限和工具能正确连接
```

## 模块职责

| 模块 | 作用 | 接收的数据 | 返回的数据 |
| --- | --- | --- | --- |
| `tools.py` | 执行真实的文件操作和测试命令 | 工作区、文件路径、文件内容 | 文件列表、文件文本、测试结果 |
| `permissions.py` | 在操作执行前检查安全规则 | 工作区和模型提交的路径 | 安全的真实路径，或权限错误 |
| `agent.py` | 识别模型动作并选择白名单工具 | 工作区和动作字典 | 工具产生的观察结果 |
| `tests/` | 证明允许的操作成功、禁止的操作被拒绝 | 临时工作区和模拟动作 | 通过或失败的测试结果 |

## 详细执行流程

每个核心文件包含哪些函数，以及函数内部的数据流，记录在 [docs/code-flow.md](docs/code-flow.md)。

## 当前数据流

以写入 Python 文件为例：

```text
模型生成动作字典
        ↓
execute_action 读取工具名称和参数
        ↓
permissions 检查路径和文件类型
        ↓
tools.write_file 修改真实文件
        ↓
execute_action 返回“已写入文件”观察结果
```

模型只能提交类似下面的结构化动作，不能直接操作磁盘：

```python
action = {
    "tool": "write_file",
    "path": "hello.py",
    "content": "print('新代码')",
}
```
