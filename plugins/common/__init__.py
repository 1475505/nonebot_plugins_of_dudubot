from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Event, MessageEvent
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.helpers import extract_image_urls

from .config import Config
from .callSFImg import callSFImg, callSfVLM
from typing import List

__plugin_meta__ = PluginMetadata(
    name="common",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

from nonebot.adapters.onebot.v11 import MessageEvent, MessageSegment

def splitTextToChunks(text: str, chunk_size: int = 2048) -> List[str]:
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks

def wrapMessageForward(title: str, texts: List[str]):
    msgs = []
    for text in texts:
         msgs.append({
            "type": "node",
            "data": {
                "name": title,
                "content": MessageSegment.text(text)
            }
        })
    return msgs

from nonebot import Bot
async def autoWrapMessage(bot: Bot, event: MessageEvent, matcher: Matcher, text: str):
    if len(text) < 114:
        await matcher.finish(text, at_sender=True)
    else:
        texts = splitTextToChunks(text)
        msgs = wrapMessageForward(f"to {event.get_user_id()}", texts)
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=msgs)

import httpx
import base64
async def get_image_data_url(img_url: str) -> str:
    """将图片URL转换为base64格式的data URL"""
    async with httpx.AsyncClient() as client:
        response = await client.get(img_url)
        response.raise_for_status()
        img_data = response.content

        # 获取图片类型（默认为jpeg）
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        img_type = content_type.split('/')[-1]

        # 创建data URL
        img_base64 = base64.b64encode(img_data).decode('utf-8')
        return f"data:image/{img_type};base64,{img_base64}"


async def extract_image_data_url(event: MessageEvent) -> str:
    """从Message event里提取图片data url"""
    # 查找图片URL
    img_urls = extract_image_urls(event.message) or []

    # 如果是回复消息，检查回复中是否有图片
    if not img_urls and hasattr(event, "reply") and event.reply:
        img_urls = extract_image_urls(event.reply.message) or []

    if not img_urls:
        return "未找到图片，请确保消息中包含图片"

    try:
        # 将第一张图片转换为data URL
        img_url = await get_image_data_url(img_urls[0])
        return img_url
    except Exception as e:
        return f"图片处理失败: {str(e)}"

def extract_text(event: MessageEvent) -> (str, str):
    """从Message event里提取文本. 返回：本体文本、消息回复文本"""
    text = None
    replyText = None

    text = event.message.extract_plain_text().strip()
    if event.reply:
        replyText = event.reply.message.extract_plain_text().strip()

    return (text, replyText)

__all__ = ["autoWrapMessage", "wrapMessageForward", "splitTextToChunks", "callSFImg", "callSfVLM",
"get_image_data_url", "extract_image_data_url", "extract_text"]