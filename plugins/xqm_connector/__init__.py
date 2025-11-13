from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="xqm_connector",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

HACHIBOT_API_URL = ""
GI_MAIN_ROOMS_API_URL = "https://api/rooms"
GI_BETA_ROOMS_API_URL = "https:///api/rooms"

from nonebot import on_command
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageSegment,
    PrivateMessageEvent,
    GroupMessageEvent,
    MessageEvent,
    helpers,
    Bot
)
from nonebot.params import CommandArg

from typing import List
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
import httpx
import base64



async def get_image_data_uri(image_url: str) -> str:
    """
    从图片URL获取图片数据并转换为data URI
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(image_url)
            response.raise_for_status()
            
        # 转换为base64
        image_data = base64.b64encode(response.content).decode('utf-8')
        
        # 获取图片格式
        content_type = response.headers.get('content-type', 'image/jpeg')
        
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
    allowed_groups = [1030307936]
    text: str = msg.extract_plain_text()
    if any(text.startswith(prefix) for prefix in forbidden_prefixes) and event.group_id not in allowed_groups:
        await command.finish("xqm是大坏蛋；此命令已被禁止使用")
        raise ValueError("xqm是大坏蛋；此命令已被禁止使用")

from plugins.common import extract_image_data_url, extract_text
xqm = on_command("xqm", priority=102, block=True)
import requests
import re
@xqm.handle()
async def _(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    await check_forbidden(xqm, event, msg)
    url = HACHIBOT_API_URL

    param = {
        "msg": msg.extract_plain_text(),
        "qq": str(event.user_id),
        "group": str(event.group_id)
    }

    # 检查当前消息中的图片
    current_image_url = await extract_image_data_url(event)
    if current_image_url:
        param["image"] = current_image_url

    (content, replied_content) = await extract_text(event)
    if replied_content:
        param["ref"] = replied_content

    print("xqm param:", param)
    response = None
    try:
        async with httpx.AsyncClient(timeout=600, http2=True) as client:
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
            return
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

    if len(text) < 204:
        await xqm.finish(text)
    else:
        msgs = wrapMessageForward(f"{event.get_user_id()}说嘟嘟可是好人", [text])
        await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=msgs)

async def fetchGuyuRooms(url: str):
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url)
        response.raise_for_status()  # 检查 HTTP 状态码
        data = response.json()
    results = ""
    for item in data:
        room_id = item.get('id')
        players = item.get('players')
        names = [v.get('name') for v in players]
        players_str = " vs ".join(names)
        results += f"{room_id}-> {players_str} \n"
    return results


xqm2 = on_command("谁在", priority=2, block=True)
@xqm2.handle()
async def _(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    await check_forbidden(xqm2, event, msg)
    msg_text = str(event.get_message()).lstrip("/")
    if msg_text == "谁在气谷雨同学":
        await xqm2.finish("xqm在" + msg_text[2:])

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
