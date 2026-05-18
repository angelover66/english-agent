"""口语脚本生成 Skill — 从视频/文章/主题生成英文口播脚本"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from core.llm import chat_json
from core.models import Script
from core.storage import StorageManager
from connectors.web import WebConnector


class ScriptSkill:
    """英语口语脚本生成 Skill"""

    def __init__(self, storage: StorageManager):
        self.storage = storage
        self.connector = WebConnector()
        self.console = Console()
        self._prompt_cache: dict[str, str] = {}

    def _load_prompt(self, name: str) -> str:
        """从 prompts/ 目录加载模板，缓存到内存"""
        if name not in self._prompt_cache:
            prompt_path = Path(__file__).parent.parent / "prompts" / name
            if prompt_path.exists():
                self._prompt_cache[name] = prompt_path.read_text(encoding="utf-8")
            else:
                raise FileNotFoundError(f"Prompt 文件未找到: {prompt_path}")
        return self._prompt_cache[name]

    def run(self, action: str = "", args: str = "") -> str:
        """统一入口，路由到具体命令"""
        action = action.strip().lower()
        if action == "generate":
            return self._cmd_generate(args)
        elif action in ("list", "ls"):
            return self._cmd_list()
        elif action in ("view", "show"):
            return self._cmd_view(args)
        elif action in ("delete", "rm", "del"):
            return self._cmd_delete(args)
        else:
            return self._cmd_help()

    # ─── generate: 核心流程 ────────────────────────────

    def _cmd_generate(self, args: str) -> str:
        """
        从 URL 或主题生成口语脚本。
        流程：抓取内容 → 确定 Day 编号 → 调用 LLM → 保存脚本
        """
        if not args.strip():
            return "[red]请提供 URL 或主题，例如: script generate https://youtube.com/watch?v=xxx[/]"

        with self.console.status("[cyan]正在抓取内容...[/]"):
            content = self.connector.fetch(args.strip())

        day_number = self.storage.get_next_day_number()

        with self.console.status(f"[cyan]正在生成 Day {day_number} 脚本...[/]"):
            prompt = self._load_prompt("script_generator.txt")
            prompt = prompt.replace("{day_number}", str(day_number))
            prompt = prompt.replace("{source_type}", content.source_type)
            prompt = prompt.replace("{source_url}", content.source_url or args.strip())
            prompt = prompt.replace("{source_title}", content.title or "Today's topic")
            prompt = prompt.replace("{content_text}", content.text or "No detailed content available. Please generate based on the topic.")

            try:
                result = chat_json(
                    system=prompt,
                    messages=[{"role": "user",
                               "content": "Generate the English oral practice script based on the content above."}],
                )
            except Exception as e:
                return f"[red]LLM 调用失败: {e}[/]"

        # 构建 Script
        now = datetime.now()
        script = Script(
            id=f"script_{now.strftime('%Y%m%d_%H%M%S')}",
            day_number=day_number,
            created_at=now.isoformat(),
            topic=result.get("topic", "Daily Practice"),
            source_url=content.source_url or args.strip(),
            source_type=content.source_type,
            english_script=result.get("english_script", ""),
            chinese_translation=result.get("chinese_translation", ""),
            word_count=result.get("word_count", 0),
            estimated_duration_seconds=result.get("estimated_duration_seconds", 0),
        )

        self.storage.save_script(script)

        # 验证固定开篇
        expected_opening = f"Hi guys, it's Lulu. Day {day_number} of my daily English practice. I keep talking to improve my oral English."
        if not script.english_script.strip().startswith(expected_opening):
            self.console.print("[yellow]⚠ 固定开篇可能被修改，请手动检查[/]\n")

        # 显示结果
        return self._render_script(script)

    def _render_script(self, script: Script) -> str:
        """用 Rich Panel 渲染脚本"""
        self.console.print()
        self.console.print(Panel(
            Text(script.english_script, style="white"),
            title=f"[bold cyan]📝 Day {script.day_number} — {script.topic}[/]",
            title_align="left",
            border_style="cyan",
            padding=(1, 2),
        ))

        self.console.print(Panel(
            Text(script.chinese_translation, style="green"),
            title="[bold green]🇨🇳 中文对照翻译[/]",
            title_align="left",
            border_style="green",
            padding=(1, 2),
        ))

        # 元数据
        table = Table(show_header=False, box=None)
        table.add_row("[dim]词数[/]", str(script.word_count),
                      "[dim]预计时长[/]", f"{script.estimated_duration_seconds}s")
        table.add_row("[dim]来源[/]",
                      f"[link={script.source_url}]{script.source_type}[/]",
                      "[dim]ID[/]", script.id)
        self.console.print(table)
        return ""  # 返回空字符串，因为已直接打印到 console

    # ─── list: 列出历史脚本 ────────────────────────────

    def _cmd_list(self) -> str:
        scripts = self.storage.list_scripts()
        if not scripts:
            return "[dim]还没有任何脚本，用 script generate <URL/主题> 来生成第一个吧～[/]"

        table = Table(title="📝 历史脚本", border_style="cyan")
        table.add_column("Day", style="cyan", width=5)
        table.add_column("主题", style="white")
        table.add_column("来源", style="dim", width=12)
        table.add_column("词数", width=6, justify="right")
        table.add_column("日期", style="dim", width=10)
        table.add_column("ID", style="dim", width=22)

        for s in scripts[:30]:  # 最多显示30条
            table.add_row(
                f"#{s.get('day_number', '?')}",
                s.get("topic", "")[:30],
                s.get("source_type", ""),
                str(s.get("word_count", "")),
                s.get("created_at", "")[:10],
                s.get("id", ""),
            )

        self.console.print(table)
        return ""

    # ─── view: 查看单个脚本 ────────────────────────────

    def _cmd_view(self, args: str) -> str:
        sid = args.strip()
        if not sid:
            return "[red]请提供脚本 ID 或 Day 编号[/]"

        # 支持按 Day 编号查找
        if sid.startswith("#"):
            day_num = int(sid[1:])
            all_scripts = self.storage.list_scripts()
            match = next((s for s in all_scripts if s.get("day_number") == day_num), None)
            if match:
                sid = match["id"]
            else:
                return f"[red]未找到 Day {day_num} 的脚本[/]"

        script = self.storage.load_script(sid)
        if not script:
            return f"[red]未找到脚本: {sid}[/]"

        return self._render_script(script)

    # ─── delete ────────────────────────────────────────

    def _cmd_delete(self, args: str) -> str:
        sid = args.strip()
        if not sid:
            return "[red]请提供要删除的脚本 ID[/]"
        self.storage.delete_script(sid)
        return f"[green]已删除脚本: {sid}[/]"

    # ─── help ──────────────────────────────────────────

    def _cmd_help(self) -> str:
        return """
[bold cyan]📝 Script Skill — 口语脚本生成[/]

  [white]script generate <URL/主题>[/]  从视频/文章/主题生成脚本
  [white]script list[/]                  查看历史脚本
  [white]script view <id 或 #Day号>[/]   查看脚本全文
  [white]script delete <id>[/]           删除脚本
""".strip()
