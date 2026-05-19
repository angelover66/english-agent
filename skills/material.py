"""AI PM 学习材料策展 Skill — 早晚推送，含 URL 可访问性验证"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path

import requests
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

    def _check_url(self, url: str, timeout: int = 5) -> bool:
        """HEAD 请求验证 URL 可访问，返回 True/False"""
        try:
            r = requests.head(url, timeout=timeout, allow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0"})
            return r.status_code < 400
        except Exception:
            # HEAD 失败时尝试 GET（有些服务器不支持 HEAD）
            try:
                r = requests.get(url, timeout=timeout, stream=True,
                                 headers={"User-Agent": "Mozilla/5.0"})
                r.close()
                return r.status_code < 400
            except Exception:
                return False

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

    # ─── push: 策展并推送（确保精准 5 篇有效文章）────

    def _cmd_push(self, args: str) -> str:
        """生成学习材料推送，验证 URL，确保恰好 5 篇"""
        args_lower = args.strip().lower()
        if "morning" in args_lower or "上午" in args_lower or "早" in args_lower:
            session = "morning"
        elif "evening" in args_lower or "晚上" in args_lower or "晚" in args_lower:
            session = "evening"
        else:
            hour = datetime.now().hour
            session = "morning" if hour < 14 else "evening"

        session_label = "早间" if session == "morning" else "晚间"
        emoji = "☀️" if session == "morning" else "🌙"
        target_count = 5
        max_retries = 3

        prompt_template = self._load_prompt("material_curator.txt")
        prompt_template = prompt_template.replace("{session}", session)
        prompt_template = prompt_template.replace("{date}", datetime.now().strftime("%Y-%m-%d"))

        all_valid = []
        session_desc = f"{session_label}学习材料"
        retry = 0

        # 生成 + 验证循环：直到凑满 5 篇或重试耗尽
        while len(all_valid) < target_count and retry <= max_retries:
            if retry == 0:
                status = f"[cyan]正在策展{session_label}学习材料...[/]"
            else:
                status = f"[cyan]补充策展中（已有 {len(all_valid)}/{target_count} 篇）...[/]"

            with self.console.status(status):
                try:
                    result = chat_json(
                        system=prompt_template,
                        messages=[{"role": "user",
                                   "content": f"Curate {session} learning materials. "
                                   f"Generate exactly 8 candidates."}],
                    )
                except Exception as e:
                    return f"[red]LLM 调用失败: {e}[/]"

            if retry == 0:
                session_desc = result.get("session_description", session_desc)

            # 验证所有候选 URL
            candidates = [MaterialItem.from_dict(m) for m in result.get("materials", [])]
            with self.console.status(f"[dim]验证链接 ({len(candidates)} 个)...[/]"):
                for m in candidates:
                    url = m.url
                    if url and self._check_url(url):
                        if m not in all_valid:
                            all_valid.append(m)
                            if len(all_valid) >= target_count:
                                break
                    elif url:
                        self.console.print(f"[yellow]⚠ 不可访问: {url[:70]}[/]")

            retry += 1

        # 取恰好 5 篇
        final_materials = all_valid[:target_count]

        if len(final_materials) < target_count:
            self.console.print(
                f"[yellow]⚠ 仅验证通过 {len(final_materials)}/{target_count} 篇"
                f"（已重试 {max_retries} 次）[/]"
            )

        # 构建并保存
        now = datetime.now()
        date_str = now.strftime("%Y%m%d")
        collection = MaterialCollection(
            id=f"materials_{date_str}_{session}",
            pushed_at=now.isoformat(),
            session=session,
            session_description=session_desc,
            materials=final_materials,
        )

        self.storage.save_materials(collection)
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
