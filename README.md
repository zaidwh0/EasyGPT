# 🤖 EasyGPT

EasyGPT is a modern Discord bot focused on **AI-assisted moderation, automation, and server management** — built to be clean, fast, and intentional.

This is not a “do-everything” bot.  
EasyGPT is designed to reduce friction for server owners and moderators using smart UX and AI where it actually makes sense.

---

## ✨ Core Features

### 🤖 AI
- `/ask` — Ask AI questions directly inside Discord  
- 3-day free trial system  
- Subscription-based access  
- Powered by Groq LLMs  

### 🛡 Moderation
- Kick, ban, timeout, warn  
- Bulk message clearing  
- Permission-aware execution  

### 🎁 Giveaways
- Reaction-based giveaways  
- Live countdown updates  

### 📊 Server Logs
- Member joins / leaves  
- Message edits & deletes  
- Role & channel changes  
- Server updates  

### ⚙️ Setup
- Slash-command based setup  
- Custom prefix support  
- Clean, minimal UX  

---

## 🧠 Experimental (WIP)

EasyGPT is experimenting with **AI-assisted actions** via a `/do` command.

Example:
```text
/do create a nitro giveaway in #freestuff for 4 hours
```

All AI-detected actions require **explicit confirmation** before execution.

---

## 🚀 Getting Started

### 1. Clone the repo
```bash
git clone https://github.com/zaidwh0/EasyGPT.git
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Create `.env` file
```env
DISCORD_BOT_TOKEN=your_token_here
GROQ_API_KEY=your_api_key_here
```

### 4. Run the bot
```bash
python main.py
```

---

## 🗺 Roadmap
- AI-assisted moderation (`/do`)
- SQLite database migration
- Rate limits & safety controls
- Config dashboard

---

## 👤 Author
Built by **zaidwh0**
