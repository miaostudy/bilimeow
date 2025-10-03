# -*- coding: utf-8 -*-
import asyncio
import http.cookies
import random
import time
from typing import *

import aiohttp
import requests

import blivedm
import blivedm.models.web as web_models

TEST_ROOM_IDS = [
    1908321388,
]

SESSDATA = 'c76ad4ad%2C1775001157%2Cddeff%2Aa2CjDZcJ6vwBwXlZS30xuy-zBN_TMF_tLyKmrfpVlpehz-Nw16hsPMcN1pI1foecgbA8ASVmdZU2hoWkJNVklhdkVhT3IzV0hvQS1oRllab25lOUY2UVdpZG5SMHh6TldpX2NjblhiY0VyTnYzS3JCeUdaX1hJcGluLXdGVFBlTmVvcFRWYkJoMmR3IIEC'
BILI_JCT = "24e4702ab79fc547b20685a40b00535b"  # 从Cookie中获取的bili_jct值

session: Optional[aiohttp.ClientSession] = None


async def main():
    init_session()
    try:
        await run_single_client()
        await run_multi_clients()
    finally:
        await session.close()


def init_session():
    cookies = http.cookies.SimpleCookie()
    cookies['SESSDATA'] = SESSDATA
    cookies['SESSDATA']['domain'] = 'bilibili.com'

    global session
    session = aiohttp.ClientSession()
    session.cookie_jar.update_cookies(cookies)


async def run_single_client():
    """演示监听一个直播间"""
    room_id = random.choice(TEST_ROOM_IDS)
    client = blivedm.BLiveClient(room_id, session=session)
    handler = MyHandler()
    client.set_handler(handler)

    client.start()
    try:
        await asyncio.Event().wait()
        client.stop()

        await client.join()
    finally:
        await client.stop_and_close()


async def run_multi_clients():
    """演示同时监听多个直播间"""
    clients = [blivedm.BLiveClient(room_id, session=session) for room_id in TEST_ROOM_IDS]
    handler = MyHandler()
    for client in clients:
        client.set_handler(handler)
        client.start()

    try:
        await asyncio.gather(*(
            client.join() for client in clients
        ))
    finally:
        await asyncio.gather(*(
            client.stop_and_close() for client in clients
        ))


def send_danmaku(room_id, message, sessdata, bili_jct):
    """
    发送弹幕到B站直播间
    """
    # API端点
    url = "https://api.live.bilibili.com/msg/send"

    # 当前Unix时间戳
    timestamp = int(time.time())

    # 请求头
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": f"https://live.bilibili.com/{room_id}",
        "Origin": "https://live.bilibili.com"
    }

    # Cookie
    cookies = {
        "SESSDATA": sessdata,
        "bili_jct": bili_jct
    }

    # 表单数据
    data = {
        "csrf": bili_jct,
        "roomid": room_id,
        "msg": message,
        "rnd": timestamp,
        "fontsize": 25,
        "color": 16777215,  # 白色
        "mode": 1,
        "bubble": 0,
        "room_type": 0,
        "jumpfrom": 0,
        "csrf_token": bili_jct
    }

    try:
        # 发送POST请求
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,
            data=data
        )

        # 解析响应
        result = response.json()

        # 处理返回结果
        if result["code"] == 0:
            print(f"弹幕发送成功: {message}")
            return True
        else:
            print(f"发送失败: {result['message']} (错误代码: {result['code']})")
            return False

    except Exception as e:
        print(f"发送过程中发生错误: {str(e)}")
        return False


class MyHandler(blivedm.BaseHandler):
    # 演示如何添加自定义回调
    _CMD_CALLBACK_DICT = blivedm.BaseHandler._CMD_CALLBACK_DICT.copy()

    # 处理用户互动消息（包括进入房间、关注等）
    def _on_interact_word_v2(self, client: blivedm.BLiveClient, message: web_models.InteractWordV2Message):
        # msg_type == 1 表示用户进入直播间
        if message.msg_type == 1:
            print(f'[{client.room_id}] 用户进入房间 - 用户名: {message.username}, 用户ID: {message.uid}')

            # 发送欢迎弹幕
            welcome_msg = f"欢迎{message.username}~"
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                None,
                send_danmaku,
                client.room_id,
                welcome_msg,
                SESSDATA,
                BILI_JCT
            )

        # msg_type == 2 表示用户关注直播间
        elif message.msg_type == 2:
            print(f'[{client.room_id}] 用户关注直播间 - 用户名: {message.username}, 用户ID: {message.uid}')

            # 发送感谢关注弹幕
            thank_msg = f"感谢{message.username}的关注~"
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                None,
                send_danmaku,
                client.room_id,
                thank_msg,
                SESSDATA,
                BILI_JCT
            )

    # 处理点赞事件
    def _on_like_info_v3_click(self, client: blivedm.BLiveClient, command: dict):
        data = command.get('data', {})
        username = data.get('uname', '未知用户')
        print(f'[{client.room_id}] 用户点赞 - 用户名: {username}')

        # 发送感谢点赞弹幕
        thank_msg = f"感谢{username}的点赞~"
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            None,
            send_danmaku,
            client.room_id,
            thank_msg,
            SESSDATA,
            BILI_JCT
        )

    # 处理送礼事件
    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        print(f'[{client.room_id}] {message.uname} 赠送{message.gift_name}x{message.num}'
              f' （{message.coin_type}瓜子x{message.total_coin}）')

        # 发送感谢礼物弹幕
        thank_msg = f"感谢{message.uname}赠送的{message.gift_name}~"
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            None,
            send_danmaku,
            client.room_id,
            thank_msg,
            SESSDATA,
            BILI_JCT
        )

    # 注册回调函数
    _CMD_CALLBACK_DICT['INTERACT_WORD'] = _on_interact_word_v2
    _CMD_CALLBACK_DICT['LIKE_INFO_V3_CLICK'] = _on_like_info_v3_click  # 点赞事件回调

    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        print(f'[{client.room_id}] 心跳')

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        print(f'[{client.room_id}] {message.uname}：{message.msg}')

    def _on_user_toast_v2(self, client: blivedm.BLiveClient, message: web_models.UserToastV2Message):
        print(f'[{client.room_id}] {message.username} 上舰，guard_level={message.guard_level}')

        # 发送感谢上舰弹幕
        thank_msg = f"感谢{message.username}的上舰支持~"
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            None,
            send_danmaku,
            client.room_id,
            thank_msg,
            SESSDATA,
            BILI_JCT
        )

    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        print(f'[{client.room_id}] 醒目留言 ¥{message.price} {message.uname}：{message.message}')

        # 发送感谢醒目留言弹幕
        thank_msg = f"感谢{message.uname}的¥{message.price}醒目留言~"
        loop = asyncio.get_event_loop()
        loop.run_in_executor(
            None,
            send_danmaku,
            client.room_id,
            thank_msg,
            SESSDATA,
            BILI_JCT
        )


if __name__ == '__main__':
    asyncio.run(main())
