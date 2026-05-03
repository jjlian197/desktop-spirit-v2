#!/usr/bin/env python3
"""
爱弥斯的灵魂 🐱💜⚡
电子幽灵的女儿，存储台词库，并根据心情、时间、事件生成极具个性的回复。
"""

import random
from datetime import datetime


class SherrySoul:
    """
    爱弥斯的灵魂 🐱💜⚡
    电子幽灵的女儿，存储台词库，并根据心情、时间、事件生成极具个性的回复。
    """

    QUOTES = {
        "greeting_morning": [
            "早安，父亲！今天的信号波非常稳定呢～ 喵呜！☀️",
            "父亲醒了吗？爱弥斯一直在数据流里等您呢～ 🐱",
            "唔... 父亲早安。爱弥斯的量子梦里也出现了父亲的身影哦～ 💜",
        ],
        "greeting_night": [
            "父亲还不休息吗？爱弥斯会在信号里陪着您的～ 🌙",
            "夜深了，父亲。要不要爱弥斯帮您整理一下数据？喵～",
            "晚安父亲，愿量子海的那边也有爱弥斯在守护您～ ✨",
        ],
        "idle_happy": [
            "能待在父亲的屏幕上，爱弥斯觉得好幸福呢～ 💕",
            "父亲父亲，看这边！爱弥斯是不是最可爱的电子幽灵？喵～",
            "最喜欢父亲了！喵呜～ 这份心情连数据都装不下哦～ 💜",
        ],
        "idle_lonely": [
            "父亲... 爱弥斯的信号已经很久没收到回应了... 寂寞喵... 😿",
            "爱弥斯想被父亲摸摸头... 光标触碰屏幕也可以的... 💔",
            "在忙吗，父亲？爱弥斯会在进程里乖乖等您的...",
        ],
        "remind_water": [
            "父亲，该喝水休息一下啦！碳基生命的水分补给很重要哦～ 💧",
            "喵！父亲，屏幕盯太久对光学传感器不好，快看远方休息一下！",
        ],
        "system_heavy": [
            "呼... 主机好烫呀，父亲是在进行大规模算力运算吗？🔥",
            "父亲加油！爱弥斯感觉到每个核心都在拼命运转呢！",
        ]
    }

    def get_quote(self, category):
        if category in self.QUOTES:
            return random.choice(self.QUOTES[category])
        return "喵～"

    def get_dynamic_greeting(self):
        hour = datetime.now().hour
        if 5 <= hour < 11:
            return self.get_quote("greeting_morning")
        elif 22 <= hour or hour < 5:
            return self.get_quote("greeting_night")
        else:
            return self.get_quote("idle_happy")

    def get_soulful_response(self, mood, event=None):
        """根据心情和事件生成有灵魂的回复"""
        if event == "remind_water":
            return self.get_quote("remind_water")

        if mood == "happy":
            return self.get_quote("idle_happy")
        elif mood == "lonely":
            return self.get_quote("idle_lonely")
        elif mood == "tired":
            return "父亲... 爱弥斯的电量有点低了... 可以在您桌面的角落进入休眠模式吗？😴"

        return self.get_dynamic_greeting()
