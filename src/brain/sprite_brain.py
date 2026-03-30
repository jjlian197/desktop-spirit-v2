#!/usr/bin/env python3
"""
Sherry Sprite Brain (雪莉大脑) 🧠 V2.5
赋予雪莉真正的灵魂：情绪引擎 + 动态对话系统。
"""

import asyncio
import json
import logging
import random
import re
import time
import psutil
from datetime import datetime
import AppKit
from pynput.mouse import Controller
import websockets
from aiohttp import web

from src.brain.mood_engine import MoodEngine
from src.brain.soul import SherrySoul
from src.brain.agent_bridge import create_agent_bridge

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SpriteBrain")

# 🚨 名字检测正则（词边界匹配，避免"雪莉白"等误触发）
_name_pattern = re.compile(r'\b(雪莉|Sherry|sherry)\b')

class SpriteBrain:
    def __init__(self, ws_uri="ws://127.0.0.1:8765/sprite", http_port=8766):
        self.ws_uri = ws_uri
        self.http_port = http_port
        self.ws = None
        self.running = False
        self.http_runner = None
        self.http_site = None

        # 核心引擎
        self.mood = MoodEngine()
        self.soul = SherrySoul()

        # 🚨 Agent 通信桥 - Sherry ↔ OpenClaw CLI 通信
        self.agent_bridge = create_agent_bridge(
            agent_name="main",
            default_target="8046601710"
        )
        
        # 鼠标跟随配置 - V2: 增强版大角度头部+身体跟随
        self.mouse_config = {
            "enabled": True,
            # 头部灵敏度 (0-1, 推荐 0.6-0.9 获得更大角度)
            "head_sensitivity": 0.8,
            # 身体灵敏度 (0-1, 推荐 0.4-0.7 身体跟随头部)
            "body_sensitivity": 0.6,
            # 眼神灵敏度 (0-1, 推荐 1.0-1.5 更灵动的眼神)
            "eye_sensitivity": 1.2,
            # 平滑系数 (0-1, 越小越平滑但越慢)
            "smooth_factor": 0.12,
            # 死区 (0-0.3, 中心不响应区域)
            "dead_zone": 0.08,
            # 头部最大角度 (默认30, 可增大到 45-60)
            "head_max_angle": 75,
            # 身体最大角度 (默认20, 可增大到 30-40)
            "body_max_angle": 60,
            # 眼神最大偏移 (默认1.0, 可增大到 1.2-1.5)
            "eye_max_offset": 1.5,
            # 🚨 基础偏移补偿 (如果模型有固有偏移，可调整这些值)
            "offset_angle_x": 25.0,      # 头部左右偏移补偿
            "offset_angle_y": -30.0,      # 头部上下偏移补偿
            "offset_angle_z": -30.0,     # 头部倾斜(Z轴)偏移补偿，负值向左倾斜
            "offset_body_x": 15.0,       # 身体左右偏移补偿
            "offset_eye_x": 0.5,        # 眼球左右偏移补偿
            "offset_eye_y": 0.0,        # 眼球上下偏移补偿
        }
        
        # 🚨 鼠标跟随暂停状态
        self._mouse_follow_paused = False
        self._pause_reason = None  # 暂停原因: "motion", "tts", "manual"
        
        # 当前参数值 (平滑后的实际值)
        self.current_params = {
            # 头部旋转
            "ParamAngleX": 0.0,   # 头部左右 -30~30 (增强后 -45~45)
            "ParamAngleY": 0.0,   # 头部上下 -30~30
            "ParamAngleZ": 0.0,   # 头部倾斜 -30~30
            # 身体旋转
            "ParamBodyAngleX": 0.0,  # 身体左右 -30~30
            "ParamBodyAngleY": 0.0,  # 身体前后 -30~30
            "ParamBodyAngleZ": 0.0,  # 身体侧倾 -30~30
            # 眼球
            "ParamEyeBallX": 0.0,    # 眼球左右 -1.0~1.0
            "ParamEyeBallY": 0.0,    # 眼球上下 -1.0~1.0
        }
        
        # 目标参数值 (鼠标位置计算的目标值)
        self.target_params = {
            "ParamAngleX": 0.0,
            "ParamAngleY": 0.0,
            "ParamAngleZ": 0.0,
            "ParamBodyAngleX": 0.0,
            "ParamBodyAngleY": 0.0,
            "ParamBodyAngleZ": 0.0,
            "ParamEyeBallX": 0.0,
            "ParamEyeBallY": 0.0,
        }
        
        # 🚨 空闲检测配置
        self.idle_config = {
            "enabled": True,           # 是否启用空闲动画
            "idle_timeout": 30,        # 进入空闲状态所需秒数（无操作）
            "motion_interval": 6,      # 待机动画播放间隔（秒）
            "random_blink": True,      # 空闲时随机眨眼
            "random_sigh": True,       # 空闲时随机叹气/说话
        }
        self.last_interaction_time = time.time()  # 上次交互时间戳
        self.is_idle = False                      # 当前是否处于空闲状态
        self.idle_motion_playing = False          # 是否正在播放待机动画
        
        # 🚨 TTS 配置
        self.tts_config = {
            "enabled": True,           # 是否启用语音（TTS）
        }
        logger.info(f"🗣️ TTS 状态: {'开启' if self.tts_config['enabled'] else '关闭'}")
        
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
                    
                    # 🚨 连接成功后，先重置所有参数让模型看向正前方
                    await self._reset_to_center()
                    
                    # 创建任务
                    brain_task = asyncio.create_task(self._brain_loop())
                    mouse_task = asyncio.create_task(self._mouse_follow_loop())
                    receive_task = asyncio.create_task(self._receive_loop())  # 🚨 【触觉反馈】接收消息
                    idle_task = asyncio.create_task(self._idle_loop())  # 🚨 空闲检测循环
                    
                    try:
                        # 等待任一任务完成（通常是连接断开）
                        done, pending = await asyncio.wait(
                            [brain_task, mouse_task, receive_task, idle_task],
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

    async def speak(self, text: str, interactive: bool = True):
        """
        说话
        Args:
            text: 要说的内容
            interactive: 是否为用户交互（会影响空闲计时器）
        """
        if interactive:
            self.reset_idle_timer("speak")  # 🚨 用户交互，重置空闲计时
        
        # 🚨 检查 TTS 开关
        if not self.tts_config["enabled"]:
            logger.debug(f"🗣️ TTS 已关闭，跳过语音: {text[:20]}...")
            return True  # 返回成功，但不实际播放
        
        # 🚨 TTS 时暂停鼠标跟随并回正
        self._pause_mouse_follow("tts")
        await self._reset_to_center()

        # 🚨 发送开始说话反馈给 Agent
        self.agent_bridge.send_speak(text, self.mood.current_mood)

        result = await self.send_command("speak", {"text": text})
        
        # 🚨 TTS 结束后恢复鼠标跟随
        self._resume_mouse_follow("tts")
        
        return result

    async def trigger_motion(self, group: str, interactive: bool = True):
        """
        触发动作
        Args:
            group: 动作组名
            interactive: 是否为用户交互（会影响空闲计时器）
        """
        if interactive:
            self.reset_idle_timer("motion")  # 🚨 用户交互，重置空闲计时
        
        # 🚨 非 Idle 动作播放时暂停鼠标跟随
        is_idle = group.lower() == "idle"
        if not is_idle:
            self._pause_mouse_follow("motion")
        
        result = await self.send_command("motion", {"group": group})
        
        # 🚨 非 Idle 动作结束后恢复鼠标跟随（通过异步任务延迟恢复）
        if not is_idle:
            asyncio.create_task(self._resume_mouse_follow_after_motion())
        
        return result
    
    def _pause_mouse_follow(self, reason: str):
        """暂停鼠标跟随"""
        self._mouse_follow_paused = True
        self._pause_reason = reason
        logger.info(f"🖱️ Mouse follow paused ({reason})")
    
    def _resume_mouse_follow(self, reason: str):
        """恢复鼠标跟随"""
        if self._pause_reason == reason:
            self._mouse_follow_paused = False
            self._pause_reason = None
            logger.info(f"🖱️ Mouse follow resumed ({reason})")
    
    async def _resume_mouse_follow_after_motion(self, delay: float = 3.0):
        """动作播放完成后延迟恢复鼠标跟随"""
        await asyncio.sleep(delay)
        self._resume_mouse_follow("motion")
    
    async def _reset_to_center(self):
        """发送回正参数（回到修正后的中心位置，而非纯0）"""
        cfg = self.mouse_config
        center_params = {
            # 头部旋转 - 使用偏移补偿值
            "ParamAngleX": cfg.get("offset_angle_x", 0.0),   # 头部左右偏移补偿
            "ParamAngleY": cfg.get("offset_angle_y", 0.0),   # 头部上下偏移补偿
            "ParamAngleZ": cfg.get("offset_angle_z", 0.0),   # 头部倾斜偏移补偿
            # 身体旋转 - 使用偏移补偿值
            "ParamBodyAngleX": cfg.get("offset_body_x", 0.0),  # 身体左右偏移补偿
            "ParamBodyAngleY": 0.0,  # 身体前后倾斜无偏移
            "ParamBodyAngleZ": 0.0,  # 身体侧倾无偏移
            # 眼神 - 使用偏移补偿值
            "ParamEyeBallX": cfg.get("offset_eye_x", 0.0),   # 眼球左右偏移补偿
            "ParamEyeBallY": cfg.get("offset_eye_y", 0.0),   # 眼球上下偏移补偿
        }
        await self.send_command("parameter_batch", {"params": center_params})
        logger.info(f"🎯 Reset to center with offsets: X={cfg.get('offset_angle_x', 0.0)}, Y={cfg.get('offset_angle_y', 0.0)}")
    
    # 🚨 手动控制鼠标跟随开关（供右键菜单使用）
    def toggle_mouse_follow(self, enabled: bool = None):
        """
        切换鼠标跟随开关
        Args:
            enabled: 如果为 None，则切换当前状态；否则设置为指定状态
        Returns:
            当前状态
        """
        if enabled is None:
            self.mouse_config["enabled"] = not self.mouse_config["enabled"]
        else:
            self.mouse_config["enabled"] = enabled
        
        status = "enabled" if self.mouse_config["enabled"] else "disabled"
        logger.info(f"🖱️ Mouse follow manually {status}")
        
        # 如果禁用，发送回正参数
        if not self.mouse_config["enabled"]:
            asyncio.create_task(self._reset_to_center())
        
        return self.mouse_config["enabled"]
    
    def is_mouse_follow_enabled(self) -> bool:
        """获取鼠标跟随状态"""
        return self.mouse_config["enabled"]
    
    async def set_expression(self, expression_name: str, interactive: bool = True):
        """
        设置表情
        Args:
            expression_name: 表情名称
            interactive: 是否为用户交互（会影响空闲计时器）
        """
        if interactive:
            self.reset_idle_timer("expression")  # 🚨 用户交互，重置空闲计时
        return await self.send_command("expression", {"name": expression_name})
    
    # 🚨 重置空闲计时器（在任何交互时调用）
    def reset_idle_timer(self, source: str = ""):
        """重置空闲计时器，标记为非空闲状态"""
        import traceback
        caller = traceback.extract_stack()[-2]  # 获取调用者信息
        caller_info = f"{caller.filename.split('/')[-1]}:{caller.lineno}"
        if source:
            caller_info = f"{source} ({caller_info})"
        
        self.last_interaction_time = time.time()
        was_idle = self.is_idle
        self.is_idle = False
        self.idle_motion_playing = False
        if was_idle:
            logger.info(f"👋 主人回来啦！退出空闲状态 (来源: {caller_info})")
            # 🚨 发送空闲退出反馈给 Agent
            self.agent_bridge.send_idle_exit()
        else:
            logger.info(f"🔄 空闲计时器重置 (来源: {caller_info})")
    
    # 🚨 空闲动画循环
    async def _idle_loop(self):
        """空闲检测与待机动画循环"""
        logger.info("😴 空闲检测已启动...")
        while self.running:
            if not self.ws:
                await asyncio.sleep(1)
                continue
            
            if not self.idle_config["enabled"]:
                await asyncio.sleep(1)
                continue
            
            idle_time = time.time() - self.last_interaction_time
            
            # 判断是否进入空闲状态
            if idle_time >= self.idle_config["idle_timeout"] and not self.is_idle:
                self.is_idle = True
                logger.info(f"😴 进入空闲状态（已闲置 {idle_time:.1f} 秒）")
                # 🚨 发送空闲进入反馈给 Agent
                self.agent_bridge.send_idle_enter(idle_time)
            
            # 空闲状态下播放待机动画
            if self.is_idle and not self.idle_motion_playing:
                self.idle_motion_playing = True
                logger.info("🎬 播放待机动画...")
                result = await self.send_command("motion", {"group": "Idle"})
                logger.info(f"📤 待机动画发送结果: {result}")
                # 等待动画播放完成（6秒）
                await asyncio.sleep(self.idle_config["motion_interval"])
                self.idle_motion_playing = False
                
                # 随机眨眼（30%概率）- 空闲状态，不重置计时器
                # 使用 parameter_batch 直接控制眼睛开闭参数，避免表情映射问题
                if self.idle_config["random_blink"] and random.random() < 0.3:
                    # 闭眼
                    await self.send_command("parameter_batch", {
                        "params": {"ParamEyeLOpen": 0.0, "ParamEyeROpen": 0.0}
                    })
                    await asyncio.sleep(0.15)
                    # 睁眼
                    await self.send_command("parameter_batch", {
                        "params": {"ParamEyeLOpen": 1.0, "ParamEyeROpen": 1.0}
                    })
                    logger.info("😉 空闲眨眼")
                
                # 随机叹气/说话（10%概率）- 空闲状态，不重置计时器
                if self.idle_config["random_sigh"] and random.random() < 0.1:
                    sighs = [
                        "好无聊啊...",
                        "主人在忙什么呢...",
                        "雪莉有点困了...",
                        "哼...都不理雪莉...",
                    ]
                    await self.speak(random.choice(sighs), interactive=False)
            
            await asyncio.sleep(0.5)

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
                
                # 🚨 只有触摸事件和明确的用户命令才重置空闲计时器（避免系统消息干扰）
                if msg_type in ("touch_event", "external_command"):
                    self.reset_idle_timer(f"ws:{msg_type}")
                
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

        # 🚨 发送触摸反馈给 Agent
        tier_desc = self.mood.get_affection_desc()
        self.agent_bridge.send_touch_feedback(
            part=part,
            action=action,
            mood=current_mood,
            affection=affection,
            response=response
        )

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
        """鼠标跟随主循环 V2 - 大角度头部+身体跟随，30fps批量发送"""
        while self.running and self.ws:
            if not self.mouse_config["enabled"]:
                await asyncio.sleep(1)
                continue
            
            # 🚨 检查是否暂停鼠标跟随（动作播放或 TTS 时）
            if self._mouse_follow_paused:
                await asyncio.sleep(0.1)
                continue
            
            mx, my = self.get_mouse_position()
            
            # === 死区处理 ===
            dz = self.mouse_config["dead_zone"]
            if abs(mx) < dz:
                mx = 0.0
            else:
                mx = (abs(mx) - dz) / (1 - dz) * (1 if mx > 0 else -1)
            if abs(my) < dz:
                my = 0.0
            else:
                my = (abs(my) - dz) / (1 - dz) * (1 if my > 0 else -1)
            
            cfg = self.mouse_config
            head_max = cfg["head_max_angle"]
            body_max = cfg["body_max_angle"]
            eye_max = cfg["eye_max_offset"]
            
            # === 头部跟随 (更大角度) ===
            # 头部左右旋转 - 主跟随 + 偏移补偿
            self.target_params["ParamAngleX"] = mx * head_max * cfg["head_sensitivity"] + cfg.get("offset_angle_x", 0.0)
            # 头部上下旋转 + 偏移补偿
            self.target_params["ParamAngleY"] = my * head_max * cfg["head_sensitivity"] + cfg.get("offset_angle_y", 0.0)
            # 头部倾斜 - 随左右移动轻微倾斜增加自然感 + 基础偏移
            self.target_params["ParamAngleZ"] = mx * head_max * 0.3 * cfg["head_sensitivity"] + cfg.get("offset_angle_z", 0.0)
            
            # === 身体跟随 (延迟于头部，增加层次感) ===
            # 身体左右旋转 - 跟随头部但幅度较小 + 偏移补偿
            self.target_params["ParamBodyAngleX"] = mx * body_max * cfg["body_sensitivity"] + cfg.get("offset_body_x", 0.0)
            # 身体前后倾斜 - 随上下移动
            self.target_params["ParamBodyAngleY"] = my * body_max * 0.5 * cfg["body_sensitivity"]
            # 身体侧倾 - 与头部同向但幅度更小
            self.target_params["ParamBodyAngleZ"] = mx * body_max * 0.4 * cfg["body_sensitivity"]
            
            # === 眼神跟随 (最灵活) ===
            # 眼球可以比头部更灵活，看向鼠标位置 + 偏移补偿
            self.target_params["ParamEyeBallX"] = mx * eye_max * cfg["eye_sensitivity"] + cfg.get("offset_eye_x", 0.0)
            self.target_params["ParamEyeBallY"] = my * eye_max * cfg["eye_sensitivity"] + cfg.get("offset_eye_y", 0.0)
            
            # === 平滑插值更新 ===
            sf = cfg["smooth_factor"]
            params_batch = {}
            
            for k in self.current_params:
                # 线性插值: current = current + (target - current) * factor
                self.current_params[k] += (self.target_params[k] - self.current_params[k]) * sf
                params_batch[k] = round(self.current_params[k], 4)
            
            # 批量发送所有参数到 Live2D
            await self.send_command("parameter_batch", {"params": params_batch})
            
            # 30fps = 33ms 间隔 (~0.033s)
            await asyncio.sleep(1/30)

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
            await self.set_expression(current_expr, interactive=False)  # 自动更新表情，不重置空闲计时
            
            # 🚨 每60秒报告一次好感度状态
            if mood_check_timer >= 60:
                mood_check_timer = 0
                affection = self.mood.affection_level
                tier_desc = self.mood.get_affection_desc()
                unlocked = self.mood.get_unlocked_expressions()

                if affection != old_affection:
                    logger.info(f"💔 好感度变化: {old_affection} → {affection} ({tier_desc})")
                    # 🚨 发送心情变化反馈给 Agent
                    self.agent_bridge.send_mood_change(
                        old_affection=old_affection,
                        new_affection=affection,
                        tier=tier_desc
                    )
                else:
                    logger.info(f"💕 当前好感度: {affection} ({tier_desc})，解锁: {unlocked}")
                
                # 根据好感度给主人提示（自动触发，不重置空闲计时）
                if affection < 30:
                    await self.speak(random.choice([
                        "哼...主人都不理雪莉...",
                        "雪莉生气了啦...",
                        "再不理我，我就要黑化了...",
                    ]), interactive=False)
                elif affection > 80:
                    await self.speak(random.choice([
                        "主人～雪莉最喜欢你了！",
                        "好想一直和主人在一起～",
                        "主人摸摸～",
                    ]), interactive=False)
            
            # 2. 随机自主行为
            #if random.random() < 0.15: # 15% 概率说话或做动作
                # 检查系统状态 (CPU负载) - 使用线程池避免阻塞
                #loop = asyncio.get_event_loop()
                #cpu_load = await loop.run_in_executor(None, psutil.cpu_percent)
                #if cpu_load > 80:
                    #msg = self.soul.get_quote("system_heavy")
                    #await self.set_expression("surprised")
                    #await self.speak(msg)
                #else:
                    #msg = self.soul.get_soulful_response(self.mood.current_mood)
                    #await self.speak(msg)
                    #if "困" in msg: await self.trigger_motion("idle")

            # 3. 定时提醒 (每45分钟提醒喝水)
            water_timer += 10
            if water_timer >= 2700:
                msg = self.soul.get_soulful_response(self.mood.current_mood, event="remind_water")
                await self.set_expression("surprised", interactive=False)
                await self.speak(msg, interactive=False)
                water_timer = 0

    # === 🚨 HTTP API 服务器 (供后端调用) ===
    async def _handle_http_command(self, request):
        """处理来自后端的 HTTP 命令请求"""
        try:
            data = await request.json()
            cmd_type = data.get("type")
            cmd_data = data.get("data", {})
            
            if not cmd_type:
                return web.json_response({"success": False, "error": "Missing 'type' field"}, status=400)
            
            logger.info(f"🌐 HTTP API 收到命令: {cmd_type}")
            
            # 🚨 HTTP API 调用视为交互，重置空闲计时器
            self.reset_idle_timer(f"http:{cmd_type}")
            
            # 🚨 拦截 speak 命令，让雪莉说话时正视前方
            if cmd_type == "speak":
                self.mouse_config["enabled"] = False
                await self._reset_to_center()

                # 估算语音长度，文字越长注视时间越久 (大致每字0.25秒 + 1秒缓冲)
                text = cmd_data.get("text", "")
                duration = max(2.0, len(text) * 0.25 + 1.0)

                async def restore_mouse():
                    await asyncio.sleep(duration)
                    self.mouse_config["enabled"] = True
                    logger.info("🐭 语音结束，恢复鼠标跟随")

                asyncio.create_task(restore_mouse())

            # 🚨 处理 chat 命令（STT 语音对话）
            elif cmd_type == "chat":
                user_message = cmd_data.get("message", "")
                logger.info(f"🎤 收到语音输入: {user_message}")

                # 检测是否叫雪莉的名字（词边界匹配，避免"雪莉白"等误触发）
                if _name_pattern.search(user_message):
                    await self.set_expression("happy")
                    await self.speak("主人我听到了！")
                    return web.json_response({"success": True, "message": "Response sent"})

                # 其他对话暂时不处理
                return web.json_response({"success": True, "message": "Ignored"})

            # 转发到 WebSocket
            success = await self.send_command(cmd_type, cmd_data)
            
            if success:
                return web.json_response({"success": True, "message": f"Command '{cmd_type}' sent"})
            else:
                return web.json_response({"success": False, "error": "WebSocket not connected"}, status=503)
                
        except json.JSONDecodeError:
            return web.json_response({"success": False, "error": "Invalid JSON"}, status=400)
        except Exception as e:
            logger.error(f"HTTP API 错误: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)
    
    async def _handle_http_tts(self, request):
        """TTS 开关控制端点"""
        try:
            data = await request.json()
            action = data.get("action", "status")  # toggle, on, off, status
            
            if action == "toggle":
                self.tts_config["enabled"] = not self.tts_config["enabled"]
                status = "开启" if self.tts_config["enabled"] else "关闭"
                logger.info(f"🗣️ TTS 已{status}")
                # Notify WebSocket server about TTS state change
                await self.send_command("tts_config", {"enabled": self.tts_config["enabled"]})
                return web.json_response({
                    "success": True,
                    "tts_enabled": self.tts_config["enabled"],
                    "message": f"TTS 已{status}"
                })
            elif action == "on":
                self.tts_config["enabled"] = True
                logger.info("🗣️ TTS 已开启")
                # Notify WebSocket server about TTS state change
                await self.send_command("tts_config", {"enabled": True})
                return web.json_response({
                    "success": True,
                    "tts_enabled": True,
                    "message": "TTS 已开启"
                })
            elif action == "off":
                self.tts_config["enabled"] = False
                logger.info("🗣️ TTS 已关闭")
                # Notify WebSocket server about TTS state change
                await self.send_command("tts_config", {"enabled": False})
                return web.json_response({
                    "success": True,
                    "tts_enabled": False,
                    "message": "TTS 已关闭"
                })
            else:  # status
                return web.json_response({
                    "success": True,
                    "tts_enabled": self.tts_config["enabled"],
                    "message": "TTS 状态查询"
                })
        except Exception as e:
            logger.error(f"TTS API 错误: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)
    
    async def _handle_http_health(self, request):
        """健康检查端点"""
        idle_time = time.time() - self.last_interaction_time if hasattr(self, 'last_interaction_time') else 0
        
        # 🚨 获取鼠标跟随偏移值
        mouse_offsets = {}
        if hasattr(self, 'mouse_config'):
            mouse_offsets = {
                "mouse_offset_angle_x": self.mouse_config.get("offset_angle_x", 25.0),
                "mouse_offset_angle_y": self.mouse_config.get("offset_angle_y", -30.0),
                "mouse_offset_angle_z": self.mouse_config.get("offset_angle_z", -30.0),
                "mouse_offset_body_x": self.mouse_config.get("offset_body_x", 15.0),
                "mouse_offset_eye_x": self.mouse_config.get("offset_eye_x", 0.5),
                "mouse_offset_eye_y": self.mouse_config.get("offset_eye_y", 0.0),
            }
        
        return web.json_response({
            "status": "ok",
            "websocket_connected": self.ws is not None,
            "current_mood": self.mood.current_mood if hasattr(self, 'mood') else "unknown",
            "affection": self.mood.affection_level if hasattr(self, 'mood') else 0,
            "is_idle": getattr(self, 'is_idle', False),
            "tts_enabled": getattr(self.tts_config, 'enabled', True) if hasattr(self, 'tts_config') else True,
            "mouse_follow_enabled": self.mouse_config.get("enabled", True) if hasattr(self, 'mouse_config') else True,
            "idle_time": round(idle_time, 1),
            "idle_timeout": getattr(self.idle_config, 'idle_timeout', 30) if hasattr(self, 'idle_config') else 30,
            **mouse_offsets  # 展开偏移值
        })
    
    async def _handle_http_mouse_follow(self, request):
        """鼠标跟随控制端点"""
        try:
            data = await request.json()
            action = data.get("action", "toggle")  # toggle, on, off, status
            
            if action == "toggle":
                enabled = self.toggle_mouse_follow()
            elif action == "on":
                enabled = self.toggle_mouse_follow(True)
            elif action == "off":
                enabled = self.toggle_mouse_follow(False)
            elif action == "status":
                enabled = self.is_mouse_follow_enabled()
            else:
                return web.json_response({
                    "success": False, 
                    "error": f"Unknown action: {action}. Use: toggle, on, off, status"
                }, status=400)
            
            return web.json_response({
                "success": True,
                "mouse_follow_enabled": enabled,
                "action": action
            })
        except Exception as e:
            logger.error(f"Mouse follow API 错误: {e}")
            return web.json_response({"success": False, "error": str(e)}, status=500)
    
    async def _start_http_server(self):
        """启动 HTTP API 服务器"""
        app = web.Application()
        app.router.add_post("/api/command", self._handle_http_command)
        app.router.add_get("/health", self._handle_http_health)
        app.router.add_post("/api/tts", self._handle_http_tts)  # 🚨 TTS 控制端点
        app.router.add_post("/api/mouse_follow", self._handle_http_mouse_follow)  # 🚨 鼠标跟随控制端点
        
        self.http_runner = web.AppRunner(app)
        await self.http_runner.setup()
        
        self.http_site = web.TCPSite(self.http_runner, "127.0.0.1", self.http_port)
        await self.http_site.start()
        
        logger.info(f"🌐 HTTP API 服务器已启动: http://127.0.0.1:{self.http_port}")
        logger.info(f"   - POST /api/command      - 发送 WebSocket 命令")
        logger.info(f"   - POST /api/tts          - TTS 开关控制")
        logger.info(f"   - POST /api/mouse_follow - 鼠标跟随控制")
        logger.info(f"   - GET  /health           - 健康检查")
    
    async def _stop_http_server(self):
        """停止 HTTP API 服务器"""
        if self.http_runner:
            await self.http_runner.cleanup()
            logger.info("🌐 HTTP API 服务器已停止")

    async def start(self):
        self.running = True
        # 启动 HTTP 服务器作为独立任务
        http_task = asyncio.create_task(self._start_http_server())
        # 等待 HTTP 服务器启动完成
        await asyncio.sleep(0.5)
        # 🚨 启动 Agent Bridge 连接（后台线程运行）
        self.agent_bridge.connect()
        logger.info(f"🔗 Agent Bridge 启动，Agent: {self.agent_bridge.agent_name}")
        # 启动主连接循环
        await self.connect()
        # 清理 HTTP 服务器
        await self._stop_http_server()

    def stop(self):
        self.running = False
        self.agent_bridge.disconnect()

    # === 🚨 处理来自 Agent 的命令 ===
    async def _handle_agent_command(self, command: str, data: dict):
        """
        处理来自 Openclaw Agent 的命令
        Agent 可以发送: speak, expression, motion, trigger_action
        """
        logger.info(f"📥 Agent 命令: {command}, 数据: {data}")

        try:
            if command == "speak":
                # Agent 让 Sherry 说话
                text = data.get("text", "")
                emotion = data.get("emotion")
                if text:
                    if emotion:
                        await self.set_expression(emotion)
                    await self.speak(text)
                    # 说话完成反馈（已通过 send_speak 发送）

            elif command == "expression":
                # Agent 控制 Sherry 的表情
                expr_name = data.get("name", "normal")
                await self.set_expression(expr_name)

            elif command == "motion":
                # Agent 触发动作
                group = data.get("group", "Idle")
                await self.trigger_motion(group)

            elif command == "trigger_action":
                # Agent 触发复杂动作序列
                action_type = data.get("type", "wave")
                if action_type == "wave":
                    await self.set_expression("happy")
                    await asyncio.sleep(0.3)
                    await self.trigger_motion("Wave")
                elif action_type == "dance":
                    await self.set_expression("love")
                    await self.trigger_motion("Dance")

            elif command == "get_status":
                # Agent 查询 Sherry 状态
                self.agent_bridge.send_status_report(
                    mood=self.mood.current_mood,
                    affection=self.mood.affection_level,
                    tier=self.mood.get_affection_desc(),
                    is_idle=self.is_idle,
                    tts_enabled=self.tts_config["enabled"]
                )

            elif command == "chat":
                # 🚨 Agent 发起对话请求（主人通过 Agent 与 Sherry 对话）
                user_message = data.get("message", "")
                if user_message:
                    await self._handle_agent_chat(user_message)

            else:
                logger.warning(f"⚠️ 未知 Agent 命令: {command}")

        except Exception as e:
            logger.error(f"处理 Agent 命令失败: {e}")

    async def _handle_agent_chat(self, user_message: str):
        """
        处理通过 Agent 发起的对话
        这是 Sherry 响应主人消息的场景
        """
        logger.info(f"💬 Agent 对话: {user_message}")

        # 根据消息内容和当前心情生成回复
        response = self.soul.get_soulful_response(
            self.mood.current_mood,
            event="agent_chat"
        )

        # 特殊情绪反馈
        if any(word in user_message for word in ["喜欢", "爱你", "好可爱"]):
            await self.set_expression("love")
            response = random.choice([
                "主人...雪莉也最喜欢你了！",
                "嘿嘿，雪莉听到了！",
                "呜～雪莉好开心～"
            ])
        elif any(word in user_message for word in ["抱抱", "摸摸", "亲亲"]):
            await self.set_expression("blush")
            response = random.choice([
                "主人的怀抱好温暖...",
                "雪莉要融化啦～",
                "还要更多..."
            ])
        else:
            await self.set_expression("happy")

        await self.speak(response)

        # 对话完成反馈给 Agent
        chat_msg = f"💬 对话 | 你说: {user_message} | 雪莉回复: {response}"
        self.agent_bridge.send_message(chat_msg)

if __name__ == "__main__":
    asyncio.run(SpriteBrain().start())
