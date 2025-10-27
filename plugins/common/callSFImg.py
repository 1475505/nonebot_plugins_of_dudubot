import os
import aiohttp

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

async def callSfVLM(prompt, image_urls=None, model="deepseek-ai/DeepSeek-OCR"):
    """
    Call SiliconFlow's chat/completions API for VLM/visual-language interactions.
    Build a single user message whose "content" is a list of content blocks:
      - {"type":"text", "text": "<prompt>"}
      - {"type":"image_url", "image_url": {"url": "<image_url>"}}

    This function returns the OCR result as a plain string by extracting all
    "text" blocks from the assistant's content and concatenating them.
    """
    url = "https://api.siliconflow.cn/v1/chat/completions"
    token = os.getenv("SF_API_KEY")

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