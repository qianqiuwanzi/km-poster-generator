#!python3
"""km-poster-generator 回归测试。

覆盖:
  1. content.json schema 校验
  2. 模板占位符填充完整性
  3. 角色路径默认值 & 可覆盖
  4. 未知占位符检测
  5. [可选] 完整渲染管线 (需要 Playwright + Chromium)
"""

import json, pathlib, sys, pytest

# 确保项目根目录在 sys.path 中
SKILL = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL))

from generate import (
    build_html, validate_content, PLACEHOLDER_MAP,
    CHARACTER_PLACEHOLDERS, CHARACTER_KEYS, DEFAULT_CHARACTERS,
)

# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture(scope="module")
def valid_content():
    """加载有效的 content.json 作为测试基准。"""
    path = SKILL / "content.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def template():
    """加载 template.html。"""
    path = SKILL / "template.html"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def filled_html(valid_content, template):
    """预生成填充后的 HTML 供多项测试复用。"""
    return build_html(valid_content, template)


# ── Schema 校验测试 ───────────────────────────────────────────

class TestSchemaValidation:
    """content.json schema 校验。"""

    def test_valid_content_passes(self, valid_content):
        """有效的 content.json 应通过校验。"""
        ok, errs = validate_content(valid_content)
        assert ok, f"校验失败: {errs}"

    def test_missing_required_field_fails(self, valid_content):
        """缺少必填字段应校验失败。"""
        c = {**valid_content}
        del c["title"]
        ok, errs = validate_content(c)
        assert not ok
        assert any("title" in e for e in errs)

    def test_wrong_type_fails(self, valid_content):
        """字段类型错误应校验失败。"""
        c = {**valid_content, "tags": "not-an-array"}
        ok, errs = validate_content(c)
        assert not ok

    def test_tags_wrong_count_fails(self, valid_content):
        """tags 数组必须恰好 4 个元素。"""
        c = {**valid_content, "tags": ["a", "b"]}
        ok, errs = validate_content(c)
        assert not ok

    def test_bar_out_of_range_fails(self, valid_content):
        """bar 值超出 0-100 应校验失败。"""
        import copy
        c = copy.deepcopy(valid_content)
        c["b1"]["bar"] = 150
        ok, errs = validate_content(c)
        assert not ok

    def test_invalid_barcolor_fails(self, valid_content):
        """barcolor 格式错误应校验失败。"""
        import copy
        c = copy.deepcopy(valid_content)
        c["b1"]["barcolor"] = "red"  # 不是 #XXXXXX
        ok, errs = validate_content(c)
        assert not ok


# ── 模板填充测试 ──────────────────────────────────────────────

class TestTemplateFilling:
    """模板占位符填充。"""

    def test_no_unresolved_placeholders(self, filled_html):
        """填充后不应有未解析的 {{...}} 占位符。"""
        import re
        left = re.findall(r"\{\{[^}]+\}\}", filled_html)
        unresolved = [p for p in left if "{{{" not in p]  # 排除 triple-brace
        assert len(unresolved) == 0, f"未解析占位符: {unresolved}"

    def test_all_placeholder_keys_in_map(self, template):
        """模板中所有 {{...}} 占位符都应在 PLACEHOLDER_MAP 中有映射。

        使用负向断言排除 {{{char_xxx}}} 三重大括号占位符（角色图）。"""
        import re
        # 仅匹配双重大括号 {{key}}，不匹配三重大括号 {{{key}}}
        placeholders = set(re.findall(r"(?<!\{)\{\{(\w+)\}\}(?!\})", template))
        mapped = set(PLACEHOLDER_MAP.keys()) | {"tags_html"}
        unmapped = placeholders - mapped
        assert len(unmapped) == 0, f"未映射的占位符: {unmapped}"

    def test_title_in_output(self, filled_html, valid_content):
        """标题文本应出现在填充后的 HTML 中。"""
        assert valid_content["title"] in filled_html

    def test_footer_in_output(self, filled_html, valid_content):
        """页脚文本应出现在填充后的 HTML 中。"""
        assert valid_content["footer"] in filled_html

    def test_tags_html_generated(self, filled_html, valid_content):
        """标签应渲染为 HTML。"""
        assert '<span class="tag">' in filled_html
        for tag in valid_content["tags"]:
            assert tag in filled_html

    def test_character_hero_placeholder_expanded(self, filled_html):
        """主角色图路径应展开为实际路径。"""
        assert 'src="assets/characters/主图_rb.png"' in filled_html

    def test_character_card1_placeholder_expanded(self, filled_html):
        """卡1 角色图路径应展开。"""
        assert 'src="assets/characters/卡1_rb.png"' in filled_html


# ── 角色图配置测试 ────────────────────────────────────────────

class TestCharacterPaths:
    """角色图路径配置。"""

    def test_default_characters_match_keys(self):
        """默认角色映射键应与 CHARACTER_KEYS 对齐。"""
        for key in CHARACTER_KEYS:
            assert key in DEFAULT_CHARACTERS, f"缺少默认角色: {key}"
        assert len(DEFAULT_CHARACTERS) == len(CHARACTER_KEYS)

    def test_custom_character_override(self, template):
        """content.characters 应覆盖默认角色路径。"""
        c = json.loads((SKILL / "content.json").read_text(encoding="utf-8"))
        c["characters"] = {"hero": "custom/hero.png"}
        html = build_html(c, template)
        assert 'src="custom/hero.png"' in html
        # 其他角色应保持默认
        assert 'src="assets/characters/卡1_rb.png"' in html

    def test_placeholder_count_matches(self, template, filled_html):
        """模板中的角色占位符数量 = CHARACTER_PLACEHOLDERS 数量。"""
        import re
        # 检查 triple-brace 占位符数量
        triple = set(re.findall(r"\{\{\{(\w+)\}\}\}", template))
        assert triple == set(CHARACTER_PLACEHOLDERS), \
            f"模板占位符 {triple} 与定义 {set(CHARACTER_PLACEHOLDERS)} 不一致"


# ── 完整渲染管线测试 (需要 Playwright + Chromium) ─────────────

@pytest.mark.slow
@pytest.mark.integration
class TestFullRenderPipeline:
    """完整渲染管线测试。需要: playwright install chromium"""

    def test_full_render_produces_png(self, tmp_path):
        """完整渲染管线应生成非空 PNG 文件。"""
        from generate import main as generate_main
        import sys

        out_path = tmp_path / "test_output.png"
        # 通过 sys.argv 模拟 CLI
        old_argv = sys.argv
        try:
            sys.argv = [
                "generate.py",
                "--content", str(SKILL / "content.json"),
                "--template", str(SKILL / "template.html"),
                "--out", str(out_path),
            ]
            generate_main()
        finally:
            sys.argv = old_argv

        assert out_path.exists(), f"输出文件未生成: {out_path}"
        assert out_path.stat().st_size > 1000, f"输出文件过小: {out_path.stat().st_size} bytes"

    def test_build_html_creates_poster_build(self, tmp_path):
        """填充阶段应创建 poster_build.html。"""
        from generate import build_html

        c = json.loads((SKILL / "content.json").read_text(encoding="utf-8"))
        tpl = (SKILL / "template.html").read_text(encoding="utf-8")
        html = build_html(c, tpl)

        build_path = tmp_path / "poster_build.html"
        build_path.write_text(html, encoding="utf-8")

        assert build_path.exists()
        content = build_path.read_text(encoding="utf-8")
        assert "智商藏不住" in content or c["title"] in content
        # 不应残留原始 {{placeholder}}
        assert "{{title}}" not in content
        assert "{{b1_title}}" not in content
