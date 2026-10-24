"""Telegram bot handlers, notifications, and scheduled nudges."""

import logging
import os
from typing import Any, Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from app.actions import ask_saves
from app.db import (
    get_next_nudge,
    get_setting,
    increment_times_surfaced,
    set_setting,
    update_status,
)
from app.llm import generate

logger = logging.getLogger(__name__)

# Global reference to running Telegram application
bot_app: Optional[Application] = None


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start: save chat_id and send welcome message."""
    if not update.effective_chat:
        return

    chat_id = str(update.effective_chat.id)
    set_setting("telegram_chat_id", chat_id)
    await update.message.reply_text(
        "👋 Resurface is ready!\n\n"
        "• When you save links or posts, I'll confirm them here.\n"
        "• Ask anything about your saves with: /ask <question>\n"
        "• Request an immediate nudge with: /nudge_now"
    )


async def ask_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /ask <question>: query saved items and respond."""
    if not update.message:
        return

    question = " ".join(context.args or []).strip()
    if not question:
        await update.message.reply_text(
            "Please provide a question, e.g.:\n/ask What books did I save?"
        )
        return

    await update.message.reply_chat_action("typing")
    answer = ask_saves(question)
    await update.message.reply_text(answer)


async def send_nudge(chat_id: str, bot: Any) -> bool:
    """Send a nudge to the given chat_id if candidate save exists."""
    save = get_next_nudge()
    if not save:
        return False

    save_id = save["id"]
    title = save.get("title") or "Untitled"
    item_type = save.get("type") or "other"
    action = save.get("action") or "other"
    why = save.get("why_saved") or ""
    url = save.get("url") or ""

    # Generate one-line reason to revisit
    prompt = (
        f"Item details:\n"
        f"- Title: {title}\n"
        f"- Type: {item_type}\n"
        f"- Why saved: {why}\n"
        f"- Action: {action}\n\n"
        "Write a concise one-line reason why the user should revisit this today."
    )
    try:
        reason = generate(
            prompt=prompt,
            system="You write concise, punchy one-line reminder reasons.",
        ).strip()
    except Exception as exc:
        logger.warning("Failed to generate nudge reason: %s", exc)
        reason = f"Time to revisit your saved {item_type}!"

    message_text = (
        f"💡 **Nudge**: {reason}\n\n"
        f"📌 **{title}** ({item_type})\n"
        f"🎯 Action: {action}"
    )
    if url:
        message_text += f"\n🔗 {url}"

    keyboard = [
        [
            InlineKeyboardButton("✅ Done", callback_data=f"done:{save_id}"),
            InlineKeyboardButton("⏭️ Ignore", callback_data=f"ignore:{save_id}"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await bot.send_message(
        chat_id=chat_id,
        text=message_text,
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )
    increment_times_surfaced(save_id)
    return True


async def nudge_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /nudge_now: trigger an immediate nudge."""
    if not update.effective_chat or not update.message:
        return

    chat_id = str(update.effective_chat.id)
    sent = await send_nudge(chat_id, context.bot)
    if not sent:
        await update.message.reply_text("Nothing waiting. Nice.")


async def nudge_job_callback(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Scheduled job callback to send recurring nudges."""
    chat_id = get_setting("telegram_chat_id")
    if chat_id:
        await send_nudge(chat_id, context.bot)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks for Done and Ignore."""
    query = update.callback_query
    if not query:
        return

    await query.answer()
    data = query.data or ""
    if ":" not in data:
        return

    action_type, save_id_str = data.split(":", 1)
    try:
        save_id = int(save_id_str)
    except ValueError:
        return

    if action_type == "done":
        update_status(save_id, "done")
        feedback = "✅ Marked as Done!"
    elif action_type == "ignore":
        update_status(save_id, "ignored")
        feedback = "⏭️ Marked as Ignored."
    else:
        return

    original = query.message.text if query.message else ""
    await query.edit_message_text(f"{original}\n\n{feedback}")


async def notify_new_save(save: dict[str, Any]) -> None:
    """Send a notification message to the registered chat_id when a save is added."""
    global bot_app
    if not bot_app:
        return

    chat_id = get_setting("telegram_chat_id")
    if not chat_id:
        logger.info("No Telegram chat_id registered yet. Send /start to bot to register.")
        return

    title = save.get("title") or "Untitled"
    item_type = save.get("type") or "other"
    why = save.get("why_saved") or ""
    action = save.get("action") or "other"
    url = save.get("url") or ""

    msg = f"Saved: {title} ({item_type}) - {why}. Action: {action}"
    if url:
        msg += f"\n{url}"

    try:
        await bot_app.bot.send_message(chat_id=chat_id, text=msg)
    except Exception as exc:
        logger.warning("Failed to send Telegram save notification: %s", exc)


def _setup_handlers(app: Application) -> None:
    """Register command and callback handlers."""
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("ask", ask_command))
    app.add_handler(CommandHandler("nudge_now", nudge_now_command))
    app.add_handler(CallbackQueryHandler(button_callback))


async def start_bot() -> Optional[Application]:
    """Initialize and start the Telegram bot with polling and job queue."""
    global bot_app
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip().strip('"').strip("'")
    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not configured; Telegram bot will not start.")
        return None

    try:
        bot_app = ApplicationBuilder().token(token).build()
        _setup_handlers(bot_app)

        await bot_app.initialize()
        await bot_app.start()
        await bot_app.updater.start_polling()

        # Configure recurring nudges
        interval_min = int(os.getenv("NUDGE_INTERVAL_MINUTES", "1440"))
        interval_sec = max(interval_min * 60, 60)
        if bot_app.job_queue:
            bot_app.job_queue.run_repeating(
                nudge_job_callback,
                interval=interval_sec,
                first=interval_sec,
            )

        logger.info("Telegram bot started successfully in polling mode.")
        return bot_app
    except Exception as exc:
        logger.error("Failed to start Telegram bot: %s", exc)
        return None


async def stop_bot() -> None:
    """Stop the Telegram bot gracefully on application shutdown."""
    global bot_app
    if not bot_app:
        return

    try:
        if bot_app.updater and bot_app.updater.running:
            await bot_app.updater.stop()
        if bot_app.running:
            await bot_app.stop()
        await bot_app.shutdown()
        logger.info("Telegram bot stopped.")
    except Exception as exc:
        logger.warning("Error stopping Telegram bot: %s", exc)
    finally:
        bot_app = None
