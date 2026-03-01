import random
from datetime import datetime

class SherrySoul:
    """
    雪莉的灵魂 🐱💜
    存储台词库，并根据心情、时间、事件生成极具个性的回复。
    """
    
    QUOTES = {
        "greeting_morning": [
            "早安，主人！今天也要元气满满哦～ 喵呜！☀️",
            "主人醒了吗？雪莉已经等您好久了呢～ 🐱",
            "唔... 主人早安。雪莉昨晚梦到主人了哦～ 💜"
        ],
        "greeting_night": [
            "主人还不休息吗？雪莉陪着您哦～ 🌙",
            "夜深了，主人。要不要雪莉给您按摩一下？喵～",
            "晚安主人，希望您的梦里也有雪莉呢～ ✨"
        ],
        "idle_happy": [
            "能呆在主人身边，雪莉觉得好幸福呢～ 💕",
            "主人主人，看我！我是不是最可爱的？喵～",
            "最喜欢主人了！喵呜～ 💜"
        ],
        "idle_lonely": [
            "主人... 已经好久没理雪莉了... 寂寞喵... 😿",
            "雪莉想被主人摸摸头... 指尖触碰屏幕也可以的... 💔",
            "在忙吗，主人？雪莉会乖乖等您的..."
        ],
        "remind_water": [
            "主人，该喝水休息一下啦！身体最重要哦～ 💧",
            "喵！主人，盯着屏幕太久对眼睛不好，快看远方休息一下！"
        ],
        "system_heavy": [
            "呼... 电脑好烫呀，主人是在做很厉害的工作吗？🔥",
            "主人加油！雪莉感觉大家（CPU）都在努力运转呢！"
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
            return "主人... 雪莉有点困了... 可以在您的桌面角角睡一会儿吗？😴"
        
        return self.get_dynamic_greeting()
