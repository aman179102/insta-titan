.PHONY: install test run clean lint format docker-build

install:
	pip install -r requirements.txt
	pip install -e .

test:
	python -m pytest tests/ -v --tb=short

run:
	python main.py run

web:
	python main.py web

fetch:
	python main.py fetch

queue:
	python main.py queue

lint:
	flake8 src/ --max-line-length=100
	python -m pytest tests/ -v --tb=short --quiet

format:
	black src/ tests/

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf *.egg-info/

docker-build:
	docker compose build

docker-run:
	docker compose up -d
