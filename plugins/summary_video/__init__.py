from nonebot import get_plugin_config, on_command, logger
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message, MessageSegment
from nonebot.params import CommandArg

from plugins.common import limiter, callDoubaoVideo
from .config import Config

__plugin_meta__ = PluginMetadata(
    name="summary_video",
    description="",
    usage="",
    config=Config,
)


aivideo = on_command("aivideo", priority=5, block=True)

@aivideo.handle()
async def handle_aivideo(args: Message = CommandArg(), event=None):
    user_id = str(event.user_id)
    
    # Rate limiting: 8 times per day (1440 minutes)
    if not limiter.check("aivideo", "*", 1440, 5):
        await aivideo.finish("今日视频生成次数已达上限（5次/天）")

    prompt = args.extract_plain_text().strip()
    if not prompt:
        await aivideo.finish("请输入视频描述")
        
    # Extract image URL if present
    image_urls = []
    for seg in args:
        if seg.type == "image":
            image_urls.append(seg.data["url"])
            
    image_url = image_urls[0] if image_urls else None
    
    await aivideo.send("视频生成中，请稍候（约需1-3分钟）...")
    
    try:
        video_url = await callDoubaoVideo(prompt, image_url=image_url)
        await aivideo.finish(MessageSegment.video(video_url))
    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        await aivideo.finish(f"视频生成失败: {e}")
