from pydantic import BaseModel
from typing import Optional

class Config(BaseModel):
    """Plugin Config Here"""
    chat_oneapi_key: Optional[str] = ""  # （必填）OpenAI官方或者是支持OneAPI的大模型中转服务商提供的KEY
    chat_oneapi_url: Optional[str] = ""  # （可选）大模型中转服务商提供的中转地址，使用OpenAI官方服务不需要填写
