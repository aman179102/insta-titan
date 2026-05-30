<div align="center">
  <br/>
  <h1>⚡ InstaForge</h1>
  <p><strong>AI-Powered Instagram Automation Platform</strong></p>
  <p>
    <em>Multi-source • Smart Scheduling • Anti-Ban • AI Captions • Web UI • 100% Free</em>
  </p>
  <br/>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License"/>
  <img src="https://img.shields.io/badge/status-production%20ready-brightgreen" alt="Status"/>
  <img src="https://img.shields.io/badge/AI-Ollama%20%7C%20BLIP-orange" alt="AI"/>
  <img src="https://img.shields.io/badge/docker-ready-2496ED" alt="Docker"/>
</p>

---

## 🚀 Overview

**InstaForge** is an enterprise-grade Instagram automation platform that fetches images from **9+ sources**, processes them through an **AI-powered pipeline**, and posts them automatically with **smart scheduling** to avoid account restrictions.

Built for creators, marketers, and developers who want zero-touch Instagram content management — completely free, open-source, and self-hosted.

---

## ✨ Features

### 🌐 Multi-Source Image Fetching
| Source | Type | Free Tier |
|--------|------|-----------|
| Reddit | Subreddit scraping | 60 req/min |
| Unsplash | REST API | 50 req/hr |
| Pexels | REST API | 200 req/hr |
| Pixabay | REST API | Unlimited |
| Google Images | Custom Search | 100/day free |
| Bing Images | Azure API | 1000/month |
| DuckDuckGo | Web scraping | Unlimited |
| RSS Feeds | Feed parsing | Unlimited |
| Local | Filesystem watch | Unlimited |

### 🤖 AI Engine
- **Caption Generation** — Ollama LLM (local, private)
- **Auto Tagging** — BLIP image captioning
- **NSFW Detection** — Transformer classifiers
- **Quality Scoring** — Aesthetic analysis
- **Duplicate Detection** — Perceptual hashing
- **Background Removal** — RMBG (local)

### ⏰ Smart Scheduler (Anti-Ban)
- Gradual account warmup (1→3 posts/day over 7 days)
- Gaussian jitter distribution (±30min random variance)
- Configurable daily limits with cooldown enforcement
- Multi-account time staggering
- Exponential backoff on errors

### 🎨 Image Processing
- Auto-resize to Instagram optimal ratios
- AI-powered smart cropping
- 30+ visual filters
- EXIF metadata stripping (privacy)
- Watermark overlay with opacity control
- Collage creation (grid/freeform)

### 🛡️ Security
- Encrypted credential vault (PBKDF2 + Fernet)
- Session encryption at rest
- Proxy rotation (HTTP/SOCKS5)
- User-agent rotation
- Rate limiting with backoff

### 🌐 Web Dashboard
- Real-time activity monitor (WebSocket)
- Queue management with drag-and-drop
- Post history with engagement metrics
- Calendar view of scheduled posts
- Source configuration UI
- Analytics charts (Chart.js)

---

## 📦 Installation

### Prerequisites
- Python 3.10+
- pip / venv

### Quick Start

```bash
# Clone
git clone https://github.com/aman/instaforge.git
cd instaforge

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
| **Dashboard** | Live stats, activity charts, recent posts |
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
instaforge/
├── main.py                 # CLI entry point
├── app.py                  # Flask web application
├── config.yaml             # YAML configuration
├── src/
│   ├── fetcher/            # 9 image source integrations
│   ├── poster/             # Instagram upload engine
│   ├── scheduler/          # Anti-ban scheduling
│   ├── filter/             # 6-stage pipeline
│   ├── processor/          # Image manipulation
│   ├── ai/                 # ML/AI inference
│   ├── security/           # Encryption & proxy
│   ├── analytics/          # Metrics & reporting
│   ├── social/             # Engagement automation
│   ├── notifications/      # Telegram, Discord, Email
│   └── db/                 # SQLite ORM layer
├── templates/              # Web UI (dark theme)
├── tests/                  # Comprehensive test suite
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
