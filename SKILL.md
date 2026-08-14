# km-poster-generator

生成「阿甜米色手帐风 · 知识图」3:4 小红书种草海报。固定 **5 个 3D 角色**（同一卡通女孩换姿势）+ 顶部标签/标题 + 2×2 色块分类 + 核心收获黑区 + 底部三张行动卡。数据驱动：只改 `content.json` 即可复现同款布局 / 人物 / 装饰 / 配色。

## 何时用
- 用户要「知识图」「知识卡片海报」「3:4 信息图」「小红书种草长图」，且指定或默认这种**带人物 IP + 卷轴元素 + 四大色块分类**的手绘插画风。
- 需要复刻已定稿的视觉：米色背景、胶带/贴纸装饰、卡通女孩 IP 贯穿、四色块（黄/橙/绿/粉）分类。

## 不要用
- 不要替换 `assets/characters/` 下的 5 张角色图（已透明抠图、固定对应模板 8 个 char-slot）。要换角色需重新 AI 生图 → rembg 抠图 → 改 `template.html` 的 img src。
- 不要改 `template.html` 的结构 / CSS（布局已校准到 3:4 不裁切：自适应压缩 + 动态视口 + 精确 clip）。改文案只走 `content.json`。

## 使用流程
1. 编辑 `content.json`（**只改值，不动键名/结构**）：
   - `title` / `subtitle`：顶部大标题 + 英文风副标题
   - `tags`：4 个标签（emoji + 词）
   - `intro`：引言气泡，支持 `<strong>` `<em>` `<br>`
   - `b1`~`b4`：四个色块卡片
     - `b1`/`b2`/`b3`：`{title, item1, item2, barlabel, bar, barcolor, highlight}`
     - `b4`：额外 `{m1, m1l, m2, m2l, m3, m3l}`（三项指标：值+标签）
     - `barcolor` 用 `#2C2C2C`（深）/ `#E85A9C`（粉）交替
   - `sum`：底部黑色核心收获区 `{label, main, sub}`
   - `footer`：页脚
   - `characters`（**可选**）：覆盖角色图路径 `{hero, card1, card2, card3, card4}`。不填则使用默认角色。
2. 运行：
   ```bash
   python generate.py
   # 可选参数：
   #   --content 路径    content.json 路径（默认: content.json）
   #   --template 路径   HTML 模板路径（默认: template.html）
   #   --out 路径        输出 PNG 路径（默认: output/poster.png）
   #   --skip-validation 跳过 content.json schema 校验
   ```
3. 产物：`output/poster.png`（约 1080×1440 类 3:4，角色透明融合、边缘干净）

## Schema 校验

`generate.py` 运行时会自动校验 `content.json` 是否符合 `content.schema.json`。校验依赖 `jsonschema` 库：
```bash
pip install jsonschema
```
校验失败会给出具体错误字段和原因，不会生成错误海报。`--skip-validation` 可跳过校验。

## 运行测试

```bash
# 单元测试（无需浏览器，秒级完成）
pytest tests/test_poster.py -v -k "not slow and not integration"

# 完整测试（含渲染管线，需要 Playwright）
pytest tests/test_poster.py -v
```

## 渲染说明
`generate.py` 内嵌自适应逻辑（与定稿 v9 同源）：Playwright 打开填充后的 HTML → 按比例压缩子元素 margin/padding/gap 使内容高≈1400（**保持字号**）→ 2×2 色块 / 核心收获 / 底部三卡之间留 20px 缝隙（避免压缩贴紧）→ 视口高度跟随海报真实右下角位置 + 精确 `bounding_box` clip（含 12px 阴影余量），保证最外框、页脚、底部三卡**零裁切**。`device_scale_factor=2`，输出约 1080×1440 类 3:4。

## 目录资产
- `template.html`：占位符模板（54 个 `{{...}}` + 5 个 `{{{char_xxx}}}` 角色图占位符，勿改结构）
- `content.json`：示例数据（智商藏不住 文案，可直接改）
- `content.schema.json`：JSON Schema 校验定义（自动校验 content.json 结构）
- `generate.py`：填充 + 渲染（固化渲染器，避免裁切回归）
- `assets/characters/`：5 张透明抠图角色（主图 / 卡1~卡4，后缀 `_rb.png`）
- `poster_build.html`：运行时临时产物（可删，每次运行覆盖）
- `tools/`：调试工具脚本
  - `debug_height.py`：对比两个 HTML 的 poster 高度
  - `debug_sections.py`：打印各区块渲染高度
- `tests/`：回归测试套件
