import os
from pathlib import Path
from openai import OpenAI
from knowflow_agent.deepseek_adapter import DeepSeekAdapter
from knowflow_agent.agent import run_agent

# API Key 只从环境变量读取，避免把密钥写进代码或提交到 Git。
api_key = os.environ.get("DEEPSEEK_API_KEY")

if api_key is None:
    raise RuntimeError("当前终端没有设置 DEEPSEEK_API_KEY")

# OpenAI SDK 通过 DeepSeek 提供的兼容地址发送请求。
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)


def request_deepseek(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """把适配器生成的提示文本发送给 DeepSeek。

    Args:
        system_prompt: 约束可用工具和响应格式的系统提示词。
        user_prompt: 包含任务和观察历史的用户提示词。

    Returns:
        DeepSeek 返回的动作 JSON 文本。

    Raises:
        RuntimeError: DeepSeek 响应中没有动作文本。
    """

    # 入口层只负责网络传输；提示词构造和响应解析由适配层负责。
    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=500,
        stream=False,
        extra_body={
            "thinking": {
                "type": "disabled",
            }
        },
    )

    # 保留供应商返回的原始文本，让适配层统一解析成动作字典。
    response_text = response.choices[0].message.content

    if response_text is None:
        raise RuntimeError("DeepSeek 没有返回动作文本")

    return response_text


# 注入请求函数后，适配器可以独立完成提示词和动作格式的转换。
adapter = DeepSeekAdapter(request=request_deepseek)

# 工作区同时限定 Agent 能观察和操作的文件范围。
workspace = Path("demo").resolve()

# 从这里启动“决策、执行、观察、再次决策”的真实反馈循环。
summary = run_agent(
    workspace=workspace,
    task="修复 calculator.py 中的错误，使测试通过",
    model=adapter,
    max_steps=8,
)

print(summary)
