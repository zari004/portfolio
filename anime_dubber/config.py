"""
Anime Dubber — Sozlamalar
"""
import os
import json

# ── API KALITLAR ─────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY', '')

# ── WHISPER SOZLAMALARI ──────────────────────────────────────────────────────
WHISPER_MODEL = 'small'  # tiny, base, small, medium, large

# ── OVOZ TURLARI ─────────────────────────────────────────────────────────────
VOICES = {
    'female': {
        'name': 'uz-UZ-MadinaNeural',
        'rate': '+0%',
        'pitch': '+0Hz',
    },
    'male_soft': {
        'name': 'uz-UZ-SardorNeural',
        'rate': '+0%',
        'pitch': '+0Hz',
    },
    'male_rough': {
        'name': 'uz-UZ-SardorNeural',
        'rate': '-10%',
        'pitch': '-15%',
    },
}

DEFAULT_VOICE = 'male_soft'

# ── GEMINI TARJIMA ───────────────────────────────────────────────────────────
GEMINI_MODEL = 'gemini-1.5-flash'

TRANSLATE_PROMPT = """Quyidagi anime dialogini tabiiy o'zbek tiliga tarjima qil.
Ohangni saqla: dramatik bo'lsa dramatik, kulgili bo'lsa kulgili qilib tarjima qil.
Faqat tarjima qilingan matnni yoz, boshqa hech narsa yozma."""

# ── FFMPEG ───────────────────────────────────────────────────────────────────
FFMPEG_PATH = 'ffmpeg'  # yoki to'liq yo'l: C:/ffmpeg/bin/ffmpeg.exe

# ── CHIQISH ──────────────────────────────────────────────────────────────────
OUTPUT_DIR = 'output'
TEMP_DIR = 'temp'


def load_from_admin(json_path=None):
    """Admin paneldan saqlangan sozlamalarni yuklash"""
    if json_path and os.path.exists(json_path):
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return data
        except Exception:
            pass
    return {}


def apply_admin_config(cfg):
    """Admin panel sozlamalarini qo'llash"""
    global GEMINI_API_KEY, WHISPER_MODEL, DEFAULT_VOICE, GEMINI_MODEL, TRANSLATE_PROMPT

    if cfg.get('geminiKey'):
        GEMINI_API_KEY = cfg['geminiKey']
    if cfg.get('whisperModel'):
        WHISPER_MODEL = cfg['whisperModel']
    if cfg.get('defaultVoice'):
        DEFAULT_VOICE = cfg['defaultVoice']
    if cfg.get('geminiModel'):
        GEMINI_MODEL = cfg['geminiModel']
    if cfg.get('translatePrompt'):
        TRANSLATE_PROMPT = cfg['translatePrompt']
    if cfg.get('voices'):
        for key, val in cfg['voices'].items():
            if key in VOICES:
                VOICES[key].update(val)
