# 翻译功能快速上手指南

根据你的网络环境和需求，选择合适的翻译方案。

---

## 🌟 推荐方案（按优先级排序）

### 方案 1：国内翻译API（推荐国内用户）

**优点**：国内访问快，稳定，无需翻墙
**推荐API**：小牛翻译（每天20万字符免费）

**快速配置**：
1. 访问 https://niutrans.com/ 注册账号
2. 获取 API Key
3. 编辑 `config.yaml`：

```yaml
tts:
  translation:
    provider: ""  # 不使用AI翻译
    china:
      niutrans:
        api_key: "your-api-key-here"
```

详细配置 → [国内翻译API文档](./CHINA_TRANSLATION_API.md)

---

### 方案 2：OpenAI（推荐海外用户/高质量需求）

**优点**：翻译质量最高，理解上下文
**费用**：约 ¥0.01/百句

**快速配置**：
1. 访问 https://platform.openai.com 获取API密钥
2. 编辑 `config.yaml`：

```yaml
tts:
  translation:
    provider: "openai"
    api_key: "sk-your-api-key-here"
    model: "gpt-4o-mini"
```

详细配置 → [日文语音功能指南](./JAPANESE_TTS_GUIDE.md)

---

### 方案 3：Ollama本地模型（推荐隐私/离线需求）

**优点**：完全免费，无需联网，隐私安全
**要求**：需要较好的电脑配置

**快速配置**：
1. 安装 Ollama：https://ollama.com
2. 下载模型：`ollama pull qwen2.5:7b`
3. 编辑 `config.yaml`：

```yaml
tts:
  translation:
    provider: "ollama"
    model: "qwen2.5:7b"
```

---

### 方案 4：Google翻译（无需配置，直接使用）

**优点**：免费，无需注册
**缺点**：国内访问需翻墙，质量一般

**无需配置**，直接启用自动翻译即可使用。

---

## 方案对比

| 方案 | 质量 | 费用 | 国内访问 | 配置难度 |
|-----|------|------|---------|---------|
| **小牛翻译** | ⭐⭐⭐⭐ | 免费 | ✅ 直接访问 | 简单 |
| **百度翻译** | ⭐⭐⭐⭐ | 免费5万/月 | ✅ 直接访问 | 简单 |
| **OpenAI** | ⭐⭐⭐⭐⭐ | 低价 | ❌ 需翻墙 | 简单 |
| **Ollama** | ⭐⭐⭐⭐ | 免费 | ✅ 本地运行 | 中等 |
| **Google** | ⭐⭐ | 免费 | ❌ 需翻墙 | 无需配置 |

---

## 快速测试

配置完成后，运行测试：

```bash
# 测试翻译质量对比
python examples/test_translation.py

# 日文语音演示
python examples/japanese_tts_demo.py
```

---

## 一键切换语言

右键点击雪莉 → 🌐 语言 → 选择目标语言

- 🇨🇳 中文：中文语音
- 🇯🇵 日本語：日文语音 + 自动翻译
- 🇺🇸 English：英文语音

---

## 获取帮助

- 国内API问题 → [CHINA_TRANSLATION_API.md](./CHINA_TRANSLATION_API.md)
- 日文语音问题 → [JAPANESE_TTS_GUIDE.md](./JAPANESE_TTS_GUIDE.md)
- 右键菜单问题 → [RIGHT_CLICK_MENU.md](./RIGHT_CLICK_MENU.md)
