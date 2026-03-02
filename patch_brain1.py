import re

file_path = "/Volumes/D - Data/sherry-desktop-sprite/src/brain/sprite_brain.py"
with open(file_path, "r", encoding="utf-8") as f:
    content = f.read()

patch = """            logger.info(f"🌐 HTTP API 收到命令: {cmd_type}")
            
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

            # 转发到 WebSocket
            success = await self.send_command(cmd_type, cmd_data)"""

# Replace the handling part
content = re.sub(
    r'            logger\.info\(f"🌐 HTTP API 收到命令: \{cmd_type\}"\)\s*# 转发到 WebSocket\s*success = await self\.send_command\(cmd_type, cmd_data\)',
    patch,
    content
)

with open(file_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied successfully.")
