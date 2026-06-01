from __future__ import annotations

import logging
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application

from . import bot as bot_module
from .config import Settings
from .vault import io as vault_io

log = logging.getLogger(__name__)


class CheckinScheduler:
    def __init__(self, app: Application, settings: Settings) -> None:
        self.app = app
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone=ZoneInfo(settings.timezone))

    def install_from_profile(self) -> None:
        profile = vault_io.read_profile(self.settings.vault_path)
        morning = profile.metadata.get("morning_checkin")
        evening = profile.metadata.get("evening_checkin")
        tz = profile.metadata.get("timezone", self.settings.timezone)
        if morning and evening:
            self.install(morning, evening, tz)
        else:
            log.info("no profile yet — scheduler idle until /start completes")

    async def install_async(self, morning: str, evening: str, tz: str) -> None:
        # callable referenced from bot_data so onboarding can re-arm
        self.install(morning, evening, tz)

    def install(self, morning: str, evening: str, tz: str) -> None:
        zone = ZoneInfo(tz)
        m_hour, m_min = (int(x) for x in morning.split(":"))
        e_hour, e_min = (int(x) for x in evening.split(":"))

        self.scheduler.add_job(
            self._fire,
            CronTrigger(hour=m_hour, minute=m_min, timezone=zone),
            args=("morning",),
            id="morning_checkin",
            replace_existing=True,
        )
        self.scheduler.add_job(
            self._fire,
            CronTrigger(hour=e_hour, minute=e_min, timezone=zone),
            args=("evening",),
            id="evening_checkin",
            replace_existing=True,
        )
        log.info("scheduled morning=%s evening=%s tz=%s", morning, evening, tz)

    async def _fire(self, slot: str) -> None:
        log.info("scheduler firing %s", slot)
        await bot_module.send_scheduled_opener(self.app, slot)

    def start(self) -> None:
        self.scheduler.start()

    def shutdown(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
