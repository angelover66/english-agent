"""JSON 文件存储管理 — 脚本、材料、索引"""
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional

from .models import Script, MaterialCollection


class StorageManager:
    """本地 JSON 文件存储管理器"""

    def __init__(self, base_dir: str = "./data"):
        self.base_dir = Path(base_dir)
        self.scripts_dir = self.base_dir / "scripts"
        self.materials_dir = self.base_dir / "materials"
        self.scripts_index = self.scripts_dir / "index.json"
        self.materials_index = self.materials_dir / "index.json"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """确保存储目录存在"""
        self.scripts_dir.mkdir(parents=True, exist_ok=True)
        self.materials_dir.mkdir(parents=True, exist_ok=True)
        # 初始化索引文件
        for idx in [self.scripts_index, self.materials_index]:
            if not idx.exists():
                self._save_json(idx, [])

    # ─── 通用 JSON 读写 ────────────────────────────────

    def _save_json(self, path: Path, data):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2))

    def _load_json(self, path: Path):
        if not path.exists():
            return None
        return json.loads(path.read_text())

    # ─── 脚本管理 ──────────────────────────────────────

    def save_script(self, script: Script):
        """保存脚本到 data/scripts/{id}.json，更新索引"""
        # 保存脚本文件
        file_path = self.scripts_dir / f"{script.id}.json"
        self._save_json(file_path, script.to_dict())
        # 更新索引
        index = self._load_json(self.scripts_index) or []
        # 避免重复：先删除同 ID 的旧条目
        index = [e for e in index if e.get("id") != script.id]
        index.insert(0, {
            "id": script.id,
            "day_number": script.day_number,
            "created_at": script.created_at,
            "topic": script.topic,
            "source_type": script.source_type,
            "word_count": script.word_count,
        })
        self._save_json(self.scripts_index, index)

    def load_script(self, script_id: str) -> Optional[Script]:
        """加载单个脚本"""
        file_path = self.scripts_dir / f"{script_id}.json"
        data = self._load_json(file_path)
        if data:
            return Script.from_dict(data)
        return None

    def list_scripts(self) -> list[dict]:
        """列出所有脚本摘要，最新在前"""
        return self._load_json(self.scripts_index) or []

    def delete_script(self, script_id: str):
        """删除脚本及其索引条目"""
        file_path = self.scripts_dir / f"{script_id}.json"
        if file_path.exists():
            os.remove(file_path)
        index = self._load_json(self.scripts_index) or []
        index = [e for e in index if e.get("id") != script_id]
        self._save_json(self.scripts_index, index)

    def get_next_day_number(self) -> int:
        """获取下一个 Day 编号"""
        index = self._load_json(self.scripts_index) or []
        if not index:
            return 1
        # 找最大 day_number
        max_day = max((e.get("day_number", 0) for e in index), default=0)
        return max_day + 1

    # ─── 材料管理 ──────────────────────────────────────

    def save_materials(self, collection: MaterialCollection):
        """保存材料集，更新索引"""
        file_path = self.materials_dir / f"{collection.id}.json"
        self._save_json(file_path, collection.to_dict())
        # 更新索引
        index = self._load_json(self.materials_index) or []
        index = [e for e in index if e.get("id") != collection.id]
        index.insert(0, {
            "id": collection.id,
            "pushed_at": collection.pushed_at,
            "session": collection.session,
            "session_description": collection.session_description,
            "material_count": len(collection.materials),
        })
        self._save_json(self.materials_index, index)

    def load_materials(self, collection_id: str) -> Optional[MaterialCollection]:
        """加载单个材料集"""
        file_path = self.materials_dir / f"{collection_id}.json"
        data = self._load_json(file_path)
        if data:
            return MaterialCollection.from_dict(data)
        return None

    def list_materials(self) -> list[dict]:
        """列出所有材料集摘要，最新在前"""
        return self._load_json(self.materials_index) or []

    def get_latest_materials(self) -> Optional[MaterialCollection]:
        """获取最新一次推送的材料"""
        index = self._load_json(self.materials_index) or []
        if not index:
            return None
        latest_id = index[0]["id"]
        return self.load_materials(latest_id)
