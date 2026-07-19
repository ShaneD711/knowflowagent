import os
from pathlib import Path
from openai import OpenAI
from knowflow_agent.deepseek_adapter import DeepSeekAdapter
from knowflow_agent.agent import run_agent

# 从当前终端读取 API Key。
api_key = os.environ.get("DEEPSEEK_API_KEY")

if api_key is None:
    raise RuntimeError("当前终端没有设置 DEEPSEEK_API_KEY")

# 创建连接 DeepSeek 的客户端。
client = OpenAI(
    api_key=api_key,
    base_url="https://api.deepseek.com",
)


def request_deepseek(
    system_prompt: str,
    user_prompt: str,
) -> str:
    """发送适配层准备好的提示文本，并返回 DeepSeek 的响应文本。"""

    # 输入：适配层已经准备好的系统提示词和用户提示词。
    # 处理：按照 OpenAI SDK 要求组成消息，然后发送给 DeepSeek。
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
        max_tokens=100,
        stream=False,
        extra_body={
            "thinking": {
                "type": "disabled",
            }
        },
    )

    # 输出：只返回 DeepSeek 生成的 JSON 文本，解析工作由适配层完成。
    response_text = response.choices[0].message.content

    if response_text is None:
        raise RuntimeError("DeepSeek 没有返回动作文本")

    return response_text


# 创建适配器时只保存请求函数；后续调用 decide 时才会真正发送请求。
adapter = DeepSeekAdapter(request=request_deepseek)

# 指定 Agent 这次允许观察的工作区。
workspace = Path("demo").resolve()

# 传入工作区，任务，适配器，最大步数，运行真实反馈循环。
summary = run_agent(
    workspace=workspace,
    task="查看工作区中有哪些文件，然后总结",
    model=adapter,
    max_steps=3,
)

print(summary)
