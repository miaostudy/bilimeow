import asyncio
import websockets
import struct
import json
import base64
import zlib
import brotli
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 连接参数
ROOM_ID = 1908321388  # 替换为目标直播间ID
UID = 0  # 0表示游客模式

# 协议常量
OP_HEARTBEAT = 2
OP_HEARTBEAT_REPLY = 3
OP_MESSAGE = 5
OP_AUTH = 7
OP_AUTH_REPLY = 8

# 重连间隔（秒）
RECONNECT_DELAY = 5


async def send_packet(websocket, data: str, op: int):
    """发送数据包到服务器"""
    data_bytes = data.encode('utf-8')
    # 构建头部 (大端序)
    header = struct.pack(
        '>I2H2I',
        len(data_bytes) + 16,  # 总长度 = 头部长度 + 数据长度
        16,  # 头部长度
        1,  # 协议版本
        op,  # 操作码
        1  # sequence
    )
    try:
        await websocket.send(header + data_bytes)
        logger.debug(f"已发送数据包，操作码: {op}")
        return True
    except Exception as e:
        logger.error(f"发送数据包失败: {e}")
        return False


async def heartbeat(websocket):
    """定期发送心跳包维持连接"""
    while True:
        try:
            # 发送心跳包
            success = await send_packet(websocket, "", OP_HEARTBEAT)
            if not success:
                break

            # 等待30秒后再次发送
            await asyncio.sleep(30)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"心跳包发送失败: {e}")
            break


def decode_data(data: bytes, version: int) -> str:
    """根据协议版本解码数据"""
    try:
        if version == 2:
            # zlib解压
            return zlib.decompress(data).decode('utf-8')
        elif version == 3:
            # brotli解压
            return brotli.decompress(data).decode('utf-8')
        else:
            # 无需解压
            return data.decode('utf-8')
    except Exception as e:
        logger.error(f"数据解码失败: {e}")
        return ""


async def handle_message(body: bytes, version: int):
    """处理接收到的消息"""
    decoded = decode_data(body, version)
    if not decoded:
        return

    try:
        # 可能包含多条消息
        messages = json.loads(decoded)
        # 确保是列表形式
        if not isinstance(messages, list):
            messages = [messages]

        for msg in messages:
            await process_message(msg)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}, 原始数据: {decoded[:100]}")
    except Exception as e:
        logger.error(f"消息处理失败: {e}")


async def process_message(msg: dict):
    """处理具体消息内容"""
    cmd = msg.get('cmd', '')
    if cmd == 'INTERACT_WORD_V2':
        # 处理用户交互消息V2（包含进入直播间信息）
        await handle_interact_word_v2(msg)
    elif cmd == 'LOG_IN_NOTICE':
        # 未登录通知
        data = msg.get('data', {})
        logger.info(f"系统通知: {data.get('notice_msg', '')}")
    elif cmd.startswith('DANMU_MSG'):
        # 可以忽略弹幕消息，或根据需要处理
        pass
    # 可以添加其他需要处理的消息类型


async def handle_interact_word_v2(msg: dict):
    """处理用户进入直播间等交互信息"""
    data = msg.get('data', {})
    pb_data = data.get('pb', '')

    if not pb_data:
        return

    try:
        # 这里需要protobuf解析，示例中简化处理
        # 实际使用时需要:
        # 1. 从base64解码
        # pb_bytes = base64.b64decode(pb_data)
        # 2. 使用对应的proto文件解析
        # 参考文档中的#1332(comment)获取proto定义

        # 简化示例 - 实际需要根据protobuf解析结果提取
        logger.info(f"检测到用户交互行为: {msg}")

        # 以下是解析后的信息提取示例（实际需要根据protobuf结构调整）
        # user_info = parse_interact_proto(pb_bytes)
        # logger.info(f"用户进入直播间: {user_info.get('uname')} (UID: {user_info.get('uid')})")

    except Exception as e:
        logger.error(f"解析用户交互信息失败: {e}")


async def connect():
    """建立连接并处理消息"""
    uri = "wss://broadcastlv.chat.bilibili.com:443/sub"
    while True:
        try:
            async with websockets.connect(uri) as websocket:
                logger.info("已连接到服务器")

                # 发送认证包
                auth_data = {
                    "uid": UID,
                    "roomid": ROOM_ID,
                    "protover": 3,
                    "platform": "web",
                    "type": 2
                }

                auth_success = await send_packet(websocket, json.dumps(auth_data), OP_AUTH)
                if not auth_success:
                    logger.error("认证包发送失败，将重试连接")
                    await asyncio.sleep(RECONNECT_DELAY)
                    continue

                # 启动心跳任务
                heartbeat_task = asyncio.create_task(heartbeat(websocket))

                # 接收消息循环
                try:
                    while True:
                        data = await websocket.recv()
                        if not data:
                            continue

                        # 解析数据包
                        offset = 0
                        while offset < len(data):
                            # 解析头部
                            header = data[offset:offset + 16]
                            if len(header) < 16:
                                break

                            total_len, header_len, ver, op, seq = struct.unpack('>I2H2I', header)

                            # 提取完整包
                            packet_end = offset + total_len
                            body = data[offset + header_len:packet_end]

                            # 处理不同操作码
                            if op == OP_MESSAGE:
                                await handle_message(body, ver)
                            elif op == OP_AUTH_REPLY:
                                # 认证回复
                                auth_result = decode_data(body, ver)
                                logger.info(f"认证结果: {auth_result}")
                            elif op == OP_HEARTBEAT_REPLY:
                                # 心跳回复，包含人气值
                                popularity = struct.unpack('>I', body[:4])[0]
                                logger.debug(f"当前房间人气值: {popularity}")

                            offset = packet_end

                except websockets.exceptions.ConnectionClosed:
                    logger.warning("连接已关闭，将尝试重连")
                except Exception as e:
                    logger.error(f"消息处理出错: {e}")
                finally:
                    # 取消心跳任务
                    heartbeat_task.cancel()
                    await heartbeat_task

        except Exception as e:
            logger.error(f"连接出错: {e}")

        # 重连延迟
        logger.info(f"{RECONNECT_DELAY}秒后尝试重连...")
        await asyncio.sleep(RECONNECT_DELAY)


if __name__ == "__main__":
    try:
        # 使用现代asyncio写法，避免事件循环警告
        asyncio.run(connect())
    except KeyboardInterrupt:
        logger.info("程序已手动终止")
    except Exception as e:
        logger.critical(f"程序崩溃: {e}", exc_info=True)
