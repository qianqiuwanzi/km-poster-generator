#!python3
# km-poster-generator: 把 content.json 填入 template.html 并渲染知识图海报
import argparse, json, math, pathlib, sys, re
from playwright.sync_api import sync_playwright

SKILL = pathlib.Path(__file__).resolve().parent

# ── 渲染常量 ──────────────────────────────────────────────────
TARGET_CONTENT_HEIGHT = 1400   # 压缩目标高：使含 margin+阴影后整体 ≈ 3:4
COMPRESS_STEP = 0.96           # 每轮压缩比例（乘性）
MIN_COMPRESS_FACTOR = 0.80     # 压缩因子下限，低于此值改用 zoom 兜底
COMPRESS_WAIT_MS = 30          # 每轮压缩后等待（ms）
INITIAL_WAIT_MS = 1500         # 页面加载后初始等待（ms）
VIEWPORT_PAD = 14              # 视口额外余量（px）
CLIP_PAD = 12                  # 截图裁剪余量（容纳 box-shadow 6px + 余量）
GAP_MARGIN_BOTTOM = 20         # blocks-grid 底部缝隙（px）
GAP_MARGIN_TOP = 18            # bottom-area 顶部缝隙（px）
GAP_MARGIN_BOTTOM_AREA = 20    # bottom-area 底部缝隙（px）
SCALE_FACTOR = 2               # Playwright device_scale_factor
DEFAULT_VIEWPORT_WIDTH = 1120
DEFAULT_VIEWPORT_HEIGHT = 1500

# ── 字符图默认路径 ────────────────────────────────────────────
DEFAULT_CHARACTERS = {
    "hero":  "assets/characters/主图_rb.png",
    "card1": "assets/characters/卡1_rb.png",
    "card2": "assets/characters/卡2_rb.png",
    "card3": "assets/characters/卡3_rb.png",
    "card4": "assets/characters/卡4_rb.png",
}

# ── 模板占位符 → content.json 路径映射 ───────────────────────
# 格式: "{{placeholder}}" → ("top_level_key", "nested_key", ...)
# 用于 build_html() 从 content dict 自动取值填充
PLACEHOLDER_MAP = {
    # 顶部
    "title":    ("title",),       "subtitle": ("subtitle",),
    # 引言
    "intro":    ("intro",),
    # 色块卡 b1
    "b1_title":      ("b1", "title"),      "b1_item1":   ("b1", "item1"),
    "b1_item2":      ("b1", "item2"),      "b1_barlabel": ("b1", "barlabel"),
    "b1_bar":        ("b1", "bar"),        "b1_barcolor": ("b1", "barcolor"),
    "b1_highlight":  ("b1", "highlight"),
    # 色块卡 b2
    "b2_title":      ("b2", "title"),      "b2_item1":   ("b2", "item1"),
    "b2_item2":      ("b2", "item2"),      "b2_barlabel": ("b2", "barlabel"),
    "b2_bar":        ("b2", "bar"),        "b2_barcolor": ("b2", "barcolor"),
    "b2_highlight":  ("b2", "highlight"),
    # 色块卡 b3
    "b3_title":      ("b3", "title"),      "b3_item1":   ("b3", "item1"),
    "b3_item2":      ("b3", "item2"),      "b3_barlabel": ("b3", "barlabel"),
    "b3_bar":        ("b3", "bar"),        "b3_barcolor": ("b3", "barcolor"),
    "b3_highlight":  ("b3", "highlight"),
    # 色块卡 b4（含 mini-stats）
    "b4_title":      ("b4", "title"),      "b4_item1":   ("b4", "item1"),
    "b4_item2":      ("b4", "item2"),      "b4_barlabel": ("b4", "barlabel"),
    "b4_bar":        ("b4", "bar"),        "b4_barcolor": ("b4", "barcolor"),
    "b4_highlight":  ("b4", "highlight"),
    "b4_m1":         ("b4", "m1"),         "b4_m1l":     ("b4", "m1l"),
    "b4_m2":         ("b4", "m2"),         "b4_m2l":     ("b4", "m2l"),
    "b4_m3":         ("b4", "m3"),         "b4_m3l":     ("b4", "m3l"),
    # 核心收获
    "sum_label":     ("sum", "label"),     "sum_main":    ("sum", "main"),
    "sum_sub":       ("sum", "sub"),
    # 页脚
    "footer":        ("footer",),
}

# ── 角色图占位符（渲染为 <img src="..."> 片段，在 template 中用 {{{...}}} 代替 {{...}}） ──
CHARACTER_PLACEHOLDERS = ["char_hero", "char_card1", "char_card2", "char_card3", "char_card4"]
CHARACTER_KEYS = ["hero", "card1", "card2", "card3", "card4"]


def _get_nested(d, path):
    """按路径元组从嵌套 dict 取值，自动转为字符串。"""
    for key in path:
        d = d[key]
    return str(d)


def validate_content(content, schema_path=None):
    """校验 content.json 是否符合 schema。返回 (ok: bool, errors: list[str])。"""
    if schema_path is None:
        schema_path = SKILL / "content.schema.json"
    try:
        import jsonschema
        schema = json.loads(pathlib.Path(schema_path).read_text(encoding="utf-8"))
        v = jsonschema.Draft202012Validator(schema)
        errs = sorted(v.iter_errors(content), key=lambda e: ".".join(map(str, e.absolute_path)))
        if errs:
            msgs = []
            for e in errs:
                path = ".".join(map(str, e.absolute_path)) or "(root)"
                msgs.append(f"  {path}: {e.message}")
            return False, msgs
        return True, []
    except ImportError:
        # jsonschema 未安装时跳过校验，打印提示
        sys.stderr.write("WARN: jsonschema not installed, skipping content validation\n"
                         "     pip install jsonschema\n")
        return True, []
    except FileNotFoundError:
        sys.stderr.write("WARN: content.schema.json not found, skipping validation\n")
        return True, []


def build_html(c, template):
    """用 content dict 填充 template 中的占位符。"""
    h = template

    # 1) 文本占位符：{{key}} → 从 content 映射取值
    for placeholder, path in PLACEHOLDER_MAP.items():
        h = h.replace("{{%s}}" % placeholder, _get_nested(c, path))

    # 2) 标签 HTML：{{tags_html}} → 生成 <span class="tag">…</span>
    tags_html = "\n".join('  <span class="tag">%s</span>' % t for t in c["tags"])
    h = h.replace("{{tags_html}}", tags_html)

    # 3) 角色图：{{{char_xxx}}} → 替换为图片路径（可被 content.characters 覆盖）
    chars = {**DEFAULT_CHARACTERS, **c.get("characters", {})}
    for placeholder, key in zip(CHARACTER_PLACEHOLDERS, CHARACTER_KEYS):
        token = "{{{" + placeholder + "}}}"
        h = h.replace(token, chars[key])

    # 4) 检查未解析占位符
    left = re.findall(r"\{\{[^}]+\}\}", h)
    if left:
        sys.stderr.write("WARN unresolved placeholders: %s\n" % sorted(set(left)))

    return h


def render(html_path, out_path):
    """Playwright 渲染 HTML → PNG，含自适应压缩 + 裁切检测。"""
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:
            sys.exit(f"ERROR: 无法启动 Chromium 浏览器: {e}\n"
                     f"       请确认已安装: playwright install chromium")

        try:
            pg = browser.new_page(
                viewport={"width": DEFAULT_VIEWPORT_WIDTH, "height": DEFAULT_VIEWPORT_HEIGHT},
                device_scale_factor=SCALE_FACTOR,
            )
            pg.goto("file://" + str(html_path))
            pg.wait_for_load_state("networkidle")
            pg.wait_for_timeout(INITIAL_WAIT_MS)

            def measure():
                return pg.evaluate("document.querySelector('.poster').scrollHeight")

            H = measure()
            factor = 1.0
            iteration = 0
            max_iterations = 20  # 安全上限

            while H > TARGET_CONTENT_HEIGHT and factor > MIN_COMPRESS_FACTOR and iteration < max_iterations:
                iteration += 1
                factor *= COMPRESS_STEP
                pg.evaluate("""(function(f){
                  document.querySelectorAll('.poster *').forEach(function(el){
                    var cs=getComputedStyle(el);
                    ['marginTop','marginBottom','paddingTop','paddingBottom','gap','rowGap','columnGap']
                      .forEach(function(pr){var v=parseFloat(cs[pr]); if(v>0) el.style[pr]=(v*f)+'px';});
                  });
                })(%f)""" % factor)
                pg.wait_for_timeout(COMPRESS_WAIT_MS)
                H = measure()

            print(f"after compress: factor={factor:.3f}, height={H:.0f}  (iterations={iteration})")

            # 保留可见缝隙（覆盖压缩造成的贴紧）
            pg.evaluate("""(function(){
              document.querySelector('.blocks-grid').style.marginBottom='%dpx';
              document.querySelector('.bottom-area').style.marginTop='%dpx';
              document.querySelector('.bottom-area').style.marginBottom='%dpx';
            })()""" % (GAP_MARGIN_BOTTOM, GAP_MARGIN_TOP, GAP_MARGIN_BOTTOM_AREA))
            pg.wait_for_timeout(COMPRESS_WAIT_MS)
            H = measure()
            print(f"after gap-set: height={H:.0f}")

            # 兜底缩放
            if H > TARGET_CONTENT_HEIGHT:
                s = TARGET_CONTENT_HEIGHT / H
                pg.evaluate("document.querySelector('.poster').style.zoom = '%f'" % s)
                pg.wait_for_timeout(COMPRESS_WAIT_MS)
                H = measure()
                print(f"zoom fallback: scale={s:.3f}, height={H:.0f}")

            pb = pg.locator(".poster").bounding_box()
            if pb is None:
                sys.exit("ERROR: 无法获取 .poster 元素的 bounding_box，请检查 HTML 结构")

            print(f"poster box: x={pb['x']:.0f} y={pb['y']:.0f} w={pb['width']:.0f} h={pb['height']:.0f} "
                  f"bottom={pb['y']+pb['height']:.0f}")

            # 视口高度跟随海报真实高度（含 margin + 阴影余量），保证零裁切
            vw = math.ceil(pb["x"] + pb["width"]) + VIEWPORT_PAD
            vh = math.ceil(pb["y"] + pb["height"]) + VIEWPORT_PAD
            pg.set_viewport_size({"width": int(vw), "height": int(vh)})
            pg.wait_for_timeout(150)

            clip = {
                "x": pb["x"] - CLIP_PAD,
                "y": pb["y"] - CLIP_PAD,
                "width": pb["width"] + CLIP_PAD * 2,
                "height": pb["height"] + CLIP_PAD * 2,
            }

            # 裁切检测：验证 footer 是否在 clip 范围内
            fb = pg.locator(".footer").bounding_box()
            if fb is None:
                sys.stderr.write("WARN: 无法获取 .footer bounding_box，跳过裁切检测\n")
            else:
                footer_bottom = fb["y"] + fb["height"]
                clip_bottom = clip["y"] + clip["height"]
                ok = footer_bottom <= clip_bottom
                print(f"footer bottom={footer_bottom:.0f}  (clip bottom={clip_bottom:.0f}) "
                      f"-> {'OK' if ok else 'CLIPPED'}")
                if not ok:
                    sys.stderr.write("WARN: 页脚可能被裁切！请检查 content 文案长度或手动调整模板。\n")

            pg.screenshot(path=str(out_path), clip=clip)

        except Exception as e:
            sys.exit(f"ERROR: 渲染过程异常: {e}")

        finally:
            browser.close()


def main():
    ap = argparse.ArgumentParser(
        description="km-poster-generator: 从 content.json + template.html 生成知识海报 PNG"
    )
    ap.add_argument("--content", default=str(SKILL / "content.json"),
                    help="content.json 路径 (默认: content.json)")
    ap.add_argument("--template", default=str(SKILL / "template.html"),
                    help="HTML 模板路径 (默认: template.html)")
    ap.add_argument("--out", default=str(SKILL / "output" / "poster.png"),
                    help="输出 PNG 路径 (默认: output/poster.png)")
    ap.add_argument("--skip-validation", action="store_true",
                    help="跳过 content.json schema 校验")
    args = ap.parse_args()

    # 读取 content.json
    content_path = pathlib.Path(args.content)
    if not content_path.exists():
        sys.exit(f"ERROR: content.json 不存在: {content_path}")
    try:
        c = json.loads(content_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        sys.exit(f"ERROR: content.json 解析失败: {e}")
    except Exception as e:
        sys.exit(f"ERROR: 读取 content.json 失败: {e}")

    # Schema 校验
    if not args.skip_validation:
        ok, errs = validate_content(c)
        if not ok:
            sys.exit("ERROR: content.json 校验失败:\n" + "\n".join(errs))

    # 读取模板
    tpl_path = pathlib.Path(args.template)
    if not tpl_path.exists():
        sys.exit(f"ERROR: 模板文件不存在: {tpl_path}")
    try:
        tpl = tpl_path.read_text(encoding="utf-8")
    except Exception as e:
        sys.exit(f"ERROR: 读取模板失败: {e}")

    # 填充模板
    html = build_html(c, tpl)

    # 写出中间产物
    filled = SKILL / "poster_build.html"
    filled.write_text(html, encoding="utf-8")

    # 输出目录
    op = pathlib.Path(args.out)
    op.parent.mkdir(parents=True, exist_ok=True)

    # 渲染
    render(filled, op)
    print("rendered ->", op)


if __name__ == "__main__":
    main()
