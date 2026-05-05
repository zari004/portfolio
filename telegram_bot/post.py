"""
Telegram Design Bot — Zarnigor Orifova
Har kuni avtomatik dizayn postlari yuboradi.
Groq (LLama3) + Leonardo.ai + Telegram Bot API
"""
import os, json, time, random, requests, base64
from datetime import datetime, timezone, timedelta

# ── ENV ───────────────────────────────────────────────────────────────────────
BOT_TOKEN    = os.environ['TG_BOT_TOKEN']
CHANNEL_ID   = os.environ.get('TG_CHANNEL_ID', '@deardsgn')
LEONARDO_KEY = os.environ.get('LEONARDO_API_KEY', '')
GROQ_KEY     = os.environ.get('GROQ_API_KEY', '')
GITHUB_TOKEN = os.environ['GITHUB_TOKEN']
GITHUB_REPO  = os.environ['GITHUB_REPO']

# Toshkent vaqt zonasi (UTC+5)
TZ_OFFSET = 5

# ── RUBRIKALAR ────────────────────────────────────────────────────────────────
RUBRICS = {
  'trend': {
    'emoji': '📈',
    'title': 'Trend',
    'desc': '2025 yildagi dizayn trendlari va yangiliklar',
    'image_prompt': 'modern graphic design trend 2025, {style}, professional, editorial, minimalist composition, high quality',
  },
  'tip': {
    'emoji': '💡',
    'title': 'Maslahat',
    'desc': 'Dizayn bo\'yicha amaliy maslahatlar',
    'image_prompt': 'clean graphic design educational poster, {style}, typography focused, professional layout',
  },
  'color': {
    'emoji': '🎨',
    'title': 'Rang',
    'desc': 'Rang psixologiyasi, kombinatsiyalar va palittralar',
    'image_prompt': 'beautiful color palette design, {style}, harmonious colors, brand identity, professional',
  },
  'typography': {
    'emoji': '✍️',
    'title': 'Tipografiya',
    'desc': 'Shrift va tipografiya asoslari',
    'image_prompt': 'editorial typography design, {style}, font pairing, text layout, clean and modern',
  },
  'logo': {
    'emoji': '⚡',
    'title': 'Logo',
    'desc': 'Logo dizayn va brending',
    'image_prompt': 'minimalist logo design concept, {style}, vector style, professional brand identity',
  },
  'inspiration': {
    'emoji': '✨',
    'title': 'Ilhom',
    'desc': 'Ilhomlantiruvchi loyihalar va g\'oyalar',
    'image_prompt': 'award winning graphic design portfolio piece, {style}, stunning visual composition, creative concept',
  },
  'tool': {
    'emoji': '🛠',
    'title': 'Vosita',
    'desc': 'Dizaynerlarga foydali vositalar va resurslar',
    'image_prompt': 'modern design workspace mockup, {style}, professional tools, creative setup',
  },
  'mindset': {
    'emoji': '🧠',
    'title': 'Fikr',
    'desc': 'Dizayn falsafasi va kreativlik haqida',
    'image_prompt': 'conceptual creative design, abstract minimalist art, {style}, thought provoking visual',
  },
}

IMAGE_STYLES = [
  'dark background', 'light minimal', 'vibrant colorful', 'black and white',
  'gradient modern', 'flat design', 'premium luxury', 'bold and dynamic',
]

# ── GROQ CAPTION GENERATOR ────────────────────────────────────────────────────
SYSTEM_PROMPT = """Siz O'zbekistonning mashhur grafik dizayner va blogerisisz.
Sizning Telegram kanalingiz (@deardsgn) bor va u yerda dizayn haqida post yozasiz.

YOZISH USLUBI (quyidagi kanallar uslubidan o'rgan):
- Oddiy, samimiy, do'stona — lekin professional
- Qisqa va mazmunli — ortiqcha gap yo'q
- O'zbek tilida yozing. Ingliz atamalar (logo, branding, typography...) o'zbek gapda ishlatsa bo'ladi
- 2-4 ta emoji ishlatish (ko'p emas)
- Har post biror qimmatli fikr, ma'lumot yoki taassurot beradi
- Ba'zan shaxsiy tajriba ulashing ("men ham bu xatoni qilganman...")
- O'quvchini fikrlashga yoki javob berishga undang
- Post 3-6 qatordan iborat bo'lsin

POST TUZILISHI:
1. Kuchli birinchi qator (diqqatni tortadigan)
2. Asosiy g'oya (2-4 qator)
3. Xulosa yoki savol (1 qator)

QOIDALAR:
- Salbiy yoki kamsituvchi narsa yozmang
- Reklama ovozida yozmang
- Haqiqiy, jonli tuyg'u bilan yozing
- "bizga murojaat qiling" tipidagi quruq reklama YOQMAYDI
"""

HASHTAG_SETS = {
  'trend':      '#dizayntrendlari #graphicdesign #design2025 #trendingdesign #dizayn #kreativ',
  'tip':        '#dizaynmaslahat #designtips #grafika #dizaynchi #o\'rganamiz #designhacks',
  'color':      '#ranglar #colorpalette #colortheory #colordesign #dizayn #brandcolor',
  'typography': '#tipografiya #typography #font #typedesign #dizayn #shrift',
  'logo':       '#logodesign #logo #branding #brandidentity #logotype #dizayn #branddesign',
  'inspiration': '#dizaynilhom #designinspiration #creativework #portfolio #graphicdesign #behance',
  'tool':       '#dizaynvositalar #designtools #figma #adobe #creativesoftware #dizaynchi',
  'mindset':    '#dizaynfikr #creativelife #designthinking #kreativlik #dizayn #mindset',
}

COMMON_TAGS = '#zarnigordesign #o\'zbekdizayner #uzbekdesign #freelancedesigner'


def groq_generate(rubric_key, rubric):
  """Groq orqali post matni generatsiya qilish"""
  if not GROQ_KEY:
    return fallback_caption(rubric_key, rubric)

  user_prompt = f"""Quyidagi rubrika uchun Telegram post yozing:

Rubrika: {rubric['emoji']} {rubric['title']}
Mavzu: {rubric['desc']}
Bugun: {datetime.now(timezone(timedelta(hours=TZ_OFFSET))).strftime('%A, %d %B %Y')}

Post matni (hashtag yo'q, faqat matn):"""

  try:
    r = requests.post(
      'https://api.groq.com/openai/v1/chat/completions',
      headers={'Authorization': f'Bearer {GROQ_KEY}', 'Content-Type': 'application/json'},
      json={
        'model': 'llama-3.3-70b-versatile',
        'messages': [
          {'role': 'system', 'content': SYSTEM_PROMPT},
          {'role': 'user', 'content': user_prompt},
        ],
        'max_tokens': 300,
        'temperature': 0.85,
      },
      timeout=30
    )
    if r.ok:
      text = r.json()['choices'][0]['message']['content'].strip()
      print(f'Groq generated: {text[:80]}...')
      return text
    else:
      print(f'Groq error: {r.text}')
      return fallback_caption(rubric_key, rubric)
  except Exception as e:
    print(f'Groq exception: {e}')
    return fallback_caption(rubric_key, rubric)


def fallback_caption(rubric_key, rubric):
  """Groq ishlamasa — zaxira shablonlar"""
  templates = {
    'trend': [
      "📈 2025 yil dizayni qaysi yo'nalishda bormoqda?\n\nMinimalizm, bold tipografiya va AI generatsiya — bular bugungi asosiy trendlar. Lekin eng muhimi: maqsadsiz bezak emas, toza va aniq vizual.\n\nSen qaysi trendni ishlatasan?",
      "📈 Har yili yangi trendlar keladi. Lekin yaxshi dizayn zamonsiz.\n\nHozirgi trendlarni bilish — yaxshi. Ularni ko'r-ko'rona kopiyalash — yo'q.\n\nQandaydir trendni ko'rib hayron qoldingizmi?",
    ],
    'tip': [
      "💡 Eng ko'p qilingan xato: to'g'ri bo'shliq (whitespace) qoldirmaslik.\n\nBo'sh joy — bu zaiflik emas, bu nafas. Elementlar bir-biriga \"nafas olsin\" — shunda dizayn yengil ko'rinadi.\n\nBu maslahat siz uchun foydali bo'ldimi?",
      "💡 Yangi dizayner bo'lsa — avval o'qing, keyin qiling.\n\nMen ham boshida hamma narsani bir vaqtda o'rganmoqchi bo'ldim. Natija — hech narsa chuqur o'rganilmadi.\n\nBitta narsani yaxshi o'rgan. Qolgani o'zi keladi.",
    ],
    'color': [
      "🎨 Rang tanlash — eng qiyin ish emas, eng muhim ish.\n\nBrend rangi — bu shunchaki chiroyli emas. U hissiyot uyg'otadi, ishonch beradi, esda qoladi.\n\nSizning sevimli rang kombinatsiyangiz qaysi?",
    ],
    'typography': [
      "✍️ 2 xil shrift yetarli. Ko'pincha.\n\nKo'pchilik 5-6 xil shrift aralashtirib, vizual tartibsizlik yaratadi. Minimalizm tipografiyada ham ishlaydi.\n\nSiz qaysi shriftlarni ko'p ishlatasiz?",
    ],
    'logo': [
      "⚡ Yaxshi logo — oddiy. Juda oddiy.\n\nKo'p detal = tezda esdan chiqadi. Nike, Apple, Mercedes — barchasi geometrik soddalik.\n\nSizning eng yoqqan logo qaysi?",
    ],
    'inspiration': [
      "✨ Ba'zan eng yaxshi g'oya — tashqaridan keladi.\n\nBehance, Dribbble, real hayot, arxitektura... Ilhom hamma joyda. Ko'rish kerak, xolos.\n\nBugun sizni nima ilhomlantirdi?",
    ],
    'tool': [
      "🛠 Figma'ni biladigan dizayner — zamonaviy dizayner.\n\nLekin vosita faqat vosita. Figma bilmasang ham yaxshi dizayn qilsa bo'ladi. Bilsang — ancha tez va qulay.\n\nSiz qaysi dasturda ishlaysiz?",
    ],
    'mindset': [
      "🧠 Dizayn — bu muammo yechish.\n\nChiroyli qilish — bu natija. Lekin bosh maqsad: foydalanuvchi uchun qulay va aniq bo'lsin.\n\nBugun qanday muammo yechdingiz?",
    ],
  }
  options = templates.get(rubric_key, templates['tip'])
  return random.choice(options)


# ── LEONARDO ──────────────────────────────────────────────────────────────────
def generate_image(rubric_key, rubric):
  if not LEONARDO_KEY:
    raise Exception('LEONARDO_API_KEY sozlanmagan')

  style = random.choice(IMAGE_STYLES)
  prompt = rubric['image_prompt'].format(style=style)
  print(f'Image prompt: {prompt[:70]}...')

  h = {'Authorization': f'Bearer {LEONARDO_KEY}', 'Content-Type': 'application/json'}

  # Model: Leonardo Phoenix (eng yaxshi bepul model)
  r = requests.post('https://cloud.leonardo.ai/api/rest/v1/generations', headers=h, json={
    'prompt': prompt,
    'negative_prompt': 'blurry, low quality, ugly, watermark, text overlay, amateur',
    'modelId': 'de7d3faf-762f-48e0-b3b7-9d0ac3a3fcf5',  # Leonardo Phoenix
    'width': 1024, 'height': 1024,
    'num_images': 1,
    'guidance_scale': 7,
    'presetStyle': 'CINEMATIC',
  })

  if not r.ok:
    # Fallback: Creative model
    r = requests.post('https://cloud.leonardo.ai/api/rest/v1/generations', headers=h, json={
      'prompt': prompt,
      'modelId': 'b24e16ff-06e3-43eb-8d33-4416c2d75876',
      'width': 1024, 'height': 1024,
      'num_images': 1,
    })

  if not r.ok:
    raise Exception(f'Leonardo error: {r.text}')

  gen_id = r.json()['sdGenerationJob']['generationId']

  for _ in range(40):
    time.sleep(5)
    c = requests.get(f'https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}', headers=h)
    g = c.json().get('generations_by_pk', {})
    if g.get('status') == 'COMPLETE':
      imgs = g.get('generated_images', [])
      if imgs:
        return imgs[0]['url']
    elif g.get('status') == 'FAILED':
      raise Exception('Leonardo generation failed')

  raise Exception('Leonardo timeout')


# ── GITHUB ────────────────────────────────────────────────────────────────────
def gh_get(path):
  r = requests.get(
    f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}',
    headers={'Authorization': f'token {GITHUB_TOKEN}'}
  )
  if r.status_code == 200:
    d = r.json()
    content = base64.b64decode(d['content'].replace('\n', '')).decode('utf-8')
    return json.loads(content), d['sha']
  return None, None


def gh_put(path, data, sha, msg):
  content = base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8')).decode('utf-8')
  body = {'message': msg, 'content': content}
  if sha:
    body['sha'] = sha
  r = requests.put(
    f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}',
    json=body,
    headers={'Authorization': f'token {GITHUB_TOKEN}', 'Content-Type': 'application/json'}
  )
  return r.ok


# ── TELEGRAM ──────────────────────────────────────────────────────────────────
def send_photo(image_url, caption):
  r = requests.post(
    f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto',
    json={'chat_id': CHANNEL_ID, 'photo': image_url, 'caption': caption, 'parse_mode': 'HTML'},
    timeout=30
  )
  if not r.ok:
    raise Exception(f'Telegram error: {r.text}')
  return r.json()['result']['message_id']


# ── SCHEDULE CHECK ────────────────────────────────────────────────────────────
def get_current_slot(schedule):
  """Hozirgi vaqtga mos slot topish"""
  now_tashkent = datetime.now(timezone(timedelta(hours=TZ_OFFSET)))
  day_names = ['mon','tue','wed','thu','fri','sat','sun']
  current_day = day_names[now_tashkent.weekday()]
  current_time = now_tashkent.strftime('%H:%M')

  # Manual trigger bo'lsa
  manual_cat = os.environ.get('MANUAL_CATEGORY', '')
  if manual_cat:
    return {'category': manual_cat, 'rubric': manual_cat}

  slots = schedule.get('slots', [])
  for slot in slots:
    if slot.get('enabled', True) and slot.get('day') == current_day:
      slot_time = slot.get('time', '10:00')
      # ±30 daqiqa oralig'ida bo'lsa, bu slot
      slot_h, slot_m = map(int, slot_time.split(':'))
      cur_h, cur_m = map(int, current_time.split(':'))
      diff = abs((cur_h * 60 + cur_m) - (slot_h * 60 + slot_m))
      if diff <= 30:
        return slot

  return None


# ── MAIN ──────────────────────────────────────────────────────────────────────
def main():
  print(f'Bot ishga tushdi: {datetime.now(timezone(timedelta(hours=TZ_OFFSET))).strftime("%Y-%m-%d %H:%M")} (Toshkent)')

  schedule, _ = gh_get('telegram_bot/schedule.json')
  if not schedule:
    schedule = {}

  if not schedule.get('enabled', True):
    print('Bot o\'chirilgan (enabled: false)'); return

  # Slot topish (yoki manual)
  slot = get_current_slot(schedule)
  is_manual = os.environ.get('MANUAL_TRIGGER', 'false').lower() in ('true', '1')
  if not slot and not is_manual:
    print('Bu vaqtda post yo\'q — jadval bo\'yicha emas'); return
  if not slot and is_manual:
    # Manual trigger bo'lsa, bugungi birinchi enabled slotdan oladi, yoki 'tip' ishlatadi
    enabled_slots = [s for s in schedule.get('slots', []) if s.get('enabled', True)]
    slot = enabled_slots[0] if enabled_slots else {'category': 'tip'}

  rubric_key = (slot or {}).get('category', 'tip')
  rubric = RUBRICS.get(rubric_key, RUBRICS['tip'])

  print(f'Rubrika: {rubric["emoji"]} {rubric["title"]}')

  # Matn generatsiya
  caption_text = groq_generate(rubric_key, rubric)

  # Hashtags
  tags = HASHTAG_SETS.get(rubric_key, '') + ' ' + COMMON_TAGS
  caption = f'{caption_text}\n\n{tags}'

  print(f'Caption: {caption[:100]}...')

  # Rasm generatsiya
  image_url = generate_image(rubric_key, rubric)
  print(f'Image: {image_url}')

  # Telegram ga yuborish
  msg_id = send_photo(image_url, caption)
  print(f'Yuborildi! msg_id={msg_id}')

  # Tarix saqlash
  history, sha = gh_get('telegram_bot/history.json')
  if not isinstance(history, list):
    history = []

  history.insert(0, {
    'id': msg_id,
    'image': image_url,
    'caption': caption_text,
    'hashtags': tags,
    'rubric': rubric_key,
    'rubric_title': rubric['title'],
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'status': 'sent',
  })
  gh_put('telegram_bot/history.json', history[:300], sha, 'Telegram: history yangilandi')
  print('Tayyor!')


if __name__ == '__main__':
  main()
