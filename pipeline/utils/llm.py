"""
共享 LLM 调用模块。

封装 SiliconFlow API，提供统一的 call_llm 接口。
所有需要 LLM 调用的模块都应使用本模块，而不是自行实现。
"""
import json
import os
from typing import Optional, Dict, Any

import requests

DEFAULT_MODEL = "Qwen/Qwen2.5-7B-Instruct"
DEFAULT_BASE_URL = "https://api.siliconflow.com/v1"
DEFAULT_TIMEOUT = 60


def get_api_key() -> str:
    """从环境变量获取 API key。"""
    key = os.getenv("SILICONFLOW_API_KEY", "").strip()
    if not key:
        raise RuntimeError(
            "SILICONFLOW_API_KEY environment variable is not set. "
            "Please set it before using LLM features."
        )
    return key


def call_llm(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    base_url: Optional[str] = None,
    system_prompt: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
) -> Optional[Dict[str, Any]]:
    """
    调用 SiliconFlow API 并返回结构化 JSON 结果。

    Args:
        prompt: 用户输入的 prompt
        model: 模型名称，默认从 SILICONFLOW_MODEL 环境变量读取
        temperature: 温度参数，默认 0.3
        base_url: API 端点，默认从 SILICONFLOW_BASE_URL 环境变量读取
        system_prompt: 系统提示词，默认使用通用助手提示
        timeout: 请求超时秒数，默认 60

    Returns:
        解析后的 JSON dict，失败返回 None
    """
    api_key = get_api_key()
    resolved_model = model or os.getenv("SILICONFLOW_MODEL", DEFAULT_MODEL)
    resolved_base_url = base_url or os.getenv("SILICONFLOW_BASE_URL", DEFAULT_BASE_URL)

    default_system = (
        "You are a helpful assistant. Always respond with valid JSON."
    )
    system_content = system_prompt or default_system

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": resolved_model,
        "messages": [
            {"role": "system", "content": system_content},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }

    try:
        response = requests.post(
            f"{resolved_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"]
        return json.loads(content)

    except requests.RequestException as e:
        print(f"[llm] API request failed: {e}")
        return None
    except (json.JSONDecodeError, KeyError) as e:
        print(f"[llm] Failed to parse API response: {e}")
        return None
