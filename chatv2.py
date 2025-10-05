# -*- coding: utf-8 -*-
import asyncio
import http.cookies
import random
import time
from typing import *
from collections import defaultdict

import aiohttp
import requests

import blivedm
import blivedm.models.web as web_models

from glm import generate_response

TEST_ROOM_IDS = [
    1908321388
]

SESSDATA = 'c76ad4ad%2C1775001157%2Cddeff%2Aa2CjDZcJ6vwBwXlZS30xuy-zBN_TMF_tLyKmrfpVlpehz-Nw16hsPMcN1pI1foecgbA8ASVmdZU2hoWkJNVklhdkVhT3IzV0hvQS1oRllab25lOUY2UVdpZG5SMHh6TldpX2NjblhiY0VyTnYzS3JCeUdaX1hJcGluLXdGVFBlTmVvcFRWYkJoMmR3IIEC'
BILI_JCT = "24e4702ab79fc547b20685a40b00535b"

message_history = defaultdict(lambda: defaultdict(list))

global_history = defaultdict(list)

MAX_HISTORY_PER_USER = 20
MAX_GLOBAL_HISTORY = 100

session: Optional[aiohttp.ClientSession] = None


def current_time():
    current_time = time.localtime()
    return time.strftime("%d-%H-%M-%S", current_time)


def get_recent_messages(room_id, uid, max_count=5):
    user_messages = message_history[room_id].get(uid, [])
    return user_messages[-max_count:] if user_messages else []


async def main():
    init_session()
    try:
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
    clients = [blivedm.BLiveClient(room_id, session=session) for room_id in TEST_ROOM_IDS]
    handler = MyHandler()
    for client in clients:
        client.set_handler(handler)
        client.start()

    try:
        await asyncio.gather(*(client.join() for client in clients))
    finally:
        await asyncio.gather(*(client.stop_and_close() for client in clients))


def send_danmaku(room_id, message, sessdata, bili_jct):
    url = "https://api.live.bilibili.com/msg/send"

    timestamp = int(time.time())

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Referer": f"https://live.bilibili.com/{room_id}",
        "Origin": "https://live.bilibili.com"
    }

    cookies = {
        "SESSDATA": sessdata,
        "bili_jct": bili_jct
    }

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
        response = requests.post(
            url,
            headers=headers,
            cookies=cookies,
            data=data
        )
        result = response.json()

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
    _CMD_CALLBACK_DICT = blivedm.BaseHandler._CMD_CALLBACK_DICT.copy()

    def _add_message_to_history(self, room_id, uid, username, message, message_type):
        time_str = current_time()
        if message_type == 'danmaku':
            msg_content = f'{time_str}  {username}：{message}'
        elif message_type == 'enter':
            msg_content = f'{time_str} 用户进入房间 - 用户名: {username}'
        elif message_type == 'follow':
            msg_content = f'{time_str} 用户关注直播间 - 用户名: {username}'
        elif message_type == 'like':
            msg_content = f'{time_str} 用户点赞 - 用户名: {username}'
        elif message_type == 'gift':
            msg_content = f'{time_str} {username} 赠送{message}'
        elif message_type == 'guard':
            msg_content = f'{time_str} {username} 上舰，guard_level={message}'
        elif message_type == 'super_chat':
            msg_content = f'{time_str} 醒目留言 ¥{message[0]} {username}：{message[1]}'
        elif message_type == 'reply':
            msg_content = f'{time_str} 喵寒OvO：{message}'
        else:
            msg_content = f'{time_str} {username}：{message}'

        user_history = message_history[room_id][uid]
        user_history.append(msg_content)

        if len(user_history) > MAX_HISTORY_PER_USER:
            message_history[room_id][uid] = user_history[-MAX_HISTORY_PER_USER:]

        global_history[room_id].append(msg_content)
        if len(global_history[room_id]) > MAX_GLOBAL_HISTORY:
            global_history[room_id] = global_history[room_id][-MAX_GLOBAL_HISTORY:]

        return msg_content

    def _generate_and_send_response(self, room_id, uid, username):
        recent_messages = get_recent_messages(room_id, uid)
        print(f"用户{username}的近期消息: {recent_messages}")

        context = global_history[room_id][-10:]

        response = generate_response(context)
        print(f"生成的回复: {response}")

        if response.get('answer') and response['answer'] != '无回复':
            # 发送弹幕
            loop = asyncio.get_event_loop()
            loop.run_in_executor(
                None,
                send_danmaku,
                room_id,
                response['answer'],
                SESSDATA,
                BILI_JCT
            )

            self._add_message_to_history(room_id, 0, "喵寒OvO", response['answer'], 'reply')

    def _on_interact_word_v2(self, client: blivedm.BLiveClient, message: web_models.InteractWordV2Message):
        room_id = client.room_id
        uid = message.uid
        username = message.username

        if message.msg_type == 1:
            print(f'[{room_id}] 用户进入房间 - 用户名: {username}, 用户ID: {uid}')
            self._add_message_to_history(room_id, uid, username, "", 'enter')
            self._generate_and_send_response(room_id, uid, username)

        elif message.msg_type == 2:
            print(f'[{room_id}] 用户关注直播间 - 用户名: {username}, 用户ID: {uid}')
            self._add_message_to_history(room_id, uid, username, "", 'follow')
            self._generate_and_send_response(room_id, uid, username)

    def _on_like_info_v3_click(self, client: blivedm.BLiveClient, command: dict):
        """处理用户点赞事件"""
        room_id = client.room_id
        data = command.get('data', {})
        uid = data.get('uid', 0)
        username = data.get('uname', '未知用户')

        print(f'[{room_id}] 用户点赞 - 用户名: {username}')
        self._add_message_to_history(room_id, uid, username, "", 'like')
        self._generate_and_send_response(room_id, uid, username)

    def _on_gift(self, client: blivedm.BLiveClient, message: web_models.GiftMessage):
        """处理礼物事件"""
        room_id = client.room_id
        uid = message.uid
        username = message.uname
        gift_info = f"{message.gift_name}x{message.num}（{message.coin_type}瓜子x{message.total_coin}）"

        print(f'[{room_id}] {username} 赠送{gift_info}')
        self._add_message_to_history(room_id, uid, username, gift_info, 'gift')
        self._generate_and_send_response(room_id, uid, username)

    def _on_danmaku(self, client: blivedm.BLiveClient, message: web_models.DanmakuMessage):
        """处理弹幕消息"""
        room_id = client.room_id
        uid = message.uid
        username = message.uname
        content = message.msg

        print(f'[{room_id}] {username}：{content}')
        self._add_message_to_history(room_id, uid, username, content, 'danmaku')
        self._generate_and_send_response(room_id, uid, username)

    def _on_user_toast_v2(self, client: blivedm.BLiveClient, message: web_models.UserToastV2Message):
        """处理上舰事件"""
        room_id = client.room_id
        uid = message.uid
        username = message.username
        guard_level = message.guard_level

        print(f'[{room_id}] {username} 上舰，guard_level={guard_level}')
        self._add_message_to_history(room_id, uid, username, guard_level, 'guard')
        # 生成并发送回复
        self._generate_and_send_response(room_id, uid, username)

    def _on_super_chat(self, client: blivedm.BLiveClient, message: web_models.SuperChatMessage):
        """处理醒目留言"""
        room_id = client.room_id
        uid = message.uid
        username = message.uname
        price = message.price
        content = message.message

        print(f'[{room_id}] 醒目留言 ¥{price} {username}：{content}')
        self._add_message_to_history(room_id, uid, username, (price, content), 'super_chat')
        # 生成并发送回复
        self._generate_and_send_response(room_id, uid, username)

    def _on_heartbeat(self, client: blivedm.BLiveClient, message: web_models.HeartbeatMessage):
        """处理心跳包"""
        print(f'[{client.room_id}] 心跳')

    # 注册回调函数
    _CMD_CALLBACK_DICT['INTERACT_WORD'] = _on_interact_word_v2
    _CMD_CALLBACK_DICT['LIKE_INFO_V3_CLICK'] = _on_like_info_v3_click  # 点赞事件回调


if __name__ == '__main__':
    asyncio.run(main())

