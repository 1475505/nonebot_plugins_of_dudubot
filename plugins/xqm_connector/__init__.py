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

class QQSetManager:
    def __init__(self, file_path):
        """
        初始化时从文件加载数据到内存中的集合。
        :param file_path: 文件路径
        """
        self.file_path = file_path
        self.qq_set = set()
        self._load_from_file()

    def _load_from_file(self):
        """
        从文件加载数据到内存中的集合。
        """
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    qq = line.strip()
                    if qq:  # 忽略空行
                        self.qq_set.add(qq)
        except FileNotFoundError:
            # 如果文件不存在，创建一个空文件
            with open(self.file_path, 'w', encoding='utf-8') as f:
                pass

    def _save_to_file(self):
        """
        将内存中的集合保存到文件。
        """
        with open(self.file_path, 'w', encoding='utf-8') as f:
            for qq in sorted(self.qq_set):  # 按顺序写入文件
                f.write(f"{qq}\n")

    def contains(self, qq):
        """
        检查集合中是否包含指定的QQ号。
        :param qq: 要检查的QQ号
        :return: 如果存在返回True，否则返回False
        """
        return qq in self.qq_set

    def add(self, qq):
        """
        向集合中添加一个QQ号，并更新文件。
        :param qq: 要添加的QQ号
        """
        if qq not in self.qq_set:
            self.qq_set.add(qq)
            self._save_to_file()

    def delete(self, qq):
        """
        从集合中删除一个QQ号，并更新文件。
        :param qq: 要删除的QQ号
        """
        if qq in self.qq_set:
            self.qq_set.remove(qq)
            self._save_to_file()



file_path = "data/xqm_white.csv"  # 文件路径
manager = QQSetManager(file_path)

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

xadmin = on_command("xqmadmin", priority=1, block=True)
@xadmin.handle()
async def _(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    data = msg.extract_plain_text()
    (op, target) = data.split(':')
    print(op)
    print(target)
    op = op.strip()
    target = target.strip()
    if op == 'add':
        manager.add(target)
        await xadmin.finish(f"已添加QQ号{target}")
    elif op == 'delete':
        manager.delete(target)
        await xadmin.finish(f"已删除QQ号{target}")
    elif op == 'contains':
        if manager.contains(target):
            await xadmin.finish(f"QQ号{target}在黑名单中")
        else:
            await xadmin.finish(f"QQ号{target}不在黑名单中")
    else:
        await xadmin.finish("参数错误")

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
xqm = on_command("xqm", aliases={"imgai"}, priority=102, block=True)
import requests
import re
@xqm.handle()
async def _(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    if manager.contains("all"):
        return
    await check_forbidden(xqm, event, msg)
    if not manager.contains(event.get_user_id()):
        #url = "https://bot.t.xqm32.org"
        url = "https://hachibot.xqm32.org"

        param = {
            "msg": msg.extract_plain_text(),
            "qq": str(event.user_id),
            "group": str(event.group_id)
        }
        
        # 检查当前消息中的图片
        current_image_url = await extract_image_data_url(event)
        if current_image_url:
            param["image"] = current_image_url
        
        (content, replied_content) = extract_text(event)        
        if replied_content:
            param["ref"] = replied_content

        print("xqm param:", param)
        try:
            async with httpx.AsyncClient(timeout=600, http2=True) as client:
                response = await client.post(url, data=param)
                response.raise_for_status()
        except Exception as e:
            await xqm.send(str(e)[:18] + "...")
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
    if manager.contains("all"):
        return
    await check_forbidden(xqm2, event, msg)
    msg = str(event.get_message()).lstrip("/")
    if msg == "谁在气谷雨同学":
        await xqm2.finish("xqm在" + msg[2:])
    if not manager.contains(event.get_user_id()):
#        url = "https://bot.t.xqm32.org"
        result = "[main]\n"
        main_rooms = await fetchGuyuRooms("https://gi.xqm32.org/api/rooms")
        beta_rooms = await fetchGuyuRooms("https://beta.gi.xqm32.org/api/rooms")
        result += main_rooms
        result += "\n---Ciallo～(∠・ω< )⌒★! ---\n\n[beta]\n" + beta_rooms
        await xqm2.finish(result)
        return
        url = "https://hachibot.xqm32.org"
        param = {
            "msg": msg,
            "qq": str(event.user_id)
        }
        
        # 检查当前消息中的图片
        current_image_url = await extract_image_from_message(event.get_message())
        if current_image_url:
            image_data_uri = await get_image_data_uri(current_image_url)
            if image_data_uri:
                param["image"] = image_data_uri
        
        if event.reply:
            # 检查被引用消息中的图片
            if not current_image_url:  # 如果当前消息没有图片，检查被引用消息
                replied_image_url = await extract_image_from_message(event.reply.message)
                if replied_image_url:
                    image_data_uri = await get_image_data_uri(replied_image_url)
                    if image_data_uri:
                        param["image"] = image_data_uri
        
        print("xqm2 param:", param)
        response = requests.post(url, data=param, timeout=15)
        await xqm.finish(response.text)

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
