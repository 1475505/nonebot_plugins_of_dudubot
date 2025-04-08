from nonebot import get_plugin_config, on_command
from nonebot.plugin import PluginMetadata
import os
import glob
import random
import difflib
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11 import Message

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="joke",
    description="鸡煲笑话插件",
    usage="发送【鸡煲笑话】获取随机笑话",
    config=Config,
)

config = get_plugin_config(Config)

# 定义命令：鸡煲笑话
joke_cmd = on_command("鸡煲笑话", block=True, priority=5)

@joke_cmd.handle()
async def handle_joke():
    # 笑话文件目录
    jokes_dir = os.path.expanduser("/root/nb/resources/jokes/jibao")
    # 获取所有txt文件
    file_paths = glob.glob(os.path.join(jokes_dir, "*.txt"))
    lines = []
    for fp in file_paths:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                # 读取所有非空行
                file_lines = [line.strip() for line in f if line.strip()]
                lines.extend(file_lines)
        except Exception as e:
            print(f"读取文件 {fp} 出错: {e}")
    if lines:
        joke = random.choice(lines)
        # 将文本中出现的 "\n" 转换为实际换行符
        joke = joke.replace("\\n", "\n")
        await joke_cmd.finish(joke)
    else:
        await joke_cmd.finish("当前没有笑话可供显示哦！")

# 定义命令：赛诺笑话
cyno_joke_cmd = on_command("赛诺笑话", block=True, priority=5)

@cyno_joke_cmd.handle()
async def handle_cyno_joke():
    # 赛诺笑话文件目录
    jokes_dir = os.path.expanduser("/root/nb/resources/jokes/cyno")
    # 获取所有txt文件
    file_paths = glob.glob(os.path.join(jokes_dir, "*.txt"))
    lines = []
    for fp in file_paths:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                # 读取所有非空行
                file_lines = [line.strip() for line in f if line.strip()]
                lines.extend(file_lines)
        except Exception as e:
            print(f"读取文件 {fp} 出错: {e}")
    if lines:
        joke = random.choice(lines)
        # 将文本中出现的 "\n" 转换为实际换行符
        joke = joke.replace("\\n", "\n")
        await cyno_joke_cmd.finish(joke)
    else:
        await cyno_joke_cmd.finish("当前没有笑话可供显示哦！")

# 定义命令：newjoke
new_joke_cmd = on_command("newjoke", aliases={"/newjoke"}, block=True, priority=5)

@new_joke_cmd.handle()
async def handle_new_joke(msg: Message = CommandArg()):
    # 解析参数，格式: {type} {content}
    args = msg.extract_plain_text().strip().split(maxsplit=1)
    if len(args) < 2:
        await new_joke_cmd.finish("格式错误，正确格式：/newjoke {类型} {笑话内容}")
    
    joke_type_input, joke_content = args
    # 将别名映射为实际代码
    mapping = {
        "jibao": "jibao",
        "鸡煲": "jibao",
        "cyno": "cyno",
        "赛诺": "cyno"
    }
    if joke_type_input not in mapping:
        await new_joke_cmd.finish("未知的笑话类型，请使用 '鸡煲' 或 '赛诺'")
    
    code = mapping[joke_type_input]
    # 将笑话内容中的实际换行符替换为 "\n" 字符串
    new_joke = joke_content.replace("\n", "\\n").strip()
    
    # 指定目标文件路径
    file_path = os.path.join(os.path.expanduser(f"/root/nb/resources/jokes/{code}"), "3.txt")
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # 若目标文件存在，检查是否已有相似笑话（相似度>=0.9）
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            existing_jokes = [line.strip() for line in f if line.strip()]
        for joke in existing_jokes:
            similarity = difflib.SequenceMatcher(None, new_joke, joke).ratio()
            if similarity >= 0.9:
                await new_joke_cmd.finish("已有相似笑话，提交失败！")
    
    # 追加新笑话到目标文件中，一行一笑话
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(new_joke + "\n")
    
    await new_joke_cmd.finish("笑话添加成功！")

