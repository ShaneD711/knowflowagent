import os
import json
from openai import OpenAI
from knowflow_agent.deepseek_adapter import DeepSeekAdapter

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
    task: str,
    observations: list[dict[str, object]],
) -> str:
    """把 Agent 的任务和观察历史发送给 DeepSeek，返回动作 JSON 文本。"""

    # observations 是 Python 对象列表，这里把它转换成可以放进提示词的 JSON 文本。
    observation_text = json.dumps(observations, ensure_ascii=False)

    response = client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            # 这部分是给模型设定规则
            {
                "role": "system",
                "content": (
                    "你是一个最小 SWE Agent。"
                    "可用工具只有 list_files。"
                    "你必须只输出 JSON，不要输出解释。"
                    'JSON 格式示例：{"tool": "list_files"}'
                ),
            },
            # user 消息
            {
                "role": "user",
                "content": (
                    f"任务：{task}\n"
                    f"观察历史：{observation_text}\n"
                    "请选择下一步工具。"
                ),
            },
        ],
        # 限制返回格式为 JSON
        response_format={"type": "json_object"},
        max_tokens=100,
        # 关闭流式输出。模型生成完成后，一次性返回完整响应。
        stream=False,
        extra_body={
            # 关闭思考模式。
            "thinking": {
                "type": "disabled",
            }
        },
    )

    # 请求函数只返回 JSON 文本，解析工作交给 DeepSeekAdapter。
    response_text = response.choices[0].message.content

    if response_text is None:
        raise RuntimeError("DeepSeek 没有返回动作文本")

    return response_text


# 把真实请求函数交给模型适配层。
model = DeepSeekAdapter(request=request_deepseek)

# DeepSeekAdapter 请求 DeepSeek，并把 JSON 文本转换成动作字典。
action = model.decide(
    task="查看工作区中有哪些文件",
    observations=[],
)

print(action)
print(type(action))
print(action["tool"])
