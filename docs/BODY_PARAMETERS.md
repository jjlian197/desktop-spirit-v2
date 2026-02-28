# 🐱 奶牛猫花丸 Live2D 身体参数全清单

> **模型**: 奶牛猫花丸_完整版  
> **用途**: WebSocket 动捕控制参数参考  
> **生成时间**: 2026-02-20

---

## 📋 目录

1. [核心动捕参数 (实时控制)](#1-核心动捕参数-实时控制)
2. [头部控制](#2-头部控制)
3. [眼部控制](#3-眼部控制)
4. [眉毛控制](#4-眉毛控制)
5. [口部控制](#5-口部控制)
6. [身体控制](#6-身体控制)
7. [功能按键开关](#7-功能按键开关)
8. [物理效果参数](#8-物理效果参数)
9. [动画参数](#9-动画参数)
10. [其他参数](#10-其他参数)
11. [WebSocket 操作指南](#11-websocket-操作指南)

---

## 1. 核心动捕参数 (实时控制) ⭐

这些参数是 **FaceRig/动捕软件** 的标准输出，需要 WebSocket 实时接管：

| 参数 ID | 名称 | 类型 | 说明 |
|---------|------|------|------|
| `ParamAngleX` | ● 头 X | 头部旋转 | 左右转头 (-30 ~ 30) |
| `ParamAngleY` | ● 头 Y | 头部旋转 | 上下点头 (-30 ~ 30) |
| `ParamAngleZ` | ● 头 Z | 头部旋转 | 歪头 (-30 ~ 30) |
| `ParamEyeBallX` | ●瞳 X | 眼球移动 | 眼睛左右看 (-1 ~ 1) |
| `ParamEyeBallY` | ●瞳 Y | 眼球移动 | 眼睛上下看 (-1 ~ 1) |
| `ParamBodyAngleX` | ● 身体  X | 身体旋转 | 身体左右倾斜 (-10 ~ 10) |
| `ParamBodyAngleY` | ● 身体  Y | 身体旋转 | 身体前后倾斜 (-10 ~ 10) |
| `ParamBodyAngleZ` | ● 身体  Z | 身体旋转 | 身体旋转 (-10 ~ 10) |
| `ParamEyeLOpen` | ●左眼  开闭 | 眼睛开闭 | 左眼睁开程度 (0 ~ 1) |
| `ParamEyeROpen` | ●右眼  开闭 | 眼睛开闭 | 右眼睁开程度 (0 ~ 1) |
| `ParamMouthOpenY` | ●口  开闭 | 嘴巴开闭 | 嘴巴张开程度 (0 ~ 1) |
| `ParamMouthForm` | ●口  变形 | 嘴型 | 嘴型变形 (-1 ~ 1) |
| `ParamBrowLY` | ●左眉  上下 | 眉毛 | 左眉上下移动 (-1 ~ 1) |
| `ParamBrowRY` | ●右眉  上下 | 眉毛 | 右眉上下移动 (-1 ~ 1) |
| `ParamBrowLForm` | ●左眉  变形 | 眉毛 | 左眉形状 (-1 ~ 1) |
| `ParamBrowRForm` | ●右眉  变形 | 眉毛 | 右眉形状 (-1 ~ 1) |
| `ParamBreath` | ●呼吸 | 呼吸动画 | 呼吸起伏 (0 ~ 1) |

---

## 2. 头部控制

### 2.1 头部旋转 (ParamGroup9 - 头XY)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `ParamAngleX` | ● 头 X | 主控：左右转头 |
| `ParamAngleY` | ● 头 Y | 主控：上下点头 |
| `ParamAngleZ` | ● 头 Z | 主控：歪头 |
| `Eyelashes_X` | 睫毛 X | 睫毛随头部X移动 |
| `Eyelashes_y` | 睫毛 Y | 睫毛随头部Y移动 |
| `HeadAngleX3` | 变Q 头 X | Q版模式头部X |
| `HeadAngleY3` | 变Q 头 Y | Q版模式头部Y |

---

## 3. 眼部控制

### 3.1 基础眼睛控制 (ParamGroup22 - 眼)

| 参数 ID | 名称 | 类型 | 说明 |
|---------|------|------|------|
| `ParamEyeLOpen` | ●左眼  开闭 | 开闭 | 0=闭眼, 1=睁眼 |
| `ParamEyeLSmile` | 左眼   微笑 | 表情 | 左眼微笑曲线 |
| `ParamEyeROpen` | ●右眼  开闭 | 开闭 | 0=闭眼, 1=睁眼 |
| `ParamEyeRSmile` | 右眼   微笑 | 表情 | 右眼微笑曲线 |
| `ParamEyeBallX` | ●瞳 X | 位置 | 瞳孔X轴位置 (-1~1) |
| `ParamEyeBallY` | ●瞳 Y | 位置 | 瞳孔Y轴位置 (-1~1) |
| `ParamEyeBallX2` | 瞳透视 X | 透视 | 瞳孔透视X |
| `ParamEyeBallY2` | 瞳透视 Y | 透视 | 瞳孔透视Y |

### 3.2 眼睛物理 (ParamGroup2 - 眼物理)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `P_eye_1` | ← 眼眶 1 | 左眼眶物理 1 |
| `P_eye_2` | ← 眼眶 2 | 左眼眶物理 2 |
| `P_eyeR_1` | 眼眶 1  → | 右眼眶物理 1 |
| `P_eyeR_2` | 眼眶 2  → | 右眼眶物理 2 |
| `P_eye_3` | ← 睫毛 1 | 左睫毛物理 |
| `P_eyeR_3` | 睫毛 1  → | 右睫毛物理 |
| `P_eyeball_1` | ← 果冻眼 1 | 左眼果冻效果 1 |
| `P_eyeball_2` | ← 果冻眼 2 | 左眼果冻效果 2 |
| `P_eyeball_3` | ← 果冻眼 3 | 左眼果冻效果 3 |
| `P_eyeballR_1` | 果冻眼 1  → | 右眼果冻效果 1 |
| `P_eyeballR_2` | 果冻眼 2  → | 右眼果冻效果 2 |
| `P_eyeballR_3` | 果冻眼 3  → | 右眼果冻效果 3 |
| `P_EyeHighlight_1` | ← 眼高光 1 | 左眼高光 1 |
| `P_EyeHighlight_2` | ← 眼高光 2 | 左眼高光 2 |
| `P_EyeHighlight_3` | ← 眼高光 3 | 左眼高光 3 |
| `P_EyeHighlightR_1` | 眼高光 1 → | 右眼高光 1 |
| `P_EyeHighlightR_2` | 眼高光 2 → | 右眼高光 2 |
| `P_EyeHighlightR_3` | 眼高光 3 → | 右眼高光 3 |
| `P_Tear_1` | ← 眼泪 1 | 左眼泪水 1 |
| `P_Tear_2` | ← 眼泪 2 | 左眼泪水 2 |
| `P_TearR_1` | 眼泪 1 → | 右眼泪水 1 |
| `P_TearR_2` | 眼泪 2 → | 右眼泪水 2 |
| `Love1` | 眨眼爱心透明度 | 左眼爱心透明度 |
| `Love2` | 眨眼爱心位移 | 左眼爱心位移 |
| `Love3` | R眨眼爱心透明度 | 右眼爱心透明度 |
| `Love4` | R眨眼爱心位移 | 右眼爱心位移 |

---

## 4. 眉毛控制

### 4.1 眉毛控制 (ParamGroup5 - 眉)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `ParamBrowLY` | ●左眉  上下 | 主控：左眉上下 |
| `ParamBrowLForm` | ●左眉  变形 | 主控：左眉形状 |
| `ParamBrowLY2` | 左眉  联动上下 | 联动：左眉上下 |
| `ParamBrowLForm2` | 左眉  联动微笑 | 联动：左眉微笑 |
| `ParamBrowRY` | ●右眉  上下 | 主控：右眉上下 |
| `ParamBrowRForm` | ●右眉  变形 | 主控：右眉形状 |
| `ParamBrowRY2` | 右眉  联动上下 | 联动：右眉上下 |
| `ParamBrowRForm2` | 右眉  联动微笑 | 联动：右眉微笑 |

---

## 5. 口部控制

### 5.1 口部控制 (ParamGroup6 - 口)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `ParamMouthForm` | ●口  变形 | 主控：嘴型变形 |
| `ParamMouthOpenY` | ●口  开闭 | 主控：嘴巴开闭 |
| `ParamTongueOut` | TongueOut | 舌头伸出 |
| `ParamMouthPuckerWiden` | PuckerWiden | 撅嘴/咧嘴 |
| `ParamMouthX` | ●MouthX | 嘴巴X轴 |
| `ParamMouthX2` | MouthX | 嘴巴X轴2 |
| `ParamCheekPuff` | ●CheekPuff | 鼓腮 |
| `ParamCheekPuff2` | CheekPuff | 鼓腮2 |
| `ParamMouthShrug` | ●MouthShrug | 耸嘴 |
| `ParamJawOpen` | ●JawOpen | 下巴张开 |
| `ParamMouthFunnel` | ●MouthFunnel | 漏斗嘴型 |
| `ParamMouthPressLeft` | ●MouthPressLeft | 左压嘴 |
| `ParamMouthPressRight` | ●MouthPressRight | 右压嘴 |
| `ParamMouthPressLipOpen3` | MouthPressLipOpen (备) | 备用 |
| `ParamMouthStretchLeft` | MouthStretchLeft | 左拉伸 |
| `ParamMouthStretchRight` | MouthStretchRight | 右拉伸 |
| `Mouth_S1` | 嘴物理 1 | 嘴部物理 1 |
| `Mouth_S2` | 嘴物理 2 | 嘴部物理 2 |
| `Mouth_S3` | 舌头物理 1 | 舌头物理 1 |
| `Mouth_S4` | 舌头物理 2 | 舌头物理 2 |
| `TheToothCorrectionX2` | 下牙修正 X+ | 下牙X+修正 |
| `TheToothCorrectionX1` | 下牙修正 X- | 下牙X-修正 |
| `TheToothCorrectionX3` | 下牙修正 Y+ | 下牙Y+修正 |
| `TheToothCorrectionX4` | 下牙修正 Y- | 下牙Y-修正 |

---

## 6. 身体控制

### 6.1 身体旋转 (ParamGroup14 - 控制器)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `ParamBodyAngleX` | ● 身体  X | 主控：身体X旋转 |
| `ParamBodyAngleY` | ● 身体  Y | 主控：身体Y旋转 |
| `ParamBodyAngleZ` | ● 身体  Z | 主控：身体Z旋转 |

### 6.2 身体XY细节 (ParamGroup3 - 身体XY)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `ParamBodyAngleX6` | 身体  X1 | 身体X1层 |
| `ParamBodyAngleY5` | 身体  Y1 | 身体Y1层 |
| `ParamBodyAngleY7` | 身体  Y1(Q版大前倾修正) | Q版前倾修正 |
| `ParamBodyAngleZ5` | 身体  Z1 | 身体Z1层 |
| `ParamBodyAngleX3` | 身体  X2 | 身体X2层 |
| `ParamBodyAngleY3` | 身体  Y2 | 身体Y2层 |
| `ParamBodyAngleZ3` | 身体  Z2 | 身体Z2层 |
| `ParamBodyAngleX5` | 腰位移  X | 腰部X位移 |
| `ParamBodyAngleX4` | 身体位移  X | 身体X位移 |
| `ParamBodyAngleZ4` | 身体位移  Z | 身体Z位移 |
| `ParamPelvisYDown` | 盆骨 YDown | 骨盆下移 |
| `ParamPelvisYUp` | 盆骨 YUp | 骨盆上移 |
| `ParamBodyAngleX7` | 俯身头腰位移  X | 俯身位移X |
| `ParamBodyShoulderX` | 肩 X | 肩膀X |
| `ParamBodyShoulderY` | 肩 Y | 肩膀Y |
| `tajiao` | 踏脚 | 踏脚动作 |
| `tajiao2` | 弹性Y | 弹性Y轴 |
| `tajiao3` | 大前倾长发修正 | 前倾头发修正 |

---

## 7. 功能按键开关 🔘

### 7.1 头部装饰开关 (ParamGroup13 - Keys)

| 参数 ID | 名称 | 类型 | 说明 |
|---------|------|------|------|
| `Key1` | ● 眼睛换色 | 开关 | 切换眼睛颜色 |
| `Key2` | ● 头发换色 | 开关 | 切换头发颜色 |
| `Key41` | ● 猫耳换色 | 开关 | 切换猫耳颜色 |
| `Key3` | ● 前发 | 开关 | 前发样式切换 |
| `Key4` | ● 鬓发 | 开关 | 鬓发样式切换 |
| `Key5` | ● 后发 | 开关 | 后发样式切换 |
| `Key44` | ● 头顶小猫 | 开关 | 显示/隐藏头顶小猫 |
| `Key29` | ● LOOK眼镜 | 开关 | 显示/隐藏眼镜 |
| `Key36` | ● 垃圾袋 | 开关 | 显示/隐藏垃圾袋 |
| `Key13` | ● 黑眼罩 | 开关 | 显示/隐藏眼罩 |
| `Key18` | ● 叼猫条 | 开关 | 叼猫条动作 |
| `Key19` | ● 叼内裤 | 开关 | 叼内裤动作 |
| `Key25` | ● 头饰显隐左 | 开关 | 左侧头饰显隐 |
| `Key24` | ● 头饰显隐右 | 开关 | 右侧头饰显隐 |
| `Key42` | ● 耳环显隐左 | 开关 | 左侧耳环显隐 |
| `Key43` | ● 耳环显隐右 | 开关 | 右侧耳环显隐 |

### 7.2 表情开关 (ParamGroup13 - Keys)

| 参数 ID | 名称 | 类型 | 说明 |
|---------|------|------|------|
| `Key11` | ● 哈气 | 开关 | 哈气表情 |
| `Key30` | ● 黑脸 | 开关 | 黑脸表情 |
| `Key21` | ● 红脸 | 开关 | 脸红表情 |
| `Key14` | ● 生气 | 开关 | 生气表情 |
| `Key15` | ● 呆 | 开关 | 发呆表情 |
| `Key16` | ● 剪刀眼 | 开关 | 剪刀眼表情 |
| `Key17` | ● 星星眼 | 开关 | 星星眼表情 |
| `Key20` | ● 哭哭 | 开关 | 哭泣表情 |

### 7.3 身体装饰开关 (ParamGroup13 - Keys)

| 参数 ID | 名称 | 类型 | 说明 |
|---------|------|------|------|
| `Key8` | ● 腰间花朵装饰 | 开关 | 腰花显示 |
| `Key9` | ● 腰间大蝴蝶结 | 开关 | 大蝴蝶结显示 |
| `Key10` | ● 腰间小蝴蝶结 | 开关 | 小蝴蝶结显示 |
| `Key7` | ● 衣服换色 | 开关 | 切换衣服颜色 |
| `Key6` | ● 尾巴 | 开关 | 尾巴显示/隐藏 |

### 7.4 手势开关 (ParamGroup13 - Keys)

| 参数 ID | 名称 | 类型 | 说明 |
|---------|------|------|------|
| `Key12` | ● 挥手 | 开关 | 挥手动作 |
| `Key31` | ● 端酒 | 开关 | 端酒动作 |
| `Key32` | ● 比心 | 开关 | 比心动作 |
| `Key33` | ● 话筒 | 开关 | 拿话筒动作 |
| `Key34` | ● 手机 | 开关 | 拿手机动作 |
| `Key35` | ● 猫爪 | 开关 | 猫爪动作 |

### 7.5 互动动作开关 (ParamGroup13 - Keys)

| 参数 ID | 名称 | 类型 | 说明 |
|---------|------|------|------|
| `Key37` | ● 捏脸 | 开关 | 捏脸互动 |
| `Key39` | ● 摸脸 | 开关 | 摸脸互动 |

### 7.6 特殊效果开关 (ParamGroup13 - Keys)

| 参数 ID | 名称 | 类型 | 说明 |
|---------|------|------|------|
| `Key22` | ● 飞头 | 开关 | 飞头特效 |
| `Key23` | ● 脖子消失 | 开关 | 脖子隐藏 |
| `Key26` | ● 变Q | 开关 | Q版模式 |
| `Key27` | ● 抬脚 开关 | 开关 | 抬脚动作 |

### 7.7 自定义改色 (ParamGroup13 - Keys)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `Key45` | ● 头发改色 R | 头发红色通道 |
| `Key46` | ● 头发改色 G | 头发绿色通道 |
| `Key47` | ● 头发改色 B | 头发蓝色通道 |
| `Key48` | ● 头发改色 饱和度 | 头发饱和度 |
| `Key49` | ● 眼睛改色 R | 眼睛红色通道 |
| `Key50` | ● 眼睛改色 G | 眼睛绿色通道 |
| `Key51` | ● 眼睛改色 B | 眼睛蓝色通道 |
| `Key52` | ● 眼睛改色 饱和度 | 眼睛饱和度 |
| `Key53` | ● 眼罩改色 R | 眼罩红色通道 |
| `Key54` | ● 眼罩改色 G | 眼罩绿色通道 |
| `Key55` | ● 眼罩改色 B | 眼罩蓝色通道 |
| `Key56` | ● 眼罩改色 饱和度 | 眼罩饱和度 |

---

## 8. 物理效果参数

### 8.1 头部物理 (ParamGroup10 - 头物理)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `toufapiaodai_1` | 头发飘带 1 | 左发飘带 1 |
| `toufapiaodai_2` | 头发飘带 2 | 左发飘带 2 |
| `toufapiaodai_3` | 头发飘带 3 | 左发飘带 3 |
| `toufapiaodai_4` | 头发飘带 4 | 左发飘带 4 |
| `toufapiaodai_5` | 头发飘带 Y1 | 左发飘带 Y1 |
| `toufapiaodai_6` | 头发飘带 Y2 | 左发飘带 Y2 |
| `toufapiaodai_7` | R头发飘带 1 | 右发飘带 1 |
| `toufapiaodai_8` | R头发飘带 2 | 右发飘带 2 |
| `toufapiaodai_9` | R头发飘带 3 | 右发飘带 3 |
| `toufapiaodai_10` | R头发飘带 4 | 右发飘带 4 |
| `toufapiaodai_11` | R头发飘带 Y1 | 右发飘带 Y1 |
| `Earrings_1` | 耳饰 1 | 左耳环 1 |
| `Earrings_2` | 耳饰 2 | 左耳环 2 |
| `Earrings_3` | 耳饰 3 | 左耳环 3 |
| `Earrings_4` | 耳饰 4 | 左耳环 4 |
| `Earrings_5` | R耳饰 1 | 右耳环 1 |
| `Earrings_6` | R耳饰 2 | 右耳环 2 |
| `Earrings_7` | R耳饰 3 | 右耳环 3 |
| `Earrings_8` | R耳饰 4 | 右耳环 4 |
| `Headwear_1` | 头饰  1 | 头饰物理 1 |
| `Headwear_2` | 头饰  2 | 头饰物理 2 |
| `Headwear_3` | 头饰  3 | 头饰物理 3 |
| `Headwear_4` | 头饰  4 | 头饰物理 4 |
| `Headwear_5` | 头饰  5 | 头饰物理 5 |
| `Headwear_6` | 2头饰  1 | 头饰2物理 1 |
| `Headwear_7` | 2头饰  2 | 头饰2物理 2 |
| `Headwear_8` | 2头饰  3 | 头饰2物理 3 |
| `Headwear_9` | 2头饰  4 | 头饰2物理 4 |
| `Headwear_10` | 2头饰  5 | 头饰2物理 5 |
| `Animal_ear_L1` | ← 兽耳 1 | 左兽耳 1 |
| `Animal_ear_L2` | ← 兽耳 2 | 左兽耳 2 |
| `Animal_ear_L3` | ← 兽耳 3 | 左兽耳 3 |
| `Animal_ear_L4` | ← 2兽耳 1 | 左兽耳2 1 |
| `Animal_ear_L5` | ← 2兽耳 2 | 左兽耳2 2 |
| `Animal_ear_L6` | ← 2兽耳 3 | 左兽耳2 3 |
| `Animal_ear_R1` | 兽耳 1 → | 右兽耳 1 |
| `Animal_ear_R2` | 兽耳 2 → | 右兽耳 2 |
| `Animal_ear_R3` | 兽耳 3 → | 右兽耳 3 |
| `Animal_ear_R4` | 2兽耳 1 → | 右兽耳2 1 |
| `Animal_ear_R5` | 2兽耳 2 → | 右兽耳2 2 |
| `Animal_ear_R6` | 2兽耳 3 → | 右兽耳2 3 |

### 8.2 刘海物理 (ParamGroup8 - 刘海)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `HairFront_1` | 中刘海 1 | 中刘海物理 1 |
| `HairFront_Y1` | 中刘海 Y1 | 中刘海Y轴 1 |
| `HairFront_2` | 中刘海 2 | 中刘海物理 2 |
| `HairFront_Y2` | 中刘海 Y2 | 中刘海Y轴 2 |
| `HairFront_3` | 中刘海 3 | 中刘海物理 3 |
| `HairFront_Y3` | 中刘海 Y3 | 中刘海Y轴 3 |
| `HairFront_L1` | ← 刘海 1 | 左刘海 1 |
| `HairFront_LY1` | ← 刘海 Y1 | 左刘海Y 1 |
| `HairFront_L2` | ← 刘海 2 | 左刘海 2 |
| `HairFront_LY2` | ← 刘海 Y2 | 左刘海Y 2 |
| `HairFront_L3` | ← 刘海 3 | 左刘海 3 |
| `HairFront_LY3` | ← 刘海 Y3 | 左刘海Y 3 |
| `HairFront_R1` | 刘海 1  → | 右刘海 1 |
| `HairFront_RY1` | 刘海 Y1  → | 右刘海Y 1 |
| `HairFront_R2` | 刘海 2  → | 右刘海 2 |
| `HairFront_RY2` | 刘海 Y2  → | 右刘海Y 2 |
| `HairFront_R3` | 刘海 3  → | 右刘海 3 |
| `HairFront_RY3` | 刘海 Y3  → | 右刘海Y 3 |

### 8.3 侧发物理 (ParamGroup17 - 侧发)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `HairSide_L1` | ← 侧发 1 | 左侧发 1 |
| `HairSide_LY1` | ← 侧发 Y1 | 左侧发Y 1 |
| `HairSide_L2` | ← 侧发 2 | 左侧发 2 |
| `HairSide_LY2` | ← 侧发 Y2 | 左侧发Y 2 |
| `HairSide_L3` | ← 侧发 3 | 左侧发 3 |
| `HairSide_LY3` | ← 侧发 Y3 | 左侧发Y 3 |
| `HairSide_L4` | ← 侧发 4 | 左侧发 4 |
| `HairSide_LY4` | ← 侧发 Y4 | 左侧发Y 4 |
| `HairSide_R1` | 侧发 1  → | 右侧发 1 |
| `HairSide_RY1` | 侧发 Y1  → | 右侧发Y 1 |
| `HairSide_R2` | 侧发 2  → | 右侧发 2 |
| `HairSide_RY2` | 侧发 Y2  → | 右侧发Y 2 |
| `HairSide_R3` | 侧发 3  → | 右侧发 3 |
| `HairSide_RY3` | 侧发 Y3  → | 右侧发Y 3 |
| `HairSide_R4` | 侧发 4  → | 右侧发 4 |
| `HairSide_RY4` | 侧发 Y4  → | 右侧发Y 4 |

### 8.4 鬓发物理 (ParamGroup11 - 鬓发)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `Earlock_L1` | ← 鬓发 1 | 左鬓发 1 |
| `Earlock_LY1` | ← 鬓发 Y1 | 左鬓发Y 1 |
| `Earlock_L2` | ← 鬓发 2 | 左鬓发 2 |
| `Earlock_LY2` | ← 鬓发 Y2 | 左鬓发Y 2 |
| `Earlock_L3` | ← 鬓发 3 | 左鬓发 3 |
| `Earlock_LY3` | ← 鬓发 Y3 | 左鬓发Y 3 |
| `Earlock_L4` | ← 鬓发 4 | 左鬓发 4 |
| `Earlock_LY4` | ← 鬓发 Y4 | 左鬓发Y 4 |
| `Earlock_R1` | 鬓发 1  → | 右鬓发 1 |
| `Earlock_RY1` | 鬓发 Y1  → | 右鬓发Y 1 |
| `Earlock_R2` | 鬓发 2  → | 右鬓发 2 |
| `Earlock_RY2` | 鬓发 Y2  → | 右鬓发Y 2 |
| `Earlock_R3` | 鬓发 3  → | 右鬓发 3 |
| `Earlock_RY3` | 鬓发 Y3  → | 右鬓发Y 3 |
| `Earlock_R4` | 鬓发 4  → | 右鬓发 4 |
| `Earlock_RY4` | 鬓发 Y4  → | 右鬓发Y 4 |

### 8.5 后发物理 (ParamGroup12 - 后发)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `HairBack_L5` | 中后发 1 | 中后发 1 |
| `HairBack_LY5` | 中后发 Y1 | 中后发Y 1 |
| `HairBack_L6` | 中后发 2 | 中后发 2 |
| `HairBack_LY6` | 中后发 Y2 | 中后发Y 2 |
| `HairBack_L7` | 中后发 3 | 中后发 3 |
| `HairBack_LY7` | 中后发 Y3 | 中后发Y 3 |
| `HairBack_L8` | 中后发 4 | 中后发 4 |
| `HairBack_LY8` | 中后发 Y4 | 中后发Y 4 |
| `HairBack_L1` | ← 后发 1 | 左后发 1 |
| `HairBack_LY1` | ← 后发 Y1 | 左后发Y 1 |
| `HairBack_L2` | ← 后发 2 | 左后发 2 |
| `HairBack_LY2` | ← 后发 Y2 | 左后发Y 2 |
| `HairBack_L3` | ← 后发 3 | 左后发 3 |
| `HairBack_LY3` | ← 后发 Y3 | 左后发Y 3 |
| `HairBack_L4` | ← 后发 4 | 左后发 4 |
| `HairBack_LY4` | ← 后发 Y4 | 左后发Y 4 |
| `HairBack_R1` | 后发 1  → | 右后发 1 |
| `HairBack_RY1` | 后发 Y1  → | 右后发Y 1 |
| `HairBack_R2` | 后发 2  → | 右后发 2 |
| `HairBack_RY2` | 后发 Y2  → | 右后发Y 2 |
| `HairBack_R3` | 后发 3  → | 右后发 3 |
| `HairBack_RY3` | 后发 Y3  → | 右后发Y 3 |
| `HairBack_R4` | 后发 4  → | 右后发 4 |
| `HairBack_RY4` | 后发 Y4  → | 右后发Y 4 |

### 8.6 身体物理 (ParamGroup7 - 身体物理)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `Shoulder_R1` | ← 肩 | 左肩物理 |
| `Elbow_R1` | ← 肘 | 左肘物理 |
| `Wrist_R1` | ← 腕 | 左腕物理 |
| `finger_R1` | ← 手指 1 | 左手指 1 |
| `finger_R2` | ← 手指 2 | 左手指 2 |
| `finger_R3` | ← 手指透视 | 左手指透视 |
| `Shoulder_L1` | 肩  → | 右肩物理 |
| `Elbow_L1` | 肘  → | 右肘物理 |
| `Wrist_L1` | 腕  → | 右腕物理 |
| `finger_L1` | 手指 1  → | 右手指 1 |
| `finger_L2` | 手指 2  → | 右手指 2 |
| `finger_L3` | 手指透视 → | 右手指透视 |
| `oupai_X1` | 胸  X1 | 胸部X 1 |
| `oupai_x2` | 胸  X2 | 胸部X 2 |
| `oupai_Y1` | 胸  Y1 | 胸部Y 1 |
| `oupai_y2` | 胸  Y2 | 胸部Y 2 |
| `Leg_X1` | 腿 X1 | 腿部X 1 |
| `Leg_X2` | 腿 X2 | 腿部X 2 |
| `Leg_Y1` | 腿 Y1 | 腿部Y 1 |
| `Leg_Y2` | 腿 Y2 | 腿部Y 2 |
| `ShadowX` | 光影变化 X | 光影X |
| `Bell_4` | 光影变化 Y | 光影Y |
| `Bell_1` | 脖子铃铛 1 | 颈铃 1 |
| `Bell_2` | 脖子铃铛 2 | 颈铃 2 |
| `NeckPendant_1` | 脖子吊坠 1 | 颈坠 1 |
| `NeckPendant_2` | 脖子吊坠 2 | 颈坠 2 |
| `zhezhou_S1` | 腰间褶皱 X1 | 腰褶X 1 |
| `zhezhou_S2` | 腰间褶皱 Y1 | 腰褶Y 1 |
| `zhezhou_S3` | 腰间褶皱 X2 | 腰褶X 2 |
| `zhezhou_S4` | 腰间褶皱 Y2 | 腰褶Y 2 |
| `yao_1` | 腰 1 | 腰部 1 |
| `yao_2` | 腰 2 | 腰部 2 |
| `yao_3` | 腰 3 | 腰部 3 |
| `Bracelet_1` | 手链 1 | 手链 1 |
| `Bracelet_2` | 手链 2 | 手链 2 |
| `Bracelet_3` | 手链 3 | 手链 3 |
| `Bracelet_4` | 手链 4 | 手链 4 |
| `Sleeves_1` | ← 袖子 1 | 左袖 1 |
| `Sleeves_2` | ← 袖子 2 | 左袖 2 |
| `Sleeves_3` | ← 袖子 3 | 左袖 3 |
| `Sleeves_4` | ← 袖子 4 | 左袖 4 |
| `Sleeves_5` | 袖子 1 → | 右袖 1 |
| `Sleeves_6` | 袖子 2 → | 右袖 2 |
| `Sleeves_7` | 袖子 3 → | 右袖 3 |
| `Sleeves_8` | 袖子 4 → | 右袖 4 |
| `Cuffs_1` | 袖口 1 | 袖口 1 |
| `Cuffs_2` | 袖口 2 | 袖口 2 |
| `Cuffs_3` | 袖口 3 | 袖口 3 |
| `Cuffs_4` | 袖口 4 | 袖口 4 |
| `HandHeld1` | 手持物 1 | 手持物 1 |
| `HandHeld2` | 手持物 2 | 手持物 2 |
| `HandHeld3` | 手持物 3 | 手持物 3 |
| `HandHeld4` | 手持物 4 | 手持物 4 |
| `Hemline_9` | 前裙摆 1 | 前裙摆 1 |
| `Hemline_10` | 前裙摆 2 | 前裙摆 2 |
| `Hemline_11` | 前裙摆 3 | 前裙摆 3 |
| `Hemline_12` | 前裙摆 4 | 前裙摆 4 |
| `Hemline_1` | ← 裙摆 1 | 左裙摆 1 |
| `Hemline_2` | ← 裙摆 2 | 左裙摆 2 |
| `Hemline_3` | ← 裙摆 3 | 左裙摆 3 |
| `Hemline_4` | ← 裙摆 4 | 左裙摆 4 |
| `Hemline_Y1` | ← 裙摆 Y1 | 左裙摆Y 1 |
| `Hemline_Y2` | ← 裙摆 Y2 | 左裙摆Y 2 |
| `Hemline_Y5` | ← 裙摆 Y3 | 左裙摆Y 3 |
| `Hemline_5` | 裙摆 1 → | 右裙摆 1 |
| `Hemline_6` | 裙摆 2 → | 右裙摆 2 |
| `Hemline_7` | 裙摆 3 → | 右裙摆 3 |
| `Hemline_8` | 裙摆 4 → | 右裙摆 4 |
| `Hemline_Y3` | 裙摆 Y1 → | 右裙摆Y 1 |
| `Hemline_Y4` | 裙摆 Y2 → | 右裙摆Y 2 |
| `Coat_1` | 外套 1 | 外套 1 |
| `Coat_2` | 外套 2 | 外套 2 |
| `Coat_3` | 外套 3 | 外套 3 |
| `Coat_4` | 外套 4 | 外套 4 |
| `CoatCollar_1` | 外套衣领 1 | 衣领 1 |
| `CoatCollar_2` | 外套衣领 2 | 衣领 2 |
| `TaiBell_1` | 尾巴铃铛 1 | 尾铃 1 |
| `TaiBell_2` | 尾巴铃铛 2 | 尾铃 2 |
| `ShoesPhysics1` | 鞋子 1 | 鞋子物理 1 |
| `ShoesPhysics2` | 鞋子 2 | 鞋子物理 2 |
| `ShoesPhysics3` | 鞋子 3 | 鞋子物理 3 |
| `ShoesPhysics4` | 鞋子 4 | 鞋子物理 4 |
| `HairSide_L5` | ← 裙后摆 1 | 左裙后摆 1 |
| `HairSide_LY5` | ← 裙后摆 Y1 | 左裙后摆Y 1 |
| `HairSide_L6` | ← 裙后摆 2 | 左裙后摆 2 |
| `HairSide_LY6` | ← 裙后摆 Y2 | 左裙后摆Y 2 |
| `HairSide_L7` | ← 裙后摆 3 | 左裙后摆 3 |
| `HairSide_LY7` | ← 裙后摆 Y3 | 左裙后摆Y 3 |
| `HairSide_L8` | ← 裙后摆 4 | 左裙后摆 4 |
| `HairSide_LY8` | ← 裙后摆 Y4 | 左裙后摆Y 4 |
| `HairSide_R5` | 裙后摆 1  → | 右裙后摆 1 |
| `HairSide_RY5` | 裙后摆 Y1  → | 右裙后摆Y 1 |
| `HairSide_R6` | 裙后摆 2  → | 右裙后摆 2 |
| `HairSide_RY6` | 裙后摆 Y2  → | 右裙后摆Y 2 |
| `HairSide_R7` | 裙后摆 3  → | 右裙后摆 3 |
| `HairSide_RY7` | 裙后摆 Y3  → | 右裙后摆Y 3 |
| `HairSide_R8` | 裙后摆 4  → | 右裙后摆 4 |
| `HairSide_RY8` | 裙后摆 Y4  → | 右裙后摆Y 4 |
| `sidai1` | 丝带 1 | 丝带 1 |
| `sidai2` | 丝带 2 | 丝带 2 |
| `sidai3` | 丝带 3 | 丝带 3 |
| `sidai4` | 丝带 4 | 丝带 4 |
| `sidai5` | 丝带 5 | 丝带 5 |
| `sidai6` | 丝带 6 | 丝带 6 |
| `sidai7` | 丝带 7 | 丝带 7 |
| `sidai8` | 丝带 8 | 丝带 8 |

### 8.7 蝴蝶结物理 (ParamGroup15 - 蝴蝶结)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `NeckBow_1` | 颈部 蝴蝶结 1 | 颈结 1 |
| `NeckBow_2` | 颈部 蝴蝶结 2 | 颈结 2 |
| `NeckBow_3` | 颈部 蝴蝶结 3 | 颈结 3 |
| `NeckBow_4` | 颈部 蝴蝶结 4 | 颈结 4 |
| `ChestBow_1` | 胸部 蝴蝶结 1 | 胸结 1 |
| `ChestBow_2` | 胸部 蝴蝶结 2 | 胸结 2 |
| `ChestBow_3` | 胸部 蝴蝶结 3 | 胸结 3 |
| `ChestBow_4` | 胸部 蝴蝶结 4 | 胸结 4 |
| `ArmBow_1` | 手臂 蝴蝶结 1 | 臂结 1 |
| `ArmBow_2` | 手臂 蝴蝶结 2 | 臂结 2 |
| `ArmBow_3` | 手臂 蝴蝶结 3 | 臂结 3 |
| `ArmBow_4` | 手臂 蝴蝶结 4 | 臂结 4 |
| `WaistBow_1` | 腰间 蝴蝶结 1 | 腰结 1 |
| `WaistBow_2` | 腰间 蝴蝶结 2 | 腰结 2 |
| `WaistBow_3` | 腰间 蝴蝶结 3 | 腰结 3 |
| `WaistBow_4` | 腰间 蝴蝶结 4 | 腰结 4 |
| `LegBow_1` | 腿部 蝴蝶结 1 | 腿结 1 |
| `LegBow_2` | 腿部 蝴蝶结 2 | 腿结 2 |
| `LegBow_3` | 腿部 蝴蝶结 3 | 腿结 3 |
| `LegBow_4` | 腿部 蝴蝶结 4 | 腿结 4 |
| `ShoesBow_1` | 鞋子 蝴蝶结 1 | 鞋结 1 |
| `ShoesBow_2` | 鞋子 蝴蝶结 2 | 鞋结 2 |
| `ShoesBow_3` | 鞋子 蝴蝶结 3 | 鞋结 3 |
| `ShoesBow_4` | 鞋子 蝴蝶结 4 | 鞋结 4 |
| `TailBow_1` | 尾巴 蝴蝶结 1 | 尾结 1 |
| `TailBow_2` | 尾巴 蝴蝶结 2 | 尾结 2 |
| `TailBow_3` | 尾巴 蝴蝶结 3 | 尾结 3 |
| `TailBow_4` | 尾巴 蝴蝶结 4 | 尾结 4 |

### 8.8 尾巴物理 (ParamGroup18 - 尾巴)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `Param_Angle_Rotation_1_ArtMesh1483` | [0]尾巴 | 尾巴段 0 |
| `Param_Angle_Rotation_2_ArtMesh1483` | [1]尾巴 | 尾巴段 1 |
| `Param_Angle_Rotation_3_ArtMesh1483` | [2]尾巴 | 尾巴段 2 |
| `Param_Angle_Rotation_4_ArtMesh1483` | [3]尾巴 | 尾巴段 3 |
| `Param_Angle_Rotation_5_ArtMesh1483` | [4]尾巴 | 尾巴段 4 |
| `Param_Angle_Rotation_6_ArtMesh1483` | [5]尾巴 | 尾巴段 5 |
| `Param_Angle_Rotation_7_ArtMesh1483` | [6]尾巴 | 尾巴段 6 |

---

## 9. 动画参数

### 9.1 主动画 (ParamGroup - 动画（参数勿改）)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `Angry1` | 生气符号 1 | 生气标记 1 |
| `Angry2` | 生气符号 2 | 生气标记 2 |
| `Angry3` | 生气符号 3 | 生气标记 3 |
| `CircleTheEyes` | 圈圈眼 | 晕眩眼 |
| `TearsLocus` | 流泪轨迹 1 | 泪水轨迹 1 |
| `TearsLocus2` | 流泪轨迹 2 | 泪水轨迹 2 |
| `TearsLocus3` | 流泪轨迹 3 | 泪水轨迹 3 |
| `TearsLocus4` | 流泪轨迹 4 | 泪水轨迹 4 |

### 9.2 辅助动画 (ParamGroup4 - 动画)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `motion_Love4` | 瞳孔爱心旋转 1 | 爱心瞳孔旋转 |
| `nielianX` | 捏脸拉扯X | 捏脸X轴 |
| `Flower` | 花旋转 | 花朵旋转动画 |
| `motion_Love1` | 爱心氛围 1 | 爱心特效 1 |
| `Param2` | 哈气缩放显示隐藏 | 哈气动画 |
| `Param3` | 摸脸 手指动 | 摸脸手指 |
| `Param4` | 摸脸 手臂动 | 摸脸手臂 |
| `Param5` | 摸头 大拇指动 | 摸头拇指 |
| `Key38` | 摸头 显示隐藏 | 摸头显隐 |
| `Param6` | 摸头 位置X | 摸头X位置 |
| `Param7` | 摸头 位置Y | 摸头Y位置 |
| `Param8` | 猫爪抓抓 | 猫爪动作 |
| `Param9` | 蝴蝶结 1 | 蝴蝶结动画 1 |
| `Param10` | 蝴蝶结 2 | 蝴蝶结动画 2 |
| `motion_Love2` | 爱心氛围 2 | 爱心特效 2 |
| `motion_Love3` | 爱心眼缩放 | 爱心眼缩放 |
| `aixinbutoumingdu` | 爱心 不透明度 | 爱心透明 |
| `CircleTheEyes4` | 爱心左半边 | 爱心左眼 |
| `CircleTheEyes5` | 爱心右半边 | 爱心右眼 |
| `CircleTheEyes13` | 爱心扩散1 | 爱心扩散 1 |
| `CircleTheEyes17` | 爱心不透明度1 | 爱心透明 1 |
| `CircleTheEyes14` | 爱心扩散2 | 爱心扩散 2 |
| `CircleTheEyes18` | 爱心不透明度2 | 爱心透明 2 |
| `CircleTheEyes19` | 爱心整体放大 | 爱心放大 |
| `CircleTheEyes6` | 手指弯曲1 | 手指弯 1 |
| `CircleTheEyes7` | 手指弯曲2 | 手指弯 2 |
| `CircleTheEyes12` | 手指弯曲3 | 手指弯 3 |
| `CircleTheEyes8` | 手腕旋转 | 手腕旋转 |
| `CircleTheEyes9` | 手肘旋转 | 手肘旋转 |
| `CircleTheEyes10` | 肩膀旋转 | 肩膀旋转 |
| `CircleTheEyes11` | 手臂高低 | 手臂高度 |
| `CircleTheEyes20` | 肩膀高低 | 肩膀高度 |
| `CircleTheEyes15` | 爱心不透明度 | 爱心透明 |
| `CircleTheEyes16` | 爱心缩放 | 爱心缩放 |
| `CircleTheEyes2` | 瞳孔圆圈 | 瞳孔圆圈 |
| `CircleTheEyes3` | 瞳孔圆圈透明度 | 瞳孔圆圈透明 |
| `WavyTears1` | 波浪泪眼 变形 | 泪眼变形 |
| `WavyTears2` | 波浪泪眼 旋转 | 泪眼旋转 |
| `Fan_Shoulder` | 扇子 肩膀 | 扇子肩膀 |
| `FanElbow` | 扇子 手肘 | 扇子手肘 |
| `FanWrist` | 扇子 手腕 | 扇子手腕 |
| `FanWrist2` | 扇扇子 | 扇动扇子 |
| `FanWrist3` | 扇子流苏修正 | 扇子流苏 |

---

## 10. 其他参数

### 10.1 吉祥物 (ParamGroup16 - 吉祥物)

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `HeadAngleX2` | 吉祥物 X | 吉祥物X旋转 |
| `HeadAngleY2` | 吉祥物 Y | 吉祥物Y旋转 |
| `HeadAngleZ2` | 吉祥物 Z | 吉祥物Z旋转 |
| `EyeHighlight1` | 吉祥物 眼睛高光1 | 吉祥物高光 1 |
| `EyeHighlight2` | 吉祥物 眼睛高光2 | 吉祥物高光 2 |
| `EyeLOpen2` | 手上吉祥物 眼睛开闭 | 手持吉祥物眼 |
| `EyeHighlight3` | 手上吉祥物 眼睛高光1 | 手持吉祥物高光 1 |
| `EyeHighlight4` | 手上吉祥物 眼睛高光2 | 手持吉祥物高光 2 |

### 10.2 无分组参数

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `Open_bianQ2` | 变Q九轴修正 | Q版九轴修正 |
| `Open_bianQ3` | 变Q手臂调整 | Q版手臂调整 |
| `Open_bianQ4` | 变Q身体大前倾阴影修正 | Q版阴影修正 |
| `Open_bianQ5` | 变Q话筒手修正1 | Q版话筒手修正 |
| `Open_bianQ6` | 变Q比心手修正1 | Q版比心手修正 |
| `ParamBreath` | ●呼吸 | 呼吸动画 |

### 10.3 元信息参数

| 参数 ID | 名称 | 说明 |
|---------|------|------|
| `Open_EyeMask2` | 画师：茄梦 | 画师信息 |
| `Open_EyeMask3` | 建模：小小时溪 | 建模师信息 |
| `Open_EyeMask4` | 去水印 | 水印控制 |
| `Open_toushi` | ███ 头部 ███ | 头部区域标记 |
| `Open_fushi` | ███ 身体 ███ | 身体区域标记 |
| `Open_fushi3` | ███ 手势 ███ | 手势区域标记 |
| `Open_fushi2` | ███ 互动动作 ███ | 互动区域标记 |
| `Open_fushi5` | ███ 其他 ███ | 其他区域标记 |
| `Open_fushi4` | ███ 自定义改色 ███ | 改色区域标记 |
| `fuzhu3` | ███ 控制器 ███ | 控制器标记 |
| `fuzhu_4` | ███ 头XY ███ | 头XY标记 |
| `fuzhu2` | ███ 动画 ███ | 动画标记 |
| `fuzhu_2` | ███ 眼 ███ | 眼标记 |
| `fuzhu_19` | ███ 眉 ███ | 眉标记 |
| `fuzhu_3` | ███ 口 ███ | 口标记 |
| `fuzhu_5` | ███ 身体XY ███ | 身体XY标记 |
| `fuzhu_6` | ███ 眼物理 ███ | 眼物理标记 |
| `fuzhu_7` | ███ 头物理 ███ | 头物理标记 |
| `fuzhu_9` | ███ 身体物理 ███ | 身体物理标记 |

---

## 11. WebSocket 操作指南

### 11.1 连接到 Live2D WebSocket

```javascript
// 连接到 VTube Studio 或 Live2DViewerEX 的 WebSocket
const ws = new WebSocket('ws://localhost:8001'); // VTube Studio 默认端口

ws.onopen = () => {
  console.log('Connected to Live2D WebSocket');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### 11.2 VTube Studio API 示例

#### 发送参数更新 (实时动捕)

```javascript
// 发送面部追踪数据到 VTube Studio
function sendFaceTrackingData(faceData) {
  const message = {
    apiName: "VTubeStudioPublicAPI",
    apiVersion: "1.0",
    requestID: "face-tracking-001",
    messageType: "InjectParameterDataRequest",
    data: {
      faceFound: true,
      mode: "default",
      parameterValues: [
        // ===== 核心动捕参数 =====
        { id: "ParamAngleX", value: faceData.headX },      // 头X: -30 ~ 30
        { id: "ParamAngleY", value: faceData.headY },      // 头Y: -30 ~ 30
        { id: "ParamAngleZ", value: faceData.headZ },      // 头Z: -30 ~ 30
        { id: "ParamEyeBallX", value: faceData.eyeX },     // 眼X: -1 ~ 1
        { id: "ParamEyeBallY", value: faceData.eyeY },     // 眼Y: -1 ~ 1
        { id: "ParamBodyAngleX", value: faceData.bodyX },  // 身体X: -10 ~ 10
        { id: "ParamBodyAngleY", value: faceData.bodyY },  // 身体Y: -10 ~ 10
        { id: "ParamBodyAngleZ", value: faceData.bodyZ },  // 身体Z: -10 ~ 10
        
        // ===== 眼睛开闭 =====
        { id: "ParamEyeLOpen", value: faceData.leftEyeOpen },   // 0 ~ 1
        { id: "ParamEyeROpen", value: faceData.rightEyeOpen },  // 0 ~ 1
        
        // ===== 嘴巴控制 =====
        { id: "ParamMouthOpenY", value: faceData.mouthOpen },   // 0 ~ 1
        { id: "ParamMouthForm", value: faceData.mouthForm },    // -1 ~ 1
        
        // ===== 眉毛控制 =====
        { id: "ParamBrowLY", value: faceData.browLeftY },      // -1 ~ 1
        { id: "ParamBrowRY", value: faceData.browRightY },     // -1 ~ 1
        { id: "ParamBrowLForm", value: faceData.browLeftForm }, // -1 ~ 1
        { id: "ParamBrowRForm", value: faceData.browRightForm } // -1 ~ 1
      ]
    }
  };
  
  ws.send(JSON.stringify(message));
}
```

#### 切换功能按键 (Key 参数)

```javascript
// 触发表情/装饰开关 (Key 参数是 0/1 开关)
function toggleKey(keyId, enabled) {
  const message = {
    apiName: "VTubeStudioPublicAPI",
    apiVersion: "1.0",
    requestID: `key-toggle-${Date.now()}`,
    messageType: "InjectParameterDataRequest",
    data: {
      parameterValues: [
        { id: keyId, value: enabled ? 1.0 : 0.0 }
      ]
    }
  };
  
  ws.send(JSON.stringify(message));
}

// 示例：启用星星眼表情
toggleKey("Key17", true);  // ● 星星眼 ON
toggleKey("Key17", false); // ● 星星眼 OFF

// 示例：显示头顶小猫
toggleKey("Key44", true);  // ● 头顶小猫 ON

// 示例：切换头发颜色
toggleKey("Key2", true);   // ● 头发换色
```

#### 常用的 Key 开关参考

```javascript
const KEY_MAPPING = {
  // 表情类
  HAPPY:     { id: "Key11", name: "哈气" },
  ANGRY:     { id: "Key14", name: "生气" },
  BLUSH:     { id: "Key21", name: "红脸" },
  BLACK_FACE:{ id: "Key30", name: "黑脸" },
  STARS:     { id: "Key17", name: "星星眼" },
  SCISSORS:  { id: "Key16", name: "剪刀眼" },
  CRY:       { id: "Key20", name: "哭哭" },
  DAZED:     { id: "Key15", name: "呆" },
  
  // 装饰类
  CAT_EARS:  { id: "Key44", name: "头顶小猫" },
  GLASSES:   { id: "Key29", name: "LOOK眼镜" },
  EYEPATCH:  { id: "Key13", name: "黑眼罩" },
  TRASH_BAG: { id: "Key36", name: "垃圾袋" },
  
  // 换色类
  EYE_COLOR: { id: "Key1", name: "眼睛换色" },
  HAIR_COLOR:{ id: "Key2", name: "头发换色" },
  CAT_EAR_COLOR:{ id: "Key41", name: "猫耳换色" },
  CLOTHES_COLOR:{ id: "Key7", name: "衣服换色" },
  
  // 手势类
  WAVE:      { id: "Key12", name: "挥手" },
  HEART:     { id: "Key32", name: "比心" },
  PHONE:     { id: "Key34", name: "手机" },
  MIC:       { id: "Key33", name: "话筒" },
  CAT_PAW:   { id: "Key35", name: "猫爪" },
  WINE:      { id: "Key31", name: "端酒" },
  
  // 特殊效果
  FLYING_HEAD:{ id: "Key22", name: "飞头" },
  NO_NECK:   { id: "Key23", name: "脖子消失" },
  Q_MODE:    { id: "Key26", name: "变Q" },
  LIFT_FOOT: { id: "Key27", name: "抬脚" },
  
  // 互动
  PINCH_FACE:{ id: "Key37", name: "捏脸" },
  TOUCH_FACE:{ id: "Key39", name: "摸脸" }
};
```

### 11.3 Live2DViewerEX WebSocket API

```javascript
// Live2DViewerEX 使用不同的消息格式
function sendToLive2DViewerEX(paramId, value) {
  const message = {
    type: 'set',
    model: '奶牛猫花丸_完整版',  // 模型名称
    param: paramId,
    value: value
  };
  
  ws.send(JSON.stringify(message));
}

// 批量发送参数
function batchUpdateParameters(params) {
  const message = {
    type: 'batch',
    model: '奶牛猫花丸_完整版',
    parameters: params
  };
  
  ws.send(JSON.stringify(message));
}

// 使用示例
batchUpdateParameters([
  { id: 'ParamAngleX', value: 15 },
  { id: 'ParamAngleY', value: -10 },
  { id: 'ParamEyeBallX', value: 0.5 },
  { id: 'Key17', value: 1 }  // 星星眼
]);
```

### 11.4 参数值范围参考

| 参数类型 | 典型范围 | 默认值 | 说明 |
|---------|----------|--------|------|
| 头部旋转 (ParamAngleX/Y/Z) | -30 ~ 30 | 0 | 角度制 |
| 眼球移动 (ParamEyeBallX/Y) | -1 ~ 1 | 0 | 归一化 |
| 身体旋转 (ParamBodyAngleX/Y/Z) | -10 ~ 10 | 0 | 角度制 |
| 眼睛开闭 (ParamEyeLOpen/ROpen) | 0 ~ 1 | 1 | 0=闭眼 |
| 嘴巴开闭 (ParamMouthOpenY) | 0 ~ 1 | 0 | 0=闭合 |
| 嘴型变形 (ParamMouthForm) | -1 ~ 1 | 0 | -1=咧嘴, 1=嘟嘴 |
| 眉毛位置 (ParamBrowLY/RY) | -1 ~ 1 | 0 | -1=下压, 1=上扬 |
| 按键开关 (KeyX) | 0 或 1 | 0 | 布尔值 |
| 自定义颜色 (Key45-56) | 0 ~ 1 | 0 | RGB通道 |

### 11.5 动捕接管最佳实践

```javascript
class Live2DController {
  constructor() {
    this.isTracking = false;
    this.ws = null;
    this.enabledKeys = new Set();
  }
  
  connect(url = 'ws://localhost:8001') {
    this.ws = new WebSocket(url);
    return new Promise((resolve, reject) => {
      this.ws.onopen = () => resolve();
      this.ws.onerror = reject;
    });
  }
  
  // 启用/禁用动捕模式
  setTracking(enabled) {
    this.isTracking = enabled;
  }
  
  // 发送动捕帧数据
  sendTrackingFrame(data) {
    if (!this.isTracking || !this.ws) return;
    
    const params = [
      // 核心动捕参数
      { id: 'ParamAngleX', value: this.clamp(data.yaw, -30, 30) },
      { id: 'ParamAngleY', value: this.clamp(data.pitch, -30, 30) },
      { id: 'ParamAngleZ', value: this.clamp(data.roll, -30, 30) },
      { id: 'ParamEyeBallX', value: this.clamp(data.eyeX, -1, 1) },
      { id: 'ParamEyeBallY', value: this.clamp(data.eyeY, -1, 1) },
      { id: 'ParamBodyAngleX', value: this.clamp(data.bodyX, -10, 10) },
      { id: 'ParamBodyAngleY', value: this.clamp(data.bodyY, -10, 10) },
      { id: 'ParamEyeLOpen', value: data.leftEyeOpen ? 1 : 0 },
      { id: 'ParamEyeROpen', value: data.rightEyeOpen ? 1 : 0 },
      { id: 'ParamMouthOpenY', value: this.clamp(data.mouthOpen, 0, 1) }
    ];
    
    this.sendBatch(params);
  }
  
  // 触发按键表情
  triggerExpression(keyId, duration = 3000) {
    // 开启
    this.setParameter(keyId, 1);
    this.enabledKeys.add(keyId);
    
    // 自动关闭
    if (duration > 0) {
      setTimeout(() => {
        this.setParameter(keyId, 0);
        this.enabledKeys.delete(keyId);
      }, duration);
    }
  }
  
  // 设置单个参数
  setParameter(id, value) {
    if (!this.ws) return;
    this.ws.send(JSON.stringify({
      type: 'set',
      param: id,
      value: value
    }));
  }
  
  // 批量设置
  sendBatch(params) {
    if (!this.ws) return;
    this.ws.send(JSON.stringify({
      type: 'batch',
      parameters: params
    }));
  }
  
  clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
  }
  
  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }
}

// 使用示例
const controller = new Live2DController();
await controller.connect();

// 启用动捕接管
controller.setTracking(true);

// 从摄像头获取面部数据并发送
// (需要配合 face-api.js 或 MediaPipe)
setInterval(() => {
  const faceData = getFaceDataFromCamera(); // 你的面部识别代码
  controller.sendTrackingFrame(faceData);
}, 1000 / 30); // 30 FPS

// 触发星星眼表情 (持续3秒)
controller.triggerExpression('Key17', 3000);
```

---

## 📊 参数统计

| 分类 | 参数数量 | 说明 |
|------|----------|------|
| 核心动捕参数 | 17 | 需要实时接管的关键参数 |
| 功能按键 (KeyX) | 37 | 装饰/表情/动作的开关 |
| 物理效果参数 | 154 | 头发/衣服/尾巴等物理 |
| 动画参数 | 41 | 内置动画效果 |
| 其他 | 29 | 辅助/标记参数 |
| **总计** | **278** | 全部可控制参数 |

---

## 🎯 快速参考

### 必须接管的动捕参数 (17个)
```
ParamAngleX, ParamAngleY, ParamAngleZ       // 头部
ParamEyeBallX, ParamEyeBallY                // 眼球
ParamBodyAngleX, ParamBodyAngleY, ParamBodyAngleZ  // 身体
ParamEyeLOpen, ParamEyeROpen                // 眼睛开闭
ParamMouthOpenY, ParamMouthForm             // 嘴巴
ParamBrowLY, ParamBrowRY                    // 眉毛上下
ParamBrowLForm, ParamBrowRForm              // 眉毛形状
ParamBreath                                 // 呼吸
```

### 常用的表情按键
```
Key11 - 哈气    Key14 - 生气    Key21 - 红脸
Key17 - 星星眼  Key16 - 剪刀眼  Key20 - 哭哭
Key30 - 黑脸    Key15 - 呆
```

### 常用的装饰按键
```
Key44 - 头顶小猫    Key29 - LOOK眼镜    Key13 - 黑眼罩
Key36 - 垃圾袋      Key18 - 叼猫条      Key19 - 叼内裤
```

### 手势动作按键
```
Key12 - 挥手    Key31 - 端酒    Key32 - 比心
Key33 - 话筒    Key34 - 手机    Key35 - 猫爪
```

---

*文档生成完毕！喵~ 🐱*
