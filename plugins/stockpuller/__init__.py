from nonebot import get_plugin_config
from nonebot.plugin import PluginMetadata
from nonebot.plugin import on_command,on_regex,on_command
from nonebot.adapters.onebot.v11 import Bot, Event

from .config import Config

__plugin_meta__ = PluginMetadata(
    name="stockpuller",
    description="",
    usage="",
    config=Config,
)

config = get_plugin_config(Config)
from nonebot.rule import to_me
showA = on_command('A股', aliases={'stockA'}, priority=10) 
showHK = on_command('港股', aliases={'stockHK'}, priority=10)
showUS = on_command('美股', aliases={'stockUS'}, priority=10)

import requests

apiKey = ''  # 在个人中心->我的数据,接口名称上方查看

def buildMessageA(res):
    info = res['result'][0]['data']
    name = info['name']
    lastestpri = info['nowPri']
    limit = info['increPer']
    yesterdayPrice = info['yestodEndPri']
    return name + '：' + lastestpri + ", 变化：" + limit + '%（昨日收盘价 ' + yesterdayPrice + ')'

def buildMessage(res):
    info = res['result'][0]['data']
    name = info['name']
    lastestpri = info['lastestpri']
    limit = info['limit']
    yesterdayPrice = info['formpri']
    return name + '：' + lastestpri + ", 变化：" + limit + '%（昨日收盘价 ' + yesterdayPrice + ')'


def buildMessageHK(res):
    info = res['result'][0]['hengsheng_data']
    name = '\n\n恒生指数'
    lastestpri = info['lastestpri']
    limit = info['limit']
    yesterdayPrice = info['formpri']
    return name + '：' + lastestpri + ", 变化：" + limit + '%（昨日收盘价 ' + yesterdayPrice + ')'

@showA.handle()
async def _(bot: Bot, event: Event):
    msg = str(event.get_message())
    # Parse multiple codes separated by comma or space
    codes_str = msg.replace('/A股', '').strip()
    if not codes_str:
        await showA.send("请提供股票代码，如：/A股 000001,000002")
        return
    
    # Split by comma and clean up
    codes = [code.strip() for code in codes_str.replace(',', ' ').split()]
    codes = codes[:3]  # Limit to 3 codes
    
    if not codes:
        await showA.send("请提供有效的股票代码")
        return
    
    results = []
    apiUrl = 'http://web.juhe.cn/finance/stock/hs'  # 接口请求URL
    
    for code in codes:
        if code[0].isdigit():
            code = "sh" + code
        requestParams = {
            'key': apiKey,
            'gid': code
        }
        try:
            response = requests.get(apiUrl, params=requestParams)
            if response.status_code == 200:
                res = response.json()
                if 'result' in res and res['result']:
                    results.append(buildMessageA(res))
                else:
                    results.append(f"股票代码 {code} 查询失败")
            else:
                results.append(f"股票代码 {code} 查询失败")
        except Exception as e:
            results.append(f"股票代码 {code} 查询出错")
    
    if results:
        await showA.send('\n'.join(results))


@showHK.handle()
async def _(bot: Bot, event: Event):
    msg = str(event.get_message())
    # Parse multiple codes separated by comma or space
    codes_str = msg.replace('/港股', '').strip()
    if not codes_str:
        await showHK.send("请提供股票代码，如：/港股 09988,00700")
        return
    
    # Split by comma and clean up
    codes = [code.strip() for code in codes_str.replace(',', ' ').split()]
    codes = codes[:3]  # Limit to 3 codes
    
    if not codes:
        await showHK.send("请提供有效的股票代码")
        return
    
    results = []
    apiUrl = 'http://web.juhe.cn/finance/stock/hk'  # 接口请求URL
    
    for code in codes:
        requestParams = {
            'key': apiKey,
            'num': code
        }
        try:
            response = requests.get(apiUrl, params=requestParams)
            if response.status_code == 200:
                res = response.json()
                if 'result' in res and res['result']:
                    results.append(buildMessage(res) + buildMessageHK(res))
                else:
                    results.append(f"股票代码 {code} 查询失败")
            else:
                results.append(f"股票代码 {code} 查询失败")
        except Exception as e:
            results.append(f"股票代码 {code} 查询出错")
    
    if results:
        await showHK.send('\n'.join(results))


@showUS.handle()
async def _(bot: Bot, event: Event):
    msg = str(event.get_message())
    # Parse multiple codes separated by comma or space
    codes_str = msg.replace('/美股', '').strip()
    if not codes_str:
        await showUS.send("请提供股票代码，如：/美股 AAPL,TSLA")
        return
    
    # Split by comma and clean up
    codes = [code.strip() for code in codes_str.replace(',', ' ').split()]
    codes = codes[:3]  # Limit to 3 codes
    
    if not codes:
        await showUS.send("请提供有效的股票代码")
        return
    
    results = []
    apiUrl = 'http://web.juhe.cn/finance/stock/usa'  # 接口请求URL
    
    for code in codes:
        requestParams = {
            'key': apiKey,
            'gid': code
        }
        try:
            response = requests.get(apiUrl, params=requestParams)
            if response.status_code == 200:
                res = response.json()
                if 'result' in res and res['result']:
                    results.append(buildMessage(res))
                else:
                    results.append(f"股票代码 {code} 查询失败")
            else:
                results.append(f"股票代码 {code} 查询失败")
        except Exception as e:
            results.append(f"股票代码 {code} 查询出错")
    
    if results:
        await showUS.send('\n'.join(results))


import requests
import random
import re

def get_latest_comic_num():
    """获取最新的 xkcd 漫画编号"""
    url = "https://xkcd.com/info.0.json"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    return data['num']

def get_comic_info(comic_num):
    """获取指定编号的 xkcd 漫画信息"""
    url = f"https://xkcd.com/{comic_num}/info.0.json"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

def get_comic_url(num):
    """获取 xkcd 漫画 URL"""

    url = f"https://xkcd.in/comic?lg=en&id={num}"
    response = requests.get(url)
    response.raise_for_status()
    regex = r"/resources/compiled/[0-9a-f]{32}.png"
    match = re.search(regex, response.text)
    if match:
        comic_url = "https://xkcd.in" + match.group(0)
        return comic_url
    else:
        return None

from nonebot.adapters.onebot.v11 import MessageSegment
xkcd = on_command("xkcd", block=False)
@xkcd.handle()
async def _(bot: Bot, event: Event):
    msg = str(event.get_message())
    numStr = msg.split()[-1].strip()
    if numStr.startswith("e"):
        num = int(numStr[1:])
        await xkcd.send(f'https://www.explainxkcd.com/wiki/index.php/{num}')
        return
    try:
        num = int(numStr)
    except ValueError:
        """获取随机的 xkcd 漫画 URL"""
        latest_comic_num = get_latest_comic_num()
        random_comic_num = random.randint(1, latest_comic_num)
        num = random_comic_num

    img_url = get_comic_url(num)
    comic_info = get_comic_info(num)
    await xkcd.send(f'[{num} - {comic_info["title"]}]\n {comic_info["alt"]} \n https://www.explainxkcd.com/wiki/index.php/{num}')
    await xkcd.finish(MessageSegment.image(img_url))

crypto = on_command("crypto", block=False)
@crypto.handle()
async def _(bot: Bot, event: Event):
    msg = str(event.get_message())
    code = msg.split()[-1].strip().upper()
    apiUrl = f'https://data-api.binance.vision/api/v3/ticker/price?symbol={code}'  # 接口请求URL
    response = requests.get(apiUrl)
    if response.status_code == 200:
        res = response.json()
        await showA.send(res["price"])



