"""
Telegram Background Remover Bot
--------------------------------
User ပုံပို့လိုက်တာနဲ့ background ကို AI (rembg / isnet-general-use model)
နဲ့ ဖြုတ်ပြီး transparent PNG အဖြစ် document အနေနဲ့ ပြန်ပို့ပေးတဲ့ bot။

GPU မလိုအပ်ပါ - CPU server (e.g. $5/mo VPS, Railway, Render) မှာ run လို့ရပါတယ်။
"""

import asyncio
import contextlib
import gc
import io
import logging
import time
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, Message
from PIL import Image
from rembg import new_session, remove

from config import (
    BOT_TOKEN,
    MAX_CONCURRENT_JOBS,
    MAX_FILE_SIZE_MB,
    MAX_IMAGE_DIMENSION,
    RATE_LIMIT_SECONDS,
    REMBG_MODEL,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
log = logging.getLogger("bg-remover-bot")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# --- Model: loaded once at startup, reused for every request (fast + memory-efficient) ---
# See config.py REMBG_MODEL for the memory/quality trade-off between models.
MODEL_SESSION = new_session(REMBG_MODEL)

# --- Concurrency control: prevents the CPU from being overloaded by parallel requests ---
_job_semaphore = asyncio.Semaphore(MAX_CONCURRENT_JOBS)

# --- Simple per-user rate limiting (in-memory) ---
_last_request_time: dict[int, float] = defaultdict(float)

# Cycled while a job runs so the status message feels alive instead of frozen.
_SPINNER_FRAMES = ["🎨", "✨", "🖌️", "⏳"]

# How often to refresh the status message / re-send the "uploading" indicator.
# Telegram's chat-action indicator expires after ~5s on its own, so this must
# stay under that to keep it visibly continuous.
_PROGRESS_INTERVAL_SECONDS = 3


async def _show_progress(chat_id: int, status_message: Message) -> None:
    """Keeps the user entertained/informed while a job runs in the background.

    Combines two things Telegram supports natively:
    - Editing the status message with an elapsed-time counter + spinner, so
      it's obvious the bot hasn't frozen.
    - Re-sending the "uploading a file" chat action, which shows Telegram's
      own animated indicator (the little pen/clip icon next to the bot's name).
    """
    start = time.monotonic()
    frame_index = 0

    while True:
        elapsed = int(time.monotonic() - start)
        frame = _SPINNER_FRAMES[frame_index % len(_SPINNER_FRAMES)]
        frame_index += 1

        with contextlib.suppress(Exception):
            # "upload_document" is the closest built-in action to what we're doing;
            # Telegram shows it as "sending a file..." near the bot's name.
            await bot.send_chat_action(chat_id, "upload_document")

        with contextlib.suppress(Exception):
            # Editing to the *same-looking* text with a changing counter is what
            # gives the "still working" feeling — a frozen message reads as stuck.
            await status_message.edit_text(
                f"{frame} Background ဖြုတ်နေပါတယ်... ({elapsed}s)\n"
                f"<i>ပုံအရွယ်အစားပေါ်မူတည်ပြီး 10-30 စက္ကန့်လောက် ကြာနိုင်ပါတယ်</i>"
            )

        await asyncio.sleep(_PROGRESS_INTERVAL_SECONDS)


def _is_rate_limited(user_id: int) -> bool:
    now = time.monotonic()
    if now - _last_request_time[user_id] < RATE_LIMIT_SECONDS:
        return True
    _last_request_time[user_id] = now
    return False


def _remove_background_sync(image_bytes: bytes) -> bytes:
    """CPU-bound work: runs in a worker thread so the event loop stays responsive.

    Large photos (modern phone cameras: 3000-4000px+) can push the model's
    memory usage well past 1GB and get the whole process killed by the host
    (OOM). Downscaling first keeps memory bounded and processing fast, with
    no visible quality loss for normal use (Telegram itself caps "photo"
    uploads at 1280px on the long edge anyway).
    """
    input_image = Image.open(io.BytesIO(image_bytes)).convert("RGBA")

    if max(input_image.size) > MAX_IMAGE_DIMENSION:
        input_image.thumbnail((MAX_IMAGE_DIMENSION, MAX_IMAGE_DIMENSION), Image.LANCZOS)

    output_image = remove(input_image, session=MODEL_SESSION)

    buffer = io.BytesIO()
    output_image.save(buffer, format="PNG")
    result = buffer.getvalue()

    # Release large image buffers immediately instead of waiting for the
    # next GC cycle — matters on 512MB-1GB hosts running back-to-back jobs.
    del input_image, output_image, buffer
    gc.collect()

    return result


@dp.message(CommandStart())
async def handle_start(message: Message) -> None:
    await message.answer(
        "👋 <b>Background Remover Bot</b>\n\n"
        "ပုံတစ်ပုံ ပို့လိုက်ပါ — background ကို ဖြုတ်ပြီး transparent PNG "
        "အဖြစ် ပြန်ပို့ပေးပါမယ်။\n\n"
        "📌 <i>Tip: ပုံအရည်အသွေး အကောင်းဆုံး ရဖို့ 'Photo' အစား "
        "'File'/'Document' အနေနဲ့ ပို့ပါ — Telegram က photo ကို compress "
        "လုပ်တတ်လို့ပါ။</i>"
    )


@dp.message(F.photo | (F.document & F.document.mime_type.startswith("image/")))
async def handle_image(message: Message) -> None:
    user_id = message.from_user.id

    if _is_rate_limited(user_id):
        await message.reply(
            f"⏳ ခဏစောင့်ပါ — {RATE_LIMIT_SECONDS} စက္ကန့်တစ်ခါ တောင်းဆိုနိုင်ပါတယ်။"
        )
        return

    # Pick the highest-quality file reference available
    if message.document:
        file_id = message.document.file_id
        file_size = message.document.file_size or 0
    else:
        file_id = message.photo[-1].file_id
        file_size = message.photo[-1].file_size or 0

    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        await message.reply(f"❌ ဖိုင်အရွယ်အစား {MAX_FILE_SIZE_MB}MB ထက် မကျော်ရပါ။")
        return

    status_message = await message.reply("🎨 Background ဖြုတ်နေပါတယ်...")
    progress_task = asyncio.create_task(_show_progress(message.chat.id, status_message))

    try:
        file = await bot.get_file(file_id)
        file_bytes_io = await bot.download_file(file.file_path)
        image_bytes = file_bytes_io.read()

        async with _job_semaphore:
            # rembg is CPU-bound / blocking — offload to a thread so other users
            # aren't blocked while this job runs.
            result_bytes = await asyncio.to_thread(_remove_background_sync, image_bytes)

        output_file = BufferedInputFile(result_bytes, filename="no_background.png")

        # IMPORTANT: send as a document, never as a photo.
        # Telegram re-compresses "photo" messages to JPEG, which destroys transparency.
        await message.reply_document(
            document=output_file,
            caption="✅ ပြီးပါပြီ!",
        )

    except Exception as exc:  # noqa: BLE001
        log.exception("Failed to process image for user %s: %s", user_id, exc)
        await message.reply(
            "❌ ပုံကို process လုပ်လို့ မရပါ။ ပုံဖျက်ဖြစ်နေတာ (သို့) "
            "မထောက်ပံ့တဲ့ format ဖြစ်နေနိုင်ပါတယ်။ ထပ်စမ်းကြည့်ပါ။"
        )
    finally:
        progress_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await progress_task
        await status_message.delete()


@dp.message()
async def handle_other(message: Message) -> None:
    await message.reply("📷 ပုံတစ်ပုံ ပို့ပေးပါ — background ဖြုတ်ပေးပါမယ်။")


async def main() -> None:
    log.info("Model loaded. Starting bot (polling mode)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
