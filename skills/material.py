"""AI PM 学习材料策展 Skill — 早晚推送"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from core.llm import chat_json
from core.models import MaterialItem, MaterialCollection
from core.storage import StorageManager


class MaterialSkill:
    """AI PM 学习材料策展与推送 Skill"""

    def __init__(self, storage: StorageManager):
        self.storage = storage
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
        if action == "push":
            return self._cmd_push(args)
        elif action in ("list", "ls"):
            return self._cmd_list()
        elif action in ("view", "show"):
            return self._cmd_view(args)
        else:
            return self._cmd_help()

    # ─── push: 策展并推送 ──────────────────────────────

    def _cmd_push(self, args: str) -> str:
        """生成学习材料推送"""
        args_lower = args.strip().lower()
        if "morning" in args_lower or "上午" in args_lower or "早" in args_lower:
            session = "morning"
        elif "evening" in args_lower or "晚上" in args_lower or "晚" in args_lower:
            session = "evening"
        else:
            # 默认按当前时间判断
            hour = datetime.now().hour
            session = "morning" if hour < 14 else "evening"

        session_label = "早间" if session == "morning" else "晚间"
        emoji = "☀️" if session == "morning" else "🌙"

        with self.console.status(f"[cyan]正在策展{session_label}学习材料...[/]"):
            prompt = self._load_prompt("material_curator.txt")
            prompt = prompt.replace("{session}", session)
            prompt = prompt.replace("{date}", datetime.now().strftime("%Y-%m-%d"))

            try:
                result = chat_json(
                    system=prompt,
                    messages=[{"role": "user",
                               "content": f"Curate {session} learning materials for today."}],
                )
            except Exception as e:
                return f"[red]LLM 调用失败: {e}[/]"

        # 构建 MaterialCollection
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        collection = MaterialCollection(
            id=f"materials_{date_str}_{session}",
            pushed_at=now.isoformat(),
            session=session,
            session_description=result.get("session_description", f"{session_label}学习材料"),
        )

        for m in result.get("materials", []):
            collection.materials.append(MaterialItem.from_dict(m))

        self.storage.save_materials(collection)

        # 显示结果
        return self._render_collection(collection, emoji, session_label)

    def _render_collection(self, collection: MaterialCollection, emoji: str,
                           label: str) -> str:
        """用 Rich 渲染材料推送"""
        self.console.print()
        self.console.print(
            f"[bold]{emoji} {label} AI PM 学习材料[/] — "
            f"{collection.pushed_at[:10]}"
        )
        self.console.print(f"[dim italic]{collection.session_description}[/]\n")

        for i, m in enumerate(collection.materials, 1):
            type_colors = {
                "article": "cyan", "video": "red", "tool": "yellow",
                "podcast": "magenta", "book": "blue", "course": "green",
                "framework": "white",
            }
            color = type_colors.get(m.type, "white")
            self.console.print(f"[bold white]{i}.[/] [bold]{m.title}[/]")
            self.console.print(f"   [{color}]{m.type}[/] {m.description}")
            if m.url:
                self.console.print(f"   [dim link={m.url}]{m.url}[/]")
            self.console.print()

        self.console.print(f"[dim]共 {len(collection.materials)} 条 | ID: {collection.id}[/]")
        return ""

    # ─── list: 历史推送 ────────────────────────────────

    def _cmd_list(self) -> str:
        records = self.storage.list_materials()
        if not records:
            return "[dim]还没有任何推送，用 material push morning/evening 来策展第一份材料吧～[/]"

        table = Table(title="📚 历史推送", border_style="magenta")
        table.add_column("日期", style="white", width=12)
        table.add_column("时段", width=6)
        table.add_column("主题", style="white")
        table.add_column("条数", width=5, justify="right")
        table.add_column("ID", style="dim", width=28)

        for r in records[:30]:
            session_label = "☀️ 早" if r.get("session") == "morning" else "🌙 晚"
            table.add_row(
                r.get("pushed_at", "")[:10],
                session_label,
                (r.get("session_description", "") or "")[:40],
                str(r.get("material_count", "")),
                r.get("id", ""),
            )

        self.console.print(table)
        return ""

    # ─── view: 查看单次推送 ────────────────────────────

    def _cmd_view(self, args: str) -> str:
        mid = args.strip()
        if not mid:
            return "[red]请提供推送 ID[/]"

        collection = self.storage.load_materials(mid)
        if not collection:
            return f"[red]未找到推送: {mid}[/]"

        emoji = "☀️" if collection.session == "morning" else "🌙"
        label = "早间" if collection.session == "morning" else "晚间"
        return self._render_collection(collection, emoji, label)

    # ─── help ──────────────────────────────────────────

    def _cmd_help(self) -> str:
        return """
[bold magenta]📚 Material Skill — 学习材料推送[/]

  [white]material push morning[/]   推送早间 AI PM 学习材料 (10:00)
  [white]material push evening[/]   推送晚间 AI PM 学习材料 (22:00)
  [white]material list[/]          查看历史推送
  [white]material view <id>[/]     查看推送详情
""".strip()
