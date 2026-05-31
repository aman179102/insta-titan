<div align="center">
  <br/>
  <h1>⚡ InstaTitan</h1>
  <p><strong>AI-Powered Instagram Automation Platform</strong></p>
  <p>
    <em>Multi-source • Smart Scheduling • Anti-Ban • AI Captions • Live Dashboard • 100% Free</em>
  </p>
  <br/>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/status-production%20ready-brightgreen" alt="Status"/>
  <img src="https://img.shields.io/badge/build-passing-success" alt="Build"/>
  <img src="https://img.shields.io/badge/docker-ready-2496ED" alt="Docker"/>
  <img src="https://img.shields.io/badge/Render%20free%20tier-ready-46E3B7" alt="Render Ready"/>
  <img src="https://img.shields.io/badge/self--pinger-%E2%9C%93-brightgreen" alt="Self-Pinger"/>
</p>

---

## 🚀 Overview

**InstaTitan** is an enterprise-grade Instagram automation platform that fetches images from **9+ sources**, processes them through a smart pipeline, and posts them automatically with **intelligent scheduling** to avoid account restrictions. Comes with a **real-time web dashboard** featuring live ping monitoring, post tracking, and analytics.

Built for creators, marketers, and developers who want zero-touch Instagram content management — completely free, open-source, and self-hosted.

---

## ✨ Features

### 🌐 Multi-Source Image Fetching
| Source | Type | API Key | Free Tier |
|--------|------|---------|-----------|
| Reddit | Subreddit scraping | Required | 60 req/min |
| Unsplash | REST API | ✅ Free key | 50 req/hr |
| Pexels | REST API | ✅ Free key | 200 req/hr |
| Pixabay | REST API | ✅ Free key | Unlimited |
| Google Images | Custom Search | ✅ Free key | 100/day |
| DuckDuckGo | Web scraping | ❌ No key | Unlimited |
| RSS Feeds | Feed parsing | ❌ No key | Unlimited |
| Local | Filesystem | ❌ No key | Unlimited |

### 💚 Built-in Ping Monitor (Render Sleep Prevention)
- **Self-pinger** — har 5 minute me app ko hi ping karta hai
- Render free tier par **server kabhi sleep nahi hoga**
- Dashboard par **live ping status** — green dot + response time
- Auto-detects `RENDER_EXTERNAL_URL` env variable
- Local dev me automatically disable ho jata hai
- SQLite me log ho jata hai future debugging ke liye

### ⏰ Smart Scheduler (Anti-Ban)
- Gradual account warmup (1→3 posts/day over 7 days)
- Gaussian jitter distribution (±30min random variance)
- Configurable daily limits with cooldown enforcement
- Multi-account time staggering
- Exponential backoff on errors

### 🎨 Image Processing
- Auto-resize to Instagram optimal ratios
- EXIF metadata stripping (privacy)
- Watermark overlay with opacity control
- Image optimization for quality/size balance

### 🛡️ Security
- Encrypted credential vault (PBKDF2 + Fernet)
- Session encryption at rest
- User-agent rotation
- Rate limiting with backoff

### 🌐 Live Dashboard
- **Ping Monitor** — green/red indicator with response time
- **Last Post** — real-time track when post hua
- Queue management
- Post history with engagement metrics
- Analytics charts (Chart.js)
- Source configuration UI

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- pip / venv

### Quick Start

```bash
# Clone
git clone https://github.com/aman179102/insta-titan.git
cd insta-titan

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys and Instagram credentials

# Fetch images
python main.py fetch

# Launch everything
python main.py run
# Web UI: http://localhost:5000
```

### Docker

```bash
docker compose up -d
# Web UI: http://localhost:5000
```

### Deploy on Render (Free Tier)

[![Deploy to Render](https://img.shields.io/badge/Deploy%20to%20Render-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com/deploy)

1. Fork this repo on GitHub
2. Go to [render.com](https://render.com) → **New Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py run`
   - **Health Check Path**: `/health`
5. Add **Environment Variables** — copy from `.env.example`
6. Deploy — Render automatically sets `RENDER_EXTERNAL_URL`
7. ✅ **Self-pinger** auto-start ho jayega — server kabhi sleep nahi hoga

---

## 🎮 Usage

### CLI Commands

```bash
python main.py run          # Start scheduler + web UI
python main.py web          # Launch web dashboard only
python main.py fetch        # Fetch from all sources
python main.py queue        # View pending posts
python main.py post-now     # Post immediately
python main.py search "nature"  # Search queue/history
python main.py analytics    # View engagement stats
python main.py telegram     # Start Telegram bot
python main.py config       # View current config
python main.py vault        # List encrypted services
python main.py health       # Account health check
```

### Web UI

| Page | Description |
|------|-------------|
| **Dashboard** | Live stats, **ping monitor**, last post tracker, activity charts, recent posts |
| **Queue** | Manage pending posts, preview, bulk actions |
| **History** | Posted items with engagement metrics |
| **Analytics** | Performance reports, source distribution |
| **Settings** | Accounts, sources, filters, notifications |

---

## ⚙️ Configuration

All configuration is managed via `config.yaml` with sensitive values securely stored in `.env`:

```yaml
instagram:
  accounts:
    - username: ""    # Set via INSTA_USERNAME in .env
      password: ""    # Set via INSTA_PASSWORD in .env

sources:
  unsplash:
    enabled: true
    access_key: ""    # Set via UNSPLASH_ACCESS_KEY
```

---

## 🧪 Testing

```bash
pytest tests/ -v              # Run all tests
pytest tests/ -v --tb=short   # Short traceback
python -m pytest tests/       # Alternative runner
```

---

## 🏗️ Architecture

```
instatitan/
├── main.py                 # CLI entry point
├── app.py                  # Flask web app + self-pinger
├── config.yaml             # YAML configuration
├── .env                    # Secrets (gitignored)
├── src/
│   ├── fetcher/            # 9 image source integrations
│   ├── poster/             # Instagram upload engine
│   ├── scheduler/          # Anti-ban scheduling
│   ├── filter/             # Multi-stage pipeline
│   ├── processor/          # Image manipulation
│   ├── security/           # Encryption & proxy
│   ├── analytics/          # Metrics & reporting
│   ├── notifications/      # Telegram, Discord, Email
│   └── db/                 # SQLite ORM (PostQueue, PostedHistory, PingLog)
├── templates/              # Web UI (dark theme)
├── tests/                  # Test suite
└── Dockerfile              # Containerized deployment
```

---

## 🔒 Security

- Credentials stored in encrypted vault, never in config
- Sessions encrypted with Fernet symmetric encryption
- EXIF data stripped from all uploaded images
- Proxy rotation for identity protection
- Rate limiting with exponential backoff
- No plaintext secrets in logs or memory

---

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for our code of conduct and submission guidelines.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  <sub>Built with ❤️ for the open-source community</sub>
  <br/>
  <sub>© 2026 Aman. All rights reserved.</sub>
</div>
