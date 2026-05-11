"""
Anime Dubber — Flask API Server
Admin paneldan video dublyaj qilish uchun backend.

Ishga tushirish:
  cd anime_dubber
  pip install -r requirements.txt
  python server.py

Server: http://localhost:5000
"""
import os
import sys
import uuid
import time
import json
import threading
import traceback
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

from config import apply_admin_config, OUTPUT_DIR, TEMP_DIR

app = Flask(__name__)
CORS(app)

# ── Job tracking ──
jobs = {}


class DubJob:
    """Dublyaj jarayonini kuzatish"""

    def __init__(self, job_id):
        self.id = job_id
        self.status = 'pending'
        self.step = 0
        self.total_steps = 6
        self.step_name = ''
        self.progress = 0
        self.logs = []
        self.result_path = None
        self.srt_path = None
        self.error = None
        self.video_name = ''
        self.created_at = time.time()

    def log(self, msg, level='info'):
        self.logs.append({
            'msg': msg,
            'level': level,
            'time': time.time()
        })

    def set_step(self, num, name):
        self.step = num
        self.step_name = name
        self.progress = int((num - 1) / self.total_steps * 100)
        self.log('[{}/{}] {}'.format(num, self.total_steps, name))

    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'step': self.step,
            'totalSteps': self.total_steps,
            'stepName': self.step_name,
            'progress': self.progress,
            'logs': self.logs[-50:],
            'resultPath': self.result_path,
            'srtPath': self.srt_path,
            'error': self.error,
            'videoName': self.video_name,
        }


def process_job(job, video_path, config):
    """Background thread da dublyaj jarayoni"""
    try:
        from extractor import extract_audio, transcribe, get_video_duration
        from voice_analyzer import analyze_segments
        from translator import translate_segments
        from tts_generator import generate_all_segments
        from mixer import create_dubbed_audio, merge_video_audio, generate_srt

        job.status = 'processing'
        basename = os.path.splitext(os.path.basename(video_path))[0]
        job.video_name = basename
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        os.makedirs(TEMP_DIR, exist_ok=True)

        # Config ni qo'llash
        if config:
            apply_admin_config(config)

        # Gemini kalitini sozlash
        gemini_key = config.get('geminiKey', '') if config else ''
        if gemini_key:
            os.environ['GEMINI_API_KEY'] = gemini_key
            import config as cfg_mod
            cfg_mod.GEMINI_API_KEY = gemini_key

        # ── 1. Audio ajratish ──
        job.set_step(1, 'Audio ajratilmoqda...')
        audio_path = extract_audio(video_path)
        video_duration = get_video_duration(video_path)
        job.log('Video uzunligi: {:.1f} sekund'.format(video_duration))

        # ── 2. Whisper transkriptsiya ──
        whisper_model = config.get('whisperModel', 'small') if config else 'small'
        job.set_step(2, 'Transkriptsiya (Whisper {})...'.format(whisper_model))
        result = transcribe(audio_path, whisper_model)
        segments = result['segments']

        if not segments:
            job.error = 'Hech qanday dialog topilmadi!'
            job.status = 'error'
            return

        job.log('{} ta segment topildi'.format(len(segments)))

        # ── 3. Ovoz tahlili ──
        voice_type = config.get('voiceType') if config else None
        if voice_type and voice_type != 'auto':
            job.set_step(3, 'Ovoz turi: {}'.format(voice_type))
            for seg in segments:
                seg['voice_type'] = voice_type
        else:
            job.set_step(3, 'Ovoz tahlili...')
            segments = analyze_segments(audio_path, segments)

        # ── 4. Tarjima ──
        job.set_step(4, 'Tarjima ({} -> uz)...'.format(result.get('language', '?')))
        segments = translate_segments(segments, gemini_key)

        # ── 5. SRT yaratish ──
        srt_path = os.path.join(OUTPUT_DIR, '{}_uz.srt'.format(basename))
        generate_srt(segments, srt_path)
        job.srt_path = os.path.abspath(srt_path)
        job.log('SRT tayyor: {}'.format(srt_path))

        subtitles_only = config.get('subtitlesOnly', False) if config else False
        if subtitles_only:
            job.log('Faqat subtitle rejimi — SRT tayyor')
            job.result_path = os.path.abspath(srt_path)
            job.progress = 100
            job.status = 'done'
            return

        # ── 5. TTS ovoz yaratish ──
        force_voice = voice_type if (voice_type and voice_type != 'auto') else None
        job.set_step(5, 'TTS ovoz yaratish...')
        segments = generate_all_segments(segments, force_voice=force_voice)

        # ── 6. Birlashtirish ──
        job.set_step(6, 'Video va audio birlashtirilmoqda...')
        dubbed_audio_path = create_dubbed_audio(segments, audio_path, video_duration)
        output_path = os.path.join(OUTPUT_DIR, '{}_dubbed.mp4'.format(basename))
        merge_video_audio(video_path, dubbed_audio_path, output_path)

        job.result_path = os.path.abspath(output_path)
        job.progress = 100
        job.status = 'done'
        job.log('TAYYOR! {}'.format(output_path), 'success')

    except Exception as e:
        job.error = str(e)
        job.status = 'error'
        job.log('XATO: {}'.format(e), 'error')
        traceback.print_exc()


# ── API Endpoints ──

@app.route('/api/health')
def health():
    """Server holatini tekshirish"""
    return jsonify({'status': 'ok', 'time': time.time()})


@app.route('/api/dub', methods=['POST'])
def start_dub():
    """Dublyaj jarayonini boshlash (URL yoki fayl)"""
    job_id = uuid.uuid4().hex[:8]
    job = DubJob(job_id)
    jobs[job_id] = job

    config = {}
    video_path = None

    if request.is_json:
        # JSON — URL orqali
        data = request.get_json()
        url = data.get('url', '').strip()
        config = data.get('config', {})

        if not url:
            return jsonify({'error': 'Video URL kerak'}), 400

        # Video yuklab olish
        try:
            from downloader import download_video
            job.log('Video yuklanmoqda: {}'.format(url))
            video_path = download_video(url)
            job.log('Yuklandi: {}'.format(os.path.basename(video_path)), 'success')
        except Exception as e:
            job.error = 'Yuklab olish xatosi: {}'.format(e)
            job.status = 'error'
            return jsonify(job.to_dict()), 400
    else:
        # Multipart — fayl yuklash
        if 'video' not in request.files:
            return jsonify({'error': 'Video fayl kerak'}), 400

        file = request.files['video']
        if not file.filename:
            return jsonify({'error': 'Fayl tanlanmagan'}), 400

        os.makedirs(TEMP_DIR, exist_ok=True)
        video_path = os.path.join(TEMP_DIR, file.filename)
        file.save(video_path)
        job.log('Fayl yuklandi: {}'.format(file.filename))

        config_str = request.form.get('config', '{}')
        try:
            config = json.loads(config_str)
        except Exception:
            config = {}

    if not video_path or not os.path.exists(video_path):
        job.error = 'Video fayl topilmadi'
        job.status = 'error'
        return jsonify(job.to_dict()), 400

    # Background da ishga tushirish
    thread = threading.Thread(
        target=process_job,
        args=(job, video_path, config),
        daemon=True
    )
    thread.start()

    return jsonify({'jobId': job_id, 'status': 'started'})


@app.route('/api/dub/<job_id>/status')
def get_status(job_id):
    """Jarayon holatini olish"""
    job = jobs.get(job_id)
    if not job:
        return jsonify({'error': 'Job topilmadi'}), 404
    return jsonify(job.to_dict())


@app.route('/api/dub/<job_id>/download')
def download_result(job_id):
    """Natija videoni yuklab olish"""
    job = jobs.get(job_id)
    if not job or not job.result_path:
        return jsonify({'error': 'Natija topilmadi'}), 404
    if not os.path.exists(job.result_path):
        return jsonify({'error': 'Fayl topilmadi'}), 404
    return send_file(
        job.result_path,
        as_attachment=True,
        download_name=os.path.basename(job.result_path)
    )


@app.route('/api/dub/<job_id>/srt')
def download_srt(job_id):
    """SRT subtitle yuklab olish"""
    job = jobs.get(job_id)
    if not job or not job.srt_path:
        return jsonify({'error': 'SRT topilmadi'}), 404
    if not os.path.exists(job.srt_path):
        return jsonify({'error': 'Fayl topilmadi'}), 404
    return send_file(
        job.srt_path,
        as_attachment=True,
        download_name=os.path.basename(job.srt_path)
    )


@app.route('/api/jobs')
def list_jobs():
    """Barcha jarayonlar ro'yxati"""
    return jsonify([j.to_dict() for j in jobs.values()])


if __name__ == '__main__':
    print('=' * 50)
    print('  ANIME DUBBER SERVER')
    print('  http://localhost:5000')
    print('=' * 50)
    print()
    print('Admin panelda "Dublyaj" rejimini oching')
    print('va server URL: http://localhost:5000 kiriting')
    print()
    app.run(host='0.0.0.0', port=5000, debug=False)
