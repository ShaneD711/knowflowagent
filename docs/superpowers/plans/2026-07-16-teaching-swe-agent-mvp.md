# Teaching SWE Agent MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a narrow but real teaching-oriented SWE Agent that lets DeepSeek inspect and repair a trusted Python example project through four safe tools and verifies success with pytest.

**Architecture:** Keep three core modules: `tools.py` owns every filesystem and subprocess side effect, `model.py` converts model responses into one tool call per round, and `agent.py` owns the observation-decision-action loop plus the CLI. Build vertically: first create an intentionally failing example, then tools and safety, then a deterministic fake-model loop, and only then add DeepSeek and the live CLI.

**Tech Stack:** Python 3.11+ (development machine: Python 3.14.6), pytest 8+, OpenAI Python SDK used with DeepSeek's OpenAI-compatible Chat Completions API, setuptools, Windows PowerShell commands.

## Global Constraints

- Keep only three core business modules: `src/knowflow_agent/tools.py`, `model.py`, and `agent.py`.
- Use only `list_files`, `read_file`, `write_file`, and fixed `run_tests` tools.
- Never expose arbitrary shell execution or model-selected commands.
- Only read and overwrite existing `.py` files inside the configured trusted workspace.
- Run tests as `[sys.executable, "-m", "pytest", "-q"]` with `shell=False` and a 30-second default timeout.
- Process exactly one model tool call per round and stop after at most eight rounds.
- Report success only after `run_tests` returns exit code `0`.
- Default automatic tests to `FakeModel`; never require network or API spending in `py -m pytest -q`.
- Use `DEEPSEEK_API_KEY` for the secret, `DEEPSEEK_MODEL` for an optional model override, and never commit an API key.
- Implement one teaching milestone at a time; run the named verification, explain the result, perform a small comprehension check, and commit before continuing.
- Do not weaken, delete, or skip tests to make a check pass.

---

## File Map

- `pyproject.toml`: package metadata, dependencies, pytest defaults, and final console entry point.
- `.gitignore`: secrets, caches, build artifacts, and disposable demo workspaces.
- `src/knowflow_agent/__init__.py`: package marker only.
- `src/knowflow_agent/__main__.py`: delegates `python -m knowflow_agent` to `agent.main`.
- `src/knowflow_agent/tools.py`: `ToolResult`, four safe tools, tool schemas, and dispatch.
- `src/knowflow_agent/model.py`: model-neutral reply types, `FakeModel`, and `DeepSeekModel`.
- `src/knowflow_agent/agent.py`: agent loop, result type, terminal logging, and CLI.
- `examples/buggy_calculator/calculator.py`: intentionally broken trusted demo code.
- `examples/buggy_calculator/test_calculator.py`: red test defining correct behavior.
- `tests/test_tools.py`: happy-path tools, safety boundaries, subprocess, and timeout tests.
- `tests/test_model.py`: DeepSeek parsing and request tests without network.
- `tests/test_agent.py`: deterministic feedback-loop tests.
- `tests/test_cli.py`: command-line wiring and exit-code tests.
- `README.md`: learner-facing setup, architecture, and demo instructions.

---

### Task 1: Create the Red Example and Project Skeleton

**Teaching outcome:** See a real failing test before any Agent code exists.

**Files:**
- Modify: `.gitignore`
- Create: `pyproject.toml`
- Create: `src/knowflow_agent/__init__.py`
- Create: `examples/buggy_calculator/calculator.py`
- Create: `examples/buggy_calculator/test_calculator.py`

**Interfaces:**
- Consumes: Python 3.14.6 through `py`.
- Produces: installable package skeleton and `divide(a: float, b: float) -> float` demo contract.

- [ ] **Step 1: Ignore disposable demo workspaces**

Add to `.gitignore`:

```gitignore
# Disposable teaching demos
work/
```

- [ ] **Step 2: Add package and test configuration**

Create `pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=75"]
build-backend = "setuptools.build_meta"

[project]
name = "knowflow-agent"
version = "0.1.0"
description = "A teaching-oriented minimal SWE agent"
requires-python = ">=3.11"
dependencies = [
    "openai>=1.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

- [ ] **Step 3: Create the package marker**

Create `src/knowflow_agent/__init__.py`:

```python
"""Teaching-oriented minimal SWE agent."""
```

- [ ] **Step 4: Create the intentionally broken function**

Create `examples/buggy_calculator/calculator.py`:

```python
def divide(a: float, b: float) -> float:
    """Return a divided by b."""
    return a * b
```

- [ ] **Step 5: Create the test defining correct division**

Create `examples/buggy_calculator/test_calculator.py`:

```python
from calculator import divide


def test_divide_six_by_two() -> None:
    assert divide(6, 2) == 3
```

- [ ] **Step 6: Install project dependencies**

Run:

```powershell
py -m pip install -e ".[dev]"
```

Expected: exit code `0` and an editable `knowflow-agent` installation.

- [ ] **Step 7: Verify the intentional red state**

Run:

```powershell
py -m pytest examples/buggy_calculator -q
```

Expected: exit code `1`, one failed test, and an assertion showing `12 != 3`.

- [ ] **Step 8: Explain the feedback**

Explain that `calculator.py` is current behavior, the test is expected behavior, and the assertion is evidence. Ask which expression produced `12`.

- [ ] **Step 9: Commit milestone 1**

```powershell
git add -- .gitignore pyproject.toml src/knowflow_agent/__init__.py examples/buggy_calculator/calculator.py examples/buggy_calculator/test_calculator.py
git commit -m "add intentionally failing calculator example"
```

---

### Task 2: Implement List, Read, and Write Happy Paths

**Teaching outcome:** See inputs, outputs, and filesystem side effects before adding a model.

**Files:**
- Create: `src/knowflow_agent/tools.py`
- Create: `tests/test_tools.py`

**Interfaces:**
- Consumes: trusted workspace path.
- Produces: `ToolResult(ok, output, exit_code)` and `WorkspaceTools` happy-path methods.

- [ ] **Step 1: Write happy-path tests**

Create `tests/test_tools.py`:

```python
from pathlib import Path

from knowflow_agent.tools import WorkspaceTools


def test_list_files_returns_sorted_relative_python_paths(tmp_path: Path) -> None:
    (tmp_path / "z.py").write_text("z = 1\n", encoding="utf-8")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "a.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignore me\n", encoding="utf-8")

    result = WorkspaceTools(tmp_path).list_files()

    assert result.ok is True
    assert result.output.splitlines() == ["nested/a.py", "z.py"]


def test_read_file_returns_utf8_text(tmp_path: Path) -> None:
    (tmp_path / "hello.py").write_text("message = '你好'\n", encoding="utf-8")

    result = WorkspaceTools(tmp_path).read_file("hello.py")

    assert result.ok is True
    assert result.output == "message = '你好'\n"


def test_write_file_overwrites_existing_python_file(tmp_path: Path) -> None:
    target = tmp_path / "calculator.py"
    target.write_text("answer = 0\n", encoding="utf-8")

    result = WorkspaceTools(tmp_path).write_file("calculator.py", "answer = 42\n")

    assert result.ok is True
    assert result.output == "wrote calculator.py"
    assert target.read_text(encoding="utf-8") == "answer = 42\n"
```

- [ ] **Step 2: Verify the red test**

Run:

```powershell
py -m pytest tests/test_tools.py -q
```

Expected: collection error containing `ModuleNotFoundError: No module named 'knowflow_agent.tools'`.

- [ ] **Step 3: Implement minimal happy-path tools**

Create `src/knowflow_agent/tools.py`:

```python
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: str
    exit_code: int | None = None


class WorkspaceTools:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()

    def list_files(self) -> ToolResult:
        paths = sorted(
            path.relative_to(self.root).as_posix()
            for path in self.root.rglob("*.py")
            if path.is_file()
        )
        return ToolResult(ok=True, output="\n".join(paths))

    def read_file(self, path: str) -> ToolResult:
        content = (self.root / path).read_text(encoding="utf-8")
        return ToolResult(ok=True, output=content)

    def write_file(self, path: str, content: str) -> ToolResult:
        (self.root / path).write_text(content, encoding="utf-8")
        return ToolResult(ok=True, output=f"wrote {Path(path).as_posix()}")
```

- [ ] **Step 4: Verify the green test**

Run:

```powershell
py -m pytest tests/test_tools.py -q
```

Expected: `3 passed` and exit code `0`.

- [ ] **Step 5: Explain the feedback**

Explain that `read_file` observes, `write_file` mutates, and `ToolResult` gives callers one return shape. Ask which line changes a file.

- [ ] **Step 6: Commit milestone 2**

```powershell
git add -- src/knowflow_agent/tools.py tests/test_tools.py
git commit -m "add basic workspace tools"
```

---

### Task 3: Add Safety Boundaries and Fixed Test Execution

**Teaching outcome:** Watch unsafe behavior fail tests, then close it with path resolution and a fixed subprocess argument list.

**Files:**
- Modify: `tests/test_tools.py`
- Modify: `src/knowflow_agent/tools.py`

**Interfaces:**
- Consumes: Task 2 `ToolResult` and `WorkspaceTools`.
- Produces: guarded methods and `run_tests() -> ToolResult`.

- [ ] **Step 1: Append boundary and subprocess tests**

Append to `tests/test_tools.py`:

```python
def test_read_file_rejects_parent_traversal(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (tmp_path / "outside.py").write_text("secret = True\n", encoding="utf-8")

    result = WorkspaceTools(workspace).read_file("../outside.py")

    assert result.ok is False
    assert "outside workspace" in result.output


def test_read_file_rejects_non_python_file(tmp_path: Path) -> None:
    (tmp_path / "notes.txt").write_text("private\n", encoding="utf-8")

    result = WorkspaceTools(tmp_path).read_file("notes.txt")

    assert result.ok is False
    assert "only .py files" in result.output


def test_write_file_rejects_missing_target(tmp_path: Path) -> None:
    result = WorkspaceTools(tmp_path).write_file("new.py", "created = True\n")

    assert result.ok is False
    assert "existing regular file" in result.output
    assert not (tmp_path / "new.py").exists()


def test_list_files_skips_hidden_and_cache_directories(tmp_path: Path) -> None:
    (tmp_path / "visible.py").write_text("visible = True\n", encoding="utf-8")
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "secret.py").write_text("secret = True\n", encoding="utf-8")
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "cached.py").write_text("cached = True\n", encoding="utf-8")

    result = WorkspaceTools(tmp_path).list_files()

    assert result.output.splitlines() == ["visible.py"]


def test_run_tests_reports_passing_exit_code(tmp_path: Path) -> None:
    (tmp_path / "test_ok.py").write_text(
        "def test_ok():\n    assert 2 + 2 == 4\n",
        encoding="utf-8",
    )

    result = WorkspaceTools(tmp_path).run_tests()

    assert result.ok is True
    assert result.exit_code == 0
    assert "1 passed" in result.output


def test_run_tests_reports_failure_output(tmp_path: Path) -> None:
    (tmp_path / "test_fail.py").write_text(
        "def test_fail():\n    assert 2 + 2 == 5\n",
        encoding="utf-8",
    )

    result = WorkspaceTools(tmp_path).run_tests()

    assert result.ok is False
    assert result.exit_code == 1
    assert "1 failed" in result.output


def test_run_tests_reports_timeout(tmp_path: Path) -> None:
    (tmp_path / "test_slow.py").write_text(
        "import time\n\ndef test_slow():\n    time.sleep(1)\n",
        encoding="utf-8",
    )

    result = WorkspaceTools(tmp_path, test_timeout=0.01).run_tests()

    assert result.ok is False
    assert result.exit_code is None
    assert result.output == "pytest timed out after 0.01 seconds"
```

- [ ] **Step 2: Observe unsafe red results**

Run:

```powershell
py -m pytest tests/test_tools.py -q
```

Expected: failures or errors demonstrating traversal, non-Python reads, missing-file creation, hidden listing, and absent `run_tests`.

- [ ] **Step 3: Replace tools with guarded implementation**

Replace `src/knowflow_agent/tools.py`:

```python
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


SKIPPED_DIRECTORIES = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}


@dataclass(frozen=True)
class ToolResult:
    ok: bool
    output: str
    exit_code: int | None = None


class ToolAccessError(ValueError):
    """An expected request that violates the MVP workspace policy."""


class WorkspaceTools:
    def __init__(self, root: str | Path, test_timeout: float = 30.0) -> None:
        self.root = Path(root).resolve()
        if not self.root.is_dir():
            raise ValueError(f"workspace is not a directory: {self.root}")
        self.test_timeout = test_timeout

    def _resolve_python_file(self, relative_path: str) -> Path:
        requested = Path(relative_path)
        if requested.is_absolute():
            raise ToolAccessError("path is outside workspace")

        candidate = (self.root / requested).resolve()
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ToolAccessError("path is outside workspace") from exc

        if candidate.suffix.lower() != ".py":
            raise ToolAccessError("only .py files are allowed")
        if not candidate.is_file():
            raise ToolAccessError("target must be an existing regular file")
        return candidate

    def list_files(self) -> ToolResult:
        paths: list[str] = []
        for path in self.root.rglob("*.py"):
            relative = path.relative_to(self.root)
            directory_parts = relative.parts[:-1]
            if any(
                part.startswith(".") or part in SKIPPED_DIRECTORIES
                for part in directory_parts
            ):
                continue
            try:
                resolved = path.resolve(strict=True)
                resolved.relative_to(self.root)
            except (FileNotFoundError, ValueError):
                continue
            if resolved.is_file():
                paths.append(relative.as_posix())
        return ToolResult(ok=True, output="\n".join(sorted(paths)))

    def read_file(self, path: str) -> ToolResult:
        try:
            target = self._resolve_python_file(path)
            return ToolResult(ok=True, output=target.read_text(encoding="utf-8"))
        except (ToolAccessError, OSError, UnicodeError) as exc:
            return ToolResult(ok=False, output=f"error: {exc}")

    def write_file(self, path: str, content: str) -> ToolResult:
        try:
            target = self._resolve_python_file(path)
            target.write_text(content, encoding="utf-8")
            relative = target.relative_to(self.root).as_posix()
            return ToolResult(ok=True, output=f"wrote {relative}")
        except (ToolAccessError, OSError, UnicodeError) as exc:
            return ToolResult(ok=False, output=f"error: {exc}")

    def run_tests(self) -> ToolResult:
        command = [sys.executable, "-m", "pytest", "-q"]
        try:
            completed = subprocess.run(
                command,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=self.test_timeout,
                shell=False,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return ToolResult(
                ok=False,
                output=f"pytest timed out after {self.test_timeout} seconds",
            )

        output_parts = [completed.stdout.strip(), completed.stderr.strip()]
        output = "\n".join(part for part in output_parts if part) or "(no output)"
        return ToolResult(
            ok=completed.returncode == 0,
            output=output,
            exit_code=completed.returncode,
        )
```

- [ ] **Step 4: Verify safety and subprocess tests**

Run:

```powershell
py -m pytest tests/test_tools.py -q
```

Expected: `10 passed` and exit code `0`.

- [ ] **Step 5: Explain the feedback**

Explain `resolve()`, containment through `relative_to(root)`, and why an argument list with `shell=False` prevents model-selected shell syntax. State that pytest still executes trusted code and is not a production sandbox.

- [ ] **Step 6: Commit milestone 3**

```powershell
git add -- src/knowflow_agent/tools.py tests/test_tools.py
git commit -m "enforce workspace boundaries and fixed tests"
```

---

### Task 4: Build the Deterministic Agent Loop

**Teaching outcome:** See that an Agent is the loop connecting decisions, tools, and observations; the model provider is replaceable.

**Files:**
- Modify: `src/knowflow_agent/tools.py`
- Create: `src/knowflow_agent/model.py`
- Create: `src/knowflow_agent/agent.py`
- Create: `tests/test_agent.py`

**Interfaces:**
- Consumes: `WorkspaceTools` and `ToolResult`.
- Produces: `ToolCall`, `ModelReply`, `FakeModel`, `AgentResult`, `Agent.run(task)`, tool schemas, and dispatch.

- [ ] **Step 1: Write deterministic Agent tests**

Create `tests/test_agent.py`:

```python
from pathlib import Path

from knowflow_agent.agent import Agent
from knowflow_agent.model import FakeModel, ModelReply, ToolCall
from knowflow_agent.tools import WorkspaceTools


def make_broken_workspace(root: Path) -> None:
    (root / "calculator.py").write_text(
        "def divide(a, b):\n    return a * b\n",
        encoding="utf-8",
    )
    (root / "test_calculator.py").write_text(
        "from calculator import divide\n\n"
        "def test_divide():\n    assert divide(6, 2) == 3\n",
        encoding="utf-8",
    )


def test_agent_uses_observations_and_stops_after_passing_tests(tmp_path: Path) -> None:
    make_broken_workspace(tmp_path)
    model = FakeModel(
        [
            ModelReply(tool_calls=(ToolCall("call-1", "list_files", {}),)),
            ModelReply(
                tool_calls=(
                    ToolCall("call-2", "read_file", {"path": "calculator.py"}),
                )
            ),
            ModelReply(
                tool_calls=(
                    ToolCall(
                        "call-3",
                        "write_file",
                        {
                            "path": "calculator.py",
                            "content": "def divide(a, b):\n    return a / b\n",
                        },
                    ),
                )
            ),
            ModelReply(tool_calls=(ToolCall("call-4", "run_tests", {}),)),
        ]
    )
    events: list[str] = []

    result = Agent(model, WorkspaceTools(tmp_path), emit=events.append).run(
        "Fix divide and make the tests pass"
    )

    assert result.success is True
    assert result.steps == 4
    assert "return a / b" in (tmp_path / "calculator.py").read_text(encoding="utf-8")
    assert any(message["role"] == "tool" for message in model.seen_messages[1])
    assert events[0] == "Step 1: model -> list_files"
    assert any("1 passed" in event for event in events if event.startswith("Observation:"))


def test_agent_fails_when_model_finishes_before_tests_pass(tmp_path: Path) -> None:
    model = FakeModel([ModelReply(content="The task is done")])

    result = Agent(model, WorkspaceTools(tmp_path), emit=lambda _: None).run("Fix it")

    assert result.success is False
    assert result.steps == 1
    assert result.summary == "model stopped before tests passed: The task is done"


def test_agent_rejects_multiple_tool_calls_in_one_round(tmp_path: Path) -> None:
    model = FakeModel(
        [
            ModelReply(
                tool_calls=(
                    ToolCall("call-1", "list_files", {}),
                    ToolCall("call-2", "run_tests", {}),
                )
            )
        ]
    )

    result = Agent(model, WorkspaceTools(tmp_path), emit=lambda _: None).run("Fix it")

    assert result.success is False
    assert result.summary == "model protocol error: expected at most one tool call"


def test_agent_stops_at_maximum_steps(tmp_path: Path) -> None:
    replies = [
        ModelReply(tool_calls=(ToolCall(f"call-{number}", "list_files", {}),))
        for number in range(1, 9)
    ]

    result = Agent(
        FakeModel(replies),
        WorkspaceTools(tmp_path),
        max_steps=8,
        emit=lambda _: None,
    ).run("Keep looking")

    assert result.success is False
    assert result.steps == 8
    assert result.summary == "maximum step count reached"
```

- [ ] **Step 2: Verify missing Agent modules**

Run:

```powershell
py -m pytest tests/test_agent.py -q
```

Expected: collection error because `knowflow_agent.agent` and `knowflow_agent.model` do not exist.

- [ ] **Step 3: Add model-neutral types and FakeModel**

Create `src/knowflow_agent/model.py`:

```python
from copy import deepcopy
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelReply:
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()


class FakeModel:
    def __init__(self, replies: list[ModelReply]) -> None:
        self._replies = replies
        self._index = 0
        self.seen_messages: list[list[dict[str, Any]]] = []

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        self.seen_messages.append(deepcopy(messages))
        if self._index >= len(self._replies):
            raise RuntimeError("FakeModel has no reply left")
        reply = self._replies[self._index]
        self._index += 1
        return reply
```

- [ ] **Step 4: Add tool schemas and dispatch**

Add after `SKIPPED_DIRECTORIES` in `tools.py`:

```python
TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List Python files inside the workspace.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read one existing Python file inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Overwrite one existing Python file inside the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": "Run pytest -q in the workspace.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]
```

Add at the end of `WorkspaceTools`:

```python
    def call(self, name: str, arguments: dict[str, object]) -> ToolResult:
        handlers = {
            "list_files": self.list_files,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "run_tests": self.run_tests,
        }
        handler = handlers.get(name)
        if handler is None:
            return ToolResult(ok=False, output=f"error: unknown tool {name}")
        try:
            return handler(**arguments)
        except TypeError as exc:
            return ToolResult(ok=False, output=f"error: invalid arguments for {name}: {exc}")
```

- [ ] **Step 5: Implement the Agent loop**

Create `src/knowflow_agent/agent.py`:

```python
import json
from dataclasses import dataclass
from typing import Any, Callable

from knowflow_agent.model import ModelReply
from knowflow_agent.tools import TOOL_SCHEMAS, WorkspaceTools


SYSTEM_PROMPT = """You are a minimal SWE agent working in a trusted Python example.
Choose at most one tool per turn. Inspect code and tests before editing.
Only report completion after run_tests passes. Never weaken or delete tests.
"""


@dataclass(frozen=True)
class AgentResult:
    success: bool
    steps: int
    summary: str


class Agent:
    def __init__(
        self,
        model: object,
        tools: WorkspaceTools,
        max_steps: int = 8,
        emit: Callable[[str], None] = print,
    ) -> None:
        self.model = model
        self.tools = tools
        self.max_steps = max_steps
        self.emit = emit

    def run(self, task: str) -> AgentResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": task},
        ]

        for step in range(1, self.max_steps + 1):
            try:
                reply: ModelReply = self.model.decide(messages, TOOL_SCHEMAS)
            except Exception as exc:
                return AgentResult(False, step, f"model error: {exc}")

            if len(reply.tool_calls) > 1:
                return AgentResult(
                    False,
                    step,
                    "model protocol error: expected at most one tool call",
                )
            if not reply.tool_calls:
                content = reply.content or "empty response"
                return AgentResult(
                    False,
                    step,
                    f"model stopped before tests passed: {content}",
                )

            call = reply.tool_calls[0]
            self.emit(f"Step {step}: model -> {call.name}")
            messages.append(
                {
                    "role": "assistant",
                    "content": reply.content or None,
                    "tool_calls": [
                        {
                            "id": call.id,
                            "type": "function",
                            "function": {
                                "name": call.name,
                                "arguments": json.dumps(
                                    call.arguments,
                                    ensure_ascii=False,
                                ),
                            },
                        }
                    ],
                }
            )

            try:
                tool_result = self.tools.call(call.name, call.arguments)
            except Exception as exc:
                return AgentResult(False, step, f"tool internal error: {exc}")

            observation = (
                f"ok={tool_result.ok}; exit_code={tool_result.exit_code}; "
                f"output={tool_result.output}"
            )
            self.emit(f"Observation: {tool_result.output}")
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": observation,
                }
            )

            if call.name == "run_tests" and tool_result.ok:
                return AgentResult(True, step, "tests passed")

        return AgentResult(False, self.max_steps, "maximum step count reached")
```

- [ ] **Step 6: Verify Agent tests**

Run:

```powershell
py -m pytest tests/test_agent.py -q
```

Expected: `4 passed` and exit code `0`.

- [ ] **Step 7: Verify the complete offline suite**

Run:

```powershell
py -m pytest -q
```

Expected: `14 passed`. The intentionally failing example is excluded by pytest `testpaths`.

- [ ] **Step 8: Explain the feedback**

Trace model decision, tool execution, observation message, and next decision. Ask which object chooses and which object changes the file.

- [ ] **Step 9: Commit milestone 4**

```powershell
git add -- src/knowflow_agent/tools.py src/knowflow_agent/model.py src/knowflow_agent/agent.py tests/test_agent.py
git commit -m "add deterministic agent feedback loop"
```

---

### Task 5: Add the DeepSeek Tool-Call Adapter

**Teaching outcome:** Replacing FakeModel with DeepSeek changes only the decision provider.

**Files:**
- Modify: `src/knowflow_agent/model.py`
- Create: `tests/test_model.py`

**Interfaces:**
- Consumes: model-neutral replies, OpenAI-style messages, and tool schemas.
- Produces: `DeepSeekModel.decide(messages, tools) -> ModelReply` and `ModelProtocolError`.

- [ ] **Step 1: Write adapter tests with a fake client**

Create `tests/test_model.py`:

```python
from types import SimpleNamespace

import pytest

from knowflow_agent.model import DeepSeekModel, ModelProtocolError


class FakeCompletions:
    def __init__(self, message: object) -> None:
        self.message = message
        self.requests: list[dict[str, object]] = []

    def create(self, **kwargs: object) -> object:
        self.requests.append(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=self.message)])


class FakeClient:
    def __init__(self, message: object) -> None:
        self.completions = FakeCompletions(message)
        self.chat = SimpleNamespace(completions=self.completions)


def test_deepseek_model_parses_one_tool_call() -> None:
    message = SimpleNamespace(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id="call-1",
                function=SimpleNamespace(
                    name="read_file",
                    arguments='{"path": "calculator.py"}',
                ),
            )
        ],
    )
    client = FakeClient(message)
    model = DeepSeekModel(client=client, model="test-model")
    messages = [{"role": "user", "content": "Fix it"}]
    tools = [{"type": "function", "function": {"name": "read_file"}}]

    reply = model.decide(messages, tools)

    assert reply.tool_calls[0].name == "read_file"
    assert reply.tool_calls[0].arguments == {"path": "calculator.py"}
    assert client.completions.requests == [
        {
            "model": "test-model",
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto",
            "stream": False,
            "extra_body": {"thinking": {"type": "disabled"}},
        }
    ]


def test_deepseek_model_returns_final_content_without_tool_call() -> None:
    client = FakeClient(SimpleNamespace(content="Finished", tool_calls=None))

    reply = DeepSeekModel(client=client).decide([], [])

    assert reply.content == "Finished"
    assert reply.tool_calls == ()


def test_deepseek_model_rejects_invalid_json_arguments() -> None:
    message = SimpleNamespace(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id="call-1",
                function=SimpleNamespace(name="read_file", arguments="not-json"),
            )
        ],
    )

    with pytest.raises(ModelProtocolError, match="invalid JSON arguments"):
        DeepSeekModel(client=FakeClient(message)).decide([], [])


def test_deepseek_model_requires_api_key_without_injected_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY is not set"):
        DeepSeekModel()
```

- [ ] **Step 2: Verify missing adapter classes**

Run:

```powershell
py -m pytest tests/test_model.py -q
```

Expected: collection error because `DeepSeekModel` and `ModelProtocolError` do not exist.

- [ ] **Step 3: Replace model.py with the final adapter**

Replace `src/knowflow_agent/model.py`:

```python
import json
import os
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelReply:
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()


class ModelProtocolError(ValueError):
    """The model response cannot be represented by the MVP protocol."""


class FakeModel:
    def __init__(self, replies: list[ModelReply]) -> None:
        self._replies = replies
        self._index = 0
        self.seen_messages: list[list[dict[str, Any]]] = []

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        self.seen_messages.append(deepcopy(messages))
        if self._index >= len(self._replies):
            raise RuntimeError("FakeModel has no reply left")
        reply = self._replies[self._index]
        self._index += 1
        return reply


class DeepSeekModel:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        client: object | None = None,
    ) -> None:
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
        if client is None:
            resolved_key = api_key or os.getenv("DEEPSEEK_API_KEY")
            if not resolved_key:
                raise ValueError("DEEPSEEK_API_KEY is not set")
            client = OpenAI(
                api_key=resolved_key,
                base_url="https://api.deepseek.com",
            )
        self.client = client

    def decide(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> ModelReply:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            stream=False,
            extra_body={"thinking": {"type": "disabled"}},
        )
        message = response.choices[0].message
        parsed_calls: list[ToolCall] = []
        for call in message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments)
            except json.JSONDecodeError as exc:
                raise ModelProtocolError("invalid JSON arguments") from exc
            if not isinstance(arguments, dict):
                raise ModelProtocolError("tool arguments must be a JSON object")
            parsed_calls.append(
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments=arguments,
                )
            )
        return ModelReply(
            content=message.content or "",
            tool_calls=tuple(parsed_calls),
        )
```

- [ ] **Step 4: Verify adapter tests**

Run:

```powershell
py -m pytest tests/test_model.py -q
```

Expected: `4 passed` without network access.

- [ ] **Step 5: Verify the complete offline suite**

Run:

```powershell
py -m pytest -q
```

Expected: `18 passed`.

- [ ] **Step 6: Explain the feedback**

Compare `FakeModel.decide` with `DeepSeekModel.decide`. Explain injected fake clients and why `DEEPSEEK_API_KEY` is never hard-coded.

- [ ] **Step 7: Commit milestone 5**

```powershell
git add -- src/knowflow_agent/model.py tests/test_model.py
git commit -m "add DeepSeek tool-call adapter"
```

---

### Task 6: Add CLI, Documentation, and Live Demo

**Teaching outcome:** Run one command and connect terminal events to the three core modules.

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/knowflow_agent/agent.py`
- Create: `src/knowflow_agent/__main__.py`
- Create: `tests/test_cli.py`
- Create: `README.md`

**Interfaces:**
- Consumes: `Agent`, `WorkspaceTools`, and `DeepSeekModel`.
- Produces: `main(argv) -> int`, `python -m knowflow_agent`, and `knowflow-agent`.

- [ ] **Step 1: Write CLI tests**

Create `tests/test_cli.py`:

```python
from pathlib import Path

import pytest

import knowflow_agent.agent as agent_module
from knowflow_agent.model import FakeModel, ModelReply, ToolCall


def test_main_runs_agent_and_returns_zero_after_tests_pass(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    (tmp_path / "calculator.py").write_text(
        "def divide(a, b):\n    return a * b\n",
        encoding="utf-8",
    )
    (tmp_path / "test_calculator.py").write_text(
        "from calculator import divide\n\n"
        "def test_divide():\n    assert divide(6, 2) == 3\n",
        encoding="utf-8",
    )
    replies = [
        ModelReply(
            tool_calls=(
                ToolCall(
                    "call-1",
                    "write_file",
                    {
                        "path": "calculator.py",
                        "content": "def divide(a, b):\n    return a / b\n",
                    },
                ),
            )
        ),
        ModelReply(tool_calls=(ToolCall("call-2", "run_tests", {}),)),
    ]
    monkeypatch.setattr(agent_module, "DeepSeekModel", lambda: FakeModel(replies))

    exit_code = agent_module.main(
        ["--workspace", str(tmp_path), "--task", "Fix division"]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Result: success - tests passed" in captured.out


def test_main_returns_two_for_missing_workspace(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing = tmp_path / "missing"

    exit_code = agent_module.main(
        ["--workspace", str(missing), "--task", "Fix division"]
    )

    captured = capsys.readouterr()
    assert exit_code == 2
    assert f"Error: workspace is not a directory: {missing}" in captured.out
```

- [ ] **Step 2: Verify main is absent**

Run:

```powershell
py -m pytest tests/test_cli.py -q
```

Expected: two failures containing `AttributeError` because `agent.main` does not exist.

- [ ] **Step 3: Add CLI construction to agent.py**

Add these imports to `agent.py`:

```python
import argparse
from pathlib import Path

from knowflow_agent.model import DeepSeekModel
```

Keep the existing imports and append:

```python
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the teaching SWE agent")
    parser.add_argument("--workspace", required=True, help="Trusted Python workspace")
    parser.add_argument("--task", required=True, help="One clear repair task")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"Error: workspace is not a directory: {workspace}")
        return 2

    try:
        model = DeepSeekModel()
        tools = WorkspaceTools(workspace)
    except ValueError as exc:
        print(f"Error: {exc}")
        return 2

    result = Agent(model, tools).run(args.task)
    status = "success" if result.success else "failed"
    print(f"Result: {status} - {result.summary}")
    return 0 if result.success else 1
```

- [ ] **Step 4: Add module entry point**

Create `src/knowflow_agent/__main__.py`:

```python
from knowflow_agent.agent import main


raise SystemExit(main())
```

- [ ] **Step 5: Add and install console entry point**

Add this section after the closing bracket of the `dev` dependency list and before `[tool.setuptools.packages.find]` in `pyproject.toml`:

```toml
[project.scripts]
knowflow-agent = "knowflow_agent.agent:main"
```

Run:

```powershell
py -m pip install -e ".[dev]"
```

Expected: exit code `0`.

- [ ] **Step 6: Verify CLI tests**

Run:

```powershell
py -m pytest tests/test_cli.py -q
```

Expected: `2 passed`.

- [ ] **Step 7: Create learner README**

Create `README.md`:

```markdown
# KnowFlowAgent

KnowFlowAgent is a teaching-oriented minimal SWE Agent. DeepSeek chooses one action at a time, Python executes one of four safe tools, and pytest decides whether the repair worked.

## The whole idea

~~~text
task + observations -> model chooses tool -> tool runs -> new observation -> model
~~~

The three core modules are:

- tools.py: file and test side effects;
- model.py: FakeModel and DeepSeek decisions;
- agent.py: feedback loop and command line.

## Install

~~~powershell
py -m pip install -e ".[dev]"
~~~

## Run automatic tests

~~~powershell
py -m pytest -q
~~~

Automatic tests use fake models and spend no API credits.

## See the intentionally failing target

~~~powershell
py -m pytest examples/buggy_calculator -q
~~~

The failure is intentional. It is the bug the Agent will repair.

## Run a disposable DeepSeek demo

Set the key only in the current PowerShell process:

~~~powershell
$env:DEEPSEEK_API_KEY = "replace-with-your-key"
~~~

Copy the broken example so the tracked fixture stays unchanged:

~~~powershell
$demo = "work/demo-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
Copy-Item examples\buggy_calculator $demo -Recurse
~~~

Run the Agent:

~~~powershell
py -m knowflow_agent --workspace $demo --task "Fix divide so the tests pass."
~~~

Success requires a real pytest exit code of 0.

## Safety boundary

The Agent can only list, read, and overwrite existing Python files in the selected workspace, plus run the fixed pytest command. This is a teaching boundary, not a production sandbox: pytest executes trusted project code.
```

- [ ] **Step 8: Run complete offline verification**

Run:

```powershell
py -m pytest -q
py -m knowflow_agent --help
git diff --check
```

Expected: `20 passed`, help text containing `--workspace` and `--task`, no whitespace errors, and all commands exit `0`.

- [ ] **Step 9: Run live DeepSeek demonstration when a key is available**

Run:

```powershell
$demo = "work/demo-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
Copy-Item examples\buggy_calculator $demo -Recurse
py -m knowflow_agent --workspace $demo --task "Fix divide so the tests pass."
py -m pytest $demo -q
```

Expected: the log contains file observations, one write, and `run_tests`; the Agent prints `Result: success - tests passed`; the final pytest reports `1 passed`.

If `DEEPSEEK_API_KEY` is unavailable, do not claim live MVP verification. Report the missing prerequisite and retain the passing offline suite.

- [ ] **Step 10: Explain the full feedback loop**

Trace CLI input into `Agent.run`, through `DeepSeekModel.decide`, into `WorkspaceTools.call`, and back as an observation. Ask which evidence proves the repair worked.

- [ ] **Step 11: Commit milestone 6**

```powershell
git add -- pyproject.toml src/knowflow_agent/agent.py src/knowflow_agent/__main__.py tests/test_cli.py README.md
git commit -m "add runnable teaching SWE agent CLI"
```

- [ ] **Step 12: Final repository verification**

Run:

```powershell
py -m pytest -q
git status -sb
git log --oneline -8
```

Expected: `20 passed`, a clean working tree, and separate commits for six teaching milestones plus design and plan documentation.

- [ ] **Step 13: Push the verified milestone history**

Run:

```powershell
git push origin main
```

Expected: exit code `0`, with local `main` and `origin/main` pointing to the same final commit.
