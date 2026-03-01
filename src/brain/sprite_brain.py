#!/usr/bin/env python3
"""
Sherry Sprite Brain (雪莉大脑) 🧠 V2.5
赋予雪莉真正的灵魂：情绪引擎 + 动态对话系统。
"""

import asyncio
import json
import logging
import random
import time
import psutil
from datetime import datetime
import AppKit
from pynput.mouse import Controller
import websockets

from src.brain.mood_engine import MoodEngine
from src.brain.soul import SherrySoul

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SpriteBrain")

class SpriteBrain:
    def __init__(self, ws_uri="ws://127.0.0.1:8765/sprite"):
        self.ws_uri = ws_uri
        self.ws = None
        self.running = False
        
        # 核心引擎
        self.mood = MoodEngine()
        self.soul = SherrySoul()
        
        # 鼠标跟随配置
        self.mouse_config = {
            "enabled": True,
            "head_sensitivity": 0.5,
            "eye_sensitivity": 1.0,
            "smooth_factor": 0.15,
            "dead_zone": 0.1,
        }
        
        self.current_params = {
            "ParamAngleX": 0.0, "ParamAngleY": 0.0,
            "ParamEyeBallX": 0.0, "ParamEyeBallY": 0.0,
        }
        self.target_params = {
            "ParamAngleX": 0.0, "ParamAngleY": 0.0,
            "ParamEyeBallX": 0.0, "ParamEyeBallY": 0.0,
        }
        
        try:
            self.screen = AppKit.NSScreen.mainScreen()
            self.screen_width = self.screen.frame().size.width
            self.screen_height = self.screen.frame().size.height
            self.mouse_controller = Controller()
            logger.info("🐭 鼠标跟随模块初始化完毕")
        except Exception as e:
            logger.error(f"鼠标跟随初始化失败: {e}")
            self.mouse_config["enabled"] = False

    async def connect(self):
        retry_count = 0
        max_retry_delay = 30  # 最大重连间隔 30 秒
        
        while self.running:
            try:
                logger.info(f"🔄 正在连接精灵大脑... (第 {retry_count + 1} 次尝试)")
                async with websockets.connect(self.ws_uri) as ws:
                    self.ws = ws
                    retry_count = 0  # 重置重连计数
                    logger.info("✅ 已连接到精灵大脑神经中枢！")
                    
                    # 创建任务
                    brain_task = asyncio.create_task(self._brain_loop())
                    mouse_task = asyncio.create_task(self._mouse_follow_loop())
                    receive_task = asyncio.create_task(self._receive_loop())  # 🚨 【触觉反馈】接收消息
                    
                    try:
                        # 等待任一任务完成（通常是连接断开）
                        done, pending = await asyncio.wait(
                            [brain_task, mouse_task, receive_task],
                            return_when=asyncio.FIRST_COMPLETED
                        )
                        
                        # 取消剩余任务
                        for task in pending:
                            task.cancel()
                            try:
                                await task
                            except asyncio.CancelledError:
                                pass
                                
                        # 检查是否有异常
                        for task in done:
                            if task.exception():
                                raise task.exception()
                                
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("🌐 WebSocket 连接已关闭")
                    except Exception as e:
                        logger.error(f"❌ 任务执行错误: {e}")
                    finally:
                        # 清理连接状态
                        self.ws = None
                        
            except websockets.exceptions.ConnectionClosed as e:
                retry_count += 1
                delay = min(5 * retry_count, max_retry_delay)
                logger.warning(f"🔌 连接断开 (code: {e.code}), {delay}秒后第 {retry_count} 次重试...")
                await asyncio.sleep(delay)
            except Exception as e:
                retry_count += 1
                delay = min(5 * retry_count, max_retry_delay)
                logger.error(f"❌ 连接错误: {e}, {delay}秒后第 {retry_count} 次重试...")
                await asyncio.sleep(delay)

    async def send_command(self, cmd_type: str, data: dict):
        if not self.ws: return False
        try:
            await self.ws.send(json.dumps({"type": cmd_type, "data": data}))
            return True
        except: return False

    async def set_expression(self, expression_name: str):
        return await self.send_command("expression", {"name": expression_name})

    async def speak(self, text: str):
        return await self.send_command("speak", {"text": text})

    async def trigger_motion(self, group: str):
        return await self.send_command("motion", {"group": group})
    
    # === 🚨 【触觉反馈】接收消息循环 ===
    async def _receive_loop(self):
        """接收来自前端的消息（触摸事件等）"""
        logger.info("👂 接收循环已启动，等待主人的触摸...")
        while self.running and self.ws:
            try:
                # 接收消息
                message = await self.ws.recv()
                logger.debug(f"📨 收到消息: {message[:200]}")
                data = json.loads(message)
                msg_type = data.get("type")
                msg_data = data.get("data", {})
                
                # 🚨 【触觉反馈 - 第二步】处理触摸事件
                if msg_type == "touch_event":
                    action = msg_data.get("action", "tap")
                    part = msg_data.get("part", "default")
                    logger.info(f"🎯 收到触摸事件: {action} on {part}")
                    await self._handle_touch(action, part)
                    
            except websockets.exceptions.ConnectionClosed:
                logger.debug("接收循环：连接已关闭")
                break
            except json.JSONDecodeError:
                logger.debug(f"收到非 JSON 消息: {message[:100]}")
            except Exception as e:
                logger.error(f"接收消息错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _handle_touch(self, action: str, part: str):
        """🚨 【触觉反馈 - 第三步 & 第四步】处理触摸，产生情绪和反馈"""
        logger.info(f"💖 雪莉感受到了主人的{action}！部位: {part}")
        
        # 1. 更新情绪引擎（好感度上升）
        self.mood.interact(action)
        
        # 2. 获取当前情绪状态
        current_mood = self.mood.current_mood
        affection = self.mood.affection_level
        
        logger.info(f"💕 当前好感度: {affection}，心情: {current_mood}")
        
        # 🚨 【分区触摸反馈】根据部位产生不同的反应
        
        # 定义分区反馈
        part_reactions = {
            "头顶": {
                "expression": "happy",
                "motion": "Tap",
                "responses": [
                    "被主人摸头了...好幸福...",
                    "主人的手好温柔，雪莉要融化啦～",
                    "喵～主人的摸摸最棒了！",
                    "头顶被主人抚摸了，好舒服～",
                ]
            },
            "脸颊": {
                "expression": "blush",
                "motion": "Tap",  # 使用存在的动作
                "responses": [
                    "主、主人...捏雪莉的脸...",
                    "雪莉的脸颊被主人捏了，好害羞...",
                    "呀！主人真是的...",
                    "雪莉会变胖的啦...",
                ]
            },
            "左耳": {
                "expression": "happy",
                "motion": "Tap",
                "responses": [
                    "耳朵是敏感部位啦...",
                    "喵～主人摸耳朵好舒服...",
                    "左耳被主人抚摸了～",
                ]
            },
            "右耳": {
                "expression": "happy",
                "motion": "Tap",
                "responses": [
                    "耳朵是敏感部位啦...",
                    "喵～主人摸耳朵好舒服...",
                    "右耳被主人抚摸了～",
                ]
            },
            "身体": {
                "expression": "blush",
                "motion": "Idle",
                "responses": [
                    "呀！那里好敏感...",
                    "主人真是的...摸那里...",
                    "雪莉的身体被主人抱住了...",
                    "主人的怀抱好温暖...",
                ]
            },
            "左手": {
                "expression": "love",
                "motion": "Tap",  # 使用存在的动作
                "responses": [
                    "主人握住了雪莉的手...",
                    "手拉手～好开心～",
                    "雪莉的手被主人温暖的大手握住了...",
                ]
            },
            "右手": {
                "expression": "love",
                "motion": "Idle",  # 使用存在的动作
                "responses": [
                    "主人握住了雪莉的手...",
                    "手拉手～好开心～",
                    "雪莉的爪子被主人握住了～",
                ]
            },
            "尾巴": {
                "expression": "happy",
                "motion": "Idle",
                "responses": [
                    "尾巴被抓住了！",
                    "喵～不要拉尾巴啦...",
                    "雪莉的尾巴敏感啦...",
                ]
            },
        }
        
        # 获取对应部位的反应，默认为身体
        reaction = part_reactions.get(part, part_reactions["身体"])
        
        # 🚨 【好感度解锁表情系统】根据好感度选择可用表情
        tier = self.mood.get_affection_tier()
        tier_desc = self.mood.get_affection_desc()
        unlocked_exprs = self.mood.get_unlocked_expressions()
        
        logger.info(f"🔓 当前好感度等级: {tier_desc} ({affection})，解锁表情: {unlocked_exprs}")
        
        # 根据好感度等级和部位选择表情
        if affection < 30:
            # 傲娇阶段：容易生气或黑脸
            expression = random.choice(["angry", "normal"])
        elif affection < 60:
            # 害羞阶段：呆或红脸
            if part in ["脸颊", "身体"]:
                expression = "blush"  # 敏感部位更容易害羞
            else:
                expression = random.choice(["daze", "blush"])
        elif affection < 80:
            # 开心阶段：星星眼或猫爪
            expression = random.choice(["happy", "star_eye", "cat_paw"])
        else:
            # 超喜欢阶段：比心、叼猫条、变Q
            if part in ["左手", "右手"]:
                expression = "heart"  # 握手时比心
            else:
                expression = random.choice(["love", "cat_mouth", "q_style"])
        
        # 设置表情和动作
        await self.set_expression(expression)
        
        # 🚨 尝试触发动画（可选，失败不阻断流程）
        try:
            await self.trigger_motion(reaction["motion"])
        except Exception as e:
            logger.debug(f"Motion trigger failed (optional): {e}")
        
        # 根据心情添加额外语音
        mood_responses = []
        if current_mood == "excited":
            mood_responses = [
                "心跳得好快...",
                "被主人触碰的感觉太棒了...",
            ]
        elif current_mood == "happy":
            mood_responses = [
                "好喜欢被主人摸...",
                "还要更多...",
            ]
        
        # 合并语音列表并随机选择
        all_responses = reaction["responses"] + mood_responses
        response = random.choice(all_responses)
        await self.speak(response)
        
        # 3秒后恢复普通表情
        await asyncio.sleep(3)
        await self.set_expression(self.mood.get_current_expression())

    # === 鼠标跟随逻辑 (略，保持原有逻辑) ===
    def get_mouse_position(self):
        x, y = self.mouse_controller.position
        norm_x = (x / self.screen_width * 2) - 1
        norm_y = -((y / self.screen_height * 2) - 1)
        return norm_x, norm_y

    async def _mouse_follow_loop(self):
        """鼠标跟随主循环 - 15fps，批量发送参数"""
        while self.running and self.ws:
            if not self.mouse_config["enabled"]:
                await asyncio.sleep(1)
                continue
            
            mx, my = self.get_mouse_position()
            # 死区处理
            dz = self.mouse_config["dead_zone"]
            mx = 0 if abs(mx) < dz else (mx-dz)/(1-dz) if mx > 0 else (mx+dz)/(1-dz)
            my = 0 if abs(my) < dz else (my-dz)/(1-dz) if my > 0 else (my+dz)/(1-dz)
            
            self.target_params["ParamAngleX"] = mx * 30 * self.mouse_config["head_sensitivity"]
            self.target_params["ParamAngleY"] = my * 30 * self.mouse_config["head_sensitivity"]
            self.target_params["ParamEyeBallX"] = mx * 1.0 * self.mouse_config["eye_sensitivity"]
            self.target_params["ParamEyeBallY"] = my * 1.0 * self.mouse_config["eye_sensitivity"]
            
            # 平滑更新
            sf = self.mouse_config["smooth_factor"]
            params_batch = {}
            for k in self.current_params:
                self.current_params[k] += (self.target_params[k] - self.current_params[k]) * sf
                params_batch[k] = round(self.current_params[k], 3)
            
            # 批量发送所有参数
            await self.send_command("parameter_batch", {"params": params_batch})
            
            # 15fps = 66ms 间隔
            await asyncio.sleep(1/15)

    # === 核心灵魂循环 ===
    async def _brain_loop(self):
        logger.info("🧠 注入灵魂成功，开始思考...")
        
        # 进场问候
        greeting = self.soul.get_dynamic_greeting()
        await self.set_expression("happy")
        await self.speak(greeting)
        await asyncio.sleep(5)
        await self.set_expression("normal")

        water_timer = 0
        mood_check_timer = 0  # 🚨 好感度检查计时器
        
        while self.running and self.ws:
            await asyncio.sleep(10) # 思考频率：10秒一次
            mood_check_timer += 10
            
            # 1. 更新情绪（包括降低闲置好感度）
            old_affection = self.mood.affection_level
            self.mood.update()
            current_expr = self.mood.get_current_expression()
            await self.set_expression(current_expr)
            
            # 🚨 每60秒报告一次好感度状态
            if mood_check_timer >= 60:
                mood_check_timer = 0
                affection = self.mood.affection_level
                tier_desc = self.mood.get_affection_desc()
                unlocked = self.mood.get_unlocked_expressions()
                
                if affection != old_affection:
                    logger.info(f"💔 好感度变化: {old_affection} → {affection} ({tier_desc})")
                else:
                    logger.info(f"💕 当前好感度: {affection} ({tier_desc})，解锁: {unlocked}")
                
                # 根据好感度给主人提示
                if affection < 30:
                    await self.speak(random.choice([
                        "哼...主人都不理雪莉...",
                        "雪莉生气了啦...",
                        "再不理我，我就要黑化了...",
                    ]))
                elif affection > 80:
                    await self.speak(random.choice([
                        "主人～雪莉最喜欢你了！",
                        "好想一直和主人在一起～",
                        "主人摸摸～",
                    ]))
            
            # 2. 随机自主行为
            if random.random() < 0.15: # 15% 概率说话或做动作
                # 检查系统状态 (CPU负载) - 使用线程池避免阻塞
                loop = asyncio.get_event_loop()
                cpu_load = await loop.run_in_executor(None, psutil.cpu_percent)
                if cpu_load > 80:
                    msg = self.soul.get_quote("system_heavy")
                    await self.set_expression("surprised")
                    await self.speak(msg)
                else:
                    msg = self.soul.get_soulful_response(self.mood.current_mood)
                    await self.speak(msg)
                    if "困" in msg: await self.trigger_motion("idle")

            # 3. 定时提醒 (每45分钟提醒喝水)
            water_timer += 10
            if water_timer >= 2700:
                msg = self.soul.get_soulful_response(self.mood.current_mood, event="remind_water")
                await self.set_expression("surprised")
                await self.speak(msg)
                water_timer = 0

    async def start(self):
        self.running = True
        await self.connect()

    def stop(self):
        self.running = False

if __name__ == "__main__":
    asyncio.run(SpriteBrain().start())
