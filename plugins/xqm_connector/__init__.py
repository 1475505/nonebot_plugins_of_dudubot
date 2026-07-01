from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from pypinyin import pinyin, Style

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="xqm_connector",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

HACHIBOT_API_URL = "https://hachibot"
GI_MAIN_ROOMS_API_URL = ""
GI_BETA_ROOMS_API_URL = ""

from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageSegment,
    PrivateMessageEvent,
    GroupMessageEvent,
    MessageEvent,
    helpers,
    Bot,
)
from nonebot.params import CommandArg

from typing import List


def wrapMessageForward(title: str, texts: List[str]):
    msgs = []
    for text in texts:
        msgs.append(
            {
                "type": "node",
                "data": {"name": title, "content": MessageSegment.text(text)},
            }
        )
    return msgs


import httpx
import base64
import asyncio


async def poll_memos_status(
    bot: Bot, event: MessageEvent, param: dict, max_polls: int = 5
):
    """轮询memos状态，最多5次，每次间隔60秒"""
    memos_url_pattern = "https://memos.?/memos/"
    url = HACHIBOT_API_URL

    for poll_count in range(max_polls):
        await asyncio.sleep(60)  # 等待60秒

        try:
            async with httpx.AsyncClient(
                timeout=600,
                http2=True,
                limits=httpx.Limits(
                    max_connections=50,
                    max_keepalive_connections=10,
                    keepalive_expiry=30,
                ),
            ) as client:
                response = await client.post(url, data=param)
                response.raise_for_status()
                text = response.text.strip()

                # 如果返回内容不以memos URL开头，发送最终结果并结束
                if not text.startswith(memos_url_pattern) and text != "generating..." and text != "少女祈祷中...":
                    # await bot.send(event, f"任务完成：{text}")
                    msgs = wrapMessageForward(f"任务完成", [text])
                    await bot.call_api(
                        "send_group_forward_msg", group_id=event.group_id, messages=msgs
                    )
                    return

        except Exception as e:
            print(e)
            await bot.send(event, f"少女吃多了：{str(e)[:50]}")
            return

    # 达到最大轮询次数
    await bot.send(event, "再次踏上轮回...(无结果, 任务结束)")


async def get_image_data_uri(image_url: str) -> str:
    """
    从图片URL获取图片数据并转换为data URI
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            response.raise_for_status()

        # 转换为base64
        image_data = base64.b64encode(response.content).decode("utf-8")

        # 获取图片格式
        content_type = response.headers.get("content-type", "image/jpeg")

        # 返回data URI
        return f"data:{content_type};base64,{image_data}"
    except Exception as e:
        print(f"获取图片失败: {e}")
        return None


async def extract_image_from_message(message: Message) -> str:
    """
    从消息中提取第一张图片的URL
    """
    for segment in message:
        if segment.type == "image":
            return segment.data.get("url")
    return None


async def check_forbidden(command, event: MessageEvent, msg: Message):
    forbidden_prefixes = ["/guyu", "/gυyυ"]
    allowed_groups = [?]
    text: str = msg.extract_plain_text()
    if (
        any(text.startswith(prefix) for prefix in forbidden_prefixes)
        and event.group_id not in allowed_groups
    ):
        await command.finish("此命令已被禁止使用")
        raise ValueError("此命令已被禁止使用")


from plugins.common import extract_image_data_url, extract_text, add_to_queue

xqm = on_command("xqm", aliases={"x"}, priority=102, block=True)
import requests
import re


@xqm.handle()
async def _(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    await check_forbidden(xqm, event, msg)
    if event.group_id in config.group_blacklist:
        await xqm.finish("该群已被禁止使用x命令")
        return
    add_to_queue(event.group_id)
    url = HACHIBOT_API_URL
    group_id = str(event.group_id)

    param = {
        "qq": str(event.user_id),
        "group": str(event.group_id),
        "msg": msg.extract_plain_text(),
    }

    if group_id == "?":
        await xqm.finish("forbidden")
        return

    # 检查当前消息中的图片
    current_image_url = await extract_image_data_url(event)
    if current_image_url:
        param["image"] = current_image_url

    (content, replied_content) = await extract_text(event)
    if replied_content:
        param["ref"] = replied_content

    print("xqm param:", str(param)[:150])
    response = None
    try:
        async with httpx.AsyncClient(
            timeout=600,
            http2=True,
            limits=httpx.Limits(
                max_connections=50, max_keepalive_connections=10, keepalive_expiry=30
            ),
        ) as client:
            response = await client.post(url, data=param)
            response.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 502:
            # 502错误重试一次
            try:
                async with httpx.AsyncClient(timeout=600, http2=True) as client:
                    response = await client.post(url, data=param)
                    response.raise_for_status()
            except Exception as retry_e:
                await xqm.send(str(retry_e)[:18] + "...")
                return
        else:
            await xqm.send(str(e)[:18] + "...")
    except Exception as e:
        await xqm.send(str(e)[:18] + "...")
        return

    if response is None:
        return

    text = response.text
    img_url_pattern = r"^https?://[^\s?#]+\.(?:jpg|jpeg|png|gif|webp|bmp)(?:\?.*)?$"
    txt = text.strip()
    data_match = re.match(r"^data:image/[^;]+;base64,([A-Za-z0-9+/=]+)$", txt)
    url_match = re.match(img_url_pattern, txt, re.IGNORECASE)
    if data_match or url_match:
        return await xqm.finish(MessageSegment.image(txt))

    # 检查是否是需要轮询的memos URL
    memos_url_pattern = "https://memos?/memos/"
    if text.startswith(memos_url_pattern):
        # 发送初始memos URL
        await xqm.send(text)
        # 启动轮询任务
        param["ref"] = text
        param["msg"] = "m"
        asyncio.create_task(poll_memos_status(bot, event, param))
        return

    if len(text) < 204:
        await xqm.finish(text)
    else:
        if text.startswith("📝 https://memos.?/memos/"):
            await xqm.send(text.split("\n")[0].replace("📝 ", ""))
        if any(
            word in text
            for word in ["习近平", "共产党", "六四事件", "64事件", "社会主义", "中共", "金正恩", "老蒋", "蒋介石", "国民党"]
        ):
            print(retContent)
            await xqm.finish(
                "为了保护Bot的发言安全，本次回复已屏蔽。请调整使用方式", at_sender=True
            )
            return
        msgs = wrapMessageForward(f"{event.get_user_id()}说嘟嘟可是好人", [text])
        await bot.call_api(
            "send_group_forward_msg", group_id=event.group_id, messages=msgs
        )


async def fetchGuyuRooms(url: str):
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()  # 检查 HTTP 状态码
        data = response.json()
    results = ""
    for item in data:
        room_id = item.get("id")
        players = item.get("players")
        names = [v.get("name") for v in players]
        players_str = " vs ".join(names)
        results += f"{room_id}-> {players_str} \n"
    return results


async def call_hachibot(params: dict) -> str:
    """调用hachibot API的通用方法

    Args:
        params: 请求参数字典

    Returns:
        str: API返回的文本内容

    Raises:
        httpx.HTTPStatusError: HTTP状态码错误
        Exception: 其他网络错误
    """
    url = HACHIBOT_API_URL

    async with httpx.AsyncClient(
        timeout=600,
        http2=True,
        limits=httpx.Limits(
            max_connections=50,
            max_keepalive_connections=10,
            keepalive_expiry=30,
        ),
    ) as client:
        response = await client.post(url, data=params)
        response.raise_for_status()
        return response.text


xqm2 = on_command("谁在", aliases={"小雀"}, priority=2, block=True)

def check_mr_initials(text):
    # 1. 检查是否为长度为 2 的字符串
    if len(text) != 2:
        return False
    
    # 2. 检查是否全是汉字 (使用正则表达式)
    if not all('\u4e00' <= char <= '\u9fff' for char in text):
        return False
    
    # 3. 提取拼音首字母
    # Style.FIRST_LETTER 仅获取拼音的首字母并转为小写
    initials = pinyin(text, style=Style.FIRST_LETTER)
    
    # initials 的结构类似 [['m'], ['r']]
    first_char_initial = initials[0][0]
    second_char_initial = initials[1][0]
    
    return first_char_initial == 'm' and second_char_initial == 'r'

@xqm2.handle()
async def _(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    await check_forbidden(xqm2, event, msg)
    msg_text = str(event.get_message()).lstrip("/")
    if msg_text == "谁在气谷雨同学":
        await xqm2.finish("xqm在" + msg_text[2:])
    if not (msg_text.startswith("小雀") and check_mr_initials(msg_text[2:])):
        return

    result = "[main]\n"
    main_rooms = await fetchGuyuRooms(GI_MAIN_ROOMS_API_URL)
    beta_rooms = await fetchGuyuRooms(GI_BETA_ROOMS_API_URL)
    result += main_rooms
    result += "\n---Ciallo～(∠・ω< )⌒★! ---\n\n[beta]\n" + beta_rooms
    await xqm2.finish(result)


async def sendJson(data):
    for item in data:
        item_type = item.get("type")
        item_data = item.get("data")

        if not item_type or not item_data:
            continue  # 跳过无效数据

        # 3. 根据type类型处理
        if item_type == "text":
            await json_parser.finish(item_data)  # 发送文本消息
        elif item_type == "image":
            await json_parser.finish(MessageSegment.image(item_data))  # 发送图片
