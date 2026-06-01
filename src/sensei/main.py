from __future__ import annotations

import logging

from .bot import build_application
from .config import get_settings
from .conversation.manager import ConversationManager
from .db.cache import init_db
from .llm.gemini import GeminiClient
from .scheduler import CheckinScheduler
from .tools.context import ToolContext

log = logging.getLogger(__name__)


def run() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )

    settings.vault_path.mkdir(parents=True, exist_ok=True)
    init_db(settings.db_path)

    llm = GeminiClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
    ctx = ToolContext(
        user_id=settings.user_id,
        vault_path=settings.vault_path,
        db_path=settings.db_path,
        tz=settings.tz,
    )
    manager = ConversationManager(llm=llm, ctx=ctx)

    scheduler_holder: dict[str, CheckinScheduler] = {}

    async def post_init(application):
        scheduler = CheckinScheduler(application, settings)
        application.bot_data["scheduler_install"] = scheduler.install_async
        application.bot_data["tool_context"] = ctx
        scheduler.install_from_profile()
        scheduler.start()
        scheduler_holder["s"] = scheduler
        log.info("ready")

    async def post_shutdown(application):
        s = scheduler_holder.get("s")
        if s is not None:
            s.shutdown()

    app = build_application(settings, manager, post_init=post_init, post_shutdown=post_shutdown)
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    run()
