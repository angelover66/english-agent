"""English Agent — CLI 入口 (Rich 交互界面)"""
from __future__ import annotations
import sys
import os
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).parent))

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt

from core.storage import StorageManager
from core.scheduler import register, parse_command, classify_intent, get_help_text, get_skill
from skills.script import ScriptSkill
from skills.material import MaterialSkill

BANNER = """
[bold cyan]Lulu's Daily Mic[/] — 全球化沟通力养成
  🎙️ 每日口播 · 📚 AI PM 材料 · 🕐 定时推送
  Web: [dim]streamlit run web/app.py[/]
"""


class AgentApp:
    """CLI Agent 主应用"""

    def __init__(self):
        self.console = Console()
        self.storage = StorageManager()
        self.script_skill = ScriptSkill(self.storage)
        self.material_skill = MaterialSkill(self.storage)
        # 注册 Skill
        register("script", self.script_skill)
        register("material", self.material_skill)

    def route(self, user_input: str) -> str:
        """优先级路由：命令 > 意图分类 > 默认"""
        text = user_input.strip()
        if not text:
            return ""

        # 退出命令
        if text.lower() in ("exit", "quit", "q", "退出"):
            return "__EXIT__"

        # 帮助命令
        if text.lower() in ("help", "h", "?"):
            return get_help_text()

        # 显式命令解析
        parsed = parse_command(text)
        if parsed:
            skill_name, args = parsed
            skill = get_skill(skill_name)
            if skill:
                result = skill.run(
                    action=args.split()[0] if args else "",
                    args=" ".join(args.split()[1:]) if len(args.split()) > 1 else "",
                )
                return result
            else:
                return f"[red]未知 Skill: {skill_name}[/]"

        # NLU 意图分类
        intent = classify_intent(text)
        if intent:
            skill_name, action = intent
            skill = get_skill(skill_name)
            if skill:
                # 从原文提取参数（去掉意图关键词后的部分）
                args = text
                if action == "generate" and skill_name == "script":
                    # 尝试提取 URL 或主题
                    import re
                    url_match = re.search(r"https?://\S+", text)
                    if url_match:
                        args = url_match.group(0)
                    else:
                        # 去掉意图关键词
                        for pattern in [
                            r"(生成|写|create|generate|做|制作).*(脚本|口语|英语|练习|口播|script)",
                            r"(练习|说|讲|聊).*(英语|口语|英文)",
                            r"今天.*(学什么|聊什么|说什么)",
                        ]:
                            args = re.sub(pattern, "", text).strip()
                        if not args:
                            args = text  # fallback
                return skill.run(action=action, args=args)

        # 默认：如果看起来像 URL 或主题，尝试生成脚本
        if any(kw in text.lower() for kw in ["script", "英语", "口语", "英文"]):
            return self.script_skill.run(action="generate", args=text)
        elif any(kw in text.lower() for kw in ["material", "材料", "推送", "资源"]):
            return self.material_skill.run(action="push", args=text)

        return "[dim]不太确定你想做什么。试试说「生成口语脚本」或输入 URL～ (输入 help 查看全部命令)[/]"

    def run_interactive(self):
        """交互式 REPL 循环"""
        self.console.print(BANNER)
        self.console.print("[dim]输入命令或自然语言，输入 help 查看帮助，exit 退出[/]\n")

        while True:
            try:
                user_input = Prompt.ask("[bold cyan]>[/]")
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[dim]See you tomorrow! 👋[/]")
                break

            result = self.route(user_input)
            if result == "__EXIT__":
                self.console.print("[dim]See you tomorrow! 👋[/]")
                break
            elif result:
                self.console.print(result)
            self.console.print()

    def run_once(self, args: list[str]):
        """单次命令模式（用于 CronCreate 触发）"""
        if not args:
            self.console.print(get_help_text())
            return

        user_input = " ".join(args)
        result = self.route(user_input)
        if result and result != "__EXIT__":
            self.console.print(result)


def main():
    app = AgentApp()

    if len(sys.argv) > 1:
        # 单次命令模式
        app.run_once(sys.argv[1:])
    else:
        # 交互模式
        app.run_interactive()


if __name__ == "__main__":
    main()
