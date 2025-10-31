from pydantic import BaseModel
from typing import List


class Config(BaseModel):
    # 腾讯云配置
    tencent_secret_id: str = ""
    tencent_secret_key: str = ""
    tencent_region: str = "ap-beijing"

    # 审查守卫监听的QQ号列表
    moderation_qq: List[str] = ["12345"]

    # 翻译守卫监听的QQ号列表
    translation_qq: List[str] = ["12345"]

    # 群聊审查配置
    # 群聊白名单：这些群中的消息不进行审查
    group_whitelist: List[str] = ["12345"]
    # 群聊黑名单：这些群中的消息必须进行审查（默认所有群都在黑名单中）
    group_blacklist: List[str] = []  # 空列表表示默认所有群都是黑名单

    # LLM配置
    llm_model: str = "z-ai/glm-4.5-air:free"