"""
Anime Dubber — Gemini API orqali tarjima
"""
import time
from tqdm import tqdm
from config import GEMINI_API_KEY, GEMINI_MODEL, TRANSLATE_PROMPT

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def init_gemini(api_key=None):
    """Gemini API ni sozlash"""
    if not GENAI_AVAILABLE:
        raise RuntimeError(
            'google-generativeai o\'rnatilmagan!\n'
            'pip install google-generativeai'
        )

    key = api_key or GEMINI_API_KEY
    if not key:
        raise RuntimeError(
            'Gemini API kalit topilmadi!\n'
            'Kalit olish: https://aistudio.google.com/\n'
            'Ishlatish: --gemini-key KALIT yoki GEMINI_API_KEY env'
        )

    genai.configure(api_key=key)
    return genai.GenerativeModel(GEMINI_MODEL)


def translate_text(model, text, source_lang='ja'):
    """Bitta matnni o'zbek tiliga tarjima qilish"""
    if not text or not text.strip():
        return ''

    prompt = f'{TRANSLATE_PROMPT}\n\nOriginal ({source_lang}): {text}'

    try:
        response = model.generate_content(prompt)
        translated = response.text.strip()
        return translated
    except Exception as e:
        error_msg = str(e)
        if 'quota' in error_msg.lower() or 'rate' in error_msg.lower():
            # Rate limit — kutib qayta urinish
            print(f'\nRate limit — 5 sekund kutilmoqda...')
            time.sleep(5)
            try:
                response = model.generate_content(prompt)
                return response.text.strip()
            except Exception:
                return text  # Original matnni qaytarish
        print(f'\nTarjima xatosi: {e}')
        return text


def translate_segments(segments, api_key=None):
    """Barcha segmentlarni tarjima qilish"""
    model = init_gemini(api_key)

    source_lang = segments[0].get('language', 'ja') if segments else 'ja'

    print(f'Tarjima boshlanmoqda ({source_lang} → uz)...')
    print(f'Model: {GEMINI_MODEL}')

    for seg in tqdm(segments, desc='Tarjima'):
        original = seg.get('text', '')
        translated = translate_text(model, original, source_lang)
        seg['original_text'] = original
        seg['translated_text'] = translated

        # Rate limit oldini olish (bepul API uchun)
        time.sleep(0.5)

    translated_count = sum(1 for s in segments if s.get('translated_text'))
    print(f'Tarjima yakunlandi: {translated_count}/{len(segments)} segment')

    return segments
