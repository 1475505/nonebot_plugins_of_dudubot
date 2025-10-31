import os
import json
import hashlib
import time
import base64
from typing import Tuple, Dict, Any
import httpx


class TencentTextModerator:
    """腾讯云文本内容安全审查服务"""

    def __init__(self, region: str = "ap-beijing"):
        # 从环境变量读取密钥信息
        self.secret_id = os.getenv("TENCENTCLOUD_SECRET_ID")
        self.secret_key = os.getenv("TENCENTCLOUD_SECRET_KEY")
        self.region = region
        self.endpoint = "ims.tencentcloudapi.com"
        self.service = "ims"
        self.version = "2020-12-29"

    def _sign(self, key: str, msg: str) -> str:
        """生成签名"""
        return hashlib.sha256(msg.encode('utf-8')).hexdigest()

    def _get_signature(self, payload: str, headers: Dict[str, str]) -> str:
        """计算HMAC-SHA256签名"""
        # 步骤1: 拼接规范请求串
        http_request_method = "POST"
        canonical_uri = "/"
        canonical_querystring = ""
        canonical_headers = '\n'.join([f"{k.lower()}:{v}" for k, v in sorted(headers.items())]) + '\n'
        signed_headers = ';'.join([k.lower() for k in sorted(headers.keys())])
        hashed_request_payload = hashlib.sha256(payload.encode('utf-8')).hexdigest()

        canonical_request = f"{http_request_method}\n{canonical_uri}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{hashed_request_payload}"

        # 步骤2: 拼接待签名字符串
        algorithm = "TC3-HMAC-SHA256"
        timestamp = headers.get("X-TC-Timestamp", "")
        date = time.strftime("%Y-%m-%d", time.gmtime(int(timestamp)))
        credential_scope = f"{date}/{self.service}/tc3_request"
        hashed_canonical_request = hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()

        string_to_sign = f"{algorithm}\n{timestamp}\n{credential_scope}\n{hashed_canonical_request}"

        # 步骤3: 计算签名
        secret_date = self._sign(f"TC3{self.secret_key}", date)
        secret_service = self._sign(secret_date, self.service)
        secret_signing = self._sign(secret_service, "tc3_request")
        signature = self._sign(secret_signing, string_to_sign)

        return signature

    async def check_text(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """
        检查文本内容

        Args:
            text: 要检查的文本内容

        Returns:
            Tuple[bool, Dict]: (是否通过, 详细结果)
        """
        if not self.secret_id or not self.secret_key:
            raise ValueError("腾讯云配置不完整")

        # 准备请求参数
        # 对文本内容进行Base64加密
        content_base64 = base64.b64encode(text.encode('utf-8')).decode('utf-8')
        payload = {
            "Content": content_base64,
            "BizType": "dudubot",  # 指定业务类型，只检查色情内容
        }

        payload_str = json.dumps(payload)

        # 准备请求头
        timestamp = str(int(time.time()))
        headers = {
            "Authorization": "",
            "Content-Type": "application/json; charset=utf-8",
            "Host": self.endpoint,
            "X-TC-Action": "TextModeration",
            "X-TC-Timestamp": timestamp,
            "X-TC-Version": self.version,
            "X-TC-Region": self.region,
        }

        # 计算签名
        signature = self._get_signature(payload_str, headers)
        authorization = f"TC3-HMAC-SHA256 Credential={self.secret_id}/{time.strftime('%Y-%m-%d', time.gmtime(int(timestamp)))}/{self.service}/tc3_request, SignedHeaders={';'.join(sorted(headers.keys()))}, Signature={signature}"
        headers["Authorization"] = authorization

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"https://{self.endpoint}",
                    headers=headers,
                    content=payload_str
                )
                response.raise_for_status()
                result = response.json()

                if "Response" in result:
                    resp = result["Response"]
                    if "Error" in resp:
                        return True, {"error": resp["Error"]}

                    # 检查审查结果
                    if resp.get("Suggestion") == "Block":
                        return False, resp
                    else:
                        return True, resp.get("Data", {"Message": "内容通过审查"})

                return True, {"error": "响应格式异常"}

        except Exception as e:
            raise Exception(f"腾讯云API调用失败: {str(e)}")