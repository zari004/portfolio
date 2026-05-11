"""
Anime Dubber — Edge TTS orqali o'zbek ovoz yaratish
"""
import os
import asyncio
import edge_tts
from pydub import AudioSegment
from tqdm import tqdm
from config import VOICES, DEFAULT_VOICE, TEMP_DIR


async def generate_speech_async(text, voice_type, output_path):
    """Bitta segment uchun TTS ovoz yaratish"""
    voice_cfg = VOICES.get(voice_type, VOICES[DEFAULT_VOICE])

    communicate = edge_tts.Communicate(
        text=text,
        voice=voice_cfg['name'],
        rate=voice_cfg.get('rate', '+0%'),
        pitch=voice_cfg.get('pitch', '+0Hz'),
    )

    await communicate.save(output_path)


def generate_speech(text, voice_type, output_path):
    """Sinxron wrapper"""
    asyncio.run(generate_speech_async(text, voice_type, output_path))


def adjust_duration(audio_path, target_duration_ms):
    """Audio uzunligini maqsadli davomiylikka moslashtirish.

    Agar TTS audio originaldan uzun/qisqa bo'lsa, tezlikni o'zgartiradi.
    """
    audio = AudioSegment.from_file(audio_path)
    current_duration = len(audio)  # millisekund

    if current_duration == 0 or target_duration_ms == 0:
        return audio

    ratio = current_duration / target_duration_ms

    if 0.8 <= ratio <= 1.2:
        # 20% dan kam farq — o'zgartirish shart emas
        return audio

    # Tezlikni o'zgartirish (frame_rate orqali)
    # ratio > 1 → audio uzun → tezlashtirish kerak
    # ratio < 1 → audio qisqa → sekinlashtirish kerak
    new_frame_rate = int(audio.frame_rate * ratio)

    # Xavfsizlik chegaralari (0.5x — 2x)
    min_rate = int(audio.frame_rate * 0.5)
    max_rate = int(audio.frame_rate * 2.0)
    new_frame_rate = max(min_rate, min(max_rate, new_frame_rate))

    adjusted = audio._spawn(audio.raw_data, overrides={
        'frame_rate': new_frame_rate
    }).set_frame_rate(audio.frame_rate)

    return adjusted


def generate_all_segments(segments, force_voice=None):
    """Barcha segmentlar uchun TTS ovoz yaratish"""
    os.makedirs(TEMP_DIR, exist_ok=True)

    print('TTS ovoz yaratish boshlanmoqda...')

    generated = []
    for seg in tqdm(segments, desc='TTS generatsiya'):
        text = seg.get('translated_text', '') or seg.get('text', '')
        if not text.strip():
            seg['tts_path'] = None
            generated.append(seg)
            continue

        voice_type = force_voice or seg.get('voice_type', DEFAULT_VOICE)
        tts_path = os.path.join(TEMP_DIR, f'tts_seg_{seg["id"]}.mp3')

        try:
            generate_speech(text, voice_type, tts_path)

            # Davomiylikni moslashtirish
            target_ms = int((seg['end'] - seg['start']) * 1000)
            if target_ms > 0 and os.path.exists(tts_path):
                adjusted = adjust_duration(tts_path, target_ms)
                adjusted_path = os.path.join(TEMP_DIR, f'tts_adj_{seg["id"]}.wav')
                adjusted.export(adjusted_path, format='wav')
                seg['tts_path'] = adjusted_path
                seg['tts_duration_ms'] = len(adjusted)
            else:
                seg['tts_path'] = tts_path

        except Exception as e:
            print(f'\nTTS xatosi (seg {seg["id"]}): {e}')
            seg['tts_path'] = None

        generated.append(seg)

    success = sum(1 for s in generated if s.get('tts_path'))
    print(f'TTS yakunlandi: {success}/{len(generated)} segment')

    return generated
