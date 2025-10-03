import requests
import time


def send_danmaku(room_id, message, sessdata, bili_jct):
    """
    发送弹幕到B站直播间

    参数:
    room_id: 直播间ID
    message: 要发送的弹幕内容
    sessdata: 登录Cookie中的SESSDATA值
    bili_jct: 登录Cookie中的bili_jct值，用作csrf
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


if __name__ == "__main__":
    # 配置信息 - 请替换为你自己的信息
    ROOM_ID = 1908321388  # 直播间ID
    MESSAGE = "test"  # 要发送的弹幕内容
    SESSDATA = "c76ad4ad%2C1775001157%2Cddeff%2Aa2CjDZcJ6vwBwXlZS30xuy-zBN_TMF_tLyKmrfpVlpehz-Nw16hsPMcN1pI1foecgbA8ASVmdZU2hoWkJNVklhdkVhT3IzV0hvQS1oRllab25lOUY2UVdpZG5SMHh6TldpX2NjblhiY0VyTnYzS3JCeUdaX1hJcGluLXdGVFBlTmVvcFRWYkJoMmR3IIEC"  # 从Cookie中获取
    BILI_JCT = "24e4702ab79fc547b20685a40b00535b"  # 从Cookie中获取

    # 发送弹幕
    send_danmaku(ROOM_ID, MESSAGE, SESSDATA, BILI_JCT)
