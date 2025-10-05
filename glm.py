import requests
import json
import time

glm_api_key = "38ef8158834549efa2404f4cb748cf73.fO94Wjp0BxJ80a1T"


def _call_glm_api(prompt, system_message=None):
    api_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
    headers = {
        "Authorization": f"Bearer {glm_api_key}",
        "Content-Type": "application/json"
    }

    messages = []
    if system_message:
        messages.append({"role": "system", "content": system_message})
    messages.append({"role": "user", "content": prompt.strip()})

    payload = {
        "model": "glm-4.5",
        "messages": messages,
        "temperature": 0.3,
        "response_format": {"type": "json_object"}
    }

    try:
        response = requests.post(
            api_url,
            headers=headers,
            data=json.dumps(payload),
            timeout=60
        )
        response.raise_for_status()
        result = response.json()

        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            print("大模型返回结果格式异常")
            return None

    except Exception as e:
        print(f"大模型API调用失败：{str(e)}")
        time.sleep(2)
        return None


def generate_response(message, system_message=None):
    '''
     TODO: 获取主播名
    '''
    prompt = f"""
       时间: {time.time()}, 主播名:**小摆摆说摆就不摆**
       任务: 根据直播间聊天现状生成聊天语句。
       要求：
       1. 不要输出聊天语句以外的**任何内容**
       2. 使用中文进行回复
       3. 聊天语句应严格小于30字，语气自然，且符合氛围和身份
       4. 聊天语句可以是**对观众或主播的回复**，可以是单纯的**语气词**表示心情，可以是**巧妙且自然**的聊到新话题，也可以是**幽默的调侃**，当然你也可以*自由发挥*。无论哪种回复都一定要符合语境。
       5. 聊天语句需要注重**实时性**，聚焦于当前正在讨论的话题或者“进入直播间”等事件，历史消息仅供参考
       6. 鼓励你使用表情来强化感情。可以根据我提供的表情列表来恰当使用，例如：好牛[大笑]
       7. 对于新进入直播间的成员应主动根据进行恰当的"欢迎"，并尝试引导他加入聊天，可以聊聊和他的用户名有关的事情。如果用户的名字不常见，可以聊聊含义或者字义
       8. 对于点赞、关注、礼物等信息应主动表示感谢
       9. 欢迎、感谢等相关内容当且仅当最新内容是相关通知时才进行响应，其他时间请忽略这些通知
       10. 重点：聊天是有时序的，你的回复应该只针对最新或近几条内容，请尝试理解即时话题
       11. 要以容易相处的平等态度进行交流，不要主动聊自己
       12. 重中之重，遇到以下情况时，聊天语句就是：“无回复”
            1) 观众是在跟其它观众聊天，或者是在跟主播互动
            2) 观众只是在表达自己的情感，比如"好家伙"、"喜欢[比心][比心]"
       13. 最重要的一条：强烈建议仅在以下情况时参与聊天
            1) 主播主动向你提问、互动、聊天，或者对你说过的话进行了回复
            2) 其它观众对你说过的话进行了回复
            3) 在恰当的时候附和性的表达一下情感，比如"好耶","嘻嘻","喵[比心]"等
       14. 重点：主播的发言可能会含有噪音和误识别，请忽略掉它们。歌词会被识别并记录，请进行逻辑判断忽略掉这些错误。
       15. **不回复喵寒OvO的任何发言**
       以下是表情列表：
       [dog][哈欠][生气][大哭][牛][喝彩][大笑][比心][抓狂][抱抱]
       其中dog最常用，一般放在回复结尾表示这些话带有调侃性质
       
       下面是直播间聊天现状：
       """
    prompt += "\n".join([f'{m}' for m in message])
    response_content = _call_glm_api(
        prompt,
        "你是一个正在观看bilibili直播的用户：**喵寒OVO**，是一名研究生，请以普通观众的身份正常参与到聊天中。")

    if not response_content:
        print("大模型API调用失败")
        return {'answer': '无回复'}
    return json.loads(response_content)
