#!/usr/bin/env python3
"""
SSH Tunnel Manager - 自动管理 SSH 隧道
用于连接远程 GPT-SoVITS 服务
"""

import os
import time
import threading
import subprocess
from typing import Optional
from dataclasses import dataclass

from loguru import logger


@dataclass
class SSHTunnelConfig:
    """SSH 隧道配置"""
    remote_host: str          # 远程服务器 IP/域名或 SSH Config 别名
    remote_port: int = 9880   # 远程 GPT-SoVITS 端口
    local_port: int = 9880    # 本地映射端口
    ssh_user: str = ""        # SSH 用户名（使用 SSH Config 别名时可省略）
    ssh_key: str = ""         # SSH 私钥路径（可选）
    ssh_password: str = ""    # SSH 密码（可选，不推荐）


class SSHTunnelManager:
    """
    SSH 隧道管理器
    支持 paramiko 库或系统 SSH 命令
    """

    def __init__(self, config: SSHTunnelConfig):
        self.config = config
        self._tunnel_process: Optional[subprocess.Popen] = None
        self._paramiko_thread: Optional[threading.Thread] = None
        self._is_connected = False

    def start(self) -> bool:
        """启动 SSH 隧道"""
        try:
            return self._start_with_system_ssh()
        except Exception as e:
            logger.warning(f"系统 SSH 失败，尝试 paramiko: {e}")
            return self._start_with_paramiko()

    def _start_with_system_ssh(self) -> bool:
        """使用系统 SSH 命令建立隧道"""
        if self.config.ssh_user:
            host_spec = f"{self.config.ssh_user}@{self.config.remote_host}"
        else:
            host_spec = self.config.remote_host

        cmd = [
            "ssh",
            "-N",
            "-L", f"{self.config.local_port}:127.0.0.1:{self.config.remote_port}",
            host_spec,
        ]

        if self.config.ssh_key and os.path.exists(self.config.ssh_key):
            cmd.extend(["-i", self.config.ssh_key])

        logger.info(f"🔌 建立 SSH 隧道: localhost:{self.config.local_port} -> {self.config.remote_host}:{self.config.remote_port}")

        self._tunnel_process = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        time.sleep(2)

        if self._tunnel_process.poll() is None:
            self._is_connected = True
            logger.info("✅ SSH 隧道已建立")
            return True
        else:
            logger.error("❌ SSH 隧道建立失败")
            return False

    def _start_with_paramiko(self) -> bool:
        """使用 paramiko 库建立隧道（备用方案）"""
        try:
            import paramiko
            from paramiko import SSHClient

            def tunnel_worker():
                try:
                    client = SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

                    connect_kwargs = {
                        "hostname": self.config.remote_host,
                        "username": self.config.ssh_user,
                    }

                    if self.config.ssh_key and os.path.exists(self.config.ssh_key):
                        connect_kwargs["key_filename"] = self.config.ssh_key
                    elif self.config.ssh_password:
                        logger.warning("⚠️ 使用密码认证 SSH 不安全，建议使用 SSH 密钥！")
                        connect_kwargs["password"] = self.config.ssh_password

                    client.connect(**connect_kwargs)

                    transport = client.get_transport()
                    transport.request_port_forward(
                        "127.0.0.1",
                        self.config.local_port,
                        handler=None
                    )

                    self._is_connected = True
                    logger.info("✅ Paramiko SSH 隧道已建立")

                    while self._is_connected:
                        time.sleep(1)

                    client.close()

                except Exception as e:
                    logger.error(f"Paramiko 隧道错误: {e}")
                    self._is_connected = False

            self._paramiko_thread = threading.Thread(target=tunnel_worker, daemon=True)
            self._paramiko_thread.start()

            time.sleep(2)
            return self._is_connected

        except ImportError:
            logger.error("❌ paramiko 未安装，无法建立 SSH 隧道")
            return False

    def stop(self):
        """停止 SSH 隧道"""
        self._is_connected = False

        if self._tunnel_process:
            self._tunnel_process.terminate()
            try:
                self._tunnel_process.wait(timeout=5)
            except:
                self._tunnel_process.kill()
            logger.info("🔌 SSH 隧道已关闭")

    def is_connected(self) -> bool:
        """检查隧道是否连接"""
        if self._tunnel_process:
            return self._tunnel_process.poll() is None
        return self._is_connected


def create_tunnel_from_env() -> Optional[SSHTunnelManager]:
    """
    从环境变量创建 SSH 隧道

    环境变量:
        SSH_TUNNEL_HOST: 远程服务器地址或 SSH 别名（必需）
        SSH_TUNNEL_USER: SSH 用户名（可选）
        SSH_TUNNEL_KEY: SSH 私钥路径（可选）
        SSH_TUNNEL_PASSWORD: SSH 密码（可选）
        GPT_SOVITS_REMOTE_PORT: 远程端口（默认9880）
        GPT_SOVITS_LOCAL_PORT: 本地端口（默认9880）
    """
    host = os.environ.get("SSH_TUNNEL_HOST", "")
    user = os.environ.get("SSH_TUNNEL_USER", "")

    if not host:
        return None

    config = SSHTunnelConfig(
        remote_host=host,
        ssh_user=user,
        ssh_key=os.environ.get("SSH_TUNNEL_KEY", ""),
        ssh_password=os.environ.get("SSH_TUNNEL_PASSWORD", ""),
        remote_port=int(os.environ.get("GPT_SOVITS_REMOTE_PORT", "9880")),
        local_port=int(os.environ.get("GPT_SOVITS_LOCAL_PORT", "9880")),
    )

    manager = SSHTunnelManager(config)
    if manager.start():
        return manager
    return None


# 全局隧道实例（单例）
_tunnel_instance: Optional[SSHTunnelManager] = None


def get_tunnel() -> Optional[SSHTunnelManager]:
    """获取或创建隧道实例"""
    global _tunnel_instance
    if _tunnel_instance is None:
        _tunnel_instance = create_tunnel_from_env()
    return _tunnel_instance
