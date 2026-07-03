# Telegram Background Remover Bot

User က ပုံပို့လိုက်တာနဲ့ AI (rembg / isnet-general-use model) နဲ့ background ဖြုတ်ပြီး
transparent PNG အဖြစ် document အနေနဲ့ ပြန်ပို့ပေးတဲ့ bot။ **GPU မလိုအပ်ပါ** — CPU
server ပေါ်မှာပဲ run ဖြစ်ပါတယ်။

## ဘယ်လို အလုပ်လုပ်လဲ

1. User → Telegram bot ဆီ ပုံ (photo သို့မဟုတ် document) ပို့
2. Bot က ပုံကို download လုပ်
3. `rembg` (isnet-general-use model) နဲ့ background ဖြုတ်
4. Transparent PNG ကို **document** အနေနဲ့ ပြန်ပို့ (photo အနေနဲ့ ပို့ရင် Telegram
   က JPEG အဖြစ် compress လုပ်လို့ transparency ပျောက်တတ်ပါတယ်)

Concurrency ကို semaphore နဲ့ ကန့်သတ်ထားတာကြောင့် user အများကြီး တစ်ပြိုင်နက်
သုံးလည်း server မလွန်ကဲပါဘူး (config.py ထဲက `MAX_CONCURRENT_JOBS` နဲ့ ချိန်ညှိလို့ရ)။

## Local စမ်းသပ်ခြင်း

```bash
# 1. Bot token ရယူပါ — Telegram ထဲမှာ @BotFather ကို /newbot ပို့ပြီး token ယူပါ
cp .env.example .env
# .env ဖိုင်ထဲက BOT_TOKEN= ကို သင့် token နဲ့ အစားထိုးပါ

# 2. Dependencies install လုပ်ပါ
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Bot ကို run ပါ
python bot.py
```

ပထမဆုံးအကြိမ် run တဲ့အခါ `rembg` model (~170MB) ကို download လုပ်ဖို့ network
လိုအပ်ပါတယ် (တစ်ခါပဲ)။ ပြီးရင် local ~/.u2net folder ထဲမှာ cache ဖြစ်နေပါမယ်။

## Deploy လုပ်နည်း (GPU မလိုအပ်ပါ)

ဒီ bot ကို **polling mode** နဲ့ ရေးထားလို့ public domain/SSL စိတ်ပူစရာ
လုံးဝမလိုပါ — server တစ်ခုပေါ် run ထားရုံပါပဲ။

### Option 1 — Railway / Render (အလွယ်ဆုံး)

1. ဒီ folder ကို GitHub repo အသစ်တစ်ခု ဖန်တီးပြီး push လုပ်ပါ
2. Railway.app သို့မဟုတ် Render.com မှာ "New Project → Deploy from GitHub"
3. Environment variable `BOT_TOKEN` ကို dashboard ထဲမှာ ထည့်ပါ
4. Dockerfile ကို auto-detect လုပ်ပြီး build/deploy လုပ်ပေးပါလိမ့်မယ်
5. **Worker/Background service** အဖြစ် deploy လုပ်ပါ (Web service မဟုတ်ပါ —
   ဒီ bot က HTTP port listen မလုပ်ပါဘူး၊ polling ပဲ လုပ်ပါတယ်)

### Option 2 — VPS (DigitalOcean, Vultr, Hetzner — $5/mo credit)

```bash
git clone <your-repo-url>
cd bg_remover_bot
docker build -t bg-remover-bot .
docker run -d --name bg-bot --restart unless-stopped \
  -e BOT_TOKEN=your_token_here \
  bg-remover-bot
```

`--restart unless-stopped` ထည့်ထားတာကြောင့် server restart ဖြစ်ရင်လည်း bot
auto-start ပြန်ဖြစ်ပါလိမ့်မယ်။

### Option 2 — DigitalOcean Droplet (RAM ပိုပြီး quality အကောင်းဆုံး model သုံးလို့ရ)

`isnet-general-use` model (edge/hair quality အကောင်းဆုံး) ကို run ဖို့ **RAM 2GB** လိုအပ်ပါတယ်။ ဒါကြောင့် **2GB RAM Droplet ($12/လ)** ကို အကြံပြုပါတယ်။

**၁. Droplet ဖန်တီးပါ**
1. DigitalOcean dashboard → **"Create" → "Droplets"**
2. Image: **"Marketplace"** tab ကို ရွေးပြီး **"Docker"** ကို ရှာပါ (Ubuntu + Docker preinstalled — setup အရမ်းလွယ်သွားပါမယ်)
3. Size: **Basic → Premium AMD/Intel → 2GB RAM / 1 vCPU (~$12/လ)** ရွေးပါ
4. Authentication: **"Password"** ကို ရွေးပြီး password တစ်ခု သတ်မှတ်ပါ (SSH key နဲ့ ရင်းနှီးမှုမရှိသေးရင် Password က ရိုးရှင်းပါတယ်)
5. **"Create Droplet"** နှိပ်ပါ — ၁ မိနစ်လောက်နဲ့ ရပါလိမ့်မယ်

**၂. Droplet ထဲ ဝင်ပါ (Browser ကနေတိုက်ရိုက်၊ terminal app မလိုပါ)**
1. Droplet list ထဲက သင့် droplet ကို နှိပ်ပါ
2. **"Console"** (သို့) **"Launch Droplet Console"** ခလုတ်ကို နှိပ်ပါ — browser ထဲမှာ terminal တစ်ခု ပွင့်လာပါလိမ့်မယ်
3. `root` / password နဲ့ login ဝင်ပါ

**၃. Bot ကို Deploy လုပ်ပါ**

Console ထဲမှာ ဒီ command တွေကို တစ်ကြောင်းချင်း paste ပြီး Enter နှိပ်ပါ:

```bash
git clone https://github.com/<your-username>/bg-remover-bot.git
cd bg-remover-bot
docker build -t bg-remover-bot .
docker run -d --name bg-bot --restart unless-stopped \
  -e BOT_TOKEN=your_token_here \
  -e REMBG_MODEL=isnet-general-use \
  bg-remover-bot
```

`your-username` ကို GitHub username နဲ့၊ `your_token_here` ကို BotFather token နဲ့ အစားထိုးပါ။

**၄. အလုပ်ဖြစ်မဖြစ် စစ်ပါ**

```bash
docker logs -f bg-bot
```

`Run polling for bot @...` ဆိုတဲ့ စာကြောင်း ပေါ်ရင် အောင်မြင်ပါပြီ — Telegram ထဲ ပြန်သွားပြီး `/start` စမ်းပါ။ Log ကြည့်တာ ရပ်ချင်ရင် `Ctrl + C` နှိပ်ပါ (bot ကတော့ background မှာ ဆက်run နေဆဲပါ)။

**Update (code ပြင်တိုင်း) လုပ်နည်း:**

```bash
cd bg-remover-bot
git pull
docker build -t bg-remover-bot .
docker stop bg-bot && docker rm bg-bot
docker run -d --name bg-bot --restart unless-stopped \
  -e BOT_TOKEN=your_token_here \
  -e REMBG_MODEL=isnet-general-use \
  bg-remover-bot
```

## Traffic များလာရင် (Scaling)

- `MAX_CONCURRENT_JOBS` ကို server ရဲ့ CPU core အရေအတွက်နဲ့ ကိုက်ညီအောင်
  ချိန်ညှိပါ (core 2 လုံးဆို 2, core 4 လုံးဆို 3-4)
- User များများ တစ်ပြိုင်နက် တောင်းဆိုရင် queue ကြာလာနိုင်ပါတယ် — ဒီအခါ
  webhook mode + separate worker processes (Celery/RQ) ပြောင်းသင့်ပါတယ်
- Quality ကို ပိုမြှင့်ချင်ရင် `bot.py` ထဲက model name ကို `"isnet-general-use"`
  အစား `"birefnet-general"` လို့ပြောင်းလို့ရပါတယ် (နှေးမယ်၊ quality ပိုကောင်းမယ်)

## Files

| File | Description |
|---|---|
| `bot.py` | Main bot logic |
| `config.py` | Environment-based settings |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container build (pre-downloads AI model) |
| `.env.example` | Environment variable template |
