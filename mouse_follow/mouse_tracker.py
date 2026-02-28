#!/usr/bin/env python3
"""
Sherry Desktop Sprite - 鼠标跟随系统
自然模式：头部灵敏度50%，眼神灵敏度100%
"""

import asyncio
import json
import websockets
import signal
import sys
from pynput import mouse
from pynput.mouse import Button, Controller
import AppKit

class MouseTracker:
    def __init__(self):
        self.running = True
        self.ws = None
        self.uri = "ws://127.0.0.1:8765/sprite"
        
        # 自然模式配置
        self.config = {
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
        
        # 获取屏幕尺寸
        self.screen = AppKit.NSScreen.mainScreen()
        self.screen_width = self.screen.frame().size.width
        self.screen_height = self.screen.frame().size.height
        
        print(f"🐱 雪莉鼠标跟随系统启动")
        print(f"📺 屏幕分辨率: {self.screen_width:.0f} x {self.screen_height:.0f}")
        print(f"🎯 模式: 自然模式 (头部{self.config['head_sensitivity']*100:.0f}%, 眼神{self.config['eye_sensitivity']*100:.0f}%)")
        print(f"🛑 按 Ctrl+C 停止")
        
    def get_mouse_position(self):
        """获取鼠标在屏幕上的归一化位置 (-1 ~ 1)"""
        mouse_controller = Controller()
        x, y = mouse_controller.position
        
        # 归一化到 0 ~ 1
        norm_x = x / self.screen_width
        norm_y = y / self.screen_height
        
        # 转换到 -1 ~ 1 (Y轴需要反转，因为屏幕坐标Y向下)
        norm_x = (norm_x * 2) - 1
        norm_y = -((norm_y * 2) - 1)  # 反转Y轴
        
        return norm_x, norm_y
    
    def apply_dead_zone(self, value):
        """应用中心死区"""
        dead_zone = self.config["dead_zone"]
        if abs(value) < dead_zone:
            return 0.0
        # 重新映射到完整范围
        sign = 1 if value > 0 else -1
        return sign * (abs(value) - dead_zone) / (1 - dead_zone)
    
    def update_target(self):
        """根据鼠标位置更新目标参数"""
        norm_x, norm_y = self.get_mouse_position()
        
        # 应用死区
        norm_x = self.apply_dead_zone(norm_x)
        norm_y = self.apply_dead_zone(norm_y)
        
        # 计算目标值
        self.target_params["ParamAngleX"] = norm_x * 30 * self.config["head_sensitivity"]
        self.target_params["ParamAngleY"] = norm_y * 30 * self.config["head_sensitivity"]
        self.target_params["ParamEyeBallX"] = norm_x * 1.0 * self.config["eye_sensitivity"]
        self.target_params["ParamEyeBallY"] = norm_y * 1.0 * self.config["eye_sensitivity"]
    
    def lerp(self, current, target, factor):
        """线性插值平滑过渡"""
        return current + (target - current) * factor
    
    def update_current(self):
        """平滑更新当前参数值"""
        factor = self.config["smooth_factor"]
        for key in self.current_params:
            self.current_params[key] = self.lerp(
                self.current_params[key],
                self.target_params[key],
                factor
            )
    
    async def connect(self):
        """连接WebSocket"""
        try:
            self.ws = await websockets.connect(self.uri)
            print("✅ 已连接到雪莉精灵~")
            return True
        except Exception as e:
            print(f"❌ 连接失败: {e}")
            return False
    
    async def send_parameters(self):
        """发送参数到精灵"""
        if not self.ws:
            return
        
        for param_id, value in self.current_params.items():
            try:
                await self.ws.send(json.dumps({
                    "type": "parameter",
                    "data": {
                        "id": param_id,
                        "value": round(value, 3)
                    }
                }))
                # 接收响应但不打印，避免刷屏
                await asyncio.wait_for(self.ws.recv(), timeout=0.01)
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                pass
    
    async def run(self):
        """主循环"""
        if not await self.connect():
            return
        
        try:
            while self.running:
                # 更新目标值
                self.update_target()
                
                # 平滑更新当前值
                self.update_current()
                
                # 发送参数
                await self.send_parameters()
                
                # 控制帧率 ~30fps
                await asyncio.sleep(1/30)
                
        except websockets.exceptions.ConnectionClosed:
            print("⚠️ 连接断开")
        except Exception as e:
            print(f"❌ 错误: {e}")
        finally:
            if self.ws:
                await self.ws.close()
    
    def stop(self):
        """停止跟踪"""
        self.running = False
        print("\n🛑 已停止鼠标跟随")


def signal_handler(sig, frame):
    """处理Ctrl+C"""
    print("\n👋 再见主人~")
    sys.exit(0)


async def main():
    # 注册信号处理
    signal.signal(signal.SIGINT, signal_handler)
    
    tracker = MouseTracker()
    await tracker.run()


if __name__ == "__main__":
    asyncio.run(main())
