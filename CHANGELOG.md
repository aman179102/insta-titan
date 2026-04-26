# Changelog

## [2.1.0] - 2026-05-28

### Added
- AI-powered caption generation via Ollama integration
- BLIP-based automatic image tagging pipeline
- NSFW content detection with transformer models
- Perceptual hash duplicate detection across sources
- Gradual account warmup scheduler for anti-ban
- 6-stage configurable filter pipeline (keyword → NSFW → quality → resolution → duplicate → color)
- Dark mode web UI with real-time WebSocket updates
- Telegram bot for remote control (stats, queue, fetch, post)
- Encrypted credential vault with PBKDF2 key derivation
- Proxy rotation for anonymous scraping operations
- Multi-platform poster framework (Instagram, Twitter, Facebook)
- Docker compose deployment with persistent volumes

### Changed
- Refactored fetcher architecture to plugin-based system
- Optimized image download pipeline with streaming and validation
- Improved session persistence with automatic reconnection
- Enhanced scheduler timing with Gaussian jitter distribution
- Updated rate limiting to adapt based on account health score

### Fixed
- Session expiry handling with automatic re-login
- Memory leak in large queue operations (>1000 items)
- Race condition in concurrent fetch operations
- EXIF metadata retention in processed uploads
- Unicode handling in multi-language captions

## [2.0.0] - 2026-05-10

### Added
- Multi-source image fetching (Reddit, Unsplash, Pexels, Pixabay, Google, Bing, DuckDuckGo, RSS, Local)
- SQLAlchemy ORM with SQLite backend
- Instagram photo posting with session persistence
- Smart scheduler with configurable daily limits
- Flask web UI with dashboard and queue management
- Image processing pipeline (resize, enhance, watermark, collage)
- Keyword and resolution filter system
- Basic analytics tracking
- CLI interface with 10+ commands
- REST API for external integrations

## [1.0.0] - 2026-04-28

### Added
- Initial project structure
- Basic configuration system
- Core database models
- Single-source image fetching (Reddit only)
- Instagram login and photo upload
- Simple scheduler with fixed intervals
- Command-line interface
- Basic documentation
