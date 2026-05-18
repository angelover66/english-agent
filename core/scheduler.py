"""Skill 注册 + 命令解析 + 意图分类"""
from __future__ import annotations
import re
from typing import Optional

# 全局 Skill 注册表
_skills: dict[str, object] = {}


def register(name: str, instance: object):
    """注册一个 Skill 实例"""
    _skills[name] = instance


def get_skill(name: str) -> Optional[object]:
    """按名称获取 Skill 实例"""
    return _skills.get(name)


def all_skills() -> dict:
    """返回全部已注册 Skill"""
    return dict(_skills)


# ─── 命令解析 ────────────────────────────────────────

def parse_command(text: str) -> Optional[tuple[str, str]]:
    """
    解析显式命令，格式：
    - script generate <url/topic>
    - script list / view / delete
    - material push morning/evening
    - material list / view
    """
    text = text.strip()
    # 支持 / 前缀
    if text.startswith("/"):
        text = text[1:]

    # 匹配已知 skill 名
    for skill_name in _skills:
        if text.startswith(skill_name):
            args = text[len(skill_name):].strip()
            return (skill_name, args)

    return None


# ─── 中文意图分类 ────────────────────────────────────

_INTENT_PATTERNS = [
    # script 相关
    (r"(生成|写|create|generate|做|制作).*(脚本|口语|英语|练习|口播|script)", "script", "generate"),
    (r"(查看|列出|list|ls|看看|浏览).*(脚本|练习|历史)", "script", "list"),
    (r"(删除|delete|remove).*(脚本|练习)", "script", "delete"),
    # material 相关
    (r"(推送|push|发送|发布).*(材料|资料|资源|素材)", "material", "push"),
    (r"(查看|列出|list|看看|浏览).*(材料|资料|资源|素材)", "material", "list"),
    # 快捷口语练习（无指定URL时，用主题生成）
    (r"(练习|说|讲|聊).*(英语|口语|英文)", "script", "generate"),
    (r"今天.*(学什么|聊什么|说什么)", "script", "generate"),
]


def classify_intent(text: str) -> Optional[tuple[str, str]]:
    """
    用正则匹配中文自然语言意图，返回 (skill_name, action)
    """
    text = text.strip()
    for pattern, skill_name, action in _INTENT_PATTERNS:
        if re.search(pattern, text):
            return (skill_name, action)
    return None


# ─── 帮助文本 ────────────────────────────────────────

def get_help_text() -> str:
    """返回帮助信息"""
    return """
[bold cyan]Lulu's Daily Mic[/] — 全球化沟通力养成

[bold]📝 脚本生成 (script)[/]
  script generate <URL/主题>   从视频/文章/主题生成口语脚本
  script list                  查看全部历史脚本
  script view <id>             查看指定脚本全文
  script delete <id>           删除指定脚本

[bold]📚 学习材料 (material)[/]
  material push morning        推送早间 AI PM 学习材料 (10:00)
  material push evening        推送晚间 AI PM 学习材料 (22:00)
  material list                查看历史推送
  material view <id>           查看指定推送详情

[bold]🖥 Web 界面[/]
  streamlit run web/app.py     启动网页端

[bold]💡 自然语言也 OK[/]
  比如直接说：「帮我生成一段口语练习，主题是产品经理面试技巧」
  或者：「今天聊什么？」「看看之前的脚本」
""".strip()
