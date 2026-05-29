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

        url = self._normalize_url(url_or_topic)
        platform = self._detect_platform(url)

        if platform == "youtube":
            return self._fetch_youtube(url)
        elif platform == "bilibili":
            return self._fetch_bilibili(url)
        else:
            return self._fetch_webpage(url)

    # ─── YouTube 字幕抓取 ──────────────────────────────

    def _fetch_youtube(self, url: str) -> ContentResult:
        """三引擎字幕抓取：页面直爬 → yt-dlp → youtube-transcript-api"""
        import re as _re, json as _json

        video_id = self._extract_youtube_id(url)
        if not video_id:
            return self._fallback(url, "youtube", "无法解析 YouTube 视频 ID，请确认链接格式正确")

        HEADERS = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }

        def _try_request(u, **kw):
            """请求 URL，代理优先（国内直连 YouTube 会被 GFW 丢包，浪费重试时间）"""
            proxy_cfg = {"http": "http://127.0.0.1:4780", "https": "http://127.0.0.1:4780"}
            for p in [proxy_cfg, None]:
                try:
                    timeout = kw.pop("timeout", 12) if p is not None else 5
                    r = requests.get(u, headers=HEADERS, proxies=p, timeout=timeout, **kw)
                    if r.status_code == 200 and "caption" not in kw:
                        # 简单检查是否 bot 页面
                        if len(r.text) > 5000 and "sign in" not in r.text[:1000].lower():
                            return r
                    elif "caption" in kw:
                        return r
                except Exception:
                    continue
            return None

        def _clean_vtt(raw):
            cleaned = _re.sub(r"<[^>]+>", "", raw)
            cleaned = _re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3} --> .*", "", cleaned)
            lines = [
                l.strip() for l in cleaned.split("\n")
                if l.strip()
                and not l.startswith("WEBVTT")
                and not l.startswith("Kind:")
                and not l.startswith("Language:")
            ]
            return " ".join(lines)

        # ── 方案一：直接爬 YouTube 页面提取 captionTracks ──
        try:
            page_url = f"https://www.youtube.com/watch?v={video_id}"
            r = _try_request(page_url)
            if r is not None:
                tracks_match = _re.findall(r"\"captionTracks\":\s*(\[.+?\])", r.text)
                if tracks_match:
                    tracks = _json.loads(tracks_match[0])
                    # 优先英文
                    en_tracks = [t for t in tracks
                                 if t.get("languageCode", "").startswith("en")]
                    target = en_tracks[0] if en_tracks else tracks[0]
                    sub_url = target.get("baseUrl") or target.get("url", "")
                    if sub_url:
                        sub_r = _try_request(sub_url)
                        if sub_r is not None:
                            text = _clean_vtt(sub_r.text)
                            if len(text) > 100:
                                if len(text) > 4000:
                                    text = text[:4000] + "..."
                                return ContentResult(
                                    title=url, text=text, source_type="youtube",
                                    source_url=url,
                                    metadata={"video_id": video_id, "method": "page-scrape"},
                                )
        except Exception:
            pass

        # ── 方案二：yt-dlp（不依赖 cookies 的轻量模式）─────
        try:
            import yt_dlp

            ydl_opts = {
                "quiet": True, "no_warnings": True, "skip_download": True,
                "extractor_args": {"youtube": {"player_client": ["ios", "web"]}},
            }
            # 尝试用代理（yt-dlp 内部处理）
            try:
                ydl_opts["proxy"] = "http://127.0.0.1:4780"
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_id, download=False)
            except Exception:
                del ydl_opts["proxy"]
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_id, download=False)

            title = info.get("title", url)
            all_subs = {}
            if info.get("subtitles"):
                all_subs.update(info["subtitles"])
            if info.get("automatic_captions"):
                all_subs.update(info["automatic_captions"])

            target = None
            for lang in ["en", "en-US", "en-GB"]:
                if lang in all_subs:
                    target = all_subs[lang]
                    break
            if target is None and all_subs:
                target = list(all_subs.values())[0]

            if target:
                sub_url = next((f["url"] for f in target if f.get("ext") == "vtt"), target[0]["url"])
                r = _try_request(sub_url)
                if r is not None:
                    text = _clean_vtt(r.text)
                    if len(text) > 4000:
                        text = text[:4000] + "..."
                    return ContentResult(
                        title=title, text=text, source_type="youtube",
                        source_url=url,
                        metadata={"video_id": video_id, "method": "yt-dlp"},
                    )
        except Exception:
            pass

        # ── 方案三：youtube-transcript-api ────────────────
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            from youtube_transcript_api._errors import (
                NoTranscriptFound, TranscriptsDisabled, VideoUnavailable,
            )
            from youtube_transcript_api.proxies import GenericProxyConfig

            # 代理优先，国内直连 YouTube 极易超时
            for use_pxy in [True, False]:
                try:
                    if use_pxy:
                        cfg = GenericProxyConfig(
                            http_url="http://127.0.0.1:4780",
                            https_url="http://127.0.0.1:4780",
                        )
                        yt_api = YouTubeTranscriptApi(proxy_config=cfg)
                    else:
                        yt_api = YouTubeTranscriptApi()
                    transcript_list = yt_api.list(video_id)
                    break
                except (VideoUnavailable, TranscriptsDisabled):
                    raise
                except Exception:
                    if use_pxy:
                        raise
                    continue

            transcript = None
            for finder in [
                lambda tl: tl.find_manually_created_transcript(["en"]),
                lambda tl: tl.find_generated_transcript(["en"]),
                lambda tl: tl.find_transcript(["en"]),
            ]:
                try:
                    transcript = finder(transcript_list)
                    break
                except NoTranscriptFound:
                    continue

            if transcript is None:
                try:
                    zh = transcript_list.find_transcript(["zh-Hans", "zh-Hant", "zh"])
                    transcript = zh.translate("en")
                except Exception:
                    pass

            if transcript is None:
                try:
                    first = list(transcript_list)[0]
                    transcript = first.translate("en") if "en" not in first.language_code else first
                except Exception:
                    pass

            if transcript is None:
                return self._fallback(url, "youtube", "该视频无可用字幕")

            captions = transcript.fetch()
            text = " ".join([c.text for c in captions])
            if len(text) > 4000:
                text = text[:4000] + "..."
            return ContentResult(
                title=url, text=text, source_type="youtube",
                source_url=url,
                metadata={"video_id": video_id, "method": "transcript-api"},
            )

        except Exception as e:
            return self._fallback(url, "youtube", f"字幕抓取失败（请尝试直接输入关键词生成脚本）: {str(e)[:100]}")

    def _extract_youtube_id(self, url: str) -> str:
        """从 YouTube URL 提取视频 ID，支持多种格式、参数顺序无关、大小写不敏感"""
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()

        # youtu.be 短链接
        if "youtu.be" in host:
            match = re.search(r"youtu\.be/([a-zA-Z0-9_-]+)", url, re.IGNORECASE)
            if match:
                return match.group(1)
            return ""

        # youtube.com 系列
        if "youtube.com" not in host:
            return ""

        # /watch — 用 parse_qs 提取 v 参数，无视参数顺序
        if parsed.path.rstrip("/").endswith("/watch"):
            params = parse_qs(parsed.query)
            v = params.get("v", [])
            if v:
                return v[0]
            return ""

        # 其他路径格式：embed / shorts / live / v
        path_patterns = [
            r"/embed/([a-zA-Z0-9_-]+)",
            r"/shorts/([a-zA-Z0-9_-]+)",
            r"/live/([a-zA-Z0-9_-]+)",
            r"/v/([a-zA-Z0-9_-]+)",
        ]
        for p in path_patterns:
            match = re.search(p, parsed.path, re.IGNORECASE)
            if match:
                return match.group(1)

        # 兜底：部分 URL 可能把 /watch?v= 嵌在 path 里（极少见）
        params = parse_qs(parsed.query)
        v = params.get("v", [])
        if v:
            return v[0]

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
        """判断输入是否为 URL（支持有/无协议前缀）"""
        text = text.strip()
        if re.match(r"https?://", text):
            return True
        # 识别无协议的裸域名 URL，如 "youtube.com/watch?v=xxx"、"youtu.be/xxx"
        if re.match(r"[\w.-]+\.\w{2,}/", text):
            return True
        return False

    @staticmethod
    def _normalize_url(text: str) -> str:
        """确保 URL 有协议前缀，无协议时自动补 https://"""
        text = text.strip()
        if not re.match(r"https?://", text):
            text = "https://" + text
        return text

    def _detect_platform(self, url: str) -> str:
        """识别 URL 对应平台（大小写不敏感）"""
        for platform, pattern in self._PLATFORM_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
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
