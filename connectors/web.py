"""多源内容抓取连接器 — YouTube / Bilibili / 网页 / 纯文本主题"""
from __future__ import annotations
import re
from urllib.parse import urlparse, parse_qs

import requests
import trafilatura

from core.models import ContentResult


class WebConnector:
    """视频/网页内容抓取连接器，自动根据 URL 类型选择抓取方式"""

    # 已知平台识别规则
    _PLATFORM_PATTERNS = [
        ("youtube", r"(youtube\.com|youtu\.be)"),
        ("bilibili", r"bilibili\.com"),
    ]

    def fetch(self, url_or_topic: str) -> ContentResult:
        """
        统一入口：根据输入类型自动判断抓取方式。
        - YouTube 链接 → 获取字幕
        - Bilibili 链接 → 获取字幕
        - 其他网页 → 提取正文
        - 纯文本 → 作为主题返回
        """
        if not self._is_url(url_or_topic):
            return ContentResult(
                title=url_or_topic,
                text=url_or_topic,
                source_type="topic",
            )

        platform = self._detect_platform(url_or_topic)

        if platform == "youtube":
            return self._fetch_youtube(url_or_topic)
        elif platform == "bilibili":
            return self._fetch_bilibili(url_or_topic)
        else:
            return self._fetch_webpage(url_or_topic)

    # ─── YouTube 字幕抓取 ──────────────────────────────

    def _fetch_youtube(self, url: str) -> ContentResult:
        """使用 youtube-transcript-api 获取字幕，优先英文手动字幕，回退自动生成/翻译"""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import (
                NoTranscriptFound, TranscriptsDisabled, VideoUnavailable
            )
            video_id = self._extract_youtube_id(url)
            if not video_id:
                return self._fallback(url, "youtube", "无法解析 YouTube 视频 ID，请确认链接格式正确")

            # 新版 API：创建实例，调用 .list() 获取字幕列表
            yt_api = YouTubeTranscriptApi()
            try:
                transcript_list = yt_api.list(video_id)
            except VideoUnavailable:
                return self._fallback(url, "youtube", "该视频不可用或已被删除")
            except TranscriptsDisabled:
                return self._fallback(url, "youtube", "该视频已禁用字幕功能")

            transcript = None

            # 优先级 1：手动英文字幕
            try:
                transcript = transcript_list.find_manually_created_transcript(["en"])
            except NoTranscriptFound:
                pass

            # 优先级 2：自动生成英文字幕
            if transcript is None:
                try:
                    transcript = transcript_list.find_generated_transcript(["en"])
                except NoTranscriptFound:
                    pass

            # 优先级 3：任意英文字幕（含翻译）
            if transcript is None:
                try:
                    transcript = transcript_list.find_transcript(["en"])
                except NoTranscriptFound:
                    pass

            # 优先级 4：中文字幕翻译成英文
            if transcript is None:
                try:
                    zh_transcript = transcript_list.find_transcript(["zh-Hans", "zh-Hant", "zh"])
                    transcript = zh_transcript.translate("en")
                except Exception:
                    pass

            # 优先级 5：获取任意可用字幕
            if transcript is None:
                try:
                    all_transcripts = list(transcript_list)
                    if all_transcripts:
                        first = all_transcripts[0]
                        if "en" not in first.language_code:
                            transcript = first.translate("en")
                        else:
                            transcript = first
                except Exception:
                    pass

            if transcript is None:
                return self._fallback(
                    url, "youtube",
                    "该视频无可用字幕（可能未上传字幕或仅含硬编码字幕）"
                )

            # 提取字幕文本
            captions = transcript.fetch()
            text = " ".join([c.text for c in captions])

            # 截断过长字幕（保留前 4000 字符）
            if len(text) > 4000:
                text = text[:4000] + "..."

            return ContentResult(
                title=url,
                text=text,
                source_type="youtube",
                source_url=url,
                metadata={"video_id": video_id},
            )

        except Exception as e:
            return self._fallback(url, "youtube", f"字幕抓取异常: {e}")

    def _extract_youtube_id(self, url: str) -> str:
        """从 YouTube URL 提取视频 ID，支持多种格式"""
        patterns = [
            r"youtu\.be/([a-zA-Z0-9_-]+)",
            r"youtube\.com/watch\?v=([a-zA-Z0-9_-]+)",
            r"youtube\.com/embed/([a-zA-Z0-9_-]+)",
            r"youtube\.com/shorts/([a-zA-Z0-9_-]+)",
            r"youtube\.com/live/([a-zA-Z0-9_-]+)",
            r"youtube\.com/v/([a-zA-Z0-9_-]+)",
        ]
        for p in patterns:
            match = re.search(p, url)
            if match:
                return match.group(1)
        return ""

    # ─── Bilibili 字幕抓取 ──────────────────────────────

    def _fetch_bilibili(self, url: str) -> ContentResult:
        """调用 Bilibili 公开 API 获取视频信息和字幕"""
        try:
            # 解析视频 ID
            match = re.search(r"bilibili\.com/video/(BV[a-zA-Z0-9]+|av\d+)", url)
            if not match:
                return self._fallback(url, "bilibili", "无法解析 Bilibili 视频 ID")
            video_ref = match.group(1)

            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.bilibili.com/",
            }

            # 获取视频基本信息
            if video_ref.startswith("BV"):
                info_url = f"https://api.bilibili.com/x/web-interface/view?bvid={video_ref}"
            else:
                info_url = f"https://api.bilibili.com/x/web-interface/view?aid={video_ref}"

            resp = requests.get(info_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                return self._fallback(url, "bilibili", f"API 返回 {resp.status_code}")

            data = resp.json()
            if data.get("code") != 0:
                return self._fallback(url, "bilibili", data.get("message", "未知错误"))

            video_info = data.get("data", {})
            title = video_info.get("title", "")
            desc = video_info.get("desc", "")
            subtitle_url = video_info.get("subtitle", {}).get("list", [])

            # 如果有字幕，尝试获取
            subtitle_text = ""
            if subtitle_url:
                for sub in subtitle_url:
                    sub_url = sub.get("subtitle_url", "")
                    if sub_url:
                        sub_resp = requests.get(sub_url, headers=headers, timeout=10)
                        sub_data = sub_resp.json()
                        # Bilibili 字幕格式：body 是列表，每项有 content
                        for item in sub_data.get("body", []):
                            subtitle_text += item.get("content", "") + " "

            # 合并标题、描述、字幕作为内容
            combined = f"Title: {title}\n\n"
            if subtitle_text.strip():
                combined += f"Subtitle: {subtitle_text.strip()}\n\n"
            if desc:
                # 截断过长的简介
                combined += f"Description: {desc[:800]}"

            if len(combined) > 4000:
                combined = combined[:4000] + "..."

            return ContentResult(
                title=title or url,
                text=combined,
                source_type="bilibili",
                source_url=url,
                metadata={"video_id": video_ref, "title": title},
            )

        except Exception as e:
            return self._fallback(url, "bilibili", str(e))

    # ─── 通用网页正文提取 ──────────────────────────────

    def _fetch_webpage(self, url: str) -> ContentResult:
        """使用 trafilatura 提取网页正文"""
        try:
            # 先尝试直接下载已抓取好的 HTML
            downloaded = trafilatura.fetch_url(url)
            if downloaded is None:
                # trafilatura 自带 fetch 失败，尝试手动请求
                headers = {
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                  "AppleWebKit/537.36"
                }
                resp = requests.get(url, headers=headers, timeout=15)
                downloaded = resp.text

            text = trafilatura.extract(downloaded, include_comments=False,
                                       include_tables=False)
            if not text:
                return self._fallback(url, "webpage", "无法提取网页正文")

            title = ""
            title_match = re.search(r"<title>(.+?)</title>",
                                    downloaded[:2000], re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()

            if len(text) > 4000:
                text = text[:4000] + "..."

            return ContentResult(
                title=title or url,
                text=text,
                source_type="webpage",
                source_url=url,
            )

        except Exception as e:
            return self._fallback(url, "webpage", str(e))

    # ─── 工具方法 ──────────────────────────────────────

    def _is_url(self, text: str) -> bool:
        """判断输入是否为 URL"""
        return bool(re.match(r"https?://", text.strip()))

    def _detect_platform(self, url: str) -> str:
        """识别 URL 对应平台"""
        for platform, pattern in self._PLATFORM_PATTERNS:
            if re.search(pattern, url):
                return platform
        return "webpage"

    def _fallback(self, url: str, source_type: str, reason: str) -> ContentResult:
        """
        抓取失败的优雅回退：返回降级 ContentResult，
        让 LLM 基于有限信息（标题/URL）继续生成脚本。
        """
        return ContentResult(
            title=url,
            text=f"[Content extraction limited: {reason}]\nURL: {url}",
            source_type=source_type,
            source_url=url,
            metadata={"fallback_reason": reason},
        )
