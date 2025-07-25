# -*- coding: utf-8 -*-

import os
import json
import nonebot
from nonebot import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageSegment
from nonebot.plugin import PluginMetadata
from tencentcloud.common import credential
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.tts.v20190823 import tts_client, models
import base64

__plugin_meta__ = PluginMetadata(
    name="语音合成",
    description="调用腾讯云接口，将文本转换为语音",
    usage="""
    指令：语音合成 {文本}
    例如：语音合成 你好，世界
    """,
)

summary_audio = on_command("语音合成", priority=13, block=True)

@summary_audio.handle()
async def handle_summary_audio(event: GroupMessageEvent, msg: Message = nonebot.params.CommandArg()):
    text_to_synthesize = msg.extract_plain_text().strip()
    if not text_to_synthesize:
        await summary_audio.finish("请输入需要合成的文本。")

    TENCENTCLOUD_SECRET_ID = os.environ.get("HUNYUAN_SECRET_ID", "")
    TENCENTCLOUD_SECRET_KEY = os.environ.get("HUNYUAN_SECRET_KEY", "")

    if not TENCENTCLOUD_SECRET_ID or not TENCENTCLOUD_SECRET_KEY:
        await summary_audio.finish("缺少腾讯云密钥，请设置 HUNYUAN_SECRET_ID 和 HUNYUAN_SECRET_KEY 环境变量。")

    try:
        cred = credential.Credential(TENCENTCLOUD_SECRET_ID, TENCENTCLOUD_SECRET_KEY)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "tts.tencentcloudapi.com"

        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile
        client = tts_client.TtsClient(cred, "", clientProfile)

        req = models.TextToVoiceRequest()
        params = {
            "Text": text_to_synthesize,
            "SessionId": str(event.user_id),
            "Volume": 5,
            "Speed": 0,
            "ProjectId": 0,
            "ModelType": 1,
            "VoiceType": 101016, # 智瑜
            "PrimaryLanguage": 1,
            "SampleRate": 24000,
            "Codec": "mp3"
        }
        req.from_json_string(json.dumps(params))

        resp = client.TextToVoice(req)

        # 将音频内容进行 Base64 编码
        audio_base64 = base64.b64encode(resp.Audio).decode('utf-8')

        # 构建语音消息段
        audio_segment = MessageSegment.record(f"base64://{audio_base64}")

        # 发送语音消息
        await summary_audio.finish(audio_segment)

    except TencentCloudSDKException as err:
        nonebot.logger.error(f"腾讯云语音合成API调用失败: {err}")
        await summary_audio.finish(f"语音合成失败，请检查后台日志。")
    except Exception as e:
        nonebot.logger.error(f"处理语音合成时发生未知错误: {e}")
        await summary_audio.finish(f"发生未知错误，请联系管理员。")
