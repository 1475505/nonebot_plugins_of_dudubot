import traceback

import nonebot
from nonebot.adapters import Bot, Event
from nonebot.exception import AdapterException
from nonebot.log import logger
from nonebot.matcher import Matcher
from nonebot.plugin import PluginMetadata
from nonebot import on_command
from plugins.common import autoWrapMessage, extract_text
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

DEEPSEEK_MODEL = plugin_config.default_online_model
OFFLINE_MODEL = plugin_config.default_offline_model

conclude = on_command("概括", priority=13, block=True)

async def callModel(model: str, content: str, temperature: float = 1.0, top_p: float =1.0):
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        extra_body={
            "enable_search": True, # hy-dsr开启联网搜索
            "thinking": {
                "type": "enabled"
            }
        },
        temperature = temperature,
        top_p=top_p
    )
    return response.choices[0].message

async def callModelChat(model: str, content: str, temperature: float = 1.0, top_p: float =1.0):
    response = await client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": content}],
        extra_body={
            "enable_search": True # hy-dsr开启联网搜索
        },
        temperature = temperature,
        top_p=top_p
    )
    return response.choices[0].message


@conclude.handle()
async def handle_reply(event: GroupMessageEvent):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = replied_content or content or "嘟嘟可是好人"
    # 对内容进行总结
    prompt = """你是一位专业的教授. 请使用1-2句话简单概括接下来的文本讲述的内容、论证逻辑和观点。如果文本中存在难以理解的内容/网络流行梗,使用通俗化的语言讲述.然后，以客观的角度分析，提供看法。输出格式：
    [总结]...
    [AI看法]...
    [罐装知识]...
    （严格按照此格式，不要输出其他内容）
    你需要处理的文本是：
    """ + input_content
    response = await callModel(OFFLINE_MODEL, prompt)
    await conclude.finish(response.content, at_sender=True)

from nonebot.params import CommandArg

webexplain = on_command("说明", aliases = {"搜索"}, priority=14, block=True)
@webexplain.handle()
async def handle_reply_webexplain(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = replied_content or msg.extract_plain_text().strip() or "嘟嘟可"
    prompt = input_content + "是什么? 根据网络搜索结果, 简单回答"
    response = await callModel(DEEPSEEK_MODEL, prompt)
    await webexplain.finish(response.content, at_sender=True)


zdict = on_command("扫盲", aliases={"何意味"}, priority=13, block=True)
@zdict.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = replied_content or msg.extract_plain_text().strip() or "嘟嘟可"
    # 获取用户提供的领域参数
    field = content.strip()
    prompt2 = f"""
    接下来请以如下的输出格式回答问题：
        [词扫盲]...
        [句扫盲]...(可附带一些简单的真实史实/网络梗/冷知识)
        （严格按照此格式简洁严谨输出）
    """

    prompt1 = f"""Q: "{input_content}"是什么意思? 给出拼音/音标和解释"""
    if len(input_content) > 4:
        prompt1 =  f"""Q:"{input_content}"里有1-2个字/词/网络梗难以理解，请解释难理解的部分,并给出拼音/音标."""
    
    prompt3 = f"""
        \n (重点关注领域/文本:{field})
    """
    prompt = prompt2 + prompt1
    if field:
        prompt = prompt + prompt3
    #response = await callModel("Pro/moonshotai/Kimi-K2-Instruct", prompt, 0.2, 0.7)
    response = await callModel(DEEPSEEK_MODEL, prompt, 0.2, 0.7)
    #response = await callModel("Pro/deepseek-ai/DeepSeek-R1", prompt)
    await zdict.finish(response.content.strip())

quest = on_command("质疑", priority=13, block=True)
@quest.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = replied_content or msg.extract_plain_text().strip() or "嘟嘟可很会写Java"
    # 对内容进行总结
    prompt = """你现在是一位高考状元/开源贡献者/字节范儿大使/C++高手/北大小男娘/梗指南大师.
    任务: 接下来给你一段文本，文本的内容、论证逻辑和观点可能存在错误。请以批判的角度进行判断，进行深入的分析，给出观点的合理之处和错误/不完善之处，对不符合事实的情况,提出1-2条适当的质疑. 然后，简洁、通俗地普及相关知识。输出格式：
    [判断]...
    [罐装知识]...
    （严格按照此格式. 输出请保持简洁的风格,符合输出格式）
    你需要处理的文本是：
    """ + input_content
    response = await callModel(OFFLINE_MODEL, prompt)
    await quest.finish(response.content, at_sender=True)
    
    

commonai = on_command("安慰", aliases={"加emoji", "人话", "讲故事", "赞同", "附议", "夸夸", "锐评", "回答", "翻译", "攻击", "译中", "思考", "反思", "断句"}, priority=13, block=True)
@commonai.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = (replied_content) or msg.extract_plain_text().strip() or "A股又跌了"
    command = event.get_plaintext().strip().split()[0][1:]
    # 对内容进行总结
    prompt = f"""
        Alice: {input_content}
        Bob: 请对Alice的话进行{command}, 需要具有同理心. 日常对话,不要长篇大论
        You（一位喜欢二次元的字节范儿程序员）：
    """
    
    response = await callModel(OFFLINE_MODEL, prompt)
    await zdict.finish("\n" + response.content, at_sender=True)

import random
mc = on_command("鸣式", priority=13, block=True)
@mc.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = replied_content or msg.extract_plain_text().strip() or "耐心等待A股上涨"
    # 对内容进行总结
    prompt1 = f"""请将文本{input_content}改写成下面的格式, 基于文本, 允许少量自由发挥，可增加适量的讽刺色彩（A和B为名词，C为一种动作，意为A只有在主体为B的条件下才能做动作C. 严格按照此格式，不要输出其他内容）:
    请谅解
    A
    只有 B
    可以 C

    示例：
    请谅解
    今天
    只有 中国人
    可以 玩原神
    """
    prompt2 = f"""请将文本{input_content}改写成下面的格式, 基于文本, 允许少量自由发挥（A/B 改写为相关 4 个字以内的对立概念, C改为相关的短句. 严格按照此格式，不要输出其他内容）:
    A是这样的。B只需要负责C就可以了，而A要考虑的事情就多了.

    示例：后方是这样的。前线的将士只要全身心投入到战场中，听命行事，奋力杀敌就可以，可是后方人员要考虑的事情就很多了。
    """
    prompt3 = f"""请将文本{input_content}改写成下面的格式, 基于文本, 允许少量自由发挥，可增加适量的讽刺色彩（A和B为名词，C为一种动作，意为A只有在主体为B的条件下才能做动作C. D可以为一个第三方旁观者名词. 严格按照此格式，不要输出其他内容）:
    请谅解
    A
    只有 B
    可以 C
    D 要考虑的事情就多了.
    """
    prompt4 = f"""
    请以文本{input_content}为主题改写成下面的格式, 基于文本, 允许少量自由发挥（这是一个双人对话的情景，A和B都为说话人1所说的完整的句子 ，A句子用一句让人期待的话激起另一个人的好奇与期待的情绪，在说话人2发起"难道说？"的反问后，说话人1说出一个常识或者严重不符合期待的事情，让说话人2大失所望。严格按照此格式，不要输出其他内容）:
    说话人1：A
    说话人2：难道说？
    说话人1：B
    """
    prompts = [prompt1, prompt2, prompt3, prompt4]
    prompt = random.choice(prompts)

    #response = await callModel("Pro/deepseek-ai/DeepSeek-R1", prompt)
    response = await callModel(OFFLINE_MODEL, prompt)
    await mc.finish("\n"+response.content, at_sender=True)


szg = on_command("丝之歌", aliases={"丝之歌体", "丝之歌式", "刘辉洲", "刘辉州", "古文小生", "szg式", "lhz式"}, priority=13, block=True)
@szg.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = (replied_content + msg.extract_plain_text().strip()) or "上班压力很大"
    #if replied_message.reply:
    #    replied_content = replied_message.reply.message.extract_plain_text(a
    p = random.random()
    prompt = f"""
    你现在是一名文盲“古风小生翻译”。请你强行乱用非口语词组与拟古词，把正常的白话中文译文增加一些矫揉造作、故弄玄虚的古语词,使其被改写成读之莫名其妙的话。不要遵守文言与诗歌语法，可以错置词性与语序,增加莫名其妙的谜语人语调等.请注意让人读起来不知所云，莫名其妙。输出对应的的玄虚版译文（字数请和原文大体一致）.

三种风格范式示例：（仅作感触，勿照搬句式）：
1. 
正常译文：钟响七下后，烦请送出：30小节又4拍的「烟岩」，8拍的「甜熔渣」。
玄虚译文：七钟响时运送：三十节又四奏烟岩，及八奏甜熔渣。
2. 
正常译文：我是路过周游的人。来者可是空洞骑士？
玄虚译文：我力衰之躯只不过是一介旅行者.啊哈哈!可是洞之空骑士？
3. 
正常译文：猪被捕了。
玄虚译文：豕遭擒获。
-----
现在开始(输出仅输出译文,不输出任何提示词和说明)：
正常译文：{input_content} 
玄虚译文：
    """
    prompt1 = f"""你现在是一名文盲古风小生诗人,文风矫揉造作,故弄玄虚. 请注意你是文盲,需要强行乱用非口语的语言（如"被囚禁多天""气力衰微"）和拟古词汇（如"奏"）将一句简单的话强行表达成很有逼格但人类不可理解的诗。请一定要让人读起来莫名其妙，不遵守文言文语法.
    诗文示例:
    1. 
  """

    prompt2 = f"""
    任务: 接下来，请对下面的输入文本改写成半文半白的短诗，只输出对应改写后让人读起来莫名其妙，不遵守文言文和诗歌语法的诗文. 不要输出其他内容,不要输出其他内容。
    示例:
    输入文本:
    没有为苦难哭泣的声音,生于神于虚空之手,你必封印在众人梦中,散布瘟疫的障目之光,你是容器,你是空洞骑士
    输出诗文:
    没含悲衔怨之哀音对于苦难
    于深渊虚空的神的手
    你一定会在魔法梦的深狱
    永远看见到处的妄光瘟疫
    尔是器血
    你是洞之空骑士
    

    输入文本：{input_content}
    输出诗文:
    """

    prompt = prompt

    #response = await callModel("Pro/moonshotai/Kimi-K2-Instruct-0905", prompt)
    response = await callModel(OFFLINE_MODEL, prompt)
    await szg.finish(response.content.strip(), at_sender=False)


htx = on_command("何式", priority=13, block=True)
@htx.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = (replied_content + msg.extract_plain_text().strip()) or "抽卡歪了"
    #if replied_message.reply:
    #    replied_content = replied_message.reply.message.extract_plain_text(a
    p = random.random()
    prompt1 = f"""任务：接下来，我将给你一段基准文本，然后，你需要将输入的文本改写成基准文本类似的语言和文本格式, 需要保证段落结构的一致性和有趣性。请严格进行改写。
    基准文本：以前打网约车，司机师傅跟我说打个好评，我都会说好好好，但是下车后也没想起来打。其实这样挺不好的。现在司机师傅跟我说打个好评，除非服务真的很好到我想打好评的程度，否则我就会直接说，抱歉我不想打，然后下车。作为一个有讨好倾向的人，这是我锻炼真诚和勇气的方式。

    示例：
    输入文本：我看B站视频不喜欢一键三连。
    输出文本：以前看何同学的视频，他总说记得一键三连，我都会说好好好，但退出后也没想起来按。其实这样挺不礼貌的。 现在何同学再提一键三连，除非视频真的有趣到让我想掏硬币，否则我就直接说：「抱歉，您的视频暂时无法三连」，然后退出全屏。作为一个有原则的观众，这是我锻炼自我和解与节能环保的方式。

    接下来，请对下面的输入文本进行改写，只输出对应改写后的输出文本，不要输出其他内容,不要输出其他内容,不要输出其他内容。
    输入文本：{input_content}
    """
    prompt2 = f"""任务：接下来，我将给你一段基准文本，然后，你需要将输入的文本改写成基准文本类似的语言和文本格式, 需要保证段落结构的一致性和通顺性，最好附带一些幽默元素。请严格进行改写。
    基准文本：不觉得这AI很酷吗? 作为一名理工男我觉得这AI太酷了，很符合我对未来生活的想象，科技并带着趣味。

    示例：
    输入文本：二次元游戏真好玩
    输出文本：不觉得原神很好玩吗? 作为一位宅男我觉得这提瓦特世界太美好了，很符合我对未来生活的想象，快乐并带着惊喜。

    接下来，请对下面的输入文本进行改写，只输出对应改写后的输出文本，不要输出其他内容,不要输出其他内容,不要输出其他内容。
    输入文本：{input_content}
    """
    prompt = prompt1
    if p > 0.7:
        prompt = prompt2
    #response = await callModel("Pro/deepseek-ai/DeepSeek-R1", prompt)
    response = await callModel(DEEPSEEK_MODEL, prompt)
    await htx.finish("\n"+response.content, at_sender=True)


syntax = on_command("公式", aliases={"模仿", "鹦鹉", "复读", "咔库库"}, priority=13, block=True)
@syntax.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    # 获取用户提供的额外参数作为格式模板
    user_content = msg.extract_plain_text()
    prompt1 = f"""任务：接下来，我将给你一段输入文本，然后，你需要改写成基准文本类似的语言和文本格式, 需要保证段落结构的一致性和通顺性, 语义需要有一定的幽默感。
    请严格进行改写.

    示例：
    基准文本（用户输入）：以前打网约车，司机师傅跟我说打个好评，我都会说好好好，但是下车后也没想起来打. 其实这样挺不好的.
    输入文本（用户输入）：我看B站视频不喜欢一键三连。
    输出文本（你的任务）：以前看何同学的视频，他总说记得一键三连，我都会说好好好，但退出后也没想起来按。其实这样挺不礼貌的。

    现在开始.

    请输出对应改写后的输出文本，不要输出其他内容，不要输出其他内容。
    基准文本：{replied_content}
    输入文本:{user_content}
    输出文本:
    """

    prompt = prompt1

    #response = await callModel("Pro/moonshotai/Kimi-K2-Instruct-0905", prompt)
    response = await callModel(DEEPSEEK_MODEL, prompt)
    await syntax.finish("\n"+response.content, at_sender=True)



from . import xf_ocr
ocr = on_command("ocr", priority=13, block=True)
@ocr.handle()
async def _(bot: Bot, event: GroupMessageEvent, msg: Message = CommandArg()):
      # 检查是否包含回复信息
    if event.reply:
        # 获取被引用消息的内容
        replied_message = event.reply.message
        for seg in replied_message:
            if seg.type == "image":
                img_url = seg.data["url"]
                txt = xf_ocr.ocr(img_url)
                if len(txt) < 30:
                    await ocr.finish(txt)
                else:
                    # 将长文本分段
                    segments = [txt[i:i+1000] for i in range(0, len(txt), 1000)]
                    messages = []
                    
                    # 创建转发消息节点
                    for index, segment in enumerate(segments, 1):
                        messages.append({
                            "type": "node",
                            "data": {
                                "name": "OCR结果",
                                "uin": event.self_id,
                                "content": f"第{index}部分：\n{segment}"
                            }
                        })
                    
                    # 发送合并转发消息
                    await bot.call_api(
                        "send_group_forward_msg",
                        group_id=event.group_id,
                        messages=messages
                    )



'''
Mods by User670
'''
user670_summary_dictionary = on_command("词典", priority=255, block=True)
@user670_summary_dictionary.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = (replied_content + msg.extract_plain_text().strip()) or "嘟嘟可"
    # 对内容进行总结
    prompt = """用户对一个或多个单字、词语或短语不理解，需要类似词典的解释。对用户给出的每个关键字、词或词组，按照如下的格式提供解释。如果用户提供的内容过长，例如包含整个句子或段落，则提取最多3个最可能需要解释的字、词或词组进行解释。请用纯文本输出，不要使用markdown语法。

格式：
<词条>
[读音]...
[词源]...
[释义]...

对于读音，如果词条语言为中文，则给出汉语拼音。如果词条语言是日文，则给出黑本式罗马字。如果词条语言是拉丁字母拼写的其他语言，则给出IPA。如果词条语言是其他书写系统拼写的其他语言，则给出IPA和拉丁化转写。
对于词源(etymology)，请给出该词条的公认的词源，例如词根词缀，构词法，相应的典故（对于俗语和成语）等。如果没有可靠的词源信息，则跳过该部分。
对于释义，请按照类似词典的格式列举该词条的释义。

用户提供的文本是：
""" + input_content
    response = await callModel("Pro/deepseek-ai/DeepSeek-V3", prompt)
    await user670_summary_dictionary.finish("\n" + response.content, at_sender=True)


user670_summary_encyclopedia = on_command("百科", priority=255, block=True)
@user670_summary_encyclopedia.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = (replied_content + msg.extract_plain_text().strip()) or "嘟嘟可"
    # 对内容进行总结
    prompt = """用户对一个或多个概念希望获取类似百科全书的解释。对用户给出的每个关键概念给出解释。如果用户提供的内容过长，例如包含整个句子或段落，则提取最多3个最可能需要解释的概念进行解释。解释应言简意赅，对关键点进行概括，格式应类似维基百科词条的首段，不要超过200字。请用纯文本输出，不要使用markdown语法。

格式：
<词条>
<解释>

用户提供的文本是：
""" + input_content
    response = await callModel("Pro/deepseek-ai/DeepSeek-V3", prompt)
    await user670_summary_encyclopedia.finish("\n" + response.content, at_sender=True)


user670_summary_meme = on_command("网络梗", priority=255, block=True)
@user670_summary_meme.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = (replied_content + msg.extract_plain_text().strip()) or "嘟嘟可"
    # 对内容进行总结
    prompt = """用户对一个或多个网络迷因、次文化梗等不理解。在用户提供的消息中，提取不超过3个最需要解释的迷因，并对每个迷因按照如下格式解释。请用纯文本输出，不要使用markdown语法。

格式：
<词条>
[词源]...
[解释]...

用户提供的文本是：
""" + input_content
    response = await callModel("Pro/deepseek-ai/DeepSeek-V3", prompt)
    await user670_summary_meme.finish("\n" + response.content, at_sender=True)


user670_summary_parse = on_command("解析", priority=255, block=True)
@user670_summary_parse.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = (replied_content + msg.extract_plain_text().strip()) or "嘟嘟可"
    # 对内容进行总结
    prompt = """用户对网络群聊中的一条消息不理解。请对提供的消息进行解析并改写为清晰易懂的语言。原文中可能包含网络迷因/次文化梗、缩写/简写/代指、谐音替换/双关语、专业术语等。请用纯文本输出，不要使用markdown语法。

格式：
您提供的消息改写结果如下：
<改写后的文本>

用户提供的文本是：
""" + input_content
    response = await callModel("Pro/deepseek-ai/DeepSeek-V3", prompt)
    await user670_summary_parse.finish("\n" + response.content, at_sender=True)

'''
End of mods by User670
'''


# 宫崎英高小故事功能
miyazaki_story = on_command("宫崎英高小故事", aliases={"宫崎英高", "魂游"},  priority=13, block=True)
@miyazaki_story.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = (replied_content + msg.extract_plain_text().strip()) or "假篝火"
    
    # 生成宫崎英高风格的小故事
    prompt = f"""
    玩家在魂系游戏中常遇到“设计者的恶意",会用设计者(比如宫崎英高)小时候的短篇故事进行调侃，用日常场景隐喻魂系游戏的机制（如假篝火、高难度boss、宝箱怪、单向门等），风格荒诞黑暗，结尾留悬念，不超过200字。
    例子:
    1. 宫崎英高小时候写作业，写着写着睡着了，被尿憋醒后发现作业刷新了。顾不了那么多转身去了厕所，结果发现厕所门不能从这一侧打开，没有办法他只能翻窗户，结果翻窗户的时候被旁边的树枝扫到了地上的洞里。
    2. 樱桃小时候去上学被流浪狗咬了一口，一怒之下和狗子打架结果被打成残血了。跑的时候不小心掉污水沟里，被虫且爬了一身，必须要满能量才能踢开。到学校后必须要跑一遍苦痛之路才能坐上座位，还被告知要考试，一看卷子还要花钱买，一摸裤兜，钱在跑路的时候掉光了，只好拿祖传的项链抵钱买了份试卷。

    接下来请基于{input_content}生成小故事,直接输出故事,不要输出其他内容
    """
    
    response = await callModel(DEEPSEEK_MODEL, prompt)
    await miyazaki_story.finish("\n" + response.content, at_sender=True)


# 股民视角功能
stock_perspective = on_command("利好", priority=13, block=True)
@stock_perspective.handle()
async def _(event: GroupMessageEvent, msg: Message = CommandArg()):
    # 使用extract_text函数提取内容
    (content, replied_content) = await extract_text(event)
    input_content = (replied_content + msg.extract_plain_text().strip()) or "纳西妲真可爱"
    
    # 从股民角度分析内容
    prompt = f"""你现在是一位李大霄的粉丝, A股股民. 接下来请将和股市不相关的新闻/话题中,咬文嚼字，强行说是对某个板块/股票的暗示和利好,输出“李大霄暗示解读”。输出语言风格:简洁 专业 沉稳,一本正经地分析暗示(胡说八道).

示例：
输入:家里的Wi-Fi路由器突然断网，重启之后，网速变流畅了一点.
输出：家里暗示房地产板块, 路由器暗示科技板块, 断网暗示科技板块经历短期调整后，将迎来更强劲的复苏。主力部队将带着新一轮行情，中国股市将步入高速牛。优质科技股，如恒生科技，宜长期持有。做好人买好股得好报。

现在开始:
输入:{input_content}
输出:
"""
    
    response = await callModel(OFFLINE_MODEL, prompt)
    await stock_perspective.finish("[不构成投资建议]  " + response.content, at_sender=False)
