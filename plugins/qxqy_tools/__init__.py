from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import (
    Message,
    MessageSegment,
    PrivateMessageEvent,
    GroupMessageEvent,
    MessageEvent,
    Bot
)
from nonebot import on_command
from nonebot.params import CommandArg
import aiohttp
import json
import random

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="qxqy_tools",
    description="千星奇域问答工具",
    usage="/qxqy 问题 - 获取千星奇域问答答案",
    config=Config,
)

config = get_plugin_config(Config)

# 创建命令处理器
qxqy_command = on_command("qxqy", aliases={"QXQY"}, block=True, priority=5)

def wrapMessageForward(title: str, texts: list):
    """包装转发消息格式"""
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

@qxqy_command.handle()
async def handle_qxqy(bot: Bot, event: MessageEvent, msg: Message = CommandArg()):
    """处理 /qxqy 命令"""
    # 只允许群聊使用
    if isinstance(event, PrivateMessageEvent):
        await qxqy_command.finish("对不起，私聊暂不支持此功能。")

    # 获取用户问题
    question = msg.extract_plain_text().strip()

    if not question:
        await qxqy_command.finish("请提供您的问题！例如：/qxqy 小地图如何使用？", at_sender=True)

    try:
        # 构造请求数据
        request_data = {
            "id": f"session_{event.group_id}_{event.user_id}_{random.randint(1000, 9999)}",
            "message": question,
            "conversation": [],
            "config": {
                "use_default_model": True
            }
        }

        # 发送API请求
        async with aiohttp.ClientSession() as session:
            async with session.post(
                config.qxqy_api_url,
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                if response.status != 200:
                    await qxqy_command.finish(f"API请求失败，状态码：{response.status}", at_sender=True)

                result = await response.json()

                if not result.get("success", False):
                    await qxqy_command.finish("API返回失败：" + result.get("message", "未知错误"), at_sender=True)

                data = result.get("data", {})
                answer = data.get("answer", "未找到答案")
                sources = data.get("sources", [])

                # 构造转发消息内容
                forward_messages = []

                # 第一条：答案
                forward_messages.append(answer)

                # 第二条：来源链接（如果有）
                if sources:
                    source_links = []
                    for source in sources:
                        title = source.get("title", "未知来源")
                        url = source.get("url", "")
                        if url:
                            source_links.append(f"• {title}\n  {url}")

                    if source_links:
                        source_text = "📚 参考来源：\n" + "\n".join(source_links)
                        forward_messages.append(source_text)

                # 发送转发消息
                if len(forward_messages) == 1 and len(forward_messages[0]) < 200:
                    # 如果答案较短且没有来源，直接发送
                    await qxqy_command.finish(forward_messages[0], at_sender=True)
                else:
                    # 使用转发消息格式
                    msgs = wrapMessageForward(f"千星奇域回答 to {event.user_id}", forward_messages)
                    await bot.call_api("send_group_forward_msg", group_id=event.group_id, messages=msgs)

    except aiohttp.ClientError as e:
        await qxqy_command.finish(f"网络请求失败：{str(e)}", at_sender=True)
    except json.JSONDecodeError:
        await qxqy_command.finish("API返回数据格式错误", at_sender=True)
    except Exception as e:
        await qxqy_command.finish(f"处理请求时发生错误：{str(e)}", at_sender=True)

