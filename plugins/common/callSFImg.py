import os
import aiohttp
import asyncio
from openai import AsyncOpenAI

async def callDoubaoVideo(prompt, image_url=None, model="doubao-seedance-1-0-pro-250528"):
    """
    Call Doubao (Volcengine Ark) video generation API
    
    Args:
        prompt (str): The text prompt for video generation
        image_url (str, optional): URL of input image
        model (str): Model to use for generation
    
    Returns:
        str: The URL of the generated video
    """
    url = "https://ark.cn-beijing.volces.com/api/v3/contents/generations/tasks"
    token = os.getenv("ARK_API_KEY")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}"
    }
    
    content = [
        {
            "type": "text", 
            "text": f"{prompt}"
        }
    ]
    
    if image_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": image_url}
        })
        
    payload = {
        "model": model,
        "content": content
    }
    
    async with aiohttp.ClientSession() as session:
        # 1. Create Task
        async with session.post(url, json=payload, headers=headers) as response:
            result = await response.json()
            if "id" not in result:
                err = result.get("error") or result
                raise Exception(f"Failed to create video task: {err}")
            task_id = result["id"]
            
        # 2. Poll Task
        for _ in range(60): # Poll for 5 minutes (5s * 60)
            await asyncio.sleep(5)
            async with session.get(f"{url}/{task_id}", headers=headers) as response:
                result = await response.json()
                status = result.get("status")
                
                if status == "succeeded":
                    # Try to find video URL in common locations
                    content = result.get("content")
                    if isinstance(content, list) and content:
                        # Check for video_url in the list items
                        for item in content:
                            if "video_url" in item:
                                return item["video_url"]
                            if "url" in item: # Fallback
                                return item["url"]
                    elif isinstance(content, dict):
                        if "video_url" in content:
                            return content["video_url"]
                        if "url" in content:
                            return content["url"]
                            
                    # If we can't find it easily, return the whole content or raise
                    if content:
                        return str(content)
                        
                    raise Exception("Video generated but URL not found in response")
                    
                elif status == "failed":
                    err = result.get("error") or result
                    raise Exception(f"Video generation failed: {err}")
                    
        raise Exception("Video generation timed out")

async def callDoubaoImage(prompt, model="doubao-seedream-4-0-250828", image_url=None,
                          url="https://ark.cn-beijing.volces.com/api/v3",
                          token=None):
    """
    Call Doubao (Volcengine Ark) image generation API using OpenAI client
    
    Args:
        prompt (str): The text prompt for image generation
        model (str): Model to use for generation
        url (str): API endpoint URL
        token (str): API Key
    
    Returns:
        str: The URL of the generated image
    """
    if not token:
        token = os.getenv("ARK_API_KEY")
    
    extra_body = {
        "watermark": False
    }

    if not image_url:
        extra_body["image"] = image_url
        
    client = AsyncOpenAI(
        api_key=token,
        base_url=url,
    )
    
    try:
        response = await client.images.generate(
            model=model,
            prompt=prompt,
            size="2K",
            response_format="url",
            extra_body=extra_body
        )
        return response.data[0].url
    except Exception as e:
        raise Exception(f"Invalid response from Doubao Image API: {e}")

async def callSFImg(prompt, model="Qwen/Qwen-Image-Edit-2509", image=None):
    """
    Call SiliconFlow's image generation API and return the image URL
    
    Args:
        prompt (str): The text prompt for image generation
        model (str): Model to use for generation, defaults to "Qwen/Qwen-Image-Edit-2509"
        image (str, optional): URL of input image for image editing
    
    Returns:
        str: The URL of the generated image
        
    Raises:
        Exception: If no image is found in the response
    """
    url = "https://api.siliconflow.cn/v1/images/generations"
    token = os.getenv("SF_API_KEY")
    
    payload = {
        "model": model,
        "prompt": prompt
    }
    
    if image:
        payload["image"] = image
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            result = await response.json()
            
            if "images" not in result or not result["images"] or "url" not in result["images"][0]:
                raise Exception("No image found in response")
            
            return result["images"][0]["url"]

async def callSfVLM(prompt, image_urls=None, model="deepseek-ai/DeepSeek-OCR", 
img_field="image_url", txt_field="text", 
url = "https://api.siliconflow.cn/v1",
token = os.getenv("SF_API_KEY")):
    """
    Call SiliconFlow's chat/completions API for VLM/visual-language interactions.
    Build a single user message whose "content" is a list of content blocks:
      - {"type":"text", "text": "<prompt>"}
      - {"type":"image_url", "image_url": {"url": "<image_url>"}}

    This function returns the OCR result as a plain string by extracting all
    "text" blocks from the assistant's content and concatenating them.
    """

    # build content blocks: text first (if provided), then image blocks
    content_blocks = []
    if prompt:
        content_blocks.append({"type": "text", "text": prompt})

    if image_urls:
        if isinstance(image_urls, str):
            image_list = [image_urls]
        elif isinstance(image_urls, (list, tuple)):
            image_list = list(image_urls)
        else:
            raise TypeError("image_urls must be str or list/tuple of str")

        for img_url in image_list:
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": img_url}
            })

    if not content_blocks:
        raise ValueError("Either prompt or image_urls must be provided")

    messages = [{"role": "user", "content": content_blocks}]

    payload = {
        "model": model,
        "messages": messages
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    url = url + "/chat/completions"

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            result = await response.json()

            if "choices" in result and result["choices"]:
                choice = result["choices"][0]

                # Try to get assistant message content in common locations
                message = None
                if "message" in choice:
                    message = choice["message"]
                elif "content" in choice:
                    message = {"content": choice["content"]}
                elif "delta" in choice:
                    message = {"content": choice["delta"]}

                content = None
                if isinstance(message, dict) and "content" in message:
                    content = message["content"]
                elif isinstance(choice.get("message"), str):
                    # fallback: raw string message
                    return choice["message"]

                # If content is a list of content-blocks, collect text blocks
                if isinstance(content, list):
                    texts = []
                    for blk in content:
                        if not isinstance(blk, dict):
                            continue
                        # block may be {"type":"text","text":"..."}
                        if blk.get("type") == "text":
                            t = blk.get("text") or blk.get("content") or ""
                            if t:
                                texts.append(t)
                        # sometimes assistant returns {"type":"response","content":"..."} etc.
                        elif "text" in blk:
                            t = blk.get("text")
                            if t:
                                texts.append(t)
                        elif "content" in blk and isinstance(blk["content"], str):
                            texts.append(blk["content"])

                    if texts:
                        return "".join(texts)

                # If content is a plain string, return it
                if isinstance(content, str):
                    return content

                # Last fallback: try to extract text fields from choice directly
                for key in ("text", "ocr", "result"):
                    val = choice.get(key)
                    if isinstance(val, str) and val.strip():
                        return val

                # If nothing parsed, return the whole choice for debugging
                return choice

            err = result.get("error") or result
            raise Exception(f"Invalid response from SF VLM API: {err}")


async def callLLM(prompt, model="z-ai/glm-4.5-air:free", json_output=False, url="http://170.106.83.133:8999/v1/chat/completions",
    token="sk-1234567"):
    """
    Args:
        prompt (str): The text prompt for LLM
        model (str): Model to use, defaults to "deepseek-ai/deepseek-chat"
        json_output (bool): Whether to request JSON output format

    Returns:
        str: The LLM response text
    """
    messages = [{"role": "user", "content": prompt}]

    payload = {
        "model": model,
        "messages": messages
    }

    # 添加JSON输出格式支持
    if json_output:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            result = await response.json()

            if "choices" in result and result["choices"]:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    return choice["message"]["content"]

            err = result.get("error") or result
            raise Exception(f"Invalid response from LLM API: {err}")