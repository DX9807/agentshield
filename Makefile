.PHONY: help install dev-install lint format test test-cov run db-upgrade db-init clean docker-up docker-down docker-build attack-lab

help:
	@echo "Available commands:"
	@echo "  install        Install production dependencies"
	@echo "  dev-install    Install development dependencies"
	@echo "  lint           Run linters"
	@echo "  format         Format code"
	@echo "  test           Run tests"
	@echo "  test-cov       Run tests with coverage"
	@echo "  run            Run the application"
	@echo "  db-upgrade     Run database migrations"
	@echo "  db-init        Initialize database"
	@echo "  clean          Clean cache files"
	@echo "  docker-up      Start Docker Compose services"
	@echo "  docker-down    Stop Docker Compose services"
	@echo "  docker-build   Build Docker images"
	@echo "  attack-lab     Run attack lab scenarios"

install:
	pip install -r requirements.txt

dev-install:
	pip install -r dev-requirements.txt
	pre-commit install

lint:
	ruff check agentshield/
	mypy agentshield/ --ignore-missing-imports

format:
	ruff format agentshield/
	ruff check --fix agentshield/

test:
	pytest agentshield/tests/ -v

test-cov:
	pytest agentshield/tests/ -v --cov=agentshield --cov-report=html --cov-report=term

run:
	uvicorn agentshield.main:app --host 0.0.0.0 --port 8000 --reload

db-upgrade:
	alembic upgrade head

db-init:
	python scripts/init_db.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down -v

docker-build:
	docker-compose build

docker-logs:
	docker-compose logs -f

attack-lab:
	python scripts/run_attack_lab.py