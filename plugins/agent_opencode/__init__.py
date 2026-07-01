from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message, MessageEvent, Bot
from nonebot.exception import FinishedException
from nonebot import on_command
from nonebot.params import CommandArg
import asyncio
import subprocess
import shlex
import re

from plugins.common import extract_text, autoWrapMessage

__plugin_meta__ = PluginMetadata(
    name="agent_opencode",
    description="Agent Opencode plugin",
    usage="/y <内容> - 使用 opencode 调用 genshin-expert agent 运行",
)

opencode_cmd = on_command("y", aliases={"opencode"}, block=True, priority=8)

def remove_ansi_escape(text: str) -> str:
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)


def parse_opencode_output(output: str) -> str:
    output = remove_ansi_escape(output.strip())
    lines = output.split('\n')
    # 移除前面的提示信息行，如 "> genshin-expert · deepseek-v4-flash-free"
    clean_lines = []
    for line in lines:
        if line.startswith("> ") and "genshin-expert" in line:
            continue
        clean_lines.append(line)
    return '\n'.join(clean_lines).strip() or "（无内容返回）"


EMPTY_OUTPUT = "（无内容返回）"

@opencode_cmd.handle()
async def handle_opencode(bot: Bot, event: MessageEvent, args: Message = CommandArg()):
    (content, replied_content) = await extract_text(event)
    prompt = replied_content or args.extract_plain_text().strip()
    
    if not prompt:
        await opencode_cmd.finish("e.g. /y 雷内为什么要发明世界式？")
    
    prompt += "\n(请一次性输出所有完整的结论，不要断片，直接给我最终结果)"
    safe_prompt = shlex.quote(prompt)
    cmd = f"opencode run --agent genshin-expert {safe_prompt}"
    
    try:
        result = await asyncio.to_thread(subprocess.run, cmd, shell=True, capture_output=True, text=True, timeout=900)
        if result.returncode != 0:
            await opencode_cmd.finish(f"执行失败:\n{result.stderr.strip() or result.stdout.strip() or '未知错误'}")

        final_output = parse_opencode_output(result.stdout)

        # 当首次没有有效内容时，最多重试 2 次；第 2 次重试前等待 120s
        if final_output == EMPTY_OUTPUT:
            retry_result_1 = await asyncio.to_thread(subprocess.run, cmd, shell=True, capture_output=True, text=True)
            if retry_result_1.returncode == 0:
                final_output = parse_opencode_output(retry_result_1.stdout)

        if final_output == EMPTY_OUTPUT:
            await asyncio.sleep(120)
            retry_result_2 = await asyncio.to_thread(subprocess.run, cmd, shell=True, capture_output=True, text=True)
            if retry_result_2.returncode == 0:
                final_output = parse_opencode_output(retry_result_2.stdout)
            
        await autoWrapMessage(bot, event, opencode_cmd, final_output, limit=130)
    except FinishedException:
        raise
    except Exception as e:
        await autoWrapMessage(bot, event, opencode_cmd, f"执行出现异常:\n{str(e)}", limit=130)
