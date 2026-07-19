# KnowFlow Agent

KnowFlow Agent 是一个 MVP 版 SWE Agent，后续会在这个最小版本上继续完善。它让模型根据任务选择工具，由 Agent 控制工具执行，并根据真实执行结果继续决策，直到完成任务或达到最大步数。

项目核心目前支持 `list_files`、`read_file`、`write_file` 和 `run_tests` 四个工具。真实 DeepSeek 演示暂时只向模型开放 `list_files` 和 `finish`，用于先验证最小反馈循环能够运行。

## Agent 怎样完成一次任务

模型负责决策，Agent 负责控制，权限模块负责检查，工具负责真实执行。

### 1. 启动真实演示

`examples/run_deepseek_agent.py` 是真实 DeepSeek 演示脚本。它先准备三个数据：

- `workspace`：Agent 可以操作的工作区路径；
- `task`：本次需要完成的任务描述；
- `adapter`：用于连接 DeepSeek 的模型适配器。

然后调用 `src/knowflow_agent/agent.py` 中的 `run_agent`：

```python
summary = run_agent(
    workspace=workspace,
    task=task,
    model=adapter,
    max_steps=3,
)
```

`adapter` 进入 `run_agent` 后由参数 `model` 接收。这样，Agent 核心只依赖统一的 `Model` 接口，不需要知道当前使用的是 DeepSeek 适配器还是假模型。

### 2. 创建观察历史并请求第一次决策

`src/knowflow_agent/agent.py` 中的 `run_agent` 先创建一个空列表：

```python
observations = []
```

`observations` 用于保存前面步骤产生的工具结果或权限错误。第一次决策时列表为空，表示 Agent 还没有执行过任何工具。

随后，`run_agent` 把任务描述和观察历史交给模型接口：

```python
action = model.decide(task, observations)
```

`workspace` 不会直接发送给 DeepSeek。它由 Agent 保留，并在执行动作时传给权限模块和工具模块。

### 3. 模型适配器发送 DeepSeek 请求

这里的 `model` 实际指向 `src/knowflow_agent/deepseek_adapter.py` 中的 `DeepSeekAdapter` 对象。它的 `decide` 方法会调用创建适配器时保存的 `request_deepseek` 函数：

```python
response_text = self.request(task, observations)
```

`request_deepseek` 位于 `examples/run_deepseek_agent.py`。它先使用 `json.dumps` 把 Python `observations` 列表转换成 JSON 文本，再把任务、观察历史、可用动作和输出规则组成消息，通过下面的代码发送给 DeepSeek：

```python
client.chat.completions.create(...)
```

### 4. 将响应文本转换成动作字典

DeepSeek 根据任务、观察历史和行为规则返回下一步动作。API 响应中的动作最初是 JSON 文本，例如：

```json
{"tool": "list_files"}
```

`request_deepseek` 从 API 响应对象中取出这段文本：

```python
response_text = response.choices[0].message.content
```

`DeepSeekAdapter` 再使用 `json.loads` 将 JSON 文本转换成 Python 字典，并把字典返回给 `run_agent`：

```python
action = {"tool": "list_files"}
```

因此，`run_agent` 收到的是 Python 动作字典，不是原始 JSON 字符串。

### 5. 检查并执行动作

`run_agent` 首先读取 `action["tool"]`：

- 如果工具名称是 `finish`，立即返回 `action["summary"]`，任务正常结束；
- 如果是普通工具，则调用同一文件中的 `execute_action(workspace, action)`。

`execute_action` 只允许调用白名单中的工具，并根据动作类型决定是否需要权限检查：

| 动作 | 检查与执行流程 |
| --- | --- |
| `list_files` | 使用固定的 `workspace` 调用 `src/knowflow_agent/tools.py` 中的 `list_files`。 |
| `read_file` | 先调用 `permissions.resolve_workspace_path`，确认路径仍在工作区内，再调用 `tools.read_file`。 |
| `write_file` | 先调用 `permissions.resolve_writable_python_path`，确认路径在工作区内且文件是 `.py`，再调用 `tools.write_file`。 |
| `run_tests` | 调用 `tools.run_tests` 执行固定的 `pytest -q`，模型不能提供任意 Shell 命令。 |
| 其他名称 | 抛出 `PermissionError`，不进入工具层。 |

大模型只负责提出动作。真正读取文件、修改文件和运行测试的是本地 `tools.py` 中的工具函数。

### 6. 将执行结果保存为观察记录

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

观察记录随后被加入 `observations`：

```python
observations.append(observation)
```

当前代码只捕获 `PermissionError`。API 请求失败、JSON 解析失败或文件不存在等其他异常不会被转换成观察记录，而是会直接中断程序。

### 7. 带着真实结果继续决策

进入下一轮循环后，`run_agent` 再次调用：

```python
action = model.decide(task, observations)
```

这一次，DeepSeek 不仅能看到任务描述，还能看到前面工具执行成功或被权限模块拒绝的真实结果。模型根据新的观察记录继续选择动作，Agent 再次完成检查、执行和记录。

循环有三种结束方式：

1. 模型返回 `finish`，`run_agent` 返回总结文本；
2. 循环达到 `max_steps`，`run_agent` 抛出 `RuntimeError`；
3. 出现当前没有捕获的异常，程序直接中断并显示错误。

## 完整数据流

```text
examples/run_deepseek_agent.py
    准备 workspace、task 和 adapter
        ↓
src/knowflow_agent/agent.py / run_agent
    创建 observations
        ↓
src/knowflow_agent/deepseek_adapter.py / DeepSeekAdapter.decide
        ↓
examples/run_deepseek_agent.py / request_deepseek
    把 task 和 observations 发送给 DeepSeek
        ↓
DeepSeek 返回动作 JSON 文本
        ↓
DeepSeekAdapter 使用 json.loads 转换成 Python 动作字典
        ↓
run_agent 判断 finish 或调用 execute_action
        ↓
src/knowflow_agent/permissions.py
    对需要访问文件的动作进行权限检查
        ↓
src/knowflow_agent/tools.py
    执行真实工具并返回结果
        ↓
run_agent 把结果或权限错误保存到 observations
        ↓
带着更新后的 observations 再次请求模型决策
```
