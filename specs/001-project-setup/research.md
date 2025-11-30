# Research: 백엔드 프로젝트 기반 설정

**Feature Branch**: `001-project-setup`
**Created**: 2025-11-30

## 1. Python 모노레포 구조 결정

### Decision: src-layout + 개별 pyproject.toml

각 마이크로서비스는 독립적인 Python 패키지로 관리하며, `src/` 레이아웃을 사용한다.

### Rationale

- **src-layout**: 패키지와 테스트 코드의 명확한 분리, import 충돌 방지
- **개별 pyproject.toml**: 서비스별 독립적인 의존성 관리, 개별 빌드/배포 가능
- **루트 pyproject.toml**: 공통 개발 도구(ruff, black, mypy) 설정 및 workspace 정의

### Alternatives Considered

| 대안 | 기각 이유 |
|------|----------|
| 단일 pyproject.toml | 서비스 간 의존성 충돌 가능, 개별 배포 어려움 |
| flat-layout | import 경로 혼란, 테스트와 소스 코드 분리 불명확 |
| Poetry workspace | Kubernetes 환경에서 pip 호환성 이슈 |

---

## 2. Python 의존성 관리 도구 결정

### Decision: uv (pip 호환)

`uv`를 기본 의존성 관리 도구로 사용하고, `pyproject.toml`로 의존성을 정의한다.

### Rationale

- **속도**: pip 대비 10-100배 빠른 의존성 해결 및 설치
- **호환성**: pip/pyproject.toml 표준 호환, Docker 환경에서 pip로 대체 가능
- **lockfile**: `uv.lock`으로 재현 가능한 빌드 보장
- **Python 버전 관리**: uv로 Python 버전도 함께 관리 가능

### Alternatives Considered

| 대안 | 기각 이유 |
|------|----------|
| Poetry | lockfile 해결 속도 느림, Kubernetes에서 추가 설정 필요 |
| pip-tools | 기능 제한적, 별도 도구 필요 |
| pip only | lockfile 없음, 재현 가능한 빌드 어려움 |

---

## 3. Docker Compose 인프라 구성

### Decision: 단일 docker-compose.yml + 프로파일

모든 인프라 서비스를 단일 `docker-compose.yml`에 정의하고, 프로파일로 선택적 실행을 지원한다.

### Rationale

- **단순성**: 파일 분리 없이 관리 용이
- **프로파일**: `--profile infra`, `--profile all` 등으로 선택적 실행
- **볼륨**: named volume으로 데이터 영속성 보장

### 인프라 서비스 구성

| 서비스 | 이미지 | 포트 | 용도 |
|--------|--------|------|------|
| postgres | postgres:15-alpine | 5432 | Recipe/User/Cookbook DB |
| redis | redis:7-alpine | 6379 | 세션, 캐시 |
| elasticsearch | elasticsearch:8.11.0 | 9200 | 검색 |
| kafka | confluentinc/cp-kafka:7.5.0 | 9092 | 이벤트 버스 |
| zookeeper | confluentinc/cp-zookeeper:7.5.0 | 2181 | Kafka 의존성 |

### Alternatives Considered

| 대안 | 기각 이유 |
|------|----------|
| 여러 docker-compose 파일 | 파일 관리 복잡, override 순서 혼란 |
| Podman Compose | Docker와 완전 호환되지 않음 |
| Kind/Minikube | 로컬 개발에 과도한 복잡성 |

---

## 4. 환경 변수 관리 방식

### Decision: Pydantic Settings + .env 파일

`pydantic-settings`를 사용하여 환경 변수를 타입 안전하게 로드하고 검증한다.

### Rationale

- **타입 안전성**: 환경 변수를 Python 타입으로 자동 변환
- **검증**: 필수 변수 누락, 잘못된 형식 검증
- **기본값**: 개발 환경 기본값 제공
- **비밀 마스킹**: `SecretStr` 타입으로 로그 출력 시 자동 마스킹

### 환경 변수 템플릿 구조

```bash
# .env.example
# 서비스 공통
SERVICE_NAME=recipe-service
SERVICE_PORT=8001
LOG_LEVEL=INFO

# 데이터베이스
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/naecipe
DATABASE_POOL_SIZE=5

# Redis
REDIS_URL=redis://localhost:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### Alternatives Considered

| 대안 | 기각 이유 |
|------|----------|
| python-dotenv만 사용 | 타입 검증 없음, 수동 파싱 필요 |
| dynaconf | 과도한 기능, 학습 곡선 |
| 환경 변수 직접 접근 | 타입 안전성 없음, 반복 코드 |

---

## 5. 로깅 표준

### Decision: structlog + JSON 포맷

구조화된 로깅을 위해 `structlog`를 사용하고, 프로덕션에서는 JSON 포맷을 사용한다.

### Rationale

- **구조화**: 키-값 쌍으로 로그 컨텍스트 추가 용이
- **JSON**: 로그 수집/분석 도구와 호환
- **개발 환경**: 컬러 콘솔 출력으로 가독성 유지
- **FastAPI 통합**: 요청 ID, 사용자 ID 자동 추가

### 로그 레벨 정책

| 레벨 | 용도 |
|------|------|
| DEBUG | 개발 시 상세 정보 |
| INFO | 정상 동작 기록 (요청, 응답) |
| WARNING | 예상된 문제 (재시도, fallback) |
| ERROR | 예외 발생, 실패 |
| CRITICAL | 서비스 장애 |

### Alternatives Considered

| 대안 | 기각 이유 |
|------|----------|
| loguru | 구조화 로깅 지원 부족 |
| Python logging만 사용 | 구조화 로깅 설정 복잡 |

---

## 6. 테스트 구조

### Decision: pytest + 계층별 분리

`pytest`를 사용하고, 테스트를 contract/integration/unit으로 분리한다.

### Rationale

- **contract**: API 스펙 준수 검증, OpenAPI 기반
- **integration**: DB, Redis, 외부 서비스 연동 테스트
- **unit**: 비즈니스 로직 단위 테스트

### 테스트 실행 명령어

```bash
# 전체 테스트
pytest

# 단위 테스트만 (빠름)
pytest tests/unit

# 통합 테스트 (인프라 필요)
pytest tests/integration

# 커버리지 포함
pytest --cov=src --cov-report=html
```

### Alternatives Considered

| 대안 | 기각 이유 |
|------|----------|
| unittest | fixture 시스템 부족, 설정 복잡 |
| nose2 | 개발 활성도 낮음 |

---

## 7. 코드 품질 도구

### Decision: Ruff + Black + mypy

단일 도구 체인으로 린팅, 포매팅, 타입 검사를 수행한다.

### Rationale

- **Ruff**: 빠른 린터, isort/flake8/pylint 규칙 통합
- **Black**: 일관된 코드 포매팅, 논쟁 제거
- **mypy**: 정적 타입 검사, strict mode

### 설정 (pyproject.toml)

```toml
[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.black]
line-length = 100
target-version = ["py311"]

[tool.mypy]
python_version = "3.11"
strict = true
```

### Alternatives Considered

| 대안 | 기각 이유 |
|------|----------|
| flake8 + isort | Ruff가 더 빠르고 통합적 |
| pylint | 속도 느림, 설정 복잡 |
| pyright | mypy 대비 생태계 작음 |

---

## 8. 마이그레이션 도구

### Decision: Alembic (서비스별 독립)

각 서비스에서 독립적으로 Alembic 마이그레이션을 관리한다.

### Rationale

- **독립성**: 서비스별 스키마 변경 독립 관리
- **SQLAlchemy 통합**: 모델에서 자동 마이그레이션 생성
- **롤백**: 버전별 롤백 지원

### 마이그레이션 명령어

```bash
# 마이그레이션 생성
alembic revision --autogenerate -m "Add user table"

# 마이그레이션 적용
alembic upgrade head

# 롤백
alembic downgrade -1
```

### Alternatives Considered

| 대안 | 기각 이유 |
|------|----------|
| Django migrations | FastAPI와 별개 프레임워크 |
| yoyo-migrations | SQLAlchemy 통합 부족 |

---

## 9. 개발 워크플로우 스크립트

### Decision: Makefile + Shell 스크립트

`Makefile`로 공통 명령어를 정의하고, 복잡한 로직은 Shell 스크립트로 분리한다.

### Rationale

- **Makefile**: 간단한 명령어 alias, 의존성 체인
- **Shell 스크립트**: 조건문, 반복문 등 복잡한 로직
- **플랫폼 호환**: Linux/macOS 기본 지원

### Makefile 명령어

```makefile
.PHONY: setup dev test lint

setup:           # 개발 환경 설정
dev:             # 개발 서버 시작
dev-service:     # 특정 서비스만 시작
test:            # 전체 테스트 실행
lint:            # 코드 품질 검사
format:          # 코드 포매팅
migrate:         # DB 마이그레이션 적용
infra-up:        # 인프라 컨테이너 시작
infra-down:      # 인프라 컨테이너 중지
```

### Alternatives Considered

| 대안 | 기각 이유 |
|------|----------|
| Just | 추가 도구 설치 필요 |
| Task (taskfile.dev) | 팀 학습 비용 |
| npm scripts | Python 프로젝트에 부적합 |

---

## Summary

| 영역 | 결정 | 핵심 근거 |
|------|------|----------|
| 프로젝트 구조 | src-layout 모노레포 | 독립 배포, import 명확성 |
| 의존성 관리 | uv | 속도, pip 호환성 |
| 로컬 인프라 | Docker Compose + 프로파일 | 단순성, 선택적 실행 |
| 환경 변수 | Pydantic Settings | 타입 안전성, 검증 |
| 로깅 | structlog + JSON | 구조화, 분석 용이 |
| 테스트 | pytest + 계층 분리 | 유연성, fixture 시스템 |
| 코드 품질 | Ruff + Black + mypy | 속도, 일관성 |
| 마이그레이션 | Alembic | SQLAlchemy 통합 |
| 워크플로우 | Makefile | 단순성, 플랫폼 호환 |
