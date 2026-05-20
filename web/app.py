"""
English Agent — Streamlit Web UI
温暖学术风：奶油纸质感 + 琥珀色点缀，像私人英语学习日记
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from core.storage import StorageManager
from core.models import Script, MaterialCollection
from skills.script import ScriptSkill
from skills.material import MaterialSkill

# ─── 页面配置 ────────────────────────────────────────

st.set_page_config(
    page_title="Lulu's Daily Mic",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─── 自定义 CSS — 温暖学术风 ────────────────────────

st.markdown("""
<style>
/* ── Google Fonts ── */
@import url('https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,500;6..72,600&family=Inter:wght@400;500&display=swap');

/* ── CSS 变量 ── */
:root {
    --cream: #FAF8F5;
    --paper: #F5F1EB;
    --warm-white: #FFFCF8;
    --ink: #2C2416;
    --ink-light: #6B5E4F;
    --amber: #C8873A;
    --amber-light: #E8C98B;
    --sage: #7A9A7E;
    --sage-light: #E8F0E9;
    --card-shadow: 0 1px 3px rgba(44, 36, 22, 0.06), 0 1px 2px rgba(44, 36, 22, 0.04);
    --card-hover-shadow: 0 4px 12px rgba(44, 36, 22, 0.08);
    --radius: 12px;
    --radius-sm: 8px;
}

/* ── 全局覆盖 ── */
.stApp {
    background-color: var(--cream);
    color: var(--ink);
}

.main .block-container {
    padding-top: 2rem;
    max-width: 1024px;
}

/* ── 顶部导航条 ── */
.top-nav {
    display: flex;
    align-items: center;
    justify-content: flex-start;
    padding: 0 0 0.75rem;
    margin-bottom: 0.5rem;
    gap: 14px;
}
.nav-logo {
    flex-shrink: 0;
}
.nav-logo svg {
    display: block;
}
.nav-brand {
    display: flex;
    flex-direction: column;
    gap: 1px;
}
.nav-brand .logo {
    font-size: 1.35rem;
    font-family: 'Newsreader', serif;
    font-weight: 600;
    color: var(--ink);
    letter-spacing: -0.01em;
    line-height: 1.2;
}
.nav-brand .subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    color: var(--ink-light);
    font-weight: 400;
    line-height: 1.3;
}

/* ── 页面标题 ── */
.page-title {
    font-family: 'Newsreader', serif;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--ink);
    margin-bottom: 0.25rem;
    letter-spacing: -0.01em;
}
.page-desc {
    font-family: 'Inter', sans-serif;
    font-size: 0.88rem;
    color: var(--ink-light);
    margin-bottom: 1.5rem;
    line-height: 1.5;
}

/* ── 卡片 ── */
.card {
    background: var(--warm-white);
    border: 1px solid #E8DFD3;
    border-radius: var(--radius);
    padding: 1.5rem;
    margin-bottom: 1rem;
    box-shadow: var(--card-shadow);
    transition: box-shadow 0.2s;
}
.card:hover {
    box-shadow: var(--card-hover-shadow);
}

/* ── 脚本展示 ── */
.script-en {
    font-family: 'Newsreader', serif;
    font-size: 1.05rem;
    line-height: 1.8;
    color: var(--ink);
    padding: 1.25rem 1.5rem;
    background: var(--warm-white);
    border-left: 3px solid var(--amber);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    margin-bottom: 1rem;
}
.script-cn {
    font-family: 'Inter', sans-serif;
    font-size: 0.92rem;
    line-height: 1.8;
    color: var(--ink-light);
    padding: 1.25rem 1.5rem;
    background: var(--sage-light);
    border-left: 3px solid var(--sage);
    border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}
.script-meta {
    display: flex;
    gap: 1.5rem;
    font-family: 'Inter', sans-serif;
    font-size: 0.8rem;
    color: var(--ink-light);
    padding: 0.5rem 1.5rem;
}

/* ── 材料卡片 ── */
.material-item {
    padding: 1rem 1.25rem;
    margin-bottom: 0.75rem;
    background: var(--warm-white);
    border-radius: var(--radius-sm);
    box-shadow: var(--card-shadow);
    transition: box-shadow 0.15s;
}
.material-item:hover {
    box-shadow: var(--card-hover-shadow);
}
.material-title {
    font-family: 'Newsreader', serif;
    font-size: 1rem;
    font-weight: 500;
    color: var(--ink);
    margin-bottom: 0.35rem;
}
.material-desc {
    font-family: 'Inter', sans-serif;
    font-size: 0.84rem;
    color: var(--ink-light);
    line-height: 1.5;
    margin-bottom: 0.35rem;
}
.material-type {
    display: inline-block;
    font-family: 'Inter', sans-serif;
    font-size: 0.7rem;
    font-weight: 500;
    padding: 2px 10px;
    border-radius: 20px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-right: 0.5rem;
}
.type-article { background: #FDF2E3; color: #C8873A; }
.type-video { background: #FDE8E8; color: #C44D4D; }
.type-tool { background: #FFF5E0; color: #B8860B; }
.type-podcast { background: #F0E8F6; color: #7C5CBF; }
.type-book { background: #E3EEFA; color: #4A7DB5; }
.type-course { background: #E8F0E9; color: #5A8A5F; }
.type-framework { background: #F2EDE4; color: #6B5E4F; }

/* ── 推送横幅 ── */
.push-banner {
    background: linear-gradient(135deg, #FDF2E3 0%, #FAF8F5 50%, #E8F0E9 100%);
    border: 1px solid #E8DFD3;
    border-radius: var(--radius);
    padding: 1.5rem 1.75rem;
    margin-bottom: 1.5rem;
}
.push-banner .emoji {
    font-size: 1.8rem;
    margin-bottom: 0.5rem;
}
.push-banner .header {
    font-family: 'Newsreader', serif;
    font-size: 1.2rem;
    font-weight: 600;
    color: var(--ink);
    margin-bottom: 0.25rem;
}
.push-banner .theme {
    font-family: 'Inter', sans-serif;
    font-size: 0.88rem;
    color: var(--ink-light);
    font-style: italic;
}

/* ── 脚本列表项 ── */
.script-list-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.85rem 1.25rem;
    background: var(--warm-white);
    border-radius: var(--radius-sm);
    margin-bottom: 0.5rem;
    box-shadow: var(--card-shadow);
    cursor: pointer;
    transition: all 0.15s;
}
.script-list-item:hover {
    box-shadow: var(--card-hover-shadow);
    transform: translateX(2px);
}
.script-list-day {
    font-family: 'Newsreader', serif;
    font-size: 0.95rem;
    font-weight: 600;
    color: var(--amber);
    min-width: 50px;
}
.script-list-topic {
    font-family: 'Newsreader', serif;
    font-size: 0.95rem;
    color: var(--ink);
    flex: 1;
}
.script-list-meta {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    color: var(--ink-light);
}

/* ── 输入区域 ── */
.input-hint {
    font-family: 'Inter', sans-serif;
    font-size: 0.78rem;
    color: var(--ink-light);
    margin-top: 0.35rem;
}

/* ── Tab 导航：方块式 radio，选中态放大+变色 ── */
div[role="radiogroup"] {
    gap: 4px !important;
    padding: 0 !important;
    align-items: flex-end !important;
}
div[role="radiogroup"] label {
    font-family: 'Inter', sans-serif !important; font-size: 0.85rem !important;
    font-weight: 500 !important; color: #8B7E6F !important;
    padding: 10px 24px !important; border-radius: 12px 12px 0 0 !important;
    border: 2px solid #E8DFD3 !important; background: #F5F1EB !important;
    border-bottom-color: #E8DFD3 !important; margin-right: 0 !important;
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    white-space: nowrap !important; flex-shrink: 0 !important;
    line-height: 1.3 !important; margin-bottom: 0 !important;
    cursor: pointer !important;
}
div[role="radiogroup"] label:hover {
    border-color: #C8873A !important; color: #C8873A !important;
    background: #FFFCF8 !important;
}
div[role="radiogroup"] label[data-selected="true"] {
    font-size: 0.95rem !important; font-weight: 700 !important;
    padding: 13px 28px !important;
    color: #C8873A !important; border-color: #C8873A !important;
    background: #FFFCF8 !important; border-bottom-color: transparent !important;
    box-shadow: 0 -2px 8px rgba(200, 135, 58, 0.1) !important;
    z-index: 1 !important;
}
/* 隐藏 radio 圆点 */
div[role="radiogroup"] label > div:first-child {
    display: none !important;
}

/* ── Quick Topics pill 按钮 ── */
.qt-pills button {
    font-size: 0.76rem !important; font-weight: 400 !important;
    padding: 3px 12px !important; border-radius: 20px !important;
    border: 1px solid #E8DFD3 !important; background: #FFFCF8 !important;
    color: #6B5E4F !important; box-shadow: none !important;
    height: auto !important; min-height: unset !important; line-height: 1.3 !important;
}
.qt-pills button:hover {
    border-color: #C8873A !important; color: #C8873A !important; background: #FDF2E3 !important;
}
/* ── Generate 按钮 ── */
button[kind="primary"],
button[type="submit"],
.stFormSubmitButton button,
div[data-testid="stFormSubmitButton"] button {
    font-family: 'Inter', sans-serif !important; font-weight: 600 !important; font-size: 0.95rem !important;
    border-radius: 8px !important; border: none !important; background: #C8873A !important;
    color: white !important; padding: 0.55rem 1.8rem !important; box-shadow: 0 2px 8px rgba(200,135,58,0.3) !important;
    transition: all 0.15s !important;
}
button[kind="primary"]:hover,
button[type="submit"]:hover,
.stFormSubmitButton button:hover { background: #B0782E !important; box-shadow: 0 4px 14px rgba(200,135,58,0.4) !important; }
    color: white;
    padding: 0.5rem 1.5rem;
    font-size: 0.9rem !important;
}
button[kind="primary"]:hover {
    background: #B0782E;
    border-color: #B0782E;
}
.stTextInput > div > div > input {
    font-family: 'Inter', sans-serif;
    border-radius: var(--radius-sm);
    border: 1px solid #D4C8B8;
    background: var(--warm-white);
    color: var(--ink);
    padding: 0.6rem 1rem;
}
.stTextInput > div > div > input::placeholder {
    color: #B5A995;
    opacity: 1;
}
.stTextInput > div > div > input:focus {
    border-color: var(--amber);
    box-shadow: 0 0 0 2px rgba(200, 135, 58, 0.15);
}
.stSelectbox > div > div {
    border-radius: var(--radius-sm);
    color: var(--ink);
}
.stSelectbox [data-baseweb="select"] * {
    color: var(--ink);
}

/* ── 覆盖浏览器自动填充样式 ── */
input:-webkit-autofill,
input:-webkit-autofill:hover,
input:-webkit-autofill:focus {
    -webkit-text-fill-color: var(--ink);
    -webkit-box-shadow: 0 0 0px 1000px var(--warm-white) inset;
    transition: background-color 5000s ease-in-out 0s;
}

/* ── 分割线 ── */
.section-divider {
    border: none;
    border-top: 1px solid #E8DFD3;
    margin: 1.5rem 0;
}

/* ── 页脚 ── */
.footer {
    text-align: center;
    font-family: 'Inter', sans-serif;
    font-size: 0.75rem;
    color: var(--ink-light);
    padding: 2rem 0 1rem;
}

/* ── Toast/通知样式 ── */
.notification-toast {
    background: var(--warm-white);
    border: 1px solid var(--amber-light);
    border-radius: var(--radius);
    padding: 1rem 1.5rem;
    margin: 1rem 0;
    display: flex;
    align-items: center;
    gap: 12px;
}
.notification-toast .icon {
    font-size: 1.5rem;
}
.notification-toast .content {
    font-family: 'Inter', sans-serif;
    font-size: 0.88rem;
    color: var(--ink);
}

/* ── 空状态 ── */
.empty-state {
    text-align: center;
    padding: 3rem 1rem;
}
.empty-state .icon {
    font-size: 2.5rem;
    margin-bottom: 0.75rem;
}
.empty-state .text {
    font-family: 'Newsreader', serif;
    font-size: 1rem;
    color: var(--ink-light);
}

/* ── Streamlit 原生文本颜色强制覆盖 ── */
.stMarkdown, .stMarkdown p, .stCaption, .stText {
    color: var(--ink) !important;
}
.stExpander [data-testid="stExpander"] details summary {
    color: var(--ink);
}
.stExpander [data-testid="stExpander"] details > div {
    color: var(--ink);
}

/* ── 隐藏 Streamlit 默认元素 ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

</style>
""", unsafe_allow_html=True)

# ─── 初始化 Storage 和 Skills ────────────────────────


@st.cache_resource
def init_resources():
    storage = StorageManager(base_dir=str(Path(__file__).parent.parent / "data"))
    script_skill = ScriptSkill(storage)
    material_skill = MaterialSkill(storage)
    return storage, script_skill, material_skill


storage, script_skill, material_skill = init_resources()


# ─── 辅助函数 ────────────────────────────────────────

def render_top_nav():
    """渲染顶部导航"""
    st.markdown("""
    <div class="top-nav">
        <div class="nav-logo">
            <svg width="42" height="42" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <ellipse cx="50" cy="55" rx="42" ry="38" fill="#F5F1EB" stroke="#C8873A" stroke-width="3"/>
                <ellipse cx="50" cy="58" rx="30" ry="26" fill="#FFFCF8"/>
                <ellipse cx="40" cy="46" rx="7" ry="8" fill="#2C2416"/>
                <ellipse cx="60" cy="46" rx="7" ry="8" fill="#2C2416"/>
                <circle cx="37" cy="43" r="2.5" fill="white"/>
                <circle cx="57" cy="43" r="2.5" fill="white"/>
                <path d="M42 56 Q50 50 58 56" stroke="#2C2416" stroke-width="2.5" fill="none" stroke-linecap="round"/>
                <path d="M42 56 Q46 62 50 56" stroke="#C8873A" stroke-width="1.5" fill="none" stroke-linecap="round"/>
                <path d="M58 56 Q54 62 50 56" stroke="#C8873A" stroke-width="1.5" fill="none" stroke-linecap="round"/>
                <path d="M22 28 Q15 12 30 20" fill="#F5F1EB" stroke="#C8873A" stroke-width="2.5"/>
                <path d="M78 28 Q85 12 70 20" fill="#F5F1EB" stroke="#C8873A" stroke-width="2.5"/>
                <path d="M20 42 Q8 34 14 22" fill="#F5F1EB" stroke="#C8873A" stroke-width="2"/>
                <path d="M80 42 Q92 34 86 22" fill="#F5F1EB" stroke="#C8873A" stroke-width="2"/>
                <path d="M18 50 Q8 46 10 34" fill="none" stroke="#C8873A" stroke-width="1.5" stroke-linecap="round"/>
                <path d="M82 50 Q92 46 90 34" fill="none" stroke="#C8873A" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
        </div>
        <div class="nav-brand">
            <span class="logo">Lulu's Daily Mic</span>
            <span class="subtitle">Speak globally. Think deeply.</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    """渲染页脚"""
    st.markdown(f"""
    <div class="footer">
        Lulu's Daily Mic · v1.0 · Made for Lulu's learning journey<br>
        {datetime.now().strftime('%Y-%m-%d')}
    </div>
    """, unsafe_allow_html=True)


def render_script_card(script: Script):
    """渲染脚本卡片：兼容旧版（单版本）和双版本"""
    has_concise = bool(script.concise_english and script.concise_english.strip())

    # 详细版
    st.markdown('<p style="font-family:Inter,sans-serif;font-size:0.82rem;'
                f'color:#C8873A;font-weight:600;margin:0.5rem 0 0.25rem;">'
                f'{"📖 Detailed" if has_concise else "📖 Script"} ({script.word_count}w · ~{script.estimated_duration_seconds}s)</p>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="script-en">{script.english_script}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="script-cn">{script.chinese_translation}</div>',
                unsafe_allow_html=True)

    # 精简版（仅新版有）
    if has_concise:
        st.markdown('<p style="font-family:Inter,sans-serif;font-size:0.82rem;'
                    f'color:#C8873A;font-weight:600;margin:1rem 0 0.25rem;">'
                    f'⚡ Concise ({script.concise_word_count}w · ~{script.concise_duration_seconds}s)</p>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="script-en">{script.concise_english}</div>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="script-cn">{script.concise_chinese}</div>',
                    unsafe_allow_html=True)

    # 元数据
    wc = f"{script.word_count}w / {script.concise_word_count}w" if has_concise else f"{script.word_count}w"
    st.markdown(f"""
    <div class="script-meta">
        <span>📝 {wc}</span>
        <span>【{script.day_number}】</span>
        <span>🔗 {script.source_type}</span>
        <span style="font-size:0.7rem;opacity:0.6">{script.id}</span>
    </div>
    """, unsafe_allow_html=True)


def send_macos_notification(title: str, subtitle: str, message: str):
    """发送 macOS 原生通知"""
    script = f'''
    display notification "{message}" with title "{title}" subtitle "{subtitle}" sound name "Glass"
    '''
    os.system(f"osascript -e '{script}'")


# ─── Page 1: Script Generator ─────────────────────────

def page_script_generator():
    st.markdown('<div class="page-title">📝 Script Generator</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="page-desc">Paste a YouTube / Bilibili link or type a topic — '
        'generates English oral scripts.</div>',
        unsafe_allow_html=True
    )

    # ── 搜索框 + Generate（st.form 支持回车触发）──
    with st.form(key="script_form", clear_on_submit=False):
        col1, col2 = st.columns([5, 1])
        with col1:
            user_input = st.text_input(
                "URL or topic",
                placeholder="e.g. https://youtube.com/watch?v=xxx  or  a topic you like",
                label_visibility="collapsed",
                key="script_input"
            )
        with col2:
            generate_btn = st.form_submit_button("Generate ✨", use_container_width=True)

    # ── 推荐词条（搜索框下方的小标签）──
    st.markdown(
        '<p style="font-family:Inter,sans-serif;font-size:0.75rem;'
        'color:#6B5E4F;margin:0 0 4px 2px;">💡 Try these topics — click to fill</p>',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="qt-pills">', unsafe_allow_html=True)
    topics = [
        "Morning routine for a productive day",
        "How to stay focused working from home",
        "Small habits that improved my speaking",
        "Interesting facts I learned this week",
        "The health benefits of walking daily",
        "What makes a great conversation",
    ]

    def _set_topic(t: str):
        st.session_state.script_input = t

    cols = st.columns([1, 1, 1])
    for i, topic in enumerate(topics):
        with cols[i % 3]:
            st.button(
                topic, key=f"qt_{i}", use_container_width=True,
                on_click=_set_topic, args=(topic,),
            )

    st.markdown('</div>', unsafe_allow_html=True)

    if generate_btn and user_input.strip():
        with st.spinner("Fetching content..."):
            content = script_skill.connector.fetch(user_input.strip())

        # 检测是否为 fallback 结果（内容抓取失败）
        is_fallback = content.metadata.get("fallback_reason") if content.metadata else False
        if is_fallback:
            st.error(f"❌ 内容抓取失败：{content.metadata['fallback_reason']}")
            st.info(
                "YouTube 视频可能没有字幕，或该网页无法提取正文。"
                "请尝试直接输入主题关键词来生成脚本，或者换一个视频链接试试。"
            )
            render_footer()
            return

        with st.spinner(f"Generating script 【{script_skill.storage.get_next_day_number()}】..."):
            prompt = script_skill._load_prompt("script_generator.txt")
            day_number = script_skill.storage.get_next_day_number()
            prompt = prompt.replace("{day_number}", str(day_number))
            prompt = prompt.replace("{source_type}", content.source_type)
            prompt = prompt.replace("{source_url}", content.source_url or user_input.strip())
            prompt = prompt.replace("{source_title}", content.title or "Today's topic")
            prompt = prompt.replace("{content_text}", content.text or "No detailed content. Generate based on topic.")

            from core.llm import chat_json  # noqa: E402

            result = chat_json(
                system=prompt,
                messages=[{"role": "user",
                           "content": "Generate the English oral practice script."}],
            )

        # 解析双版本 JSON
        detailed = result.get("detailed", {})
        concise = result.get("concise", {})

        now = datetime.now()
        script = Script(
            id=f"script_{now.strftime('%Y%m%d_%H%M%S')}",
            day_number=day_number,
            created_at=now.isoformat(),
            topic=result.get("topic", "Daily Practice"),
            source_url=content.source_url or user_input.strip(),
            source_type=content.source_type,
            english_script=detailed.get("english_script", ""),
            chinese_translation=detailed.get("chinese_translation", ""),
            word_count=detailed.get("word_count", 0),
            estimated_duration_seconds=detailed.get("estimated_duration_seconds", 0),
            concise_english=concise.get("english_script", ""),
            concise_chinese=concise.get("chinese_translation", ""),
            concise_word_count=concise.get("word_count", 0),
            concise_duration_seconds=concise.get("estimated_duration_seconds", 0),
        )

        storage.save_script(script)

        # 检查固定开篇
        expected = (f"Hi guys, it's Lulu. Day {day_number} of my daily English "
                    f"practice. I keep talking to improve my oral English.")
        if not script.english_script.strip().startswith(expected):
            st.warning("⚠️ Fixed opening may have been modified — please double check")

        # 显示结果：详细版在上，精简版在下
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown(f'<div class="page-title" style="font-size:1.2rem;">'
                    f'【{script.day_number}】 {script.topic}</div>',
                    unsafe_allow_html=True)

        # 详细版
        st.markdown('<p style="font-family:Inter,sans-serif;font-size:0.85rem;'
                    f'color:#C8873A;font-weight:600;margin:1rem 0 0.25rem;">'
                    f'📖 Detailed ({script.word_count} words · ~{script.estimated_duration_seconds}s)</p>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="script-en">{script.english_script}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="script-cn">{script.chinese_translation}</div>', unsafe_allow_html=True)

        # 精简版
        st.markdown('<p style="font-family:Inter,sans-serif;font-size:0.85rem;'
                    f'color:#C8873A;font-weight:600;margin:1.5rem 0 0.25rem;">'
                    f'⚡ Concise ({script.concise_word_count} words · ~{script.concise_duration_seconds}s)</p>',
                    unsafe_allow_html=True)
        st.markdown(f'<div class="script-en">{script.concise_english}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="script-cn">{script.concise_chinese}</div>', unsafe_allow_html=True)

        # 下载按钮
        text_content = (
            f"{'=' * 50}\n"
            f"【{script.day_number}】 {script.topic}\n"
            f"{'=' * 50}\n\n"
            f"--- Detailed (English) ---\n\n{script.english_script}\n\n"
            f"--- Detailed (中文) ---\n\n{script.chinese_translation}\n\n"
            f"--- Concise (English) ---\n\n{script.concise_english}\n\n"
            f"--- Concise (中文) ---\n\n{script.concise_chinese}\n\n"
            f"Detailed: {script.word_count}w | Concise: {script.concise_word_count}w | "
            f"Duration: ~{script.estimated_duration_seconds}s | "
            f"Source: {script.source_url}\n"
        )
        st.download_button(
            label="📥 Download script",
            data=text_content,
            file_name=f"script{script.day_number}_{script.topic.replace(' ', '_')}.txt",
            mime="text/plain",
        )

    render_footer()


# ─── Page 2: My Scripts ───────────────────────────────

def page_my_scripts():
    st.markdown('<div class="page-title">📚 My Scripts</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="page-desc">Browse your practice history. '
        'Each script is a step toward fluent English.</div>',
        unsafe_allow_html=True
    )

    scripts = storage.list_scripts()

    if not scripts:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📖</div>
            <div class="text">No scripts yet — go to Script Generator to create your first one.</div>
        </div>
        """, unsafe_allow_html=True)
        render_footer()
        return

    # 搜索 + 日期筛选
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("🔍 Search", placeholder="Filter by topic...",
                               label_visibility="collapsed", key="script_search")
    with col2:
        sort_order = st.selectbox("Sort", ["Newest first", "Oldest first",
                                           "By day number"],
                                  label_visibility="collapsed", key="script_sort")

    # 过滤和排序
    filtered = scripts
    if search:
        filtered = [s for s in filtered
                    if search.lower() in s.get("topic", "").lower()]

    if sort_order == "Oldest first":
        filtered = list(reversed(filtered))
    elif sort_order == "By day number":
        filtered = sorted(filtered,
                          key=lambda s: s.get("day_number", 0), reverse=True)

    # 渲染脚本列表
    for s in filtered:
        # 简化显示：点击展开
        with st.expander(
            f"**【{s.get('day_number', '?')}】** {s.get('topic', 'Untitled')}  "
            f"({s.get('word_count', 0)} words · {s.get('created_at', '')[:10]})"
        ):
            script = storage.load_script(s["id"])
            if script:
                render_script_card(script)
                c1, c2 = st.columns([1, 1])
                with c1:
                    tc_parts = [
                        f"【{script.day_number}】 {script.topic}\n",
                        f"--- English ---\n{script.english_script}\n",
                        f"--- 中文 ---\n{script.chinese_translation}\n",
                    ]
                    if script.concise_english and script.concise_english.strip():
                        tc_parts += [
                            f"--- Concise English ---\n{script.concise_english}\n",
                            f"--- Concise 中文 ---\n{script.concise_chinese}\n",
                        ]
                    text_content = "\n".join(tc_parts)
                    st.download_button(
                        "📥 Download", data=text_content,
                        file_name=f"script{script.day_number}.txt",
                        mime="text/plain",
                        key=f"dl_{script.id}"
                    )
                with c2:
                    if st.button("🗑 Delete", key=f"del_{script.id}"):
                        storage.delete_script(script.id)
                        st.rerun()

    st.caption(f"Total: {len(scripts)} scripts")
    render_footer()


# ─── Page 3: AI Radar ────────────────────────────────

def page_materials():
    st.markdown('<div class="page-title">📡 AI Radar</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="page-desc">Curated twice daily at 10:00 AM and 10:00 PM. '
        'Scanning the AI landscape so you don\'t have to.</div>',
        unsafe_allow_html=True
    )

    # 最新推送横幅
    latest = storage.get_latest_materials()
    if latest:
        emoji = "☀️" if latest.session == "morning" else "🌙"
        session_label = "Morning" if latest.session == "morning" else "Evening"
        st.markdown(f"""
        <div class="push-banner">
            <div class="emoji">{emoji}</div>
            <div class="header">{session_label} Edition · {latest.pushed_at[:10]}</div>
            <div class="theme">{latest.session_description}</div>
        </div>
        """, unsafe_allow_html=True)

        # 渲染材料列表
        for i, m in enumerate(latest.materials, 1):
            m_dict = m.to_dict() if hasattr(m, 'to_dict') else m
            m_type = m_dict.get("type", "article")
            type_class = f"type-{m_type}" if m_type in [
                "article", "video", "tool", "podcast", "book", "course", "framework"
            ] else "type-article"

            st.markdown(f"""
            <div class="material-item">
                <div class="material-title">{i}. {m_dict.get("title", "")}</div>
                <div class="material-desc">{m_dict.get("description", "")}</div>
                <span class="material-type {type_class}">{m_type}</span>
                <span style="font-size:0.75rem;color:#6B5E4F;">
                    <a href="{m_dict.get('url', '#')}" target="_blank">
                        {m_dict.get('url', '')[:60]}{'...' if len(m_dict.get('url', '')) > 60 else ''}
                    </a>
                </span>
            </div>
            """, unsafe_allow_html=True)

        st.caption(f"📌 {len(latest.materials)} resources · ID: {latest.id}")
    else:
        st.markdown("""
        <div class="empty-state">
            <div class="icon">📬</div>
            <div class="text">No materials yet. The first push is coming soon!</div>
        </div>
        """, unsafe_allow_html=True)

    # 历史推送
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown('<div class="page-title" style="font-size:1.1rem;">📋 History</div>',
                unsafe_allow_html=True)

    records = storage.list_materials()
    if records:
        for r in records[:20]:
            session_label = "☀️ Morning" if r.get("session") == "morning" else "🌙 Evening"
            with st.expander(
                f"{session_label} · {r.get('pushed_at', '')[:10]} — "
                f"{(r.get('session_description') or '')[:50]}  "
                f"({r.get('material_count', 0)} resources)"
            ):
                collection = storage.load_materials(r["id"])
                if collection:
                    for i, m in enumerate(collection.materials, 1):
                        m_dict = m.to_dict() if hasattr(m, 'to_dict') else m
                        st.markdown(f"""
                        <div class="material-item">
                            <div class="material-title">{i}. {m_dict.get("title", "")}</div>
                            <div class="material-desc">{m_dict.get("description", "")}</div>
                            <span class="material-type type-{m_dict.get('type', 'article')}">
                                {m_dict.get("type", "article")}
                            </span>
                            <span style="font-size:0.75rem;">
                                <a href="{m_dict.get('url', '#')}" target="_blank">🔗 Link</a>
                            </span>
                        </div>
                        """, unsafe_allow_html=True)

    render_footer()


# ─── 主入口 ───────────────────────────────────────────

def main():
    render_top_nav()

    # Tab 导航 — 方块式 radio：图标在文字左侧，选中态放大+变色
    if "active_tab" not in st.session_state:
        st.session_state["active_tab"] = "speak"

    tab_labels = {
        "speak": "🦜 Script Generator",
        "library": "🦉 My Scripts",
        "radar": "🦊 AI Radar",
    }

    active_tab = st.radio(
        "Nav", options=["speak", "library", "radar"],
        format_func=lambda k: tab_labels[k],
        horizontal=True, label_visibility="collapsed",
        index=["speak", "library", "radar"].index(st.session_state["active_tab"]),
    )
    st.session_state["active_tab"] = active_tab

    st.markdown(
        '<hr class="section-divider" style="margin-top:0.25rem;border-color:#E8DFD3;">',
        unsafe_allow_html=True,
    )

    if active_tab == "speak":
        page_script_generator()
    elif active_tab == "library":
        page_my_scripts()
    else:
        page_materials()


if __name__ == "__main__":
    main()
