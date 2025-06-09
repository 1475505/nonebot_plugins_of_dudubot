from nonebot import get_app, get_driver
from nonebot.plugin import PluginMetadata
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse
import os
import difflib

__plugin_meta__ = PluginMetadata(
    name="文件上传插件",
    description="通过FastAPI路由实现文件上传",
    usage="访问 /upload/midi 或 /upload/7s 路由上传文件"
)

app = get_app()
midi_app = FastAPI()

@midi_app.post("/midi")
async def upload_file(file: UploadFile = File(...)):
    save_path = f"/root/nb/resources/{file.filename}"
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    content = await file.read()
    with open(save_path, 'wb') as f:
        f.write(content)
    return {"filename": file.filename, "message": "文件上传成功"}

@midi_app.get("/midi", response_class=HTMLResponse)
async def upload_page():
    return """
    <html>
        <body>
            <h1>文件上传</h1>
            <form action="/upload/midi" enctype="multipart/form-data" method="post">
                <input name="file" type="file">
                <input type="submit" value="上传">
            </form>
        </body>
    </html>
    """

# 添加腾讯云COS上传功能
from qcloud_cos import CosConfig, CosS3Client
import sys
import logging

# 配置腾讯云COS
secret_id = ''  # 替换为您的 SecretId
secret_key = ''  # 替换为您的 SecretKey
region = ''  # 替换为您的地域
bucket = '' # 替换为您的存储桶名称

# 初始化COS客户端
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
cos_config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
cos_client = CosS3Client(cos_config)

@midi_app.post("/7s")
async def upload_7s_to_cos(file: UploadFile = File(...), folder: str = Form("")):
    try:
        content = await file.read()
        
        # 根据选择的文件夹构建Key
        key = file.filename
        if folder:
            key = f"{folder}/{file.filename}"
            
        # 上传到腾讯云COS
        response = cos_client.put_object(
            Bucket=bucket,
            Body=content,
            Key=key,
            EnableMD5=False
        )
        
        # 构建访问URL
        file_url = f"https://{bucket}.cos.{region}.myqcloud.com/{key}"
        access_url = f"https://7simg.070077.xyz/{key}"
        return {"filename": file.filename, "folder": folder, "message": "文件上传成功", "url": file_url, "access_url": access_url}
    except Exception as e:
        return {"error": str(e)}
    finally:
        # 确保文件被关闭，临时文件会被清理
        await file.close()

@midi_app.get("/7s", response_class=HTMLResponse)
async def upload_7s_page():
    return """
    <html>
        <body>
            <h1>7s文件上传到腾讯云COS</h1>
            <form action="/upload/7s" enctype="multipart/form-data" method="post">
                <select name="folder">
                    <option value="" selected>根目录</option>
                    <option value="7s">7s</option>
                    <option value="image">image</option>
                </select>
                <input name="file" type="file">
                <input type="submit" value="上传">
            </form>
        </body>
    </html>
    """

@midi_app.get("/jokes", response_class=HTMLResponse)
async def jokes_page():
    return """
    <html>
        <body>
            <h1>添加笑话</h1>
            <form action="/upload/jokes" method="post">
                <label for="joke_type">笑话类型:</label>
                <select name="joke_type" id="joke_type">
                    <option value="cyno">赛诺</option>
                    <option value="jibao">鸡煲</option>
                </select>
                <br/><br/>
                <label for="joke_content">笑话内容:</label><br/>
                <textarea name="joke_content" id="joke_content" rows="10" cols="50"></textarea>
                <br/><br/>
                <input type="submit" value="提交">
            </form>
        </body>
    </html>
    """

@midi_app.post("/jokes")
async def submit_joke(joke_type: str = Form(...), joke_content: str = Form(...)):
    # 根据 joke_type 映射到具体目录
    if joke_type == "jibao":
        jokes_dir = os.path.expanduser("/root/nb/resources/jokes/jibao")
    elif joke_type == "cyno":
        jokes_dir = os.path.expanduser("/root/nb/resources/jokes/cyno")
    else:
        return {"error": "未知的笑话类型"}
    
    # 指定存储笑话的文件路径
    file_path = os.path.join(jokes_dir, "2.txt")
    # 确保目录存在
    os.makedirs(jokes_dir, exist_ok=True)
    
    # 将提交的笑话内容中的实际换行符转换为 "\n" 字符串
    new_joke = joke_content.replace("\n", "\\n").strip()
    
    # 如果文件存在，检查是否已有相似笑话（相似度大于90%）
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            existing_jokes = [line.strip() for line in f if line.strip()]
        for joke in existing_jokes:
            similarity = difflib.SequenceMatcher(None, new_joke, joke).ratio()
            if similarity >= 0.9:
                return {"error": "已有相似笑话"}
    
    # 追加新笑话到文件中，一行一笑话
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(new_joke + "\n")
    
    return {"message": "笑话添加成功", "joke": new_joke}

from fastapi import Depends, HTTPException
from fastapi.responses import FileResponse
from nonebot.plugin import PluginMetadata
from pathlib import Path

@midi_app.get("/getFile")
async def get_file(file: str = None):
    if not file:
        raise HTTPException(status_code=400, detail="请指定文件名")
    BASE_DIR = Path("/root/nb/resources")
    file_path = BASE_DIR / file
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    # 防止路径穿越攻击
    try:
        file_path.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="无权访问该文件")

    return FileResponse(
        file_path,
        filename=file_path.name,
        media_type="application/octet-stream"
    )

from fastapi import Header, Request
from typing import Optional
import json
from datetime import datetime

@midi_app.post("/report")
async def _(req: Request, content_disposition: Optional[str] = Header(None)):
    json_body = await req.json()
    filename = "received_data.json"  # Default filename
    if content_disposition:
        parts = content_disposition.split(';')
        for part in parts:
            part = part.strip()
            if part.startswith("filename="):
                filename = part.split('=')[1].strip().strip('"')
                break
    SAVE_DIR = "/root/nb/resources/logs"
    filepath = os.path.join(SAVE_DIR, filename)
     # Check if file exists and append timestamp if needed
    if os.path.exists(filepath):
        # Get current timestamp in yyyyMMdd-HHmmssSSS format
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")[:-3]
        # Split filename into name and extension
        name, ext = os.path.splitext(filename)
        # Create new filename with timestamp
        filename = f"{name}_{timestamp}{ext}"
        filepath = os.path.join(SAVE_DIR, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(json_body, f, ensure_ascii=False, indent=4)
    bot: Bot = list(get_driver().bots.values())[0] # Get the first available bot instance
    group_id = -1
    msg = "http://1.2.3.4:1234/upload/getLog?file=" + filename
    await bot.send_msg(group_id=group_id, message=msg, message_type="group")


@midi_app.get("/getLog")
async def get_file2(file: str = None):
    if not file:
        raise HTTPException(status_code=400, detail="请指定文件名")
    BASE_DIR = Path("/root/nb/resources/logs/")
    file_path = BASE_DIR / file
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="文件不存在")

    # 防止路径穿越攻击
    try:
        file_path.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="无权访问该文件")

    return FileResponse(
        file_path,
        filename=file_path.name
    )


driver = get_driver()

@driver.on_startup
async def startup():
    driver.server_app.mount('/upload', midi_app)
