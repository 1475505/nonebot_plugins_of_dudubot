import traceback

import nonebot
from nonebot.adapters import Bot, Event
from nonebot.exception import AdapterException
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot import on_command


from nonebot_plugin_alconna import Alconna, Args, on_alconna

from .config import Config
from nonebot.adapters import MessageSegment
from nonebot.adapters.onebot.v11 import GroupMessageEvent,Message

__plugin_meta__ = PluginMetadata(
    name="对引用的信息进行总结",
    description="11",
    usage="122",
    config=Config,

)

from openai import AsyncOpenAI

plugin_config = Config.parse_obj(nonebot.get_driver().config.dict())

client = AsyncOpenAI(
    api_key=plugin_config.chat_oneapi_key, base_url=plugin_config.chat_oneapi_url
)

conclude = on_command("概括", priority=13, block=True)

async def callModel(model: str, content: str):
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
    )
    return response.choices[0].message

@conclude.handle()
async def handle_reply(event: GroupMessageEvent):
    # 检查是否包含回复信息
    if event.reply:
        # 获取被引用消息的内容
        replied_message = event.reply.message
        replied_content = replied_message.extract_plain_text()  # 提取纯文本内容
        #if replied_message.reply:
        #    replied_content = replied_message.reply.message.extract_plain_text()
        # 对内容进行总结
        prompt = """你现在是一位专业的教授. 请使用1-2句话简单概括接下来的文本讲述的内容、论证逻辑和观点。如果文本中存在难以理解的内容/网络流行梗,使用通俗化的语言讲述.然后，以客观的角度分析，提供看法。输出格式：
        [总结]...
        [AI看法]...
        [相关知识]...
        （严格按照此格式，不要输出其他内容）
        你需要处理的文本是：
        """ + replied_content
        response = await callModel("Pro/deepseek-ai/DeepSeek-R1", prompt)
        await conclude.finish(response.content, at_sender=True)

from nonebot.params import CommandArg
zdict = on_command("扫盲", priority=13, block=True)
@zdict.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 检查是否包含回复信息
    replied_content = "嘟嘟可"
    if event.reply:
        # 获取被引用消息的内容
        replied_message = event.reply.message
        replied_content = replied_message.extract_plain_text()  # 提取纯文本内容
    else:
        replied_content = msg.extract_plain_text()
    # 对内容进行总结
    prompt = """你现在是一位喜欢二次元的程序员，面向高三竞赛生,讲解接下来基于的文字/词语/短句/网络流行词中,对应的读音(拼音/该语言对应的音标),中文含义和历史渊源,即词典功能.输出最好能激发学习兴趣,格式：
        [词典]...
        [相关故事]...
        （严格按照此格式，不要输出其他内容）
        你需要处理的文本是：
    """ + replied_content
    response = await callModel("Pro/deepseek-ai/DeepSeek-V3", prompt)
    await zdict.finish("\n" + response.content, at_sender=True)

quest = on_command("质疑", priority=13, block=True)
@quest.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
      # 检查是否包含回复信息
    if event.reply:
        # 获取被引用消息的内容
        replied_message = event.reply.message
        replied_content = replied_message.extract_plain_text()  # 提取纯文本内容
        #if replied_message.reply:
        #    replied_content = replied_message.reply.message.extract_plain_text()
        # 对内容进行总结
        prompt = """你现在是一位高考状元/开源贡献者/C++高手/北大小男娘/梗指南大师. 接下来我将给出一段文本，文本的内容、论证逻辑和观点可能存在错误。请以批判性质疑的角度，对其进行深入的分析，给出文本中观点的合理之处、错误之处，提出适当的质疑，并通俗地补充相关知识。输出格式：
        [判断]...
        [质疑]...
        [相关知识]...
        （严格按照此格式，不要输出其他内容）
        你需要处理的文本是：
        """ + replied_content
        response = await callModel("Pro/deepseek-ai/DeepSeek-R1", prompt)
        await quest.finish(response.content, at_sender=True)
    
    

commonai = on_command("安慰", aliases={"夸夸"}, priority=13, block=True)
@commonai.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 检查是否包含回复信息
    replied_content = "嘟嘟可"
    if event.reply:
        # 获取被引用消息的内容
        replied_message = event.reply.message
        replied_content = replied_message.extract_plain_text()  # 提取纯文本内容
    else:
        replied_content = msg.extract_plain_text()
    command = event.get_plaintext().strip().split()[0][1:]
    # 对内容进行总结
    prompt = f"""你现在是一位喜欢二次元的程序员. 接下来我将给出一段文本, 请对该文本进行简单的{command}, 需要具有同理心. 输出格式：
        [{command}]...
        [相关建议]...
        （严格按照此格式，不要输出其他内容）
        你需要处理的文本是：
    """ + replied_content
    response = await callModel("Pro/deepseek-ai/DeepSeek-V3", prompt)
    await zdict.finish("\n" + response.content, at_sender=True)

import random

mc = on_command("鸣式", priority=13, block=True)
@mc.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
      # 检查是否包含回复信息
    if event.reply:
        # 获取被引用消息的内容
        replied_message = event.reply.message
        replied_content = replied_message.extract_plain_text()  # 提取纯文本内容
        #if replied_message.reply:
        #    replied_content = replied_message.reply.message.extract_plain_text(a
        # 对内容进行总结
        p = random.random()
        prompt1 = f"""请将文本{replied_content}改写成下面的格式, 基于文本, 允许少量自由发挥，可增加适量的讽刺色彩（A和B为名词，C为一种动作，意为A只有在主体为B的条件下才能做动作C. 严格按照此格式，不要输出其他内容）:
        请谅解
        A
        只有 B
        可以 C
        """ 
        prompt2 = f"""请将文本{replied_content}改写成下面的格式, 基于文本, 允许少量自由发挥（A/B 改写为相关 4 个字以内的对立概念, **改为相关的短句. 严格按照此格式，不要输出其他内容）:
        A是这样的。B只需要负责**就可以了，而A要考虑的事情就多了.
        """
        prompt = prompt1
        if p > 0.8:
            prompt = prompt2
        #response = await callModel("Pro/deepseek-ai/DeepSeek-R1", prompt)
        response = await callModel("Pro/deepseek-ai/DeepSeek-V3", prompt)
        await mc.finish("\n"+response.content, at_sender=True)
