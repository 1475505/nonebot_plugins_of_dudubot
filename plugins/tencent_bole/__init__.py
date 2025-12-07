from nonebot import on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageSegment
from nonebot.plugin import PluginMetadata
from datetime import datetime
import json
import os
from pathlib import Path

# 插件元信息
__plugin_meta__ = PluginMetadata(
    name="内推自动机",
    description="当日首次出现'鹅'消息时发送图片",
    usage="当群内第一次出现包含'鹅'的消息时，机器人会发送一张图片",
    type="application",
)

# 状态存储文件路径
STATE_FILE = Path("data/goose_plugin_state.json")

# 确保数据目录存在
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)

# 加载状态
def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

# 保存状态
def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# 消息事件处理器
goose_matcher = on_message(priority=10, block=False)

@goose_matcher.handle()
async def handle_goose(event: GroupMessageEvent):
    text = event.get_plaintext()

    # 获取当前日期
    today = datetime.now().strftime("%Y-%m-%d")

    # 加载状态
    state = load_state()

    # 检查该群今天是否已经触发过
    group_id = str(event.group_id)
    if group_id in state and state[group_id] == today:
        return
    

    # 检查消息是否包含"鹅"
    if "鹅" in text or "腾讯" in text or "宇宙厂" in text:
        # 更新状态
        state[group_id] = today
        save_state(state)

        # 发送图片
        # 这里替换为你要发送的图片路径或URL
        image_path = "https://7s-1304005994.cos.ap-singapore.myqcloud.com/tencent_bole.png"  # 本地文件路径
        img = MessageSegment.image(image_path)

        await goose_matcher.finish(img)
    elif "bytedance" in text.lower() or "字节跳动" in text or "火山引擎" in text:
        state[group_id] = today
        save_state(state)

        image_path = "/root/nb/resources/zijie_neitui.png"  # 本地文件路径
        img = MessageSegment.image(image_path)

        await goose_matcher.finish(img)
    elif "bot群" in text:
        state[group_id] = today
        save_state(state)

        await goose_matcher.finish("玩刷屏游戏的话，可以进群 1030307936 （https://qm.qq.com/q/Zinx0Q7HOK）")
        
