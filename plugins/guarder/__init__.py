import os
import json
import re
import time
import nonebot
from datetime import datetime
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.log import logger
from typing import Set, Dict, Any

from plugins.common import TencentTextModerator, callSfVLM, callLLM
from .config import Config

# 配置检查
config = Config.parse_obj(nonebot.get_driver().config.dict())

MODERATION_MODEL=config.or_free_model2
#MODERATION_MODEL="google/gemma-3-27b-it:free"
#TRANSLATION_MODEL="z-ai/glm-4.5-air:free"
TRANSLATION_MODEL="x-ai/grok-code-fast-1"

# 审查守卫监听的QQ号列表
MODERATION_QQ: Set[str] = {str(qq) for qq in config.moderation_qq}

# 翻译守卫监听的QQ号列表
TRANSLATION_QQ: Set[str] = {str(qq) for qq in config.translation_qq}

# 群聊黑白名单
GROUP_WHITELIST: Set[str] = {str(group_id) for group_id in config.group_whitelist}
GROUP_BLACKLIST: Set[str] = {str(group_id) for group_id in config.group_blacklist}

# 初始化腾讯云审查器
moderator = TencentTextModerator(
    region=config.tencent_region
)

# 审查缓存，避免频繁重复审查
moderation_cache: Dict[str, float] = {}

def should_moderate_group(group_id: str) -> bool:
    """
    判断群聊是否需要审查

    规则：
    1. 如果群在白名单中，不进行审查（白名单优先级最高）
    2. 如果黑名单为空（默认状态），所有群都需要审查
    3. 如果群在黑名单中，必须审查
    """
    group_id_str = str(group_id)

    # 白名单优先级最高：如果在白名单中，不审查
    if group_id_str in GROUP_WHITELIST:
        return False

    # 如果黑名单为空（默认状态），所有群都需要审查
    if not GROUP_BLACKLIST:
        return True

    # 如果群在黑名单中，必须审查
    if group_id_str in GROUP_BLACKLIST:
        return True

    # 其他情况（不在黑白名单中，且黑名单不为空），不审查
    return False

# 审查守卫监听器，block=False
moderation_guarder = on_message(priority=1000, block=False)

# 翻译守卫监听器，block=False
translation_guarder = on_message(priority=1000, block=False)

@moderation_guarder.handle()
async def handle_moderation(bot: Bot, event: MessageEvent):
    """处理消息审查"""
    user_id = event.user_id
    group_id = getattr(event, 'group_id', None)

    # 只监听特定QQ号
    if str(user_id) not in MODERATION_QQ:
        return

    # 检查群聊是否需要审查（如果是群聊消息）
    if group_id and not should_moderate_group(group_id):
        logger.debug(f"群聊 {group_id} 在白名单中或不在黑名单中，跳过审查")
        return

    message_text = event.get_plaintext().strip()
    if not message_text:
        return

    replySz = 50
    blackTexts = ['jb', '🦌', '龟头', '撸', '鸡巴']
    if any(blackText in message_text for blackText in blackTexts):
        replySz = 20
        response = await check_and_respond(replySz, True)
        await moderation_guarder.send(response, at_sender=True)
        return

    # 检查缓存，45min内不再重复审查
    current_time = time.time()
    cache_key = f"{user_id}"
    if cache_key in moderation_cache:
        last_moderation_time = moderation_cache[cache_key]
        if current_time - last_moderation_time < 2700:  # 0.75小时 = 1800秒
            logger.debug(f"用户 {user_id} 在45min内已触发过审查，跳过本次审查")
            return

    try:
        logger.info(f"开始对用户 {user_id} 的消息进行审查: {message_text[:50]}...")

        # 原腾讯云文本审查机制（已注释）
        # is_pass, result = await moderator.check_text(message_text)
        # if not is_pass:
        #     logger.warning(f"用户 {user_id} 消息未通过审查: {result}")
        #     moderation_cache[cache_key] = current_time
        #     response = await generate_moderation_response(replySz)
        #     await moderation_guarder.send(response, at_sender=True)
        # else:
        #     logger.info(f"用户 {user_id} 的消息通过审查")

        # 使用大模型进行文本审查并生成回复
        response = await check_and_respond(message_text)
        if response:
            logger.warning(f"用户 {user_id} 消息被判定为不适合日常聊天展示")
            # 记录审查缓存，半小时内不再审查
            moderation_cache[cache_key] = current_time
            await moderation_guarder.send(response, at_sender=True)
        else:
            logger.info(f"用户 {user_id} 的消息通过审查")

    except Exception as e:
        logger.error(f"消息审查处理出错: {e}")

@translation_guarder.handle()
async def handle_translation(bot: Bot, event: MessageEvent):
    """处理语言检测和翻译"""
    user_id = event.user_id

    # 只监听特定QQ号
    if str(user_id) not in TRANSLATION_QQ:
        return

    message_text = event.get_plaintext().strip()
    if not message_text:
        return

    try:
        logger.info(f"开始对用户 {user_id} 的消息进行语言检测: {message_text[:50]}...")

        # 语言检测和翻译
        translation_result = await detect_and_translate(message_text)
        if translation_result:
            logger.info(f"检测到外语并完成翻译: {translation_result[:50]}...")
            await translation_guarder.send(translation_result)
        else:
            logger.debug(f"用户 {user_id} 的消息无需翻译")

    except Exception as e:
        logger.error(f"翻译处理出错: {e}")

def contains_japanese(text: str) -> bool:
    """检测文本是否包含日语字符"""
    # 日语字符范围：
    # \u3040-\u309F: 平假名
    # \u30A0-\u30FF: 片假名
    # \u4E00-\u9FAF: 汉字（共用，但在特定上下文中可能是日语）
    japanese_chars = re.findall(r'[\u3040-\u309F\u30A0-\u30FF]', text)
    return len(japanese_chars) > 0

def contains_korean(text: str) -> bool:
    """检测文本是否包含韩语字符"""
    # 韩语字符范围：
    # \uAC00-\uD7AF: 韩文音节
    # \u1100-\u11FF: 韩文字母
    korean_chars = re.findall(r'[\uAC00-\uD7AF\u1100-\u11FF]', text)
    return len(korean_chars) > 0

async def detect_and_translate(text: str) -> str:
    """检测语言并翻译（如果是日语或韩语则翻译成中文）"""
    try:
        logger.debug(f"开始语言检测，输入文本: {text[:100]}...")

        # 检测语言类型
        is_japanese = contains_japanese(text)
        is_korean = contains_korean(text)

        # 如果不包含日语或韩语字符，直接跳过LLM调用
        if not is_japanese and not is_korean:
            logger.info("未检测到日语或韩语字符，跳过翻译")
            return ""

        if "Ciallo～(∠・ω< )⌒" in text:
            return ""

        # 根据语言类型进行翻译
        if is_japanese:
            logger.debug("检测到日语字符，调用LLM进行翻译")
            language = "日语"
        elif is_korean:
            logger.debug("检测到韩语字符，调用LLM进行翻译")
            language = "韩语"
        else:
            return ""

        prompt = f"""请将以下{language}文本翻译成中文：

原文：{text}

请直接输出翻译结果，不要包含任何其他解释。"""

        logger.debug(f"调用LLM进行{language}翻译...")
        response = await callLLM(prompt, model=TRANSLATION_MODEL)
        logger.debug(f"LLM翻译响应: {response}")

        translation = response.strip()
        if translation:
            logger.info(f"{language}翻译完成: {translation[:50]}...")
            return f"自动翻译：{translation}"
        else:
            logger.debug("翻译结果为空")
            return ""

    except Exception as e:
        logger.error(f"翻译失败: {e}")

    return ""

async def check_and_respond(text: str, fast: bool = False) -> str:
    """使用大模型一次性完成文本审查和回复生成"""
    # 获取完整时间戳
    now = datetime.now()
    # 格式：年月日时分秒毫秒，例如 20251103204556789
    timestamp_str = f"{now.year:04d}{now.month:02d}{now.day:02d}{now.hour:02d}{now.minute:02d}{now.second:02d}{now.microsecond//1000:03d}"
    timestamp = int(timestamp_str)

    # 根据时间戳取模选择创作方向
    direction = timestamp % 3
    directions = [
        "寓意美好/赞美良辰美景的中国古代流行诗文，如唐诗、诗经、宋词等（示例：春江花月夜、滕王阁序，请选择其他类似诗句）",
        "近现代中外经典哲学名句，如鲁迅等（示例：每一个不曾起舞的日子...，请选择其他类似名句）",
        "流行电影/二次元游戏台词（示例：「花车颠呀颠，纳西妲睁开眼」--原神，请选择其他类似台词）"
    ]
    selected_direction = directions[direction]

    prompt1 = f"""{text}
----
任务：
"""
    prompt2 = f"""判断以上文本是否符合下面不适合在聊天中展示的情况：
1. 性暗示或色情低俗, 比如:今晚来一发
2. 人身攻击
3. 令人强烈不适的不良价值观

请先返回判断结果，如果文本非常不适合在聊天中展示，同时检索优美的句子回复。如果非常不适合在聊天中展示，返回时设置need_ban为true，并
"""
    prompt3 = f"""
请[充分结合]当前时间：{timestamp_str} 和上面的文本进行检索优美的句子，方向：{selected_direction}. 请直接输出JSON，无需解释。
注意：方向中的示例仅供参考，请根据当前时间和文本引用合适的句子，不要直接使用提到的示例。引用的句子应高于高中语文水平,与当前时间和文本相关,不要过于简单.
    """
    prompt4 = f"""
请严格按照以下JSON格式返回：
{{
  "need_ban": true/false,  // 是否很不适合日常聊天展示
  "inappropriate_reasons": ["1", "3"],  // 不适合的情况（仅当need_ban为true时）
  "poetry_content": "经典句子 —— 作者/出处\n(English translation)"  // 根据当前时间和上面的文本引用的美好句子内容（仅当need_ban为true时）
}}
    """
    prompt5 = f"""
请严格按照以下JSON格式返回：
{{
  "need_ban": true, 
  "inappropriate_reasons": ["2"],
  "poetry_content": "经典句子 —— 作者/出处\n(English translation)"  // 根据当前时间和上面的文本引用的美好句子内容（need_ban为true）
}}

"""

    prompt = prompt1 + prompt2 + prompt3 + prompt4
    if fast:
        prompt = prompt1 + prompt3 + prompt5
    try:
        # 使用callLLM函数调用LLM，启用JSON输出
        response = await callLLM(prompt, model=MODERATION_MODEL, json_output=True)
        response = response.strip()

        # 解析JSON响应
        try:
            result = json.loads(response)
            if fast or (result.get("need_ban", True) and result.get("poetry_content")):
                logger.info(f"文本不适合展示，原因: {result.get('inappropriate_reasons', [])}, 类别: {selected_direction}")
                return "\n" + result["poetry_content"]
            else:
                logger.debug("文本适合日常聊天展示")
                return ""
        except json.JSONDecodeError:
            logger.error(f"LLM返回的JSON格式错误: {response}")
            return ""
    except Exception as e:
        logger.error(f"LLM调用失败: {e}")
        return ""

def get_moderation_qq() -> Set[str]:
    """获取审查守卫监听QQ号列表"""
    return MODERATION_QQ.copy()

def add_moderation_qq(qq_number: str) -> bool:
    """添加审查守卫监听QQ号"""
    if qq_number in MODERATION_QQ:
        return False
    MODERATION_QQ.add(qq_number)
    return True

def remove_moderation_qq(qq_number: str) -> bool:
    """移除审查守卫监听QQ号"""
    if qq_number not in MODERATION_QQ:
        return False
    MODERATION_QQ.remove(qq_number)
    return True

def get_translation_qq() -> Set[str]:
    """获取翻译守卫监听QQ号列表"""
    return TRANSLATION_QQ.copy()

def add_translation_qq(qq_number: str) -> bool:
    """添加翻译守卫监听QQ号"""
    if qq_number in TRANSLATION_QQ:
        return False
    TRANSLATION_QQ.add(qq_number)
    return True

def remove_translation_qq(qq_number: str) -> bool:
    """移除翻译守卫监听QQ号"""
    if qq_number not in TRANSLATION_QQ:
        return False
    TRANSLATION_QQ.remove(qq_number)
    return True

def get_group_whitelist() -> Set[str]:
    """获取群聊白名单"""
    return GROUP_WHITELIST.copy()

def add_group_whitelist(group_id: str) -> bool:
    """添加群聊到白名单"""
    group_id_str = str(group_id)
    if group_id_str in GROUP_WHITELIST:
        return False
    GROUP_WHITELIST.add(group_id_str)
    return True

def remove_group_whitelist(group_id: str) -> bool:
    """从白名单中移除群聊"""
    group_id_str = str(group_id)
    if group_id_str not in GROUP_WHITELIST:
        return False
    GROUP_WHITELIST.remove(group_id_str)
    return True

def get_group_blacklist() -> Set[str]:
    """获取群聊黑名单"""
    return GROUP_BLACKLIST.copy()

def add_group_blacklist(group_id: str) -> bool:
    """添加群聊到黑名单"""
    group_id_str = str(group_id)
    if group_id_str in GROUP_BLACKLIST:
        return False
    GROUP_BLACKLIST.add(group_id_str)
    return True

def remove_group_blacklist(group_id: str) -> bool:
    """从黑名单中移除群聊"""
    group_id_str = str(group_id)
    if group_id_str not in GROUP_BLACKLIST:
        return False
    GROUP_BLACKLIST.remove(group_id_str)
    return True
