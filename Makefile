.PHONY: setup dev dev-service test lint format infra-up infra-down infra-logs migrate migrate-create migrate-rollback clean help

# 기본 변수
DOCKER_COMPOSE := docker compose -f docker/docker-compose.yml
SERVICE ?= recipe-service

# ==============================================================================
# 개발 환경 설정
# ==============================================================================

setup: ## 개발 환경 설정 (Python 가상환경 + 의존성 설치)
	@./scripts/setup.sh

# ==============================================================================
# 개발 서버
# ==============================================================================

dev: ## 전체 서비스 시작 (개발 모드)
	@./scripts/dev.sh

dev-service: ## 특정 서비스만 시작 (SERVICE=xxx)
	@./scripts/dev.sh $(SERVICE)

# ==============================================================================
# 인프라 (Docker Compose)
# ==============================================================================

infra-up: ## 로컬 인프라 시작 (PostgreSQL, Redis, Elasticsearch, Kafka)
	$(DOCKER_COMPOSE) up -d

infra-down: ## 로컬 인프라 중지
	$(DOCKER_COMPOSE) down

infra-logs: ## 인프라 로그 확인
	$(DOCKER_COMPOSE) logs -f

infra-reset: ## 인프라 초기화 (볼륨 포함 삭제)
	$(DOCKER_COMPOSE) down -v

# ==============================================================================
# 테스트
# ==============================================================================

test: ## 전체 테스트 실행
	@for dir in services/*/; do \
		if [ -d "$$dir/tests" ]; then \
			echo "Testing $$dir..."; \
			cd $$dir && uv run pytest && cd ../..; \
		fi \
	done

test-service: ## 특정 서비스 테스트 (SERVICE=xxx)
	cd services/$(SERVICE) && uv run pytest

test-cov: ## 커버리지 포함 테스트
	cd services/$(SERVICE) && uv run pytest --cov=src --cov-report=html

# ==============================================================================
# 코드 품질
# ==============================================================================

lint: ## 린팅 + 타입 검사
	uv run ruff check .
	uv run mypy services/ shared/

format: ## 코드 포매팅
	uv run ruff format .
	uv run black .

format-check: ## 포매팅 검사 (수정 없음)
	uv run ruff format --check .
	uv run black --check .

# ==============================================================================
# 데이터베이스 마이그레이션
# ==============================================================================

migrate: ## 마이그레이션 적용 (SERVICE=xxx)
	cd services/$(SERVICE) && uv run alembic upgrade head

migrate-create: ## 마이그레이션 생성 (SERVICE=xxx MSG="메시지")
	cd services/$(SERVICE) && uv run alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## 마이그레이션 롤백 (SERVICE=xxx)
	cd services/$(SERVICE) && uv run alembic downgrade -1

migrate-history: ## 마이그레이션 히스토리 (SERVICE=xxx)
	cd services/$(SERVICE) && uv run alembic history

# ==============================================================================
# 정리
# ==============================================================================

clean: ## 캐시 및 빌드 아티팩트 정리
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true

# ==============================================================================
# 도움말
# ==============================================================================

help: ## 도움말 표시
	@echo "사용 가능한 명령어:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "예시:"
	@echo "  make setup                    # 개발 환경 설정"
	@echo "  make infra-up                 # 인프라 시작"
	@echo "  make dev-service SERVICE=recipe-service  # recipe-service 시작"
	@echo "  make test-service SERVICE=recipe-service # recipe-service 테스트"
