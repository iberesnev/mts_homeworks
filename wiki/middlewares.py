from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from urllib.parse import urlparse

from scrapy.http import Request, Response


@dataclass
class SlotBackoffConfig:
    max_delay: float = 60.0          # верхняя граница delay после backoff
    backoff_factor: float = 2.0      # во сколько раз увеличивать delay при 429


class SlotPolicyAndBackoffMiddleware:
    """
    1) Привязывает request.meta['download_slot'] к hostname, чтобы DOWNLOAD_SLOTS точно применялся.
    2) При 429 увеличивает delay для конкретного слота (backoff), чтобы снизить rate limit.
    """

    def __init__(self, download_slots: dict[str, dict[str, Any]], cfg: SlotBackoffConfig):
        self.download_slots = download_slots or {}
        self.cfg = cfg

    @classmethod
    def from_crawler(cls, crawler):
        download_slots = crawler.settings.getdict("DOWNLOAD_SLOTS") or {}
        cfg = SlotBackoffConfig(
            max_delay=crawler.settings.getfloat("SLOT_BACKOFF_MAX_DELAY", 60.0),
            backoff_factor=crawler.settings.getfloat("SLOT_BACKOFF_FACTOR", 2.0),
        )
        return cls(download_slots=download_slots, cfg=cfg)

    def process_request(self, request: Request, spider):
        hostname = urlparse(request.url).hostname or ""
        request.meta.setdefault("download_slot", hostname)

        self._apply_slot_policy_if_possible(spider, request.meta["download_slot"])
        return None

    def process_response(self, request: Request, response: Response, spider):
        slot_name = request.meta.get("download_slot")
        if slot_name and response.status == 429:
            self._backoff_slot_delay(spider, slot_name, response)
        return response

    def _get_downloader_slot(self, spider, slot_name: str):
        engine = getattr(spider.crawler, "engine", None)
        downloader = getattr(engine, "downloader", None)
        slots = getattr(downloader, "slots", None)
        if not slots:
            return None
        return slots.get(slot_name)

    def _apply_slot_policy_if_possible(self, spider, slot_name: str) -> None:
        slot = self._get_downloader_slot(spider, slot_name)
        if not slot:
            return

        policy = self.download_slots.get(slot_name)
        if not policy:
            return

        if "delay" in policy:
            slot.delay = float(policy["delay"])
        if "randomize_delay" in policy:
            slot.randomize_delay = bool(policy["randomize_delay"])
        if "concurrency" in policy:
            try:
                slot.concurrency = int(policy["concurrency"])
            except Exception:
                pass

    def _backoff_slot_delay(self, spider, slot_name: str, response: Response) -> None:
        slot = self._get_downloader_slot(spider, slot_name)
        if not slot:
            return

        retry_after = response.headers.get("Retry-After")
        new_delay: float | None = None

        if retry_after:
            try:
                new_delay = float(retry_after.decode("utf-8").strip())
            except Exception:
                new_delay = None

        if new_delay is None:
            new_delay = max(getattr(slot, "delay", 0.0) or 0.0, 0.5) * self.cfg.backoff_factor

        new_delay = min(new_delay, self.cfg.max_delay)

        old = getattr(slot, "delay", None)
        slot.delay = new_delay

        spider.logger.warning(
            f"[429 backoff] slot={slot_name!r}: delay {old} -> {new_delay} (status={response.status})"
        )