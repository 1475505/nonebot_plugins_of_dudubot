from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="summary_image",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

import os
from openai import AsyncOpenAI
from nonebot import on_command, on_message, Bot
from nonebot.rule import Rule
from nonebot.adapters.onebot.v11 import MessageEvent, Message, MessageSegment
from nonebot.adapters.onebot.v11.helpers import extract_image_urls
from nonebot.matcher import Matcher
from nonebot.params import EventMessage, CommandArg
from typing import Optional
import httpx
import base64
import asyncio
from plugins.common import autoWrapMessage

# 腾讯混元API配置
HUNYUAN_API_KEY = os.environ.get("HUNYUAN_API_KEY", "sk-")
API_BASE_URL = "https://api.hunyuan.cloud.tencent.com/v1"

# 默认提示语
DEFAULT_PROMPT = "简洁地输出该图片的内容"

# 创建异步OpenAI客户端
client = AsyncOpenAI(
    api_key=HUNYUAN_API_KEY,
    base_url=API_BASE_URL,
)

async def analyze_image(image_url: str, prompt: str) -> str:
    """使用腾讯混元API分析图片"""
    try:
        # 构造消息内容
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": image_url}
                    }
                ]
            }
        ]

        # 调用API
        response = await client.chat.completions.create(
            model="hunyuan-turbos-vision-20250619",
            #model="hunyuan-t1-vision-20250619",
            messages=messages,
            max_tokens=1024,
            temperature=0.5
        )

        return response.choices[0].message.content

    except Exception as e:
        return f"图片分析失败: {str(e)}"

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

async def process_image(event: MessageEvent, prompt: str) -> Optional[str]:
    """处理并分析图片"""
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
        return await analyze_image(img_url, prompt)

    except Exception as e:
        return f"图片处理失败: {str(e)}"

# 处理命令形式: /imgai <prompt> [图片]
imgai_command = on_command("imgai", aliases={"img2txt", "totxt"}, priority=5, block=True)

@imgai_command.handle()
async def handle_imgai_command(bot: Bot, event: MessageEvent, matcher: Matcher, args: Message = CommandArg()):
    # 提取提示语
    prompt = args.extract_plain_text().strip() or DEFAULT_PROMPT

    # 处理图片并获取结果
    result = await process_image(event, prompt)
    if result:
        await autoWrapMessage(bot, event, matcher, result)
        #await matcher.finish(result)

# 处理引用形式: 引用图片 + /imgai <prompt>
async def is_reply_imgai(event: MessageEvent) -> bool:
    """检查是否为引用图片+imgai命令的消息"""
    if not hasattr(event, "reply") or not event.reply:
        return False

    # 检查回复消息是否包含图片
    if not extract_image_urls(event.reply.message):
        return False

    # 检查当前消息是否以命令开头
    msg_text = event.message.extract_plain_text().strip()
    return msg_text.startswith(("/imgai", "/totxt"))

reply_imgai = on_message(
    rule=Rule(is_reply_imgai),
    priority=6,
    block=True
)

@reply_imgai.handle()
async def handle_reply_imgai(bot: Bot, event: MessageEvent, matcher: Matcher):
    # 提取提示语
    msg_text = event.message.extract_plain_text().strip()
    prompt = msg_text.replace("/imgai", "").replace("/totxt", "").strip()
    prompt = prompt or DEFAULT_PROMPT

    # 处理图片并获取结果
    result = await process_image(event, prompt)
    if result:
        #await matcher.finish(result)
        await autoWrapMessage(bot, event, matcher, result)

import os
from datetime import datetime  # 添加这一行
from nonebot.adapters.onebot.v11 import MessageEvent, Message, MessageSegment
from nonebot.matcher import Matcher
from nonebot.params import CommandArg
import httpx
import base64
import json
import hashlib
import hmac
import time

# 腾讯云配置
SECRET_ID = os.environ.get("HUNYUAN_SECRET_ID", "")
SECRET_KEY = os.environ.get("HUNYUAN_SECRET_KEY", "")
TEXT_TO_IMAGE_ENDPOINT = "https://hunyuan.tencentcloudapi.com"

# 默认提示语
DEFAULT_GEN_PROMPT = "请基于下面的文本生成图片:"

# 注册文生图命令
aiimg_command = on_command(
    "aiimg", 
    aliases={"draw", "toimg"},
    priority=5,
    block=True
)

@aiimg_command.handle()
async def handle_aiimg_command(
    event: MessageEvent, 
    matcher: Matcher, 
    args: Message = CommandArg()
):
    # 提取当前消息的prompt2
    prompt2 = args.extract_plain_text().strip()
    # 检查是否引用了消息
    prompt1 = ""
    if hasattr(event, "reply") and event.reply:
        prompt1 = event.reply.message.extract_plain_text().strip()
    # 合并prompt
    if prompt2 or prompt1:
        prompt = (prompt2 + " " + prompt1).strip()
    else:
        prompt = DEFAULT_GEN_PROMPT
    # 调用文生图API
    #result = await text_to_image_lite(prompt)
    result = await callModelImage(prompt) 
    # 发送结果
    if isinstance(result, MessageSegment):
        await matcher.finish(Message(result))
    else:
        await matcher.finish(result)

# 支持直接引用消息+aiimg命令（如：引用消息<prompt1> /aiimg <prompt2>）
async def is_reply_aiimg(event: MessageEvent) -> bool:
    if not hasattr(event, "reply") or not event.reply:
        return False
    msg_text = event.message.extract_plain_text().strip()
    return msg_text.startswith(("/aiimg", "/draw", "/toimg"))

reply_aiimg = on_message(
    rule=Rule(is_reply_aiimg),
    priority=6,
    block=True
)

@reply_aiimg.handle()
async def handle_reply_aiimg(event: MessageEvent, matcher: Matcher):
    # prompt2
    msg_text = event.message.extract_plain_text().strip()
    prompt2 = msg_text
    for cmd in ["/aiimg", "/toimg", "/draw"]:
        if prompt2.startswith(cmd):
            prompt2 = prompt2[len(cmd):].strip()
    # prompt1
    prompt1 = event.reply.message.extract_plain_text().strip() if event.reply else ""
    # 合并
    prompt = (prompt2 + " " + prompt1).strip() or DEFAULT_GEN_PROMPT
    #result = await text_to_image_lite(prompt)
    result = await callModelImage(prompt) 
    if isinstance(result, MessageSegment):
        await matcher.finish(Message(result))
    else:
        await matcher.finish(result)

import os
import json
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.hunyuan.v20230901 import hunyuan_client, models
import httpx
from nonebot.adapters.onebot.v11 import MessageSegment

async def text_to_image_lite(prompt: str) -> MessageSegment:
    """调用腾讯云轻量版文生图API"""
    try:
        cred = credential.Credential(
            os.getenv("TENCENTCLOUD_SECRET_ID", SECRET_ID),
            os.getenv("TENCENTCLOUD_SECRET_KEY", SECRET_KEY)
        )
        httpProfile = HttpProfile()
        httpProfile.endpoint = "hunyuan.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = hunyuan_client.HunyuanClient(cred, "ap-guangzhou", clientProfile)

        req = models.TextToImageLiteRequest()
        params = {
            "Prompt": prompt,
            "RspImgType": "url"
        }
        req.from_json_string(json.dumps(params))
        resp = client.TextToImageLite(req)
        img_url = resp.ResultImage
        return MessageSegment.image(img_url)
    except TencentCloudSDKException as err:
        return f"❌ 腾讯云SDK错误: {str(err)}"
    except Exception as e:
        return f"⚠️ 错误: {str(e)}"

