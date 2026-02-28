#!/usr/bin/env python3
"""
Sherry Sprite Brain (雪莉大脑) 🧠
用于赋予桌面精灵自主行为和智能交互能力，已融合鼠标跟随系统！
"""

import asyncio
import json
import logging
import random
import time
import websockets
import AppKit
from pynput.mouse import Controller

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
        
        # 鼠标跟随配置 (自然模式)
        self.mouse_config = {
            "enabled": True,
            "head_sensitivity": 0.5,    # 头部灵敏度50%
            "eye_sensitivity": 1.0,     # 眼神灵敏度100%
            "smooth_factor": 0.15,      # 平滑系数
            "dead_zone": 0.1,           # 中心死区10%
        }
        
        # 当前参数值
        self.current_params = {
            "ParamAngleX": 0.0,
            "ParamAngleY": 0.0,
            "ParamEyeBallX": 0.0,
            "ParamEyeBallY": 0.0,
        }
        
        # 目标参数值
        self.target_params = {
            "ParamAngleX": 0.0,
            "ParamAngleY": 0.0,
            "ParamEyeBallX": 0.0,
            "ParamEyeBallY": 0.0,
        }
        
        # 获取屏幕尺寸用于鼠标跟随
        try:
            self.screen = AppKit.NSScreen.mainScreen()
            self.screen_width = self.screen.frame().size.width
            self.screen_height = self.screen.frame().size.height
            self.mouse_controller = Controller()
            logger.info(f"鼠标跟随模块初始化完毕 (屏幕: {self.screen_width}x{self.screen_height})")
        except Exception as e:
            logger.error(f"鼠标跟随模块初始化失败: {e}")
            self.mouse_config["enabled"] = False

    async def connect(self):
        """连接到桌面精灵的 WebSocket 服务器"""
        while self.running:
            try:
                logger.info(f"正在连接到精灵: {self.ws_uri}")
                async with websockets.connect(self.ws_uri) as ws:
                    self.ws = ws
                    logger.info("✅ 已成功连接到精灵大脑神经中枢！")
                    
                    # 并发运行大脑主循环和鼠标跟随循环
                    brain_task = asyncio.create_task(self._brain_loop())
                    mouse_task = asyncio.create_task(self._mouse_follow_loop())
                    
                    await asyncio.gather(brain_task, mouse_task)
            except ConnectionRefusedError:
                logger.warning("无法连接到精灵，精灵可能未启动，5秒后重试...")
                await asyncio.sleep(5)
            except websockets.exceptions.ConnectionClosed:
                logger.warning("与精灵的连接已断开，准备重连...")
                await asyncio.sleep(3)
            except Exception as e:
                logger.error(f"连接发生未知错误: {e}")
                await asyncio.sleep(5)

    async def send_command(self, cmd_type: str, data: dict):
        """向精灵发送控制指令"""
        if not self.ws or not self.ws.open:
            return False
            
        try:
            payload = {
                "type": cmd_type,
                "data": data
            }
            await self.ws.send(json.dumps(payload))
            return True
        except Exception as e:
            # 忽略发送失败的日志，避免刷屏
            return False

    async def set_expression(self, expression_name: str):
        """设置表情 (normal, happy, sad, angry, surprised, love, sleepy)"""
        logger.info(f"变更表情: {expression_name}")
        return await self.send_command("expression", {"name": expression_name})

    async def speak(self, text: str):
        """让精灵说话"""
        logger.info(f"准备说话: {text}")
        return await self.send_command("speak", {"text": text})

    # === 鼠标跟随相关方法 ===
    def get_mouse_position(self):
        """获取鼠标在屏幕上的归一化位置 (-1 ~ 1)"""
        x, y = self.mouse_controller.position
        norm_x = x / self.screen_width
        norm_y = y / self.screen_height
        norm_x = (norm_x * 2) - 1
        norm_y = -((norm_y * 2) - 1)  # 反转Y轴
        return norm_x, norm_y
    
    def apply_dead_zone(self, value):
        """应用中心死区"""
        dead_zone = self.mouse_config["dead_zone"]
        if abs(value) < dead_zone:
            return 0.0
        sign = 1 if value > 0 else -1
        return sign * (abs(value) - dead_zone) / (1 - dead_zone)
    
    def update_mouse_target(self):
        """根据鼠标位置更新目标参数"""
        norm_x, norm_y = self.get_mouse_position()
        norm_x = self.apply_dead_zone(norm_x)
        norm_y = self.apply_dead_zone(norm_y)
        
        self.target_params["ParamAngleX"] = norm_x * 30 * self.mouse_config["head_sensitivity"]
        self.target_params["ParamAngleY"] = norm_y * 30 * self.mouse_config["head_sensitivity"]
        self.target_params["ParamEyeBallX"] = norm_x * 1.0 * self.mouse_config["eye_sensitivity"]
        self.target_params["ParamEyeBallY"] = norm_y * 1.0 * self.mouse_config["eye_sensitivity"]
    
    def update_current_params(self):
        """平滑更新当前参数值"""
        factor = self.mouse_config["smooth_factor"]
        for key in self.current_params:
            current = self.current_params[key]
            target = self.target_params[key]
            self.current_params[key] = current + (target - current) * factor

    async def _mouse_follow_loop(self):
        """鼠标跟随主循环 (30fps)"""
        logger.info("🐭 鼠标跟随系统已激活")
        while self.running and self.ws and self.ws.open:
            if not self.mouse_config["enabled"]:
                await asyncio.sleep(1)
                continue
                
            self.update_mouse_target()
            self.update_current_params()
            
            for param_id, value in self.current_params.items():
                await self.send_command("parameter", {
                    "id": param_id,
                    "value": round(value, 3)
                })
                
            await asyncio.sleep(1/30)

    async def _brain_loop(self):
        """大脑主循环，负责自主决策和行为"""
        logger.info("🧠 大脑开始运作...")
        
        # 初始打招呼
        await self.set_expression("happy")
        await asyncio.sleep(2)
        await self.set_expression("normal")

        while self.running and self.ws and self.ws.open:
            # 简单的待机循环示例
            await asyncio.sleep(10)
            
            # 随机小动作演示
            if random.random() < 0.1:
                logger.info("触发随机小动作...")
                await self.set_expression("love")
                await asyncio.sleep(3)
                await self.set_expression("normal")

    async def start(self):
        """启动大脑"""
        self.running = True
        await self.connect()

    def stop(self):
        """停止大脑"""
        self.running = False
        logger.info("大脑停止运作。")

async def main():
    brain = SpriteBrain()
    try:
        await brain.start()
    except KeyboardInterrupt:
        brain.stop()

if __name__ == "__main__":
    asyncio.run(main())
