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
    page_title="English Practice · Ivy",
    page_icon="📖",
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
}

.main .block-container {
    padding-top: 2rem;
    max-width: 1024px;
}

/* ── 顶部导航条 ── */
.top-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1rem 0 1.5rem;
    border-bottom: 1px solid #E8DFD3;
    margin-bottom: 2rem;
}
.nav-brand {
    display: flex;
    align-items: center;
    gap: 10px;
}
.nav-brand .logo {
    font-size: 1.6rem;
    font-family: 'Newsreader', serif;
    font-weight: 600;
    color: var(--ink);
    letter-spacing: -0.01em;
}
.nav-brand .subtitle {
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    color: var(--ink-light);
    font-weight: 400;
    margin-left: 4px;
    padding-top: 4px;
}
.nav-actions {
    display: flex;
    gap: 4px;
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

/* ── Streamlit 原生组件覆盖 ── */
.stButton > button {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    border-radius: var(--radius-sm);
    border: 1px solid var(--amber);
    background: var(--amber);
    color: white;
    padding: 0.5rem 1.5rem;
    transition: all 0.15s;
}
.stButton > button:hover {
    background: #B0782E;
    border-color: #B0782E;
}
.stTextInput > div > div > input {
    font-family: 'Inter', sans-serif;
    border-radius: var(--radius-sm);
    border: 1px solid #D4C8B8;
    background: var(--warm-white);
    padding: 0.6rem 1rem;
}
.stTextInput > div > div > input:focus {
    border-color: var(--amber);
    box-shadow: 0 0 0 2px rgba(200, 135, 58, 0.15);
}
.stSelectbox > div > div {
    border-radius: var(--radius-sm);
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

/* ── 隐藏 Streamlit 默认元素 ── */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* ── 标签页样式 ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    border-bottom: 1px solid #E8DFD3;
}
.stTabs [data-baseweb="tab"] {
    font-family: 'Inter', sans-serif;
    font-size: 0.88rem;
    font-weight: 500;
    color: var(--ink-light);
    padding: 0.6rem 1.2rem;
    border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    border: none;
    background: transparent;
}
.stTabs [aria-selected="true"] {
    color: var(--amber) !important;
    border-bottom: 2px solid var(--amber) !important;
}
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
        <div class="nav-brand">
            <span class="logo">English Practice</span>
            <span class="subtitle">Ivy's daily speaking journal</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_footer():
    """渲染页脚"""
    st.markdown(f"""
    <div class="footer">
        English Practice Agent · v1.0 · Made for Ivy's learning journey<br>
        {datetime.now().strftime('%Y-%m-%d')}
    </div>
    """, unsafe_allow_html=True)


def render_script_card(script: Script):
    """渲染脚本展示卡片"""
    st.markdown(f'<div class="script-en">{script.english_script}</div>',
                unsafe_allow_html=True)
    st.markdown(f'<div class="script-cn">{script.chinese_translation}</div>',
                unsafe_allow_html=True)

    duration_min = script.estimated_duration_seconds // 60
    duration_sec = script.estimated_duration_seconds % 60
    st.markdown(f"""
    <div class="script-meta">
        <span>📝 {script.word_count} words</span>
        <span>⏱ {duration_min}m {duration_sec}s</span>
        <span>📌 Day {script.day_number}</span>
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
    render_top_nav()

    st.markdown('<div class="page-title">📝 Script Generator</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="page-desc">Paste a video/article URL or type a topic — '
        'get a 2-minute English oral practice script with Chinese translation.</div>',
        unsafe_allow_html=True
    )

    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            "URL or topic",
            placeholder="e.g. https://youtube.com/watch?v=xxx  or  AI product manager skills",
            label_visibility="collapsed",
            key="script_input"
        )
    with col2:
        generate_btn = st.button("Generate ✨", use_container_width=True,
                                 key="generate_btn")

    st.markdown(
        '<div class="input-hint">💡 Supports YouTube, Bilibili, articles, '
        'or just a topic you want to talk about</div>',
        unsafe_allow_html=True
    )

    if generate_btn and user_input.strip():
        with st.spinner("Fetching content..."):
            content = script_skill.connector.fetch(user_input.strip())

        with st.spinner(f"Generating Day {script_skill.storage.get_next_day_number()} script..."):
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

        now = datetime.now()
        script = Script(
            id=f"script_{now.strftime('%Y%m%d_%H%M%S')}",
            day_number=day_number,
            created_at=now.isoformat(),
            topic=result.get("topic", "Daily Practice"),
            source_url=content.source_url or user_input.strip(),
            source_type=content.source_type,
            english_script=result.get("english_script", ""),
            chinese_translation=result.get("chinese_translation", ""),
            word_count=result.get("word_count", 0),
            estimated_duration_seconds=result.get("estimated_duration_seconds", 0),
        )

        storage.save_script(script)

        # 检查固定开篇
        expected = (f"Hi guys, it's Ivy. Day {day_number} of my daily English "
                    f"practice. I keep talking to improve my oral English.")
        if not script.english_script.strip().startswith(expected):
            st.warning("⚠️ Fixed opening may have been modified — please double check")

        # 显示结果
        st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
        st.markdown(f'<div class="page-title" style="font-size:1.2rem;">'
                    f'Day {script.day_number} — {script.topic}</div>',
                    unsafe_allow_html=True)
        render_script_card(script)

        # 下载按钮
        text_content = (
            f"{'=' * 50}\n"
            f"Day {script.day_number}: {script.topic}\n"
            f"{'=' * 50}\n\n"
            f"--- English Script ---\n\n{script.english_script}\n\n"
            f"--- 中文翻译 ---\n\n{script.chinese_translation}\n\n"
            f"Words: {script.word_count} | "
            f"Duration: ~{script.estimated_duration_seconds}s | "
            f"Source: {script.source_url}\n"
        )
        st.download_button(
            label="📥 Download script",
            data=text_content,
            file_name=f"day{script.day_number}_{script.topic.replace(' ', '_')}.txt",
            mime="text/plain",
        )

    # 快捷主题按钮
    st.markdown('<hr class="section-divider">', unsafe_allow_html=True)
    st.markdown(
        '<div style="font-family:Inter,sans-serif;font-size:0.82rem;'
        'color:#6B5E4F;margin-bottom:0.5rem;">🎯 Quick topics</div>',
        unsafe_allow_html=True
    )
    topics = [
        "AI product manager daily work routine",
        "How to write a good PRD",
        "Agile vs waterfall for AI teams",
        "What I learned from a tech podcast today",
        "Tips for communicating with engineers",
        "The future of AI agents",
    ]
    cols = st.columns(3)
    for i, topic in enumerate(topics):
        with cols[i % 3]:
            if st.button(topic, key=f"qt_{i}", use_container_width=True):
                st.session_state["script_input"] = topic

    render_footer()


# ─── Page 2: My Scripts ───────────────────────────────

def page_my_scripts():
    render_top_nav()

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
            f"**Day {s.get('day_number', '?')}** — {s.get('topic', 'Untitled')}  "
            f"({s.get('word_count', 0)} words · {s.get('created_at', '')[:10]})"
        ):
            script = storage.load_script(s["id"])
            if script:
                render_script_card(script)
                c1, c2 = st.columns([1, 1])
                with c1:
                    text_content = (
                        f"Day {script.day_number}: {script.topic}\n\n"
                        f"--- English ---\n\n{script.english_script}\n\n"
                        f"--- 中文 ---\n\n{script.chinese_translation}\n"
                    )
                    st.download_button(
                        "📥 Download", data=text_content,
                        file_name=f"day{script.day_number}.txt",
                        mime="text/plain",
                        key=f"dl_{script.id}"
                    )
                with c2:
                    if st.button("🗑 Delete", key=f"del_{script.id}"):
                        storage.delete_script(script.id)
                        st.rerun()

    st.caption(f"Total: {len(scripts)} scripts")
    render_footer()


# ─── Page 3: AI PM Materials ──────────────────────────

def page_materials():
    render_top_nav()

    st.markdown('<div class="page-title">📬 AI PM Learning Materials</div>',
                unsafe_allow_html=True)
    st.markdown(
        '<div class="page-desc">Curated twice daily at 10:00 AM and 10:00 PM. '
        'Practical resources for an AI product manager.</div>',
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
    # 简单的自定义导航标签
    tab1, tab2, tab3 = st.tabs([
        "📝 Script Generator",
        "📚 My Scripts",
        "📬 AI PM Materials"
    ])

    with tab1:
        page_script_generator()

    with tab2:
        page_my_scripts()

    with tab3:
        page_materials()


if __name__ == "__main__":
    main()
