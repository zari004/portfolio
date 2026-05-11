"""
Anime Dubber — Video yuklab olish (URL dan)
yt-dlp va requests orqali
"""
import os
import re
import requests as req

try:
    import yt_dlp
    YT_DLP_AVAILABLE = True
except ImportError:
    YT_DLP_AVAILABLE = False

from config import TEMP_DIR


def is_direct_video_url(url):
    """To'g'ridan-to'g'ri video fayl havolasimi?"""
    video_exts = ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv')
    clean = url.lower().split('?')[0].split('#')[0]
    return any(clean.endswith(ext) for ext in video_exts)


def sanitize_filename(name):
    """Fayl nomidan noto'g'ri belgilarni olib tashlash"""
    name = re.sub(r'[<>:"/\\|?*]', '_', name)
    name = name.strip('. ')
    if not name:
        name = 'video'
    return name[:200]


def download_direct(url, output_dir):
    """To'g'ridan-to'g'ri URL dan yuklab olish (requests)"""
    # Fayl nomini aniqlash
    filename = url.split('/')[-1].split('?')[0].split('#')[0]
    if not filename or '.' not in filename:
        filename = 'video.mp4'
    filename = sanitize_filename(filename)
    filepath = os.path.join(output_dir, filename)

    print(f'Yuklanmoqda (to\'g\'ridan-to\'g\'ri): {url}')
    resp = req.get(url, stream=True, timeout=120, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    resp.raise_for_status()

    total = int(resp.headers.get('content-length', 0))
    downloaded = 0

    with open(filepath, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=65536):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = int(downloaded / total * 100)
                print(f'\r  Yuklandi: {pct}% ({downloaded // 1048576} MB)', end='', flush=True)

    print()
    size_mb = os.path.getsize(filepath) / 1048576
    print(f'Yuklandi: {filepath} ({size_mb:.1f} MB)')
    return filepath


def download_ytdlp(url, output_dir):
    """yt-dlp orqali yuklab olish (YouTube, va boshqa saytlar)"""
    if not YT_DLP_AVAILABLE:
        raise RuntimeError(
            "yt-dlp o'rnatilmagan!\n"
            "pip install yt-dlp"
        )

    output_template = os.path.join(output_dir, '%(title)s.%(ext)s')

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': True,
        'progress_hooks': [_progress_hook],
    }

    print(f'Yuklanmoqda (yt-dlp): {url}')
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)

    if not os.path.exists(filename):
        # ext o'zgargan bo'lishi mumkin
        base = os.path.splitext(filename)[0]
        for ext in ['.mp4', '.mkv', '.webm']:
            alt = base + ext
            if os.path.exists(alt):
                filename = alt
                break

    size_mb = os.path.getsize(filename) / 1048576
    print(f'Yuklandi: {filename} ({size_mb:.1f} MB)')
    return filename


def _progress_hook(d):
    """yt-dlp progress callback"""
    if d['status'] == 'downloading':
        pct = d.get('_percent_str', '?')
        speed = d.get('_speed_str', '?')
        print(f'\r  {pct} | {speed}', end='', flush=True)
    elif d['status'] == 'finished':
        print('\n  Yuklab olish tugadi, qayta ishlash...')


def download_video(url, output_dir=None):
    """URL dan video yuklab olish (avto-aniqlash)"""
    output_dir = output_dir or TEMP_DIR
    os.makedirs(output_dir, exist_ok=True)

    url = url.strip()
    if not url:
        raise ValueError("Bo'sh URL")

    if is_direct_video_url(url):
        return download_direct(url, output_dir)
    else:
        return download_ytdlp(url, output_dir)
