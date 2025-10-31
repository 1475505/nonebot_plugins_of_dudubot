import os
import json
import re
import time
from datetime import datetime
from nonebot import on_message
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.log import logger
from typing import Set, Dict, Any

from plugins.common import TencentTextModerator, callSfVLM, callLLM
from .config import Config

# 配置检查
config = Config.parse_obj({})

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

# 审查缓存，避免1小时内重复审查
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
moderation_guarder = on_message(priority=1, block=False)

# 翻译守卫监听器，block=False
translation_guarder = on_message(priority=6, block=False)

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
        replySz = 15
        response = await generate_moderation_response(replySz)
        await moderation_guarder.send(response, at_sender=True)
        return

    # 检查缓存，1小时内不再重复审查
    current_time = time.time()
    cache_key = f"{user_id}"
    if cache_key in moderation_cache:
        last_moderation_time = moderation_cache[cache_key]
        if current_time - last_moderation_time < 3600:  # 1小时 = 3600秒
            logger.debug(f"用户 {user_id} 在1小时内已触发过审查，跳过本次审查")
            return

    try:
        logger.info(f"开始对用户 {user_id} 的消息进行审查: {message_text[:50]}...")

        # 腾讯云文本审查
        is_pass, result = await moderator.check_text(message_text)

        if not is_pass:
            logger.warning(f"用户 {user_id} 消息未通过审查: {result}")

            # 记录审查缓存，1小时内不再审查
            moderation_cache[cache_key] = current_time

            # 调用LLM生成回复
            response = await generate_moderation_response(replySz)
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
            logger.info(f"检测到日语并完成翻译: {translation_result[:50]}...")
            await translation_guarder.send(translation_result)
        else:
            logger.debug(f"用户 {user_id} 的消息非日语或无需翻译")

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

async def detect_and_translate(text: str) -> str:
    """检测语言并翻译（如果是日语则翻译成中文）"""
    try:
        logger.debug(f"开始语言检测，输入文本: {text[:100]}...")

        # 预检测：如果不包含日语字符，直接跳过LLM调用
        if not contains_japanese(text):
            logger.info("未检测到日语字符，跳过翻译")
            return ""

        logger.debug("检测到日语字符，调用LLM进行翻译")

        prompt = f"""请将以下日语文本翻译成中文：

原文：{text}

请直接输出翻译结果，不要包含任何其他解释。"""

        logger.debug("调用LLM进行日文翻译...")
        response = await callLLM(prompt, model="deepseek/deepseek-chat-v3-0324:free")
        logger.debug(f"LLM翻译响应: {response}")

        translation = response.strip()
        if translation:
            logger.info(f"日文翻译完成: {translation[:50]}...")
            return f"自动翻译：{translation}"
        else:
            logger.debug("翻译结果为空")
            return ""

    except Exception as e:
        logger.error(f"日文翻译失败: {e}")

    return ""

async def generate_moderation_response(txtSz: int) -> str:
    """生成基于当前时间的哲学/古典句子作为审查回复"""
    # 获取完整时间戳
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d%H%M%S%S")
    timestamp = int(timestamp_str)

    # 根据时间戳取模选择创作方向
    direction = timestamp % 3
    directions = [
        "中国古代流行诗句，如唐诗、诗经、宋词等",
        "近现代中外经典文学名句，如莎士比亚、泰戈尔、鲁迅等",
        "经典电影/二次元/《原神》游戏台词"
    ]
    selected_direction = directions[direction]

    prompt = f"""当前时间：{timestamp_str}

请专注于以下方向生成一句经典句子，{txtSz}字以内，中英文互译：

创作方向：{selected_direction}

格式：
[经典句子] —— [作者/出处]
[English translation]

请直接输出，无需解释。"""

    try:
        # 使用callLLM函数调用LLM
        response = await callLLM(prompt, model="z-ai/glm-4.5-air:free")
        return "\n" + response.strip()
    except Exception as e:
        logger.error(f"LLM调用失败: {e}")
        return f"""有宝宝尝试发脏东西"""

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