from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="starrail_lucky_star",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

import random

probabilities = [0.0005, 0.9, 0.1]
def draw_star_jade():
    # 定义对应的星琼数量
    rewards = [500000, 50, 600]

    # 抽签
    draw = random.choices(rewards, probabilities)[0]
    return draw

from nonebot import on_command

roll = on_command("银河幸运星")

@roll.handle()
async def _():
    total_star_jade = 0
    results = []

    msg = "\n"

    for i in range(7):
        result = draw_star_jade()
        results.append(result)
        total_star_jade += result

    # 打印每次抽签结果
    for i, result in enumerate(results, 1):
        msg += f"第 {i} 次抽签：{result} 星琼\n"

    # 打印总量
    msg += f"================\n总量：{total_star_jade} 星琼"

    if total_star_jade > 500000:
        msg += f"(注:当前配置下,50w中奖概率{probabilities[0]})"

    await roll.finish(msg, at_sender=True)
