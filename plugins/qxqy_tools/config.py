from pydantic import BaseModel


class Config(BaseModel):
    """Plugin Config Here"""
    qxqy_api_url: str = "https://ugc.070077.xyz/api/v1/rag/chat"
