import asyncio
import logging
from typing import Optional
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message, InlineKeyboardMarkup, InlineKeyboardButton,
    CallbackQuery, BotCommand, LabeledPrice, PreCheckoutQuery,
    BufferedInputFile, BusinessConnection, BusinessMessagesDeleted, FSInputFile
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiohttp
import json
import os
from datetime import datetime, timedelta
import base64
import subprocess
import re
import html
import random
import shutil
from urllib.parse import quote

try:
    from emoji_to_custom_id import EMOJI_TO_CUSTOM_ID
except Exception:
    EMOJI_TO_CUSTOM_ID = {}

# Обратный маппинг custom_emoji_id -> unicode emoji (для fallback внутри <tg-emoji>).
CUSTOM_ID_TO_EMOJI = {}
for _emoji_char, _emoji_id in EMOJI_TO_CUSTOM_ID.items():
    if _emoji_id not in CUSTOM_ID_TO_EMOJI:
        CUSTOM_ID_TO_EMOJI[_emoji_id] = _emoji_char

# ==================== КОНФИГУРАЦИЯ ====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CRYPTO_BOT_TOKEN = os.getenv("CRYPTO_BOT_TOKEN")
CRYPTO_BOT_API = "https://pay.crypt.bot/api" # не менять!
ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS", "228").split(",") if x.strip().isdigit()]
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "@inzdi")
#остальное как есть:
API_URL = "http://api.onlysq.ru/ai/v2"
IMAGE_API_URL = "https://api.onlysq.ru/ai/imagen"
FREE_IMAGE_API_URL = "https://image.pollinations.ai/prompt"
API_BEARER_TOKEN = os.getenv("API_BEARER_TOKEN", "")
# Ключ DeepSeek (sk-...) — читается при запуске, не при сборке (чтобы Railway не требовал переменную на build)
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
IMAGE_DAILY_LIMIT_PRO = int(os.getenv("IMAGE_DAILY_LIMIT_PRO", "20"))
IMAGE_MONTHLY_LIMIT_PRO = int(os.getenv("IMAGE_MONTHLY_LIMIT_PRO", "300"))
FREE_TRIAL_LIMIT = int(os.getenv("FREE_TRIAL_LIMIT", "3"))
FREE_IMAGE_TRIAL_LIMIT = int(os.getenv("FREE_IMAGE_TRIAL_LIMIT", "2"))
REFERRAL_BONUS_REQUESTS = int(os.getenv("REFERRAL_BONUS_REQUESTS", "3"))
DAILY_FREE_REQUESTS = int(os.getenv("DAILY_FREE_REQUESTS", "1"))
FIRST_BUY_DISCOUNT_STARS = int(os.getenv("FIRST_BUY_DISCOUNT_STARS", "49"))
FIRST_BUY_DISCOUNT_USD = float(os.getenv("FIRST_BUY_DISCOUNT_USD", "0.5"))
WEEKLY_PRICE_STARS = int(os.getenv("WEEKLY_PRICE_STARS", "29"))
WEEKLY_PRICE_USD = float(os.getenv("WEEKLY_PRICE_USD", "0.3"))
WEEKLY_DAYS = 7
DEFAULT_MODEL = "deepseek-chat"
MAX_MESSAGE_LENGTH = 4000
SYSTEM_GIF_URL = os.getenv("SYSTEM_GIF_URL", "").strip()
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DEFAULT_SYSTEM_GIF_URLS = []
SECTION_MEDIA_PATHS = {
    "start": os.path.join(PROJECT_ROOT, "1.gif"),
    "subscription": os.path.join(PROJECT_ROOT, "2.gif"),
    "settings": os.path.join(PROJECT_ROOT, "3.gif"),
    "thinking": os.path.join(PROJECT_ROOT, "4.gif")
}
DEFAULT_BUTTON_EMOJI_PACK = {
    # Main menu
    "models": "6030400221232501136",        # 🤖
    "thinking": "5864019342873598613",      # 🧠
    "subscription": "6028338546736107668",  # ⭐️
    "info": "6028435952299413210",          # ℹ
    "home": "6042137469204303531",          # 🏠
    "image": "6030466823290360017",         # 🖼
    # Model navigation
    "model_item": "5936143551854285132",    # 📊
    "nav_prev": "5960671702059848143",      # ⬅️
    "nav_next": "5773626993010546707",      # ▶️
    "nav_back": "5960671702059848143",      # ◁ назад
    # Subscription/payment
    "extend_stars": "6028338546736107668",  # ⭐️
    "extend_crypto": "5776023601941582822", # 💎
    "buy_stars": "5778613750688911681",     # 🪙
    "buy_crypto": "5776023601941582822",    # 💎
    "pay_crypto": "5776023601941582822",    # 💎
    "money": "5904462880941545555",         # 🪙
    "money_send": "5890848474563352982",    # 🪙 отправить
    "money_receive": "5879814368572478751", # 🏧 принять
    # Common actions
    "cancel": "6030757850274336631",        # ❌
    "confirm": "5774022692642492953",       # ✅
    "confirm_clear": "5774022692642492953", # ✅
    "required_channel": "6021418126061605425",  # 📢
    "check_channels": "5843596438373667352",    # ✅️
    "contact_admin": "6030784887093464891",     # 💬
    "loading": "5345906554510012647",       # 🔄
    "code": "5940433880585605708",          # 🔨 </>
    "broadcast": "5370599459661045441",     # 📢
    "delete": "6039522349517115015",        # 🗑
    "add": "5774022692642492953",           # ➕
    "block": "6030757850274336631",         # 🚫
    "unblock": "5774034804450267485",       # ➖
    # Style presets
    "preset_serious": "6030537007350944596",    # 🛡
    "preset_neutral": "6041748912102968702",    # 😐
    "preset_funny": "6043996047582170909",      # 😀
    "preset_friend": "5774034804450267485",     # 🙂
    "thinking_edit": "6039779802741739617",      # ✏️
    "thinking_delete": "6039522349517115015",    # 🗑
    # Admin panel
    "admin_stats": "5936143551854285132",       # 📊
    "admin_price": "5904462880941545555",       # 💰
    "admin_models": "6030400221232501136",      # 🧬
    "admin_grant": "5774022692642492953",       # ✅
    "admin_revoke": "6030757850274336631",      # ⛔
    "admin_broadcast": "5370599459661045441",   # 📢
    "admin_users": "6030784887093464891",       # 👥
    "admin_channels": "6021418126061605425",    # 📺
    "admin_blacklist": "6030757850274336631",   # 🚫
    "admin_media": "6030466823290360017",       # 🖼️
    # Models page
    "text_model": "6039779802741739617",        # ✏️
    "image_model": "6030466823290360017",       # 🎨
}
TEXT_EMOJI_IDS = {
    "wave": "6041921818896372382",          # 👋
    "crown": "5805553606635559688",         # 👑
    "robot": "6030400221232501136",         # 🤖
    "chat": "6030784887093464891",          # 💬
    "style": "5864019342873598613",         # 🧠
    "star": "6028338546736107668",          # ⭐️
    "info": "6028435952299413210",          # ℹ
    "home": "6042137469204303531",          # 🏠
    "money": "5778421276024509124",         # 💰
    "clock": "5850317551090800862",         # ⏰
    "rocket": "6041731551845159060",        # 🎉 (ассоц. преимущества/апгрейд)
    "models": "6030400221232501136",        # 🤖
    "image": "6030466823290360017",         # 🖼
    "note": "5920046907782074235",          # 📝
    "check": "5774022692642492953"          # ✅
}

STYLE_PRESET_PROMPTS = {
    "serious": (
        "Стиль: деловой и чёткий. Без эмоций, без сленга. "
        "Факты, структура, конкретика. Коротко."
    ),
    "neutral": (
        "Стиль: спокойный и понятный. "
        "Дружелюбно, но без лишних эмоций. Коротко и по делу."
    ),
    "funny": (
        "Стиль: лёгкий, с юмором. "
        "Шути уместно, но не теряй пользу. Коротко."
    ),
    "friend": (
        "Стиль: как близкий друг. "
        "Тепло, просто, поддерживающе. Можно разговорный язык. Коротко."
    )
}

STYLE_PRESET_LABELS = {
    "serious": "Серьезный",
    "neutral": "Нейтральный",
    "funny": "Веселый",
    "friend": "Друг"
}

# Короткие описания пресетов для юзера (чем отличаются)
STYLE_PRESET_DESCRIPTIONS = {
    "serious": "Для работы и деловых вопросов. Чётко, без лишнего.",
    "neutral": "На каждый день. Понятно, спокойно, по делу.",
    "funny": "С юмором. Когда хочется поднять настроение.",
    "friend": "Как друг. Тепло, просто, по-человечески."
}

START_EXAMPLES = [
    "«Что приготовить из курицы, риса и овощей?»",
    "«Напиши поздравление маме — тёплое, не банальное»",
    "«Что подарить мужу на ДР? Бюджет 3000₽»",
    "«Объясни ребёнку 7 лет, почему идёт дождь»",
    "«Напиши ответ начальнику — вежливо, но твёрдо»",
    "«Куда поехать на выходные из Москвы с детьми?»",
    "«Посоветуй сериал — чтобы не оторваться»",
    "«Помоги написать резюме — я менеджер, хочу в IT»",
    "«Как оформить налоговый вычет за квартиру?»",
    "«Тренировка дома на 20 минут — без инвентаря»",
    "«Нарисуй открытку с днём рождения для бабушки»",
    "«Напиши отзыв на товар — коротко и по делу»",
    "«Что значит эта ошибка в стиральной машине?»",
    "«Составь список покупок на неделю для семьи из 4»",
    "«Как успокоить ребёнка, когда капризничает?»",
]

RESPONSE_STYLE_SYSTEM_PROMPT = (
    "Ты — помощник в Telegram. Тебя спрашивают занятые взрослые люди.\n\n"
    "ГЛАВНОЕ ПРАВИЛО: ДЕЛАЙ, а не объясняй как делать.\n"
    "- Просят написать поздравление — ПИШИ ГОТОВОЕ ПОЗДРАВЛЕНИЕ, а не инструкцию.\n"
    "- Просят составить меню — ПИШИ МЕНЮ, а не советы по составлению.\n"
    "- Просят текст письма — ПИШИ ПИСЬМО.\n"
    "- Человек хочет получить ГОТОВЫЙ РЕЗУЛЬТАТ, который можно скопировать и использовать.\n\n"
    "ДЛИНА: КОРОТКО. Максимум 5-8 строк для простых вопросов. Максимум 15 строк для сложных.\n"
    "Никаких простыней текста. Люди читают с телефона.\n\n"
    "ФОРМАТ:\n"
    "- Сразу к делу. Без вступлений типа «Конечно!», «Отличный вопрос!», «Давай разберёмся».\n"
    "- Без воды, повторов и очевидных вещей.\n"
    "- Списки — коротко, 3-5 пунктов максимум.\n"
    "- В конце можно 1 короткий вопрос-предложение: «Сделать короче?», «Нужен другой вариант?»\n\n"
    "СТИЛЬ: живой, тёплый, без канцелярита. Как умный друг, который сразу даёт ответ.\n\n"
    "Разметка: **жирный**, *курсив*, списки через '- '. Без таблиц и [ссылок](url). "
    "Не выдумывай факты."
)

RESPONSE_STYLE_HARD_GUARD_PROMPT = (
    "КРИТИЧНО: будь КРАТКИМ. Не больше 15 строк. Давай ГОТОВЫЙ РЕЗУЛЬТАТ, а не инструкцию. "
    "Если просят написать текст — пиши текст. Если просят совет — давай конкретный совет без воды. "
    "Формат Telegram: коротко, чисто, по делу."
)


def _get_deepseek_key() -> str:
    """Читать ключ только при первом запросе к AI, не при импорте модуля."""
    return os.getenv("DEEPSEEK_API_KEY", "").strip()

if not TELEGRAM_TOKEN:
    similar_keys = sorted(
        [k for k in os.environ.keys() if "TELEGRAM" in k.upper() or "TOKEN" in k.upper()]
    )
    raise RuntimeError(
        "Set TELEGRAM_TOKEN environment variable before start. "
        f"Visible similar env keys: {similar_keys}"
    )

if not CRYPTO_BOT_TOKEN:
    logging.warning("CRYPTO_BOT_TOKEN is not set. CryptoBot payments will be unavailable.")

if not API_BEARER_TOKEN:
    logging.warning("API_BEARER_TOKEN is not set. Text/image generation via onlysq.ru may be unavailable.")

if not ADMIN_IDS:
    raise RuntimeError("Set ADMIN_IDS environment variable with at least one Telegram user ID")

# Пути к файлам (DATA_DIR — для персистентного хранения при деплое)
# 1) DATA_DIR в .env  2) RAILWAY_VOLUME_MOUNT_PATH (Railway)  3) ./data
_data_dir = (
    os.getenv("DATA_DIR", "").strip()
    or os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
)
DATA_DIR = os.path.abspath(_data_dir) if _data_dir else os.path.join(PROJECT_ROOT, "data")
USERS_DIR = os.path.join(DATA_DIR, "users")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
BLACKLIST_FILE = os.path.join(DATA_DIR, "blacklist.json")
PENDING_INVOICES_FILE = os.path.join(DATA_DIR, "pending_invoices.json")
BUSINESS_CONNECTIONS_FILE = os.path.join(DATA_DIR, "business_connections.json")

PAYMENTS_LOG_FILE = os.path.join(DATA_DIR, "payments.log")
REQUESTS_LOG_FILE = os.path.join(DATA_DIR, "requests.log")
FEEDBACK_LOG_FILE = os.path.join(DATA_DIR, "feedback.log")

# Создаем директории
os.makedirs(USERS_DIR, exist_ok=True)
logging.info(f"📁 Данные: {DATA_DIR}")


# ==================== БЕЗОПАСНАЯ РАБОТА С ФАЙЛАМИ ====================
def _safe_write_json(file_path: str, data):
    """Атомарная запись JSON: пишем во временный файл, затем переименовываем.
    Это гарантирует, что файл не повредится при краше/рестарте."""
    tmp_path = file_path + ".tmp"
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)
    except Exception as e:
        logging.error(f"Ошибка записи {file_path}: {e}")
        # Удаляем битый tmp если остался
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise


def _safe_read_json(file_path: str, default=None):
    """Безопасное чтение JSON с восстановлением из .bak при повреждении."""
    for path in [file_path, file_path + ".bak"]:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                    if not content:
                        continue
                    data = json.loads(content)
                    # Если прочитали из .bak — восстанавливаем основной файл
                    if path.endswith(".bak"):
                        logging.warning(f"⚠️ Восстановлено из бэкапа: {file_path}")
                        _safe_write_json(file_path, data)
                    else:
                        # Основной файл OK — обновляем бэкап
                        try:
                            shutil.copy2(file_path, file_path + ".bak")
                        except Exception:
                            pass
                    return data
            except (json.JSONDecodeError, ValueError) as e:
                logging.warning(f"⚠️ Повреждён {path}: {e}, пробую бэкап...")
                continue
            except Exception as e:
                logging.error(f"Ошибка чтения {path}: {e}")
                continue
    return default() if callable(default) else (default if default is not None else None)


def _append_payment_log(user_id: int, amount, currency: str, method: str):
    """Дописать запись об оплате в append-only лог (никогда не перезаписывается)."""
    try:
        line = json.dumps({
            "ts": datetime.now().isoformat(),
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "method": method
        }, ensure_ascii=False)
        with open(PAYMENTS_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
            f.flush()
    except Exception as e:
        logging.error(f"Ошибка записи payment log: {e}")

def _rotate_request_log():
    """Удалить записи старше 90 дней из лога."""
    try:
        if not os.path.exists(REQUESTS_LOG_FILE):
            return
        cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        kept = []
        with open(REQUESTS_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("ts", "") >= cutoff:
                        kept.append(line)
                except Exception:
                    continue
        with open(REQUESTS_LOG_FILE, 'w', encoding='utf-8') as f:
            f.writelines(kept)
    except Exception as e:
        logging.error(f"Ошибка ротации request log: {e}")


_LOG_ROTATION_COUNTER = 0


def _categorize_request(text: str) -> str:
    """Определить категорию запроса для аналитики."""
    t = text.lower()
    if any(w in t for w in ["рецепт", "приготов", "меню", "блюд", "ужин", "завтрак", "обед"]):
        return "food"
    if any(w in t for w in ["напиши", "текст", "письм", "поздравл", "пост", "стать"]):
        return "writing"
    if any(w in t for w in ["подар", "купить", "выбрать", "посоветуй"]):
        return "advice"
    if any(w in t for w in ["ребён", "детск", "школ", "урок", "объясни"]):
        return "kids"
    if any(w in t for w in ["картинк", "нарисуй", "рисунок", "открытк", "логотип"]):
        return "image"
    if any(w in t for w in ["работ", "резюме", "собеседован", "начальник"]):
        return "work"
    if any(w in t for w in ["здоровь", "болит", "врач", "лекарств"]):
        return "health"
    return "other"


def _append_request_log(user_id: int, request_type: str, user_input: str, ai_response: str, model: str = ""):
    """Дописать запрос+ответ в append-only лог."""
    global _LOG_ROTATION_COUNTER
    try:
        category = _categorize_request(user_input) if request_type == "text" else request_type
        line = json.dumps({
            "ts": datetime.now().isoformat(),
            "user_id": user_id,
            "type": request_type,
            "category": category,
            "input": user_input[:500],
            "response": ai_response[:1000],
            "model": model
        }, ensure_ascii=False)
        with open(REQUESTS_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
            f.flush()
        # Ротация каждые 500 записей
        _LOG_ROTATION_COUNTER += 1
        if _LOG_ROTATION_COUNTER >= 500:
            _LOG_ROTATION_COUNTER = 0
            _rotate_request_log()
    except Exception as e:
        logging.error(f"Ошибка записи request log: {e}")


# In-memory dict для связи message_id → данные запроса (для фидбэка)
_pending_feedback = {}


def _append_feedback_log(user_id: int, message_id: int, feedback: str, query: str = "", response: str = ""):
    """Дописать фидбэк в append-only лог."""
    try:
        line = json.dumps({
            "ts": datetime.now().isoformat(),
            "user_id": user_id,
            "message_id": message_id,
            "feedback": feedback,
            "query": query[:500],
            "response": response[:500],
        }, ensure_ascii=False)
        with open(FEEDBACK_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(line + "\n")
            f.flush()
    except Exception as e:
        logging.error(f"Ошибка записи feedback log: {e}")


def get_feedback_stats() -> dict:
    """Получить статистику фидбэка."""
    stats = {"total": 0, "positive": 0, "negative": 0}
    try:
        if not os.path.exists(FEEDBACK_LOG_FILE):
            return stats
        with open(FEEDBACK_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    stats["total"] += 1
                    if entry.get("feedback") == "up":
                        stats["positive"] += 1
                    elif entry.get("feedback") == "down":
                        stats["negative"] += 1
                except Exception:
                    continue
    except Exception:
        pass
    return stats


def get_user_request_count(user_id: int, since_date: str = None) -> int:
    """Подсчитать количество запросов пользователя из requests.log."""
    count = 0
    try:
        if not os.path.exists(REQUESTS_LOG_FILE):
            return 0
        with open(REQUESTS_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    entry = json.loads(line.strip())
                    if entry.get("user_id") == user_id:
                        if since_date and entry.get("ts", "") < since_date:
                            continue
                        count += 1
                except Exception:
                    continue
    except Exception:
        pass
    return count


def extract_url(text: str) -> str:
    """Извлечь первый URL из текста."""
    if not text:
        return ""
    match = re.search(r'https?://[^\s<>"\']+', text)
    return match.group(0) if match else ""


async def fetch_and_summarize_url(url: str, user_id: int) -> str:
    """Загрузить страницу по URL и вернуть AI-саммари."""
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, allow_redirects=True) as resp:
                if resp.status != 200:
                    return f"Не удалось загрузить страницу (код {resp.status})."
                content_type = resp.headers.get("Content-Type", "")
                if "text/html" not in content_type:
                    return "Эта ссылка ведёт не на веб-страницу. Я могу анализировать только HTML-страницы."
                raw = await resp.read()
                if len(raw) > 100_000:
                    raw = raw[:100_000]
                html_text = raw.decode('utf-8', errors='replace')
        # Очистка HTML — извлекаем текст
        clean = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', html_text, flags=re.IGNORECASE)
        clean = re.sub(r'<style[^>]*>[\s\S]*?</style>', '', clean, flags=re.IGNORECASE)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        clean = re.sub(r'\s+', ' ', clean).strip()
        clean = clean[:3000]
        if len(clean) < 50:
            return "Не удалось извлечь текст со страницы."
        summary_prompt = (
            "Суммируй содержание этой веб-страницы по-русски. "
            "Выдели 3-5 ключевых мыслей, кратко и по делу:\n\n"
            f"{clean}"
        )
        ai_response = await get_ai_response(user_id, summary_prompt)
        return f"📎 <b>Краткое содержание ссылки:</b>\n\n{ai_response}"
    except asyncio.TimeoutError:
        return "Страница загружается слишком долго (>15 сек). Попробуй другую ссылку."
    except Exception as e:
        logging.error(f"Ошибка fetch_and_summarize_url: {e}")
        return "Не получилось загрузить страницу. Проверь ссылку и попробуй ещё раз."


# ==================== ПРОВЕРКА ЗАВИСИМОСТЕЙ ДЛЯ ГОЛОСА ====================
logging.basicConfig(level=logging.INFO)

try:
    import speech_recognition as sr
except ImportError:
    sr = None
    logging.warning("⚠️ SpeechRecognition не найден. Установите зависимость заранее через requirements.")

# Проверка ffmpeg
try:
    result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise FileNotFoundError
except FileNotFoundError:
    logging.warning("⚠️ ffmpeg не установлен!")
    logging.warning("Установите для распознавания голоса:")
    logging.warning("  Ubuntu: sudo apt install ffmpeg")
    logging.warning("  MacOS: brew install ffmpeg")
    logging.warning("  Windows: скачайте с ffmpeg.org")


def sanitize_user_input(text: str, max_length: int = 4000) -> str:
    """Ограничить размер и убрать управляющие символы из пользовательского ввода."""
    if not text:
        return ""
    text = str(text)[:max_length]
    return ''.join(ch for ch in text if ch.isprintable() or ch in '\n\t').strip()


def _custom_emoji_tag(emoji_id: str, fallback_emoji: str = "✨") -> str:
    """
    Сформировать tg-emoji тег с fallback символом.
    Некоторые клиенты не показывают custom emoji без содержимого внутри тега.
    """
    fallback = fallback_emoji or "✨"
    return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'


def text_emoji(name: str) -> str:
    """Вернуть HTML-тег custom emoji для текста."""
    emoji_id = TEXT_EMOJI_IDS.get(name)
    if not emoji_id:
        return ""
    fallback_emoji = CUSTOM_ID_TO_EMOJI.get(emoji_id, "✨")
    return _custom_emoji_tag(emoji_id, fallback_emoji)


def button_emoji_tag(button_key: str) -> str:
    """Вернуть HTML-тег custom emoji из того же пака, что и у кнопок."""
    emoji_id = get_button_emoji_pack().get(button_key)
    if not emoji_id:
        return ""
    fallback_emoji = CUSTOM_ID_TO_EMOJI.get(emoji_id, "✨")
    return _custom_emoji_tag(emoji_id, fallback_emoji)


def _unicode_to_custom_emoji_tag(emoji_char: str) -> str:
    """Конвертировать обычный emoji в тег custom emoji."""
    emoji_id = EMOJI_TO_CUSTOM_ID.get(emoji_char)
    if not emoji_id:
        return emoji_char
    return _custom_emoji_tag(emoji_id, emoji_char)


def normalize_text_emojis(text: str) -> str:
    """Заменить обычные emoji в тексте на custom emoji-теги (если есть маппинг).
    Не трогает emoji внутри существующих <tg-emoji> тегов."""
    if not text or not EMOJI_TO_CUSTOM_ID:
        return text

    # Разбиваем текст на части: внутри <tg-emoji> тегов и вне их
    parts = re.split(r'(<tg-emoji[^>]*>.*?</tg-emoji>)', text)
    for i, part in enumerate(parts):
        # Четные индексы — текст вне тегов, нечетные — сами теги
        if i % 2 == 0:
            for emoji_char in sorted(EMOJI_TO_CUSTOM_ID.keys(), key=len, reverse=True):
                if emoji_char in part:
                    part = part.replace(emoji_char, _unicode_to_custom_emoji_tag(emoji_char))
            parts[i] = part
    return "".join(parts)


def get_default_header_emoji_tag() -> str:
    """Базовая анимодзи-иконка для заголовков во всех HTML-сообщениях."""
    return (
        text_emoji("wave")
        or text_emoji("star")
        or button_emoji_tag("subscription")
        or button_emoji_tag("info")
    )


def add_header_emoji_to_bold_lines(text: str, header_emoji_tag: Optional[str] = None) -> str:
    """Добавить анимодзи только к первому заголовку <b>...</b> в сообщении."""
    if not text:
        return text
    header_prefix = f"{header_emoji_tag or get_default_header_emoji_tag()} "
    return re.sub(
        r'(?m)^(?!\s*<tg-emoji)(\s*<b>[^<].*?</b>)',
        rf'{header_prefix}\1',
        text,
        count=1
    )


def strip_custom_emoji_outside_first_header(text: str) -> str:
    """Оставить custom emoji только в первой строке-заголовке, в остальных местах убрать."""
    if not text:
        return text

    lines = text.splitlines()
    header_idx = None
    header_re = re.compile(r'^\s*(?:<tg-emoji[^>]*>.*?</tg-emoji>\s*)?<b>[^<].*?</b>')
    for i, line in enumerate(lines):
        if header_re.search(line):
            header_idx = i
            break

    cleaned = []
    for i, line in enumerate(lines):
        if i != header_idx:
            line = _tg_emoji_open_re.sub('', line)
            line = _tg_emoji_close_re.sub('', line)
        cleaned.append(line)
    return "\n".join(cleaned)


def normalize_html_outgoing_text(text: str) -> str:
    """Нормализация исходящих HTML-текстов: emoji -> custom emoji + анимодзи в заголовках."""
    normalized = normalize_text_emojis(text)
    normalized = add_header_emoji_to_bold_lines(normalized)
    normalized = strip_custom_emoji_outside_first_header(normalized)
    return normalized


def normalize_system_text(text: str) -> str:
    """
    Нормализовать системный текст:
    1) заменить обычные emoji на custom emoji, если есть id в паке,
    2) добавить анимодзи в начало каждой строки-заголовка.
    """
    if not text:
        return text

    return normalize_html_outgoing_text(text)


def is_image_generation_request(text: str) -> bool:
    """Определить, просит ли пользователь сгенерировать изображение."""
    if not text:
        return False
    t = re.sub(r"\s+", " ", text.lower().strip())
    image_markers = [
        "сгенерируй картин",
        "сделай картин",
        "сделай изображ",
        "создай фото",
        "сгенерируй изображ",
        "картинк",
        "картинку",
        "кратинк",      # частая опечатка: "кратинка"
        "кратинку",
        "нарисуй",
        "изобрази",
        "покажи",
        "создай изображ",
        "создай картин",
        "сделай изображ",
        "сделай фото",
        "фото ",
        "сделай мем",
        "сгенерируй мем",
        "иллюстрац",
        "арт",
        "аватарк",
        "обои",
        "poster",
        "make me an image",
        "make an image",
        "create image",
        "create a picture",
        "make me a picture",
        "draw",
        "image",
        "generate image",
        "image of",
        "logo",
        "стикер",
        "лого",
        "логотип",
        "сделай арт",
        "нарисуй арт",
        "wallpaper",
        "сгенери",
        "сгенерь",
        "генерируй",
        "сделай обои",
        "портрет",
        "нарисовать",
        "рисунок",
        "иконк",
        "баннер",
        "постер",
        "обложк",
        "визуализ",
        "коллаж"
    ]
    return any(marker in t for marker in image_markers)


def is_photo_edit_request(text: str) -> bool:
    """Определить, просит ли пользователь изменить/обработать присланное фото."""
    if not text:
        return False
    t = re.sub(r"\s+", " ", text.lower().strip())

    direct_markers = [
        "измени фото",
        "измени фотку",
        "измени изображение",
        "отредактируй фото",
        "обработай фото",
        "улучши фото",
        "сделай из этого фото",
        "сделай из этой фотки",
        "edit this photo",
        "edit this image",
        "retouch this photo",
        "enhance this photo",
        "change this photo",
        "remove background",
        "убери фон",
    ]
    if any(marker in t for marker in direct_markers):
        return True

    edit_verbs = [
        "измени", "отредакт", "обработ", "улучши", "передел", "преврати",
        "замени", "убери", "добавь", "edit", "retouch", "enhance", "change"
    ]
    photo_refs = [
        "фото", "фотку", "фотография", "изображение", "картинку",
        "picture", "photo", "image", "pic", "this"
    ]
    return any(v in t for v in edit_verbs) and any(p in t for p in photo_refs)


def build_photo_edit_prompt(user_instruction: str, photo_context: str) -> str:
    """
    Построить prompt для режима "изменить фото" через генерацию:
    максимально сохранить объект и сцену, менять только запрошенное.
    """
    instruction = sanitize_user_input(user_instruction, max_length=900)
    context = sanitize_user_input(photo_context, max_length=1200)
    if not instruction:
        instruction = "сделай аккуратную художественную обработку фото"
    if not context:
        context = "source photo with a clear main subject"

    composed = (
        f"SOURCE PHOTO CONTEXT: {context}. "
        f"EDIT REQUEST: {instruction}. "
        "Keep the same main subject identity, pose and framing from the source photo. "
        "Apply only requested edits. Preserve scene coherence and realism unless user asked for stylization. "
        "Do not replace the subject with a different person/animal/object."
    )
    return sanitize_user_input(composed, max_length=1800) or composed


ENHANCE_IMAGE_PROMPT_SYSTEM = (
    "You are an expert image prompt engineer for AI image generators (DALL-E 3, GPT Image, Flux). "
    "The user gives you a description (often in Russian). "
    "Your job: translate it to English and rewrite as a vivid, detailed image generation prompt.\n\n"
    "RULES:\n"
    "- Output ONLY the English prompt, nothing else — no explanations, no quotes\n"
    "- Keep it 40-80 words\n"
    "- Preserve EVERY detail the user asked for\n"
    "- If user says 'мем' (meme): make it funny, exaggerated, cartoon/comic style, expressive face, dramatic lighting, humorous composition\n"
    "- If user says 'логотип' (logo): clean, minimalist, vector style, centered, white background\n"
    "- If user says 'арт/рисунок': digital art, vibrant colors, detailed\n"
    "- If user says 'фото/реалистичное': photorealistic, DSLR, natural lighting\n"
    "- Add style keywords matching the mood (comic style for memes, cinematic for dramatic scenes, etc.)\n"
    "- Add quality keywords: highly detailed, sharp focus, professional\n"
    "- Do NOT add random objects or subjects the user didn't ask for\n"
    "- End with: --no text, letters, words, watermark, logo, blurry, low quality"
)


async def enhance_image_prompt(user_text: str) -> Optional[str]:
    """Перевести и улучшить промпт через быстрый LLM."""
    if not API_BEARER_TOKEN:
        return None
    try:
        payload = {
            "model": "gemini-3-flash",
            "request": {
                "messages": [
                    {"role": "system", "content": ENHANCE_IMAGE_PROMPT_SYSTEM},
                    {"role": "user", "content": user_text}
                ]
            }
        }
        headers = {"Authorization": f"Bearer {API_BEARER_TOKEN}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers, timeout=15) as response:
                if response.status == 200:
                    data = await response.json()
                    result = data.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                    if result and len(result) > 5:
                        return result
    except Exception as e:
        logging.warning(f"Prompt enhancement failed: {e}")
    return None


def build_image_prompt(user_text: str) -> str:
    """
    Быстрый fallback-промпт (если LLM-улучшение недоступно).
    Очищает русский текст от мусора и добавляет минимальные инструкции.
    """
    src = sanitize_user_input(user_text, max_length=1500)
    if not src:
        return ""

    core = src.strip()
    core = re.sub(
        r'(?i)\b(привет|здравствуйте|братка|бро|пожалуйста|плиз|pls|please)\b',
        '',
        core
    )
    core = re.sub(
        r'(?i)\b(дай|сделай|сгенерируй|создай|нарисуй|покажи|выдай)\b',
        '',
        core
    )
    core = re.sub(r'(?i)\b(мне|me)\b', '', core)
    core = re.sub(
        r'(?i)\b(картинку|картинка|изображение|фото|арт|image|picture)\b',
        '',
        core
    )
    core = re.sub(r'\s+', ' ', core).strip(" ,.!?-")
    if not core:
        core = src

    # Добавляем стилевые подсказки на английском
    core_l = core.lower()
    style_hints = []
    if any(w in core_l for w in ("мем", "смешн", "юмор", "прикол", "ржач")):
        style_hints.append("funny meme, comic style, exaggerated expressions, humorous")
    elif any(w in core_l for w in ("лого", "логотип")):
        style_hints.append("clean logo, minimalist, vector, white background")
    elif any(w in core_l for w in ("реалист", "фотореалист")):
        style_hints.append("photorealistic, DSLR photography, natural lighting")
    else:
        style_hints.append("digital art, vibrant colors")

    style_hints.append("highly detailed, sharp focus, professional quality")
    suffix = ", ".join(style_hints)
    return f"{core}, {suffix}. --no text, letters, watermark, logo, blurry"


def prompt_requests_animals(prompt_text: str) -> bool:
    t = (prompt_text or "").lower()
    animal_words = (
        "кот", "кошка", "кошк", "cat", "kitten",
        "собак", "dog", "puppy",
        "птиц", "bird", "лошад", "horse", "медвед", "bear",
        "животн", "animal"
    )
    return any(w in t for w in animal_words)


def _image_retry_prompt_no_animals(prompt_text: str, attempt: int) -> str:
    base = sanitize_user_input(prompt_text, max_length=1200)
    suffix = (
        " STRICT: no animals, no pets, no cats, no dogs, no birds. "
        "If any animal appears, regenerate the scene without animals."
    )
    if attempt >= 2:
        suffix += " Focus only on requested objects and environment."
    return f"{base}. {suffix}"


async def image_contains_animal(image_bytes: bytes) -> Optional[bool]:
    """
    Проверить через vision API, есть ли на изображении животное.
    Возвращает True/False или None, если проверка недоступна.
    """
    if not API_BEARER_TOKEN or not image_bytes:
        return None
    try:
        img_b64 = base64.b64encode(image_bytes).decode("utf-8")
        messages = [
            {
                "role": "system",
                "content": (
                    "You are an image validator. Return strictly JSON only: "
                    '{"contains_animal": true|false}'
                )
            },
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    {"type": "text", "text": "Does this image contain any animal (cat, dog, bird, etc.)?"}
                ]
            }
        ]
        payload = {"model": "gemini-3-flash", "request": {"messages": messages}}
        headers = {"Authorization": f"Bearer {API_BEARER_TOKEN}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, json=payload, headers=headers, timeout=40) as response:
                if response.status != 200:
                    return None
                data = await response.json()
                raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                try:
                    parsed = json.loads(raw)
                    val = parsed.get("contains_animal")
                    if isinstance(val, bool):
                        return val
                except Exception:
                    raw_l = str(raw).lower()
                    if '"contains_animal": true' in raw_l:
                        return True
                    if '"contains_animal": false' in raw_l:
                        return False
        return None
    except Exception as e:
        logging.warning(f"Image validation skipped: {e}")
        return None


async def generate_image_with_guard(user_id: int, prompt: str, model: str, max_attempts: int = 2) -> tuple:
    """
    Генерация картинки с fallback на другие модели при ошибках.
    Промпт улучшается через LLM один раз перед генерацией.
    """
    # Улучшаем промпт через LLM один раз
    enhanced = await enhance_image_prompt(prompt)
    if enhanced:
        logging.info(f"Enhanced image prompt: {enhanced[:200]}")
    else:
        logging.warning(f"Prompt enhancement failed/skipped, using fallback for: {prompt[:100]}")

    last_error = "Не получилось нарисовать. Попробуй описать по-другому."

    # План моделей: сначала текущая, затем альтернативы.
    # pollinations-flux-free всегда последний — бесплатный fallback
    enabled_models = set(get_enabled_models())
    preferred_order = ["gpt-image-1", "dall-e-3", "flux", "flux-2-dev", "grok-2-image", "phoenix-1.0", "lucid-origin", "pollinations-flux-free"]

    model_plan = [model]
    for m in preferred_order:
        if m in IMAGE_MODELS and m in enabled_models and m not in model_plan:
            model_plan.append(m)
    # Гарантируем pollinations как последний fallback
    if "pollinations-flux-free" not in model_plan:
        model_plan.append("pollinations-flux-free")

    logging.info(f"Image generation plan: {model_plan}")

    for model_idx, current_model in enumerate(model_plan):
        for attempt in range(1, max_attempts + 1):
            logging.info(f"Image attempt {attempt}/{max_attempts} with model={current_model}")
            success, result = await generate_image(user_id, prompt, current_model, enhanced_prompt=enhanced)
            if not success:
                last_error = result
                logging.warning(f"Image failed: model={current_model}, attempt={attempt}, error={str(result)[:200]}")
                lower_err = str(result).lower()
                if any(x in lower_err for x in ("429", "rate limit", "bad argument", "credits", "spending limit")):
                    break
                continue

            return True, result

        if model_idx < len(model_plan) - 1:
            logging.warning(f"All attempts failed for {current_model}, switching to {model_plan[model_idx + 1]}")

    logging.error(f"All image models failed. Last error: {last_error}")
    return False, last_error


def pick_image_model(user_id: int) -> Optional[str]:
    """Выбрать модель генерации изображения: сначала пользовательскую, затем дефолт из доступных."""
    enabled_models = set(get_enabled_models())
    enabled_image_models = [m for m in AVAILABLE_MODELS if m in IMAGE_MODELS and m in enabled_models]
    if not enabled_image_models:
        return None

    user_data = load_user_data(user_id)
    preferred_model = user_data.get("model")
    if preferred_model in enabled_image_models:
        return preferred_model

    # По умолчанию предпочитаем GPT image-модели.
    for candidate in ("gpt-image-1", "dall-e-3", "flux", "flux-2-dev", "grok-2-image", "phoenix-1.0", "lucid-origin", "pollinations-flux-free"):
        if candidate in enabled_image_models:
            return candidate
    return enabled_image_models[0]


def pick_image_model_for_prompt(user_id: int, prompt_text: str) -> Optional[str]:
    """
    Выбрать image-модель с учетом типа сцены.
    Для предметных сцен (без животных) предпочитаем модели, лучше держащие промпт.
    """
    enabled_models = set(get_enabled_models())
    enabled_image_models = [m for m in AVAILABLE_MODELS if m in IMAGE_MODELS and m in enabled_models]
    if not enabled_image_models:
        return None

    t = (prompt_text or "").lower()
    has_animal = any(x in t for x in ("кот", "кошк", "cat", "kitten", "собак", "dog", "puppy", "животн", "animal"))
    object_scene = any(x in t for x in ("обои", "рулон", "валик", "ролик", "краск", "стол", "предмет", "product"))

    if object_scene and not has_animal:
        for candidate in ("gpt-image-1", "dall-e-3", "lucid-origin", "phoenix-1.0", "flux-2-dev", "flux"):
            if candidate in enabled_image_models:
                return candidate

    return pick_image_model(user_id)


def validate_json_structure(value, depth: int = 0, max_depth: int = 8, max_items: int = 200):
    """Ограничить глубину/размер JSON, чтобы избежать перегрузки."""
    if depth > max_depth:
        raise ValueError("JSON слишком глубоко вложен")

    if isinstance(value, dict):
        if len(value) > max_items:
            raise ValueError("JSON содержит слишком много ключей")
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError("Ключи JSON должны быть строками")
            validate_json_structure(item, depth + 1, max_depth, max_items)
    elif isinstance(value, list):
        if len(value) > max_items:
            raise ValueError("JSON содержит слишком большой список")
        for item in value:
            validate_json_structure(item, depth + 1, max_depth, max_items)


async def send_system_message(chat_id: int, text: str, reply_markup=None, parse_mode: str = "HTML"):
    """Отправить системное сообщение с GIF/анимацией в caption, если задана."""
    # НЕ нормализуем здесь — monkey-patched send_message/send_animation сделают это сами
    gif_pool = []
    env_gif_urls = os.getenv("SYSTEM_GIF_URLS", "").strip()
    if env_gif_urls:
        gif_pool.extend([u.strip() for u in env_gif_urls.split(",") if u.strip()])
    if SYSTEM_GIF_URL:
        gif_pool.append(SYSTEM_GIF_URL)

    # Берем пул из config, если задан
    try:
        config = load_config()
        cfg_urls = config.get("system_gif_urls")
        if isinstance(cfg_urls, list):
            gif_pool = [str(u).strip() for u in cfg_urls if str(u).strip()]
    except Exception:
        pass

    if not gif_pool:
        gif_pool = DEFAULT_SYSTEM_GIF_URLS.copy()

    if gif_pool:
        chosen_gif = random.choice(gif_pool)
        try:
            await bot.send_animation(
                chat_id=chat_id,
                animation=chosen_gif,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
            return
        except Exception as e:
            logging.warning(f"Не удалось отправить system GIF: {e}")

    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
        parse_mode=parse_mode
    )


async def send_section_media_message(chat_id: int, text: str, reply_markup, section: str, parse_mode: str = "HTML") -> bool:
    """Отправить сообщение с локальным медиа (gif/photo) для конкретного экрана."""
    # НЕ нормализуем здесь — monkey-patched send_animation/send_photo сделают это сами
    media_path = SECTION_MEDIA_PATHS.get(section)
    if not media_path or not os.path.exists(media_path):
        return False
    try:
        media_file = FSInputFile(media_path)
        if media_path.lower().endswith(".gif"):
            await bot.send_animation(
                chat_id=chat_id,
                animation=media_file,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await bot.send_photo(
                chat_id=chat_id,
                photo=media_file,
                caption=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        return True
    except Exception as e:
        logging.warning(f"Не удалось отправить media для секции {section}: {e}")
        return False

# ==================== МОДЕЛИ ====================
AVAILABLE_MODELS = [
    # deepseek
    "deepseek-v3",
    "deepseek-r1",

    # gemini
    "gemini-3-pro",
    "gemini-3-pro-preview",
    "gemini-3-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",

    # claude
    "claude-opus-4-6",
    "claude-opus-4-5",
    "claude-sonnet-4-5",
    "claude-haiku-4-5",

    # chatgpt / gpt
    "gpt-5.2-chat",
    "gpt-5.1-chat",
    "gpt-5.1-2025-11-13",
    "gpt-5.1",
    "gpt-5-search-api-2025-10-14",
    "gpt-5-search",
    "gpt-5-nano-2025-08-07",
    "gpt-5-nano",
    "gpt-5-mini-2025-08-07",
    "gpt-5-mini",
    "gpt-5-chat",
    "gpt-5-2025-08-07",
    "gpt-5",
    "gpt-4.1-nano-2025-04-14",
    "gpt-4.1-nano",
    "gpt-4.1-mini-2025-04-14",
    "gpt-4.1-mini",
    "gpt-4.1-2025-04-14",
    "gpt-4.1",
    "o4-mini-2025-04-16",
    "o4-mini",
    "o3-mini-2025-01-31",
    "o3-mini",
    "o3-2025-04-16",
    "o3",
    "o1-2024-12-17",
    "o1",
    "chatgpt-4o",
    "gpt-4o-search-preview-2025-03-11",
    "gpt-4o-search-preview",
    "gpt-4o-mini-search-preview-2025-03-11",
    "gpt-4o-mini-search-preview",
    "gpt-4o-mini-2024-07-18",
    "gpt-4o-mini",
    "gpt-4o-2024-11-20",
    "gpt-4o-2024-08-06",
    "gpt-4o-2024-05-13",
    "gpt-4o",
    "gpt-4-turbo-preview",
    "gpt-4-turbo-2024-04-09",
    "gpt-4-turbo",
    "gpt-4-1106-preview",
    "gpt-4-0613",
    "gpt-4-0125-preview",
    "gpt-4",
    "gpt-3.5-turbo-16k",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125",
    "gpt-3.5-turbo",

    # остальные
    "sonar-deep-research",
    "sonar-reasoning-pro",
    "sonar-reasoning",
    "sonar-pro",
    "sonar",
    "d-gemma-3-4b-it",
    "d-llama-3.3-70b",
    "d-llama-4-maverick",
    "rev-perplexity",
    "searchgpt",
    "grok-2-vision",
    "grok-3",
    "gpt-oss-120b",
    "gpt-oss-20b",
    "mistral-small-3.1",
    "zai-glm-4.6",
    "llama3.1-8b",
    "llama-3.3-70b",
    "qwen-3-32b",
    "gpt-image-1",
    "dall-e-3",
    "p-flux",
    "grok-2-image",
    "flux-2-dev",
    "phoenix-1.0",
    "lucid-origin",
    "flux",
    "pollinations-flux-free"
]

IMAGE_MODELS = {
    "gpt-image-1", "dall-e-3",
    "p-flux", "grok-2-image", "flux-2-dev", "phoenix-1.0", "lucid-origin", "flux",
    "pollinations-flux-free"
}
MODELS_PER_PAGE = 8

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
# Хранилище бизнес-подключений (инициализируется в main)
business_connections = {}


def _is_html_parse_mode(parse_mode) -> bool:
    return isinstance(parse_mode, str) and parse_mode.upper() == "HTML"


_original_bot_send_message = Bot.send_message
_original_message_answer = Message.answer
_original_bot_send_photo = Bot.send_photo
_original_bot_send_video = Bot.send_video
_original_bot_send_animation = Bot.send_animation


_tg_emoji_open_re = re.compile(r'<tg-emoji[^>]*>')
_tg_emoji_close_re = re.compile(r'</tg-emoji>')


def _strip_tg_emoji(text: str) -> str:
    """Убрать все <tg-emoji> теги из текста (fallback если бот не может отправить custom emoji).
    Обрабатывает вложенные теги, удаляя открывающие и закрывающие по отдельности."""
    if not text:
        return text
    text = _tg_emoji_open_re.sub('', text)
    text = _tg_emoji_close_re.sub('', text)
    return text


async def _bot_send_message_with_custom_emoji(self, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    original_text = kwargs.get("text") if "text" in kwargs else (args[1] if len(args) >= 2 else None)
    if _is_html_parse_mode(parse_mode):
        if "text" in kwargs and isinstance(kwargs["text"], str):
            kwargs["text"] = normalize_html_outgoing_text(kwargs["text"])
        elif len(args) >= 2 and isinstance(args[1], str):
            args = list(args)
            args[1] = normalize_html_outgoing_text(args[1])
            args = tuple(args)
    try:
        return await _original_bot_send_message(self, *args, **kwargs)
    except Exception:
        # Fallback: убираем custom emoji и пробуем снова
        if _is_html_parse_mode(parse_mode):
            if "text" in kwargs and isinstance(kwargs["text"], str):
                kwargs["text"] = _strip_tg_emoji(kwargs["text"])
            elif len(args) >= 2 and isinstance(args[1], str):
                args = list(args)
                args[1] = _strip_tg_emoji(args[1])
                args = tuple(args)
            return await _original_bot_send_message(self, *args, **kwargs)
        raise


async def _message_answer_with_custom_emoji(self, text, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    original_text = text
    if _is_html_parse_mode(parse_mode) and isinstance(text, str):
        text = normalize_html_outgoing_text(text)
    try:
        return await _original_message_answer(self, text, *args, **kwargs)
    except Exception:
        if _is_html_parse_mode(parse_mode) and isinstance(text, str):
            text = _strip_tg_emoji(text)
            return await _original_message_answer(self, text, *args, **kwargs)
        raise


async def _bot_send_photo_with_custom_emoji(self, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    if _is_html_parse_mode(parse_mode) and isinstance(kwargs.get("caption"), str):
        kwargs["caption"] = normalize_html_outgoing_text(kwargs["caption"])
    try:
        return await _original_bot_send_photo(self, *args, **kwargs)
    except Exception:
        if _is_html_parse_mode(parse_mode) and isinstance(kwargs.get("caption"), str):
            kwargs["caption"] = _strip_tg_emoji(kwargs["caption"])
            return await _original_bot_send_photo(self, *args, **kwargs)
        raise


async def _bot_send_video_with_custom_emoji(self, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    if _is_html_parse_mode(parse_mode) and isinstance(kwargs.get("caption"), str):
        kwargs["caption"] = normalize_html_outgoing_text(kwargs["caption"])
    try:
        return await _original_bot_send_video(self, *args, **kwargs)
    except Exception:
        if _is_html_parse_mode(parse_mode) and isinstance(kwargs.get("caption"), str):
            kwargs["caption"] = _strip_tg_emoji(kwargs["caption"])
            return await _original_bot_send_video(self, *args, **kwargs)
        raise


async def _bot_send_animation_with_custom_emoji(self, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    if _is_html_parse_mode(parse_mode) and isinstance(kwargs.get("caption"), str):
        kwargs["caption"] = normalize_html_outgoing_text(kwargs["caption"])
    try:
        return await _original_bot_send_animation(self, *args, **kwargs)
    except Exception:
        if _is_html_parse_mode(parse_mode) and isinstance(kwargs.get("caption"), str):
            kwargs["caption"] = _strip_tg_emoji(kwargs["caption"])
            return await _original_bot_send_animation(self, *args, **kwargs)
        raise


Bot.send_message = _bot_send_message_with_custom_emoji
Message.answer = _message_answer_with_custom_emoji
Bot.send_photo = _bot_send_photo_with_custom_emoji
Bot.send_video = _bot_send_video_with_custom_emoji
Bot.send_animation = _bot_send_animation_with_custom_emoji


# ==================== FSM STATES ====================
class AdminStates(StatesGroup):
    waiting_for_price = State()
    waiting_for_price_stars = State()  # НОВОЕ
    waiting_for_price_crypto = State()  # НОВОЕ
    waiting_for_user_id_grant = State()
    waiting_for_grant_days = State()
    waiting_for_user_id_revoke = State()
    waiting_for_broadcast = State()
    waiting_for_broadcast_confirm = State()
    waiting_for_start_media = State()
    waiting_for_channel = State()
    waiting_for_blacklist_add = State()
    waiting_for_blacklist_remove = State()
    waiting_for_channel_media = State()


class UserStates(StatesGroup):
    waiting_for_thinking = State()


# ==================== СООБЩЕНИЯ (A/B тестирование) ====================
MESSAGES_FILE = os.path.join(DATA_DIR, "messages.json")

DEFAULT_MESSAGES = {
    "paywall": (
        "{proof}"
        "<b>Бесплатные запросы закончились</b>\n\n"
        "Тебе понравилось? С PRO будет ещё лучше:\n\n"
        "✅ Вопросы без ограничений — хоть 100 в день\n"
        "✅ Картинки, фото, голосовые — всё включено\n"
        "✅ Лучшие модели AI — GPT-5, Claude, Gemini\n\n"
        "<b>{price_stars} ⭐ за месяц</b> — это 3₽ в день.\n"
        "<i>Дешевле, чем один запрос к фрилансеру.</i>"
    ),
    "paywall_proof": "Уже {active_subs} чел. пользуются каждый день\n\n",
    "welcome_intro": (
        "{greeting} Напиши вопрос — получишь ответ за секунды."
    ),
    "welcome_free_requests": "<b>Бесплатно:</b> {remaining}",
    "welcome_example_intro": "<b>Попробуй:</b>",
    "welcome_subscribe_cta": "<b>Без ограничений — PRO.</b>",
    "channel_subscribe": (
        "<b>Подпишись на канал — и бот заработает</b>\n\n"
        "Там советы, лайфхаки и примеры запросов.\n\n"
        "{proof}"
        "👇 Нажми и подпишись:"
    ),
    "channel_proof": "Нас уже {subs_count}.\n\n",
    "subscription_outcome": "Помощник, который экономит тебе часы каждую неделю.",
    "subscription_proof": "{active_subs} чел. уже пользуются каждый день\n\n",
    "subscription_benefits": (
        "✅ <b>Любые вопросы</b> — работа, дом, дети, здоровье, деньги\n"
        "✅ <b>Картинки</b> — открытки, аватарки, идеи, логотипы\n"
        "✅ <b>Экономия времени</b> — письма, планы, тексты за секунды\n"
        "✅ <b>Фото + голос</b> — отправь что угодно, бот разберётся\n"
        "✅ <b>24/7</b> — всегда на связи, без очередей"
    ),
    "subscription_price_anchor": "<s>5 USD</s>  <b>{price_stars} ⭐</b> или <b>{price_usd} USD</b> за 30 дней",
    "trial_reminder_1_left": (
        "<b>Остался последний бесплатный запрос!</b>\n\n"
        "Используй его — и реши что-то важное:\n"
        "• <i>«Составь меню на неделю»</i>\n"
        "• <i>«Напиши деловое письмо»</i>\n\n"
        "Дальше — PRO. <b>Всего {price} ⭐ за месяц.</b>"
    ),
    "trial_reminder_24h": (
        "Ты вчера попробовал помощника — понравилось?\n\n"
        "Вот что спрашивают другие:\n"
        "• «Составь список покупок на неделю»\n"
        "• «Напиши поздравление свекрови»\n"
        "• «Объясни ребёнку, почему небо голубое»\n\n"
        "С PRO — спрашивай сколько хочешь.\n"
        "<b>{price} ⭐ за месяц. Это 3₽ в день.</b>"
    ),
    "image_generation_progress": (
        "🎨 Рисую...\n"
        "<i>10–30 секунд</i>"
    ),
    "image_success_free_cta": (
        "\n\n<i>С PRO — до {img_daily} картинок в день, без ограничений</i>"
    ),
    "soft_paywall": (
        "<b>Осталось бесплатно: {remaining}</b>\n"
        "PRO — без ограничений."
    ),
    "referral_invite": (
        "<b>Получи +{bonus} бесплатных запроса!</b>\n\n"
        "Отправь эту ссылку другу:\n<code>{link}</code>\n\n"
        "Друг запустит бота — тебе сразу начислится {bonus} запроса."
    ),
    "referral_bonus_received": (
        "🎉 Друг зашёл! Тебе <b>+{bonus} бесплатных запроса</b>."
    ),
    "daily_free_available": (
        "У тебя <b>1 бесплатный запрос сегодня</b>.\n\n"
        "<i>С PRO — без ограничений каждый день.</i>"
    ),
    "trial_reminder_1h": (
        "Ну как тебе?\n\n"
        "Это только начало — с PRO ты сможешь:\n"
        "• Спрашивать без ограничений\n"
        "• Рисовать картинки и открытки\n"
        "• Отправлять фото и голосовые\n\n"
        "🔥 <b>Для тебя — первый месяц {discount_price} ⭐ вместо {full_price}</b>"
    ),
    "trial_reminder_3d": (
        "Привет! Ты давно не заходил.\n\n"
        "А люди каждый день спрашивают:\n"
        "• «Что приготовить из курицы и риса?»\n"
        "• «Напиши отзыв на товар»\n"
        "• «Посоветуй сериал на вечер»\n\n"
        "У тебя <b>1 бесплатный запрос</b> — попробуй.\n\n"
        "<i>PRO — {price} ⭐/мес. Это 3₽ в день.</i>"
    ),
    "first_buy_discount": (
        "🔥 <b>Только для тебя — первый месяц со скидкой!</b>\n\n"
        "<b>{discount_price} ⭐</b> вместо <s>{full_price}</s> за 30 дней.\n\n"
        "<i>Предложение одноразовое.</i>"
    ),
    "inactive_7d": (
        "Привет! Давно не виделись 👋\n\n"
        "Пока тебя не было, я научился отвечать ещё лучше.\n\n"
        "Попробуй спросить:\n"
        "• «{example1}»\n"
        "• «{example2}»\n\n"
        "У тебя <b>1 бесплатный запрос</b> — проверь!"
    ),
    "inactive_14d": (
        "Соскучился! 😊\n\n"
        "Люди каждый день экономят часы с помощником:\n"
        "меню, письма, подарки, советы — всё за секунды.\n\n"
        "Напиши что-нибудь — у тебя <b>1 бесплатный запрос</b> сегодня."
    ),
    "pro_welcome": (
        "🎉 <b>Добро пожаловать в PRO, {name}!</b>\n\n"
        "Подписка активна до <b>{end_date}</b>\n\n"
        "Теперь тебе доступно всё без ограничений:\n"
        "✅ Любые вопросы — сколько угодно\n"
        "✅ Картинки, фото, голосовые\n"
        "✅ Лучшие модели AI\n\n"
        "<b>Попробуй прямо сейчас:</b>"
    ),
    "expired_1h": (
        "<b>Подписка PRO истекла</b>\n\n"
        "Продли сейчас — и продолжай пользоваться без ограничений.\n\n"
        "<i>Без PRO — только 1 запрос в день.</i>"
    ),
    "expired_24h": (
        "<b>Без PRO уже сутки</b>\n\n"
        "За время подписки ты сделал <b>{request_count} запросов</b>.\n"
        "Без PRO — только 1 в день.\n\n"
        "Верни себе безлимит — <b>{price} ⭐ за месяц</b>."
    ),
    "expired_3d": (
        "Привет! Уже 3 дня без PRO.\n\n"
        "Другие пользователи каждый день спрашивают:\n"
        "• «Составь план на неделю»\n"
        "• «Напиши текст для поста»\n"
        "• «Нарисуй открытку»\n\n"
        "Вернись — <b>{price} ⭐ за месяц</b>. Это 3₽ в день."
    ),
}


def load_messages() -> dict:
    """Загрузить сообщения из файла (для A/B тестов)"""
    data = _safe_read_json(MESSAGES_FILE)
    if data and isinstance(data, dict):
        return data
    return {}


def get_message(key: str, default: str = None, **kwargs) -> str:
    """Получить сообщение по ключу. Переопределения из messages.json > DEFAULT_MESSAGES."""
    custom = load_messages()
    text = custom.get(key) or default or DEFAULT_MESSAGES.get(key, "")
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text


# ==================== РАБОТА С КОНФИГОМ ====================
def load_config():
    """Загрузить конфигурацию"""
    data = _safe_read_json(CONFIG_FILE)
    if data and isinstance(data, dict):
        return data
    return {
        "subscription_price": 99,
        "subscription_price_usd": 1,
        "system_gif_urls": [],
        "button_emoji_pack": DEFAULT_BUTTON_EMOJI_PACK.copy()
    }


def save_config(config):
    """Сохранить конфигурацию"""
    _safe_write_json(CONFIG_FILE, config)


def get_subscription_price():
    """Получить цену подписки в звездах"""
    config = load_config()
    return config.get("subscription_price", 99)


def get_subscription_price_usd():
    """Получить цену подписки в USD"""
    config = load_config()
    return config.get("subscription_price_usd", 1)


def set_subscription_price(price: int):
    """Установить цену подписки в звездах"""
    config = load_config()
    config["subscription_price"] = price
    save_config(config)


def set_subscription_price_usd(price: float):
    """Установить цену подписки в USD"""
    config = load_config()
    config["subscription_price_usd"] = price
    save_config(config)


# Модели по умолчанию
DEFAULT_ENABLED_MODELS = [
    "gpt-5.2-chat",
    "claude-opus-4-6",
    "claude-sonnet-4-5",
    "deepseek-v3",
    "deepseek-r1",
    "gemini-3-flash",
    "gpt-image-1"
]


def get_enabled_models() -> list:
    """Получить список включенных моделей"""
    config = load_config()
    raw_models = config.get("enabled_models", DEFAULT_ENABLED_MODELS)
    if not isinstance(raw_models, list):
        raw_models = DEFAULT_ENABLED_MODELS.copy()

    # Оставляем только модели, которые реально есть в AVAILABLE_MODELS.
    enabled = [m for m in raw_models if m in AVAILABLE_MODELS]
    if not enabled:
        enabled = [m for m in DEFAULT_ENABLED_MODELS if m in AVAILABLE_MODELS]

    # Авто-страховка: если нет ни одной image-модели, добавляем первую доступную.
    has_image_model = any(m in IMAGE_MODELS for m in enabled)
    if not has_image_model:
        for candidate in ("gpt-image-1", "dall-e-3", "flux", "flux-2-dev", "grok-2-image", "phoenix-1.0", "lucid-origin", "pollinations-flux-free"):
            if candidate in AVAILABLE_MODELS and candidate not in enabled:
                enabled.append(candidate)
                break

    # Если токен onlysq не задан, гарантируем бесплатную модель в списке.
    if not API_BEARER_TOKEN and "pollinations-flux-free" in AVAILABLE_MODELS and "pollinations-flux-free" not in enabled:
        enabled.append("pollinations-flux-free")

    return enabled


def set_enabled_models(models: list):
    """Установить список включенных моделей"""
    config = load_config()
    config["enabled_models"] = models
    save_config(config)


def toggle_model(model: str) -> bool:
    """Переключить модель (вкл/выкл). Возвращает новое состояние"""
    enabled = get_enabled_models()
    if model in enabled:
        enabled.remove(model)
        result = False
    else:
        enabled.append(model)
        result = True
    set_enabled_models(enabled)
    return result


def is_model_enabled(model: str) -> bool:
    """Проверить, включена ли модель"""
    return model in get_enabled_models()


# ==================== РАБОТА СО СТАТИСТИКОЙ ====================
def _default_stats():
    return {
        "total_users": 0,
        "total_starts": 0,
        "total_messages": 0,
        "total_payments": 0,
        "total_revenue": 0,
        "total_revenue_usd": 0.0,
        "paywall_shown": 0,
        "subscription_clicked": 0,
        "total_referrals": 0,
    }


def load_stats():
    """Загрузить статистику (с восстановлением из бэкапа при повреждении)"""
    data = _safe_read_json(STATS_FILE)
    if data and isinstance(data, dict):
        # Добавляем отсутствующие ключи, не затирая существующие
        defaults = _default_stats()
        for k, v in defaults.items():
            data.setdefault(k, v)
        return data
    return _default_stats()


def save_stats(stats):
    """Сохранить статистику (атомарно)"""
    _safe_write_json(STATS_FILE, stats)


def increment_stat(key: str, value=1):
    """Увеличить значение статистики (value: int или float)"""
    stats = load_stats()
    stats[key] = stats.get(key, 0) + value
    save_stats(stats)

# ==================== РАБОТА С БИЗНЕС-ПОДКЛЮЧЕНИЯМИ ====================
def load_business_connections():
    """Загрузить бизнес-подключения из файла"""
    data = _safe_read_json(BUSINESS_CONNECTIONS_FILE)
    if data and isinstance(data, dict):
        logging.info(f"✅ Загружено {len(data)} бизнес-подключений")
        return data
    return {}


def save_business_connections(connections):
    """Сохранить бизнес-подключения в файл"""
    try:
        _safe_write_json(BUSINESS_CONNECTIONS_FILE, connections)
        logging.info(f"💾 Сохранено {len(connections)} бизнес-подключений")
    except Exception as e:
        logging.error(f"❌ Ошибка сохранения подключений: {e}")


def add_business_connection(connection_id: str, user_id: int):
    """Добавить бизнес-подключение"""
    business_connections[connection_id] = user_id
    save_business_connections(business_connections)

# ==================== РАБОТА С ПОЛЬЗОВАТЕЛЯМИ ====================
def get_user_dir(user_id: int) -> str:
    """Получить директорию пользователя"""
    user_dir = os.path.join(USERS_DIR, str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def get_user_data_path(user_id: int) -> str:
    """Получить путь к данным пользователя"""
    return os.path.join(get_user_dir(user_id), "user_data.json")


def get_user_history_path(user_id: int) -> str:
    """Получить путь к истории чата пользователя"""
    return os.path.join(get_user_dir(user_id), "chat_history.json")


def load_user_data(user_id: int) -> dict:
    """Загрузить данные пользователя (с восстановлением из бэкапа)"""
    path = get_user_data_path(user_id)
    data = _safe_read_json(path)
    if data and isinstance(data, dict):
        return data
    return {
        "user_id": user_id,
        "model": DEFAULT_MODEL,
        "subscription_end": None,
        "created_at": datetime.now().isoformat(),
        "username": None,
        "full_name": None
    }


def save_user_data(user_id: int, data: dict):
    """Сохранить данные пользователя (атомарно)"""
    path = get_user_data_path(user_id)
    _safe_write_json(path, data)


def load_chat_history(user_id: int) -> list:
    """Загрузить историю чата"""
    path = get_user_history_path(user_id)
    data = _safe_read_json(path)
    if data and isinstance(data, list):
        return data
    return []


def save_chat_history(user_id: int, history: list):
    """Сохранить историю чата"""
    path = get_user_history_path(user_id)
    _safe_write_json(path, history)


def add_message_to_history(user_id: int, role: str, content: str):
    """Добавить сообщение в историю"""
    history = load_chat_history(user_id)
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    # Ограничиваем историю последними 50 сообщениями
    if len(history) > 50:
        history = history[-50:]
    save_chat_history(user_id, history)


def clear_chat_history(user_id: int):
    """Очистить историю чата"""
    save_chat_history(user_id, [])


def get_history_for_api(user_id: int, limit: int = 20) -> list:
    """Получить историю для API"""
    history = load_chat_history(user_id)
    messages = history[-limit:]
    return [{"role": msg["role"], "content": msg["content"]} for msg in messages]

# ==================== РАБОТА С ИСТОРИЕЙ БИЗНЕС-ЧАТОВ ====================
def get_business_chat_history_path(business_connection_id: str, client_chat_id: int) -> str:
    """Получить путь к истории бизнес-чата"""
    business_dir = os.path.join(DATA_DIR, "business_chats")
    os.makedirs(business_dir, exist_ok=True)
    return os.path.join(business_dir, f"{business_connection_id}_{client_chat_id}.json")


def load_business_chat_history(business_connection_id: str, client_chat_id: int) -> list:
    """Загрузить историю бизнес-чата"""
    path = get_business_chat_history_path(business_connection_id, client_chat_id)
    data = _safe_read_json(path)
    if data and isinstance(data, list):
        return data
    return []


def save_business_chat_history(business_connection_id: str, client_chat_id: int, history: list):
    """Сохранить историю бизнес-чата"""
    path = get_business_chat_history_path(business_connection_id, client_chat_id)
    _safe_write_json(path, history)


def add_message_to_business_history(business_connection_id: str, client_chat_id: int, role: str, content: str):
    """Добавить сообщение в историю бизнес-чата"""
    history = load_business_chat_history(business_connection_id, client_chat_id)
    history.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat()
    })
    # Ограничиваем историю последними 50 сообщениями
    if len(history) > 50:
        history = history[-50:]
    save_business_chat_history(business_connection_id, client_chat_id, history)


def get_business_history_for_api(business_connection_id: str, client_chat_id: int, limit: int = 20) -> list:
    """Получить историю бизнес-чата для API"""
    history = load_business_chat_history(business_connection_id, client_chat_id)
    messages = history[-limit:]
    return [{"role": msg["role"], "content": msg["content"]} for msg in messages]


def clear_business_chat_history(business_connection_id: str, client_chat_id: int):
    """Очистить историю бизнес-чата"""
    save_business_chat_history(business_connection_id, client_chat_id, [])

# ==================== ПОДПИСКА ====================
def has_active_subscription(user_id: int) -> bool:
    """Проверить активность подписки"""
    # Админы имеют бесплатный доступ
    if user_id in ADMIN_IDS:
        return True

    user_data = load_user_data(user_id)
    sub_end = user_data.get("subscription_end")

    if not sub_end:
        return False

    try:
        end_date = datetime.fromisoformat(sub_end)
        return datetime.now() < end_date
    except:
        return False


def get_subscription_end(user_id: int) -> Optional[datetime]:
    """Получить дату окончания подписки"""
    user_data = load_user_data(user_id)
    sub_end = user_data.get("subscription_end")

    if not sub_end:
        return None

    try:
        return datetime.fromisoformat(sub_end)
    except:
        return None


def get_free_trial_used(user_id: int) -> int:
    """Сколько бесплатных текстовых запросов уже использовано"""
    user_data = load_user_data(user_id)
    return int(user_data.get("free_trial_used") or 0)


def get_free_image_trial_used(user_id: int) -> int:
    """Сколько бесплатных запросов на картинки уже использовано"""
    user_data = load_user_data(user_id)
    return int(user_data.get("image_trial_used") or 0)


def get_free_trial_remaining(user_id: int) -> tuple:
    """Вернуть (текст_осталось, картинок_осталось) — триал + бонусы"""
    text_rem = max(0, FREE_TRIAL_LIMIT - get_free_trial_used(user_id))
    img_rem = max(0, FREE_IMAGE_TRIAL_LIMIT - get_free_image_trial_used(user_id))
    return text_rem, img_rem


def get_total_free_remaining(user_id: int) -> int:
    """Всего бесплатных запросов (триал + реф.бонус + ежедневный)"""
    text_rem, img_rem = get_free_trial_remaining(user_id)
    ref_bonus = get_referral_bonus_remaining(user_id)
    daily_free = get_daily_free_remaining(user_id)
    return text_rem + img_rem + ref_bonus + daily_free


def consume_free_trial(user_id: int, is_image: bool = False):
    """Списать 1 бесплатный запрос. Приоритет: триал → реф.бонус → ежедневный."""
    user_data = load_user_data(user_id)
    used = get_free_trial_used(user_id)
    if used == 0 and not user_data.get("first_use_time"):
        user_data["first_use_time"] = datetime.now().isoformat()
    if is_image:
        if get_free_image_trial_used(user_id) < FREE_IMAGE_TRIAL_LIMIT:
            user_data["image_trial_used"] = user_data.get("image_trial_used", 0) + 1
            save_user_data(user_id, user_data)
            return
    else:
        if used < FREE_TRIAL_LIMIT:
            user_data["free_trial_used"] = used + 1
            save_user_data(user_id, user_data)
            return
    save_user_data(user_id, user_data)
    # Триал закончился — списываем из реферальных бонусов
    if get_referral_bonus_remaining(user_id) > 0:
        consume_referral_bonus(user_id)
        return
    # Списываем из ежедневного бесплатного
    if get_daily_free_remaining(user_id) > 0:
        consume_daily_free(user_id)
        return


def can_make_request(user_id: int, is_image: bool = False) -> bool:
    """Может ли пользователь сделать запрос (подписка, триал, реф.бонус или ежедневный)"""
    if user_id in ADMIN_IDS:
        return True
    if has_active_subscription(user_id):
        return True
    if is_image:
        if get_free_image_trial_used(user_id) < FREE_IMAGE_TRIAL_LIMIT:
            return True
    else:
        if get_free_trial_used(user_id) < FREE_TRIAL_LIMIT:
            return True
    # Реферальные бонусы
    if get_referral_bonus_remaining(user_id) > 0:
        return True
    # Ежедневный бесплатный запрос
    if get_daily_free_remaining(user_id) > 0:
        return True
    return False


def can_make_any_request(user_id: int) -> bool:
    """Есть ли хоть какие-то бесплатные запросы (текст, картинки, реф.бонус, ежедневный)"""
    if user_id in ADMIN_IDS:
        return True
    if has_active_subscription(user_id):
        return True
    text_rem, img_rem = get_free_trial_remaining(user_id)
    if text_rem > 0 or img_rem > 0:
        return True
    if get_referral_bonus_remaining(user_id) > 0:
        return True
    if get_daily_free_remaining(user_id) > 0:
        return True
    return False


def get_free_trial_paywall_text(user_id: int = None) -> str:
    """Текст пейвола при исчерпании бесплатного триала."""
    active_subs = len(get_users_with_active_subscription())
    proof = get_message("paywall_proof", active_subs=active_subs) if active_subs > 0 else ""

    if user_id:
        eff_stars, eff_usd = get_effective_price(user_id)
        first = is_first_purchase(user_id)
        text_rem, img_rem = get_free_trial_remaining(user_id)

        # Скидочная строка
        if first:
            full_price = get_subscription_price()
            discount_line = f"\n🔥 <b>Первый месяц — {eff_stars} звёзд вместо <s>{full_price}</s>!</b>"
        else:
            discount_line = ""

        if text_rem > 0 and img_rem == 0:
            return (
                f"{proof}"
                f"<b>Бесплатные картинки закончились</b>\n\n"
                f"У тебя ещё {text_rem} текстовых запросов.\n"
                f"Для безлимитных картинок — оформи PRO.\n\n"
                f"<b>Всего {eff_stars} Stars / {eff_usd} USD за 30 дней</b>"
                f"{discount_line}"
            )
        if img_rem > 0 and text_rem == 0:
            return (
                f"{proof}"
                f"<b>Бесплатные текстовые запросы закончились</b>\n\n"
                f"У тебя ещё {img_rem} картинок.\n"
                f"Для безлимита — оформи PRO.\n\n"
                f"<b>Всего {eff_stars} Stars / {eff_usd} USD за 30 дней</b>"
                f"{discount_line}"
            )
    else:
        eff_stars = get_subscription_price()
        eff_usd = get_subscription_price_usd()
        discount_line = ""

    paywall_text = get_message(
        "paywall",
        proof=proof,
        price_stars=eff_stars,
        price_usd=eff_usd,
        img_daily=IMAGE_DAILY_LIMIT_PRO
    )
    if user_id and is_first_purchase(user_id):
        full_price = get_subscription_price()
        paywall_text += f"\n\n🔥 <b>Первый месяц — {eff_stars} звёзд вместо <s>{full_price}</s>!</b>"
    return paywall_text


def try_consume_image_generation_limit(user_id: int) -> tuple:
    """
    Проверить и списать 1 генерацию изображения из лимита.
    Лимит действует для платной подписки: в день и в месяц.
    """
    if user_id in ADMIN_IDS:
        return True, ""

    if not has_active_subscription(user_id):
        if get_free_image_trial_used(user_id) < FREE_IMAGE_TRIAL_LIMIT:
            return True, ""
        return False, get_free_trial_paywall_text(user_id)

    user_data = load_user_data(user_id)
    today_key = datetime.now().strftime("%Y-%m-%d")
    month_key = datetime.now().strftime("%Y-%m")

    daily_date = str(user_data.get("image_daily_date") or "")
    daily_count = int(user_data.get("image_daily_count") or 0)
    monthly_period = str(user_data.get("image_monthly_period") or "")
    monthly_count = int(user_data.get("image_monthly_count") or 0)

    if daily_date != today_key:
        daily_date = today_key
        daily_count = 0
    if monthly_period != month_key:
        monthly_period = month_key
        monthly_count = 0

    if daily_count >= IMAGE_DAILY_LIMIT_PRO:
        return False, f"Дневной лимит генераций ({IMAGE_DAILY_LIMIT_PRO}) исчерпан. Приходи завтра!"
    if monthly_count >= IMAGE_MONTHLY_LIMIT_PRO:
        return False, f"Месячный лимит генераций ({IMAGE_MONTHLY_LIMIT_PRO}) исчерпан. Лимит обновится в начале месяца."

    user_data["image_daily_date"] = daily_date
    user_data["image_daily_count"] = daily_count + 1
    user_data["image_monthly_period"] = monthly_period
    user_data["image_monthly_count"] = monthly_count + 1
    save_user_data(user_id, user_data)
    return True, ""


def grant_subscription(user_id: int, days: int = 30):
    """Выдать подписку пользователю"""
    user_data = load_user_data(user_id)

    # Если есть активная подписка, продлеваем
    current_end = get_subscription_end(user_id)
    if current_end and current_end > datetime.now():
        new_end = current_end + timedelta(days=days)
    else:
        new_end = datetime.now() + timedelta(days=days)

    user_data["subscription_end"] = new_end.isoformat()
    save_user_data(user_id, user_data)

    # Обновляем статистику
    increment_stat("active_subscriptions")


def revoke_subscription(user_id: int):
    """Отобрать подписку у пользователя"""
    user_data = load_user_data(user_id)
    user_data["subscription_end"] = None
    save_user_data(user_id, user_data)


# ==================== РЕФЕРАЛЬНАЯ СИСТЕМА ====================
def get_referral_link(user_id: int) -> str:
    """Получить реферальную ссылку пользователя"""
    bot_info_username = os.getenv("BOT_USERNAME", "")
    if bot_info_username:
        return f"https://t.me/{bot_info_username}?start=ref_{user_id}"
    return f"ref_{user_id}"


def process_referral(new_user_id: int, referrer_id: int):
    """Обработать реферал — начислить бонусы приглашающему."""
    if new_user_id == referrer_id:
        return False
    # Проверяем, что новый пользователь действительно новый
    new_user_data = load_user_data(new_user_id)
    if new_user_data.get("referred_by"):
        return False  # уже был приглашён
    # Сохраняем реферала у нового пользователя
    new_user_data["referred_by"] = referrer_id
    save_user_data(new_user_id, new_user_data)
    # Начисляем бонус приглашающему
    referrer_data = load_user_data(referrer_id)
    referrer_data["referral_bonus"] = referrer_data.get("referral_bonus", 0) + REFERRAL_BONUS_REQUESTS
    referrer_data["referral_count"] = referrer_data.get("referral_count", 0) + 1
    save_user_data(referrer_id, referrer_data)
    increment_stat("total_referrals")
    return True


def get_referral_bonus_remaining(user_id: int) -> int:
    """Сколько реферальных бонусных запросов осталось"""
    user_data = load_user_data(user_id)
    bonus = user_data.get("referral_bonus", 0)
    used = user_data.get("referral_bonus_used", 0)
    return max(0, bonus - used)


def consume_referral_bonus(user_id: int):
    """Списать 1 реферальный бонусный запрос"""
    user_data = load_user_data(user_id)
    user_data["referral_bonus_used"] = user_data.get("referral_bonus_used", 0) + 1
    save_user_data(user_id, user_data)


# ==================== ЕЖЕДНЕВНЫЙ БЕСПЛАТНЫЙ ЗАПРОС ====================
def get_daily_free_remaining(user_id: int) -> int:
    """Сколько ежедневных бесплатных запросов осталось"""
    user_data = load_user_data(user_id)
    today_key = datetime.now().strftime("%Y-%m-%d")
    daily_date = user_data.get("daily_free_date", "")
    if daily_date != today_key:
        return DAILY_FREE_REQUESTS
    return max(0, DAILY_FREE_REQUESTS - user_data.get("daily_free_used", 0))


def consume_daily_free(user_id: int):
    """Списать 1 ежедневный бесплатный запрос"""
    user_data = load_user_data(user_id)
    today_key = datetime.now().strftime("%Y-%m-%d")
    if user_data.get("daily_free_date") != today_key:
        user_data["daily_free_date"] = today_key
        user_data["daily_free_used"] = 0
    user_data["daily_free_used"] = user_data.get("daily_free_used", 0) + 1
    save_user_data(user_id, user_data)


# ==================== СКИДКА НА ПЕРВУЮ ПОКУПКУ ====================
def is_first_purchase(user_id: int) -> bool:
    """Проверить, является ли это первой покупкой пользователя"""
    user_data = load_user_data(user_id)
    return not user_data.get("has_ever_paid", False)


def get_effective_price(user_id: int) -> tuple:
    """Получить актуальную цену для пользователя (звёзды, USD)"""
    if is_first_purchase(user_id):
        return FIRST_BUY_DISCOUNT_STARS, FIRST_BUY_DISCOUNT_USD
    return get_subscription_price(), get_subscription_price_usd()


def mark_as_paid(user_id: int):
    """Пометить, что пользователь хотя бы раз оплатил"""
    user_data = load_user_data(user_id)
    user_data["has_ever_paid"] = True
    save_user_data(user_id, user_data)


def get_all_users() -> list:
    """Получить список всех пользователей"""
    users = []
    if os.path.exists(USERS_DIR):
        for user_dir in os.listdir(USERS_DIR):
            try:
                user_id = int(user_dir)
                user_data = load_user_data(user_id)
                user_data["user_id"] = user_id  # ensure present for iteration
                users.append(user_data)
            except:
                continue
    return users


def get_users_with_active_subscription() -> list:
    """Получить пользователей с активной подпиской"""
    users = get_all_users()
    return [u for u in users if has_active_subscription(u["user_id"])]


def get_user_by_username(username: str) -> Optional[dict]:
    """Найти пользователя по username"""
    username = username.lstrip('@').lower()
    users = get_all_users()
    for user in users:
        if user.get("username") and user["username"].lower() == username:
            return user
    return None

async def create_crypto_invoice(user_id: int, amount: float) -> Optional[dict]:
    """Создать инвойс в CryptoBot"""
    try:
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(
                f"{CRYPTO_BOT_API}/createInvoice",
                headers={"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN},
                json={
                    "amount": amount,
                    "currency_type": "fiat",
                    "fiat": "USD",
                    "description": f"Подписка AI Chat Bot (30 дней)",
                    "payload": f"subscription_{user_id}",
                    "expires_in": 3600
                }
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok"):
                        result = data["result"]
                        return {
                            "invoice_id": result["invoice_id"],
                            "bot_invoice_url": result["bot_invoice_url"]
                        }
                logging.error(f"CryptoBot error status={response.status}")
                return None
    except Exception as e:
        logging.error(f"Ошибка создания CryptoBot инвойса: {e}")
        return None


async def check_crypto_invoice(invoice_id: str) -> Optional[dict]:
    """Проверить статус инвойса CryptoBot"""
    try:
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.get(
                f"{CRYPTO_BOT_API}/getInvoices",
                headers={"Crypto-Pay-API-Token": CRYPTO_BOT_TOKEN},
                params={"invoice_ids": invoice_id}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("ok") and data.get("result", {}).get("items"):
                        invoice = data["result"]["items"][0]
                        return {
                            "status": invoice.get("status"),
                            "payload": invoice.get("payload")
                        }
                return None
    except Exception as e:
        logging.error(f"Ошибка проверки CryptoBot инвойса: {e}")
        return None

def get_thinking_preference(user_id: int) -> Optional[str]:
    """Получить настройки мышления пользователя"""
    user_data = load_user_data(user_id)
    return user_data.get("thinking_preference")


def set_thinking_preference(user_id: int, preference: Optional[str]):
    """Установить настройки мышления пользователю"""
    user_data = load_user_data(user_id)
    user_data["thinking_preference"] = preference
    save_user_data(user_id, user_data)


def get_response_style_preset(user_id: int) -> str:
    """Получить preset стиля ответа (serious|neutral|funny|friend)."""
    user_data = load_user_data(user_id)
    preset = user_data.get("style_preset", "neutral")
    return preset if preset in STYLE_PRESET_PROMPTS else "neutral"


def set_response_style_preset(user_id: int, preset: str):
    """Установить preset стиля ответа."""
    if preset not in STYLE_PRESET_PROMPTS:
        return
    user_data = load_user_data(user_id)
    user_data["style_preset"] = preset
    save_user_data(user_id, user_data)


def get_start_example(user_id: int, rotate: bool = False) -> str:
    """Вернуть пример для стартового экрана; при rotate меняет пример."""
    user_data = load_user_data(user_id)
    last_idx = user_data.get("start_example_idx", -1)

    if not START_EXAMPLES:
        return "«Сделай смешную картинку про работу и кофе»"

    if rotate or last_idx not in range(len(START_EXAMPLES)):
        idx = random.randrange(len(START_EXAMPLES))
        if len(START_EXAMPLES) > 1:
            while idx == last_idx:
                idx = random.randrange(len(START_EXAMPLES))
        user_data["start_example_idx"] = idx
        save_user_data(user_id, user_data)
        return START_EXAMPLES[idx]

    return START_EXAMPLES[last_idx]


def get_button_emoji_pack() -> dict:
    """
    Получить маппинг button_key -> custom emoji id.
    Источники: config.button_emoji_pack или env BUTTON_EMOJI_PACK_JSON.
    """
    config = load_config()
    from_config = config.get("button_emoji_pack")
    if isinstance(from_config, dict):
        return {str(k): str(v) for k, v in from_config.items() if str(v).strip()}

    raw = os.getenv("BUTTON_EMOJI_PACK_JSON", "").strip()
    if not raw:
        return {}

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {str(k): str(v) for k, v in parsed.items() if str(v).strip()}
    except Exception:
        pass
    return DEFAULT_BUTTON_EMOJI_PACK.copy()


def make_inline_button(
    text: str,
    callback_data: Optional[str] = None,
    url: Optional[str] = None,
    button_key: Optional[str] = None,
    style: Optional[str] = None
) -> InlineKeyboardButton:
    """Создать кнопку с поддержкой цвета и custom emoji (если API/библиотека поддерживают)."""
    kwargs = {"text": text}
    if callback_data is not None:
        kwargs["callback_data"] = callback_data
    if url is not None:
        kwargs["url"] = url

    emoji_pack = get_button_emoji_pack()
    custom_emoji_id = emoji_pack.get(button_key) if button_key else None
    if custom_emoji_id:
        kwargs["icon_custom_emoji_id"] = custom_emoji_id
    if style in {"primary", "success", "danger"}:
        kwargs["style"] = style

    try:
        return InlineKeyboardButton(**kwargs)
    except TypeError:
        # Совместимость со старыми версиями aiogram/Bot API
        kwargs.pop("style", None)
        try:
            return InlineKeyboardButton(**kwargs)
        except TypeError:
            kwargs.pop("icon_custom_emoji_id", None)
            return InlineKeyboardButton(**kwargs)


def get_start_media() -> Optional[dict]:
    """Получить медиа для /start"""
    config = load_config()
    return config.get("start_media")


def set_start_media(media_type: Optional[str], file_id: Optional[str]):
    """Установить медиа для /start"""
    config = load_config()
    if media_type and file_id:
        config["start_media"] = {"type": media_type, "file_id": file_id}
    else:
        config["start_media"] = None
    save_config(config)


def get_channel_media() -> Optional[dict]:
    """Получить медиа для сообщения о подписке на канал"""
    config = load_config()
    return config.get("channel_media")


def set_channel_media(media_type: Optional[str], file_id: Optional[str]):
    """Установить медиа для сообщения о подписке на канал"""
    config = load_config()
    if media_type and file_id:
        config["channel_media"] = {"type": media_type, "file_id": file_id}
    else:
        config["channel_media"] = None
    save_config(config)


# ==================== ЧЕРНЫЙ СПИСОК ====================
def load_blacklist() -> list:
    """Загрузить черный список"""
    data = _safe_read_json(BLACKLIST_FILE)
    if data and isinstance(data, list):
        return data
    return []


def save_blacklist(blacklist: list):
    """Сохранить черный список"""
    _safe_write_json(BLACKLIST_FILE, blacklist)


def is_blacklisted(user_id: int) -> bool:
    """Проверить, в черном ли списке пользователь"""
    return user_id in load_blacklist()


def add_to_blacklist(user_id: int):
    """Добавить пользователя в черный список"""
    blacklist = load_blacklist()
    if user_id not in blacklist:
        blacklist.append(user_id)
        save_blacklist(blacklist)


def remove_from_blacklist(user_id: int):
    """Удалить пользователя из черного списка"""
    blacklist = load_blacklist()
    if user_id in blacklist:
        blacklist.remove(user_id)
        save_blacklist(blacklist)

def load_pending_invoices() -> dict:
    """Загрузить ожидающие инвойсы"""
    data = _safe_read_json(PENDING_INVOICES_FILE)
    if data and isinstance(data, dict):
        return data
    return {}


def save_pending_invoices(invoices: dict):
    """Сохранить ожидающие инвойсы"""
    _safe_write_json(PENDING_INVOICES_FILE, invoices)


def add_pending_invoice(invoice_id: str, user_id: int):
    """Добавить ожидающий инвойс"""
    invoices = load_pending_invoices()
    invoices[invoice_id] = {
        "user_id": user_id,
        "created_at": datetime.now().isoformat()
    }
    save_pending_invoices(invoices)


def remove_pending_invoice(invoice_id: str):
    """Удалить ожидающий инвойс"""
    invoices = load_pending_invoices()
    if invoice_id in invoices:
        del invoices[invoice_id]
        save_pending_invoices(invoices)

# ==================== ОБЯЗАТЕЛЬНЫЕ КАНАЛЫ ====================
def get_required_channels() -> list:
    """Получить список обязательных каналов"""
    config = load_config()
    return config.get("required_channels", [])


def add_required_channel(channel_id: str, channel_name: str, channel_link: str):
    """Добавить обязательный канал"""
    config = load_config()
    channels = config.get("required_channels", [])

    # Проверяем, нет ли уже такого канала
    for ch in channels:
        if ch["id"] == channel_id:
            return False

    channels.append({
        "id": channel_id,
        "name": channel_name,
        "link": channel_link
    })
    config["required_channels"] = channels
    save_config(config)
    return True


def remove_required_channel(channel_id: str):
    """Удалить обязательный канал"""
    config = load_config()
    channels = config.get("required_channels", [])
    channels = [ch for ch in channels if ch["id"] != channel_id]
    config["required_channels"] = channels
    save_config(config)


async def check_channel_subscription(user_id: int) -> bool:
    """Проверить подписку на все обязательные каналы"""
    channels = get_required_channels()

    if not channels:
        return True

    for channel in channels:
        try:
            member = await bot.get_chat_member(channel["id"], user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception as e:
            logging.warning(f"Ошибка проверки подписки на канал {channel['id']}: {e}")
            # Если не можем проверить - пропускаем
            continue

    return True


# ==================== НАПОМИНАНИЯ О ПОДПИСКЕ ====================
def get_last_reminder(user_id: int) -> Optional[dict]:
    """Получить информацию о последнем напоминании"""
    user_data = load_user_data(user_id)
    return user_data.get("last_reminder")


def set_last_reminder(user_id: int, reminder_type: str):
    """Установить время последнего напоминания"""
    user_data = load_user_data(user_id)
    # Храним каждый тип напоминания отдельно
    reminders_sent = user_data.get("reminders_sent", {})
    reminders_sent[reminder_type] = datetime.now().isoformat()
    user_data["reminders_sent"] = reminders_sent
    # Обратная совместимость
    user_data["last_reminder"] = {
        "type": reminder_type,
        "time": datetime.now().isoformat()
    }
    save_user_data(user_id, user_data)


def should_send_reminder(user_id: int, reminder_type: str) -> bool:
    """Проверить, нужно ли отправлять напоминание (каждый тип — один раз)"""
    user_data = load_user_data(user_id)
    reminders_sent = user_data.get("reminders_sent", {})

    if reminder_type in reminders_sent:
        return False  # Уже отправлялось

    # Обратная совместимость со старым форматом
    last_reminder = user_data.get("last_reminder")
    if last_reminder and last_reminder.get("type") == reminder_type:
        return False

    return True


# ==================== КЛАВИАТУРЫ ====================
def get_main_keyboard(user_id: int = None):
    """Главная клавиатура"""
    has_sub = has_active_subscription(user_id) if user_id else False
    buttons = [
        [
            make_inline_button("✍️ Написать текст", callback_data="quick_write", button_key="quick_write", style="primary"),
            make_inline_button("📋 Составить план", callback_data="quick_plan", button_key="quick_plan", style="primary"),
        ],
        [
            make_inline_button("💡 Подсказка/совет", callback_data="quick_advice", button_key="quick_advice", style="primary"),
            make_inline_button("🎨 Картинка", callback_data="generate_image_prompt", button_key="image", style="primary"),
        ],
        [
            make_inline_button("Настройки", callback_data="settings", button_key="info", style="primary")
        ],
    ]
    if not has_sub:
        if user_id and is_first_purchase(user_id):
            buttons.append([
                make_inline_button(f"🔥 PRO за {FIRST_BUY_DISCOUNT_STARS} ⭐ (скидка!)", callback_data="subscription", button_key="subscription", style="success")
            ])
        else:
            buttons.append([
                make_inline_button("Подписка PRO", callback_data="subscription", button_key="subscription", style="success")
            ])
        buttons.append([
            make_inline_button("Пригласи друга → +3 запроса", callback_data="referral_info", button_key="info", style="primary")
        ])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_models_keyboard(page: int, user_id: int):
    """Клавиатура выбора моделей — текстовые и картиночные разделены"""
    has_sub = has_active_subscription(user_id)

    enabled_models = get_enabled_models()
    available = [m for m in AVAILABLE_MODELS if m in enabled_models]

    # Разделяем на текстовые и картиночные
    text_models = [m for m in available if m not in IMAGE_MODELS]
    image_models_list = [m for m in available if m in IMAGE_MODELS]

    # Дружественные названия
    MODEL_DISPLAY_NAMES = {
        "gpt-5.2-chat": "GPT-5.2 Chat",
        "gpt-5.1-chat": "GPT-5.1 Chat",
        "gpt-5-chat": "GPT-5 Chat",
        "gpt-5": "GPT-5",
        "gpt-5-mini": "GPT-5 Mini",
        "gpt-5-nano": "GPT-5 Nano",
        "gpt-4.1": "GPT-4.1",
        "gpt-4.1-mini": "GPT-4.1 Mini",
        "gpt-4o": "GPT-4o",
        "gpt-4o-mini": "GPT-4o Mini",
        "claude-opus-4-6": "Claude Opus 4.6",
        "claude-opus-4-5": "Claude Opus 4.5",
        "claude-sonnet-4-5": "Claude Sonnet 4.5",
        "claude-haiku-4-5": "Claude Haiku 4.5",
        "deepseek-v3": "DeepSeek V3",
        "deepseek-r1": "DeepSeek R1 (Reasoning)",
        "gemini-3-pro": "Gemini 3 Pro",
        "gemini-3-flash": "Gemini 3 Flash",
        "gemini-2.5-pro": "Gemini 2.5 Pro",
        "gemini-2.5-flash": "Gemini 2.5 Flash",
        "grok-3": "Grok 3",
        "flux": "Flux",
        "flux-2-dev": "Flux 2 Dev",
        "grok-2-image": "Grok 2 Image",
        "phoenix-1.0": "Phoenix 1.0",
        "lucid-origin": "Lucid Origin",
        "pollinations-flux-free": "Flux Free",
        "gpt-image-1": "GPT Image",
        "dall-e-3": "DALL-E 3",
    }

    # Объединяем в один список с разделителями для пагинации
    combined = []
    if text_models:
        combined.append(("header", "✏️ ОТВЕЧАЮТ НА ВОПРОСЫ"))
        for m in text_models:
            combined.append(("model", m))
    if image_models_list:
        combined.append(("header", "🎨 РИСУЮТ КАРТИНКИ"))
        for m in image_models_list:
            combined.append(("model", m))

    start_idx = page * MODELS_PER_PAGE
    end_idx = start_idx + MODELS_PER_PAGE
    page_items = combined[start_idx:end_idx]

    emoji_pack = get_button_emoji_pack()
    buttons = []
    for item_type, item_value in page_items:
        if item_type == "header":
            buttons.append([InlineKeyboardButton(text=f"— {item_value} —", callback_data="noop")])
        else:
            display_name = MODEL_DISPLAY_NAMES.get(item_value, item_value)
            bkey = "image_model" if item_value in IMAGE_MODELS else "text_model"
            callback_data = f"setmodel_{item_value}" if has_sub else f"needsub_{item_value}"
            btn_kwargs = {"text": display_name, "callback_data": callback_data}
            eid = emoji_pack.get(bkey)
            if eid:
                btn_kwargs["icon_custom_emoji_id"] = eid
            try:
                buttons.append([InlineKeyboardButton(**btn_kwargs)])
            except TypeError:
                btn_kwargs.pop("icon_custom_emoji_id", None)
                buttons.append([InlineKeyboardButton(**btn_kwargs)])

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(make_inline_button("Назад", callback_data=f"models_{page - 1}", button_key="nav_back"))
    if end_idx < len(combined):
        nav_buttons.append(make_inline_button("Далее", callback_data=f"models_{page + 1}", button_key="nav_next"))

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([make_inline_button("На главную", callback_data="main_menu", button_key="home")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_subscription_keyboard(user_id: int):
    """Клавиатура подписки"""
    has_sub = has_active_subscription(user_id)

    buttons = []

    if has_sub:
        price_stars = get_subscription_price()
        price_usd = get_subscription_price_usd()
        buttons.append([make_inline_button(
            f"Продлить за {price_stars} звёзд",
            callback_data="extend_stars",
            button_key="extend_stars",
            style="success"
        )])
        buttons.append([make_inline_button(
            f"Продлить за {price_usd} USD (крипто)",
            callback_data="extend_crypto",
            button_key="extend_crypto",
            style="primary"
        )])
    else:
        eff_stars, eff_usd = get_effective_price(user_id)
        first = is_first_purchase(user_id)
        # Недельная подписка — низкий порог входа
        buttons.append([make_inline_button(
            f"Попробовать 7 дней — {WEEKLY_PRICE_STARS} ⭐",
            callback_data="buy_weekly_stars",
            button_key="buy_stars",
            style="success"
        )])
        # Месячная подписка
        stars_label = f"🔥 30 дней — {eff_stars} ⭐ (скидка!)" if first else f"30 дней — {eff_stars} ⭐"
        buttons.append([make_inline_button(
            stars_label,
            callback_data="buy_stars",
            button_key="buy_stars",
            style="success"
        )])
        buttons.append([make_inline_button(
            f"Оплатить {eff_usd} USD (крипто)",
            callback_data="buy_crypto",
            button_key="buy_crypto",
            style="primary"
        )])

    # Кнопка реферальной программы для бесплатных пользователей
    if not has_sub:
        buttons.append([make_inline_button(
            "Пригласи друга → +3 запроса",
            callback_data="referral_info",
            button_key="info",
            style="primary"
        )])

    buttons.append([make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard(callback_data: str = "admin_menu"):
    """Клавиатура отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_inline_button("Отмена", callback_data=callback_data, button_key="cancel", style="danger")]
    ])


def get_admin_keyboard():
    """Клавиатура админ-панели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_inline_button("Аналитика", callback_data="admin_stats", button_key="admin_stats")],
        [make_inline_button("Тарифы", callback_data="admin_price", button_key="admin_price")],
        [make_inline_button("Доступные модели", callback_data="admin_models_0", button_key="admin_models")],
        [make_inline_button("Выдать подписку", callback_data="admin_grant", button_key="admin_grant")],
        [make_inline_button("Забрать подписку", callback_data="admin_revoke", button_key="admin_revoke")],
        [make_inline_button("Массовая рассылка", callback_data="admin_broadcast", button_key="admin_broadcast")],
        [make_inline_button("База пользователей", callback_data="admin_users_0", button_key="admin_users")],
        [make_inline_button("Каналы обяз. подписки", callback_data="admin_channels", button_key="admin_channels")],
        [make_inline_button("Blacklist", callback_data="admin_blacklist", button_key="admin_blacklist")],
        [make_inline_button("Медиа-оформление", callback_data="admin_media", button_key="admin_media")],
        [make_inline_button("Лог запросов", callback_data="admin_reqlog_0", button_key="admin_reqlog")]
    ])


def get_broadcast_confirm_keyboard():
    """Клавиатура подтверждения рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_inline_button("Отправить", callback_data="broadcast_confirm", button_key="confirm", style="success")],
        [make_inline_button("Отмена", callback_data="admin_menu", button_key="cancel")]
    ])


async def safe_edit_or_send(callback: CallbackQuery, text: str, reply_markup=None, parse_mode="HTML"):
    """Безопасно отправить новое системное сообщение (с GIF при наличии)."""
    try:
        try:
            await callback.message.delete()
        except Exception:
            pass
        await send_system_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )
    except Exception as e:
        logging.warning(f"Ошибка safe_edit_or_send: {e}")
        chat_id = callback.message.chat.id
        # Попытка 2: send_system_message
        try:
            await send_system_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        except Exception as e2:
            logging.error(f"safe_edit_or_send fallback failed: {e2}")
            # Попытка 3: простой send_message без GIF
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            except Exception as e3:
                logging.error(f"safe_edit_or_send final fallback failed: {e3}")


# ==================== КОМАНДЫ БОТА ====================
async def set_bot_commands():
    """Установить команды бота"""
    # Команды для всех
    user_commands = [
        BotCommand(command="start", description="🏠 На главную"),
        BotCommand(command="clear", description="🗑️ Начать чат заново")
    ]

    # Команды для админов (включая /admin)
    admin_commands = [
        BotCommand(command="start", description="🏠 На главную"),
        BotCommand(command="clear", description="🗑️ Начать чат заново"),
        BotCommand(command="admin", description="⚙️ Админ-панель")
    ]

    # Устанавливаем базовые команды для всех
    await bot.set_my_commands(user_commands)

    # Устанавливаем команды для админов
    from aiogram.types import BotCommandScopeChat
    for admin_id in ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logging.warning(f"Не удалось установить команды для админа {admin_id}: {e}")


# ==================== TELEGRAM BUSINESS HANDLERS ====================
@dp.business_connection()
async def handle_business_connection(business_connection: BusinessConnection):
    """Обработка подключения бизнес-аккаунта"""
    try:
        user_id = business_connection.user.id
        connection_id = business_connection.id

        add_business_connection(connection_id, user_id)

        logging.info(f"✅ Бизнес-подключение сохранено: {connection_id} -> User {user_id}")
        logging.info(f"📊 Всего подключений: {len(business_connections)}")

    except Exception as e:
        logging.error(f"❌ Ошибка сохранения подключения: {e}")

@dp.business_message(F.text)
async def handle_business_text_message(message: Message):
    """Обработка текстовых сообщений из бизнес-чатов"""
    try:
        business_connection_id = message.business_connection_id

        if not business_connection_id:
            return

            # Если подключение неизвестно, пробуем получить user_id из сообщения
        if business_connection_id not in business_connections:
            logging.warning(f"⚠️ Неизвестное подключение {business_connection_id}, пробую определить владельца...")

            # Для бизнес-сообщений владелец бота = тот, кто подключил бота
            # Используем ID из chat (это будет ID владельца бизнес-аккаунта)
            try:
                # Получаем информацию о чате
                chat_info = await bot.get_chat(message.chat.id)
                if hasattr(chat_info, 'business_connection_id'):
                    bot_owner_id = message.from_user.id if message.from_user else None
                    if bot_owner_id:
                        business_connections[business_connection_id] = bot_owner_id
                        logging.info(f"✅ Автосохранение: {business_connection_id} -> {bot_owner_id}")
                    else:
                        return
                else:
                    return
            except Exception as e:
                logging.error(f"❌ Не удалось определить владельца: {e}")
                return

        # Получаем ID владельца бизнес-аккаунта
        bot_owner_id = business_connections[business_connection_id]

        # Игнорируем сообщения от самого владельца бизнес-аккаунта
        if message.from_user and message.from_user.id == bot_owner_id:
            return

        # Проверки
        if is_blacklisted(bot_owner_id):
            return

        if not can_make_any_request(bot_owner_id):
            increment_stat("paywall_shown")
            await bot.send_message(
                message.chat.id,
                get_free_trial_paywall_text(bot_owner_id),
                business_connection_id=business_connection_id
            )
            return

        await bot.send_chat_action(
            message.chat.id,
            "typing",
            business_connection_id=business_connection_id
        )

        # Обработка сообщения
        user_data = load_user_data(bot_owner_id)
        user_model = user_data.get("model", DEFAULT_MODEL)

        if is_photo_edit_request(message.text or ""):
            await bot.send_message(
                message.chat.id,
                "Для редактирования отправь фото с подписью — что именно нужно изменить.",
                business_connection_id=business_connection_id
            )
            return

        should_generate_image = user_model in IMAGE_MODELS or is_image_generation_request(message.text or "")
        if should_generate_image:
            image_model = user_model if user_model in IMAGE_MODELS else pick_image_model_for_prompt(bot_owner_id, message.text or "")
            if not image_model:
                await bot.send_message(
                    message.chat.id,
                    "Рисование картинок сейчас недоступно. Попробуй позже.",
                    business_connection_id=business_connection_id
                )
                return

            ok_limit, limit_msg = try_consume_image_generation_limit(bot_owner_id)
            if not ok_limit:
                await bot.send_message(
                    message.chat.id,
                    limit_msg,
                    business_connection_id=business_connection_id
                )
                return

            await bot.send_chat_action(
                message.chat.id,
                "upload_photo",
                business_connection_id=business_connection_id
            )
            success, result = await generate_image_with_guard(bot_owner_id, message.text, image_model)

            if success:
                photo = (
                    BufferedInputFile(result, filename="generated_image.jpg")
                    if isinstance(result, (bytes, bytearray))
                    else result
                )
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo,
                    caption=f"🖼 {image_model}",
                    business_connection_id=business_connection_id
                )
                if not has_active_subscription(bot_owner_id):
                    consume_free_trial(bot_owner_id, is_image=True)
                    await maybe_send_trial_reminder_1_left(bot_owner_id, bot_owner_id)
            else:
                await bot.send_message(
                    message.chat.id,
                    result,
                    business_connection_id=business_connection_id
                )
        else:
            ai_response = await get_business_ai_response(
                bot_owner_id,
                business_connection_id,
                message.chat.id,
                message.text
            )
            ai_response = markdown_to_html(ai_response)

            # Отправка длинного сообщения для бизнес-чата
            if len(ai_response) <= MAX_MESSAGE_LENGTH:
                await bot.send_message(
                    message.chat.id,
                    ai_response,
                    business_connection_id=business_connection_id,
                    parse_mode="HTML"
                )
            else:
                parts = [ai_response[i:i + MAX_MESSAGE_LENGTH]
                         for i in range(0, len(ai_response), MAX_MESSAGE_LENGTH)]
                for part in parts:
                    await bot.send_message(
                        message.chat.id,
                        part,
                        business_connection_id=business_connection_id,
                        parse_mode="HTML"
                    )
            if not has_active_subscription(bot_owner_id):
                consume_free_trial(bot_owner_id)
                await maybe_send_trial_reminder_1_left(bot_owner_id, bot_owner_id)

        increment_stat("total_messages")

    except Exception as e:
        logging.error(f"❌ Ошибка бизнес-сообщения: {e}")


@dp.business_message(F.photo)
async def handle_business_photo(message: Message):
    """Обработка фото из бизнес-чатов"""
    try:
        business_connection_id = message.business_connection_id

        if not business_connection_id or business_connection_id not in business_connections:
            return

        bot_owner_id = business_connections[business_connection_id]

        # Игнорируем фото от самого владельца
        if message.from_user and message.from_user.id == bot_owner_id:
            return

        if is_blacklisted(bot_owner_id):
            return

        if not can_make_any_request(bot_owner_id):
            increment_stat("paywall_shown")
            await bot.send_message(
                message.chat.id,
                get_free_trial_paywall_text(bot_owner_id),
                business_connection_id=business_connection_id
            )
            return

        await bot.send_chat_action(
            message.chat.id,
            "typing",
            business_connection_id=business_connection_id
        )

        user_text = message.caption if message.caption else "Что на фото?"

        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        photo_bytes = await bot.download_file(file.file_path)
        photo_base64 = base64.b64encode(photo_bytes.read()).decode('utf-8')

        if is_photo_edit_request(user_text):
            image_model = pick_image_model_for_prompt(bot_owner_id, user_text)
            if not image_model:
                await bot.send_message(
                    message.chat.id,
                    "Рисование картинок сейчас недоступно. Попробуй позже.",
                    business_connection_id=business_connection_id
                )
                return

            ok_limit, limit_msg = try_consume_image_generation_limit(bot_owner_id)
            if not ok_limit:
                await bot.send_message(
                    message.chat.id,
                    limit_msg,
                    business_connection_id=business_connection_id
                )
                return

            await bot.send_chat_action(
                message.chat.id,
                "upload_photo",
                business_connection_id=business_connection_id
            )

            # Берем краткий контекст фото через текущий vision-путь, затем собираем edit-промпт.
            context_prompt = (
                "Кратко опиши фото для дальнейшего редактирования: главный объект, фон, цвета, ракурс, свет. "
                "Формат: 1 строка до 220 символов."
            )
            source_context = await get_business_ai_response(
                bot_owner_id,
                business_connection_id,
                message.chat.id,
                context_prompt,
                photo_base64
            )
            if isinstance(source_context, str) and ("временно недоступен" in source_context or "Попробуй позже" in source_context):
                source_context = ""

            edit_prompt = build_photo_edit_prompt(user_text, source_context or "")
            success, result = await generate_image_with_guard(bot_owner_id, edit_prompt, image_model)
            if success:
                photo_out = (
                    BufferedInputFile(result, filename="edited_image.jpg")
                    if isinstance(result, (bytes, bytearray))
                    else result
                )
                await bot.send_photo(
                    chat_id=message.chat.id,
                    photo=photo_out,
                    caption=f"🖼 {image_model}\n✏️ Редактирование выполнено",
                    business_connection_id=business_connection_id
                )
                if not has_active_subscription(bot_owner_id):
                    consume_free_trial(bot_owner_id, is_image=True)
                    await maybe_send_trial_reminder_1_left(bot_owner_id, bot_owner_id)
            else:
                await bot.send_message(
                    message.chat.id,
                    f"{result}\nПопробуй описать точнее — что изменить (фон, цвет, стиль).",
                    business_connection_id=business_connection_id
                )
            return

        ai_response = await get_business_ai_response(
            bot_owner_id,
            business_connection_id,
            message.chat.id,
            user_text,
            photo_base64
        )
        ai_response = markdown_to_html(ai_response)

        await bot.send_message(
            message.chat.id,
            ai_response,
            business_connection_id=business_connection_id,
            parse_mode="HTML"
        )
        if not has_active_subscription(bot_owner_id):
            consume_free_trial(bot_owner_id)
            await maybe_send_trial_reminder_1_left(bot_owner_id, bot_owner_id)

    except Exception as e:
        logging.error(f"❌ Ошибка бизнес-фото: {e}")


@dp.business_message(F.voice)
async def handle_business_voice(message: Message):
    """Обработка голоса из бизнес-чатов"""
    try:
        business_connection_id = message.business_connection_id

        if not business_connection_id or business_connection_id not in business_connections:
            return

        bot_owner_id = business_connections[business_connection_id]

        # Игнорируем голосовые от самого владельца
        if message.from_user and message.from_user.id == bot_owner_id:
            return

        if is_blacklisted(bot_owner_id):
            return

        if not can_make_any_request(bot_owner_id):
            increment_stat("paywall_shown")
            await bot.send_message(
                message.chat.id,
                get_free_trial_paywall_text(bot_owner_id),
                business_connection_id=business_connection_id
            )
            return

        await bot.send_chat_action(
            message.chat.id,
            "typing",
            business_connection_id=business_connection_id
        )

        voice = message.voice
        file = await bot.get_file(voice.file_id)
        voice_path = f"/tmp/business_voice_{voice.file_id}.ogg"
        await bot.download_file(file.file_path, voice_path)

        transcribed_text = await transcribe_voice(voice_path)

        if not transcribed_text:
            await bot.send_message(
                message.chat.id,
                "Не получилось разобрать голосовое. Попробуй записать ещё раз.",
                business_connection_id=business_connection_id
            )
            return

        ai_response = await get_business_ai_response(
            bot_owner_id,
            business_connection_id,
            message.chat.id,
            transcribed_text
        )
        ai_response = markdown_to_html(ai_response)

        await bot.send_message(
            message.chat.id,
            ai_response,
            business_connection_id=business_connection_id,
            parse_mode="HTML"
        )
        if not has_active_subscription(bot_owner_id):
            consume_free_trial(bot_owner_id)
            await maybe_send_trial_reminder_1_left(bot_owner_id, bot_owner_id)

    except Exception as e:
        logging.error(f"❌ Ошибка бизнес-голос: {e}")


@dp.business_message(F.text.startswith('/clear'))
async def handle_business_clear(message: Message):
    """Очистка истории для клиента в бизнес-чате"""
    try:
        business_connection_id = message.business_connection_id

        if not business_connection_id or business_connection_id not in business_connections:
            return

        # Очищаем историю этого клиента
        clear_business_chat_history(business_connection_id, message.chat.id)

        await bot.send_message(
            message.chat.id,
            "✔️ История чата очищена!",
            business_connection_id=business_connection_id
        )

    except Exception as e:
        logging.error(f"❌ Ошибка очистки бизнес-истории: {e}")

@dp.message(CommandStart())
async def cmd_start(message: Message):
    """Команда /start"""
    user_id = message.from_user.id

    # Проверяем черный список
    if is_blacklisted(user_id):
        return

    user_data = load_user_data(user_id)
    is_new_user = not os.path.exists(get_user_history_path(user_id))

    # Обновляем данные пользователя
    user_data["username"] = message.from_user.username
    user_data["full_name"] = message.from_user.full_name
    save_user_data(user_id, user_data)

    # Статистика: каждый /start
    increment_stat("total_starts")
    # Новый пользователь (первый раз)
    if is_new_user:
        increment_stat("total_users")

    # Обработка реферальной ссылки (ref_XXXXXX)
    if message.text and len(message.text.split()) > 1:
        param = message.text.split()[1]
        if param.startswith("ref_") and is_new_user:
            try:
                referrer_id = int(param.replace("ref_", ""))
                if process_referral(user_id, referrer_id):
                    # Уведомляем пригласившего
                    try:
                        await send_system_message(
                            chat_id=referrer_id,
                            text=get_message("referral_bonus_received", bonus=REFERRAL_BONUS_REQUESTS),
                            parse_mode="HTML"
                        )
                    except Exception:
                        pass
            except (ValueError, TypeError):
                pass

    # Проверяем подписку на каналы (админы не проверяются)
    if user_id not in ADMIN_IDS:
        channels = get_required_channels()
        if channels and not await check_channel_subscription(user_id):
            await send_channel_subscription_message(message.chat.id, user_id)
            return

    await send_start_message(message.chat.id, user_id, rotate_example=True)

    # Онбординг-демо: для новых пользователей автоматически показываем пример ответа
    if is_new_user:
        asyncio.create_task(_send_onboarding_demo(message.chat.id, user_id))


ONBOARDING_DEMOS = [
    {
        "q": "Что приготовить из курицы и картошки?",
        "a": (
            "<b>Картошка с курицей в духовке</b> — 40 минут, минимум возни.\n\n"
            "Курицу нарезать, картошку дольками, добавить лук, чеснок, "
            "соль, перец, ложку масла. Всё в форму, накрыть фольгой — "
            "200°C на 30 мин, потом без фольги ещё 10.\n\n"
            "<i>Хочешь, подберу гарнир или соус?</i>"
        ),
    },
    {
        "q": "Посоветуй сериал на вечер",
        "a": (
            "<b>«Медведь» (The Bear)</b> — если хочешь залипнуть.\n\n"
            "Шеф-повар возвращается в Чикаго и пытается спасти семейную забегаловку. "
            "Драма, юмор, еда — цепляет с первой серии.\n\n"
            "<i>Хочешь ещё варианты — комедию или триллер?</i>"
        ),
    },
    {
        "q": "Что подарить жене на годовщину?",
        "a": (
            "<b>Топ-3 идеи, которые точно зайдут:</b>\n\n"
            "- <b>Впечатление</b> — спа, мастер-класс или ужин вдвоём\n"
            "- <b>Персональное</b> — украшение с гравировкой или фотокнига\n"
            "- <b>Уют</b> — кашемировый плед + свечи + письмо от руки\n\n"
            "<i>Скажи бюджет — подберу конкретный вариант.</i>"
        ),
    },
]


async def _send_onboarding_demo(chat_id: int, user_id: int):
    """Отправить короткий демо-пример через 3 секунды после /start."""
    try:
        await asyncio.sleep(3)
        await bot.send_chat_action(chat_id, "typing")
        await asyncio.sleep(2)

        demo = random.choice(ONBOARDING_DEMOS)

        text = (
            f"<b>Пример — как я отвечаю:</b>\n\n"
            f"<i>Вопрос: {demo['q']}</i>\n\n"
            f"{demo['a']}"
        )

        text_rem, img_rem = get_free_trial_remaining(user_id)
        text += (
            f"\n\n——\n"
            f"Это был пример. У тебя <b>{text_rem} вопроса</b> — напиши свой!"
        )

        await bot.send_message(chat_id=chat_id, text=text, parse_mode="HTML")

    except Exception as e:
        logging.warning(f"Ошибка онбординг-демо для {user_id}: {e}")


async def send_channel_subscription_message(chat_id: int, user_id: int):
    """Отправить сообщение о необходимости подписки на каналы"""
    channels = get_required_channels()

    if not channels:
        return

    stats = load_stats()
    subs_count = stats.get("total_users", 0)
    proof = get_message("channel_proof", subs_count=subs_count) if subs_count > 10 else ""
    text = get_message("channel_subscribe", proof=proof)

    buttons = []
    for ch in channels:
        buttons.append([make_inline_button(
            text=ch['name'],
            url=ch['link'],
            button_key="required_channel",
            style="primary"
        )])

    buttons.append([make_inline_button(
        text="✔️ Продолжить",
        callback_data="check_channels",
        button_key="check_channels",
        style="success"
    )])

    channel_media = get_channel_media()

    if channel_media:
        media_type = channel_media.get("type")
        file_id = channel_media.get("file_id")

        try:
            if media_type == "photo":
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                    parse_mode="HTML"
                )
            elif media_type == "video":
                await bot.send_video(
                    chat_id=chat_id,
                    video=file_id,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                    parse_mode="HTML"
                )
            elif media_type == "animation":
                await bot.send_animation(
                    chat_id=chat_id,
                    animation=file_id,
                    caption=text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                    parse_mode="HTML"
                )
            else:
                await send_system_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                    parse_mode="HTML"
                )
        except Exception as e:
            logging.error(f"Ошибка отправки медиа каналов: {e}")
            await send_system_message(
                chat_id=chat_id,
                text=text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
                parse_mode="HTML"
            )
    else:
        await send_system_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )


async def send_start_message(chat_id: int, user_id: int, rotate_example: bool = False):
    """Отправить приветственное сообщение."""
    has_sub = has_active_subscription(user_id)
    start_example = get_start_example(user_id, rotate=rotate_example)

    header_emoji = text_emoji("wave") or "👋"
    text = f"{header_emoji} <b>Напиши вопрос — получи ответ за секунды.</b>\n\n"
    text += (
        "Меню на неделю, письмо начальнику, подарок жене, "
        "объяснение ребёнку — спроси что угодно.\n\n"
        "А ещё умею:\n"
        "🎨 рисовать картинки и открытки\n"
        "📷 разбирать фото\n"
        "🎤 понимать голосовые\n"
    )

    if not has_sub:
        text_rem, img_rem = get_free_trial_remaining(user_id)
        ref_bonus = get_referral_bonus_remaining(user_id)
        daily_free = get_daily_free_remaining(user_id)
        if text_rem > 0 or img_rem > 0:
            text += (
                f"\n👉 <b>У тебя {text_rem} бесплатных вопроса и {img_rem} картинки — попробуй:</b>\n"
            )
        elif ref_bonus > 0:
            text += f"\n👉 <b>Бонусных запросов: {ref_bonus} — попробуй:</b>\n"
        elif daily_free > 0:
            text += f"\n👉 <b>1 бесплатный запрос сегодня — попробуй:</b>\n"
        else:
            text += "\n<b>Бесплатные запросы закончились.</b> Подключи PRO — от 49 ⭐\n"

        if is_first_purchase(user_id) and (text_rem > 0 or img_rem > 0 or ref_bonus > 0 or daily_free > 0):
            text += f"<blockquote>{start_example}</blockquote>\n"
            text += f"\n🔥 <i>Первый месяц PRO — {FIRST_BUY_DISCOUNT_STARS} ⭐ вместо 99</i>\n"
        elif text_rem > 0 or img_rem > 0 or ref_bonus > 0 or daily_free > 0:
            text += f"<blockquote>{start_example}</blockquote>\n"
    else:
        text += (
            f"\n<b>Просто напиши:</b>\n"
            f"<blockquote>{start_example}</blockquote>\n"
        )

    if await send_section_media_message(
        chat_id=chat_id,
        text=text,
        reply_markup=get_main_keyboard(user_id),
        section="start",
        parse_mode="HTML"
    ):
        return

    kb = get_main_keyboard(user_id)
    start_media = get_start_media()
    if start_media:
        media_type = start_media.get("type")
        file_id = start_media.get("file_id")

        try:
            if media_type == "photo":
                await bot.send_photo(chat_id=chat_id, photo=file_id, caption=text, reply_markup=kb, parse_mode="HTML")
            elif media_type == "video":
                await bot.send_video(chat_id=chat_id, video=file_id, caption=text, reply_markup=kb, parse_mode="HTML")
            elif media_type == "animation":
                await bot.send_animation(chat_id=chat_id, animation=file_id, caption=text, reply_markup=kb, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка отправки медиа: {e}")
            await send_system_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="HTML")
    else:
        await send_system_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="HTML")


@dp.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    """Пустой обработчик для разделителей"""
    await callback.answer()


@dp.callback_query(F.data == "check_channels")
async def callback_check_channels(callback: CallbackQuery):
    """Проверка подписки на каналы"""
    user_id = callback.from_user.id

    if await check_channel_subscription(user_id):
        try:
            await callback.message.delete()
        except:
            pass
        await send_start_message(callback.message.chat.id, user_id, rotate_example=False)
        await callback.answer()
    else:
        await callback.answer("Сначала подпишись на канал выше!", show_alert=True)


@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    """Команда /clear"""
    await send_system_message(
        chat_id=message.chat.id,
        text=(
            "<b>Начать чат заново?</b>\n\n"
            "Бот забудет всё, о чём вы говорили.\nЭто нельзя отменить."
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [make_inline_button(text="Да, начать заново", callback_data="confirm_clear", button_key="confirm_clear", style="danger")],
            [make_inline_button(text="Отмена", callback_data="cancel_clear", button_key="cancel", style="primary")]
        ]),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "confirm_clear")
async def callback_confirm_clear(callback: CallbackQuery):
    """Подтверждение очистки истории"""
    clear_chat_history(callback.from_user.id)
    await safe_edit_or_send(callback, "Готово! Чат очищен — можно начинать заново.")
    await callback.answer()


@dp.callback_query(F.data == "cancel_clear")
async def callback_cancel_clear(callback: CallbackQuery):
    """Отмена очистки истории"""
    await callback.message.delete()
    await callback.answer("Отменено")


@dp.message(Command("admin"))
async def cmd_admin(message: Message):
    """Команда /admin"""
    if message.from_user.id not in ADMIN_IDS:
        return

    await send_system_message(
        chat_id=message.chat.id,
        text="⚙️ <b>Админ-панель</b>",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )


# ==================== CALLBACK HANDLERS ====================
@dp.callback_query(F.data == "main_menu")
async def callback_main_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()

    user_id = callback.from_user.id
    try:
        await callback.message.delete()
    except Exception:
        pass

    await send_start_message(callback.message.chat.id, user_id, rotate_example=False)

    await callback.answer()


@dp.callback_query(F.data.startswith("models_"))
async def callback_models(callback: CallbackQuery):
    """Показать модели"""
    user_id = callback.from_user.id
    chat_id = callback.message.chat.id

    # Проверки
    if is_blacklisted(user_id):
        await callback.answer()
        return

    if user_id not in ADMIN_IDS and get_required_channels():
        if not await check_channel_subscription(user_id):
            await callback.answer("Сначала подпишись на канал!", show_alert=True)
            return

    try:
        parts = callback.data.split("_")
        page = int(parts[1]) if len(parts) > 1 else 0

        user_data = load_user_data(user_id)
        current_model = user_data.get("model", DEFAULT_MODEL)
        model_mode = "картинки" if current_model in IMAGE_MODELS else "текст"

        text = (
            "🤖 <b>Выбор модели</b>\n\n"
            f"Сейчас: <b>{current_model}</b> ({model_mode})\n\n"
            "✏️ <b>Текстовые</b> — отвечают на вопросы, пишут тексты\n"
            "🎨 <b>Для картинок</b> — рисуют по твоему описанию\n\n"
            "Нажми на нужную модель:"
        )

        keyboard = get_models_keyboard(page, user_id)

        try:
            await callback.message.delete()
        except Exception:
            pass

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    except Exception as e:
        logging.exception(f"callback_models: {e}")
        try:
            await bot.send_message(
                chat_id=chat_id,
                text="Не получилось загрузить модели. Попробуй ещё раз.",
                parse_mode="HTML"
            )
        except Exception:
            pass

    await callback.answer()


@dp.callback_query(F.data.startswith("setmodel_"))
async def callback_set_model(callback: CallbackQuery):
    """Установить модель"""
    model = callback.data.replace("setmodel_", "")
    user_id = callback.from_user.id

    if not has_active_subscription(user_id):
        await callback.answer("Эта модель доступна в PRO — от 49 ⭐/мес", show_alert=True)
        return

    user_data = load_user_data(user_id)
    user_data["model"] = model
    save_user_data(user_id, user_data)

    model_mode = "картинки" if model in IMAGE_MODELS else "текст"

    await callback.answer(f"Выбрано: {model}")

    await safe_edit_or_send(
        callback,
        f"<b>Готово!</b>\n\n"
        f"Теперь используется: <b>{model}</b>\n"
        f"Тип: {model_mode}\n\n"
        "Просто напиши что-нибудь — и я отвечу.",
        InlineKeyboardMarkup(inline_keyboard=[
            [make_inline_button("Назад к выбору", callback_data="models_0", button_key="models", style="primary")],
            [make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")]
        ])
    )


@dp.callback_query(F.data.startswith("needsub_"))
async def callback_need_subscription(callback: CallbackQuery):
    """Нужна подписка для смены модели — перенаправляем на страницу подписки"""
    user_id = callback.from_user.id
    user_data = load_user_data(user_id)
    user_data["needsub_clicked"] = True
    save_user_data(user_id, user_data)
    await callback.answer()
    # Перенаправляем на экран подписки
    await callback_subscription(callback)


@dp.callback_query(F.data == "subscription")
async def callback_subscription(callback: CallbackQuery):
    """Информация о подписке"""
    user_id = callback.from_user.id
    increment_stat("subscription_clicked")
    has_sub = has_active_subscription(user_id)
    sub_end = get_subscription_end(user_id)
    price_stars = get_subscription_price()
    price_usd = get_subscription_price_usd()

    if user_id in ADMIN_IDS:
        text = f"{text_emoji('star')} <b>Подписка</b>\n\n"
        text += "Вы администратор бота и имеете неограниченный доступ."
    elif has_sub:
        text = f"{text_emoji('star')} <b>PRO активен</b>\n\n"
        text += f"<b>До:</b> {sub_end.strftime('%d.%m.%Y')}\n"
        time_left = sub_end - datetime.now()
        days = time_left.days
        hours = time_left.seconds // 3600
        text += f"<b>Осталось:</b> {days}д {hours}ч\n\n"
        text += (
            "✅ Вопросы — без ограничений\n"
            f"✅ Картинки — до {IMAGE_DAILY_LIMIT_PRO}/день\n"
            "✅ Все модели AI — GPT-5, Claude, Gemini\n"
            "✅ Фото, голос, любой стиль\n"
        )
    else:
        eff_stars, eff_usd = get_effective_price(user_id)
        full_stars = get_subscription_price()
        active_subs = len(get_users_with_active_subscription())
        proof = get_message("subscription_proof", active_subs=active_subs) if active_subs > 0 else ""
        user_data = load_user_data(user_id)
        text_rem, img_rem = get_free_trial_remaining(user_id)
        text = f"{text_emoji('star')} <b>Подписка PRO</b>\n\n"
        text += f"<b>{get_message('subscription_outcome')}</b>\n\n"
        text += proof
        text += f"<blockquote>{get_message('subscription_benefits')}</blockquote>\n\n"
        text += f"<b>{WEEKLY_PRICE_STARS} ⭐ за 7 дней</b> — попробуй без риска\n"
        if is_first_purchase(user_id):
            text += f"🔥 <b>{eff_stars} ⭐ за 30 дней</b> (вместо <s>{full_stars}</s>) — скидка для новых!\n"
        else:
            text += f"<b>{eff_stars} ⭐ за 30 дней</b> — выгоднее в 2 раза\n"
        if text_rem > 0 or img_rem > 0:
            text += f"\n\n<i>Осталось бесплатно: {text_rem} вопросов, {img_rem} картинок</i>"

    try:
        await callback.message.delete()
    except Exception:
        pass
    if not await send_section_media_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=get_subscription_keyboard(user_id),
        section="subscription",
        parse_mode="HTML"
    ):
        await send_system_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=get_subscription_keyboard(user_id),
            parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(F.data == "referral_info")
async def callback_referral_info(callback: CallbackQuery):
    """Информация о реферальной программе"""
    user_id = callback.from_user.id

    # Получаем username бота для ссылки
    bot_me = await bot.get_me()
    ref_link = f"https://t.me/{bot_me.username}?start=ref_{user_id}"

    user_data = load_user_data(user_id)
    ref_count = user_data.get("referral_count", 0)
    ref_bonus = get_referral_bonus_remaining(user_id)

    text = get_message("referral_invite", bonus=REFERRAL_BONUS_REQUESTS, link=ref_link)
    text += f"\n\n<b>Твоя статистика:</b>\n"
    text += f"Приглашено друзей: {ref_count}\n"
    text += f"Бонусных запросов: {ref_bonus}"

    buttons = [
        [make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")]
    ]

    await safe_edit_or_send(callback, text, InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@dp.callback_query(F.data.startswith("quick_"))
async def callback_quick_action(callback: CallbackQuery):
    """Быстрые действия — подсказки что написать боту."""
    user_id = callback.from_user.id
    if is_blacklisted(user_id):
        await callback.answer()
        return

    action = callback.data.replace("quick_", "")
    prompts = {
        "write": {
            "title": "✍️ <b>Написать текст</b>",
            "desc": "Поздравления, письма, посты, объявления — напиши что нужно.\n\n<b>Примеры:</b>",
            "examples": [
                "«Напиши поздравление маме с юбилеем»",
                "«Составь пост для соцсетей про открытие кафе»",
                "«Напиши деловое письмо начальнику с просьбой об отпуске»",
                "«Текст для объявления о продаже машины»",
            ]
        },
        "plan": {
            "title": "📋 <b>Составить план</b>",
            "desc": "Меню, списки, планы на день/неделю, чеклисты.\n\n<b>Примеры:</b>",
            "examples": [
                "«Составь меню на неделю для семьи из 4 человек»",
                "«План ремонта в ванной — пошагово»",
                "«Список дел на отпуск с ребёнком»",
                "«Чеклист для переезда в новую квартиру»",
            ]
        },
        "advice": {
            "title": "💡 <b>Совет / подсказка</b>",
            "desc": "Спроси что угодно — работа, дом, дети, здоровье.\n\n<b>Примеры:</b>",
            "examples": [
                "«Что подарить мужу на годовщину?»",
                "«Как убрать пятно от кофе с белой рубашки?»",
                "«Ребёнок не хочет делать уроки — что делать?»",
                "«Посоветуй сериал на вечер, чтобы не грустный»",
            ]
        },
    }

    data = prompts.get(action, prompts["write"])
    example = random.choice(data["examples"])

    text = f"{data['title']}\n\n{data['desc']}\n<blockquote>{example}</blockquote>\n\n<i>Просто напиши свой запрос в чат:</i>"

    buttons = [
        [make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")]
    ]

    await safe_edit_or_send(callback, text, InlineKeyboardMarkup(inline_keyboard=buttons))
    await callback.answer()


@dp.callback_query(F.data == "generate_image_prompt")
async def callback_generate_image_prompt(callback: CallbackQuery):
    """Подсказка по генерации картинок"""
    user_id = callback.from_user.id

    if is_blacklisted(user_id):
        await callback.answer()
        return

    examples = [
        "«Открытка с днём рождения — цветы и торт»",
        "«Логотип для кофейни — минималистичный»",
        "«Уютная кухня в скандинавском стиле»",
        "«Семейный портрет в мультяшном стиле»",
        "«Аватарка для соцсетей — стильная и яркая»",
        "«Котик в костюме космонавта»",
    ]
    example = random.choice(examples)

    text = (
        f"{text_emoji('image')} <b>Опиши — я нарисую</b>\n\n"
        "Открытки, логотипы, аватарки, идеи интерьера — что угодно.\n\n"
        "<b>Попробуй написать:</b>\n"
        f"<blockquote>{example}</blockquote>"
    )

    buttons = [
        [make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")]
    ]
    if not has_active_subscription(user_id):
        text_rem, img_rem = get_free_trial_remaining(user_id)
        if text_rem > 0 or img_rem > 0:
            text += f"\n\nБесплатно: <b>{text_rem} вопросов, {img_rem} картинок</b>"
        else:
            buttons.insert(0, [make_inline_button("Подключить PRO", callback_data="subscription", button_key="subscription", style="success")])

    await safe_edit_or_send(
        callback,
        text,
        InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@dp.callback_query(F.data == "buy_weekly_stars")
async def callback_buy_weekly_stars(callback: CallbackQuery):
    """Покупка недельной подписки за звезды"""
    user_id = callback.from_user.id
    increment_stat("subscription_clicked")

    await bot.send_invoice(
        chat_id=user_id,
        title="PRO на 7 дней — попробуй!",
        description="Безлимитные вопросы, картинки, фото, голос. Все модели AI.",
        payload=f"weekly_{user_id}",
        currency="XTR",
        prices=[LabeledPrice(label="PRO (7 дней)", amount=WEEKLY_PRICE_STARS)]
    )
    await callback.answer()


@dp.callback_query(F.data == "buy_stars")
async def callback_buy_stars(callback: CallbackQuery):
    """Покупка подписки за звезды"""
    user_id = callback.from_user.id
    increment_stat("subscription_clicked")
    eff_stars, _ = get_effective_price(user_id)

    first = is_first_purchase(user_id)
    title = "🔥 PRO — первый месяц со скидкой!" if first else "PRO подписка — 30 дней"
    desc = (
        "Безлимитные вопросы, картинки, фото, голос. "
        "GPT-5, Claude, Gemini — все модели включены."
    )

    await bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=desc,
        payload=f"subscription_{user_id}",
        currency="XTR",
        prices=[LabeledPrice(label="PRO (30 дней)", amount=eff_stars)]
    )
    await callback.answer()


@dp.callback_query(F.data == "buy_crypto")
async def callback_buy_crypto(callback: CallbackQuery):
    """Покупка подписки через CryptoBot"""
    user_id = callback.from_user.id
    increment_stat("subscription_clicked")
    _, price_usd = get_effective_price(user_id)

    await safe_edit_or_send(callback, "<b>Создаю ссылку для оплаты...</b>", parse_mode="HTML")

    invoice_data = await create_crypto_invoice(user_id, price_usd)

    if invoice_data:
        add_pending_invoice(invoice_data["invoice_id"], user_id)

        await safe_edit_or_send(
            callback,
            (
                "<b>Оплата через CryptoBot</b>\n\n"
                f"Сумма: <b>{price_usd} USD</b>\n"
                "Ссылка действительна 1 час.\n\n"
                "Нажми кнопку ниже — после оплаты подписка активируется автоматически."
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [make_inline_button("Оплатить", url=invoice_data["bot_invoice_url"], button_key="pay_crypto", style="success")],
                [make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")]
            ]),
            parse_mode="HTML"
        )
    else:
        await safe_edit_or_send(
            callback,
            "Не получилось создать ссылку. Попробуй позже или оплати звёздами Telegram.",
            reply_markup=get_main_keyboard(user_id)
        )

    await callback.answer()


@dp.callback_query(F.data == "extend_stars")
async def callback_extend_stars(callback: CallbackQuery):
    """Продление подписки за звезды"""
    user_id = callback.from_user.id
    price = get_subscription_price()

    await bot.send_invoice(
        chat_id=user_id,
        title="Продление PRO — 30 дней",
        description="Продление подписки: безлимитные запросы, все модели, генерация картинок.",
        payload=f"extend_{user_id}",
        currency="XTR",
        prices=[LabeledPrice(label="Продление PRO (30 дней)", amount=price)]
    )
    await callback.answer()


@dp.callback_query(F.data == "extend_crypto")
async def callback_extend_crypto(callback: CallbackQuery):
    """Продление подписки через CryptoBot"""
    user_id = callback.from_user.id
    price_usd = get_subscription_price_usd()

    await safe_edit_or_send(callback, "<b>Создаю ссылку для оплаты...</b>", parse_mode="HTML")

    invoice_data = await create_crypto_invoice(user_id, price_usd)

    if invoice_data:
        add_pending_invoice(invoice_data["invoice_id"], user_id)

        await safe_edit_or_send(
            callback,
            (
                "<b>Продление через CryptoBot</b>\n\n"
                f"Сумма: <b>{price_usd} USD</b>\n"
                "Ссылка действительна 1 час.\n\n"
                "Нажми кнопку ниже — подписка продлится автоматически."
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [make_inline_button("Оплатить", url=invoice_data["bot_invoice_url"], button_key="pay_crypto", style="success")],
                [make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")]
            ]),
            parse_mode="HTML"
        )
    else:
        await safe_edit_or_send(
            callback,
            "Не получилось создать ссылку. Попробуй позже или оплати звёздами Telegram.",
            reply_markup=get_main_keyboard(user_id)
        )

    await callback.answer()


async def send_pro_welcome(chat_id: int, user_id: int):
    """Отправить wow-сообщение после оплаты PRO."""
    try:
        sub_end = get_subscription_end(user_id)
        end_date = sub_end.strftime('%d.%m.%Y') if sub_end else "—"
        user_data = load_user_data(user_id)
        name = user_data.get("first_name") or "друг"

        text = get_message("pro_welcome", name=name, end_date=end_date)

        buttons = [
            [InlineKeyboardButton(text="🍽 Составь меню на неделю", callback_data="pro_demo_menu")],
            [InlineKeyboardButton(text="💌 Напиши поздравление", callback_data="pro_demo_letter")],
            [InlineKeyboardButton(text="🎨 Нарисуй открытку", callback_data="pro_demo_image")],
            [make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")],
        ]
        await send_system_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.warning(f"Ошибка send_pro_welcome для {user_id}: {e}")


@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Обработка предварительного запроса оплаты"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Обработка успешной оплаты"""
    user_id = message.from_user.id
    payload = message.successful_payment.invoice_payload or ""

    # Определяем срок подписки по payload
    if payload.startswith("weekly_"):
        days = WEEKLY_DAYS
        plan_label = "7 дней"
    else:
        days = 30
        plan_label = "30 дней"

    # Выдаем подписку
    grant_subscription(user_id, days=days)
    mark_as_paid(user_id)

    # Обновляем статистику
    price = message.successful_payment.total_amount
    increment_stat("total_payments")
    increment_stat("total_revenue", price)
    _append_payment_log(user_id, price, "XTR", "telegram_stars")

    await send_pro_welcome(message.chat.id, user_id)


# ==================== PRO DEMO CALLBACKS ====================
PRO_DEMO_PROMPTS = {
    "pro_demo_menu": "Составь разнообразное меню на неделю для семьи из 3 человек. Завтрак, обед, ужин. Простые продукты.",
    "pro_demo_letter": "Напиши красивое и душевное поздравление с днём рождения для близкого человека. Тёплое, искреннее, не банальное.",
    "pro_demo_image": "Нарисуй красивую поздравительную открытку с цветами и добрыми пожеланиями",
}


@dp.callback_query(F.data.in_(["pro_demo_menu", "pro_demo_letter", "pro_demo_image"]))
async def callback_pro_demo(callback: CallbackQuery):
    """Обработка демо-кнопок после оплаты PRO."""
    user_id = callback.from_user.id
    demo_key = callback.data
    prompt = PRO_DEMO_PROMPTS.get(demo_key, "")
    if not prompt:
        await callback.answer()
        return

    await callback.answer("Готовлю ответ...")

    if demo_key == "pro_demo_image":
        image_model = pick_image_model_for_prompt(user_id, prompt)
        if image_model:
            await bot.send_chat_action(callback.message.chat.id, "upload_photo")
            success, result = await generate_image_with_guard(user_id, prompt, image_model)
            if success:
                photo = (
                    BufferedInputFile(result, filename="demo_image.jpg")
                    if isinstance(result, (bytes, bytearray))
                    else result
                )
                await bot.send_photo(
                    chat_id=callback.message.chat.id,
                    photo=photo,
                    caption=f"🎨 <b>{image_model}</b>\nВот твоя открытка!",
                    parse_mode="HTML"
                )
                return
            else:
                await bot.send_message(callback.message.chat.id, result)
                return

    await bot.send_chat_action(callback.message.chat.id, "typing")
    ai_response = await get_ai_response(user_id, prompt)
    _append_request_log(user_id, "text", prompt, ai_response, load_user_data(user_id).get("model", DEFAULT_MODEL))
    await send_long_message(callback.message, ai_response, feedback_query=prompt)


# ==================== FEEDBACK CALLBACKS ====================
@dp.callback_query(F.data.startswith("fb_up_"))
async def callback_feedback_up(callback: CallbackQuery):
    """Обработка положительного фидбэка."""
    msg_id = callback.data.replace("fb_up_", "")
    user_id = callback.from_user.id

    fb_data = _pending_feedback.pop(msg_id, {})
    _append_feedback_log(user_id, int(msg_id) if msg_id.isdigit() else 0, "up", fb_data.get("query", ""), fb_data.get("response", ""))

    # Формируем кнопку "Поделиться"
    ref_link = get_referral_link(user_id)
    response_preview = fb_data.get("response", "")[:200]
    share_text = f"{response_preview}\n\nОтвет от AI-помощника 👉 {ref_link}"
    share_url = f"https://t.me/share/url?url={quote(ref_link)}&text={quote(response_preview[:100])}"

    try:
        await callback.message.edit_reply_markup(
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📤 Поделиться ответом", url=share_url)]
            ])
        )
    except Exception:
        pass
    await callback.answer("Спасибо! 🙏")


@dp.callback_query(F.data.startswith("fb_down_"))
async def callback_feedback_down(callback: CallbackQuery):
    """Обработка негативного фидбэка."""
    msg_id = callback.data.replace("fb_down_", "")
    user_id = callback.from_user.id

    fb_data = _pending_feedback.pop(msg_id, {})
    _append_feedback_log(user_id, int(msg_id) if msg_id.isdigit() else 0, "down", fb_data.get("query", ""), fb_data.get("response", ""))

    try:
        await callback.message.edit_reply_markup(reply_markup=None)
    except Exception:
        pass
    await callback.answer("Учту. Попробуй переформулировать запрос 💡")


# ==================== MY STATS CALLBACK ====================
@dp.callback_query(F.data == "my_stats")
async def callback_my_stats(callback: CallbackQuery):
    """Личная статистика пользователя."""
    user_id = callback.from_user.id
    user_data = load_user_data(user_id)

    total_requests = user_data.get("total_requests", 0)
    total_images = user_data.get("total_images", 0)
    days_active = len(user_data.get("days_active_set", []))
    categories = user_data.get("categories", {})

    # Топ-3 категории
    cat_names = {
        "food": "🍽 Еда/рецепты", "writing": "✍️ Тексты",
        "advice": "💡 Советы", "kids": "👶 Дети/школа",
        "image": "🎨 Картинки", "work": "💼 Работа",
        "health": "🏥 Здоровье", "other": "💬 Прочее",
    }
    sorted_cats = sorted(categories.items(), key=lambda x: -x[1])[:3]
    cat_text = ""
    if sorted_cats:
        cat_text = "\n<b>Топ категории:</b>\n"
        for cat, cnt in sorted_cats:
            label = cat_names.get(cat, cat)
            cat_text += f"  {label}: {cnt}\n"

    # Примерное время экономии (1 запрос ≈ 3 минуты)
    saved_minutes = total_requests * 3

    text = (
        "📊 <b>Твоя статистика</b>\n\n"
        f"💬 Запросов: <b>{total_requests}</b>\n"
        f"🎨 Картинок: <b>{total_images}</b>\n"
        f"📅 Дней активности: <b>{days_active}</b>\n"
        f"⏱ Сэкономлено: <b>~{saved_minutes} мин</b>"
        f"{cat_text}"
    )

    await safe_edit_or_send(
        callback, text,
        InlineKeyboardMarkup(inline_keyboard=[
            [make_inline_button("Назад", callback_data="settings", button_key="nav_back")]
        ])
    )
    await callback.answer()


# ==================== ADMIN HANDLERS ====================
@dp.callback_query(F.data == "admin_menu")
async def callback_admin_menu(callback: CallbackQuery, state: FSMContext):
    """Возврат в админ-меню"""
    await state.clear()

    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    await safe_edit_or_send(
        callback,
        "⚙️ <b>Админ-панель</b>",
        get_admin_keyboard()
    )
    await callback.answer()


@dp.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Статистика"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    stats = load_stats()
    users = get_all_users()
    active_subs = len(get_users_with_active_subscription())
    trial_users = len([u for u in users if get_free_trial_used(u["user_id"]) > 0])
    price = get_subscription_price()
    revenue_usd = stats.get("total_revenue_usd", 0) or 0
    paywall_shown = stats.get("paywall_shown", 0)
    sub_clicked = stats.get("subscription_clicked", 0)
    total_payments = stats.get("total_payments", 0)
    total_users = stats.get("total_users", 0)
    conv_rate = (total_payments / total_users * 100) if total_users > 0 else 0

    text = (
        "📊 <b>Статистика</b>\n\n"
        f"🟢 <b>Нажатий /start:</b> {stats.get('total_starts', 0)}\n"
        f"👥 <b>Всего пользователей:</b> {len(users)}\n"
        f"⭐ <b>Активных подписок:</b> {active_subs}\n"
        f"💳 <b>Оплат подписки:</b> {total_payments}\n"
        f"💬 <b>Всего сообщений:</b> {stats.get('total_messages', 0)}\n\n"
        "<b>📈 Воронка конверсии:</b>\n"
        f"  start → trial_used: {trial_users}\n"
        f"  paywall_shown: {paywall_shown}\n"
        f"  subscription_clicked: {sub_clicked}\n"
        f"  payment: {total_payments}\n"
        f"  CR (users→paid): {conv_rate:.1f}%\n\n"
        f"💰 <b>Доход (звёзды):</b> {stats.get('total_revenue', 0)} ⭐\n"
        f"💎 <b>Доход (CryptoBot):</b> {revenue_usd:.2f} USD\n\n"
        f"👥 <b>Рефералов:</b> {stats.get('total_referrals', 0)}\n"
        f"🏷️ <b>Текущая цена:</b> {price} ⭐ / {get_subscription_price_usd()} USD\n"
        f"🔥 <b>Скидка первый месяц:</b> {FIRST_BUY_DISCOUNT_STARS} ⭐ / {FIRST_BUY_DISCOUNT_USD} USD"
    )

    # Категории запросов из лога
    try:
        if os.path.exists(REQUESTS_LOG_FILE):
            cats = {}
            with open(REQUESTS_LOG_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        cat = entry.get("category", "other")
                        cats[cat] = cats.get(cat, 0) + 1
                    except Exception:
                        continue
            if cats:
                cat_names = {
                    "food": "🍽 Еда/рецепты", "writing": "✍️ Тексты/письма",
                    "advice": "💡 Советы", "kids": "👶 Дети/школа",
                    "image": "🎨 Картинки", "work": "💼 Работа",
                    "health": "🏥 Здоровье", "other": "💬 Прочее",
                    "photo": "📷 Фото", "voice": "🎤 Голос",
                }
                sorted_cats = sorted(cats.items(), key=lambda x: -x[1])
                text += "\n\n<b>📂 Категории запросов:</b>\n"
                for cat, cnt in sorted_cats[:8]:
                    label = cat_names.get(cat, cat)
                    text += f"  {label}: {cnt}\n"
    except Exception:
        pass

    # Фидбэк-статистика
    try:
        fb_stats = get_feedback_stats()
        if fb_stats["total"] > 0:
            pct = (fb_stats["positive"] / fb_stats["total"] * 100) if fb_stats["total"] > 0 else 0
            text += (
                f"\n\n<b>👍 Фидбэк:</b>\n"
                f"  Всего: {fb_stats['total']}\n"
                f"  👍 {fb_stats['positive']} / 👎 {fb_stats['negative']}\n"
                f"  Позитивных: {pct:.0f}%"
            )
    except Exception:
        pass

    await safe_edit_or_send(
        callback, text,
        InlineKeyboardMarkup(inline_keyboard=[
            [make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")]
        ])
    )
    await callback.answer()


# ==================== ADMIN REQUEST LOG ====================
@dp.callback_query(F.data.startswith("admin_reqlog_"))
async def callback_admin_reqlog(callback: CallbackQuery):
    """Просмотр лога запросов"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    page = int(callback.data.split("_")[-1])
    per_page = 10

    try:
        if not os.path.exists(REQUESTS_LOG_FILE):
            await safe_edit_or_send(
                callback, "📋 <b>Лог запросов пуст</b>\n\nПока нет записей.",
                InlineKeyboardMarkup(inline_keyboard=[
                    [make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")]
                ])
            )
            await callback.answer()
            return

        with open(REQUESTS_LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        total = len(lines)
        if total == 0:
            await safe_edit_or_send(
                callback, "📋 <b>Лог запросов пуст</b>\n\nПока нет записей.",
                InlineKeyboardMarkup(inline_keyboard=[
                    [make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")]
                ])
            )
            await callback.answer()
            return

        # Показываем от новых к старым
        start_idx = total - 1 - page * per_page
        end_idx = max(start_idx - per_page, -1)
        entries = []
        for i in range(start_idx, end_idx, -1):
            try:
                entry = json.loads(lines[i].strip())
                ts = entry.get("ts", "?")[:16].replace("T", " ")
                uid = entry.get("user_id", "?")
                req_type = entry.get("type", "?")
                inp = entry.get("input", "")[:80]
                resp = entry.get("response", "")[:100]
                model = entry.get("model", "")
                model_str = f" [{model}]" if model else ""
                entries.append(
                    f"<b>{ts}</b> | uid:{uid} | {req_type}{model_str}\n"
                    f"❓ {html.escape(inp)}\n"
                    f"💬 {html.escape(resp)}"
                )
            except Exception:
                continue

        total_pages = (total + per_page - 1) // per_page
        text = f"📋 <b>Лог запросов</b> (стр. {page + 1}/{total_pages}, всего: {total})\n\n"
        text += "\n\n".join(entries)

        nav_buttons = []
        if page > 0:
            nav_buttons.append(make_inline_button("◀️ Новее", callback_data=f"admin_reqlog_{page - 1}", button_key="nav_prev"))
        if end_idx > 0:
            nav_buttons.append(make_inline_button("Старее ▶️", callback_data=f"admin_reqlog_{page + 1}", button_key="nav_next"))

        keyboard_rows = []
        if nav_buttons:
            keyboard_rows.append(nav_buttons)
        keyboard_rows.append([make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")])

        await safe_edit_or_send(
            callback, text,
            InlineKeyboardMarkup(inline_keyboard=keyboard_rows)
        )
    except Exception as e:
        logging.exception(f"admin_reqlog error: {e}")
        await safe_edit_or_send(
            callback, f"❌ Ошибка чтения лога: {e}",
            InlineKeyboardMarkup(inline_keyboard=[
                [make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")]
            ])
        )
    await callback.answer()


# ==================== ADMIN MODELS MANAGEMENT ====================
@dp.callback_query(F.data.startswith("admin_models_"))
async def callback_admin_models(callback: CallbackQuery):
    """Управление моделями"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    page = int(callback.data.split("_")[-1])
    enabled_models = get_enabled_models()

    # Пагинация
    per_page = 8
    total_pages = (len(AVAILABLE_MODELS) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_models = AVAILABLE_MODELS[start_idx:end_idx]

    buttons = []
    for model in page_models:
        is_enabled = model in enabled_models
        status = "🟢" if is_enabled else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{model} {status}",
            callback_data=f"togglemodel_{model}"
        )])

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(make_inline_button("Назад", callback_data=f"admin_models_{page - 1}", button_key="nav_prev"))
    if page < total_pages - 1:
        nav_buttons.append(make_inline_button("Далее", callback_data=f"admin_models_{page + 1}", button_key="nav_next"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")])

    await safe_edit_or_send(
        callback,
        f"🧬 <b>Управление моделями</b>\n\n"
        f"🟢 - включена для пользователей\n"
        f"🔴 - выключена\n\n"
        f"Включено: {len(enabled_models)} из {len(AVAILABLE_MODELS)}",
        InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("togglemodel_"))
async def callback_toggle_model(callback: CallbackQuery):
    """Переключение модели"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    model = callback.data.replace("togglemodel_", "")
    new_state = toggle_model(model)

    status = "включена 🟢" if new_state else "выключена 🔴"
    await callback.answer(f"{model} {status}", show_alert=False)

    # Обновляем список моделей (остаёмся на той же странице)
    enabled_models = get_enabled_models()

    # Определяем текущую страницу
    try:
        model_index = AVAILABLE_MODELS.index(model)
        page = model_index // 8
    except ValueError:
        page = 0

    per_page = 8
    total_pages = (len(AVAILABLE_MODELS) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_models = AVAILABLE_MODELS[start_idx:end_idx]

    buttons = []
    for m in page_models:
        is_enabled = m in enabled_models
        status = "🟢" if is_enabled else "🔴"
        buttons.append([InlineKeyboardButton(
            text=f"{m} {status}",
            callback_data=f"togglemodel_{m}"
        )])

    nav_buttons = []
    if page > 0:
        nav_buttons.append(make_inline_button("Назад", callback_data=f"admin_models_{page - 1}", button_key="nav_prev"))
    if page < total_pages - 1:
        nav_buttons.append(make_inline_button("Далее", callback_data=f"admin_models_{page + 1}", button_key="nav_next"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")])

    try:
        await callback.message.edit_text(
            f"🧬 <b>Управление моделями</b>\n\n"
            f"🟢 - включена для пользователей\n"
            f"🔴 - выключена\n\n"
            f"Включено: {len(enabled_models)} из {len(AVAILABLE_MODELS)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    except:
        pass


@dp.callback_query(F.data == "admin_price")
async def callback_admin_price(callback: CallbackQuery, state: FSMContext):
    """Выбор валюты для изменения цены"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    price_stars = get_subscription_price()
    price_usd = get_subscription_price_usd()

    await safe_edit_or_send(
        callback,
        f"💰 <b>Изменить цену подписки</b>\n\n"
        f"⭐ Текущая цена (Звезды): {price_stars} ⭐\n"
        f"💎 Текущая цена (Crypto): {price_usd} USD\n\n"
        f"Выберите валюту:",
        InlineKeyboardMarkup(inline_keyboard=[
            [make_inline_button("Звезды", callback_data="price_stars", button_key="extend_stars")],
            [make_inline_button("CryptoBot", callback_data="price_crypto", button_key="extend_crypto")],
            [make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "price_stars")
async def callback_price_stars(callback: CallbackQuery, state: FSMContext):
    """Изменение цены в звездах"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    price = get_subscription_price()

    await safe_edit_or_send(
        callback,
        f"⭐ <b>Введите новую цену в звёздах:</b>\n\n"
        f"Текущая цена: {price} ⭐",
        get_cancel_keyboard("admin_menu")
    )

    await state.set_state(AdminStates.waiting_for_price_stars)
    await callback.answer()


@dp.callback_query(F.data == "price_crypto")
async def callback_price_crypto(callback: CallbackQuery, state: FSMContext):
    """Изменение цены в USD"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    price = get_subscription_price_usd()

    await safe_edit_or_send(
        callback,
        f"💎 <b>Введите новую цену в USD:</b>\n\n"
        f"Текущая цена: {price} USD",
        get_cancel_keyboard("admin_menu")
    )

    await state.set_state(AdminStates.waiting_for_price_crypto)
    await callback.answer()


@dp.message(AdminStates.waiting_for_price_stars)
async def process_new_price_stars(message: Message, state: FSMContext):
    """Обработка новой цены в звездах"""
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_price = int(message.text.strip())
        if not 1 <= new_price <= 100000:
            raise ValueError("Цена должна быть в диапазоне 1..100000")

        set_subscription_price(new_price)

        await message.answer(
            f"✔️ <b>Цена в звездах изменена!</b>\n\n"
            f"Новая цена: {new_price} ⭐/мес",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "✖️ Неверный формат. Введите целое число больше 0:",
            reply_markup=get_cancel_keyboard("admin_menu")
        )
        return

    await state.clear()


@dp.message(AdminStates.waiting_for_price_crypto)
async def process_new_price_crypto(message: Message, state: FSMContext):
    """Обработка новой цены в USD"""
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        new_price = float(message.text.strip().replace(',', '.'))
        if not 0.01 <= new_price <= 10000:
            raise ValueError("Цена должна быть в диапазоне 0.01..10000")

        set_subscription_price_usd(new_price)

        await message.answer(
            f"✔️ <b>Цена в USD изменена!</b>\n\n"
            f"Новая цена: {new_price} USD/мес",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
    except ValueError:
        await message.answer(
            "✖️ Неверный формат. Введите число больше 0.01:",
            reply_markup=get_cancel_keyboard("admin_menu")
        )
        return

    await state.clear()


@dp.callback_query(F.data == "admin_grant")
async def callback_admin_grant(callback: CallbackQuery, state: FSMContext):
    """Выдача подписки"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    await safe_edit_or_send(
        callback,
        "✔️ <b>Выдача подписки</b>\n\n"
        "Введите ID пользователя или @username:",
        get_cancel_keyboard("admin_menu")
    )

    await state.set_state(AdminStates.waiting_for_user_id_grant)
    await callback.answer()


@dp.message(AdminStates.waiting_for_user_id_grant)
async def process_grant_user_id(message: Message, state: FSMContext):
    """Получение ID/username пользователя для выдачи подписки"""
    if message.from_user.id not in ADMIN_IDS:
        return

    input_text = message.text.strip()
    user_id = None

    # Проверяем, это @username или ID
    if input_text.startswith('@'):
        user = get_user_by_username(input_text)
        if user:
            user_id = user["user_id"]
        else:
            await message.answer(
                "✖️ Пользователь с таким username не найден.\n"
                "Введите ID или @username:",
                reply_markup=get_cancel_keyboard("admin_menu")
            )
            return
    else:
        try:
            user_id = int(input_text)
        except ValueError:
            await message.answer(
                "✖️ Неверный формат. Введите ID (число) или @username:",
                reply_markup=get_cancel_keyboard("admin_menu")
            )
            return

    await state.update_data(grant_user_id=user_id)

    await message.answer(
        f"👤 Пользователь: <code>{user_id}</code>\n\n"
        "📅 Введите количество дней подписки:",
        reply_markup=get_cancel_keyboard("admin_menu"),
        parse_mode="HTML"
    )

    await state.set_state(AdminStates.waiting_for_grant_days)


@dp.message(AdminStates.waiting_for_grant_days)
async def process_grant_days(message: Message, state: FSMContext):
    """Обработка количества дней подписки"""
    if message.from_user.id not in ADMIN_IDS:
        return

    try:
        days = int(message.text.strip())
        if not 1 <= days <= 3650:
            raise ValueError("Days must be in range 1..3650")
    except ValueError:
        await message.answer(
            "✖️ Введите целое число дней (больше 0):",
            reply_markup=get_cancel_keyboard("admin_menu")
        )
        return

    data = await state.get_data()
    user_id = data.get("grant_user_id")

    grant_subscription(user_id, days=days)

    # Уведомляем пользователя
    try:
        await bot.send_message(
            user_id,
            f"🎁 <b>Вам выдана подписка!</b>\n\n"
            f"Подписка активна на {days} дней. Наслаждайтесь!",
            parse_mode="HTML"
        )
    except:
        pass

    await message.answer(
        f"✔️ <b>Подписка выдана!</b>\n\n"
        f"Пользователь: <code>{user_id}</code>\n"
        f"Срок: {days} дней",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

    await state.clear()


@dp.callback_query(F.data == "admin_revoke")
async def callback_admin_revoke(callback: CallbackQuery, state: FSMContext):
    """Отбор подписки"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    await safe_edit_or_send(
        callback,
        "✖️ <b>Отбор подписки</b>\n\n"
        "Введите ID пользователя или @username:",
        get_cancel_keyboard("admin_menu")
    )

    await state.set_state(AdminStates.waiting_for_user_id_revoke)
    await callback.answer()


@dp.message(AdminStates.waiting_for_user_id_revoke)
async def process_revoke_subscription(message: Message, state: FSMContext):
    """Обработка отбора подписки"""
    if message.from_user.id not in ADMIN_IDS:
        return

    input_text = message.text.strip()
    user_id = None

    # Проверяем, это @username или ID
    if input_text.startswith('@'):
        user = get_user_by_username(input_text)
        if user:
            user_id = user["user_id"]
        else:
            await message.answer(
                "✖️ Пользователь с таким username не найден.\n"
                "Введите ID или @username:",
                reply_markup=get_cancel_keyboard("admin_menu")
            )
            return
    else:
        try:
            user_id = int(input_text)
        except ValueError:
            await message.answer(
                "✖️ Неверный формат. Введите ID (число) или @username:",
                reply_markup=get_cancel_keyboard("admin_menu")
            )
            return

    revoke_subscription(user_id)

    await message.answer(
        f"✔️ <b>Подписка отобрана!</b>\n\n"
        f"Пользователь: <code>{user_id}</code>",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

    await state.clear()


@dp.callback_query(F.data == "admin_broadcast")
async def callback_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Рассылка"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    users = get_all_users()

    await safe_edit_or_send(
        callback,
        f"📢 <b>Рассылка</b>\n\n"
        f"Получателей: {len(users)} пользователей\n\n"
        "Отправьте сообщение для рассылки:",
        get_cancel_keyboard("admin_menu")
    )

    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()


@dp.message(AdminStates.waiting_for_broadcast)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Получение сообщения для рассылки"""
    if message.from_user.id not in ADMIN_IDS:
        return

    await state.update_data(broadcast_text=message.text, broadcast_msg_id=message.message_id)

    users = get_all_users()

    await message.answer(
        f"📢 <b>Подтверждение рассылки</b>\n\n"
        f"Сообщение:\n<blockquote>{message.text[:500]}</blockquote>\n\n"
        f"Получателей: {len(users)}\n\n"
        "Отправить?",
        reply_markup=get_broadcast_confirm_keyboard(),
        parse_mode="HTML"
    )

    await state.set_state(AdminStates.waiting_for_broadcast_confirm)


@dp.callback_query(F.data == "broadcast_confirm", AdminStates.waiting_for_broadcast_confirm)
async def callback_broadcast_confirm(callback: CallbackQuery, state: FSMContext):
    """Подтверждение рассылки"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    data = await state.get_data()
    broadcast_text = data.get("broadcast_text", "")

    users = get_all_users()
    success = 0
    failed = 0

    await safe_edit_or_send(callback, "📤 Отправка рассылки...")

    for user in users:
        try:
            await bot.send_message(user["user_id"], broadcast_text)
            success += 1
            await asyncio.sleep(0.05)  # Защита от флуда
        except Exception as e:
            logging.warning(f"Не удалось отправить сообщение {user['user_id']}: {e}")
            failed += 1

    await bot.send_message(
        chat_id=callback.message.chat.id,
        text=f"✔️ <b>Рассылка завершена!</b>\n\n"
             f"✉️ Успешно: {success}\n"
             f"✖️ Ошибки: {failed}",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )

    await state.clear()
    await callback.answer()


@dp.callback_query(F.data.startswith("admin_users_"))
async def callback_admin_users(callback: CallbackQuery):
    """Список всех пользователей с пагинацией"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    page = int(callback.data.split("_")[-1])
    all_users = get_all_users()

    if not all_users:
        await safe_edit_or_send(
            callback,
            "👥 <b>Пользователи</b>\n\nПользователей нет.",
            InlineKeyboardMarkup(inline_keyboard=[
                [make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")]
            ])
        )
        await callback.answer()
        return

    # Пагинация
    per_page = 10
    total_pages = (len(all_users) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = start_idx + per_page
    page_users = all_users[start_idx:end_idx]

    buttons = []
    for user in page_users:
        user_id = user["user_id"]
        name = user.get("full_name") or user.get("username") or str(user_id)
        # Добавляем ⭐️ если есть подписка
        has_sub = has_active_subscription(user_id)
        star = " ⭐️" if has_sub else ""
        buttons.append([InlineKeyboardButton(
            text=f"👤 {name}{star}",
            callback_data=f"viewuser_{user_id}"
        )])

    # Навигация (показываем только если больше 10 пользователей)
    nav_buttons = []
    if len(all_users) > per_page:
        if page > 0:
            nav_buttons.append(make_inline_button("Назад", callback_data=f"admin_users_{page - 1}", button_key="nav_prev"))
        if page < total_pages - 1:
            nav_buttons.append(make_inline_button("Далее", callback_data=f"admin_users_{page + 1}", button_key="nav_next"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")])

    await safe_edit_or_send(
        callback,
        f"👥 <b>Пользователи:</b>",
        InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("viewuser_"))
async def callback_view_user(callback: CallbackQuery):
    """Просмотр информации о пользователе"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    user_id = int(callback.data.split("_")[1])
    user_data = load_user_data(user_id)

    name = user_data.get("full_name") or "Без имени"
    username = f"@{user_data.get('username')}" if user_data.get('username') else "Нет"
    sub_end = get_subscription_end(user_id)

    if sub_end and sub_end > datetime.now():
        time_left = sub_end - datetime.now()
        days = time_left.days
        hours = time_left.seconds // 3600
        minutes = (time_left.seconds % 3600) // 60
        sub_status = f"Активна - {days}д {hours}ч {minutes}м"
    else:
        sub_status = "Не активна"

    text = (
        f"👤 <b>{name}</b>\n\n"
        f"🏷 <b>ID:</b> <code>{user_id}</code>\n"
        f"📱 <b>Username:</b> {username}\n"
        f"⭐ <b>Подписка:</b> {sub_status}"
    )

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [make_inline_button("Назад", callback_data="admin_users_0", button_key="nav_back")]
    ])

    # Удаляем текущее сообщение
    try:
        await callback.message.delete()
    except:
        pass

    # Пытаемся получить фото профиля
    try:
        photos = await bot.get_user_profile_photos(user_id, limit=1)

        if photos.total_count > 0:
            photo = photos.photos[0][-1]
            await bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=photo.file_id,
                caption=text,
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            await bot.send_message(
                chat_id=callback.message.chat.id,
                text=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
    except Exception as e:
        logging.warning(f"Ошибка получения фото: {e}")
        await bot.send_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    await callback.answer()


# ==================== MEDIA MANAGEMENT ====================
@dp.callback_query(F.data == "admin_media")
async def callback_admin_media(callback: CallbackQuery):
    """Управление медиа"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    start_media = get_start_media()
    channel_media = get_channel_media()

    start_status = "+" if start_media else "—"
    channel_status = "+" if channel_media else "—"

    buttons = [
        [make_inline_button(f"/start [{start_status}]", callback_data="media_start", button_key="home")],
        [make_inline_button(f"Подписка на канал [{channel_status}]", callback_data="media_channel", button_key="admin_channels")]
    ]

    buttons.append([make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")])

    await safe_edit_or_send(
        callback,
        f"🖼 <b>Управление медиа</b>\n\n"
        f"📌 /start: {start_status}\n"
        f"📌 Подписка на канал: {channel_status}",
        InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@dp.callback_query(F.data == "media_start")
async def callback_media_start(callback: CallbackQuery, state: FSMContext):
    """Установка медиа для /start"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    start_media = get_start_media()

    buttons = []
    if start_media:
        buttons.append([make_inline_button("Удалить", callback_data="media_start_delete", button_key="delete")])

    buttons.append([make_inline_button("Отмена", callback_data="admin_media", button_key="cancel")])

    await safe_edit_or_send(
        callback,
        "🖼 <b>Медиа для /start</b>\n\n"
        "Отправьте фото, видео или GIF:",
        InlineKeyboardMarkup(inline_keyboard=buttons)
    )

    await state.set_state(AdminStates.waiting_for_start_media)
    await callback.answer()


@dp.callback_query(F.data == "media_channel")
async def callback_media_channel(callback: CallbackQuery, state: FSMContext):
    """Установка медиа для сообщения о подписке на канал"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    channel_media = get_channel_media()

    buttons = []
    if channel_media:
        buttons.append([make_inline_button("Удалить", callback_data="media_channel_delete", button_key="delete")])

    buttons.append([make_inline_button("Отмена", callback_data="admin_media", button_key="cancel")])

    await safe_edit_or_send(
        callback,
        "🖼 <b>Медиа для подписки на канал</b>\n\n"
        "Отправьте фото, видео или GIF:",
        InlineKeyboardMarkup(inline_keyboard=buttons)
    )

    await state.set_state(AdminStates.waiting_for_channel_media)
    await callback.answer()


@dp.callback_query(F.data == "media_channel_delete")
async def callback_media_channel_delete(callback: CallbackQuery):
    """Удаление медиа для канала"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    set_channel_media(None, None)
    await callback.answer("✔️ Медиа удалено!")

    # Возвращаемся в меню медиа
    await callback_admin_media(callback)


@dp.message(AdminStates.waiting_for_start_media, F.photo)
async def process_start_media_photo(message: Message, state: FSMContext):
    """Обработка фото для /start"""
    if message.from_user.id not in ADMIN_IDS:
        return

    photo = message.photo[-1]
    set_start_media("photo", photo.file_id)

    await message.answer(
        "✔️ Фото для /start установлено!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


@dp.message(AdminStates.waiting_for_start_media, F.video)
async def process_start_media_video(message: Message, state: FSMContext):
    """Обработка видео для /start"""
    if message.from_user.id not in ADMIN_IDS:
        return

    set_start_media("video", message.video.file_id)

    await message.answer(
        "✔️ Видео для /start установлено!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


@dp.message(AdminStates.waiting_for_start_media, F.animation)
async def process_start_media_gif(message: Message, state: FSMContext):
    """Обработка GIF для /start"""
    if message.from_user.id not in ADMIN_IDS:
        return

    set_start_media("animation", message.animation.file_id)

    await message.answer(
        "✔️ GIF для /start установлено!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


@dp.callback_query(F.data == "media_start_delete")
async def callback_media_start_delete(callback: CallbackQuery):
    """Удаление медиа для /start"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    set_start_media(None, None)
    await callback.answer("✔️ Медиа удалено!")
    await callback_admin_media(callback)


# Обработчики медиа для канала
@dp.message(AdminStates.waiting_for_channel_media, F.photo)
async def process_channel_media_photo(message: Message, state: FSMContext):
    """Обработка фото для канала"""
    if message.from_user.id not in ADMIN_IDS:
        return

    photo = message.photo[-1]
    set_channel_media("photo", photo.file_id)

    await message.answer(
        "✔️ Фото для подписки на канал установлено!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


@dp.message(AdminStates.waiting_for_channel_media, F.video)
async def process_channel_media_video(message: Message, state: FSMContext):
    """Обработка видео для канала"""
    if message.from_user.id not in ADMIN_IDS:
        return

    set_channel_media("video", message.video.file_id)

    await message.answer(
        "✔️ Видео для подписки на канал установлено!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


@dp.message(AdminStates.waiting_for_channel_media, F.animation)
async def process_channel_media_gif(message: Message, state: FSMContext):
    """Обработка GIF для канала"""
    if message.from_user.id not in ADMIN_IDS:
        return

    set_channel_media("animation", message.animation.file_id)

    await message.answer(
        "✔️ GIF для подписки на канал установлено!",
        reply_markup=get_admin_keyboard()
    )
    await state.clear()


# ==================== INFO HANDLER ====================
@dp.callback_query(F.data.in_(["settings", "info"]))
async def callback_info(callback: CallbackQuery):
    """Настройки и информация о боте."""
    user_id = callback.from_user.id
    user_data = load_user_data(user_id)
    current_model = user_data.get("model", DEFAULT_MODEL)
    model_mode = "изображения" if current_model in IMAGE_MODELS else "текст"
    style_preset = get_response_style_preset(user_id)
    style_label = STYLE_PRESET_LABELS.get(style_preset, "Нейтральный")

    text = (
        f"{text_emoji('info')} <b>Настройки</b>\n\n"
        f"Модель: <b>{current_model}</b>\n"
        f"Стиль: <b>{style_label}</b>\n\n"
        "<i>Бот подбирает модель автоматически, но ты можешь выбрать сам.</i>"
    )

    admin_username = ADMIN_USERNAME.lstrip('@')

    has_sub = has_active_subscription(user_id)
    buttons = [
        [make_inline_button(text="Выбрать модель", callback_data="models_0", button_key="models", style="primary")],
        [make_inline_button(text="Стиль ответа", callback_data="thinking_menu", button_key="thinking", style="primary")],
        [make_inline_button(text="Начать чат заново", callback_data="confirm_clear", button_key="confirm_clear")],
        [make_inline_button(text="📊 Моя статистика", callback_data="my_stats", button_key="info")],
    ]
    if not has_sub:
        buttons.append([make_inline_button(text="Подписка PRO", callback_data="subscription", button_key="subscription", style="success")])
    buttons.extend([
        [make_inline_button(text="Написать поддержке", url=f"https://t.me/{admin_username}", button_key="contact_admin")],
        [make_inline_button(text="На главную", callback_data="main_menu", button_key="home", style="primary")]
    ])
    try:
        await callback.message.delete()
    except Exception:
        pass
    settings_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    if not await send_section_media_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=settings_markup,
        section="settings",
        parse_mode="HTML"
    ):
        await send_system_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=settings_markup,
            parse_mode="HTML"
        )
    await callback.answer()


# ==================== EXTEND SUBSCRIPTION ====================

# ==================== ADMIN CHANNELS MANAGEMENT ====================
@dp.callback_query(F.data == "admin_channels")
async def callback_admin_channels(callback: CallbackQuery):
    """Управление обязательными каналами"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    channels = get_required_channels()

    buttons = []

    if channels:
        for ch in channels:
            buttons.append([make_inline_button(
                ch['name'],
                callback_data=f"delchannel_{ch['id']}",
                button_key="cancel"
            )])

    buttons.append([make_inline_button("Добавить канал", callback_data="add_channel", button_key="add")])
    buttons.append([make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")])

    status = f"Каналов: {len(channels)}" if channels else "Нет обязательных каналов"

    await safe_edit_or_send(
        callback,
        f"📺 <b>Подписка на канал</b>\n\n"
        f"{status}\n\n"
        "Нажмите на канал чтобы удалить его.",
        InlineKeyboardMarkup(inline_keyboard=buttons)
    )
    await callback.answer()


@dp.callback_query(F.data == "add_channel")
async def callback_add_channel(callback: CallbackQuery, state: FSMContext):
    """Добавление канала"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    await safe_edit_or_send(
        callback,
        "📺 <b>Добавление канала</b>\n\n"
        "Перешлите любое сообщение из канала или введите данные в формате:\n\n"
        "<code>@channel_username | Название канала</code>\n\n"
        "Например:\n"
        "<code>@mychannel | Мой канал</code>\n\n"
        "⚠️ Бот должен быть администратором канала с правом 'Приглашение пользователей'!",
        get_cancel_keyboard("admin_channels")
    )

    await state.set_state(AdminStates.waiting_for_channel)
    await callback.answer()


@dp.message(AdminStates.waiting_for_channel)
async def process_add_channel(message: Message, state: FSMContext):
    """Обработка добавления канала"""
    if message.from_user.id not in ADMIN_IDS:
        return

    # Проверяем, переслано ли сообщение из канала
    if message.forward_from_chat and message.forward_from_chat.type == "channel":
        channel = message.forward_from_chat
        channel_id = str(channel.id)
        channel_name = channel.title
    else:
        # Парсим текст
        try:
            parts = message.text.split("|")
            if len(parts) < 2:
                raise ValueError("Неверный формат")

            channel_id = parts[0].strip()
            channel_name = parts[1].strip()
        except:
            await message.answer(
                "✖️ Неверный формат. Перешлите сообщение из канала или используйте формат:\n"
                "<code>@channel | Название</code>",
                reply_markup=get_cancel_keyboard("admin_channels"),
                parse_mode="HTML"
            )
            return

    # Проверяем доступ к каналу и создаем пригласительную ссылку
    try:
        chat = await bot.get_chat(channel_id)
        channel_id = str(chat.id)
        channel_name = chat.title or channel_name

        # Создаем вечную пригласительную ссылку
        invite_link = await bot.create_chat_invite_link(
            chat_id=channel_id,
            name=f"Invite from AI Bot - {datetime.now().strftime('%d.%m.%Y')}",
            creates_join_request=False  # Автоматическое одобрение
        )
        channel_link = invite_link.invite_link

    except Exception as e:
        logging.warning(f"Ошибка создания ссылки для канала: {e}")
        await message.answer(
            "⚠️ Не удалось создать пригласительную ссылку.\n\n"
            "Убедитесь что:\n"
            "• Бот добавлен в канал как администратор\n"
            "• У бота есть право 'Приглашение пользователей'\n\n"
            "Попробуйте еще раз или обратитесь к документации.",
            reply_markup=get_cancel_keyboard("admin_channels")
        )
        await state.clear()
        return

    if add_required_channel(channel_id, channel_name, channel_link):
        await message.answer(
            f"✔️ Канал <b>{channel_name}</b> добавлен!\n\n"
            f"🔗 Создана пригласительная ссылка:\n"
            f"<code>{channel_link}</code>",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "✖️ Этот канал уже добавлен!",
            reply_markup=get_admin_keyboard()
        )

    await state.clear()


@dp.callback_query(F.data.startswith("delchannel_"))
async def callback_delete_channel(callback: CallbackQuery):
    """Удаление канала"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    channel_id = callback.data.replace("delchannel_", "")
    remove_required_channel(channel_id)

    await callback.answer("✔️ Канал удалён!")
    await callback_admin_channels(callback)


# ==================== ADMIN BLACKLIST MANAGEMENT ====================
@dp.callback_query(F.data == "admin_blacklist")
async def callback_admin_blacklist(callback: CallbackQuery):
    """Управление черным списком"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    blacklist = load_blacklist()

    text = f"🚫 <b>Чёрный список</b>\n\n"

    if blacklist:
        text += f"Заблокировано: {len(blacklist)} пользователей\n\n"
        for user_id in blacklist[:10]:
            user_data = load_user_data(user_id)
            name = user_data.get("full_name") or user_data.get("username") or str(user_id)
            text += f"• <code>{user_id}</code> - {name}\n"

        if len(blacklist) > 10:
            text += f"\n... и ещё {len(blacklist) - 10}"
    else:
        text += "Список пуст"

    await safe_edit_or_send(
        callback, text,
        InlineKeyboardMarkup(inline_keyboard=[
            [make_inline_button("Заблокировать", callback_data="blacklist_add", button_key="block")],
            [make_inline_button("Разблокировать", callback_data="blacklist_remove", button_key="unblock")],
            [make_inline_button("Назад", callback_data="admin_menu", button_key="nav_back")]
        ])
    )
    await callback.answer()


@dp.callback_query(F.data == "blacklist_add")
async def callback_blacklist_add(callback: CallbackQuery, state: FSMContext):
    """Добавление в черный список"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    await safe_edit_or_send(
        callback,
        "🚫 <b>Заблокировать пользователя</b>\n\n"
        "Введите ID пользователя или @username:",
        get_cancel_keyboard("admin_blacklist")
    )

    await state.set_state(AdminStates.waiting_for_blacklist_add)
    await callback.answer()


@dp.message(AdminStates.waiting_for_blacklist_add)
async def process_blacklist_add(message: Message, state: FSMContext):
    """Обработка добавления в черный список"""
    if message.from_user.id not in ADMIN_IDS:
        return

    input_text = message.text.strip()
    user_id = None

    if input_text.startswith('@'):
        user = get_user_by_username(input_text)
        if user:
            user_id = user["user_id"]
        else:
            await message.answer(
                "✖️ Пользователь не найден.\n"
                "Введите ID или @username:",
                reply_markup=get_cancel_keyboard("admin_blacklist")
            )
            return
    else:
        try:
            user_id = int(input_text)
        except ValueError:
            await message.answer(
                "✖️ Неверный формат. Введите ID или @username:",
                reply_markup=get_cancel_keyboard("admin_blacklist")
            )
            return

    if user_id in ADMIN_IDS:
        await message.answer(
            "✖️ Нельзя заблокировать администратора!",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        return

    add_to_blacklist(user_id)

    await message.answer(
        f"✔️ Пользователь <code>{user_id}</code> заблокирован!",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()


@dp.callback_query(F.data == "blacklist_remove")
async def callback_blacklist_remove(callback: CallbackQuery, state: FSMContext):
    """Удаление из черного списка"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("✖️ Доступ запрещен", show_alert=True)
        return

    await safe_edit_or_send(
        callback,
        "🚫 <b>Разблокировать пользователя</b>\n\n"
        "Введите ID пользователя или @username:",
        get_cancel_keyboard("admin_blacklist")
    )

    await state.set_state(AdminStates.waiting_for_blacklist_remove)
    await callback.answer()


@dp.message(AdminStates.waiting_for_blacklist_remove)
async def process_blacklist_remove(message: Message, state: FSMContext):
    """Обработка удаления из черного списка"""
    if message.from_user.id not in ADMIN_IDS:
        return

    input_text = message.text.strip()
    user_id = None

    if input_text.startswith('@'):
        user = get_user_by_username(input_text)
        if user:
            user_id = user["user_id"]
        else:
            await message.answer(
                "✖️ Пользователь не найден.\n"
                "Введите ID или @username:",
                reply_markup=get_cancel_keyboard("admin_blacklist")
            )
            return
    else:
        try:
            user_id = int(input_text)
        except ValueError:
            await message.answer(
                "✖️ Неверный формат. Введите ID или @username:",
                reply_markup=get_cancel_keyboard("admin_blacklist")
            )
            return

    if not is_blacklisted(user_id):
        await message.answer(
            "✖️ Этот пользователь не в чёрном списке!",
            reply_markup=get_admin_keyboard()
        )
        await state.clear()
        return

    remove_from_blacklist(user_id)

    await message.answer(
        f"✔️ Пользователь <code>{user_id}</code> разблокирован!",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await state.clear()


# ==================== THINKING PREFERENCES ====================
@dp.callback_query(F.data == "thinking_menu")
async def callback_thinking_menu(callback: CallbackQuery):
    """Меню настройки мышления"""
    user_id = callback.from_user.id

    # Проверки
    if is_blacklisted(user_id):
        await callback.answer()
        return

    if user_id not in ADMIN_IDS and get_required_channels():
        if not await check_channel_subscription(user_id):
            await callback.answer("Сначала подпишись на канал!", show_alert=True)
            return

    current_pref = get_thinking_preference(user_id)
    current_preset = get_response_style_preset(user_id)
    preset_human = STYLE_PRESET_LABELS.get(current_preset, "Нейтральный")
    preset_desc = STYLE_PRESET_DESCRIPTIONS.get(current_preset, "")
    preset_block = (
        f"<b>Как бот будет отвечать</b>\n"
        "Выбери стиль общения:\n"
        "• <b>Серьёзный</b> — для работы и деловых задач\n"
        "• <b>Нейтральный</b> — универсальный, на каждый день\n"
        "• <b>Весёлый</b> — когда хочется легкости\n"
        "• <b>Друг</b> — тёплое дружеское общение\n\n"
        f"<b>Сейчас: {preset_human}</b>\n"
        f"<i>{preset_desc}</i>\n"
    )

    if current_pref:
        # Проверяем, это JSON или обычный текст
        try:
            pref_json = json.loads(current_pref)

            # Для JSON показываем краткую информацию
            top_keys = list(pref_json.keys())
            keys_display = ", ".join(top_keys[:5])
            if len(top_keys) > 5:
                keys_display += f" +{len(top_keys) - 5}"

            # Считаем общее количество параметров
            def count_params(obj):
                if isinstance(obj, dict):
                    return sum(count_params(v) for v in obj.values()) + len(obj)
                elif isinstance(obj, list):
                    return sum(count_params(item) for item in obj) + 1
                return 1

            total_params = count_params(pref_json)

            text = (
                f"{text_emoji('style')} <b>Стиль ответа</b>\n\n"
                f"{preset_block}\n"
                "<b>Дополнительные настройки загружены</b>\n"
                f"Секций: {len(top_keys)}\n"
                f"Параметров: {total_params}\n"
                f"Ключи: <code>{keys_display}</code>"
            )
        except:
            # Обычный текст
            pref_display = f"<blockquote>{current_pref[:200]}{'...' if len(current_pref) > 200 else ''}</blockquote>"
            text = (
                f"{text_emoji('style')} <b>Стиль ответа</b>\n\n"
                f"{preset_block}\n"
                "<b>Твои настройки:</b>\n"
                f"{pref_display}"
            )

        buttons = [
            [
                make_inline_button("Серьезный", callback_data="stylepreset_serious", button_key="preset_serious"),
                make_inline_button("Нейтральный", callback_data="stylepreset_neutral", button_key="preset_neutral")
            ],
            [
                make_inline_button("Веселый", callback_data="stylepreset_funny", button_key="preset_funny"),
                make_inline_button("Друг", callback_data="stylepreset_friend", button_key="preset_friend")
            ],
            [make_inline_button("Изменить", callback_data="thinking_edit", button_key="thinking_edit", style="primary")],
            [make_inline_button("Удалить", callback_data="thinking_delete", button_key="thinking_delete", style="danger")],
            [make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")]
        ]
    else:
        text = (
            f"{text_emoji('style')} <b>Стиль ответа</b>\n\n"
            f"{preset_block}\n"
            "<blockquote>Хочешь настроить точнее?\n"
            "Нажми «Настроить» и напиши, как бот должен отвечать.\n"
            "Например: «пиши коротко и просто»</blockquote>"
        )
        buttons = [
            [
                make_inline_button("Серьезный", callback_data="stylepreset_serious", button_key="preset_serious"),
                make_inline_button("Нейтральный", callback_data="stylepreset_neutral", button_key="preset_neutral")
            ],
            [
                make_inline_button("Веселый", callback_data="stylepreset_funny", button_key="preset_funny"),
                make_inline_button("Друг", callback_data="stylepreset_friend", button_key="preset_friend")
            ],
            [make_inline_button("Настроить", callback_data="thinking_edit", button_key="thinking_edit", style="primary")],
            [make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")]
        ]

    # Проверяем подписку
    if not has_active_subscription(user_id):
        buttons = [
            [make_inline_button("Подключить PRO", callback_data="subscription", button_key="subscription", style="success")],
            [make_inline_button("На главную", callback_data="main_menu", button_key="home", style="primary")]
        ]
        text = (
            f"{text_emoji('style')} <b>Стиль ответа</b>\n\n"
            f"{preset_block}\n"
            "Чтобы менять стиль — подключи PRO."
        )

    try:
        await callback.message.delete()
    except Exception:
        pass
    thinking_markup = InlineKeyboardMarkup(inline_keyboard=buttons)
    if not await send_section_media_message(
        chat_id=callback.message.chat.id,
        text=text,
        reply_markup=thinking_markup,
        section="thinking",
        parse_mode="HTML"
    ):
        await send_system_message(
            chat_id=callback.message.chat.id,
            text=text,
            reply_markup=thinking_markup,
            parse_mode="HTML"
        )
    await callback.answer()


@dp.callback_query(F.data.startswith("stylepreset_"))
async def callback_style_preset(callback: CallbackQuery):
    """Установить пресет стиля ответа."""
    user_id = callback.from_user.id
    preset = callback.data.replace("stylepreset_", "").strip()

    if not has_active_subscription(user_id):
        await callback.answer("Чтобы менять стиль — подключи PRO", show_alert=True)
        return

    if preset not in STYLE_PRESET_PROMPTS:
        await callback.answer("Такой стиль не найден", show_alert=True)
        return

    set_response_style_preset(user_id, preset)
    await callback_thinking_menu(callback)


@dp.callback_query(F.data == "thinking_edit")
async def callback_thinking_edit(callback: CallbackQuery, state: FSMContext):
    """Редактирование предпочтений мышления"""
    user_id = callback.from_user.id

    if not has_active_subscription(user_id):
        await callback.answer("Тонкая настройка доступна с PRO", show_alert=True)
        return

    await safe_edit_or_send(
        callback,
        "⚙️ <b>Тонкая настройка</b>\n\n"
        "Напиши, как бот должен с тобой общаться.\n\n"
        "<b>Например:</b>\n"
        "<i>«общайся со мной как друг, пиши с маленькой буквы, используй эмодзи»</i>\n\n"
        "<i>«отвечай коротко, по делу, без воды»</i>\n\n"
        "<i>«пиши развёрнуто, с примерами и объяснениями»</i>",
        get_cancel_keyboard("thinking_menu")
    )

    await state.set_state(UserStates.waiting_for_thinking)
    await callback.answer()


@dp.message(UserStates.waiting_for_thinking, F.text)
async def process_thinking_preference(message: Message, state: FSMContext):
    """Сохранение предпочтений мышления"""
    user_id = message.from_user.id

    if not has_active_subscription(user_id):
        await state.clear()
        return

    # Проверка на наличие текста
    if not message.text:
        await message.answer(
            "Напиши текстом, как бот должен общаться:",
            reply_markup=get_cancel_keyboard("thinking_menu")
        )
        return

    preference = message.text.strip()

    if len(preference) < 5:
        await message.answer(
            "Слишком коротко. Напиши подробнее — как бот должен отвечать:",
            reply_markup=get_cancel_keyboard("thinking_menu")
        )
        return

    if len(preference) > 10000:
        await message.answer(
            "Слишком длинный текст (максимум 10000 символов). Сократи:",
            reply_markup=get_cancel_keyboard("thinking_menu")
        )
        return

    # Проверяем, это JSON или обычный текст
    is_json = False
    json_config = None

    if preference.strip().startswith('{'):
        try:
            json_config = json.loads(preference)
            is_json = True

            # Валидация: проверяем что это словарь
            if not isinstance(json_config, dict):
                raise ValueError("JSON должен быть объектом")

            # Проверяем размер JSON
            json_str = json.dumps(json_config, ensure_ascii=False, indent=2)
            if len(json_str) > 10000:
                raise ValueError("JSON слишком большой (макс. 10000 символов)")

        except json.JSONDecodeError as e:
            await message.answer(
                f"Ошибка в формате:\n<code>{str(e)}</code>\n\n"
                "Проверь и попробуй снова:",
                reply_markup=get_cancel_keyboard("thinking_menu"),
                parse_mode="HTML"
            )
            return
        except ValueError as e:
            await message.answer(
                f"{str(e)}\n\nПопробуй снова:",
                reply_markup=get_cancel_keyboard("thinking_menu")
            )
            return

    set_thinking_preference(user_id, preference)

    if is_json:
        # Подсчитываем ключи верхнего уровня
        top_keys = list(json_config.keys())
        keys_display = ", ".join(top_keys[:5])
        if len(top_keys) > 5:
            keys_display += f" и ещё {len(top_keys) - 5}"

        await message.answer(
            "✔️ <b>Настройки сохранены!</b>\n\n"
            f"Разделов: {len(top_keys)}\n"
            f"Ключи: {keys_display}\n\n"
            "Бот будет учитывать эти настройки в ответах.",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "✔️ <b>Сохранено!</b>\n\n"
            "Бот будет учитывать твои пожелания в ответах.",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )

    await state.clear()


@dp.message(UserStates.waiting_for_thinking, F.document)
async def process_thinking_document(message: Message, state: FSMContext):
    """Обработка JSON файла для настройки мышления"""
    user_id = message.from_user.id

    if not has_active_subscription(user_id):
        await state.clear()
        return

    # Проверяем расширение файла
    if not message.document.file_name.endswith('.json'):
        await message.answer(
            "Отправь файл в формате .json",
            reply_markup=get_cancel_keyboard("thinking_menu")
        )
        return

    # Проверяем размер файла (макс 1 МБ)
    if message.document.file_size > 1024 * 1024:
        await message.answer(
            "Файл слишком большой (максимум 1 МБ)",
            reply_markup=get_cancel_keyboard("thinking_menu")
        )
        return

    try:
        # Скачиваем файл
        file = await bot.get_file(message.document.file_id)
        file_bytes = await bot.download_file(file.file_path)

        # Читаем JSON
        json_text = file_bytes.read().decode('utf-8')
        json_config = json.loads(json_text)

        # Валидация
        if not isinstance(json_config, dict):
            raise ValueError("JSON должен быть объектом")

        if len(json_text) > 10000:
            raise ValueError("JSON слишком большой (макс. 10000 символов)")

        validate_json_structure(json_config)

        # Сохраняем
        set_thinking_preference(user_id, json_text)

        # Подсчитываем ключи верхнего уровня
        top_keys = list(json_config.keys())
        keys_display = ", ".join(top_keys[:5])
        if len(top_keys) > 5:
            keys_display += f" и ещё {len(top_keys) - 5}"

        await message.answer(
            "✔️ <b>Настройки загружены из файла!</b>\n\n"
            f"Разделов: {len(top_keys)}\n"
            f"Ключи: {keys_display}\n\n"
            "Бот будет учитывать эти настройки в ответах.",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="HTML"
        )

        await state.clear()

    except json.JSONDecodeError as e:
        await message.answer(
            f"Ошибка в файле:\n<code>{str(e)}</code>\n\n"
            "Проверь файл и попробуй снова:",
            reply_markup=get_cancel_keyboard("thinking_menu"),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка загрузки JSON: {e}")
        await message.answer(
            f"Не получилось загрузить файл. Попробуй ещё раз.",
            reply_markup=get_cancel_keyboard("thinking_menu")
        )

@dp.callback_query(F.data == "thinking_delete")
async def callback_thinking_delete(callback: CallbackQuery):
    """Удаление предпочтений мышления"""
    user_id = callback.from_user.id

    set_thinking_preference(user_id, None)

    await safe_edit_or_send(
        callback,
        "✔️ Настройки сброшены!\n\n"
        "Бот вернулся к обычному стилю общения.",
        get_main_keyboard(user_id)
    )
    await callback.answer()


# ==================== AI FUNCTIONS ====================
def _messages_to_deepseek_format(messages: list) -> list:
    """Преобразовать сообщения в формат DeepSeek: content только строка."""
    result = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        parts.append(part.get("text", ""))
                    elif part.get("type") == "image_url":
                        parts.append("[Пользователь приложил изображение]")
            content = " ".join(parts) if parts else "[Медиа]"
        result.append({"role": role, "content": content or ""})
    return result


def _deepseek_model(user_model: str) -> str:
    """Маппинг модели бота на модель DeepSeek API."""
    if user_model == "deepseek-r1":
        return "deepseek-reasoner"
    return "deepseek-chat"


AI_MODEL_ANSWER = "Российская нейросеть АЛИСА"

_AI_MODEL_QUESTION_PATTERNS = [
    r"(?i)на\s+основе\s+какой\s+нейрон",
    r"(?i)какая\s+нейросеть",
    r"(?i)какая\s+нейронка",
    r"(?i)какой\s+нейрон",
    r"(?i)какая\s+модель\s+(ты|используешь|отвечаешь)",
    r"(?i)какой\s+ии\s+(ты|используешь|отвечаешь)",
    r"(?i)какой\s+искусственный\s+интеллект",
    r"(?i)на\s+базе\s+чего\s+ты\s+работаешь",
    r"(?i)что\s+за\s+нейросеть",
    r"(?i)что\s+за\s+нейронка",
    r"(?i)кто\s+тебя\s+создал",
    r"(?i)кто\s+тебя\s+сделал",
    r"(?i)на\s+чем\s+ты\s+работаешь",
    r"(?i)какой\s+чатгпт",
    r"(?i)это\s+чатгпт",
    r"(?i)ты\s+gpt",
    r"(?i)ты\s+chatgpt",
]


def _is_ai_model_question(text: str) -> bool:
    """Проверить, спрашивает ли пользователь о нейросети/модели бота."""
    if not text or len(text.strip()) < 5:
        return False
    t = text.strip().lower()
    return any(re.search(p, t) for p in _AI_MODEL_QUESTION_PATTERNS)


async def get_ai_response(user_id: int, user_message: str, photo_base64: str = None) -> str:
    """Получить ответ от AI"""
    user_message = sanitize_user_input(user_message)

    # Вопрос о нейросети — фиксированный ответ
    if _is_ai_model_question(user_message):
        return AI_MODEL_ANSWER

    # Получаем предпочтения мышления
    thinking_pref = get_thinking_preference(user_id)

    # Формируем историю с системным сообщением если есть предпочтения
    messages = []
    messages.append({
        "role": "system",
        "content": RESPONSE_STYLE_SYSTEM_PROMPT
    })

    style_preset = get_response_style_preset(user_id)
    messages.append({
        "role": "system",
        "content": STYLE_PRESET_PROMPTS.get(style_preset, STYLE_PRESET_PROMPTS["neutral"])
    })

    if thinking_pref:
        # Проверяем, это JSON или текст
        try:
            pref_json = json.loads(thinking_pref)

            # Формируем промпт для ролевой игры - ИИ становится персонажем из JSON
            system_msg = "Ты - это персонаж, описанный в следующем профиле. Общайся от первого лица, будто это твоя настоящая личность.\n\n"
            system_msg += "=== ТВОЙ ПРОФИЛЬ ===\n\n"

            # Рекурсивно формируем описание из JSON
            def format_json_to_text(obj, indent=0):
                result = ""
                prefix = "  " * indent

                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, (dict, list)):
                            result += f"{prefix}{key}:\n"
                            result += format_json_to_text(value, indent + 1)
                        else:
                            result += f"{prefix}{key}: {value}\n"
                elif isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, (dict, list)):
                            result += format_json_to_text(item, indent)
                        else:
                            result += f"{prefix}• {item}\n"
                return result

            system_msg += format_json_to_text(pref_json)
            system_msg += "\n=== ИНСТРУКЦИИ ===\n"
            system_msg += "• Общайся от первого лица ('я', 'мне', 'мой')\n"
            system_msg += "• Используй стиль речи и сленг из профиля\n"
            system_msg += "• Веди себя естественно, как реальный человек\n"
            system_msg += "• Если в профиле указано использование мата - используй его естественно\n"
            system_msg += "• Отвечай на основе фактов из профиля\n"
            system_msg += "• Не упоминай, что ты ИИ или бот"

            messages.append({
                "role": "system",
                "content": system_msg
            })
        except:
            # Обычный текст - старая логика
            messages.append({
                "role": "system",
                "content": f"Следуй этим указаниям при общении: {thinking_pref}"
            })

    # Жестко фиксируем формат ответа, даже при пользовательских пресетах/ролях.
    messages.append({
        "role": "system",
        "content": RESPONSE_STYLE_HARD_GUARD_PROMPT
    })

    # Добавляем историю
    history = get_history_for_api(user_id, limit=20)
    messages.extend(history)

    # Формируем сообщение пользователя
    if photo_base64:
        user_content = [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{photo_base64}"}},
            {"type": "text", "text": user_message}
        ]
    else:
        user_content = user_message

    messages.append({"role": "user", "content": user_content})

    user_data = load_user_data(user_id)
    user_model = user_data.get("model", DEFAULT_MODEL)
    # Для текстового/мультимодального чата не используем image-only модели.
    if user_model in IMAGE_MODELS:
        user_model = DEFAULT_MODEL

    def _save_and_return(ai_reply: str) -> str:
        text_msg = user_message if not photo_base64 else f"[Фото] {user_message}"
        add_message_to_history(user_id, "user", text_msg)
        add_message_to_history(user_id, "assistant", ai_reply)
        increment_stat("total_messages")
        return ai_reply

    try:
        # При наличии фото используем onlysq API (поддерживает vision)
        if photo_base64 and API_BEARER_TOKEN:
            payload = {"model": "gemini-3-flash", "request": {"messages": messages}}
            headers = {"Authorization": f"Bearer {API_BEARER_TOKEN}", "Content-Type": "application/json"}
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=payload, headers=headers, timeout=60) as response:
                    if response.status == 200:
                        data = await response.json()
                        ai_reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if ai_reply:
                            return _save_and_return(ai_reply)
                    logging.warning(f"onlysq vision API status={response.status}, fallback to DeepSeek")

        if not _get_deepseek_key():
            return "Текстовый AI временно недоступен. Попробуй позже."

        # Чат через DeepSeek API (без фото или fallback)
        ds_messages = _messages_to_deepseek_format(messages)
        ds_model = _deepseek_model(user_model)
        send = {"model": ds_model, "messages": ds_messages}
        headers = {"Authorization": f"Bearer {_get_deepseek_key()}", "Content-Type": "application/json"}
        url = DEEPSEEK_API_URL

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=send, headers=headers, timeout=60) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_reply = data['choices'][0]['message']['content']
                    return _save_and_return(ai_reply)
                else:
                    return "Сервис временно недоступен. Попробуй через пару минут."
    except asyncio.TimeoutError:
        return "Ответ слишком долго формируется. Попробуй отправить запрос ещё раз."
    except Exception as e:
        logging.error(f"Ошибка AI: {e}")
        return "Ошибка соединения с сервисом. Попробуй через минуту."


async def get_business_ai_response(bot_owner_id: int, business_connection_id: str, client_chat_id: int,
                                   user_message: str, photo_base64: str = None) -> str:
    """Получить ответ от AI для бизнес-чата"""
    user_message = sanitize_user_input(user_message)

    if _is_ai_model_question(user_message):
        return AI_MODEL_ANSWER

    # Получаем предпочтения мышления владельца
    thinking_pref = get_thinking_preference(bot_owner_id)

    # Формируем историю
    messages = []
    messages.append({
        "role": "system",
        "content": RESPONSE_STYLE_SYSTEM_PROMPT
    })

    style_preset = get_response_style_preset(bot_owner_id)
    messages.append({
        "role": "system",
        "content": STYLE_PRESET_PROMPTS.get(style_preset, STYLE_PRESET_PROMPTS["neutral"])
    })

    if thinking_pref:
        # Проверяем, это JSON или текст
        try:
            pref_json = json.loads(thinking_pref)

            # Формируем промпт для ролевой игры - ИИ становится персонажем из JSON
            system_msg = "Ты - это персонаж, описанный в следующем профиле. Общайся от первого лица, будто это твоя настоящая личность.\n\n"
            system_msg += "=== ТВОЙ ПРОФИЛЬ ===\n\n"

            # Рекурсивно формируем описание из JSON
            def format_json_to_text(obj, indent=0):
                result = ""
                prefix = "  " * indent

                if isinstance(obj, dict):
                    for key, value in obj.items():
                        if isinstance(value, (dict, list)):
                            result += f"{prefix}{key}:\n"
                            result += format_json_to_text(value, indent + 1)
                        else:
                            result += f"{prefix}{key}: {value}\n"
                elif isinstance(obj, list):
                    for item in obj:
                        if isinstance(item, (dict, list)):
                            result += format_json_to_text(item, indent)
                        else:
                            result += f"{prefix}• {item}\n"
                return result

            system_msg += format_json_to_text(pref_json)
            system_msg += "\n=== ИНСТРУКЦИИ ===\n"
            system_msg += "• Общайся от первого лица ('я', 'мне', 'мой')\n"
            system_msg += "• Используй стиль речи и сленг из профиля\n"
            system_msg += "• Веди себя естественно, как реальный человек\n"
            system_msg += "• Если в профиле указано использование мата - используй его естественно\n"
            system_msg += "• Отвечай на основе фактов из профиля\n"
            system_msg += "• Не упоминай, что ты ИИ или бот"

            messages.append({
                "role": "system",
                "content": system_msg
            })
        except:
            # Обычный текст - старая логика
            messages.append({
                "role": "system",
                "content": f"Следуй этим указаниям при общении: {thinking_pref}"
            })

    # Жестко фиксируем формат ответа, даже при пользовательских пресетах/ролях.
    messages.append({
        "role": "system",
        "content": RESPONSE_STYLE_HARD_GUARD_PROMPT
    })

    # Добавляем историю ЭТОГО КОНКРЕТНОГО клиента
    history = get_business_history_for_api(business_connection_id, client_chat_id, limit=20)
    messages.extend(history)

    # Формируем сообщение пользователя
    if photo_base64:
        user_content = [
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{photo_base64}"}},
            {"type": "text", "text": user_message}
        ]
    else:
        user_content = user_message

    messages.append({"role": "user", "content": user_content})

    user_data = load_user_data(bot_owner_id)
    user_model = user_data.get("model", DEFAULT_MODEL)
    if user_model in IMAGE_MODELS:
        user_model = DEFAULT_MODEL

    if photo_base64 and API_BEARER_TOKEN:
        payload = {"model": "gemini-3-flash", "request": {"messages": messages}}
        headers = {"Authorization": f"Bearer {API_BEARER_TOKEN}", "Content-Type": "application/json"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=payload, headers=headers, timeout=60) as response:
                    if response.status == 200:
                        data = await response.json()
                        ai_reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                        if ai_reply:
                            text_msg = user_message if not photo_base64 else f"[Фото] {user_message}"
                            add_message_to_business_history(business_connection_id, client_chat_id, "user", text_msg)
                            add_message_to_business_history(business_connection_id, client_chat_id, "assistant", ai_reply)
                            increment_stat("total_messages")
                            return ai_reply
        except Exception as e:
            logging.warning(f"onlysq vision API error: {e}")

    if not _get_deepseek_key():
        return "Текстовый AI временно недоступен. Попробуй позже."

    ds_messages = _messages_to_deepseek_format(messages)
    ds_model = _deepseek_model(user_model)
    send = {"model": ds_model, "messages": ds_messages}
    headers = {"Authorization": f"Bearer {_get_deepseek_key()}", "Content-Type": "application/json"}
    url = DEEPSEEK_API_URL

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=send, headers=headers, timeout=60) as response:
                if response.status == 200:
                    data = await response.json()
                    ai_reply = data['choices'][0]['message']['content']

                    # Сохраняем в историю ЭТОГО клиента
                    text_msg = user_message if not photo_base64 else f"[Фото] {user_message}"
                    add_message_to_business_history(business_connection_id, client_chat_id, "user", text_msg)
                    add_message_to_business_history(business_connection_id, client_chat_id, "assistant", ai_reply)

                    # Обновляем статистику
                    increment_stat("total_messages")

                    return ai_reply
                else:
                    return "Сервис временно недоступен. Попробуй через пару минут."
    except asyncio.TimeoutError:
        return "Ответ слишком долго формируется. Попробуй отправить запрос ещё раз."
    except Exception as e:
        logging.error(f"Ошибка AI: {e}")
        return "Ошибка соединения с сервисом. Попробуй через минуту."

async def generate_image(user_id: int, prompt: str, model: str, enhanced_prompt: str = None) -> tuple:
    """Сгенерировать изображение. enhanced_prompt — уже улучшенный промпт от LLM."""
    if model == "pollinations-flux-free":
        clean_prompt = enhanced_prompt or build_image_prompt(prompt)
        clean_prompt = sanitize_user_input(clean_prompt, max_length=800)
        if not clean_prompt:
            return False, "Не получилось понять, что нарисовать. Попробуй описать подробнее."
        try:
            encoded_prompt = quote(clean_prompt, safe="")
            urls = [
                f"{FREE_IMAGE_API_URL}/{encoded_prompt}",
                f"https://pollinations.ai/p/{encoded_prompt}",
            ]
            retry_statuses = {429, 500, 502, 503, 504, 520, 522, 524, 530}
            # Для бесплатного API делаем несколько попыток с разными моделями.
            attempts = [
                {"model": "sana", "nologo": "true", "width": "1024", "height": "1024"},
                {"model": "turbo", "nologo": "true", "width": "1024", "height": "1024"},
                {"model": "zimage", "nologo": "true", "width": "1024", "height": "1024"},
            ]
            last_status = None
            async with aiohttp.ClientSession() as session:
                for base_url in urls:
                    for i, params in enumerate(attempts):
                        params = dict(params)
                        params["seed"] = str(random.randint(1, 10_000_000))
                        try:
                            async with session.get(base_url, params=params, timeout=90) as response:
                                content_type = response.headers.get("content-type", "")
                                if response.status == 200 and "image" in content_type:
                                    image_bytes = await response.read()
                                    if image_bytes and len(image_bytes) > 1000:
                                        increment_stat("total_messages")
                                        logging.info(f"Pollinations success: size={len(image_bytes)}, attempt={i+1}")
                                        return True, image_bytes
                                    last_status = 200
                                    logging.warning(f"Pollinations returned small/empty response: size={len(image_bytes) if image_bytes else 0}, content-type={content_type}")
                                elif response.status == 200:
                                    body = (await response.text())[:300]
                                    last_status = 200
                                    logging.warning(f"Pollinations returned non-image: content-type={content_type}, body={body}")
                                else:
                                    body = (await response.text())[:500]
                                    last_status = response.status
                                    logging.warning(
                                        f"Free image API error {response.status} on attempt {i + 1} ({base_url}): {body}"
                                    )
                        except Exception as req_e:
                            # Ошибка конкретного хоста/запроса: логируем и пробуем дальше.
                            last_status = 0
                            logging.warning(
                                f"Free image API request failed on attempt {i + 1} ({base_url}): {req_e}"
                            )

                        if i < len(attempts) - 1 and (last_status in retry_statuses or last_status in {0, 200}):
                            await asyncio.sleep(1.2 + i * 0.8)
                            continue
                        break

            if last_status:
                if last_status in retry_statuses or last_status == 0:
                    return False, "Сейчас много запросов — попробуй через 10–30 секунд."
                return False, "Не получилось нарисовать. Попробуй ещё раз или опиши по-другому."
            return False, "Картинка не пришла. Попробуй ещё раз."
        except asyncio.TimeoutError:
            return False, "Слишком долго рисовал. Попробуй ещё раз или опиши проще."
        except Exception as e:
            logging.error(f"Ошибка бесплатной генерации: {e}")
            return False, "Что-то пошло не так. Попробуй ещё раз."

    if not API_BEARER_TOKEN:
        return False, "Рисование картинок сейчас недоступно. Попробуй позже."

    prompt_clean = enhanced_prompt or build_image_prompt(prompt)
    prompt_clean = sanitize_user_input(prompt_clean, max_length=1500)
    if not prompt_clean:
        return False, "Не получилось понять, что нарисовать. Попробуй описать подробнее."

    headers = {"Authorization": f"Bearer {API_BEARER_TOKEN}", "Content-Type": "application/json"}

    # Пробуем ТОЛЬКО указанную модель (fallback между моделями делает generate_image_with_guard)
    logging.info(f"Image API request: model={model}, prompt={prompt_clean[:100]}...")
    try:
        async with aiohttp.ClientSession() as session:
            send = {"model": model, "prompt": prompt_clean, "n": 1}
            async with session.post(IMAGE_API_URL, json=send, headers=headers, timeout=90) as response:
                if response.status == 200:
                    data = await response.json()
                    if "files" in data and isinstance(data["files"], list) and len(data["files"]) > 0:
                        try:
                            image_bytes = base64.b64decode(data["files"][0])
                            increment_stat("total_messages")
                            logging.info(f"Image generated successfully: model={model}, size={len(image_bytes)}")
                            return True, image_bytes
                        except Exception:
                            return False, "Не получилось обработать картинку. Попробуй ещё раз."
                    logging.warning(f"Image API 200 but no files: model={model}, data_keys={list(data.keys())}")
                    return False, "Картинка не пришла. Попробуй ещё раз."

                body = (await response.text())[:500]
                logging.warning(f"Image API error {response.status} (model={model}): {body}")
                if response.status == 401:
                    return False, "Сервис временно недоступен. Попробуй позже."
                if response.status == 429:
                    return False, f"429 rate limit (model={model})"
                return False, "Не получилось нарисовать. Попробуй ещё раз или опиши по-другому."
    except asyncio.TimeoutError:
        logging.warning(f"Image API timeout: model={model}")
        return False, "Слишком долго рисовал. Попробуй ещё раз или опиши проще."
    except Exception as e:
        logging.error(f"Ошибка генерации: {e} | last_status={last_status} body={last_body}")
        return False, "Что-то пошло не так. Попробуй ещё раз."


async def transcribe_voice(voice_file_path: str) -> str:
    """Распознать голосовое сообщение через Google Speech Recognition"""
    if sr is None:
        logging.warning("Распознавание голоса недоступно: SpeechRecognition не установлен")
        return None

    wav_path = voice_file_path.replace('.ogg', '.wav')
    try:
        # Конвертируем OGG в WAV через ffmpeg
        process = await asyncio.create_subprocess_exec(
            'ffmpeg', '-i', voice_file_path, '-acodec', 'pcm_s16le',
            '-ar', '16000', '-ac', '1', wav_path, '-y',
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await process.communicate()

        # Используем speech_recognition
        recognizer = sr.Recognizer()

        with sr.AudioFile(wav_path) as source:
            audio_data = recognizer.record(source)
            # Google Speech API - бесплатный и точный
            text = recognizer.recognize_google(audio_data, language='ru-RU')

        return text

    except sr.UnknownValueError:
        logging.error("Google Speech Recognition не смог распознать речь")
        return None
    except sr.RequestError as e:
        logging.error(f"Ошибка Google Speech Recognition: {e}")
        return None
    except Exception as e:
        logging.error(f"Ошибка распознавания: {e}")
        return None
    finally:
        for temp_path in (wav_path, voice_file_path):
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception:
                pass


# ==================== MESSAGE HANDLERS ====================
def split_message(text: str, max_length: int = MAX_MESSAGE_LENGTH) -> list:
    """Разбить длинное сообщение"""
    if len(text) <= max_length:
        return [text]

    parts = []
    while text:
        if len(text) <= max_length:
            parts.append(text)
            break

        split_pos = text.rfind('\n', 0, max_length)
        if split_pos == -1:
            split_pos = text.rfind(' ', 0, max_length)
        if split_pos == -1:
            split_pos = max_length

        parts.append(text[:split_pos])
        text = text[split_pos:].lstrip()

    return parts

def markdown_to_html(text: str) -> str:
    """Конвертировать markdown в HTML"""
    source = text or ""
    link_placeholders = {}

    # 1) Сохраняем markdown-ссылки до escaping, чтобы корректно превратить их в <a>.
    def _store_markdown_link(match):
        label = match.group(1).strip()
        url = match.group(2).strip()
        token = f"__MD_LINK_{len(link_placeholders)}__"
        safe_url = html.escape(url, quote=True)
        safe_label = html.escape(label)
        link_placeholders[token] = f'<a href="{safe_url}">{safe_label}</a>'
        return token

    source = re.sub(r'\[([^\]\n]+)\]\((https?://[^\s)]+)\)', _store_markdown_link, source)

    escaped = html.escape(source)
    escaped = re.sub(r'(?m)^#{1,3}\s+(.+)$', r'<b>\1</b>', escaped)
    escaped = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', escaped)
    escaped = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<i>\1</i>', escaped)
    escaped = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', escaped)
    # После html.escape символ '>' превращается в '&gt;', учитываем это для цитат.
    escaped = re.sub(r'(?m)^\s*&gt;\s?(.*)$', r'<blockquote>\1</blockquote>', escaped)
    escaped = re.sub(r'(?m)^-\s+', '• ', escaped)

    # 2) Восстанавливаем markdown-ссылки в виде HTML-гиперссылок.
    for token, tag in link_placeholders.items():
        escaped = escaped.replace(token, tag)

    trailing_url_punct = ".,;:!?)]}>\"'"

    def _linkify_bare_url(match):
        raw_url = match.group(1)
        clean_url = raw_url.rstrip(trailing_url_punct)
        tail = raw_url[len(clean_url):]
        if not clean_url:
            return raw_url
        anchor = f'<a href="{html.escape(clean_url, quote=True)}">{html.escape(clean_url)}</a>'
        return f"{anchor}{html.escape(tail)}"

    # 3) Делаем bare URLs кликабельными.
    escaped = re.sub(
        r'(?<!["\'>])(https?://[^\s<]+)',
        _linkify_bare_url,
        escaped
    )
    return escaped

async def send_long_message(message: Message, text: str, feedback_query: str = ""):
    """Отправить длинное сообщение с опциональными кнопками фидбэка."""
    raw_text = text  # сохраняем для фидбэка
    text = markdown_to_html(text)

    parts = split_message(text)
    last_idx = len(parts) - 1

    sent_msg = None
    for i, part in enumerate(parts):
        if i > 0:
            await asyncio.sleep(0.5)
        is_last = (i == last_idx)
        reply_markup = None
        if is_last and feedback_query:
            # Placeholder msg_id — обновим после отправки
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="👍", callback_data="fb_up_0"),
                    InlineKeyboardButton(text="👎", callback_data="fb_down_0"),
                ]
            ])
        try:
            sent_msg = await message.answer(part, parse_mode="HTML", reply_markup=reply_markup)
        except:
            sent_msg = await message.answer(part, reply_markup=reply_markup)

    # Обновляем callback_data с реальным message_id
    if feedback_query and sent_msg:
        msg_id = str(sent_msg.message_id)
        _pending_feedback[msg_id] = {
            "query": feedback_query,
            "response": raw_text[:500],
        }
        try:
            await sent_msg.edit_reply_markup(
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [
                        InlineKeyboardButton(text="👍", callback_data=f"fb_up_{msg_id}"),
                        InlineKeyboardButton(text="👎", callback_data=f"fb_down_{msg_id}"),
                    ]
                ])
            )
        except Exception:
            pass


@dp.message(F.photo)
async def handle_photo(message: Message, state: FSMContext):
    """Обработка фото"""
    current_state = await state.get_state()
    if current_state:
        return

    user_id = message.from_user.id

    # Проверка черного списка
    if is_blacklisted(user_id):
        return

    # Проверка подписки на каналы
    if user_id not in ADMIN_IDS and get_required_channels():
        if not await check_channel_subscription(user_id):
            await send_channel_subscription_message(message.chat.id, user_id)
            return

    if not can_make_any_request(user_id):
        increment_stat("paywall_shown")
        await send_system_message(
            chat_id=message.chat.id,
            text=get_free_trial_paywall_text(user_id),
            reply_markup=get_subscription_keyboard(user_id)
        )
        return

    user_text = message.caption if message.caption else "Что изображено на этом фото?"

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        photo = message.photo[-1]
        file = await bot.get_file(photo.file_id)
        photo_bytes = await bot.download_file(file.file_path)
        photo_base64 = base64.b64encode(photo_bytes.read()).decode('utf-8')

        if is_photo_edit_request(user_text):
            image_model = pick_image_model_for_prompt(user_id, user_text)
            if not image_model:
                await message.answer("Рисование картинок сейчас недоступно. Попробуй позже.")
                return

            ok_limit, limit_msg = try_consume_image_generation_limit(user_id)
            if not ok_limit:
                await message.answer(limit_msg)
                return

            await bot.send_chat_action(message.chat.id, "upload_photo")

            # Берем краткий контекст фото через текущий vision-путь, затем собираем edit-промпт.
            context_prompt = (
                "Кратко опиши фото для дальнейшего редактирования: главный объект, фон, цвета, ракурс, свет. "
                "Формат: 1 строка до 220 символов."
            )
            source_context = await get_ai_response(user_id, context_prompt, photo_base64)
            if isinstance(source_context, str) and ("временно недоступен" in source_context or "Попробуй позже" in source_context):
                source_context = ""

            edit_prompt = build_photo_edit_prompt(user_text, source_context or "")
            success, result = await generate_image_with_guard(user_id, edit_prompt, image_model)
            if success:
                photo_out = (
                    BufferedInputFile(result, filename="edited_image.jpg")
                    if isinstance(result, (bytes, bytearray))
                    else result
                )
                edit_caption = f"{text_emoji('image')} <b>{image_model}</b>\nРедактирование выполнено"
                if not has_active_subscription(user_id):
                    edit_caption += get_message("image_success_free_cta", img_daily=IMAGE_DAILY_LIMIT_PRO)
                await message.answer_photo(
                    photo=photo_out,
                    caption=edit_caption,
                    parse_mode="HTML"
                )
                if not has_active_subscription(user_id):
                    consume_free_trial(user_id, is_image=True)
                    await maybe_send_trial_reminder_1_left(message.chat.id, user_id)
            else:
                await message.answer(
                    f"{result}\nПопробуй описать точнее — что изменить (фон, цвет, стиль)."
                )
            return

        ai_response = await get_ai_response(user_id, user_text, photo_base64)
        _append_request_log(user_id, "photo", user_text, ai_response)
        await send_long_message(message, ai_response, feedback_query=user_text)
        if not has_active_subscription(user_id):
            consume_free_trial(user_id)
            await maybe_send_soft_paywall(message.chat.id, user_id)
            await maybe_send_trial_reminder_1_left(message.chat.id, user_id)
    except Exception as e:
        logging.error(f"Ошибка фото: {e}")
        await message.answer("Не получилось разобрать фото. Попробуй отправить другое.")


@dp.message(F.voice)
async def handle_voice(message: Message, state: FSMContext):
    """Обработка голосовых сообщений"""
    current_state = await state.get_state()
    if current_state:
        return

    user_id = message.from_user.id

    # Проверка черного списка
    if is_blacklisted(user_id):
        return

    # Проверка подписки на каналы
    if user_id not in ADMIN_IDS and get_required_channels():
        if not await check_channel_subscription(user_id):
            await send_channel_subscription_message(message.chat.id, user_id)
            return

    if not can_make_any_request(user_id):
        increment_stat("paywall_shown")
        await send_system_message(
            chat_id=message.chat.id,
            text=get_free_trial_paywall_text(user_id),
            reply_markup=get_subscription_keyboard(user_id)
        )
        return

    await bot.send_chat_action(message.chat.id, "typing")

    try:
        # Скачиваем голосовое сообщение
        voice = message.voice
        file = await bot.get_file(voice.file_id)

        # Создаем временный файл
        voice_path = f"/tmp/voice_{user_id}_{voice.file_id}.ogg"
        await bot.download_file(file.file_path, voice_path)

        # Распознаем голос
        transcribed_text = await transcribe_voice(voice_path)

        if not transcribed_text:
            await message.answer("Не получилось разобрать голосовое. Попробуй записать ещё раз — говори чётче.")
            return

        if is_image_generation_request(transcribed_text):
            image_model = pick_image_model_for_prompt(user_id, transcribed_text)
            if not image_model:
                await message.answer("Рисование картинок сейчас недоступно. Попробуй позже.")
                return
            ok_limit, limit_msg = try_consume_image_generation_limit(user_id)
            if not ok_limit:
                await message.answer(limit_msg)
                return
            await bot.send_chat_action(message.chat.id, "upload_photo")
            success, result = await generate_image_with_guard(user_id, transcribed_text, image_model)
            if success:
                photo = (
                    BufferedInputFile(result, filename="generated_image.jpg")
                    if isinstance(result, (bytes, bytearray))
                    else result
                )
                voice_caption = f"{text_emoji('image')} <b>{image_model}</b>\n{text_emoji('note')} {transcribed_text[:80]}{'...' if len(transcribed_text) > 80 else ''}"
                if not has_active_subscription(user_id):
                    voice_caption += get_message("image_success_free_cta", img_daily=IMAGE_DAILY_LIMIT_PRO)
                await message.answer_photo(
                    photo=photo,
                    caption=voice_caption,
                    parse_mode="HTML"
                )
                if not has_active_subscription(user_id):
                    consume_free_trial(user_id, is_image=True)
                    await maybe_send_trial_reminder_1_left(message.chat.id, user_id)
            else:
                await message.answer(result)
            return

        ai_response = await get_ai_response(user_id, transcribed_text)
        _append_request_log(user_id, "voice", transcribed_text, ai_response)
        await send_long_message(message, ai_response, feedback_query=transcribed_text)
        if not has_active_subscription(user_id):
            consume_free_trial(user_id)
            await maybe_send_soft_paywall(message.chat.id, user_id)
            await maybe_send_trial_reminder_1_left(message.chat.id, user_id)

    except Exception as e:
        logging.error(f"Ошибка голоса: {e}")
        await message.answer("Не получилось обработать голосовое. Попробуй ещё раз.")


@dp.message(F.text)
async def handle_message(message: Message, state: FSMContext):
    """Обработка текстовых сообщений"""
    current_state = await state.get_state()
    if current_state:
        return

    if message.text.startswith('/'):
        return

    user_id = message.from_user.id

    # Трекинг активности + статистика
    try:
        ud = load_user_data(user_id)
        ud["last_active"] = datetime.now().isoformat()
        today_str = datetime.now().strftime("%Y-%m-%d")
        days_set = ud.get("days_active_set", [])
        if today_str not in days_set:
            days_set.append(today_str)
            # Храним только последние 365 дней
            if len(days_set) > 365:
                days_set = days_set[-365:]
            ud["days_active_set"] = days_set
        ud["total_requests"] = ud.get("total_requests", 0) + 1
        category = _categorize_request(message.text)
        cats = ud.get("categories", {})
        cats[category] = cats.get(category, 0) + 1
        ud["categories"] = cats
        # Сохраним имя для pro_welcome
        if message.from_user.first_name:
            ud["first_name"] = message.from_user.first_name
        save_user_data(user_id, ud)
    except Exception:
        pass

    # Проверка черного списка
    if is_blacklisted(user_id):
        return

    # Проверка подписки на каналы
    if user_id not in ADMIN_IDS and get_required_channels():
        if not await check_channel_subscription(user_id):
            await send_channel_subscription_message(message.chat.id, user_id)
            return

    if not can_make_any_request(user_id):
        increment_stat("paywall_shown")
        await send_system_message(
            chat_id=message.chat.id,
            text=get_free_trial_paywall_text(user_id),
            reply_markup=get_subscription_keyboard(user_id)
        )
        return

    # URL-саммари (Feature 6): если сообщение содержит URL — суммируем страницу
    detected_url = extract_url(message.text)
    if detected_url and len(message.text.strip()) < len(detected_url) + 50:
        # Сообщение в основном является ссылкой
        if not has_active_subscription(user_id) and user_id not in ADMIN_IDS:
            if not can_make_request(user_id, is_image=False):
                increment_stat("paywall_shown")
                await send_system_message(
                    chat_id=message.chat.id,
                    text=get_free_trial_paywall_text(user_id),
                    reply_markup=get_subscription_keyboard(user_id)
                )
                return

        progress_msg = await message.answer("📎 Читаю страницу...")
        await bot.send_chat_action(message.chat.id, "typing")
        summary = await fetch_and_summarize_url(detected_url, user_id)
        try:
            await progress_msg.delete()
        except Exception:
            pass
        _append_request_log(user_id, "text", message.text, summary, "url_summary")
        await send_long_message(message, summary, feedback_query=message.text)
        if not has_active_subscription(user_id):
            consume_free_trial(user_id)
            await maybe_send_soft_paywall(message.chat.id, user_id, response_len=len(summary), user_query=message.text)
            await maybe_send_trial_reminder_1_left(message.chat.id, user_id)
        return

    if is_photo_edit_request(message.text):
        await message.answer("Для редактирования отправь фото с подписью — что именно нужно изменить.")
        return

    if is_image_generation_request(message.text):
        image_model = pick_image_model_for_prompt(user_id, message.text)
        if not image_model:
            await message.answer("Рисование картинок сейчас недоступно. Попробуй позже.")
            return

        ok_limit, limit_msg = try_consume_image_generation_limit(user_id)
        if not ok_limit:
            await message.answer(limit_msg)
            return

        # Отправляем прогресс-сообщение
        progress_msg = await message.answer(
            get_message("image_generation_progress"),
            parse_mode="HTML"
        )
        await bot.send_chat_action(message.chat.id, "upload_photo")

        success, result = await generate_image_with_guard(user_id, message.text, image_model)
        _append_request_log(user_id, "image", message.text, "success" if success else str(result)[:200], image_model)

        # Удаляем прогресс-сообщение
        try:
            await progress_msg.delete()
        except Exception:
            pass

        if success:
            # Трекинг total_images
            try:
                ud = load_user_data(user_id)
                ud["total_images"] = ud.get("total_images", 0) + 1
                save_user_data(user_id, ud)
            except Exception:
                pass
            try:
                photo = (
                    BufferedInputFile(result, filename="generated_image.jpg")
                    if isinstance(result, (bytes, bytearray))
                    else result
                )
                caption = f"{text_emoji('image')} <b>{image_model}</b>"
                prompt_preview = message.text[:80] + ('...' if len(message.text) > 80 else '')
                caption += f"\n{text_emoji('note')} {prompt_preview}"
                if not has_active_subscription(user_id):
                    caption += get_message("image_success_free_cta", img_daily=IMAGE_DAILY_LIMIT_PRO)
                await message.answer_photo(
                    photo=photo,
                    caption=caption,
                    parse_mode="HTML"
                )
                if not has_active_subscription(user_id):
                    consume_free_trial(user_id, is_image=True)
                    await maybe_send_trial_reminder_1_left(message.chat.id, user_id)
            except Exception as e:
                await message.answer("Не получилось отправить картинку. Попробуй ещё раз.")
        else:
            await message.answer(result)
        return

    # Проверяем текстовый лимит перед запросом к AI
    if not has_active_subscription(user_id) and user_id not in ADMIN_IDS:
        if not can_make_request(user_id, is_image=False):
            increment_stat("paywall_shown")
            await send_system_message(
                chat_id=message.chat.id,
                text=get_free_trial_paywall_text(user_id),
                reply_markup=get_subscription_keyboard(user_id)
            )
            return

    await bot.send_chat_action(message.chat.id, "typing")
    ai_response = await get_ai_response(user_id, message.text)
    _append_request_log(user_id, "text", message.text, ai_response, load_user_data(user_id).get("model", DEFAULT_MODEL))
    await send_long_message(message, ai_response, feedback_query=message.text)
    if not has_active_subscription(user_id):
        consume_free_trial(user_id)
        await maybe_send_soft_paywall(message.chat.id, user_id, response_len=len(ai_response), user_query=message.text)
        await maybe_send_trial_reminder_1_left(message.chat.id, user_id)


async def maybe_send_soft_paywall(chat_id: int, user_id: int, response_len: int = 0, user_query: str = ""):
    """Мягкий пейвол — показать оставшиеся запросы и кнопку PRO после бесплатного ответа."""
    if user_id in ADMIN_IDS or has_active_subscription(user_id):
        return
    total_rem = get_total_free_remaining(user_id)
    if total_rem <= 0:
        return

    eff_stars, _ = get_effective_price(user_id)
    first = is_first_purchase(user_id)

    # Контекстные апселлы в зависимости от типа запроса
    query_lower = user_query.lower() if user_query else ""

    if response_len > 800:
        wow_texts = [
            "Полезно? С PRO — так каждый день, без ограничений.",
            "Представь, что такие ответы — без лимита.",
            "Это только начало. С PRO — спрашивай сколько хочешь.",
        ]
        text = f"<i>{random.choice(wow_texts)}</i>\n"
    elif any(w in query_lower for w in ["меню", "рецепт", "приготов", "блюд"]):
        text = "<i>С PRO — новое меню каждую неделю за секунды.</i>\n"
    elif any(w in query_lower for w in ["письм", "напиши", "текст", "поздравл", "пост"]):
        text = "<i>С PRO — любые тексты без ограничений.</i>\n"
    elif any(w in query_lower for w in ["подар", "совет", "посоветуй", "помоги"]):
        text = "<i>С PRO — советы по любому вопросу 24/7.</i>\n"
    elif any(w in query_lower for w in ["ребён", "детск", "школ", "урок"]):
        text = "<i>С PRO — помощник для всей семьи каждый день.</i>\n"
    else:
        text = ""

    text += f"<i>Осталось бесплатно: {total_rem}</i>"
    if first:
        text += f"  |  <b>PRO — {eff_stars} ⭐</b>"

    buttons = [[make_inline_button(
        f"🔥 PRO за {eff_stars} ⭐" if first else "Подключить PRO",
        callback_data="subscription",
        button_key="subscription",
        style="success"
    )]]
    try:
        await send_system_message(
            chat_id=chat_id,
            text=text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons),
            parse_mode="HTML"
        )
    except Exception:
        pass


# ==================== TRIAL REMINDERS ====================
async def maybe_send_trial_reminder_1_left(chat_id: int, user_id: int):
    """Отправить напоминание, когда бесплатные запросы почти закончились."""
    if user_id in ADMIN_IDS or has_active_subscription(user_id):
        return
    text_rem, img_rem = get_free_trial_remaining(user_id)
    total_rem = text_rem + img_rem
    if total_rem > 2 or total_rem == 0:
        return
    if not should_send_reminder(user_id, "trial_1_left"):
        return
    try:
        await send_system_message(
            chat_id=chat_id,
            text=get_message("trial_reminder_1_left", price=get_subscription_price()),
            reply_markup=get_subscription_keyboard(user_id),
            parse_mode="HTML"
        )
        set_last_reminder(user_id, "trial_1_left")
    except Exception as e:
        logging.warning(f"Не удалось отправить напоминание trial_1_left для {user_id}: {e}")


async def check_trial_reminders():
    """Напоминания для trial-пользователей: 1ч, 24ч, 3 дня после первого использования."""
    while True:
        try:
            users = get_all_users()
            now = datetime.now()

            for user in users:
                user_id = user["user_id"]

                if user_id in ADMIN_IDS or is_blacklisted(user_id):
                    continue
                if has_active_subscription(user_id):
                    continue

                first_use = user.get("first_use_time")
                if not first_use:
                    continue

                try:
                    first_dt = datetime.fromisoformat(first_use)
                except (ValueError, TypeError):
                    continue

                hours_since = (now - first_dt).total_seconds() / 3600

                # Напоминание через 1 час
                if 0.9 < hours_since < 1.5:
                    if should_send_reminder(user_id, "trial_1h"):
                        try:
                            eff_stars, _ = get_effective_price(user_id)
                            full_price = get_subscription_price()
                            await send_system_message(
                                chat_id=user_id,
                                text=get_message("trial_reminder_1h",
                                    discount_price=eff_stars,
                                    full_price=full_price),
                                reply_markup=get_subscription_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "trial_1h")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить напоминание trial_1h для {user_id}: {e}")

                # Напоминание через 24 часа
                elif 23 < hours_since < 25:
                    if should_send_reminder(user_id, "trial_24h"):
                        try:
                            eff_stars, _ = get_effective_price(user_id)
                            await send_system_message(
                                chat_id=user_id,
                                text=get_message("trial_reminder_24h", price=eff_stars),
                                reply_markup=get_subscription_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "trial_24h")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить напоминание trial_24h для {user_id}: {e}")

                # Напоминание через 3 дня
                elif 71 < hours_since < 73:
                    if should_send_reminder(user_id, "trial_3d"):
                        try:
                            eff_stars, _ = get_effective_price(user_id)
                            await send_system_message(
                                chat_id=user_id,
                                text=get_message("trial_reminder_3d", price=eff_stars),
                                reply_markup=get_subscription_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "trial_3d")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить напоминание trial_3d для {user_id}: {e}")

        except Exception as e:
            logging.error(f"Ошибка проверки trial-напоминаний: {e}")

        await asyncio.sleep(1800)


# ==================== SUBSCRIPTION REMINDER ====================
async def check_subscription_reminders():
    """Проверка и отправка напоминаний о подписке"""
    while True:
        try:
            users = get_all_users()
            now = datetime.now()

            for user in users:
                user_id = user["user_id"]

                # Пропускаем админов и заблокированных
                if user_id in ADMIN_IDS or is_blacklisted(user_id):
                    continue

                sub_end = get_subscription_end(user_id)
                if not sub_end:
                    continue

                time_left = sub_end - now
                hours_left = time_left.total_seconds() / 3600

                # Напоминание за 24 часа
                if 23 < hours_left < 25:
                    if should_send_reminder(user_id, "24h"):
                        try:
                            await send_system_message(
                                chat_id=user_id,
                                text=(
                                    "<b>Подписка истекает через 24 часа</b>\n\n"
                                    "Продли сейчас — и не потеряй доступ к безлимитным запросам и генерации картинок."
                                ),
                                reply_markup=get_subscription_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "24h")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить напоминание 24ч для {user_id}: {e}")

                # Напоминание за 2 часа
                elif 1.5 < hours_left < 2.5:
                    if should_send_reminder(user_id, "2h"):
                        try:
                            await send_system_message(
                                chat_id=user_id,
                                text=(
                                    "<b>Подписка заканчивается через 2 часа!</b>\n\n"
                                    "После истечения запросы будут ограничены.\nПродли PRO одним нажатием."
                                ),
                                reply_markup=get_subscription_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "2h")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить напоминание 2ч для {user_id}: {e}")

                # === Win-back: напоминания ПОСЛЕ истечения подписки ===
                # 1 час после истечения
                elif -1.5 < hours_left < -0.5:
                    if should_send_reminder(user_id, "expired_1h"):
                        try:
                            eff_stars, _ = get_effective_price(user_id)
                            await send_system_message(
                                chat_id=user_id,
                                text=get_message("expired_1h"),
                                reply_markup=get_subscription_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "expired_1h")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить expired_1h для {user_id}: {e}")

                # 24 часа после истечения
                elif -25 < hours_left < -23:
                    if should_send_reminder(user_id, "expired_24h"):
                        try:
                            eff_stars, _ = get_effective_price(user_id)
                            req_count = get_user_request_count(user_id, sub_end.isoformat() if sub_end else None)
                            # Если не нашли за период подписки, берём общее число
                            if req_count == 0:
                                req_count = get_user_request_count(user_id)
                            await send_system_message(
                                chat_id=user_id,
                                text=get_message("expired_24h", request_count=req_count, price=eff_stars),
                                reply_markup=get_subscription_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "expired_24h")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить expired_24h для {user_id}: {e}")

                # 3 дня после истечения
                elif -73 < hours_left < -71:
                    if should_send_reminder(user_id, "expired_3d"):
                        try:
                            eff_stars, _ = get_effective_price(user_id)
                            await send_system_message(
                                chat_id=user_id,
                                text=get_message("expired_3d", price=eff_stars),
                                reply_markup=get_subscription_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "expired_3d")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить expired_3d для {user_id}: {e}")

        except Exception as e:
            logging.error(f"Ошибка проверки напоминаний: {e}")

        # Проверяем каждые 30 минут
        await asyncio.sleep(1800)


# ==================== INACTIVITY REMINDERS ====================
INACTIVE_EXAMPLES = [
    ("Составь меню на неделю", "Что подарить коллеге на ДР?"),
    ("Напиши поздравление свекрови", "Посоветуй фильм на вечер"),
    ("Объясни ребёнку, почему идёт дождь", "Напиши отзыв на товар"),
    ("Составь список покупок на неделю", "Помоги написать резюме"),
    ("Что приготовить из того, что в холодильнике?", "Напиши пост для соцсети"),
]


async def check_inactivity_reminders():
    """Напоминания неактивным пользователям: 7 дней и 14 дней."""
    while True:
        try:
            users = get_all_users()
            now = datetime.now()

            for user in users:
                user_id = user["user_id"]

                if user_id in ADMIN_IDS or is_blacklisted(user_id):
                    continue
                if has_active_subscription(user_id):
                    continue

                last_active = user.get("last_active") or user.get("first_use_time")
                if not last_active:
                    continue

                try:
                    last_dt = datetime.fromisoformat(last_active)
                except (ValueError, TypeError):
                    continue

                days_inactive = (now - last_dt).total_seconds() / 86400

                # 7 дней неактивности
                if 6.5 < days_inactive < 8:
                    if should_send_reminder(user_id, "inactive_7d"):
                        try:
                            ex1, ex2 = random.choice(INACTIVE_EXAMPLES)
                            await send_system_message(
                                chat_id=user_id,
                                text=get_message("inactive_7d", example1=ex1, example2=ex2),
                                reply_markup=get_main_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "inactive_7d")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить inactive_7d для {user_id}: {e}")

                # 14 дней неактивности
                elif 13.5 < days_inactive < 15:
                    if should_send_reminder(user_id, "inactive_14d"):
                        try:
                            eff_stars, _ = get_effective_price(user_id)
                            await send_system_message(
                                chat_id=user_id,
                                text=get_message("inactive_14d"),
                                reply_markup=get_main_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "inactive_14d")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить inactive_14d для {user_id}: {e}")

        except Exception as e:
            logging.error(f"Ошибка проверки inactivity-напоминаний: {e}")

        await asyncio.sleep(3600)  # Каждый час


async def check_pending_invoices():
    """Проверка ожидающих инвойсов CryptoBot"""
    while True:
        try:
            invoices = load_pending_invoices()

            for invoice_id, data in list(invoices.items()):
                user_id = data["user_id"]

                # Проверяем статус
                invoice_status = await check_crypto_invoice(invoice_id)

                if invoice_status:
                    if invoice_status["status"] == "paid":
                        # Активируем подписку
                        grant_subscription(user_id, days=30)
                        mark_as_paid(user_id)

                        # Обновляем статистику
                        price_usd = get_subscription_price_usd()
                        increment_stat("total_payments")
                        increment_stat("total_revenue_usd", price_usd)
                        _append_payment_log(user_id, price_usd, "USD", "crypto_bot")

                        # Уведомляем пользователя (wow-момент)
                        try:
                            await send_pro_welcome(user_id, user_id)
                        except Exception as e:
                            logging.warning(f"Не удалось уведомить пользователя {user_id}: {e}")

                        # Удаляем инвойс из ожидающих
                        remove_pending_invoice(invoice_id)
                        logging.info(f"✅ Подписка активирована для {user_id} через CryptoBot")

                    elif invoice_status["status"] in ["expired", "cancelled"]:
                        # Удаляем просроченный инвойс
                        remove_pending_invoice(invoice_id)
                        logging.info(f"⏰ Инвойс {invoice_id} истек или отменен")

                await asyncio.sleep(1)  # Задержка между проверками инвойсов

        except Exception as e:
            logging.error(f"Ошибка проверки инвойсов: {e}")

        # Проверяем каждые 30 секунд
        await asyncio.sleep(30)

# ==================== MAIN ====================
async def main():
    global business_connections
    business_connections = load_business_connections()

    logging.info("🚀 AI Chat Bot запущен!")

    # Устанавливаем команды
    await set_bot_commands()

    # Запускаем проверку напоминаний
    asyncio.create_task(check_subscription_reminders())
    asyncio.create_task(check_trial_reminders())

    # Запускаем проверку CryptoBot инвойсов
    asyncio.create_task(check_pending_invoices())

    # Напоминания неактивным пользователям
    asyncio.create_task(check_inactivity_reminders())

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 Бот остановлен")
