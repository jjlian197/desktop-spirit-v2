#!/usr/bin/env python3
"""
Sherry Agent Bridge (雪莉 ↔ OpenClaw Agent CLI 通信桥)
通过 openclaw CLI 向 OpenClaw 发送反馈消息。
"""

import logging
import re
import subprocess
import threading
from typing import Optional

logger = logging.getLogger("AgentBridge")

# 🚨 全局开关：Agent Bridge 默认关闭
_agent_bridge_enabled = False

# 🚨 日志行过滤正则：过滤包含 [plugins]、[INFO]、[WARNING] 等日志标记的行
LOG_LINE_PATTERN = re.compile(r'\[(plugins|INFO|WARNING|ERROR|DEBUG)\]')


def set_agent_bridge_enabled(enabled: bool):
    """设置 Agent Bridge 是否启用"""
    global _agent_bridge_enabled
    _agent_bridge_enabled = enabled
    logger.info(f"{'✅' if enabled else '🚫'} Agent Bridge {'已启用' if enabled else '已禁用'}")


def is_agent_bridge_enabled() -> bool:
    """检查 Agent Bridge 是否启用"""
    return _agent_bridge_enabled


def call_agent(
    message: str,
    agent_name: str = "main",
    channel: str = "telegram",
    target: str = "8046601710",
    timeout: int = 60
) -> Optional[str]:
    """
    调用 OpenClaw Agent 并返回 stdout 响应（阻塞调用）。

    Args:
        message: 要发送给 Agent 的消息
        agent_name: Agent 名称（默认 main）
        channel: 消息渠道（默认 telegram）
        target: 目标用户 ID（默认 8046601710）
        timeout: 超时秒数（默认 30）

    Returns:
        Agent 的 stdout 响应文字，或 None（失败时）
    """
    if not _agent_bridge_enabled:
        logger.debug("Agent Bridge 已关闭，跳过调用")
        return None

    full_message = f"{channel}@{target}: {message}"

    try:
        result = subprocess.run(
            ["openclaw", "agent", "--agent", agent_name, "--message", full_message],
            capture_output=True,
            text=True,
            timeout=timeout
        )

        if result.returncode == 0:
            logger.info(f"📤 Agent 调用成功: {message[:30]}...")
            # 过滤掉日志行（包含 [plugins]、[INFO] 等标记的行）
            if result.stdout:
                lines = result.stdout.strip().split('\n')
                # 用正则匹配日志行（行首或行内包含日志标记都过滤）
                response_lines = [l for l in lines if not LOG_LINE_PATTERN.search(l)]
                if response_lines:
                    # 保留所有非日志行，拼接为完整响应
                    return ''.join(response_lines).strip()
            return None
        else:
            logger.warning(f"⚠️ Agent CLI 异常: {result.stderr}")
            return None

    except subprocess.TimeoutExpired:
        logger.error(f"⏰ Agent 调用超时（{timeout}s）")
        return None
    except FileNotFoundError:
        logger.error("❌ 未找到 openclaw 命令")
        return None
    except Exception as e:
        logger.error(f"Agent 调用失败: {e}")
        return None


class AgentBridge:
    """
    Sherry ↔ OpenClaw Agent CLI 通信桥

    功能:
    - 通过 openclaw CLI 向 OpenClaw 发送反馈消息
    - 监控空闲/忙碌状态
    - 自动重连机制（检测 Agent 是否在线）
    """

    def __init__(
        self,
        agent_name: str = "main",
        default_channel: str = "telegram",
        default_target: str = "8046601710"
    ):
        """
        Args:
            agent_name: OpenClaw Agent 名称
            default_channel: 默认消息渠道
            default_target: 默认目标用户 ID
        """
        self.agent_name = agent_name
        self.default_channel = default_channel
        self.default_target = default_target

        self.connected = False
        self.running = False
        self._health_thread: Optional[threading.Thread] = None

        # 回调：收到 Agent 命令
        self.on_command: Optional[callable] = None

    def connect(self):
        """启动 Agent 通信桥（健康检查线程）"""
        self.running = True
        self._health_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self._health_thread.start()
        logger.info("✅ Agent Bridge 已启动")

    def _health_check_loop(self):
        """健康检查循环（在线程中运行）"""
        import time
        retry_count = 0

        while self.running:
            try:
                if self._check_agent_health_sync():
                    if not self.connected:
                        logger.info("✅ OpenClaw Agent 已连接！")
                        self.connected = True
                    retry_count = 0
                else:
                    if self.connected:
                        logger.warning("⚠️ OpenClaw Agent 离线")
                        self.connected = False
                    retry_count += 1

                # 每 30 秒检测一次
                time.sleep(30)

            except Exception as e:
                logger.error(f"Agent 健康检查错误: {e}")
                retry_count += 1
                time.sleep(min(5 * retry_count, 30))

    def _check_agent_health_sync(self) -> bool:
        """检查 Agent 是否在线（通过 CLI 检测）"""
        try:
            result = subprocess.run(
                ["openclaw", "agent", "--agent", self.agent_name, "--ping"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def disconnect(self):
        """断开连接"""
        self.running = False
        self.connected = False
        if self._health_thread:
            self._health_thread.join(timeout=2)

    def send_message(
        self,
        message: str,
        channel: Optional[str] = None,
        target: Optional[str] = None,
        blocking: bool = False
    ) -> bool:
        """
        发送消息给 Agent（通过 CLI）

        Args:
            message: 消息内容
            channel: 消息渠道（默认使用 default_channel）
            target: 目标用户 ID（默认使用 default_target）
            blocking: 是否同步阻塞等待（默认 False，非阻塞）

        Returns:
            发送是否成功（非阻塞模式立即返回 True）
        """
        # 🚨 检查全局开关
        if not _agent_bridge_enabled:
            logger.debug("📤 Agent Bridge 已关闭，跳过发送")
            return False

        if not channel:
            channel = self.default_channel
        if not target:
            target = self.default_target

        # 构建完整消息：渠道@目标: 消息内容
        full_message = f"{channel}@{target}: {message}"

        def _do_send():
            """在线程中执行 subprocess 调用"""
            try:
                result = subprocess.run(
                    ["openclaw", "agent", "--agent", self.agent_name, "--message", full_message],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                if result.returncode == 0:
                    logger.info(f"📤 消息已发送: {message[:50]}...")
                else:
                    logger.warning(f"⚠️ Agent CLI 异常: {result.stderr}")
            except subprocess.TimeoutExpired:
                logger.error("⏰ Agent 命令超时")
            except Exception as e:
                logger.error(f"发送消息失败: {e}")

        if blocking:
            # 同步阻塞模式
            _do_send()
            return True
        else:
            # 🚨 非阻塞模式：在线程中执行，避免阻塞主事件循环
            threading.Thread(target=_do_send, daemon=True).start()
            return True

    # === 便捷方法 ===

    def send_touch_feedback(
        self,
        part: str,
        action: str,
        mood: str,
        affection: int,
        response: str
    ) -> bool:
        """发送触摸反馈"""
        message = f"💖 触摸 | {part}/{action} | 心情:{mood} | 好感度:{affection} | 雪莉: {response}"
        return self.send_message(message)

    def send_mood_change(
        self,
        old_affection: int,
        new_affection: int,
        tier: str
    ) -> bool:
        """发送心情/好感度变化"""
        message = f"💕 好感度变化: {old_affection} → {new_affection} ({tier})"
        return self.send_message(message)

    def send_speak(
        self,
        text: str,
        mood: str
    ) -> bool:
        """发送雪莉说话内容"""
        message = f"💬 雪莉: {text}"
        return self.send_message(message)

    def send_idle_enter(self, idle_time: float) -> bool:
        """发送进入空闲状态"""
        message = f"😴 进入空闲（闲置 {idle_time:.0f} 秒）"
        return self.send_message(message)

    def send_idle_exit(self) -> bool:
        """发送退出空闲状态"""
        message = "👋 退出空闲状态"
        return self.send_message(message)

    def send_status_report(
        self,
        mood: str,
        affection: int,
        tier: str,
        is_idle: bool,
        tts_enabled: bool
    ) -> bool:
        """发送状态报告"""
        message = f"📊 状态 | 心情:{mood} | 好感度:{affection}({tier}) | 空闲:{is_idle} | TTS:{tts_enabled}"
        return self.send_message(message)


def create_agent_bridge(
    **kwargs
) -> AgentBridge:
    """工厂函数，创建 Agent Bridge"""
    return AgentBridge(**kwargs)