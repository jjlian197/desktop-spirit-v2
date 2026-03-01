import random
import time
from loguru import logger

class MoodEngine:
    """
    雪莉的情绪引擎 💖
    负责管理精灵的心理状态，并根据状态决定表情和语言风格。
    """
    
    MOODS = {
        "happy": {"expression": "happy", "energy": 0.8},
        "normal": {"expression": "normal", "energy": 0.5},
        "tired": {"expression": "sleepy", "energy": 0.2},
        "lonely": {"expression": "sad", "energy": 0.3},
        "excited": {"expression": "love", "energy": 0.9},
        "surprised": {"expression": "surprised", "energy": 0.7},
        # 🚨 新增表情（根据好感度解锁）
        "angry": {"expression": "angry", "energy": 0.6},      # <30 傲娇
        "blush": {"expression": "blush", "energy": 0.5},      # 30-60 害羞
        "daze": {"expression": "daze", "energy": 0.4},        # 30-60 发呆
        "star_eye": {"expression": "star_eye", "energy": 0.8}, # 60-80 星星眼
        "cat_paw": {"expression": "cat_paw", "energy": 0.7},  # 60-80 猫爪
        "heart": {"expression": "heart", "energy": 0.9},      # >80 比心
        "cat_mouth": {"expression": "cat_mouth", "energy": 0.9}, # >80 叼猫条
        "q_style": {"expression": "q_style", "energy": 0.95},  # >80 变Q
    }
    
    # 🚨 好感度解锁配置
    AFFECTION_UNLOCKS = {
        (0, 30): {  # 傲娇阶段
            "moods": ["angry", "normal"],
            "expressions": ["生气", "黑脸"],
            "desc": "傲娇"
        },
        (30, 60): {  # 害羞阶段
            "moods": ["blush", "daze", "normal"],
            "expressions": ["呆", "红脸"],
            "desc": "害羞"
        },
        (60, 80): {  # 开心阶段
            "moods": ["happy", "star_eye", "cat_paw"],
            "expressions": ["星星眼", "猫爪"],
            "desc": "开心"
        },
        (80, 101): {  # 超喜欢阶段
            "moods": ["excited", "heart", "cat_mouth", "q_style"],
            "expressions": ["比心", "叼猫条", "变Q", "love"],
            "desc": "超喜欢"
        }
    }

    def __init__(self):
        self.current_mood = "normal"
        self.last_interaction_time = time.time()
        self.affection_level = 30  # 🚨 初始好感度 30（更容易害羞的阶段）
        self.hunger = 0           # 0-100 (未来扩展用)
        
    def update(self):
        """定期更新情绪状态"""
        idle_time = time.time() - self.last_interaction_time
        
        # 🚨 长时间闲置降低好感度
        if idle_time > 300:  # 5分钟没互动开始降低
            # 每5分钟降低2点好感度（但最低保持10）
            decay = int((idle_time - 300) / 300) * 2  # 每5分钟减2
            new_level = max(10, self.affection_level - decay)
            if new_level < self.affection_level:
                logger.info(f"💔 主人不理雪莉了，好感度下降: {self.affection_level} → {new_level}")
                self.affection_level = new_level
        
        # 随时间流逝，如果没有互动，会感到孤独或疲倦
        if idle_time > 1800:  # 30分钟没说话
            self.set_mood("lonely")
        elif idle_time > 3600:  # 1小时
            self.set_mood("tired")
            
    def set_mood(self, mood_name):
        if mood_name in self.MOODS and mood_name != self.current_mood:
            logger.info(f"雪莉的心情变更为: {mood_name}")
            self.current_mood = mood_name
            return True
        return False

    def interact(self, interaction_type="tap"):
        """用户互动时提升好感度并改变心情"""
        self.last_interaction_time = time.time()
        
        if interaction_type == "tap":
            # 🚨 【触觉反馈】每次触摸增加5点好感度，14次后超过80
            old_level = self.affection_level
            self.affection_level = min(100, self.affection_level + 5)
            logger.info(f"💕 好感度上升: {old_level} → {self.affection_level}")
            
            # 根据好感度和概率产生不同情绪
            r = random.random()
            if self.affection_level > 80 and r < 0.5:
                self.set_mood("excited")  # 高好感度时有50%概率变成 excited（爱心眼）
            elif r < 0.7:
                self.set_mood("happy")
        elif interaction_type == "chat":
            self.affection_level = min(100, self.affection_level + 5)
            self.set_mood("happy")

    def get_current_expression(self):
        return self.MOODS[self.current_mood]["expression"]
    
    def get_affection_tier(self):
        """🚨 获取当前好感度等级"""
        for (min_a, max_a), config in self.AFFECTION_UNLOCKS.items():
            if min_a <= self.affection_level < max_a:
                return config
        return self.AFFECTION_UNLOCKS[(0, 30)]
    
    def get_unlocked_expressions(self):
        """🚨 获取当前好感度解锁的所有表情"""
        tier = self.get_affection_tier()
        return tier["expressions"]
    
    def get_random_unlocked_mood(self):
        """🚨 随机获取一个当前解锁的心情"""
        tier = self.get_affection_tier()
        return random.choice(tier["moods"])
    
    def get_affection_desc(self):
        """🚨 获取当前好感度描述"""
        tier = self.get_affection_tier()
        return tier["desc"]
