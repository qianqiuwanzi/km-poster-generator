#!python3
"""debug_height.py — 对比两个 HTML 文件的 poster 高度。

用于开发时对比当前 build (poster_build.html) 与原始参考 (poster.html)
的 poster 区域高度，验证布局修改后高度一致性。

用法:
    python tools/debug_height.py
"""

from playwright.sync_api import sync_playwright
import pathlib

SKILL = pathlib.Path(__file__).resolve().parent.parent
PROJ = pathlib.Path(r"D:\OpenClaw\workspace\project\knowledge-card-journal-skill")
files = {
    "build(T+content)": SKILL / "poster_build.html",
    "orig(poster.html)": PROJ / "poster.html",
}

with sync_playwright() as p:
    b = p.chromium.launch()
    for name, f in files.items():
        if not f.exists():
            print(f"SKIP {name}: file not found ({f})")
            continue
        pg = b.new_page(viewport={"width": 1100, "height": 1480})
        pg.goto("file://" + str(f))
        pg.wait_for_timeout(1800)
        H = pg.evaluate("document.querySelector('.poster').getBoundingClientRect().height")
        cw = pg.evaluate(
            "(document.querySelector('.character-wrap')||{getBoundingClientRect:function(){return{height:0}}}).getBoundingClientRect().height"
        )
        print(name, "posterH=", round(H), "charWrapH=", round(cw))
        pg.close()
    b.close()
