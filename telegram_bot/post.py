"""
Telegram Design Bot — Zarnigor Orifova
Har kuni avtomatik dizayn postlari yuboradi.
Pipeline: Groq (matn) → Tekshiruvchi Agent → Telegram
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
    'image_prompt': 'abstract modern design aesthetic 2025, {style}, geometric shapes, NO TEXT, NO WORDS, NO LETTERS, clean composition, high quality, award winning',
  },
  'tip': {
    'emoji': '💡',
    'title': 'Maslahat',
    'desc': 'Dizayn bo\'yicha amaliy maslahatlar',
    'image_prompt': 'creative designer workspace flat lay, {style}, NO TEXT NO LETTERS, tools and stationery, professional photography',
  },
  'color': {
    'emoji': '🎨',
    'title': 'Rang',
    'desc': 'Rang psixologiyasi, kombinatsiyalar va palittralar',
    'image_prompt': 'stunning color palette abstract art, {style}, NO TEXT, harmonious color swatches, gradient flow, brand identity mood board',
  },
  'typography': {
    'emoji': '✍️',
    'title': 'Tipografiya',
    'desc': 'Shrift va tipografiya asoslari',
    'image_prompt': 'abstract letterform art sculpture, {style}, single elegant letter form, NO READABLE TEXT, 3d render, artistic typography concept',
  },
  'logo': {
    'emoji': '⚡',
    'title': 'Logo',
    'desc': 'Logo dizayn va brending',
    'image_prompt': 'minimalist abstract logo mark concept, {style}, NO TEXT NO WORDS, clean geometric symbol, vector aesthetic, white background or dark',
  },
  'inspiration': {
    'emoji': '✨',
    'title': 'Ilhom',
    'desc': 'Ilhomlantiruvchi loyihalar va g\'oyalar',
    'image_prompt': 'stunning abstract art installation, {style}, NO TEXT, visually arresting composition, museum quality, dramatic lighting, contemporary art',
  },
  'tool': {
    'emoji': '🛠',
    'title': 'Vosita',
    'desc': 'Dizaynerlarga foydali vositalar va resurslar',
    'image_prompt': 'minimal creative tools flat lay photography, {style}, NO TEXT NO LABELS, Pantone chips pens notebooks, professional product photography',
  },
  'mindset': {
    'emoji': '🧠',
    'title': 'Fikr',
    'desc': 'Dizayn falsafasi va kreativlik haqida',
    'image_prompt': 'surreal conceptual abstract art, {style}, NO TEXT, brain creativity concept, flowing shapes, deep perspective, cinematic',
  },
}

IMAGE_STYLES = [
  'ultra dark moody background', 'crisp white minimal', 'vibrant neon colorful',
  'elegant black and gold', 'deep gradient purple blue', 'earthy tones natural',
  'electric green accent dark', 'soft pastel dreamy', 'bold red and black',
]

# ── GROQ CAPTION GENERATOR ────────────────────────────────────────────────────
SYSTEM_PROMPT = """Siz O'zbekistonning tajribali grafik dizayner va Telegram blogerisisz (@deardsgn).

MAJBURIY FORMAT — Telegram HTML:
- Muhim so'z yoki iborani <b>qalin</b> qilib yozing (har postda 2-4 ta)
- Taassurot yoki shaxsiy fikrni <i>kursiv</i> qiling (har postda 1-2 ta)
- Hech qachon oddiy tekst bilan to'ldirmang

USLUB VARIATSIYALARI — har postda BOSHQACHA boshlang:
• Ba'zan qisqa provokatsion savol bilan: "Nima uchun ko'p dizaynerlar bu xatoni qiladi?"
• Ba'zan shaxsiy voqea bilan: "Kecha mijoz loyihasida shunday narsaga duch keldim..."
• Ba'zan qattiq bayonot bilan: "Ko'pchilik aytadigan narsa — yolg'on."
• Ba'zan ro'yxat bilan: 3 ta sabab, 5 ta belgi, 2 ta variant
• Ba'zan qisqa hikoya bilan: muammo → yechim → xulosa

MAZMUN QOIDALARI:
- O'zbek tilida, lekin branding, whitespace, grid, layout — inglizcha atamalar OK
- 1-2 ta emoji yetarli (ko'p emas)
- Post 4-8 qator (na juda qisqa, na juda uzun)
- Har doim 1 ta aniq qimmatli ma'lumot bo'lsin
- Oxirida savol YOKI qisqa harakat chaqiruvi (ixtiyoriy)
- "Bizga murojaat qiling" YOZMANG
- Har post BOSHQACHA strukturada bo'lsin

MANBA LINKLARI — MAJBURIY:
- Har postda kamida 1 ta manba linki bo'lsin
- Format: <a href="url">manba nomi</a>
- Linkni matn ichida TABIIY joylashtiring, masalan: "...bu haqda <a href="url">Behance</a>da ko'rishingiz mumkin"
- Linkni post oxirida alohida qo'ymang, matn oqimida qo'shing

MISOL (qanday ko'rinishi kerak):
<b>Whitespace</b> — dizayndagi eng kam baholi, eng ko'p noto'g'ri tushuniladigan element.

Ko'pchilik bo'sh joyni "to'ldirish kerak" deb o'ylaydi. <i>Aslida bo'sh joy — bu nafas, bu ritm.</i>

Apple'ning sahifalariga qarang: <b>kontent ozmi?</b> Yo'q. Bo'sh joy ko'pmi? Ha. Natija? Premium his.

Keyingi loyihangizda ataylab 20% ko'proq whitespace qoldiring — farqni ko'rasiz."""

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

# ── MANBALAR (rubrika bo'yicha) ──────────────────────────────────────────────
SOURCES = {
  'trend': [
    {'name': 'Behance', 'url': 'https://www.behance.net/galleries/graphic-design'},
    {'name': 'Awwwards', 'url': 'https://www.awwwards.com/websites/trend/'},
    {'name': 'Dribbble', 'url': 'https://dribbble.com/shots/popular'},
    {'name': 'DesignBoom', 'url': 'https://www.designboom.com/design/'},
  ],
  'tip': [
    {'name': 'Smashing Magazine', 'url': 'https://www.smashingmagazine.com/category/design/'},
    {'name': 'UX Planet', 'url': 'https://uxplanet.org/'},
    {'name': 'Nielsen Norman', 'url': 'https://www.nngroup.com/articles/'},
  ],
  'color': [
    {'name': 'Coolors', 'url': 'https://coolors.co/palettes/trending'},
    {'name': 'Color Hunt', 'url': 'https://colorhunt.co/'},
    {'name': 'Adobe Color', 'url': 'https://color.adobe.com/trends'},
  ],
  'typography': [
    {'name': 'Google Fonts', 'url': 'https://fonts.google.com/'},
    {'name': 'Typewolf', 'url': 'https://www.typewolf.com/'},
    {'name': 'Fonts In Use', 'url': 'https://fontsinuse.com/'},
  ],
  'logo': [
    {'name': 'LogoLounge', 'url': 'https://www.logolounge.com/'},
    {'name': 'Brand New', 'url': 'https://www.underconsideration.com/brandnew/'},
    {'name': 'Logomoose', 'url': 'https://www.logomoose.com/'},
  ],
  'inspiration': [
    {'name': 'Behance', 'url': 'https://www.behance.net/'},
    {'name': 'Pinterest Design', 'url': 'https://www.pinterest.com/categories/design/'},
    {'name': 'It\'s Nice That', 'url': 'https://www.itsnicethat.com/'},
  ],
  'tool': [
    {'name': 'Figma Community', 'url': 'https://www.figma.com/community'},
    {'name': 'ProductHunt Design', 'url': 'https://www.producthunt.com/topics/design-tools'},
    {'name': 'Muzli', 'url': 'https://muz.li/'},
  ],
  'mindset': [
    {'name': 'Creative Boom', 'url': 'https://www.creativeboom.com/'},
    {'name': 'AIGA Eye on Design', 'url': 'https://eyeondesign.aiga.org/'},
    {'name': 'The Futur', 'url': 'https://thefutur.com/blog'},
  ],
}

MAX_QUALITY_RETRIES = 3

# ── TEKSHIRUVCHI AGENT ───────────────────────────────────────────────────────
REVIEWER_PROMPT = """Siz professional kontent tekshiruvchi agentisiz. Telegram dizayn kanaliga (@deardsgn) yuboriladigan postni tekshirishingiz kerak.

TEKSHIRISH MEZONLARI:
1. FORMAT: <b>qalin</b> va <i>kursiv</i> HTML teglar bor-yo'qligi (kamida 2 ta <b>, 1 ta <i>)
2. UZUNLIK: 4-8 qator orasida bo'lishi kerak (juda qisqa yoki juda uzun emas)
3. QIMMAT: Post o'quvchiga biror yangi bilim yoki foydali ma'lumot berishi kerak
4. USLUB: Monoton, boring, shart qolipli bo'lmasin. Tirik, qiziqarli bo'lishi kerak
5. GRAMMATIK: O'zbek tili grammatikasi to'g'ri bo'lishi kerak
6. MANBA: Post ichida kamida bitta <a href="...">manba nomi</a> link bo'lishi kerak
7. REKLAMA: "Bizga murojaat qiling", "Buyurtma bering" kabi reklama bo'lmasligi kerak
8. TAKROR: Oldingi postlar bilan bir xil bo'lmasligi kerak (har safar boshqacha struktura)

JAVOB FORMATI (faqat JSON):
{"passed": true} — agar post tayyor bo'lsa
{"passed": false, "errors": ["xato1", "xato2"], "suggestion": "qanday tuzatish kerak"} — agar post yaroqsiz bo'lsa

Faqat JSON qaytaring, boshqa hech narsa yozmang."""


def quality_check(post_text, rubric_key):
  """Tekshiruvchi agent: postni sifat bo'yicha baholash"""
  if not GROQ_KEY:
    return {'passed': True}

  try:
    r = requests.post(
      'https://api.groq.com/openai/v1/chat/completions',
      headers={'Authorization': f'Bearer {GROQ_KEY}', 'Content-Type': 'application/json'},
      json={
        'model': 'llama-3.3-70b-versatile',
        'messages': [
          {'role': 'system', 'content': REVIEWER_PROMPT},
          {'role': 'user', 'content': f'Rubrika: {rubric_key}\n\nPost matni:\n{post_text}'},
        ],
        'max_tokens': 200,
        'temperature': 0.2,
      },
      timeout=20
    )
    if r.ok:
      raw = r.json()['choices'][0]['message']['content'].strip()
      # JSON ajratish
      if '{' in raw:
        json_str = raw[raw.index('{'):raw.rindex('}')+1]
        result = json.loads(json_str)
        print(f'Tekshiruv: {"✅ O\'tdi" if result.get("passed") else "❌ Qaytarildi"}')
        if not result.get('passed'):
          print(f'  Xatolar: {result.get("errors", [])}')
        return result
    return {'passed': True}
  except Exception as e:
    print(f'Tekshiruv xatosi: {e}')
    return {'passed': True}


def groq_generate(rubric_key, rubric, feedback=None):
  """Groq orqali post matni generatsiya qilish (manba linklari bilan)"""
  if not GROQ_KEY:
    return fallback_caption(rubric_key, rubric)

  styles = [
    "Shaxsiy tajriba yoki voqeadan boshlang",
    "Provokatsion savol bilan boshlang",
    "Qattiq, to'g'ridan-to'g'ri bayonot bilan boshlang",
    "Ro'yxat formatida yozing (3-5 ta band)",
    "Muammo → yechim → xulosa strukturasida yozing",
    "Mashhur brend yoki dizaynerga havola qilib boshlang",
    "Umumiy noto'g'ri tushunchani rad eting",
  ]
  chosen_style = random.choice(styles)

  # Manba linklari
  rubric_sources = SOURCES.get(rubric_key, SOURCES['tip'])
  selected_sources = random.sample(rubric_sources, min(2, len(rubric_sources)))
  source_info = '\n'.join([f'  - {s["name"]}: {s["url"]}' for s in selected_sources])

  user_prompt = f"""Rubrika: {rubric['emoji']} {rubric['title']}
Mavzu: {rubric['desc']}
Bugun: {datetime.now(timezone(timedelta(hours=TZ_OFFSET))).strftime('%A, %d %B %Y')}
Yozish uslubi: {chosen_style}

MANBALAR (post ichida kamida 1 ta link shu manbalardan qo'shing):
{source_info}
Link formati: <a href="url">manba nomi</a> — matn ichida tabiiy joylang.

Telegram HTML formatida post yozing (<b>qalin</b>, <i>kursiv</i>, <a href="...">link</a> ishlatish MAJBURIY).
Hashtag yozmang. Faqat post matni:"""

  # Agar feedback bo'lsa (qayta yozish uchun)
  if feedback:
    user_prompt += f'\n\n⚠️ OLDINGI POST RAD ETILDI. Xatolar:\n{feedback}\nYuqoridagi xatolarni tuzatib QAYTADAN yozing:'

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
        'max_tokens': 400,
        'temperature': 0.85 if not feedback else 0.7,
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

  # ── PIPELINE: Matn → Tekshiruv → Qayta yozish (agar kerak) ──
  caption_text = None
  feedback = None

  for attempt in range(MAX_QUALITY_RETRIES):
    print(f'\n--- Urinish {attempt + 1}/{MAX_QUALITY_RETRIES} ---')

    # 1. Matn agenti: post generatsiya
    caption_text = groq_generate(rubric_key, rubric, feedback=feedback)

    # 2. Tekshiruvchi agent: sifat nazorati
    review = quality_check(caption_text, rubric_key)

    if review.get('passed'):
      print(f'✅ Post tekshiruvdan o\'tdi (urinish {attempt + 1})')
      break
    else:
      errors = review.get('errors', [])
      suggestion = review.get('suggestion', '')
      feedback = '\n'.join([f'- {e}' for e in errors])
      if suggestion:
        feedback += f'\nTaklif: {suggestion}'
      print(f'🔄 Qayta yozishga yuborildi...')

  # Hashtags
  tags = HASHTAG_SETS.get(rubric_key, '') + ' ' + COMMON_TAGS
  caption = f'{caption_text}\n\n{tags}'

  print(f'\nFinal caption: {caption[:120]}...')

  # Rasm generatsiya
  image_url = generate_image(rubric_key, rubric)
  print(f'Image: {image_url}')

  # Telegram ga yuborish
  msg_id = send_photo(image_url, caption)
  print(f'✅ Yuborildi! msg_id={msg_id}')

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
    'attempts': attempt + 1,
  })
  gh_put('telegram_bot/history.json', history[:300], sha, 'Telegram: history yangilandi')
  print('Tayyor!')


if __name__ == '__main__':
  main()
