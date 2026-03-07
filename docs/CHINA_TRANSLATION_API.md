# 国内翻译 API 使用指南

为国内用户提供稳定、快速的翻译服务，无需翻墙即可使用。

## 支持的 API

| 服务商 | 免费额度 | 特点 | 注册地址 |
|-------|---------|------|---------|
| **百度翻译** | 每月5万字符 | 准确度高，速度快 | [注册](https://fanyi-api.baidu.com/) |
| **有道翻译** | 新用户50元 | 专业术语翻译好 | [注册](https://ai.youdao.com/) |
| **小牛翻译** | 每天20万字符 | 学术背景，稳定 | [注册](https://niutrans.com/) |

> ⚠️ **小牛翻译注意**：需要先登录控制台领取试用金或充值后才能使用API。新用户有20元试用金。

## 快速配置（百度翻译推荐）

### 步骤 1：注册百度翻译

1. 访问 https://fanyi-api.baidu.com/
2. 登录百度账号
3. 点击 "立即使用" → "通用翻译API"
4. 填写应用名称（如：雪莉桌面精灵）
5. 选择 "标准版"（免费）或 "高级版"（付费）
6. 复制 **APP ID** 和 **密钥**

### 步骤 2：配置密钥

编辑 `config.yaml`：

```yaml
tts:
  auto_translate: true
  
  translation:
    provider: ""  # 不使用AI翻译，只用国内API
    
    china:
      baidu:
        app_id: "your-app-id-here"      # 替换为你的APP ID
        app_key: "your-app-key-here"    # 替换为你的密钥
```

### 步骤 3：运行测试

```bash
python examples/japanese_tts_demo.py
```

---

## 配置示例

### 仅使用国内API（无AI翻译）

```yaml
tts:
  translation:
    provider: ""  # 留空
    
    china:
      baidu:
        app_id: "20240307001999999"
        app_key: "your_secret_key_here"
```

### 小牛翻译配置（免费额度最大）

```yaml
tts:
  translation:
    provider: ""
    
    china:
      niutrans:
        api_key: "your-niutrans-api-key"
```

**小牛翻译注册步骤**：
1. 访问 https://niutrans.com/
2. 注册账号并登录
3. 进入控制台 → 个人中心 → API密钥
4. 复制API密钥
5. **重要**：进入 "我的账户" → 领取试用金（新用户有20元）
6. 配置到 config.yaml

### 国内API + AI翻译（推荐）

```yaml
tts:
  translation:
    provider: "openai"
    api_key: "sk-your-openai-key"
    model: "gpt-4o-mini"
    
    china:
      baidu:
        app_id: "your-baidu-app-id"
        app_key: "your-baidu-key"
```

**优先级**：
1. OpenAI 翻译（质量最高）
2. 百度翻译（国内访问快）
3. Google 翻译（免费备选）

### 多国内API配置（自动回退）

```yaml
tts:
  translation:
    china:
      baidu:
        app_id: "your-baidu-app-id"
        app_key: "your-baidu-key"
      
      youdao:
        app_id: "your-youdao-app-id"
        app_key: "your-youdao-key"
      
      niutrans:
        api_key: "your-niutrans-key"
```

**回退顺序**：百度 → 有道 → 小牛 → Google

---

## 测试工具

我们提供了测试工具来验证API配置是否正确：

```bash
python examples/test_china_translation.py
```

此工具会：
1. 读取你的 config.yaml 配置
2. 测试所有已配置的国内翻译API
3. 显示翻译结果和错误信息
4. 提供常见问题的解决方案

---

## 环境变量配置

也可以不修改配置文件，使用环境变量：

```bash
# Windows PowerShell
$env:BAIDU_APP_ID="your-app-id"
$env:BAIDU_APP_KEY="your-app-key"
python main.py
```

或创建 `.env` 文件：
```
BAIDU_APP_ID=your-app-id
BAIDU_APP_KEY=your-app-key
```

---

## 翻译质量对比

**原文**："哎呀，你怎么来了？真是让我又惊又喜呢！"

| API | 翻译结果 | 评价 |
|-----|---------|------|
| Google | あら、どうして来たの？本当に驚きと喜びですね！ | 生硬，逐字翻译 |
| **百度** | あら、いらっしゃったの？驚いちゃった！嬉しいな～ | 自然，口语化 |
| **有道** | あら、どうしていらっしゃったんですか？驚きと嬉しさがありますね！ | 礼貌，略正式 |
| **小牛** | あら、来てくれたの？びっくりしちゃった！嬉しい！ | 活泼，自然 |

---

## 免费额度对比

| API | 免费额度 | 超出后费用 |
|-----|---------|-----------|
| 百度标准版 | 5万字符/月 | 49元/百万字符 |
| 百度高级版 | 200万字符/月 | 50元/百万字符 |
| 有道 | 50元体验金 | 48元/百万字符 |
| 小牛 | 20万字符/天 | 免费额度通常够用 |

**推荐**：小牛翻译（每天20万字符，对桌面宠物完全够用）

---

## 常见问题

### Q: 为什么配置了但翻译还是走的Google？

A: 检查以下几点：
1. APP ID 和密钥是否正确
2. 是否有额外的空格
3. 配置文件格式是否正确（缩进用空格）

### Q: 百度翻译报错 "52003"？

A: 错误码含义：
- 52001: 请求超时，重试即可
- 52002: 系统错误，联系百度
- 52003: 未授权用户，检查APP ID是否正确

### Q: 小牛翻译报错 "小牛翻译API认证失败"？

A: 这通常意味着：
1. **API密钥未激活**：登录 https://niutrans.com/ → 控制台 → 我的账户 → 领取试用金
2. **账户余额不足**：需要充值或领取试用金后才能使用API
3. **API密钥错误**：检查复制的API密钥是否完整

**解决方法**：
```bash
# 1. 登录控制台
https://niutrans.com/

# 2. 进入"我的账户"

# 3. 领取试用金（新用户有20元）或充值

# 4. 重新运行测试
python examples/test_china_translation.py
```

### Q: 可以同时配置多个API吗？

A: 可以！系统会自动按顺序尝试，直到成功。

### Q: 翻译速度慢？

A: 
1. 开启 `use_cache: true` 缓存常用句子
2. 使用百度/有道，国内访问速度快
3. 避免在高峰期使用

---

## 注册指南截图

### 百度翻译注册步骤

1. 访问 https://fanyi-api.baidu.com/
2. 登录后点击 "管理控制台"
3. 点击 "开通服务"
4. 选择 "通用翻译"
5. 填写应用信息：
   - 应用名称：雪莉桌面精灵
   - 应用类别：工具类
   - 应用简介：桌面宠物语音翻译
6. 提交后获得 APP ID 和密钥

---

## 相关文档

- [日文语音功能指南](./JAPANESE_TTS_GUIDE.md)
- [右键菜单功能说明](./RIGHT_CLICK_MENU.md)
