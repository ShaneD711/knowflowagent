# Chinese Comment Convention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前代码和配置中的说明注释统一改为中文，并保存这条长期协作规则。

**Architecture:** 这次调整只修改注释、Python 文档字符串和本地协作说明，不增加模块、测试或运行时分支。修改后用旧英文短语搜索和现有红测试证明注释已替换且程序行为没有改变。

**Tech Stack:** Python 3.14、pytest、Git、PowerShell

## Global Constraints

- Python 的 `#` 注释、模块和函数文档字符串统一使用中文，`.gitignore` 中的说明注释也使用中文。
- 函数名、变量名和类型注解继续使用英文，因为它们属于代码标识符，不是注释。
- 注释解释原因，不重复代码已经表达的动作。
- 第一阶段不增加英文注释自动检测脚本。
- 故意错误 `return a * b` 必须保留，现有测试仍应以 `assert 12 == 3` 失败。

---

### Task 1: 统一当前注释并保存规则

**Files:**
- Modify: `.gitignore`
- Modify: `src/knowflow_agent/__init__.py`
- Modify: `examples/buggy_calculator/calculator.py`
- Modify locally, ignored by Git: `C:/Dev/knowflowagent/AGENTS.md`
- Test: `examples/buggy_calculator/test_calculator.py`

**Interfaces:**
- Consumes: 现有 `divide(a: float, b: float) -> float`，不修改其签名或实现。
- Produces: 中文注释约定；不产生新的运行时接口。

- [ ] **Step 1: 翻译当前受 Git 管理的注释和文档字符串**

将 `.gitignore` 改为：

```gitignore
# 密钥和本地配置
.env
AGENTS.md

# 虚拟环境
.venv/
venv/

# 本地 Git 工作区
.worktrees/

# Python 缓存和测试产物
__pycache__/
*.py[cod]
.pytest_cache/
.coverage
htmlcov/

# 构建产物
build/
dist/
*.egg-info/

# 一次性教学示例
work/
```

将 `src/knowflow_agent/__init__.py` 改为：

```python
"""教学型最小 SWE Agent。"""
```

将 `examples/buggy_calculator/calculator.py` 改为：

```python
def divide(a: float, b: float) -> float:
    """返回 a 除以 b 的结果。"""
    return a * b
```

- [ ] **Step 2: 把长期规则加入本地协作说明**

在 `C:/Dev/knowflowagent/AGENTS.md` 的“代码清晰度原则”中加入：

```markdown
- Python 的 `#` 注释、模块和函数文档字符串必须使用中文，`.gitignore` 中的说明注释也使用中文；函数名、变量名和类型注解继续使用英文。
```

- [ ] **Step 3: 验证旧英文注释已经消失**

Run:

```powershell
rg -n "Secrets and local configuration|Virtual environments|Local Git worktrees|Python caches and test artifacts|Build artifacts|Disposable teaching demos|Teaching-oriented minimal SWE agent|Return a divided by b" .gitignore src/knowflow_agent/__init__.py examples/buggy_calculator/calculator.py
```

Expected: 命令退出码为 `1` 且没有输出，表示这些旧短语都不存在。

- [ ] **Step 4: 验证程序行为没有改变**

Run:

```powershell
py -m pytest examples/buggy_calculator -q
```

Expected: 命令退出码为 `1`，只有一个预期失败，核心证据仍为 `assert 12 == 3`。

- [ ] **Step 5: 检查改动范围和文本格式**

Run:

```powershell
git diff --check
git diff -- .gitignore src/knowflow_agent/__init__.py examples/buggy_calculator/calculator.py
```

Expected: `git diff --check` 退出码为 `0`；差异中只包含注释和文档字符串的中文化。

- [ ] **Step 6: 提交受 Git 管理的修改**

```powershell
git add -- .gitignore src/knowflow_agent/__init__.py examples/buggy_calculator/calculator.py
git commit -m "translate project comments to Chinese"
```

Expected: 提交包含三个受 Git 管理的文件；本地 `AGENTS.md` 继续被忽略，不进入提交。
