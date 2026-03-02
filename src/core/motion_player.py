#!/usr/bin/env python3
"""
🐱💜 参数动画播放器
用于替代 StartMotion，手动解析 motion3.json 并按时间轴设置参数
"""

import json
import time
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable
from loguru import logger


class MotionPlayer:
    """手动解析并播放 Live2D motion3.json 动画"""
    
    def __init__(self, param_setter: Callable[[str, float], None]):
        """
        Args:
            param_setter: 参数设置回调函数 (param_id, value) -> None
        """
        self.param_setter = param_setter
        self._playing = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
    
    def load_motion(self, motion_file: Path) -> Optional[Dict]:
        """加载 motion3.json 文件"""
        try:
            with open(motion_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load motion file {motion_file}: {e}")
            return None
    
    def play(self, motion_file: Path, loop: bool = False) -> bool:
        """播放动作"""
        motion_data = self.load_motion(motion_file)
        if not motion_data:
            return False
        
        # 如果正在播放，先停止
        self.stop()
        
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._play_loop,
            args=(motion_data, loop),
            daemon=True
        )
        self._thread.start()
        return True
    
    def stop(self):
        """停止播放"""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
    
    def _play_loop(self, motion_data: Dict, loop: bool):
        """播放循环"""
        meta = motion_data.get("Meta", {})
        duration = meta.get("Duration", 6.0)  # 默认6秒
        fps = meta.get("Fps", 60.0)
        curves = motion_data.get("Curves", [])
        
        logger.info(f"🎬 Playing motion: duration={duration}s, curves={len(curves)}")
        
        do_loop = True
        while do_loop:
            start_time = time.time()
            
            while not self._stop_event.is_set():
                elapsed = time.time() - start_time
                if elapsed > duration:
                    break
                
                # 计算当前时间点所有参数的值
                for curve in curves:
                    param_id = curve.get("Id")
                    segments = curve.get("Segments", [])
                    value = self._interpolate_value(elapsed, segments)
                    
                    # 设置参数
                    try:
                        self.param_setter(param_id, value)
                        # 每3秒记录一次关键参数的值
                        if int(elapsed) % 3 == 0 and param_id in ["Angry2", "TearsLocus", "TailBow_1", "Flower"]:
                            logger.debug(f"Motion param {param_id} = {value:.2f} @ {elapsed:.1f}s")
                    except Exception as e:
                        logger.debug(f"Failed to set parameter {param_id}: {e}")
                
                # 控制帧率 (约30fps)
                time.sleep(1/30)
            
            # 重置所有参数到0
            for curve in curves:
                param_id = curve.get("Id")
                try:
                    self.param_setter(param_id, 0.0)
                except:
                    pass
            
            do_loop = loop and not self._stop_event.is_set()
        
        logger.info("🎬 Motion finished")
    
    def _interpolate_value(self, time: float, segments: List) -> float:
        """
        根据时间插值计算参数值
        
        Segments 格式: [type, time, value, ...]
        - type 0: 线性 [0, time, value]
        - type 1: 贝塞尔 [1, time, value, cp1x, cp1y, cp2x, cp2y]
        """
        if not segments:
            return 0.0
        
        # 解析时间段
        points = []
        i = 0
        while i < len(segments):
            seg_type = segments[i]
            if seg_type == 0:  # 线性段
                t = segments[i + 1]
                v = segments[i + 2]
                points.append((t, v))
                i += 3
            elif seg_type == 1:  # 贝塞尔段
                t = segments[i + 1]
                v = segments[i + 2]
                points.append((t, v))
                i += 7
            else:
                break
        
        if not points:
            return 0.0
        
        # 找到当前时间所在的段
        if time <= points[0][0]:
            return points[0][1]
        if time >= points[-1][0]:
            return points[-1][1]
        
        for i in range(len(points) - 1):
            t1, v1 = points[i]
            t2, v2 = points[i + 1]
            if t1 <= time <= t2:
                # 线性插值
                if t2 == t1:
                    return v1
                t = (time - t1) / (t2 - t1)
                return v1 + (v2 - v1) * t
        
        return points[-1][1]
