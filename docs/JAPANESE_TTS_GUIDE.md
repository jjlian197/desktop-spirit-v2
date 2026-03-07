# 日文语音功能使用指南

本项目支持**高质量的 AI 翻译** + 日文语音，让雪莉的中文台词自然流畅地转换成日文！

## 🌟 功能特点

- ✅ **AI 翻译**：支持 OpenAI、Claude、Ollama，理解上下文，翻译自然
- ✅ **智能缓存**：相同内容不会重复翻译，节省 API 费用
- ✅ **自动回退**：AI 翻译失败时自动使用 Google 翻译
- ✅ **语言检测**：自动检测文本语言，避免重复翻译

---

## 快速开始

### 方案 1：OpenAI 翻译（推荐，质量最好）

1. **安装依赖**
```bash
pip install openai
```

2. **配置 API 密钥**

编辑 `config.yaml`：
```yaml
tts:
  auto_translate: true
  
  translation:
    provider: "openai"
    api_key: "sk-your-api-key-here"  # 你的 OpenAI API 密钥
    # model: "gpt-4o-mini"  # 默认即可，可选 gpt-4o, gpt-3.5-turbo
```

3. **运行**
```python
from src.core.tts_manager import get_tts_manager

tts = get_tts_manager()
tts.set_language("ja")  # 切换到日文模式

# 中文自动翻译成高质量日文
await tts.speak("你好，今天过得怎么样？")
# 输出：こんにちは、今日はどんな一日でしたか？
```

---

### 方案 2：本地 Ollama 翻译（免费，无需联网）

1. **安装 Ollama**
```bash
# 访问 https://ollama.com 下载安装
```

2. **下载日文模型**
```bash
# 推荐模型（按质量排序）
ollama pull qwen2.5:7b      # 阿里通义，中日翻译优秀
ollama pull llama3.2        # Meta 模型
ollama pull phi4            # 微软模型
```

3. **配置**
```yaml
tts:
  translation:
    provider: "ollama"
    api_base: "http://localhost:11434"
    model: "qwen2.5:7b"
```

4. **运行**
```python
tts.set_language("ja")
await tts.speak("很高兴见到你！")  # 本地模型翻译
```

---

### 方案 3：Claude 翻译

```yaml
tts:
  translation:
    provider: "claude"
    api_key: "sk-ant-your-api-key"
    # model: "claude-3-haiku-20240307"  # 默认即可
```

---

## 翻译质量对比

| 翻译方式 | 质量 | 成本 | 速度 | 适用场景 |
|---------|------|------|------|----------|
| **OpenAI** | ⭐⭐⭐⭐⭐ | 低 | 快 | 推荐日常使用 |
| **Claude** | ⭐⭐⭐⭐⭐ | 中 | 快 | 专业场景 |
| **Ollama** | ⭐⭐⭐⭐ | 免费 | 中等 | 隐私要求高 |
| **Google** | ⭐⭐ | 免费 | 快 | 备用方案 |

### 翻译示例

**中文原文**："哎呀，你怎么来了？真是让我又惊又喜呢！"

| 翻译方式 | 结果 |
|---------|------|
| Google | あら、どうして来たの？本当に驚きと喜びですね！（生硬） |
| OpenAI | あら、いらっしゃったの？驚いちゃった！嬉しいなぁ～（自然流畅） |

---

## 高级配置

### 环境变量配置（不写入配置文件）

```bash
# Windows PowerShell
$env:OPENAI_API_KEY="sk-your-api-key"
$env:OPENAI_MODEL="gpt-4o-mini"
python main.py

# 或者写入 .env 文件
```

### 使用代理

```yaml
tts:
  translation:
    provider: "openai"
    api_key: "sk-your-key"
    api_base: "https://your-proxy.com/v1"  # 代理地址
```

### 禁用翻译

```python
tts.set_auto_translate(False)  # 临时禁用
```

### 清空缓存

翻译结果会自动缓存到 `.translation_cache.json`，如需清空直接删除该文件。

---

## 完整配置示例

```yaml
tts:
  default_provider: "edge"
  auto_translate: true
  
  translation:
    provider: "openai"
    api_key: "${OPENAI_API_KEY}"  # 从环境变量读取
    model: "gpt-4o-mini"
    use_cache: true
  
  edge:
    voice: "ja-JP-NanamiNeural"
```

---

## 常见问题

### Q: OpenAI 翻译费用高吗？
A: **非常低**。使用 `gpt-4o-mini` 模型：
- 每 1000 个汉字约 $0.0015
- 正常对话一天花费不到 $0.1
- 缓存机制避免重复翻译

### Q: 没有 API 密钥怎么办？
A: 使用 **Ollama 本地模型**，完全免费：
```bash
ollama pull qwen2.5:7b
```
然后在 config.yaml 中配置 `provider: "ollama"`。

### Q: 翻译速度很慢？
A: 
- 开启 `use_cache: true` 缓存常用句子
- 使用更快的模型如 `gpt-4o-mini`
- Ollama 需要较好的显卡加速

### Q: 某些句子翻译不好？
A: AI 翻译已经比 Google 好很多了，但如果遇到特定术语：
1. 直接提供日文输入
2. 修改 `.translation_cache.json` 手动校正

### Q: 如何测试翻译质量？
```bash
python examples/test_translation.py
```

---

## 安装依赖

```bash
# 使用 OpenAI（推荐）
pip install openai

# 使用 Claude
pip install anthropic

# 使用 Ollama（无需安装额外库）
# 只需安装 Ollama 软件

# 使用 Google（备用）
pip install deep-translator
```
