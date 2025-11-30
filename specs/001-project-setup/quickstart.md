# Quickstart: 백엔드 개발 환경 설정

**Feature Branch**: `001-project-setup`
**Created**: 2025-11-30

## 사전 요구사항

- **Python**: 3.11 이상
- **Docker**: Docker Desktop 또는 Docker Engine + Docker Compose
- **Git**: 최신 버전
- **OS**: macOS, Linux, Windows (WSL2 권장)

## 1. 저장소 클론 및 환경 설정 (2분)

```bash
# 저장소 클론
git clone https://github.com/your-org/naecipe-backend.git
cd naecipe-backend

# 개발 환경 설정 (Python 가상환경 + 의존성 설치)
make setup

# 또는 수동으로
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv sync
```

## 2. 환경 변수 설정 (30초)

```bash
# 환경 변수 템플릿 복사
cp .env.example .env

# 필요시 .env 파일 수정 (기본값으로 로컬 개발 가능)
```

## 3. 로컬 인프라 시작 (1분)

```bash
# PostgreSQL, Redis, Elasticsearch, Kafka 시작
make infra-up

# 컨테이너 상태 확인
docker compose ps

# 예상 출력:
# NAME                  STATUS
# naecipe-postgres      running
# naecipe-redis         running
# naecipe-elasticsearch running
# naecipe-kafka         running
# naecipe-zookeeper     running
```

## 4. 서비스 시작 (30초)

### 전체 서비스 시작

```bash
make dev
```

### 특정 서비스만 시작

```bash
# recipe-service만 시작
make dev-service SERVICE=recipe-service

# 또는 직접 실행
cd services/recipe-service
uvicorn src.recipe_service.main:app --reload --port 8001
```

## 5. 헬스체크 확인

```bash
# 서비스 헬스체크
curl http://localhost:8001/health

# 예상 응답:
# {"status":"healthy","service":"recipe-service","version":"1.0.0","timestamp":"2025-11-30T12:00:00Z"}

# 준비 상태 확인
curl http://localhost:8001/ready

# 예상 응답:
# {"status":"ready","service":"recipe-service","checks":{"database":true,"redis":true,"kafka":true},"timestamp":"2025-11-30T12:00:00Z"}
```

## 6. 테스트 실행

```bash
# 전체 테스트
make test

# 특정 서비스 테스트
cd services/recipe-service
pytest

# 커버리지 포함
pytest --cov=src --cov-report=html
```

## 7. 코드 품질 검사

```bash
# 린팅 + 포매팅 + 타입 검사
make lint

# 자동 포매팅
make format
```

## 서비스 포트 목록

| 서비스 | 포트 | 설명 |
|--------|------|------|
| recipe-service | 8001 | 레시피 CRUD, 검색 |
| user-service | 8002 | 인증, 사용자 관리 |
| cookbook-service | 8003 | 레시피북, 피드백 |
| ai-agent-service | 8004 | AI 보정/Q&A |
| embedding-service | 8005 | 벡터 임베딩 |
| search-service | 8006 | Elasticsearch |
| notification-service | 8007 | 알림 |
| analytics-service | 8008 | 이벤트 집계 |
| ingestion-service | 8009 | 크롤링 레시피 수신 |

## 인프라 포트 목록

| 서비스 | 포트 | 용도 |
|--------|------|------|
| PostgreSQL | 5432 | 데이터베이스 |
| Redis | 6379 | 캐시, 세션 |
| Elasticsearch | 9200 | 검색 엔진 |
| Kafka | 9092 | 메시지 큐 |
| Zookeeper | 2181 | Kafka 의존성 |

## 자주 사용하는 명령어

```bash
# 환경 설정
make setup              # 개발 환경 설정

# 개발 서버
make dev                # 전체 서비스 시작
make dev-service SERVICE=xxx  # 특정 서비스 시작

# 인프라
make infra-up           # 인프라 컨테이너 시작
make infra-down         # 인프라 컨테이너 중지
make infra-logs         # 인프라 로그 확인

# 테스트/품질
make test               # 테스트 실행
make lint               # 코드 품질 검사
make format             # 코드 포매팅

# 데이터베이스
make migrate            # 마이그레이션 적용
make migrate-create MSG="xxx"  # 마이그레이션 생성
make migrate-rollback   # 마이그레이션 롤백
```

## 문제 해결

### 포트 충돌

```bash
# 사용 중인 포트 확인
lsof -i :8001

# 프로세스 종료
kill -9 <PID>
```

### 인프라 연결 실패

```bash
# 컨테이너 재시작
make infra-down
make infra-up

# 컨테이너 로그 확인
docker compose logs postgres
docker compose logs redis
```

### Python 버전 문제

```bash
# Python 버전 확인
python --version

# uv로 Python 설치
uv python install 3.11
```

## 다음 단계

1. [SPEC-001: 사용자 인증 기본](../../SPECKIT_TODO.md) 구현
2. API 개발 시작
3. 테스트 작성
