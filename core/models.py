"""数据模型 — 口语脚本、学习材料、抓取结果"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContentResult:
    """连接器返回的统一内容格式"""
    title: str = ""
    text: str = ""            # 提取的文本内容（字幕/文章正文）
    source_type: str = ""     # youtube / bilibili / webpage / topic
    source_url: str = ""
    metadata: dict = field(default_factory=dict)  # 时长、作者等额外信息


@dataclass
class Script:
    """口语练习脚本"""
    id: str = ""                          # 文件名标识 (script_YYYYMMDD_HHMMSS)
    day_number: int = 1                   # Day X 序号
    created_at: str = ""                  # ISO 时间戳
    topic: str = ""                       # 主题 (3-5词简述)
    source_url: str = ""                  # 来源 URL
    source_type: str = ""                 # youtube / bilibili / webpage / topic
    english_script: str = ""              # 完整英文脚本
    chinese_translation: str = ""         # 完整中文翻译
    word_count: int = 0                   # 英文词数
    estimated_duration_seconds: int = 0   # 预估朗读时长(秒)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "day_number": self.day_number,
            "created_at": self.created_at,
            "topic": self.topic,
            "source_url": self.source_url,
            "source_type": self.source_type,
            "english_script": self.english_script,
            "chinese_translation": self.chinese_translation,
            "word_count": self.word_count,
            "estimated_duration_seconds": self.estimated_duration_seconds,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Script":
        return cls(**d)


@dataclass
class MaterialItem:
    """单条学习材料"""
    title: str = ""
    description: str = ""
    type: str = ""            # article / video / tool / podcast / book / course / framework
    url: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "description": self.description,
            "type": self.type,
            "url": self.url,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MaterialItem":
        return cls(**d)


@dataclass
class MaterialCollection:
    """一次推送的材料集合"""
    id: str = ""                          # materials_YYYYMMDD_morning / evening
    pushed_at: str = ""                   # ISO 时间戳
    session: str = ""                     # morning / evening
    session_description: str = ""         # 本期主题描述
    materials: list = field(default_factory=list)  # MaterialItem 列表

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pushed_at": self.pushed_at,
            "session": self.session,
            "session_description": self.session_description,
            "materials": [m.to_dict() if isinstance(m, MaterialItem) else m
                          for m in self.materials],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MaterialCollection":
        materials = [MaterialItem.from_dict(m) if isinstance(m, dict)
                     else m for m in d.get("materials", [])]
        return cls(
            id=d.get("id", ""),
            pushed_at=d.get("pushed_at", ""),
            session=d.get("session", ""),
            session_description=d.get("session_description", ""),
            materials=materials,
        )
