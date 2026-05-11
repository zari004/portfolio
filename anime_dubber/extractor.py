"""
Anime Dubber — Audio ajratish va Whisper transkriptsiya
"""
import os
import subprocess
import whisper
from tqdm import tqdm
from config import WHISPER_MODEL, FFMPEG_PATH, TEMP_DIR


def check_ffmpeg():
    """FFmpeg o'rnatilganligini tekshirish"""
    try:
        result = subprocess.run(
            [FFMPEG_PATH, '-version'],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def extract_audio(video_path, output_path=None):
    """Videodan audio ajratib olish (WAV formatda)"""
    if not check_ffmpeg():
        raise RuntimeError(
            'FFmpeg topilmadi! O\'rnating:\n'
            '  Windows: https://ffmpeg.org/download.html\n'
            '  Mac: brew install ffmpeg\n'
            '  Linux: sudo apt install ffmpeg'
        )

    os.makedirs(TEMP_DIR, exist_ok=True)

    if output_path is None:
        base = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(TEMP_DIR, f'{base}_audio.wav')

    print(f'Audio ajratilmoqda: {video_path}')
    cmd = [
        FFMPEG_PATH, '-i', video_path,
        '-vn',                    # videoni olib tashlash
        '-acodec', 'pcm_s16le',  # WAV format
        '-ar', '16000',           # 16kHz (Whisper uchun optimal)
        '-ac', '1',               # mono
        '-y',                     # ustiga yozish
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'FFmpeg xatosi: {result.stderr[:500]}')

    print(f'Audio tayyor: {output_path}')
    return output_path


def transcribe(audio_path, model_size=None):
    """Whisper bilan audioni matnga aylantirish"""
    model_name = model_size or WHISPER_MODEL

    print(f'Whisper model yuklanmoqda: {model_name}')
    model = whisper.load_model(model_name)

    print(f'Transkriptsiya boshlanmoqda...')
    result = model.transcribe(
        audio_path,
        verbose=False,
        task='transcribe',
    )

    language = result.get('language', 'unknown')
    segments = result.get('segments', [])

    print(f'Til aniqlandi: {language}')
    print(f'Segmentlar soni: {len(segments)}')

    # Segmentlarni formatlash
    formatted = []
    for seg in tqdm(segments, desc='Segmentlar qayta ishlanmoqda'):
        formatted.append({
            'id': seg['id'],
            'start': seg['start'],
            'end': seg['end'],
            'text': seg['text'].strip(),
            'language': language,
        })

    return {
        'language': language,
        'segments': formatted,
        'full_text': result.get('text', ''),
    }


def get_video_duration(video_path):
    """Video uzunligini olish (sekundlarda)"""
    cmd = [
        FFMPEG_PATH, '-i', video_path,
        '-f', 'null', '-'
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    # FFmpeg chiqishidan duration ni olish
    for line in result.stderr.split('\n'):
        if 'Duration' in line:
            time_str = line.split('Duration:')[1].split(',')[0].strip()
            parts = time_str.split(':')
            hours = float(parts[0])
            minutes = float(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
    return 0
