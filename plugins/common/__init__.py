from nonebot import get_plugin_config
from nonebot import get_bot
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Event, MessageEvent
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.helpers import extract_image_urls
from nonebot.log import logger

from .config import Config
from .callSFImg import callSFImg, callSfVLM, callLLM
from .tencent_moderator import TencentTextModerator
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
import json
import html
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

async def extract_forward_text(bot: Bot, message: Message, limit: int = 1) -> List[str]:
    """从折叠消息（合并转发消息）中提取文本

    Args:
        bot: Bot实例
        message: 消息对象
        limit: 限制提取的文本数量，默认为1（只提取第一条），设为-1表示提取所有

    Returns:
        提取到的纯文本列表
    """
    texts = []
    extracted = 0
    unlimited = limit <= 0

    for seg in message:
        if not unlimited and extracted >= limit:
            break

        if seg.type == "forward":
            forward_data = await bot.call_api("get_forward_msg", id=seg.data["id"])

            if not forward_data:
                continue

            nodes = forward_data.get("messages", [])

            for node in nodes:
                if not unlimited and extracted >= limit:
                    break

                msg_text = (node.get("raw_message") or "").strip()
                if msg_text:
                    texts.append(msg_text)
                    extracted += 1

        elif seg.type == "json":
            payload = seg.data.get("data")
            if not payload:
                continue

            if isinstance(payload, str):
                try:
                    payload = json.loads(payload)
                except json.JSONDecodeError:
                    try:
                        payload = json.loads(html.unescape(payload))
                    except json.JSONDecodeError:
                        logger.warning("无法解析转发JSON消息: %s", payload)
                        continue

            if not isinstance(payload, dict):
                continue

            if payload.get("app") != "com.tencent.multimsg":
                continue

            news_items = (
                payload.get("meta", {})
                .get("detail", {})
                .get("news", [])
            )

            for item in news_items:
                if not unlimited and extracted >= limit:
                    break

                if not isinstance(item, dict):
                    continue

                msg_text = (item.get("text") or "").strip()
                if msg_text:
                    texts.append(msg_text)
                    extracted += 1

    return texts


async def extract_text(event: MessageEvent, forward_limit: int = 1) -> (str, str):
    """从Message event里提取文本. 返回：本体文本、消息回复文本

    如果回复的消息是折叠消息，会自动提取其中的文本（默认只提取第一条）

    Args:
        event: 消息事件
        forward_limit: 如果回复的是折叠消息，限制提取的文本数量（默认1）

    Returns:
        (本体文本, 消息回复文本) 元组
    """
    text = event.message.extract_plain_text().strip()
    replyText = ""

    if event.reply:
        # 先尝试直接提取文本
        replyText = event.reply.message.extract_plain_text().strip()

        # 如果没有提取到文本，检查是否是转发消息
        if not replyText:
            bot = get_bot()
            forward_texts = await extract_forward_text(bot, event.reply.message, limit=forward_limit)
            if forward_texts:
                replyText = forward_texts[0]  # 默认只取第一条

    return (text, replyText)

__all__ = ["autoWrapMessage", "wrapMessageForward", "splitTextToChunks", "callSFImg", "callSfVLM", "callLLM",
"get_image_data_url", "extract_image_data_url", "extract_text", "TencentTextModerator"]
