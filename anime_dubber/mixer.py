"""
Anime Dubber — Audio/Video birlashtirish va SRT yaratish
"""
import os
import subprocess
from pydub import AudioSegment
from tqdm import tqdm
from config import FFMPEG_PATH, OUTPUT_DIR, TEMP_DIR


def create_dubbed_audio(segments, original_audio_path, video_duration):
    """Barcha TTS segmentlarini bitta audio trekga birlashtirish.

    Original vaqtga moslashtirilgan uzunlikda bo'sh audio yaratib,
    har bir TTS segmentni to'g'ri pozitsiyaga joylashtiradi.
    """
    print('Dublyaj audio yaratilmoqda...')

    # Video uzunligida bo'sh audio yaratish
    total_ms = int(video_duration * 1000)
    dubbed_audio = AudioSegment.silent(duration=total_ms)

    placed = 0
    for seg in tqdm(segments, desc='Audio birlashtirish'):
        tts_path = seg.get('tts_path')
        if not tts_path or not os.path.exists(tts_path):
            continue

        try:
            tts_audio = AudioSegment.from_file(tts_path)
            start_ms = int(seg['start'] * 1000)

            # Segmentni joylashtirish
            dubbed_audio = dubbed_audio.overlay(tts_audio, position=start_ms)
            placed += 1
        except Exception as e:
            print(f'\nSegment {seg["id"]} joylashtirish xatosi: {e}')

    print(f'Joylashtirildi: {placed}/{len(segments)} segment')

    # WAV sifatida saqlash
    os.makedirs(TEMP_DIR, exist_ok=True)
    dubbed_path = os.path.join(TEMP_DIR, 'dubbed_audio.wav')
    dubbed_audio.export(dubbed_path, format='wav')
    print(f'Dublyaj audio tayyor: {dubbed_path}')

    return dubbed_path


def merge_video_audio(video_path, dubbed_audio_path, output_path):
    """Video va yangi audio trekni birlashtirish.

    Original audio -15dB ga pasaytiriladi (fon sifatida qoladi),
    dublyaj audio asosiy ovoz sifatida qo'shiladi.
    """
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)

    print(f'Video va audio birlashtirilmoqda...')

    cmd = [
        FFMPEG_PATH,
        '-i', video_path,           # original video
        '-i', dubbed_audio_path,    # dublyaj audio
        '-filter_complex',
        # Original audioni pasaytirish + dublyaj audio qo'shish
        '[0:a]volume=0.15[bg];'     # original audio -15dB fon
        '[1:a]volume=1.0[dub];'     # dublyaj audio to'liq
        '[bg][dub]amix=inputs=2:duration=first[out]',
        '-map', '0:v',              # original video
        '-map', '[out]',            # aralashtirilgan audio
        '-c:v', 'copy',            # videoni qayta kodlamaslik
        '-c:a', 'aac',             # audio AAC
        '-b:a', '192k',
        '-y',
        output_path
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'FFmpeg birlashtirish xatosi: {result.stderr[:500]}')

    print(f'Tayyor video: {output_path}')
    return output_path


def generate_srt(segments, output_path):
    """SRT subtitle fayl yaratish"""
    print(f'SRT fayl yaratilmoqda...')

    def format_time(seconds):
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        ms = int((seconds % 1) * 1000)
        return f'{h:02d}:{m:02d}:{s:02d},{ms:03d}'

    lines = []
    for i, seg in enumerate(segments, 1):
        text = seg.get('translated_text', '') or seg.get('text', '')
        if not text.strip():
            continue
        start = format_time(seg['start'])
        end = format_time(seg['end'])
        lines.append(f'{i}')
        lines.append(f'{start} --> {end}')
        lines.append(text)
        lines.append('')

    srt_content = '\n'.join(lines)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)

    print(f'SRT tayyor: {output_path} ({len(segments)} segment)')
    return output_path
