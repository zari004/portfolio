"""
Anime Dubber — Ovoz tahlili (erkak/ayol, past/baland)
"""
import numpy as np

try:
    import librosa
    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False


def analyze_voice(audio_path, start=None, end=None):
    """Audio segmentning ovoz turini aniqlash.

    Qaytaradi: 'female', 'male_soft', yoki 'male_rough'

    Fundamental chastota (F0) orqali:
      - > 180 Hz → ayol ovozi
      - 100-180 Hz → erkak yumshoq ovoz
      - < 100 Hz → erkak past/qo'pol ovoz
    """
    if not LIBROSA_AVAILABLE:
        return 'male_soft'  # default

    try:
        # Audio yuklash
        if start is not None and end is not None:
            duration = end - start
            y, sr = librosa.load(audio_path, sr=16000, offset=start, duration=duration)
        else:
            y, sr = librosa.load(audio_path, sr=16000)

        if len(y) < sr * 0.1:  # 0.1 sekunddan qisqa
            return 'male_soft'

        # Fundamental chastota (F0) aniqlash
        f0, voiced_flag, _ = librosa.pyin(
            y, fmin=50, fmax=500, sr=sr
        )

        # Faqat ovozli qismlarni olish
        f0_voiced = f0[voiced_flag] if voiced_flag is not None else f0[~np.isnan(f0)]

        if len(f0_voiced) == 0:
            return 'male_soft'

        median_f0 = float(np.median(f0_voiced))

        if median_f0 > 180:
            return 'female'
        elif median_f0 > 100:
            return 'male_soft'
        else:
            return 'male_rough'

    except Exception:
        return 'male_soft'


def analyze_segments(audio_path, segments):
    """Barcha segmentlar uchun ovoz turini aniqlash"""
    if not LIBROSA_AVAILABLE:
        print('librosa o\'rnatilmagan — barcha segmentlar male_soft sifatida belgilanadi')
        for seg in segments:
            seg['voice_type'] = 'male_soft'
        return segments

    from tqdm import tqdm
    print('Ovoz tahlili boshlanmoqda...')

    for seg in tqdm(segments, desc='Ovoz tahlili'):
        voice_type = analyze_voice(audio_path, seg['start'], seg['end'])
        seg['voice_type'] = voice_type

    # Statistika
    counts = {}
    for seg in segments:
        vt = seg['voice_type']
        counts[vt] = counts.get(vt, 0) + 1

    print('Ovoz statistikasi:')
    for vt, cnt in counts.items():
        print(f'  {vt}: {cnt} segment')

    return segments
