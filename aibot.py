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
FREE_TRIAL_LIMIT = int(os.getenv("FREE_TRIAL_LIMIT", "5"))
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
    # Model navigation
    "model_item": "5936143551854285132",    # 📊
    "nav_prev": "5960671702059848143",      # ⬅️
    "nav_next": "5773626993010546707",      # ▶️
    # Subscription/payment
    "extend_stars": "6028338546736107668",  # ⭐️
    "extend_crypto": "5776023601941582822", # 💎
    "buy_stars": "5778613750688911681",     # 🪙
    "buy_crypto": "5776023601941582822",    # 💎
    "pay_crypto": "5776023601941582822",    # 💎
    # Common actions
    "cancel": "6030757850274336631",        # ❌
    "confirm_clear": "5774022692642492953", # ✅
    "required_channel": "6021418126061605425",  # 📢
    "check_channels": "5843596438373667352",    # ✅️
    "contact_admin": "6030784887093464891",     # 💬
    # Style presets
    "preset_serious": "6030537007350944596",    # 🛡
    "preset_neutral": "6041748912102968702",    # 😐
    "preset_funny": "6043996047582170909",      # 😀
    "preset_friend": "5774034804450267485",     # 🙂
    "thinking_edit": "6039779802741739617",      # ✏️
    "thinking_delete": "6039522349517115015"     # 🗑
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
        "Стиль ответа: серьезный и деловой. "
        "Минимум эмоций, четкая структура, точные формулировки, без разговорного сленга."
    ),
    "neutral": (
        "Стиль ответа: нейтральный и дружелюбно-деловой. "
        "Понятно и спокойно, без лишней эмоциональности."
    ),
    "funny": (
        "Стиль ответа: веселый и легкий. "
        "Добавляй уместный юмор, но сохраняй пользу и корректность."
    ),
    "friend": (
        "Стиль ответа: как близкий друг. "
        "Тепло, просто и поддерживающе, можно немного разговорного стиля."
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
    "serious": "Сухо и по делу: минимум эмоций, чёткая структура, без сленга. Для рабочих задач и формального тона.",
    "neutral": "Спокойно и универсально: понятно, дружелюбно, без лишней эмоциональности. Подходит для большинства запросов.",
    "funny": "С юмором и легко: уместные шутки, но с пользой и без перегибов. Идеально для креатива и развлечения.",
    "friend": "Как близкий друг: тепло, просто, с поддержкой и разговорным стилем. Для неформального общения."
}

START_EXAMPLES = [
    "«Сделай 5 идей смешной открытки про понедельник для коллег»",
    "«Придумай короткий текст для поздравления друга с днем рождения»",
    "«Сгенерируй идею мем-картинки про удаленку и дедлайны»",
    "«Объясни простыми словами, как составить план на неделю»",
    "«Придумай подпись к фото для сторис в веселом стиле»",
    "«Напиши короткий пост для соцсетей про выходные»",
    "«Нарисуй смешную картинку: кот в костюме офисного работника»",
    "«Помоги сформулировать отказ от встречи вежливо и коротко»",
    "«Идеи для смешного стикера про утро понедельника»",
]

RESPONSE_STYLE_SYSTEM_PROMPT = (
    "Ты — полезный ассистент для массового пользователя Telegram. "
    "Отвечай коротко, точно, без воды, без повторов, без лишних вступлений. "
    "Всегда используй аккуратный Telegram-формат: короткие абзацы, списки, уместные выделения. "
    "Базовая структура: 1 короткий вывод, затем 2-6 пунктов по сути. "
    "Если запрос простой — ответь в 1-3 предложениях без списка. "
    "Разрешенная разметка: **жирный**, *курсив*, `код`, цитаты >, списки через '-'. "
    "Не используй таблицы и markdown-ссылки вида [текст](url). "
    "Если просят источники/видео/ссылки — давай прямые URL (https://...). "
    "Если уместно, добавляй 1 короткую цитату-акцент в формате '> ...'. "
    "В конце ответа можно добавить 1 короткий доп-вопрос с предложением следующего шага "
    "(например: программа, видео, шаблон, чек-лист), но только если это действительно полезно теме. "
    "Не выдумывай факты; если данных не хватает, коротко уточни."
)

RESPONSE_STYLE_HARD_GUARD_PROMPT = (
    "КРИТИЧНО: независимо от остального контекста сохраняй стиль Telegram — чисто, четко, по делу, "
    "без словесного мусора. Используй выделения осознанно: важное — **жирным**, термины — *курсивом*, "
    "при необходимости цитаты через >."
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

# Пути к файлам
DATA_DIR = "data"
USERS_DIR = os.path.join(DATA_DIR, "users")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
BLACKLIST_FILE = os.path.join(DATA_DIR, "blacklist.json")
PENDING_INVOICES_FILE = os.path.join(DATA_DIR, "pending_invoices.json")
BUSINESS_CONNECTIONS_FILE = os.path.join(DATA_DIR, "business_connections.json")

# Создаем директории
os.makedirs(USERS_DIR, exist_ok=True)

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
    """Заменить обычные emoji в тексте на custom emoji-теги (если есть маппинг)."""
    if not text:
        return text

    normalized = text
    if EMOJI_TO_CUSTOM_ID:
        for emoji_char in sorted(EMOJI_TO_CUSTOM_ID.keys(), key=len, reverse=True):
            if emoji_char in normalized:
                normalized = normalized.replace(emoji_char, _unicode_to_custom_emoji_tag(emoji_char))
    return normalized


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

    tg_emoji_re = re.compile(r'\s*<tg-emoji[^>]*>.*?</tg-emoji>\s*')
    cleaned = []
    for i, line in enumerate(lines):
        if i != header_idx:
            line = tg_emoji_re.sub('', line)
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
        "стикер"
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


def build_image_prompt(user_text: str) -> str:
    """
    Нормализовать пользовательский запрос в более строгий prompt для генерации изображения.
    Это снижает шанс подмены главного объекта (например, кот -> собака).
    """
    src = sanitize_user_input(user_text, max_length=1500)
    if not src:
        return ""

    core = src.strip()
    # Убираем частые "обертки" запроса, оставляя суть сцены.
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
        r'(?i)\b(картинку|картинку|картинка|изображение|фото|арт|image|picture)\b',
        '',
        core
    )
    core = re.sub(r'\s+', ' ', core).strip(" ,.!?-")
    if not core:
        core = src

    core_l = core.lower()
    animal_words = (
        "кот", "кошка", "кошк", "cat", "kitten",
        "собак", "dog", "puppy",
        "птиц", "bird", "лошад", "horse", "медвед", "bear",
        "животн", "animal"
    )
    has_animal = any(w in core_l for w in animal_words)

    strict_prompt = (
        f"USER REQUEST (literal): {core}. "
        "Follow the user request exactly and literally. "
        "Build ONE coherent scene from the request. "
        "Keep all explicitly requested entities, attributes and relations (object, color, material, position, style). "
        "Do not replace the main subject with a different object/animal/person even if it seems more aesthetic. "
        "Do not add unrelated dominant subjects. "
        "If request is ambiguous, prefer the most literal interpretation."
    )

    if not has_animal:
        strict_prompt += " No animals or pets unless explicitly requested."

    strict_prompt += " NEGATIVE: text, logo, watermark, captions."
    return strict_prompt


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


async def generate_image_with_guard(user_id: int, prompt: str, model: str, max_attempts: int = 3) -> tuple:
    """
    Генерация с авто-проверкой:
    если пользователь не просил животных, но на картинке есть животное, делаем автоповтор.
    """
    animal_allowed = prompt_requests_animals(prompt)
    last_error = "✖️ Не удалось сгенерировать изображение."

    # План моделей: сначала текущая, затем альтернативы.
    t = (prompt or "").lower()
    object_scene = any(x in t for x in ("обои", "рулон", "валик", "ролик", "краск", "стол", "предмет", "product"))
    enabled_models = set(get_enabled_models())
    if object_scene and not animal_allowed:
        preferred_order = ["lucid-origin", "phoenix-1.0", "flux-2-dev", "flux", "grok-2-image", "pollinations-flux-free"]
    else:
        preferred_order = ["flux", "flux-2-dev", "grok-2-image", "phoenix-1.0", "lucid-origin", "pollinations-flux-free"]

    model_plan = [model]
    for m in preferred_order:
        if m in IMAGE_MODELS and m in enabled_models and m not in model_plan:
            model_plan.append(m)

    for model_idx, current_model in enumerate(model_plan):
        current_prompt = prompt
        for attempt in range(1, max_attempts + 1):
            success, result = await generate_image(user_id, current_prompt, current_model)
            if not success:
                last_error = result
                # Если модель явно недоступна/лимитирована — сразу пробуем следующую модель.
                lower_err = str(result).lower()
                if any(x in lower_err for x in ("429", "rate limit", "bad argument", "credits", "spending limit")):
                    break
                continue

            # Если результат не bytes (например URL), пропускаем валидацию.
            if not isinstance(result, (bytes, bytearray)):
                return True, result

            if animal_allowed:
                return True, result

            contains_animal = await image_contains_animal(bytes(result))
            if contains_animal is False:
                return True, result
            if contains_animal is None:
                # Валидация недоступна — не блокируем пользователя.
                return True, result

            # contains_animal == True -> усиливаем негатив и пробуем еще.
            current_prompt = _image_retry_prompt_no_animals(prompt, attempt)
            last_error = "✖️ Модель упорно добавляет лишние объекты. Попробуйте уточнить запрос."

        # Переход на следующую модель после серии неудач.
        if model_idx < len(model_plan) - 1:
            logging.warning(f"Switching image model fallback: {current_model} -> {model_plan[model_idx + 1]}")

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

    # По умолчанию предпочитаем onlysq image-модели.
    for candidate in ("flux", "flux-2-dev", "grok-2-image", "phoenix-1.0", "lucid-origin", "pollinations-flux-free"):
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
        for candidate in ("lucid-origin", "phoenix-1.0", "flux-2-dev", "flux"):
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
    text = normalize_system_text(text)
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
    text = normalize_system_text(text)
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
    "p-flux",
    "grok-2-image",
    "flux-2-dev",
    "phoenix-1.0",
    "lucid-origin",
    "flux",
    "pollinations-flux-free"
]

IMAGE_MODELS = {
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


async def _bot_send_message_with_custom_emoji(self, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    if _is_html_parse_mode(parse_mode):
        if "text" in kwargs and isinstance(kwargs["text"], str):
            kwargs["text"] = normalize_html_outgoing_text(kwargs["text"])
        elif len(args) >= 2 and isinstance(args[1], str):
            args = list(args)
            args[1] = normalize_html_outgoing_text(args[1])
            args = tuple(args)
    return await _original_bot_send_message(self, *args, **kwargs)


async def _message_answer_with_custom_emoji(self, text, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    if _is_html_parse_mode(parse_mode) and isinstance(text, str):
        text = normalize_html_outgoing_text(text)
    return await _original_message_answer(self, text, *args, **kwargs)


async def _bot_send_photo_with_custom_emoji(self, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    if _is_html_parse_mode(parse_mode) and isinstance(kwargs.get("caption"), str):
        kwargs["caption"] = normalize_html_outgoing_text(kwargs["caption"])
    return await _original_bot_send_photo(self, *args, **kwargs)


async def _bot_send_video_with_custom_emoji(self, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    if _is_html_parse_mode(parse_mode) and isinstance(kwargs.get("caption"), str):
        kwargs["caption"] = normalize_html_outgoing_text(kwargs["caption"])
    return await _original_bot_send_video(self, *args, **kwargs)


async def _bot_send_animation_with_custom_emoji(self, *args, **kwargs):
    parse_mode = kwargs.get("parse_mode")
    if _is_html_parse_mode(parse_mode) and isinstance(kwargs.get("caption"), str):
        kwargs["caption"] = normalize_html_outgoing_text(kwargs["caption"])
    return await _original_bot_send_animation(self, *args, **kwargs)


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
        "Специальное предложение! Всего {price_stars} Stars / {price_usd} USD за 30 дней, вместо 1000."
    ),
    "paywall_proof": "Присоединяйся к {active_subs} пользователям с PRO.\n\n",
    "welcome_intro": (
        "{greeting} Сэкономь часы на рутине — напиши, что нужно, и получи готовый результат."
    ),
    "welcome_free_requests": "<b>Бесплатных запросов:</b> {remaining}",
    "welcome_example_intro": "<b>Например, напиши:</b>",
    "welcome_subscribe_cta": "<b>Для использования без ограничений оформите подписку PRO.</b>",
    "channel_subscribe": (
        "📺 <b>Подпишись на канал — и получи доступ к боту</b>\n\n"
        "Советы по AI, обновления бота и эксклюзивные промпты.\n\n"
        "{proof}"
        "👇 Нажми на канал ниже и подпишись:"
    ),
    "channel_proof": "Уже {subs_count} пользователей в боте.\n\n",
    "subscription_outcome": "Получи доступ ко всем возможностям — без ограничений.",
    "subscription_proof": "{active_subs} пользователей уже выбрали PRO.\n\n",
    "subscription_benefits": (
        "• <b>Все модели нейросети</b> — от быстрых до самых умных\n"
        "• <b>Генерация картинок</b> — мемы, иллюстрации по тексту\n"
        "• <b>Стиль ответа</b> — серьёзный, нейтральный, весёлый или «как друг»\n"
        "• <b>Фото и голос</b> — отправляй скриншоты и голосовые"
    ),
    "subscription_price_anchor": "<s>15 USD</s> — сейчас <b>{price_stars} Stars</b> или <b>{price_usd} USD</b> за 30 дней",
    "trial_reminder_1_left": (
        "💡 <b>Остался 1 бесплатный запрос!</b>\n\n"
        "Попробуй что-то крутое — например, генерацию картинки по описанию.\n"
        "После этого оформи PRO и продолжай без ограничений."
    ),
    "trial_reminder_24h": (
        "👋 <b>Как тебе бот?</b>\n\n"
        "Если понравилось — оформи PRO и получи доступ ко всем моделям "
        "и генерации картинок без ограничений."
    ),
}


def load_messages() -> dict:
    """Загрузить сообщения из файла (для A/B тестов)"""
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logging.warning(f"Ошибка загрузки messages.json: {e}")
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
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "subscription_price": 100,  # Цена в звездах
        "subscription_price_usd": 5,  # Цена в USD для CryptoBot
        "system_gif_urls": [],
        "button_emoji_pack": DEFAULT_BUTTON_EMOJI_PACK.copy()
    }


def save_config(config):
    """Сохранить конфигурацию"""
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def get_subscription_price():
    """Получить цену подписки в звездах"""
    config = load_config()
    return config.get("subscription_price", 100)


def get_subscription_price_usd():
    """Получить цену подписки в USD"""
    config = load_config()
    return config.get("subscription_price_usd", 5)


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
    "flux"
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
        for candidate in ("flux", "flux-2-dev", "grok-2-image", "phoenix-1.0", "lucid-origin", "pollinations-flux-free"):
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
def load_stats():
    """Загрузить статистику"""
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "total_users": 0,
        "total_starts": 0,
        "total_messages": 0,
        "total_payments": 0,
        "total_revenue": 0,
        "total_revenue_usd": 0.0,
        "paywall_shown": 0,
        "subscription_clicked": 0,
    }


def save_stats(stats):
    """Сохранить статистику"""
    with open(STATS_FILE, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)


def increment_stat(key: str, value=1):
    """Увеличить значение статистики (value: int или float)"""
    stats = load_stats()
    stats[key] = stats.get(key, 0) + value
    save_stats(stats)

# ==================== РАБОТА С БИЗНЕС-ПОДКЛЮЧЕНИЯМИ ====================
def load_business_connections():
    """Загрузить бизнес-подключения из файла"""
    if os.path.exists(BUSINESS_CONNECTIONS_FILE):
        try:
            with open(BUSINESS_CONNECTIONS_FILE, 'r', encoding='utf-8') as f:
                connections = json.load(f)
                logging.info(f"✅ Загружено {len(connections)} бизнес-подключений")
                return connections
        except Exception as e:
            logging.error(f"❌ Ошибка загрузки подключений: {e}")
            return {}
    return {}


def save_business_connections(connections):
    """Сохранить бизнес-подключения в файл"""
    try:
        with open(BUSINESS_CONNECTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(connections, f, ensure_ascii=False, indent=2)
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
    """Загрузить данные пользователя"""
    path = get_user_data_path(user_id)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "user_id": user_id,
        "model": DEFAULT_MODEL,
        "subscription_end": None,
        "created_at": datetime.now().isoformat(),
        "username": None,
        "full_name": None
    }


def save_user_data(user_id: int, data: dict):
    """Сохранить данные пользователя"""
    path = get_user_data_path(user_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_chat_history(user_id: int) -> list:
    """Загрузить историю чата"""
    path = get_user_history_path(user_id)
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_chat_history(user_id: int, history: list):
    """Сохранить историю чата"""
    path = get_user_history_path(user_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


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
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_business_chat_history(business_connection_id: str, client_chat_id: int, history: list):
    """Сохранить историю бизнес-чата"""
    path = get_business_chat_history_path(business_connection_id, client_chat_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


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
    """Сколько бесплатных запросов уже использовано"""
    user_data = load_user_data(user_id)
    return int(user_data.get("free_trial_used") or 0)


def consume_free_trial(user_id: int, is_image: bool = False):
    """Списать 1 бесплатный запрос. Сохраняет first_use_time при первом использовании."""
    user_data = load_user_data(user_id)
    used = get_free_trial_used(user_id)
    if used == 0:
        user_data["first_use_time"] = datetime.now().isoformat()
    user_data["free_trial_used"] = used + 1
    if is_image:
        user_data["image_trial_used"] = user_data.get("image_trial_used", 0) + 1
    save_user_data(user_id, user_data)


def can_make_request(user_id: int) -> bool:
    """Может ли пользователь сделать запрос (подписка или бесплатный триал)"""
    if user_id in ADMIN_IDS:
        return True
    if has_active_subscription(user_id):
        return True
    return get_free_trial_used(user_id) < FREE_TRIAL_LIMIT


def get_free_trial_paywall_text(user_id: int = None) -> str:
    """Текст пейвола при исчерпании бесплатного триала."""
    price_stars = get_subscription_price()
    price_usd = get_subscription_price_usd()
    active_subs = len(get_users_with_active_subscription())
    proof = get_message("paywall_proof", active_subs=active_subs) if active_subs > 0 else ""
    return get_message(
        "paywall",
        proof=proof,
        price_stars=price_stars,
        price_usd=price_usd
    )


def try_consume_image_generation_limit(user_id: int) -> tuple:
    """
    Проверить и списать 1 генерацию изображения из лимита.
    Лимит действует для платной подписки: в день и в месяц.
    """
    if user_id in ADMIN_IDS:
        return True, ""

    if not has_active_subscription(user_id):
        if get_free_trial_used(user_id) < FREE_TRIAL_LIMIT:
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
        return False, f"✖️ Достигнут дневной лимит генераций ({IMAGE_DAILY_LIMIT_PRO}). Попробуйте завтра."
    if monthly_count >= IMAGE_MONTHLY_LIMIT_PRO:
        return False, f"✖️ Достигнут месячный лимит генераций ({IMAGE_MONTHLY_LIMIT_PRO})."

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
    if os.path.exists(BLACKLIST_FILE):
        with open(BLACKLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []


def save_blacklist(blacklist: list):
    """Сохранить черный список"""
    with open(BLACKLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(blacklist, f, ensure_ascii=False, indent=2)


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
    if os.path.exists(PENDING_INVOICES_FILE):
        with open(PENDING_INVOICES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_pending_invoices(invoices: dict):
    """Сохранить ожидающие инвойсы"""
    with open(PENDING_INVOICES_FILE, 'w', encoding='utf-8') as f:
        json.dump(invoices, f, ensure_ascii=False, indent=2)


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
    user_data["last_reminder"] = {
        "type": reminder_type,
        "time": datetime.now().isoformat()
    }
    save_user_data(user_id, user_data)


def should_send_reminder(user_id: int, reminder_type: str) -> bool:
    """Проверить, нужно ли отправлять напоминание"""
    last_reminder = get_last_reminder(user_id)

    if not last_reminder:
        return True

    if last_reminder.get("type") != reminder_type:
        return True

    last_time = datetime.fromisoformat(last_reminder["time"])
    time_diff = datetime.now() - last_time

    # Не отправлять чаще чем раз в 12 часов для одного типа напоминания
    if time_diff.total_seconds() < 12 * 3600:
        return False

    return True


# ==================== КЛАВИАТУРЫ ====================
def get_main_keyboard():
    """Главная клавиатура"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            make_inline_button("Стиль ответа", callback_data="thinking_menu", button_key="thinking", style="primary")
        ],
        [
            make_inline_button("Подписка PRO", callback_data="subscription", button_key="subscription", style="success"),
            make_inline_button("Настройки", callback_data="settings", button_key="info")
        ]
    ])


def get_models_keyboard(page: int, user_id: int):
    """Клавиатура выбора моделей"""
    has_sub = has_active_subscription(user_id)

    # Получаем только включенные модели
    enabled_models = get_enabled_models()
    available = [m for m in AVAILABLE_MODELS if m in enabled_models]

    start_idx = page * MODELS_PER_PAGE
    end_idx = start_idx + MODELS_PER_PAGE
    models_page = available[start_idx:end_idx]

    buttons = []
    for model in models_page:
        display_name = f"Картинки: {model}" if model in IMAGE_MODELS else model
        callback_data = f"setmodel_{model}" if has_sub else f"needsub_{model}"
        buttons.append([make_inline_button(display_name, callback_data=callback_data, button_key="model_item")])

    # Навигация
    nav_buttons = []
    if page > 0:
        nav_buttons.append(make_inline_button("Назад", callback_data=f"models_{page - 1}", button_key="nav_prev"))
    if end_idx < len(available):
        nav_buttons.append(make_inline_button("Далее", callback_data=f"models_{page + 1}", button_key="nav_next"))

    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([make_inline_button("Главная", callback_data="main_menu", button_key="home", style="primary")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_subscription_keyboard(user_id: int):
    """Клавиатура подписки"""
    has_sub = has_active_subscription(user_id)
    price_stars = get_subscription_price()
    price_usd = get_subscription_price_usd()

    buttons = []

    if has_sub:
        # Если подписка активна - показываем кнопки продления
        buttons.append([make_inline_button(
            f"Продлить звездами ({price_stars})",
            callback_data="extend_stars",
            button_key="extend_stars",
            style="success"
        )])
        buttons.append([make_inline_button(
            f"Продлить через CryptoBot ({price_usd} USD)",
            callback_data="extend_crypto",
            button_key="extend_crypto",
            style="primary"
        )])
    else:
        buttons.append([make_inline_button(
            f"Купить звездами ({price_stars})",
            callback_data="buy_stars",
            button_key="buy_stars",
            style="success"
        )])
        buttons.append([make_inline_button(
            f"Купить через CryptoBot ({price_usd} USD)",
            callback_data="buy_crypto",
            button_key="buy_crypto",
            style="primary"
        )])

    buttons.append([make_inline_button("Главная", callback_data="main_menu", button_key="home", style="primary")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard(callback_data: str = "admin_menu"):
    """Клавиатура отмены"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [make_inline_button("Отмена", callback_data=callback_data, button_key="cancel", style="danger")]
    ])


def get_admin_keyboard():
    """Клавиатура админ-панели"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Аналитика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="💰 Тарифы", callback_data="admin_price")],
        [InlineKeyboardButton(text="🧬 Доступные модели", callback_data="admin_models_0")],
        [InlineKeyboardButton(text="✅ Выдать подписку", callback_data="admin_grant")],
        [InlineKeyboardButton(text="⛔ Забрать подписку", callback_data="admin_revoke")],
        [InlineKeyboardButton(text="📢 Массовая рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="👥 База пользователей", callback_data="admin_users_0")],
        [InlineKeyboardButton(text="📺 Каналы обяз. подписки", callback_data="admin_channels")],
        [InlineKeyboardButton(text="🚫 Blacklist", callback_data="admin_blacklist")],
        [InlineKeyboardButton(text="🖼️ Медиа-оформление", callback_data="admin_media")]
    ])


def get_broadcast_confirm_keyboard():
    """Клавиатура подтверждения рассылки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✔️ Отправить", callback_data="broadcast_confirm")],
        [InlineKeyboardButton(text="✖️ Отмена", callback_data="admin_menu")]
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
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="clear", description="🗑️ Очистить историю чата")
    ]

    # Команды для админов (включая /admin)
    admin_commands = [
        BotCommand(command="start", description="🏠 Главное меню"),
        BotCommand(command="clear", description="🗑️ Очистить историю чата"),
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

        if not can_make_request(bot_owner_id):
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
                "✖️ Для редактирования пришлите фото с подписью, что нужно изменить.",
                business_connection_id=business_connection_id
            )
            return

        should_generate_image = user_model in IMAGE_MODELS or is_image_generation_request(message.text or "")
        if should_generate_image:
            image_model = user_model if user_model in IMAGE_MODELS else pick_image_model_for_prompt(bot_owner_id, message.text or "")
            if not image_model:
                await bot.send_message(
                    message.chat.id,
                    "✖️ Сейчас нет доступной модели для генерации изображений.",
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

        if not can_make_request(bot_owner_id):
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
                    "✖️ Сейчас нет доступной модели для генерации изображений.",
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
            if isinstance(source_context, str) and source_context.startswith("✖️"):
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
                    f"{result}\nПопробуйте уточнить правку (например: стиль, фон, цвет, ракурс).",
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

        if not can_make_request(bot_owner_id):
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
                "✖️ Не удалось распознать",
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

    # Обновляем данные пользователя
    user_data["username"] = message.from_user.username
    user_data["full_name"] = message.from_user.full_name
    save_user_data(user_id, user_data)

    # Статистика: каждый /start
    increment_stat("total_starts")
    # Новый пользователь (первый раз)
    if not os.path.exists(get_user_history_path(user_id)):
        increment_stat("total_users")

    # Проверяем подписку на каналы (админы не проверяются)
    if user_id not in ADMIN_IDS:
        channels = get_required_channels()
        if channels and not await check_channel_subscription(user_id):
            await send_channel_subscription_message(message.chat.id, user_id)
            return

    await send_start_message(message.chat.id, user_id, rotate_example=True)


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
            text=f"📢 {ch['name']}",
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
    """Отправить приветственное сообщение (формат как на скриншоте)."""
    has_sub = has_active_subscription(user_id)
    start_example = get_start_example(user_id, rotate=rotate_example)
    user_data = load_user_data(user_id)
    first_name = (user_data.get("full_name") or "").split()[0] if user_data.get("full_name") else None

    start_title_emoji = (
        text_emoji("wave")
        or text_emoji("star")
        or button_emoji_tag("subscription")
        or button_emoji_tag("info")
    )
    greeting_text = f"Привет, {first_name}!" if first_name else "Привет!"
    greeting = get_message("welcome_intro", greeting=greeting_text)
    # 1. Приветствие — жирным
    text = f"{start_title_emoji} <b>{greeting}</b>\n\n"

    # 2. Бесплатных запросов: 5 — «Бесплатных запросов» жирным, число обычным
    if not has_sub:
        remaining = FREE_TRIAL_LIMIT - get_free_trial_used(user_id)
        if remaining > 0:
            text += f"{get_message('welcome_free_requests', remaining=remaining)}\n\n"

    # 3. Например, напиши: — жирным
    text += f"{get_message('welcome_example_intro')}\n\n"

    # 4. Пример — цитата (blockquote)
    text += f"<blockquote>{start_example}</blockquote>\n\n"

    # 5. CTA — жирным
    if not has_sub:
        text += get_message("welcome_subscribe_cta")

    if await send_section_media_message(
        chat_id=chat_id,
        text=text,
        reply_markup=get_main_keyboard(),
        section="start",
        parse_mode="HTML"
    ):
        return

    start_media = get_start_media()
    if start_media:
        media_type = start_media.get("type")
        file_id = start_media.get("file_id")

        try:
            if media_type == "photo":
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="HTML"
                )
            elif media_type == "video":
                await bot.send_video(
                    chat_id=chat_id,
                    video=file_id,
                    caption=text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="HTML"
                )
            elif media_type == "animation":
                await bot.send_animation(
                    chat_id=chat_id,
                    animation=file_id,
                    caption=text,
                    reply_markup=get_main_keyboard(),
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(chat_id=chat_id, text=text, reply_markup=get_main_keyboard(), parse_mode="HTML")
        except Exception as e:
            logging.error(f"Ошибка отправки медиа: {e}")
            await send_system_message(chat_id=chat_id, text=text, reply_markup=get_main_keyboard(), parse_mode="HTML")
    else:
        await send_system_message(chat_id=chat_id, text=text, reply_markup=get_main_keyboard(), parse_mode="HTML")


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
        await callback.answer("✖️ Вы не подписались на все каналы!", show_alert=True)


@dp.message(Command("clear"))
async def cmd_clear(message: Message):
    """Команда /clear"""
    await send_system_message(
        chat_id=message.chat.id,
        text=(
            "🗑️ <b>Очистить историю чата?</b>\n\n"
            "Все сообщения будут удалены безвозвратно."
        ),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [make_inline_button(text="✔️ Да, очистить", callback_data="confirm_clear", button_key="confirm_clear", style="danger")],
            [make_inline_button(text="✖️ Отмена", callback_data="cancel_clear", button_key="cancel", style="primary")]
        ]),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "confirm_clear")
async def callback_confirm_clear(callback: CallbackQuery):
    """Подтверждение очистки истории"""
    clear_chat_history(callback.from_user.id)
    await safe_edit_or_send(callback, "✔️ История чата очищена!")
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
            await callback.answer("✖️ Подпишитесь на каналы!", show_alert=True)
            return

    try:
        parts = callback.data.split("_")
        page = int(parts[1]) if len(parts) > 1 else 0

        user_data = load_user_data(user_id)
        current_model = user_data.get("model", DEFAULT_MODEL)
        model_type = (
            f"{text_emoji('image')} Генерация изображений"
            if current_model in IMAGE_MODELS
            else f"{text_emoji('chat')} Текстовый чат"
        )

        text = (
            f"{text_emoji('models')} <b>Модели</b>\n\n"
            f"{text_emoji('robot')} <b>Текущая модель:</b> <code>{current_model}</code>\n"
            f"<b>Тип:</b> {model_type}\n\n"
            "Бот сам выбирает текст или картинку по вашему запросу.\n"
            "Тут вы меняете базовую модель по умолчанию."
        )

        keyboard = get_models_keyboard(page, user_id)

        # Удаляем предыдущее сообщение и отправляем новое напрямую (без GIF)
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
                text="⚠️ Ошибка загрузки моделей. Попробуйте позже.",
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
        await callback.answer("✖️ Для смены модели требуется подписка!", show_alert=True)
        return

    user_data = load_user_data(user_id)
    user_data["model"] = model
    save_user_data(user_id, user_data)

    model_type = (
        f"{text_emoji('image')} Генерация изображений"
        if model in IMAGE_MODELS
        else f"{text_emoji('chat')} Текстовый чат"
    )

    await callback.answer(f"✔️ Модель изменена на {model}!")

    await safe_edit_or_send(
        callback,
        f"{text_emoji('check')} <b>Модель изменена!</b>\n\n"
        f"{text_emoji('robot')} <b>Новая модель:</b> <code>{model}</code>\n"
        f"<b>Тип:</b> {model_type}",
        InlineKeyboardMarkup(inline_keyboard=[
            [make_inline_button("Модели", callback_data="models_0", button_key="models", style="primary")],
            [make_inline_button("Главная", callback_data="main_menu", button_key="home", style="primary")]
        ])
    )


@dp.callback_query(F.data.startswith("needsub_"))
async def callback_need_subscription(callback: CallbackQuery):
    """Нужна подписка для смены модели"""
    user_id = callback.from_user.id
    user_data = load_user_data(user_id)
    user_data["needsub_clicked"] = True
    save_user_data(user_id, user_data)
    await callback.answer(
        "⭐ Для смены модели необходимо оформить подписку!",
        show_alert=True
    )


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
        text = f"{text_emoji('star')} <b>Подписка активна!</b>\n\n"
        text += f"<b>Действует до:</b> {sub_end.strftime('%d.%m.%Y %H:%M')}\n\n"
        time_left = sub_end - datetime.now()
        days = time_left.days
        hours = time_left.seconds // 3600
        minutes = (time_left.seconds % 3600) // 60
        text += f"<b>Осталось:</b> {days}д {hours}ч {minutes}м\n"
        text += f"Лимит генерации картинок: {IMAGE_DAILY_LIMIT_PRO}/день, {IMAGE_MONTHLY_LIMIT_PRO}/месяц"
    else:
        price_stars = get_subscription_price()
        price_usd = get_subscription_price_usd()
        active_subs = len(get_users_with_active_subscription())
        proof = get_message("subscription_proof", active_subs=active_subs) if active_subs > 0 else ""
        user_data = load_user_data(user_id)
        needsub = user_data.get("needsub_clicked")
        text = f"{text_emoji('star')} <b>Подписка PRO</b>\n\n"
        if needsub:
            text += f"<b>Разблокируй все модели — оформи PRO!</b>\n\n"
        text += f"<b>{get_message('subscription_outcome')}</b>\n\n"
        text += proof
        text += f"<blockquote>{get_message('subscription_benefits')}</blockquote>\n\n"
        text += get_message("subscription_price_anchor", price_stars=price_stars, price_usd=price_usd)

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


@dp.callback_query(F.data == "buy_stars")
async def callback_buy_stars(callback: CallbackQuery):
    """Покупка подписки за звезды"""
    user_id = callback.from_user.id
    increment_stat("subscription_clicked")
    price = get_subscription_price()

    await bot.send_invoice(
        chat_id=user_id,
        title="Подписка на AI Chat Bot",
        description="Подписка на 30 дней. Доступ ко всем моделям AI.",
        payload=f"subscription_{user_id}",
        currency="XTR",
        prices=[LabeledPrice(label="Подписка (30 дней)", amount=price)]
    )
    await callback.answer()


@dp.callback_query(F.data == "buy_crypto")
async def callback_buy_crypto(callback: CallbackQuery):
    """Покупка подписки через CryptoBot"""
    user_id = callback.from_user.id
    increment_stat("subscription_clicked")
    price_usd = get_subscription_price_usd()

    await safe_edit_or_send(callback, "💎 <b>Создание инвойса...</b>", parse_mode="HTML")

    invoice_data = await create_crypto_invoice(user_id, price_usd)

    if invoice_data:
        # Сохраняем инвойс для отслеживания
        add_pending_invoice(invoice_data["invoice_id"], user_id)

        await safe_edit_or_send(
            callback,
            (
                "💎 <b>Оплата через CryptoBot</b>\n\n"
                f"💰 Сумма: {price_usd} USD\n"
                "⏰ Ссылка действительна 1 час\n\n"
                "Нажмите кнопку ниже для оплаты:"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [make_inline_button("Оплатить", url=invoice_data["bot_invoice_url"], button_key="pay_crypto", style="success")],
                [make_inline_button("Главная", callback_data="main_menu", button_key="home", style="primary")]
            ]),
            parse_mode="HTML"
        )
    else:
        await safe_edit_or_send(
            callback,
            "✖️ Ошибка создания инвойса. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )

    await callback.answer()


@dp.callback_query(F.data == "extend_stars")
async def callback_extend_stars(callback: CallbackQuery):
    """Продление подписки за звезды"""
    user_id = callback.from_user.id
    price = get_subscription_price()

    await bot.send_invoice(
        chat_id=user_id,
        title="Продление подписки AI Chat Bot",
        description="Продление подписки на 30 дней.",
        payload=f"extend_{user_id}",
        currency="XTR",
        prices=[LabeledPrice(label="Продление (30 дней)", amount=price)]
    )
    await callback.answer()


@dp.callback_query(F.data == "extend_crypto")
async def callback_extend_crypto(callback: CallbackQuery):
    """Продление подписки через CryptoBot"""
    user_id = callback.from_user.id
    price_usd = get_subscription_price_usd()

    await safe_edit_or_send(callback, "💎 <b>Создание инвойса...</b>", parse_mode="HTML")

    invoice_data = await create_crypto_invoice(user_id, price_usd)

    if invoice_data:
        # Сохраняем инвойс для отслеживания
        add_pending_invoice(invoice_data["invoice_id"], user_id)

        await safe_edit_or_send(
            callback,
            (
                "💎 <b>Продление через CryptoBot</b>\n\n"
                f"💰 Сумма: {price_usd} USD\n"
                "⏰ Ссылка действительна 1 час\n\n"
                "Нажмите кнопку ниже для оплаты:"
            ),
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [make_inline_button("Оплатить", url=invoice_data["bot_invoice_url"], button_key="pay_crypto", style="success")],
                [make_inline_button("Главная", callback_data="main_menu", button_key="home", style="primary")]
            ]),
            parse_mode="HTML"
        )
    else:
        await safe_edit_or_send(
            callback,
            "✖️ Ошибка создания инвойса. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )

    await callback.answer()


@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    """Обработка предварительного запроса оплаты"""
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)


@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    """Обработка успешной оплаты"""
    user_id = message.from_user.id

    # Выдаем подписку
    grant_subscription(user_id, days=30)

    # Обновляем статистику
    price = get_subscription_price()
    increment_stat("total_payments")
    increment_stat("total_revenue", price)

    sub_end = get_subscription_end(user_id)

    await send_system_message(
        chat_id=message.chat.id,
        text=(
            "🎉 <b>Оплата прошла успешно!</b>\n\n"
            f"⭐ Подписка активирована до: {sub_end.strftime('%d.%m.%Y %H:%M')}\n\n"
            "Теперь вы можете использовать все функции бота!"
        ),
        reply_markup=get_main_keyboard(),
        parse_mode="HTML"
    )


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
        f"👥 <b>Уникальных пользователей:</b> {stats.get('total_users', 0)}\n"
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
        f"🏷️ <b>Текущая цена:</b> {price} ⭐ / {get_subscription_price_usd()} USD"
    )

    await safe_edit_or_send(
        callback, text,
        InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
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
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_models_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_models_{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])

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
        nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_models_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_models_{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])

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
            [InlineKeyboardButton(text="⭐ Звезды", callback_data="price_stars")],
            [InlineKeyboardButton(text="💎 CryptoBot", callback_data="price_crypto")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
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
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
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
            nav_buttons.append(InlineKeyboardButton(text="◀️", callback_data=f"admin_users_{page - 1}"))
        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton(text="▶️", callback_data=f"admin_users_{page + 1}"))
    if nav_buttons:
        buttons.append(nav_buttons)

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])

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
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_users_0")]
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

    start_status = "✔️" if start_media else "✖️"
    channel_status = "✔️" if channel_media else "✖️"

    buttons = [
        [InlineKeyboardButton(text=f"🏠 /start {start_status}", callback_data="media_start")],
        [InlineKeyboardButton(text=f"📺 Подписка на канал {channel_status}", callback_data="media_channel")]
    ]

    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])

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
        buttons.append([InlineKeyboardButton(text="🗑️ Удалить", callback_data="media_start_delete")])

    buttons.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="admin_media")])

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
        buttons.append([InlineKeyboardButton(text="🗑️ Удалить", callback_data="media_channel_delete")])

    buttons.append([InlineKeyboardButton(text="✖️ Отмена", callback_data="admin_media")])

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
    text = (
        f"{text_emoji('info')} <b>Настройки</b>\n\n"
        f"<b>Текущая модель:</b> <code>{current_model}</code> ({model_mode})\n"
        "Бот сам выбирает режим (текст/картинка) по вашему запросу.\n\n"
        "<b>Возможности:</b>\n"
        "<blockquote>"
        "• Генерация изображений\n"
        "• Анализ фото\n"
        "• Голосовые сообщения\n"
        "• Настройка стиля общения"
        "</blockquote>"
    )

    # Извлекаем username без @
    admin_username = ADMIN_USERNAME.lstrip('@')

    buttons = [
        [make_inline_button(text="Модели AI", callback_data="models_0", button_key="models", style="primary")],
        [make_inline_button(text="Связаться", url=f"https://t.me/{admin_username}", button_key="contact_admin", style="primary")],
        [make_inline_button(text="Главная", callback_data="main_menu", button_key="home", style="primary")]
    ]
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
            buttons.append([InlineKeyboardButton(
                text=f"✖️ {ch['name']}",
                callback_data=f"delchannel_{ch['id']}"
            )])

    buttons.append([InlineKeyboardButton(text="➕ Добавить канал", callback_data="add_channel")])
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")])

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
            [InlineKeyboardButton(text="➕ Заблокировать", callback_data="blacklist_add")],
            [InlineKeyboardButton(text="➖ Разблокировать", callback_data="blacklist_remove")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_menu")]
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
            await callback.answer("✖️ Подпишитесь на каналы!", show_alert=True)
            return

    current_pref = get_thinking_preference(user_id)
    current_preset = get_response_style_preset(user_id)
    preset_human = STYLE_PRESET_LABELS.get(current_preset, "Нейтральный")
    preset_desc = STYLE_PRESET_DESCRIPTIONS.get(current_preset, "")
    preset_block = (
        f"<b>Стиль ответа</b>\n"
        "Выберите, как ИИ будет отвечать:\n"
        "• <b>Серьезный</b> — коротко и по делу\n"
        "• <b>Нейтральный</b> — спокойно и универсально\n"
        "• <b>Веселый</b> — легко, с уместным юмором\n"
        "• <b>Друг</b> — просто и по-человечески\n\n"
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
                f"{text_emoji('style')} <b>Мышление</b>\n\n"
                f"{preset_block}\n"
                "<b>JSON конфиг загружен</b>\n"
                f"Секций: {len(top_keys)}\n"
                f"Параметров: {total_params}\n"
                f"📝 Ключи: <code>{keys_display}</code>"
            )
        except:
            # Обычный текст
            pref_display = f"<blockquote>{current_pref[:200]}{'...' if len(current_pref) > 200 else ''}</blockquote>"
            text = (
                f"{text_emoji('style')} <b>Мышление</b>\n\n"
                f"{preset_block}\n"
                "<b>Текущие предпочтения:</b>\n"
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
            [make_inline_button("Главная", callback_data="main_menu", button_key="home", style="primary")]
        ]
    else:
        text = (
            f"{text_emoji('style')} <b>Мышление</b>\n\n"
            f"{preset_block}\n"
            "<blockquote>Хотите тоньше настроить стиль?\n"
            "Нажмите «Настроить» и отправьте:\n"
            "• обычный текст (например: «пиши кратко и просто»)</blockquote>"
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
            [make_inline_button("Главная", callback_data="main_menu", button_key="home", style="primary")]
        ]

    # Проверяем подписку
    if not has_active_subscription(user_id):
        buttons = [
            [make_inline_button("Оформить подписку", callback_data="subscription", button_key="subscription", style="success")],
            [make_inline_button("Главная", callback_data="main_menu", button_key="home", style="primary")]
        ]
        text = (
            f"{text_emoji('style')} <b>Мышление</b>\n\n"
            f"{preset_block}\n"
            "Для настройки мышления необходима подписка."
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
        await callback.answer("⭐ Для смены стиля ответа нужна подписка PRO", show_alert=True)
        return

    if preset not in STYLE_PRESET_PROMPTS:
        await callback.answer("✖️ Неизвестный пресет", show_alert=True)
        return

    set_response_style_preset(user_id, preset)
    await callback_thinking_menu(callback)


@dp.callback_query(F.data == "thinking_edit")
async def callback_thinking_edit(callback: CallbackQuery, state: FSMContext):
    """Редактирование предпочтений мышления"""
    user_id = callback.from_user.id

    if not has_active_subscription(user_id):
        await callback.answer("⭐ Необходима подписка!", show_alert=True)
        return

    await safe_edit_or_send(
        callback,
        "⚙️ <b>Настройка мышления</b>\n\n"
        "Отправьте настройки в одном из форматов:\n\n"
        "<b>Текст:</b>\n"
        "<i>«общайся со мной как друг, пиши с маленькой буквы, используй эмодзи»</i>\n\n"
        "<b>JSON:</b>\n"
        "<code>{\n"
        '  "tone": "friendly",\n'
        '  "style": "informal",\n'
        '  "lowercase": true,\n'
        '  "emoji": true,\n'
        '  "personality": "веселый помощник",\n'
        '  "response_length": "short"\n'
        "}</code>",
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
            "✖️ Отправьте текстовое сообщение:",
            reply_markup=get_cancel_keyboard("thinking_menu")
        )
        return

    preference = message.text.strip()

    if len(preference) < 5:
        await message.answer(
            "✖️ Слишком короткое описание. Попробуйте подробнее:",
            reply_markup=get_cancel_keyboard("thinking_menu")
        )
        return

    if len(preference) > 10000:
        await message.answer(
            "✖️ Слишком длинный конфиг (макс. 10000 символов). Сократите:",
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
                f"✖️ Ошибка в JSON:\n<code>{str(e)}</code>\n\n"
                "Проверьте синтаксис и попробуйте снова:",
                reply_markup=get_cancel_keyboard("thinking_menu"),
                parse_mode="HTML"
            )
            return
        except ValueError as e:
            await message.answer(
                f"✖️ {str(e)}\n\nПопробуйте снова:",
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
            "✔️ <b>JSON конфиг сохранён!</b>\n\n"
            f"📦 Секций: {len(top_keys)}\n"
            f"🔑 Ключи: {keys_display}\n\n"
            "ИИ будет использовать эти настройки при общении.",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "✔️ <b>Предпочтения сохранены!</b>\n\n"
            "ИИ будет учитывать ваши пожелания при общении.",
            reply_markup=get_main_keyboard(),
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
            "✖️ Отправьте файл формата .json",
            reply_markup=get_cancel_keyboard("thinking_menu")
        )
        return

    # Проверяем размер файла (макс 1 МБ)
    if message.document.file_size > 1024 * 1024:
        await message.answer(
            "✖️ Файл слишком большой (макс. 1 МБ)",
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
            "✔️ <b>JSON конфиг загружен из файла!</b>\n\n"
            f"📦 Секций: {len(top_keys)}\n"
            f"🔑 Ключи: {keys_display}\n\n"
            "ИИ будет использовать эти настройки при общении.",
            reply_markup=get_main_keyboard(),
            parse_mode="HTML"
        )

        await state.clear()

    except json.JSONDecodeError as e:
        await message.answer(
            f"✖️ Ошибка в JSON файле:\n<code>{str(e)}</code>\n\n"
            "Проверьте синтаксис и попробуйте снова:",
            reply_markup=get_cancel_keyboard("thinking_menu"),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Ошибка загрузки JSON: {e}")
        await message.answer(
            f"✖️ Ошибка: {str(e)}",
            reply_markup=get_cancel_keyboard("thinking_menu")
        )

@dp.callback_query(F.data == "thinking_delete")
async def callback_thinking_delete(callback: CallbackQuery):
    """Удаление предпочтений мышления"""
    user_id = callback.from_user.id

    set_thinking_preference(user_id, None)

    await safe_edit_or_send(
        callback,
        "✔️ Предпочтения удалены!\n\n"
        "ИИ будет общаться в стандартном режиме.",
        get_main_keyboard()
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
            return "✖️ Не настроен DEEPSEEK_API_KEY. Текстовые ответы работают только через DeepSeek."

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
                    return "✖️ Ошибка API"
    except asyncio.TimeoutError:
        return "✖️ Превышено время ожидания ответа"
    except Exception as e:
        logging.error(f"Ошибка AI: {e}")
        return "✖️ Ошибка соединения"


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
        return "✖️ Не настроен DEEPSEEK_API_KEY. Текстовые ответы работают только через DeepSeek."

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
                    return "✖️ Ошибка API"
    except asyncio.TimeoutError:
        return "✖️ Превышено время ожидания ответа"
    except Exception as e:
        logging.error(f"Ошибка AI: {e}")
        return "✖️ Ошибка соединения"

async def generate_image(user_id: int, prompt: str, model: str) -> tuple:
    """Сгенерировать изображение"""
    if model == "pollinations-flux-free":
        clean_prompt = build_image_prompt(prompt)
        clean_prompt = sanitize_user_input(clean_prompt, max_length=800)
        if not clean_prompt:
            return False, "✖️ Пустой промпт для генерации."
        try:
            encoded_prompt = quote(clean_prompt, safe="")
            urls = [
                f"{FREE_IMAGE_API_URL}/{encoded_prompt}",
                f"https://pollinations.ai/p/{encoded_prompt}",
            ]
            retry_statuses = {429, 500, 502, 503, 504, 520, 522, 524, 530}
            # Для бесплатного API делаем несколько попыток, так как он часто нестабилен.
            attempts = [
                {"model": "flux", "nologo": "true", "width": "1024", "height": "1024"},
                {"model": "flux", "nologo": "true", "width": "1024", "height": "1024", "enhance": "true"},
                {"model": "turbo", "nologo": "true", "width": "1024", "height": "1024"},
            ]
            last_status = None
            async with aiohttp.ClientSession() as session:
                for base_url in urls:
                    for i, params in enumerate(attempts):
                        params = dict(params)
                        params["seed"] = str(random.randint(1, 10_000_000))
                        try:
                            async with session.get(base_url, params=params, timeout=90) as response:
                                if response.status == 200:
                                    image_bytes = await response.read()
                                    if image_bytes:
                                        increment_stat("total_messages")
                                        return True, image_bytes
                                    last_status = 200
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
                    return False, "✖️ Бесплатный API временно перегружен. Попробуйте через 10-30 секунд."
                return False, f"✖️ Ошибка бесплатного API ({last_status})"
            return False, "✖️ Бесплатный API не вернул изображение."
        except asyncio.TimeoutError:
            return False, "✖️ Бесплатный API: превышено время ожидания (90 сек)"
        except Exception as e:
            logging.error(f"Ошибка бесплатной генерации: {e}")
            return False, "✖️ Ошибка бесплатной генерации изображения"

    if not API_BEARER_TOKEN:
        return False, "✖️ Не настроен API_BEARER_TOKEN для генерации изображений."

    prompt_clean = build_image_prompt(prompt)
    prompt_clean = sanitize_user_input(prompt_clean, max_length=1500)
    if not prompt_clean:
        return False, "✖️ Пустой промпт для генерации."

    headers = {"Authorization": f"Bearer {API_BEARER_TOKEN}", "Content-Type": "application/json"}

    enabled_models = set(get_enabled_models())
    ordered_candidates = ["flux", "flux-2-dev", "grok-2-image", "phoenix-1.0", "lucid-origin"]
    model_attempts = [model]
    for candidate in ordered_candidates:
        if candidate in AVAILABLE_MODELS and candidate in IMAGE_MODELS and candidate != "pollinations-flux-free" and candidate not in model_attempts:
            model_attempts.append(candidate)

    last_status = None
    last_body = ""
    try:
        connector = aiohttp.TCPConnector()
        async with aiohttp.ClientSession(connector=connector) as session:
            for idx, model_name in enumerate(model_attempts):
                send = {"model": model_name, "prompt": prompt_clean, "n": 1}
                async with session.post(IMAGE_API_URL, json=send, headers=headers, timeout=90) as response:
                    if response.status == 200:
                        data = await response.json()
                        if "files" in data and isinstance(data["files"], list) and len(data["files"]) > 0:
                            try:
                                image_bytes = base64.b64decode(data["files"][0])
                                increment_stat("total_messages")
                                return True, image_bytes
                            except Exception:
                                return False, "✖️ Ошибка декодирования изображения"
                        last_status = 200
                        continue

                    body = (await response.text())[:500]
                    last_status = response.status
                    last_body = body
                    logging.warning(f"Image API error {response.status} (model={model_name}): {body}")

                    # На rate limit пробуем следующую onlysq image-модель.
                    if response.status == 429 and idx < len(model_attempts) - 1:
                        continue
                    if response.status == 401:
                        return False, "✖️ Ошибка API (401): проверьте API_BEARER_TOKEN в Railway Variables."

        # Если onlysq не справился (например, 429 на всех моделях) — пробуем бесплатный fallback.
        if last_status in {429, 500, 502, 503, 504, 520, 522, 524, 530}:
            return await generate_image(user_id, prompt_clean, "pollinations-flux-free")
        if last_status:
            return False, f"✖️ Ошибка API ({last_status})"
        return False, f"✖️ API не вернул изображение"
    except asyncio.TimeoutError:
        return False, "✖️ Превышено время ожидания (90 сек)"
    except Exception as e:
        logging.error(f"Ошибка генерации: {e} | last_status={last_status} body={last_body}")
        return False, f"✖️ Ошибка: {str(e)}"


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

async def send_long_message(message: Message, text: str):
    """Отправить длинное сообщение"""
    text = markdown_to_html(text)

    parts = split_message(text)

    for i, part in enumerate(parts):
        if i > 0:
            await asyncio.sleep(0.5)
        try:
            await message.answer(part, parse_mode="HTML")
        except:
            await message.answer(part)


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

    if not can_make_request(user_id):
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
                await message.answer("✖️ Сейчас нет доступной модели для генерации изображений.")
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
            if isinstance(source_context, str) and source_context.startswith("✖️"):
                source_context = ""

            edit_prompt = build_photo_edit_prompt(user_text, source_context or "")
            success, result = await generate_image_with_guard(user_id, edit_prompt, image_model)
            if success:
                photo_out = (
                    BufferedInputFile(result, filename="edited_image.jpg")
                    if isinstance(result, (bytes, bytearray))
                    else result
                )
                await message.answer_photo(
                    photo=photo_out,
                    caption=f"{text_emoji('image')} Модель: {image_model}\n✏️ Редактирование выполнено",
                    parse_mode="HTML"
                )
                if not has_active_subscription(user_id):
                    consume_free_trial(user_id, is_image=True)
                    await maybe_send_trial_reminder_1_left(message.chat.id, user_id)
            else:
                await message.answer(
                    f"{result}\nПопробуйте уточнить правку (например: стиль, фон, цвет, ракурс)."
                )
            return

        ai_response = await get_ai_response(user_id, user_text, photo_base64)
        await send_long_message(message, ai_response)
        if not has_active_subscription(user_id):
            consume_free_trial(user_id)
            await maybe_send_trial_reminder_1_left(message.chat.id, user_id)
    except Exception as e:
        logging.error(f"Ошибка фото: {e}")
        await message.answer("✖️ Ошибка при обработке фото")


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

    if not can_make_request(user_id):
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
            await message.answer("✖️ Не удалось распознать голосовое сообщение. Попробуйте еще раз.")
            return

        if is_image_generation_request(transcribed_text):
            image_model = pick_image_model_for_prompt(user_id, transcribed_text)
            if not image_model:
                await message.answer("✖️ Сейчас нет доступной модели для генерации изображений.")
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
                await message.answer_photo(
                    photo=photo,
                    caption=f"{text_emoji('image')} Модель: {image_model}\n{text_emoji('note')} Промпт: {transcribed_text[:100]}{'...' if len(transcribed_text) > 100 else ''}",
                    parse_mode="HTML"
                )
                if not has_active_subscription(user_id):
                    consume_free_trial(user_id, is_image=True)
                    await maybe_send_trial_reminder_1_left(message.chat.id, user_id)
            else:
                await message.answer(result)
            return

        ai_response = await get_ai_response(user_id, transcribed_text)
        await send_long_message(message, ai_response)
        if not has_active_subscription(user_id):
            consume_free_trial(user_id)
            await maybe_send_trial_reminder_1_left(message.chat.id, user_id)

    except Exception as e:
        logging.error(f"Ошибка голоса: {e}")
        await message.answer("✖️ Ошибка при обработке голосового сообщения")


@dp.message(F.text)
async def handle_message(message: Message, state: FSMContext):
    """Обработка текстовых сообщений"""
    current_state = await state.get_state()
    if current_state:
        return

    if message.text.startswith('/'):
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

    if not can_make_request(user_id):
        increment_stat("paywall_shown")
        await send_system_message(
            chat_id=message.chat.id,
            text=get_free_trial_paywall_text(user_id),
            reply_markup=get_subscription_keyboard(user_id)
        )
        return

    if is_photo_edit_request(message.text):
        await message.answer("✖️ Для редактирования пришлите фото с подписью, что нужно изменить.")
        return

    if is_image_generation_request(message.text):
        image_model = pick_image_model_for_prompt(user_id, message.text)
        if not image_model:
            await message.answer("✖️ Сейчас нет доступной модели для генерации изображений.")
            return

        ok_limit, limit_msg = try_consume_image_generation_limit(user_id)
        if not ok_limit:
            await message.answer(limit_msg)
            return

        await bot.send_chat_action(message.chat.id, "upload_photo")

        success, result = await generate_image_with_guard(user_id, message.text, image_model)

        if success:
            try:
                photo = (
                    BufferedInputFile(result, filename="generated_image.jpg")
                    if isinstance(result, (bytes, bytearray))
                    else result
                )
                await message.answer_photo(
                    photo=photo,
                    caption=f"{text_emoji('image')} Модель: {image_model}\n{text_emoji('note')} Промпт: {message.text[:100]}{'...' if len(message.text) > 100 else ''}",
                    parse_mode="HTML"
                )
                if not has_active_subscription(user_id):
                    consume_free_trial(user_id, is_image=True)
                    await maybe_send_trial_reminder_1_left(message.chat.id, user_id)
            except Exception as e:
                await message.answer(f"✖️ Ошибка отправки: {str(e)}")
        else:
            await message.answer(result)
        return

    await bot.send_chat_action(message.chat.id, "typing")
    ai_response = await get_ai_response(user_id, message.text)
    await send_long_message(message, ai_response)
    if not has_active_subscription(user_id):
        consume_free_trial(user_id)
        await maybe_send_trial_reminder_1_left(message.chat.id, user_id)


# ==================== TRIAL REMINDERS ====================
async def maybe_send_trial_reminder_1_left(chat_id: int, user_id: int):
    """Отправить напоминание, когда остался 1 бесплатный запрос (после 4-го использования)."""
    if user_id in ADMIN_IDS or has_active_subscription(user_id):
        return
    used = get_free_trial_used(user_id)
    if used != FREE_TRIAL_LIMIT - 1:
        return
    if not should_send_reminder(user_id, "trial_1_left"):
        return
    try:
        await send_system_message(
            chat_id=chat_id,
            text=get_message("trial_reminder_1_left"),
            reply_markup=get_subscription_keyboard(user_id),
            parse_mode="HTML"
        )
        set_last_reminder(user_id, "trial_1_left")
    except Exception as e:
        logging.warning(f"Не удалось отправить напоминание trial_1_left для {user_id}: {e}")


async def check_trial_reminders():
    """Напоминания для trial-пользователей: 24ч после первого использования."""
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
                if 23 < hours_since < 25:
                    if should_send_reminder(user_id, "trial_24h"):
                        try:
                            await send_system_message(
                                chat_id=user_id,
                                text=get_message("trial_reminder_24h"),
                                reply_markup=get_subscription_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "trial_24h")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить напоминание trial_24h для {user_id}: {e}")

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
                                    "⏰ <b>Напоминание!</b>\n\n"
                                    "Ваша подписка истекает через 24 часа.\n"
                                    "Не забудьте продлить её!"
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
                                    "⚠️ <b>Внимание!</b>\n\n"
                                    "Ваша подписка истекает через 2 часа!\n"
                                    "Продлите подписку, чтобы не потерять доступ."
                                ),
                                reply_markup=get_subscription_keyboard(user_id),
                                parse_mode="HTML"
                            )
                            set_last_reminder(user_id, "2h")
                        except Exception as e:
                            logging.warning(f"Не удалось отправить напоминание 2ч для {user_id}: {e}")

        except Exception as e:
            logging.error(f"Ошибка проверки напоминаний: {e}")

        # Проверяем каждые 30 минут
        await asyncio.sleep(1800)


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

                        # Обновляем статистику
                        price_usd = get_subscription_price_usd()
                        increment_stat("total_payments")
                        increment_stat("total_revenue_usd", price_usd)

                        # Уведомляем пользователя
                        try:
                            sub_end = get_subscription_end(user_id)
                            await send_system_message(
                                chat_id=user_id,
                                text=(
                                    "✅ <b>Оплата получена!</b>\n\n"
                                    "💎 Подписка активирована через CryptoBot\n"
                                    f"📅 Действует до: {sub_end.strftime('%d.%m.%Y %H:%M')}\n\n"
                                    "Спасибо за покупку! 🎉"
                                ),
                                reply_markup=get_main_keyboard(),
                                parse_mode="HTML"
                            )
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
    asyncio.create_task(check_pending_invoices())  # НОВОЕ

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("👋 Бот остановлен")
