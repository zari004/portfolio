import os, json, time, random, requests, base64
from datetime import datetime, timezone

BOT_TOKEN     = os.environ['TG_BOT_TOKEN']
CHANNEL_ID    = os.environ.get('TG_CHANNEL_ID', '@deardsgn')
LEONARDO_KEY  = os.environ.get('LEONARDO_API_KEY', '')
GITHUB_TOKEN  = os.environ['GITHUB_TOKEN']
GITHUB_REPO   = os.environ['GITHUB_REPO']

# ── PROMPTS ────────────────────────────────────────────────────────────────────
PROMPTS = {
  'logo': [
    'minimalist logo design for a modern tech startup, clean vector style, white background, professional branding',
    'elegant luxury brand logo, gold typography on dark background, sophisticated monogram style',
    'bold geometric logo for architecture firm, black and white, sharp angular shapes, premium quality',
    'playful colorful logo for children education app, flat design, friendly characters, vibrant palette',
    'clean minimal wordmark logo design, sans-serif typography, premium brand identity, white background',
  ],
  'poster': [
    'modern music festival poster, bold typography, neon colors on dark background, electric atmosphere',
    'minimalist movie poster design, strong visual composition, cinematic mood, professional layout',
    'elegant fashion brand poster, editorial style, high contrast, luxury aesthetic, model silhouette',
    'vibrant food and restaurant promotional poster, appetizing colors, clean layout, premium quality',
    'corporate business event poster, professional, clean grid layout, blue and white corporate palette',
  ],
  'social': [
    'Instagram carousel post design for luxury fashion brand, minimal aesthetic, editorial typography',
    'social media banner for tech product launch, futuristic UI mockup, dark gradient background',
    'engaging Instagram story design for lifestyle brand, bold typography, warm earthy color palette',
    'professional LinkedIn banner design, corporate modern, clean lines, subtle blue gradient',
    'TikTok thumbnail design for creative content, eye-catching, bold colors, dynamic composition',
  ],
  'business_card': [
    'premium minimalist business card design, dark background, foil stamp effect, luxury typography',
    'creative double-sided business card, bold color gradient, modern typographic layout',
    'elegant white business card with embossed details, clean Swiss design, precision and quality',
    'vibrant startup business card, full color illustration, unique die-cut shape, memorable design',
  ],
  'branding': [
    'complete brand identity for sustainable eco startup, earthy colors, organic shapes, clean minimal',
    'luxury hotel brand identity system, gold and black, sophisticated typography, premium packaging',
    'energetic sports brand identity, bold red and black, dynamic shapes, athletic performance feel',
    'artisan bakery brand identity, handcrafted warmth, serif typography, beige and brown palette',
  ],
}

CAPTIONS_UZ = [
  "Yangi kreativ dizayn! Sizning loyihangiz uchun ham shu darajada professional dizayn kerakmi? ✉️ Murojaat qiling",
  "Grafik dizayn — brendingizning ovozi. Kuchli vizual = ko'proq mijozlar! 🎨",
  "Har bir loyiha — bu alohida hikoya. Sizning brendingizning hikoyasini birgalikda yozamiz 🚀",
  "Professional dizayn xizmatlari: logo, brending, poster, SMM kontent va boshqalar. DM yozing! 📩",
  "Dizayn faqat chiroyli emas — u sotadi, ishontiradi, esda qoladi. Hisob-kitob uchun yozing ✨",
]

CAPTIONS_EN = [
  "Fresh creative work dropping! Need professional design for your project? Let's talk! 📩",
  "Design that converts. Strong visuals = more clients, more trust, more sales 🎨",
  "Every brand has a story — let's tell yours through exceptional design 🚀",
  "Professional graphic design: logos, branding, posters, social media content. DM for inquiries! ✨",
  "Design is not just what it looks like — it's how it works. Let's create something great! 💪",
]

HASHTAGS_BY_CAT = {
  'logo':          '#logodesign #logo #branding #logodesigner #brandidentity #logotype #logomaker',
  'poster':        '#posterdesign #poster #graphicdesign #typography #printdesign #creativedesign',
  'social':        '#socialmediadesign #contentcreation #instagramdesign #digitalmarketing #smm',
  'business_card': '#businesscard #businesscarddesign #printdesign #brandidentity #stationerydesign',
  'branding':      '#branding #brandidentity #branddesign #visualidentity #brandingstrategy',
}

COMMON_TAGS = '#zarnigordesign #graphicdesign #designer #freelancedesigner #designinspiration #uzbekdesign'


# ── GITHUB HELPERS ────────────────────────────────────────────────────────────
def gh_get(path):
  r = requests.get(f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}',
                   headers={'Authorization': f'token {GITHUB_TOKEN}'})
  if r.status_code == 200:
    d = r.json()
    return json.loads(base64.b64decode(d['content']).decode()), d['sha']
  return None, None

def gh_put(path, data, sha, msg):
  body = {'message': msg,
          'content': base64.b64encode(json.dumps(data, ensure_ascii=False, indent=2).encode()).decode()}
  if sha: body['sha'] = sha
  requests.put(f'https://api.github.com/repos/{GITHUB_REPO}/contents/{path}',
               json=body, headers={'Authorization': f'token {GITHUB_TOKEN}'})


# ── LEONARDO ──────────────────────────────────────────────────────────────────
def generate_image(prompt):
  if not LEONARDO_KEY:
    raise Exception('LEONARDO_API_KEY not set')
  h = {'Authorization': f'Bearer {LEONARDO_KEY}', 'Content-Type': 'application/json'}
  r = requests.post('https://cloud.leonardo.ai/api/rest/v1/generations', headers=h, json={
    'prompt': prompt,
    'modelId': 'b24e16ff-06e3-43eb-8d33-4416c2d75876',
    'width': 1024, 'height': 1024, 'num_images': 1, 'guidance_scale': 7,
  })
  if not r.ok: raise Exception(f'Leonardo error: {r.text}')
  gen_id = r.json()['sdGenerationJob']['generationId']

  for _ in range(30):
    time.sleep(5)
    c = requests.get(f'https://cloud.leonardo.ai/api/rest/v1/generations/{gen_id}', headers=h)
    g = c.json().get('generations_by_pk', {})
    if g.get('status') == 'COMPLETE':
      imgs = g.get('generated_images', [])
      if imgs: return imgs[0]['url']
    elif g.get('status') == 'FAILED':
      raise Exception('Leonardo generation failed')
  raise Exception('Leonardo timeout')


# ── TELEGRAM ──────────────────────────────────────────────────────────────────
def send_photo(image_url, caption):
  r = requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto', json={
    'chat_id': CHANNEL_ID, 'photo': image_url,
    'caption': caption, 'parse_mode': 'HTML',
  })
  if not r.ok: raise Exception(f'Telegram error: {r.text}')
  return r.json()['result']['message_id']


# ── MAIN ─────────────────────────────────────────────────────────────────────
def main():
  schedule, _ = gh_get('telegram_bot/schedule.json')
  if not schedule: schedule = {}

  if not schedule.get('enabled', True):
    print('Bot schedule disabled — skipping'); return

  cat  = schedule.get('category', 'logo')
  lang = schedule.get('language', 'uz')

  prompt = random.choice(PROMPTS.get(cat, PROMPTS['logo']))
  print(f'Category: {cat} | Prompt: {prompt[:70]}...')

  image_url = generate_image(prompt)
  print(f'Image: {image_url}')

  caption_text = random.choice(CAPTIONS_UZ if lang == 'uz' else CAPTIONS_EN)
  tags = HASHTAGS_BY_CAT.get(cat, '') + ' ' + COMMON_TAGS
  caption = f'{caption_text}\n\n{tags}'

  msg_id = send_photo(image_url, caption)
  print(f'Sent! msg_id={msg_id}')

  history, sha = gh_get('telegram_bot/history.json')
  if not isinstance(history, list): history = []
  history.insert(0, {
    'id': msg_id,
    'image': image_url,
    'caption': caption_text,
    'hashtags': tags,
    'category': cat,
    'prompt': prompt,
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'status': 'sent',
  })
  gh_put('telegram_bot/history.json', history[:200], sha, 'Telegram: history yangilandi')
  print('History saved. Done!')

if __name__ == '__main__':
  main()
