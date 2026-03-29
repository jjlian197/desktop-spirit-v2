# 🎀 PyInstaller 打包指南

## 打包步骤

### 1. 标准打包（无控制台）

```bash
# 激活虚拟环境
source venv/bin/activate

# 打包
pyinstaller SherryApp.spec --clean

# 输出位置
# dist/SherryApp.app
```

### 2. 调试打包（有控制台，用于排查问题）

```bash
pyinstaller SherryApp_debug.spec --clean

# 运行调试版本查看日志
./dist/SherryApp_debug.app/Contents/MacOS/SherryApp_debug
```

## 常见问题

### 问题 1: 打包后双击闪退

**原因**: 应用没有 GUI 就退出了，看不到错误信息

**解决**: 使用调试版本查看日志
```bash
pyinstaller SherryApp_debug.spec --clean
./dist/SherryApp_debug.app/Contents/MacOS/SherryApp_debug
```

### 问题 2: SSH 命令找不到

**原因**: 打包后的应用环境变量 PATH 不完整

**解决**: 在终端中先建立 SSH 隧道，再启动应用
```bash
# 先手动建立隧道
ssh -N -L 9880:127.0.0.1:9880 pc &

# 再启动应用（使用原始模式）
SHERRY_NO_LAUNCHER=1 open ./dist/SherryApp.app
```

### 问题 3: GPT-SoVITS 检测卡住

**原因**: 后台线程阻塞了 GUI

**解决**: 使用环境变量跳过自动初始化
```bash
# 跳过 launcher 的 GPT-SoVITS 初始化
SHERRY_NO_LAUNCHER=1 ./dist/SherryApp.app/Contents/MacOS/SherryApp
```

然后在应用内的右键菜单手动配置 GPT-SoVITS。

### 问题 4: 打包后找不到资源文件

**检查**: 确保 spec 文件中的 datas 配置正确
```python
datas=[
    ('src/assets/models', 'src/assets/models'),
    ('config.yaml', '.'),
    (live2d_shaders, 'live2d/v3/FrameworkShaders'),
],
```

## 推荐的打包流程

### 方案 A: 全自动（需要 SSH 可用）

1. 确保 `ssh pc` 可用
2. 执行打包
3. 双击启动 `SherryApp.app`

### 方案 B: 手动 SSH（更稳定）

1. 打包应用
2. 创建启动脚本 `launch_sakiko.sh`:
```bash
#!/bin/bash
# 先建立 SSH 隧道
ssh -N -L 9880:127.0.0.1:9880 pc &
SSH_PID=$!

# 设置环境变量
export GPT_SOVITS_URL="http://127.0.0.1:9880/tts"
export GPT_SOVITS_REFER_WAV="D:/Workspace/..."
export GPT_SOVITS_PROMPT_TEXT="なんだか申し訳..."

# 启动应用（跳过 launcher）
export SHERRY_NO_LAUNCHER=1
open /Applications/SherryApp.app

# 等待应用关闭
sleep 5

# 关闭 SSH 隧道
kill $SSH_PID
```

3. 使用脚本启动

## 文件说明

| 文件 | 说明 |
|------|------|
| `SherryApp.spec` | 标准打包配置（无控制台） |
| `SherryApp_debug.spec` | 调试打包配置（有控制台） |
| `src/launcher.py` | 打包后入口点，自动初始化 GPT-SoVITS |
| `src/main.py` | 原始入口点（开发用） |

## 环境变量

| 变量 | 说明 |
|------|------|
| `SHERRY_NO_LAUNCHER=1` | 跳过 launcher，直接使用原始启动 |
| `GPT_SOVITS_URL` | GPT-SoVITS API 地址 |
| `GPT_SOVITS_REFER_WAV` | 参考音频路径 |
| `GPT_SOVITS_PROMPT_TEXT` | 参考文本 |

## 调试技巧

1. **查看崩溃日志**: 使用 `SherryApp_debug.spec` 打包，从终端运行
2. **检查资源加载**: 在代码中添加 `print(os.listdir('.'))` 查看工作目录
3. **检查 SSH**: 手动执行 `ssh -N -L 9880:127.0.0.1:9880 pc` 测试

## 最小测试

如果打包后有问题，先测试最小功能：

```bash
# 只打包不依赖 SSH 的版本
SHERRY_NO_LAUNCHER=1 pyinstaller SherryApp.spec --clean

# 测试能否启动
./dist/SherryApp.app/Contents/MacOS/SherryApp
```

如果这样可以启动，说明问题在 SSH/GPT-SoVITS 初始化部分。
