from nonebot import on_command, get_driver
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Event, MessageEvent
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from nonebot.adapters.onebot.v11.helpers import extract_image_urls
from openai import OpenAI
import os
import asyncio
from typing import Optional, Dict, Any
from plugins.common import autoWrapMessage, callSFImg, callSfVLM, limiter, callDoubaoImage
from nonebot import get_plugin_config
import re
import base64
import httpx

imgai = on_command("imgai", priority=5)
aiimg = on_command("aiimg", priority=5)
aiimg2 = on_command("aiimg2", priority=10)
aiimg3 = on_command("aiimg3", priority=15)
aiimg4 = on_command("aiimg4", priority=16)

config = get_driver().config


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


async def process_image(event: MessageEvent) -> str:
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
        return img_url
    except Exception as e:
        return f"图片处理失败: {str(e)}"

async def call_openrouter(image_url: Optional[str], text: str) -> str:
    """调用 OpenRouter API."""
    client = OpenAI(
        base_url="https://hachibot.xqm32.org/api/v1",
        api_key="sk-noneed",
    )

    messages: list[Dict[str, Any]] = []
    messages.append({"role": "user", "content": [{"type": "text", "text": text}]})

    if image_url:
        messages[0]["content"].append({
            "type": "image_url",
            "image_url": {"url": image_url},
        })

    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "your_site_url",  # Replace with your site URL
                "X-Title": "DuduBot",  # Replace with your site name
            },
            model="google/gemini-2.5-flash-image-preview",
            messages=messages,
            timeout=60  # Add a timeout
        )
        # 遍历所有choices，优先返回图片data uri，否则拼接所有文本
        image_data_uri = None
        texts = []
        for choice in completion.choices:
            content = choice.message.content
            if isinstance(content, str) and content.startswith("data:image/"):
                image_data_uri = content
                break
            elif isinstance(content, str):
                texts.append(content)
        if image_data_uri:
            return image_data_uri
        else:
            return "\n".join(texts)
    except Exception as e:
        return f"OpenRouter API 调用失败: {e}"

async def call_xqm(image_url: Optional[str], text: str, 
                   model: str = "google/gemini-3-pro-image-preview",
                   provider: str = "",
                   url = "https://hachibot.xqm32.org/api/v1/chat/completions") -> str:
    """
    直接通过 HTTP POST 调用 xqm32.org 的 API，返回内容为 result。
    """
    
    headers = {
        "Content-Type": "application/json",
    }
    if "https://api.chatanywhere.tech/" in url:
        api_key = os.environ.get("CHATANY_API_KEY", "")
        headers["Authorization"] = f"Bearer {api_key}"
    if "https://openrouter.ai/api/v1" in url:
        api_key = os.environ.get("MY_OR_KEY", "")
        headers["Authorization"] = f"Bearer {api_key}"
    messages = [{
        "role": "user",
        "content": [{"type": "text", "text": text}]
    }]
    if image_url:
        messages[0]["content"].append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
    data = {
        "model": model,
        "messages": messages,
        "stream": False
    }
    if provider:
        # 使用 extra_body.provider.order 以强制路由到指定供应商（等价于示例中的 provider.order）
        data["extra_body"] = {
            "provider": {
                "order": [provider]
            }
        }
    try:
        content = ""
        async with httpx.AsyncClient(timeout=600) as client:
            resp = await client.post(url, headers=headers, json=data)
            resp.raise_for_status()
            result = resp.json()
            # print(result)
            # 新结构处理
            for choice in result.get("choices", []):
                msg = choice.get("message", {})
                # 检查 content 中的 markdown 图片
                msg_content = msg.get("content", "")
                if msg_content:
                    match = re.search(r'!\[.*?\]\((.*?)\)', msg_content)
                    if match:
                        url = match.group(1)
                        print(f"get markdown url: {url[:14]}...")
                        if url and is_data_uri(url):
                            return url

                images = msg.get("images", [])
                if images:
                    for img in images:
                        url = img.get("image_url", {}).get("url")
                        print(f"get url: {url[:14]}...")  # 修复bug，显示前14位
                        if url and is_data_uri(url):
                            return url  # 返回图片直链
                else:
                    print(f"no images for this request, {str(msg)[:200]}")
                content += "\n" + str(msg_content)
            if content:
                return content
            return "未获取到有效回复"
    except Exception as e:
        return f'API 调用失败: {str(e).replace(url, url[:14])}'

def is_data_uri(s: str) -> bool:
    return isinstance(s, str) and (s.startswith("data") or s.startswith("http")) 

@aiimg.handle()
async def handle_aiimg(bot, matcher: Matcher, event: Event, args: Message = CommandArg(), model="gemini-3-pro-image-preview",
url="https://api.chatanywhere.tech/v1/chat/completions"):
    user_id = event.user_id
    
    special_dict = {
        "1211660648": -1,
        "1553636305": -1, # 好哥哥们求求你啦
        "725230880": 30,
        "458173774": 10,
        "2735274489": 10,
        "2438771332": -1,
        "1063438541": 15
    }
    
    # 限制调用频率：192小时内最多4次
    if not limiter.checkWithSpecialUsers("aiimg", str(user_id), 192 * 60, 4, special_dict):
        await matcher.finish("没钱生图了，赞助嘟嘟bot以提升限额（感谢xqm, 氢原子）")
    
    """处理 /aiimg 命令."""
    image_url = None
    text = "Draw a picture of the following requests:"  # Default prompt

    # 1. 寻找图片 URL
    image_url = await process_image(event)

    # 2. 寻找文本
    if event.reply:
        text += event.reply.message.extract_plain_text() + "\n"
    text += args.extract_plain_text()

    if not text:
        text = "Draw a picture of klee"  # Default prompt

    # 3. 调用 OpenRouter API
    if not image_url or not is_data_uri(image_url):
        result = await call_xqm(None, text, 
        url=url, 
        model=model
        #model="gemini-3-pro-image-preview"
        #model="gemini-2.5-flash-image-preview"
        )
    else:
        result = await call_xqm(image_url, text, 
        url=url,
        model=model
        #model="gemini-3-pro-image-preview"
        #model="gemini-2.5-flash-image-preview"
        )

    # 4. 构造回复内容
    if is_data_uri(result):
        # data:image/png;base64,xxxx
        await matcher.finish(MessageSegment.image(result))
    else:
        await autoWrapMessage(bot, event, matcher, result)

@imgai.handle()
async def handle_imgai(bot, matcher: Matcher, event: Event, args: Message = CommandArg()):
    image_url = None
    text = "Explain this image:"

    # 1. 寻找图片 URL
    image_url = await process_image(event)
    if not image_url:
        await matcher.finish("图片解析失败")

    # 2. 寻找文本
    if event.reply:
        text += event.reply.message.extract_plain_text() + "\n"
    text += args.extract_plain_text()


    if is_data_uri(image_url):
        # 3. 调用 OpenRouter API
        result = await callSfVLM(text, [image_url], "ep-20251206222208-k45ft",
        img_field="input_image", txt_field="input_text",
        url=getattr(config, "openai_base_url", ""),
        token=getattr(config, "openai_api_key", "")
        )
        #result = await callSfVLM(text, [image_url], "Qwen/Qwen3-VL-32B-Thinking")
        if is_data_uri(result):
            # 4. 构造回复内容
            # data:image/png;base64,xxxx
            await matcher.finish(MessageSegment.image(result))
        else:
            await autoWrapMessage(bot, event, matcher, result)
    else:
        await autoWrapMessage(bot, event, matcher, image_url)

@aiimg2.handle()
async def handle_aiimg2(bot, matcher: Matcher, event: Event, args: Message = CommandArg()):
    await handle_aiimg(bot, matcher, event, args, model="gemini-2.5-flash-image-preview")
    return

@aiimg4.handle()
async def handle_aiimg4(bot, matcher: Matcher, event: Event, args: Message = CommandArg()):
    """处理 /aiimg4 命令."""
    if not limiter.check("aiimg4", "*", 24 * 60, 10):
        await matcher.finish("豆包生图限每日10张，使用其他渠道，或赞助嘟嘟bot以提升限额（感谢xqm, 氢原子）")
    model = "doubao-seedream-4-0-250828"
    text = "Draw a picture of the following requests:"  # Default prompt

    # 1. 寻找图片 URL
    image_url = await process_image(event)

    # 2. 寻找文本
    if event.reply:
        text += event.reply.message.extract_plain_text() + "\n"
    text += args.extract_plain_text()

    # 3. 调用 OpenRouter API
    try:
        if not image_url or not is_data_uri(image_url):
            result = await callDoubaoImage(text, model)
        else:
            result = await callDoubaoImage(text, model, image_url)

        # 4. 构造回复内容
        if is_data_uri(result):
            # data:image/png;base64,xxxx
            await matcher.finish(MessageSegment.image(result))
        else:
            await autoWrapMessage(bot, event, matcher, result)
    except Exception as e:
        # 提取异常信息的前30个字符
        error_msg = str(e)[:30]
        print(f"生成图片失败: {error_msg}")

@aiimg3.handle()
async def handle_aiimg3(bot, matcher: Matcher, event: Event, args: Message = CommandArg()):
    await handle_aiimg(bot, matcher, event, args, model="google/gemini-3-pro-image-preview", 
    url="https://openrouter.ai/api/v1/chat/completions")
    return
