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

# TODO: async client
xqm = on_command("xqm", priority=2, block=True)
import requests
@xqm.handle()
async def _(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    if manager.contains("all"):
        return
    if not manager.contains(event.get_user_id()):
        #url = "https://bot.t.xqm32.org"
        url = "https://hachibot.xqm32.org"
        param = {
            "msg": msg.extract_plain_text(),
            "qq": str(event.user_id)
        }
        if event.reply:
            # 获取被引用消息的内容
            replied_message = event.reply.message
            replied_content = replied_message.extract_plain_text()  # 提取纯文本内容
            param["ref"] = replied_content
        print(param)
        try:
            response = requests.post(url, data=param, timeout=180)
        except Exception as e:
            await xqm.finish(f"{e}, 但是我知道嘟嘟可是好人")
        text = response.text
        if len(text) < 204:
            await xqm.finish(text)
        else:
            msgs = wrapMessageForward(f"{event.get_user_id()}说嘟嘟可是好人", [text])
            await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=msgs)



xqm2 = on_command("谁在打", priority=2, block=True)
@xqm2.handle()
async def _(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    if manager.contains("all"):
        return
    if not manager.contains(event.get_user_id()):
#        url = "https://bot.t.xqm32.org"
        url = "https://hachibot.xqm32.org"
        param = {
            "msg": str(event.get_message()).lstrip("/"),
            "qq": str(event.user_id)
        }
        print(param)
        response = requests.post(url, data=param, timeout=15)
        await xqm.finish(response.text)

# TODO: xqm 拒绝用json，要改成 xml
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
