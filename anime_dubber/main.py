"""
Anime O'zbek Dublyajchi
Anime videolarni o'zbek tiliga ovozli dublyaj qilish.

Ishlatish:
  python main.py --input video.mp4 --gemini-key KALIT
  python main.py --input video.mp4 --output dubbed.mp4 --whisper-model medium
  python main.py --input video.mp4 --subtitles-only
  python main.py --input ./videos/ --gemini-key KALIT
"""
import os
import sys
import glob
import shutil
import argparse
import traceback
import time

from config import (
    GEMINI_API_KEY, WHISPER_MODEL, DEFAULT_VOICE,
    OUTPUT_DIR, TEMP_DIR, apply_admin_config, load_from_admin
)


def parse_args():
    parser = argparse.ArgumentParser(
        description='Anime videolarni o\'zbek tiliga dublyaj qilish',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Misollar:
  python main.py --input anime.mp4 --gemini-key AIza...
  python main.py --input anime.mp4 --voice-type female
  python main.py --input ./videos/ --subtitles-only
  python main.py --input anime.mp4 --whisper-model medium
        '''
    )
    parser.add_argument('--input', '-i', required=True,
                        help='Video fayl yoki papka yo\'li')
    parser.add_argument('--output', '-o', default=None,
                        help='Chiqish fayl nomi (default: output/)')
    parser.add_argument('--gemini-key', default=None,
                        help='Gemini API kalit')
    parser.add_argument('--whisper-model', default=None,
                        choices=['tiny', 'base', 'small', 'medium', 'large'],
                        help='Whisper model (default: small)')
    parser.add_argument('--voice-type', default=None,
                        choices=['female', 'male_soft', 'male_rough'],
                        help='Ovoz turini qo\'lda belgilash')
    parser.add_argument('--subtitles-only', action='store_true',
                        help='Faqat SRT subtitle yaratish')
    parser.add_argument('--admin-config', default=None,
                        help='Admin panel config fayl yo\'li (JSON)')
    return parser.parse_args()


def get_video_files(input_path):
    """Video fayllarni topish (fayl yoki papka)"""
    video_exts = {'.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv'}

    if os.path.isfile(input_path):
        return [input_path]
    elif os.path.isdir(input_path):
        files = []
        for ext in video_exts:
            files.extend(glob.glob(os.path.join(input_path, f'*{ext}')))
        if not files:
            print(f'Papkada video topilmadi: {input_path}')
        return sorted(files)
    else:
        print(f'Fayl yoki papka topilmadi: {input_path}')
        return []


def process_video(video_path, args):
    """Bitta video faylni dublyaj qilish"""
    from extractor import extract_audio, transcribe, get_video_duration
    from voice_analyzer import analyze_segments
    from translator import translate_segments
    from tts_generator import generate_all_segments
    from mixer import create_dubbed_audio, merge_video_audio, generate_srt

    basename = os.path.splitext(os.path.basename(video_path))[0]
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(TEMP_DIR, exist_ok=True)

    total_start = time.time()
    print(f'\n{"=" * 60}')
    print(f'Video: {video_path}')
    print(f'{"=" * 60}')

    # ── 1. Audio ajratish ──
    print(f'\n[1/6] Audio ajratilmoqda...')
    audio_path = extract_audio(video_path)
    video_duration = get_video_duration(video_path)
    print(f'Video uzunligi: {video_duration:.1f} sekund')

    # ── 2. Whisper transkriptsiya ──
    print(f'\n[2/6] Transkriptsiya (Whisper {args.whisper_model or WHISPER_MODEL})...')
    result = transcribe(audio_path, args.whisper_model)
    segments = result['segments']

    if not segments:
        print('Hech qanday dialog topilmadi!')
        return None

    # ── 3. Ovoz tahlili ──
    print(f'\n[3/6] Ovoz tahlili...')
    if args.voice_type:
        print(f'Qo\'lda belgilangan ovoz: {args.voice_type}')
        for seg in segments:
            seg['voice_type'] = args.voice_type
    else:
        segments = analyze_segments(audio_path, segments)

    # ── 4. Tarjima ──
    print(f'\n[4/6] Tarjima ({result["language"]} → uz)...')
    segments = translate_segments(segments, args.gemini_key)

    # ── 5. SRT yaratish ──
    srt_path = os.path.join(OUTPUT_DIR, f'{basename}_uz.srt')
    generate_srt(segments, srt_path)

    if args.subtitles_only:
        print(f'\nFaqat subtitle rejimi — SRT tayyor: {srt_path}')
        elapsed = time.time() - total_start
        print(f'Umumiy vaqt: {elapsed:.1f} sekund')
        return srt_path

    # ── 5. TTS ovoz yaratish ──
    print(f'\n[5/6] TTS ovoz yaratish...')
    segments = generate_all_segments(segments, force_voice=args.voice_type)

    # ── 6. Video + Audio birlashtirish ──
    print(f'\n[6/6] Video va audio birlashtirilmoqda...')
    dubbed_audio_path = create_dubbed_audio(segments, audio_path, video_duration)

    output_path = args.output or os.path.join(OUTPUT_DIR, f'{basename}_dubbed.mp4')
    merge_video_audio(video_path, dubbed_audio_path, output_path)

    elapsed = time.time() - total_start
    print(f'\n{"=" * 60}')
    print(f'TAYYOR!')
    print(f'Video:    {output_path}')
    print(f'Subtitle: {srt_path}')
    print(f'Vaqt:     {elapsed:.1f} sekund')
    print(f'{"=" * 60}')

    return output_path


def cleanup_temp():
    """Vaqtinchalik fayllarni tozalash"""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
        print('Temp fayllar tozalandi.')


def main():
    args = parse_args()

    # Admin panel sozlamalarini yuklash
    if args.admin_config:
        cfg = load_from_admin(args.admin_config)
        if cfg:
            apply_admin_config(cfg)
            print('Admin panel sozlamalari yuklandi.')

    # Gemini kalit
    if args.gemini_key:
        os.environ['GEMINI_API_KEY'] = args.gemini_key
        import config
        config.GEMINI_API_KEY = args.gemini_key

    print('=' * 60)
    print('  ANIME O\'ZBEK DUBLYAJCHI')
    print('=' * 60)

    video_files = get_video_files(args.input)
    if not video_files:
        sys.exit(1)

    print(f'Topilgan videolar: {len(video_files)}')

    results = []
    for i, video_path in enumerate(video_files, 1):
        if len(video_files) > 1:
            print(f'\n[{i}/{len(video_files)}] navbatdagi video...')
        try:
            result = process_video(video_path, args)
            results.append((video_path, result, None))
        except Exception as e:
            print(f'\nXATO: {e}')
            traceback.print_exc()
            results.append((video_path, None, str(e)))

    # Yakuniy hisobot
    if len(video_files) > 1:
        print(f'\n{"=" * 60}')
        print(f'YAKUNIY HISOBOT:')
        success = sum(1 for _, r, _ in results if r)
        failed = sum(1 for _, _, e in results if e)
        print(f'  Muvaffaqiyatli: {success}')
        print(f'  Xato: {failed}')
        print(f'{"=" * 60}')

    cleanup_temp()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nBekor qilindi.')
        cleanup_temp()
        sys.exit(0)
    except Exception as e:
        print(f'\nKutilmagan xato: {e}')
        traceback.print_exc()
        cleanup_temp()
        sys.exit(1)
