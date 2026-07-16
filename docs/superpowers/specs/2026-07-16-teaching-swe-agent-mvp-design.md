# 教学型 SWE Agent MVP 设计

日期：2026-07-16

## 1. 目标

构建一个能力很窄、逻辑清晰、真实可用的 SWE Agent。用户给出一个明确的 Python 修复任务后，DeepSeek 根据当前任务和历史观察自主选择工具。程序执行工具，把真实结果返回给模型，循环直到测试通过、模型结束或达到最大步数。

本项目同时是教学项目。实现按小里程碑推进，每一步都必须可以运行、观察和解释，不一次性生成完整系统。

## 2. MVP 判定标准

最终 MVP 必须同时满足以下条件：

1. 模型根据真实观察自主选择下一步，而不是执行预先写死的修复步骤。
2. Agent 可以列出文件、读取文件、写入 Python 文件和运行测试。
3. 所有文件操作限制在指定工作区内。
4. 测试只能通过固定的 Python 子进程调用运行，不能执行模型提供的任意 Shell 命令。
5. 自动测试使用可预测的假模型，真实演示使用 DeepSeek。
6. 内置示例项目能够被 Agent 从测试失败修复到测试通过。
7. 终端日志能显示每一轮的模型决策、工具调用和工具结果。

## 3. 非目标

第一阶段不实现：

- 任意 Shell；
- 网络搜索工具；
- 多 Agent 或并发工具调用；
- 插件系统；
- 通用任务规划器；
- Git 自动提交；
- 复杂配置文件；
- 面向不可信仓库的生产级沙箱；
- 多语言代码修复。

## 4. 用户可见流程

用户最终通过命令行提供工作区和任务，例如：

```powershell
python -m knowflow_agent --workspace examples/buggy_calculator --task "修复除法函数并确保测试通过"
```

终端按轮次输出：

```text
Step 1: model -> list_files
Observation: calculator.py, test_calculator.py

Step 2: model -> read_file(test_calculator.py)
Observation: ...

Step 3: model -> write_file(calculator.py)
Observation: file written

Step 4: model -> run_tests
Observation: 1 passed

Result: success
```

## 5. 极简结构

最终包只有三个核心模块：

### `tools.py`

Agent 的“手”。它包含四个工具和必要的路径安全检查：

- `list_files()`；
- `read_file(path)`；
- `write_file(path, content)`；
- `run_tests()`。

该模块集中管理所有文件和进程副作用。权限检查不单独拆成模块，避免 MVP 过度分层。

### `model.py`

Agent 的“大脑接口”。它提供两个实现：

- `FakeModel`：测试使用，按预设顺序返回动作；
- `DeepSeekModel`：真实运行使用，通过 DeepSeek 的 Tool Calls 接口选择工具。

Agent 只依赖对象具有统一的 `decide(messages, tools)` 行为，不引入复杂抽象框架。

### `agent.py`

Agent 的“循环”。它负责：

- 保存任务和消息历史；
- 请求模型选择下一步；
- 把工具调用交给 `tools.py`；
- 把工具结果加入历史；
- 判断成功、失败和最大步数。

数据结构和命令行参数解析也暂时放在这个模块内；只有当代码确实变得难读时才继续拆分。

包还需要很小的 `__init__.py` 和 `__main__.py`，它们只是 Python 包入口，不承担业务逻辑。

## 6. Agent 数据流

每轮只处理一个工具调用：

```text
任务和历史消息
    -> DeepSeekModel.decide
    -> 一个工具调用，或最终回答
    -> tools.py 执行
    -> 工具观察结果
    -> 追加到历史消息
    -> 下一轮
```

模型可以提出动作，但不能直接操作文件或进程。只有 `tools.py` 能产生这些副作用。

## 7. 工具行为

### `list_files`

递归列出工作区内的 `.py` 文件，返回相对路径并保持稳定排序。MVP 不扫描虚拟环境、缓存和隐藏目录。

### `read_file`

输入相对路径，返回 UTF-8 文本。路径解析后必须仍位于工作区内，并且目标必须是普通 `.py` 文件。

### `write_file`

输入相对路径和完整的新文件内容。路径检查规则与 `read_file` 相同，因此 MVP 只能覆盖工作区内已经存在的普通 `.py` 文件。MVP 不创建新代码文件，也不实现补丁格式。

### `run_tests`

在工作区中执行：

```python
[sys.executable, "-m", "pytest", "-q"]
```

使用 `subprocess.run`、参数列表和 `shell=False`，设置 30 秒超时，返回退出码、标准输出和标准错误。

## 8. 安全边界

文件路径先与工作区根目录组合并调用 `resolve()`，然后确认解析后的路径仍位于根目录内。这同时阻止 `../` 越界和指向工作区外的符号链接。

模型没有通用命令执行接口。`run_tests` 不接受命令参数，因此模型无法把它变成任意 Shell。

预期内的操作错误会转成文本观察交还模型，包括路径拒绝、文件不存在、非 `.py` 文件、测试失败和测试超时。模型可以据此选择其他合法动作。未预期的 Python 内部异常会终止当前运行并报告失败。达到八轮仍未完成时，Agent 返回失败，避免无限循环。

该边界只保护宿主文件路径和命令入口，不是生产级代码沙箱。`pytest` 会执行项目测试代码，因此 MVP 只运行仓库内自带的可信示例项目，不用于未知或不可信代码。

## 9. DeepSeek 接入

`DeepSeekModel` 使用 OpenAI Python SDK，读取环境变量 `DEEPSEEK_API_KEY`，将 `base_url` 设为 `https://api.deepseek.com`，默认模型使用 `deepseek-v4-flash`。模型名可通过 `DEEPSEEK_MODEL` 覆盖，避免以后模型名称变化时修改 Agent 核心代码。

使用非流式 Chat Completions 和官方 Tool Calls 格式。系统提示要求每轮最多选择一个工具。若响应包含多个工具调用或无法解析的参数，当前运行以清楚的协议错误结束，不在 MVP 中实现自动修复协议。

选择依据：截至 2026-07-16，DeepSeek 官方文档展示了 OpenAI SDK、`https://api.deepseek.com` 基础地址和 Tool Calls 用法；官方模型页列出 `deepseek-v4-flash` 和 `deepseek-v4-pro`。参考：

- https://api-docs.deepseek.com/guides/tool_calls
- https://api-docs.deepseek.com/quick_start/pricing/
- https://api-docs.deepseek.com/guides/multi_round_chat

## 10. 完成和失败

Agent 只有在观察到 `run_tests` 返回退出码 `0` 后才报告 `success`。

以下情况报告 `failed` 并提供原因：

- 达到最大八轮；
- DeepSeek 请求失败；
- 模型响应违反单工具调用协议；
- 模型在测试通过前主动结束；
- 工具遇到不能恢复的内部错误。

路径拒绝、文件不存在和测试失败属于可观察的工具结果，不会立即终止循环。

## 11. 测试策略

### 工具测试

使用 pytest 的临时目录验证：

- 文件列表稳定；
- 正常读写成功；
- `../` 越界被拒绝；
- 非 `.py` 文件被拒绝；
- 测试退出码和输出被正确捕获；
- 测试超时被转换为清楚结果。

### Agent 循环测试

使用 `FakeModel` 预设动作序列，验证：

- 每次观察都进入下一轮历史；
- 工具按模型选择执行；
- 测试通过后成功；
- 模型提前结束时失败；
- 最大步数生效。

### 真实模型验证

DeepSeek 测试不放进默认自动测试，避免网络、费用和随机性。最终里程碑通过人工运行内置示例完成端到端验证，并保存终端输出。

## 12. 教学里程碑

### 里程碑 1：失败测试

创建只有一个错误函数的示例项目，运行 pytest，理解测试为什么失败。

### 里程碑 2：工具

逐个实现并直接调用四个工具，理解输入、输出和副作用。

### 里程碑 3：安全边界

用正常路径和越界路径做对比测试，理解权限检查。

### 里程碑 4：Agent 循环

使用 `FakeModel` 跑通“决策 -> 执行 -> 观察”循环，理解 Agent 与模型的区别。

### 里程碑 5：DeepSeek

替换为真实模型适配器，理解消息历史和 Tool Calls。

### 里程碑 6：端到端修复

让 DeepSeek 驱动 Agent 修复示例项目，并观察测试从失败变为通过。

每个里程碑都单独运行验证、解释当前新增代码，并在进入下一步前做一个小理解检查。每个确认完成的里程碑形成一个独立 Git 提交。

## 13. 最终目录形态

```text
knowflowagent/
|-- pyproject.toml
|-- README.md
|-- src/
|   `-- knowflow_agent/
|       |-- __init__.py
|       |-- __main__.py
|       |-- agent.py
|       |-- model.py
|       `-- tools.py
|-- examples/
|   `-- buggy_calculator/
|       |-- calculator.py
|       `-- test_calculator.py
|-- tests/
|   |-- test_agent.py
|   |-- test_cli.py
|   |-- test_model.py
|   `-- test_tools.py
`-- docs/
    `-- superpowers/
        `-- specs/
            `-- 2026-07-16-teaching-swe-agent-mvp-design.md
```
