from plugins.common import autoWrapMessage, callSFImg, callSfVLM, limiter
from nonebot import on_command, get_driver
from nonebot.adapters.onebot.v11 import Message, MessageSegment, Event, MessageEvent
from nonebot.params import CommandArg
from nonebot.matcher import Matcher
from openai import OpenAI
import os
from typing import Optional, Dict, Any
from plugins.common import (
    autoWrapMessage,
    callSFImg,
    callSfVLM,
    callLLM,
    callDoubaoImage,
    extract_image_data_url,
)
from plugins.chat_oneapi import parse_input, DEFAULT_MODEL
from nonebot import get_plugin_config
import re
import httpx
from datetime import datetime

imgai = on_command("imgai", aliases={"ia"}, priority=5)
aiimg = on_command("aiimg", aliases={"ig"}, priority=5)
aiimg2 = on_command("aiimg2", aliases={"ig2"}, priority=10)
aiimg3 = on_command("aiimg3", aliases={"ig3"}, priority=15)
aiimg4 = on_command("aiimg4", aliases={"ig4"}, priority=16)
aiimg5 = on_command("aiimg5", aliases={"ig5"}, priority=17)

config = get_driver().config


async def call_openrouter(image_url: Optional[str], text: str) -> str:
    """调用 OpenRouter API."""
    client = OpenAI(
        base_url="",
        api_key="sk-noneed",
    )

    messages: list[Dict[str, Any]] = []
    messages.append({"role": "user", "content": [{"type": "text", "text": text}]})

    if image_url:
        messages[0]["content"].append(
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            }
        )

    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "your_site_url",  # Replace with your site URL
                "X-Title": "DuduBot",  # Replace with your site name
            },
            model="google/gemini-2.5-flash-image-preview",
            messages=messages,
            timeout=60,  # Add a timeout
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


async def call_xqm(
    image_url: Optional[str],
    text: str,
    model: str = "google/gemini-3-pro-image-preview",
    provider: str = "",
    url="",
) -> str:
    """
    直接通过 HTTP POST 调用 xqm 的 API，返回内容为 result。
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
    if "api.bltcy.ai" in url:
        api_key = os.environ.get("bltai_key", "")
        headers["Authorization"] = f"Bearer {api_key}"
    messages = [{"role": "user", "content": [{"type": "text", "text": text}]}]
    if image_url:
        messages[0]["content"].append(
            {"type": "image_url", "image_url": {"url": image_url}}
        )
    data = {"model": model, "messages": messages, "stream": False}
    if provider:
        # 使用 extra_body.provider.order 以强制路由到指定供应商（等价于示例中的 provider.order）
        data["extra_body"] = {"provider": {"order": [provider]}}
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
                    match = re.search(r"!\[.*?\]\((.*?)\)", msg_content)
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
        return f"API 调用失败: {str(e).replace(url, url[:14])}"


def is_data_uri(s: str) -> bool:
    return isinstance(s, str) and (s.startswith("data") or s.startswith("http"))


@aiimg.handle()
async def handle_aiimg(
    bot,
    matcher: Matcher,
    event: Event,
    args: Message = CommandArg(),
    model="gpt-image-2",
    url="",
):
    user_id = event.user_id

    special_dict = {
       
    }

    # 限制调用频率：24小时内最多4次
    if not limiter.checkWithSpecialUsers(
        "aiimg", str(user_id), 24 * 60, 4, special_dict
    ):
        await matcher.finish(
            "请节制生图，赞助...可尝试豆包渠道 /aiimg4"
        )

    """处理 /aiimg 命令."""
    image_url = None
    text = "Draw a picture of the following requests:"  # Default prompt

    # 1. 寻找图片 URL
    image_url = await extract_image_data_url(event)

    # 2. 寻找文本
    if event.reply:
        text += event.reply.message.extract_plain_text() + "\n"
    text += args.extract_plain_text()

    if not text:
        text = "Draw a picture of klee"  # Default prompt

    # 3. 调用 OpenRouter API
    if not image_url or not is_data_uri(image_url):
        result = await call_xqm(
            None,
            text,
            url=url,
            model=model,
            # model="gemini-3-pro-image-preview"
            # model="gemini-2.5-flash-image-preview"
        )
    else:
        result = await call_xqm(
            image_url,
            text,
            url=url,
            model=model,
            # model="gemini-3-pro-image-preview"
            # model="gemini-2.5-flash-image-preview"
        )

    # 4. 构造回复内容
    if is_data_uri(result):
        # data:image/png;base64,xxxx
        await matcher.finish(MessageSegment.image(result))
    else:
        await autoWrapMessage(bot, event, matcher, result)


@imgai.handle()
async def handle_imgai(
    bot, matcher: Matcher, event: Event, args: Message = CommandArg()
):
    image_url = None

    # 1. 寻找图片 URL
    image_url = await extract_image_data_url(event)
    if not image_url:
        await matcher.finish("图片解析失败")

    # 2. 解析输入
    data = args.extract_plain_text()
    model, content = await parse_input(data, is_llms=False)
    if model == DEFAULT_MODEL:
        model = "Qwen/Qwen3.5-397B-A17B"
    else:
        await matcher.send(f"Model：{model}")

    # 3. 构建文本
    text = "Explain this image. And then"
    if event.reply:
        text += event.reply.message.extract_plain_text() + "\n"
    text += content

    if is_data_uri(image_url):
        # 4. 调用 API
        if "doubao" in model:
            result = await callSfVLM(
                text,
                [image_url],
                model,
                img_field="input_image",
                txt_field="input_text",
                url=getattr(config, "openai_base_url", ""),
                token=getattr(config, "openai_api_key", ""),
            )
        else:
            result = await callSfVLM(
                text,
                [image_url],
                model,
                img_field="input_image",
                txt_field="input_text",
                url=getattr(config, "openai_base_url", ""),
                token=getattr(config, "openai_api_key", ""),
            )
        # result = await callSfVLM(text, [image_url], "zai-org/GLM-4.6V")
        if is_data_uri(result):
            # 5. 构造回复内容
            # data:image/png;base64,xxxx
            await matcher.finish(MessageSegment.image(result))
        else:
            await autoWrapMessage(bot, event, matcher, result)
    else:
        await autoWrapMessage(bot, event, matcher, image_url)


@aiimg2.handle()
async def handle_aiimg2(
    bot, matcher: Matcher, event: Event, args: Message = CommandArg()
):
    await handle_aiimg(
        bot, matcher, event, args,
        model="gemini-3-pro-image-preview"
    )
    return


@aiimg4.handle()
async def handle_aiimg4(
    bot,
    matcher: Matcher,
    event: Event,
    args: Message = CommandArg(),
    model: str = "doubao-seedream-4-5-251128",
    check: bool = True,
):
    current_date = datetime.now().strftime("%Y-%m-%d")
    if check and not limiter.check("aiimg4", current_date, 24 * 60, 20):
        await matcher.finish(
            "豆包生图限每日20张，可尝试/aiimg5(旧版)，或赞助嘟嘟bot以提升限额"
        )
    group_id = str(getattr(event, "group_id", ""))
    if check and group_id and not limiter.check(f"aiimg4_group", group_id, 24 * 60, 16):
        await matcher.finish(
            "本群豆包生图限16张/24h，可尝试/aiimg5，或赞助嘟嘟bot以提升限额"
        )
    text = "Draw a picture of the following requests:"  # Default prompt

    # 1. 寻找图片 URL
    image_url = await extract_image_data_url(event)

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


@aiimg5.handle()
async def handle_aiimg5(
    bot, matcher: Matcher, event: Event, args: Message = CommandArg()
):
    current_date = datetime.now().strftime("%Y-%m-%d")
    if not limiter.check("aiimg5", current_date, 24 * 60, 18):
        await matcher.finish(
            "豆包生图限每日18张，可尝试/aiimg /aiimg2，或赞助嘟嘟bot以提升限额"
        )
    await handle_aiimg4(
        bot, matcher, event, args, model="doubao-seedream-5-0-260128", check=False
    )
    return


@aiimg3.handle()
async def handle_aiimg3(
    bot, matcher: Matcher, event: Event, args: Message = CommandArg()
):
    await handle_aiimg(
        bot,
        matcher,
        event,
        args,
        model="gemini-3.1-flash-image-preview"
    )
    return
