# 函数执行流程

阅读这个项目时，不需要把每个函数当成孤立的代码。核心程序只有三层：`agent.py` 接收动作，`permissions.py` 判断动作是否安全，`tools.py` 执行真实操作。

```text
模型生成动作
    ↓
agent.py 识别动作
    ↓
permissions.py 检查权限
    ↓
tools.py 操作文件或运行测试
    ↓
执行结果返回给 Agent
```

## 动作从 `agent.py` 进入程序

`agent.py` 目前只有一个函数 `execute_action(workspace, action)`。`workspace` 表示 Agent 可以操作的工作区，`action` 是模型生成的动作字典。

例如，模型想查看文件时会产生：

```python
{"tool": "list_files"}
```

`execute_action` 先读取 `action["tool"]`，得到工具名称。名称是 `list_files` 时，它把工作区交给 `tools.list_files`，然后把文件列表直接返回。

写入文件的流程更长，因为写入会改变磁盘。模型需要同时提供工具名称、文件路径和新内容：

```python
{
    "tool": "write_file",
    "path": "hello.py",
    "content": "print('新代码')",
}
```

`execute_action` 取出路径后，不会马上写入。它先调用 `permissions.resolve_writable_python_path`。只有权限检查通过，才会继续调用 `tools.write_file`，最后返回“已写入文件”的观察结果。

```text
execute_action
    ↓ 读取 tool
write_file
    ↓ 取出 path
resolve_writable_python_path
    ↓ 检查通过
tools.write_file
    ↓
返回写入结果
```

如果工具名称既不是 `list_files`，也不是当前允许的 `write_file`，`execute_action` 会抛出 `PermissionError`。因此，模型可以提出动作，但真正允许执行哪些动作由程序决定。

## `permissions.py` 先检查范围，再检查文件类型

`permissions.py` 包含 `resolve_workspace_path` 和 `resolve_writable_python_path`。这两个函数不是彼此独立的规则，第二个函数建立在第一个函数之上。

`resolve_workspace_path(workspace, relative_path)` 先把工作区转换成真实绝对路径，再把模型提供的相对路径转换成目标绝对路径。随后，它判断目标路径是否仍在工作区内部。目标在工作区内时返回真实路径；目标逃出工作区时抛出 `PermissionError`。

```text
工作区 + 相对路径
        ↓
两个真实绝对路径
        ↓
判断目标是否属于工作区
   ↙                    ↘
属于                    不属于
 ↓                        ↓
返回路径              拒绝访问
```

`resolve_writable_python_path(workspace, relative_path)` 用于写入前的进一步检查。它先调用 `resolve_workspace_path`，所以越界路径会先被拒绝；路径没有越界时，它再检查扩展名是否为 `.py`。两个条件都满足后，才返回允许写入的绝对路径。

```text
准备写入的路径
      ↓
是否在工作区内
      ↓ 是
是否为 .py 文件
   ↙           ↘
 是             否
 ↓               ↓
返回路径       拒绝写入
```

## `tools.py` 负责产生真实结果

权限模块只判断“能不能做”，真正接触文件和进程的是 `tools.py`。这个文件中的四个函数对应 Agent 修复代码时的四种基本操作。

Agent 进入一个陌生项目后，先通过 `list_files(workspace)` 观察有哪些文件。这个函数递归找到工作区中的所有文件，把它们转换成相对路径，排序后返回文件列表。

Agent 从列表中选择目标文件后，通过 `read_file(workspace, relative_path)` 读取代码。这个函数拼接工作区和相对路径，使用 UTF-8 读取文件，再返回完整文本。

模型分析代码并生成修改结果后，`write_file(workspace, relative_path, content)` 使用 UTF-8 覆盖目标文件。它只负责执行写入，不负责检查权限，因此必须由 `execute_action` 在调用前完成权限检查。

写入完成后，`run_tests(workspace)` 在指定工作区启动固定的 `pytest -q`。它等待测试结束，收集正常输出和错误输出，最后返回退出码与完整输出文本。Agent 将根据这个结果判断修改是否正确。

四个工具组成了未来 Agent 循环中的完整操作顺序：

```text
list_files        read_file        write_file        run_tests
了解项目文件  →  读取目标代码  →  保存修改结果  →  验证修改是否正确
```

当前 `read_file` 和 `run_tests` 已经在工具层实现并通过测试，但还没有接入 `execute_action`。

## 三个测试文件分别守住一层

测试代码使用 pytest 提供的 `tmp_path` 创建临时工作区。测试可以在其中创建和修改文件，不会碰到真实项目文件。每个测试都遵循“准备数据 → 执行函数 → 验证结果”的顺序。

`tests/test_tools.py` 直接验证工具层。`test_list_files_returns_sorted_relative_paths` 检查文件列表；`test_read_file_returns_content` 检查读取结果；`test_write_file_replaces_content` 检查磁盘内容是否被替换；`test_run_tests_returns_passing_result` 检查测试退出码和输出。它回答的问题是：每个工具单独运行时是否正确。

`tests/test_permissions.py` 直接验证权限层。`test_resolve_workspace_path_rejects_escape` 和 `test_resolve_workspace_path_allows_inside_path` 从拒绝、允许两个方向验证工作区边界；`test_resolve_writable_python_path_rejects_non_python_file` 和 `test_resolve_writable_python_path_allows_python_file` 从拒绝、允许两个方向验证文件类型规则。它回答的问题是：安全规则能否同时挡住错误请求并放行正常请求。

`tests/test_agent.py` 验证模块之间的连接。`test_execute_action_runs_list_files` 确认允许的观察动作能够到达工具层；`test_execute_action_rejects_unknown_tool` 确认未知工具被白名单挡住；`test_execute_action_runs_write_file` 确认合法写入经过权限检查后能够执行；`test_execute_action_rejects_non_python_write` 确认非法写入被拒绝，并且磁盘中的原有内容没有改变。

三个测试文件由内向外形成保护：

```text
test_tools.py        验证工具本身
       ↑
test_permissions.py  验证安全规则
       ↑
test_agent.py        验证动作、权限和工具的完整连接
```

如果 `test_tools.py` 失败，先检查具体工具；如果 `test_permissions.py` 失败，先检查路径或文件类型规则；如果只有 `test_agent.py` 失败，通常说明模块之间的调用顺序或传递数据出现了问题。
