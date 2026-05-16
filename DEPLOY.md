# 🚀 GitHub + Railway деплой нұсқаулығы

---

## 1️⃣ GitHub репозитория жасау

1. **github.com** → жоғарғы оң жақтан **"+"** → **"New repository"**
2. Атауы: `language-bot` (немесе кез-келген)
3. **Private** таңдаңыз (бот токені жасырын болсын)
4. **"Create repository"** басыңыз

---

## 2️⃣ Файлдарды GitHub-қа жүктеу

Терминалда (бот қалтасының ішінде):

```bash
cd language_bot

git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/СІЗДІҢ_USERNAME/language-bot.git
git push -u origin main
```

> **Ескерту:** config.py-де токен жоқ — ол Railway-де environment variable ретінде қойылады.

---

## 3️⃣ Railway-де жоба жасау

1. **railway.app** → **"Login with GitHub"**
2. **"New Project"** → **"Deploy from GitHub repo"**
3. `language-bot` репозиторийін таңдаңыз
4. **"Deploy Now"** басыңыз

---

## 4️⃣ Environment Variables қою (МАҢЫЗДЫ!)

Railway → Сіздің жоба → **"Variables"** қойындысы → **"New Variable"**:

| Variable атауы | Мәні |
|---|---|
| `BOT_TOKEN` | `7xxxxxxxxx:AAF...` (BotFather токені) |
| `TEACHER_SECRET_CODE` | `mugalim2024` (немесе өз кодыңыз) |

**"Add"** → **"Deploy"** басыңыз.

---

## 5️⃣ Дерекқорды Volume-ға байлау (bot.db сақталсын)

Railway-де SQLite файлы рестарт кезінде жоғалуы мүмкін.
Шешімі — **Volume** жасау:

1. Railway жобасы → **"New"** → **"Volume"**
2. Mount Path: `/app/data`
3. Сосын `database/db.py`-де `DB_PATH`-ті өзгертіңіз:

```python
import os
DB_PATH = os.environ.get("DB_PATH", "data/bot.db")
```

4. Осыны да Variable-ға қосыңыз:

| Variable | Мән |
|---|---|
| `DB_PATH` | `data/bot.db` |

---

## 6️⃣ seed_tasks.py іске қосу (тапсырмаларды қосу)

Тапсырмаларды базаға қосу үшін **бір рет** іске қосу керек.

### Локальды іске қосу (ең оңай):
```bash
# Файлдарды дайындаңыз (бот қалтасында):
# img_sark.png, audio_sark.mp3, img_balam.png, audio_balam.m4a, img_bala.png, audio_bala.mp3

pip install -r requirements.txt
BOT_TOKEN="сіздің_токен" python seed_tasks.py
```

Содан кейін `bot.db` файлын Railway Volume-ға көшіруге болады немесе бот өзі іске қосылғанда мұғалім `/start` арқылы тіркеліп, тапсырмаларды қолмен қоса алады.

---

## 7️⃣ Деплойды тексеру

Railway → **"Deployments"** → Логтарды көріңіз.

Сәтті болса:
```
INFO: Bot started polling
```

---

## ♻️ Кодты жаңарту

```bash
git add .
git commit -m "Жаңарту сипаттамасы"
git push
```

Railway автоматты түрде қайта деплой жасайды!

---

## 💰 Railway бағасы

- **Тегін tier**: $5 кредит/ай (шағын бот үшін жеткілікті)
- Егер аз болса: **Hobby plan** — $5/ай

---

## ❓ Жиі кездесетін қателер

**"Module not found"** → `requirements.txt`-те кем пакет бар, тексеріңіз

**Bot не жауап береді** → Railway Variables-те `BOT_TOKEN` дұрыс па?

**db жоғалды** → Volume қосыңыз (5-қадам)
