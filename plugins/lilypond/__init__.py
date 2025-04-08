from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import Bot, Event, MessageSegment, Message

from .config import Config

import subprocess
import json
import shlex
import tempfile
import shutil
import os

__plugin_meta__ = PluginMetadata(
    name="lilypond",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)

lilypond = on_command('lilypond', aliases={'ly'}, priority=10)

@lilypond.handle()
async def _(bot: Bot, event: Event):
    message = event.get_message().extract_plain_text()
    if message.startswith('/lilypond'):
        message = message[len('/lilypond'):].strip()
    elif message.startswith('/ly'):
        message = message[len('/ly'):].strip()
    
    temp_dir = tempfile.mkdtemp()
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        generate_ts_path = os.path.join(script_dir, 'generate.ts')
        
        command = ["bun", generate_ts_path, message]
        try:
            result = subprocess.run(command, capture_output=True, text=True, cwd=temp_dir)
            output = result.stdout
            print(output)
            data = json.loads(output)
            for path in data['images']:
                await lilypond.send(MessageSegment.image(path))
            await lilypond.send(MessageSegment.record(data['audio']))
        except:
            await lilypond.finish(result.stderr)
    finally:
        shutil.rmtree(temp_dir)


from nonebot.params import CommandArg
lilypond_raw = on_command('lilypond_raw', aliases={'ly_r'}, priority=9, block=True)

@lilypond_raw.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    message = msg.extract_plain_text()
    temp_dir = tempfile.mkdtemp()
    output_path = os.path.join(temp_dir, 'output.ly')
    with open(output_path, 'w') as f:
        f.write(message)
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        generate_ts_path = os.path.join(script_dir, 'generate-raw.ts')
        print(output_path)
        command = ["bun", generate_ts_path, output_path]
        try:
            result = subprocess.run(command, capture_output=True, text=True, cwd=temp_dir)
            output = result.stdout
            print(output)
            data = json.loads(output)
            for path in data['images']:
                await lilypond_raw.send(MessageSegment.image(path))
            await lilypond_raw.send(MessageSegment.record(data['audio']))
        except:
            await lilypond_raw.finish(result.stderr)
    finally:
        shutil.rmtree(temp_dir)


lilypond_midi = on_command('lilypond_midi', aliases={'ly_m'}, priority=9, block=True)

import os
from pathlib import Path
import wave
import contextlib

from pathlib import Path
import pretty_midi

def extractMidiFirst(inputPath: Path, outputPath: Path, upperSecs: int):
    inputPath = Path(inputPath)
    outputPath = Path(outputPath)
    
    # 加载 MIDI 文件
    midi_data = pretty_midi.PrettyMIDI(str(inputPath))
    
    # 获取 MIDI 文件的总时长
    total_duration = midi_data.get_end_time()
    
    # 如果时长超过 upperSecs 秒，截取前 upperSecs 秒
    if total_duration > upperSecs:
        # 获取原始 MIDI 文件的 resolution
        resolution = midi_data.resolution
        if resolution <= 0:
            resolution = 220  # 使用默认 resolution
        
        # 获取初始节奏（转换为 BPM）
        tempos, tempo_times = midi_data.get_tempo_changes()
        if len(tempos) > 0:
            us_per_quarter_note = tempos[0]
            if us_per_quarter_note > 0 and us_per_quarter_note != float('inf'):
                initial_tempo = 60e6 / us_per_quarter_note  # 转换为 BPM
            else:
                initial_tempo = 120.0  # 默认节奏
        else:
            initial_tempo = 120.0  # 默认节奏

        print(f"使用 initial_tempo={initial_tempo}, resolution={resolution}")
        
        # 创建一个新的 PrettyMIDI 对象
        new_midi = pretty_midi.PrettyMIDI(
            initial_tempo=initial_tempo,
            resolution=resolution
        )
        
        # 复制乐器信息
        for instrument in midi_data.instruments:
            new_instrument = pretty_midi.Instrument(
                program=instrument.program,
                is_drum=instrument.is_drum,
                name=instrument.name
            )
            # 复制在 upperSecs 秒之前的音符
            for note in instrument.notes:
                if note.start < upperSecs:
                    # 调整音符的结束时间，如果超过 upperSecs，则截断
                    note_end = min(note.end, upperSecs)
                    new_note = pretty_midi.Note(
                        velocity=note.velocity,
                        pitch=note.pitch,
                        start=note.start,
                        end=note_end
                    )
                    new_instrument.notes.append(new_note)
            # 复制弯音事件
            for bend in instrument.pitch_bends:
                if bend.time <= upperSecs:
                    new_instrument.pitch_bends.append(bend)
            # 复制控制器变化事件
            for cc in instrument.control_changes:
                if cc.time <= upperSecs:
                    new_instrument.control_changes.append(cc)
            # 将新乐器添加到 new_midi
            new_midi.instruments.append(new_instrument)
        
        # 保存新的 MIDI 数据到输出文件
        new_midi.write(str(outputPath))
    else:
        # 如果时长不超过 upperSecs，直接复制文件
        midi_data.write(str(outputPath))


def extractWavFirst(inputPath: Path, outputPath: Path, upperSecs: int):
    """
    读取输入的wav文件，判断时长，如果大于upperSecs秒，截取前upperSecs秒，输出到outputPath
    """
    inputPath = Path(inputPath)
    outputPath = Path(outputPath)
    
    # 打开输入 WAV 文件
    with wave.open(str(inputPath), 'rb') as infile:
        # 获取音频参数
        params = infile.getparams()
        n_channels, sampwidth, framerate, n_frames = params[:4]
        
        # 计算音频时长
        duration = n_frames / float(framerate)
        
        # 如果时长大于 upperSecs，则截取前 upperSecs 秒
        if duration > upperSecs:
            # 计算需要保留的帧数
            frames_to_keep = int(framerate * upperSecs)
            # 读取前 frames_to_keep 帧
            frames = infile.readframes(frames_to_keep)
        else:
            # 读取所有帧
            frames = infile.readframes(n_frames)
            frames_to_keep = n_frames  # 实际保留的帧数
        
    # 将截取的音频数据写入输出 WAV 文件
    with wave.open(str(outputPath), 'wb') as outfile:
        outfile.setnchannels(n_channels)
        outfile.setsampwidth(sampwidth)
        outfile.setframerate(framerate)
        outfile.writeframes(frames)    

@lilypond_midi.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    file_name = msg.extract_plain_text().strip()
    temp_dir = tempfile.mkdtemp()

    resources_dir = Path("/root/nb/resources")
    input_path = resources_dir / file_name
    input_trimmed_path = input_path.with_suffix(".trimmed.mid")
    output_path = resources_dir / f"{file_name}.ly"
    
    # 检查是否是文件
    if not input_path.is_file():
        with open(resources_dir / "damands.txt", "w") as f:
            f.write(file_name)
        await lilypond_midi.finish("文件不存在，已经加入人才库")
    
    if file_name.endswith(".ly"):
        output_path = input_path
    else:
        extractMidiFirst(input_path, input_trimmed_path, 300)
        try:
            if not output_path.is_file():
                # 执行转换命令
                cmd = [
                    "midi2ly", 
                    str(input_path),
                    "-o", str(output_path)  # 正确分隔参数
                ]
                subprocess.run(cmd, check=True, capture_output=True, text=True)
        except Exception as e:
            print(f"发生错误：{str(e)}")
            return
    
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        generate_ts_path = os.path.join(script_dir, 'generate-raw.ts')

        print(output_path)
        
        command = ["bun", generate_ts_path, output_path]
        try:
            result = subprocess.run(command, capture_output=True, text=True, cwd=temp_dir)
            output = result.stdout
            print(output)
            data = json.loads(output)
            # images = data['images']
            # if len(images) > 1:
            #     await lilypond_midi.send(f'五线谱数量过多，只发送第一张')
            #     await lilypond_raw.send(MessageSegment.image(images[0]))
            wav_file_path = data['audio']
            trimmed_wav_file_path = wav_file_path.replace(".wav", "-trimmed.wav")
            if os.path.exists(wav_file_path):
                extractWavFirst(wav_file_path, trimmed_wav_file_path, 300)
                await lilypond_raw.send(MessageSegment.record(trimmed_wav_file_path))
                # await bot.call_api("upload_group_file", group_id=event.group_id, file=wav_file_path, name=file_name + ".wav")
        except:
            await lilypond_raw.finish(result.stderr)
    finally:
        shutil.rmtree(temp_dir)
        pass



sf2_path = "data/sf2.txt"  # 文件路径
sf2_set = on_command("ly_sf2", block=True, priority=8)
@sf2_set.handle()
async def _(bot: Bot, event: Event, msg: Message = CommandArg()):
    data = msg.extract_plain_text().strip()
    path = Path(data)
    if not path.is_file():
        await sf2_set.finish("文件不存在")
        return
    with open(sf2_path, 'w', encoding='utf-8') as f:
        f.write(data)
    await sf2_set.finish(f"已设置 sf2 文件路径为：{data}")