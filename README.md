# KnowFlow Agent

KnowFlow Agent 是一个 MVP 版 SWE Agent，后续会在这个最小版本上继续完善。它让模型根据任务选择工具，由 Agent 检查并执行动作，再根据真实工具结果继续决策，直到完成任务或达到最大步数。

项目目前向模型开放 `list_files`、`read_file`、`write_file` 和 `run_tests` 四个工具。模型还可以返回 `finish` 动作结束任务，但不能直接访问文件或执行任意 Shell 命令。

## 运行真实修复演示

`demo/calculator.py` 中故意把除法写成了乘法：

```python
return a * b
```

`demo/test_calculator.py` 则要求 `divide(6, 2)` 返回 `3`。这构成了一个真实、可以重复验证的错误。

先在当前 PowerShell 终端设置 DeepSeek API Key：

```powershell
$env:DEEPSEEK_API_KEY = "你的 API Key"
```

然后从项目根目录运行：

```powershell
py .\examples\run_deepseek_agent.py
```

终端会显示每轮动作和观察结果。正常情况下，Agent 会读取示例代码和测试，把错误实现修改为 `return a / b`，运行测试，并在看到测试通过后返回任务总结。

演示运行完成后，`demo/calculator.py` 会处于修复后的正确状态。若要重新演示，需要先把它恢复成 `return a * b`。

## Agent 怎样完成一次任务

模型负责决策，Agent 负责控制，权限模块负责检查，工具负责真实执行。

### 1. 入口程序启动反馈循环

`examples/run_deepseek_agent.py` 是真实 DeepSeek 演示的入口程序。它准备以下三个数据：

- `workspace`：Agent 可以观察和操作的工作区路径；
- `task`：本次需要完成的任务描述；
- `adapter`：负责连接 Agent 数据与 DeepSeek 请求格式的模型适配器。

入口程序把它们传给 `src/knowflow_agent/agent.py/run_agent`：

```python
summary = run_agent(
    workspace=workspace,
    task="修复 calculator.py 中的错误，使测试通过",
    model=adapter,
    max_steps=8,
)
```

`adapter` 进入 `run_agent` 后由参数 `model` 接收。这样，Agent 核心只依赖统一的 `Model` 接口，不需要知道当前使用的是真实 DeepSeek 适配器还是测试中的假模型。

### 2. Agent 创建观察历史

`src/knowflow_agent/agent.py/run_agent` 首先创建一个空列表：

```python
observations = []
```

`observations` 保存前面步骤产生的工具结果或权限错误。第一次决策时列表为空，表示 Agent 还没有执行过任何工具。

随后，`run_agent` 把任务描述和观察历史交给模型接口：

```python
action = model.decide(task, observations)
```

`workspace` 不会直接发送给 DeepSeek。它由 Agent 保留，并在执行动作时传给权限模块和工具模块。

### 3. 适配器构造 DeepSeek 提示文本

这里的 `model` 实际指向 `src/knowflow_agent/deepseek_adapter.py/DeepSeekAdapter` 对象。它的 `decide` 方法先使用 `json.dumps` 把 Python `observations` 列表转换成 JSON 文本：

```python
observation_text = json.dumps(observations, ensure_ascii=False)
```

然后，适配器把工具白名单、决策规则和输出格式组成 `system_prompt`，把任务与观察历史组成 `user_prompt`。准备完成后，它调用创建适配器时保存的请求函数：

```python
response_text = self.request(system_prompt, user_prompt)
```

`examples/run_deepseek_agent.py/request_deepseek` 不负责理解任务，也不负责决定使用哪个工具。它只把适配器准备好的两段提示文本交给 OpenAI SDK，再由 SDK 发送给 DeepSeek：

```python
client.chat.completions.create(...)
```

### 4. 适配器把响应转换成动作字典

DeepSeek 根据任务、观察历史和行为规则返回一个动作。API 响应中的动作最初是 JSON 文本，例如：

```json
{"tool": "read_file", "path": "calculator.py"}
```

`examples/run_deepseek_agent.py/request_deepseek` 从 API 响应对象中取出文本，`DeepSeekAdapter` 再使用 `json.loads` 把文本转换成 Python 字典：

```python
action = {"tool": "read_file", "path": "calculator.py"}
```

因此，`run_agent` 收到的是 Python 动作字典，不是原始 JSON 字符串。

### 5. Agent 检查并执行动作

`src/knowflow_agent/agent.py/run_agent` 把普通工具动作交给同一文件中的 `execute_action`。`execute_action` 只允许执行白名单工具，并在访问文件前调用权限模块：

| 动作 | 检查与执行流程 |
| --- | --- |
| `list_files` | 使用固定的 `workspace` 调用 `src/knowflow_agent/tools.py/list_files`。 |
| `read_file` | 先调用 `src/knowflow_agent/permissions.py/resolve_workspace_path`，确认路径仍在工作区内，再调用 `tools.read_file`。 |
| `write_file` | 先调用 `src/knowflow_agent/permissions.py/resolve_writable_python_path`，确认路径在工作区内且文件是 `.py`，再调用 `tools.write_file`。 |
| `run_tests` | 调用 `src/knowflow_agent/tools.py/run_tests` 执行固定的 `pytest -q`，模型不能提供任意 Shell 命令。 |
| 其他名称 | 抛出 `PermissionError`，不进入工具层。 |

模型只负责提出动作。真正读取文件、修改文件和运行测试的是本地工具函数。

### 6. Agent 保存并输出观察记录

工具执行成功后，`run_agent` 把结果包装成结构统一的观察记录：

```python
observation = {
    "ok": True,
    "tool": action["tool"],
    "result": result,
}
```

如果 `execute_action` 抛出 `PermissionError`，`run_agent` 会把权限错误转换成失败观察：

```python
observation = {
    "ok": False,
    "tool": action["tool"],
    "error": str(error),
}
```

观察记录随后被加入 `observations`。当前 `show_steps` 默认开启，所以 `run_agent` 还会把每轮动作和观察结果输出到终端：

```text
动作：{'tool': 'list_files'}
观察：{'ok': True, 'tool': 'list_files', 'result': [...]}
```

若某个调用场景不需要终端记录，可以明确传入 `show_steps=False`。

### 7. 模型根据真实结果继续决策

进入下一轮循环后，`run_agent` 再次调用：

```python
action = model.decide(task, observations)
```

这一次，DeepSeek 不仅能看到任务描述，还能看到前面工具执行成功或被权限模块拒绝的真实结果。模型根据新的观察记录继续选择动作，Agent 再次完成检查、执行和记录。

本项目中的真实修复过程通常是：

```text
list_files
    ↓
read_file：读取 calculator.py
    ↓
read_file：读取 test_calculator.py
    ↓
write_file：把乘法修改为除法
    ↓
run_tests：获得退出码 0 和 1 passed
    ↓
finish：返回任务总结
```

循环有三种结束方式：

1. 模型返回 `finish`，`run_agent` 返回总结文本；
2. 循环达到 `max_steps`，`run_agent` 抛出 `RuntimeError`；
3. 出现当前没有捕获的异常，程序直接中断并显示错误。

## 完整数据流

```text
examples/run_deepseek_agent.py
    准备 workspace、task 和 adapter
        ↓
src/knowflow_agent/agent.py/run_agent
    创建 observations
        ↓
src/knowflow_agent/deepseek_adapter.py/DeepSeekAdapter.decide
    把 task 和 observations 转换成提示文本
        ↓
examples/run_deepseek_agent.py/request_deepseek
    把提示文本发送给 DeepSeek
        ↓
DeepSeek 返回动作 JSON 文本
        ↓
DeepSeekAdapter 使用 json.loads 转换成 Python 动作字典
        ↓
src/knowflow_agent/agent.py/execute_action
    根据工具名称分派动作
        ↓
src/knowflow_agent/permissions.py
    对文件路径和写入类型进行权限检查
        ↓
src/knowflow_agent/tools.py
    执行真实工具并返回结果
        ↓
run_agent 把结果或权限错误保存到 observations，并输出运行记录
        ↓
带着更新后的 observations 再次请求模型决策
```
