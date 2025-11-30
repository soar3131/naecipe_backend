# 내시피(Naecipe) 백엔드

AI 기반 맞춤형 레시피 보정 서비스의 백엔드 마이크로서비스 모노레포입니다.

## 프로젝트 구조

```
├── services/                    # 마이크로서비스
│   ├── recipe-service/          # 레시피 CRUD, 검색 (8001)
│   ├── user-service/            # 인증, 사용자 관리 (8002)
│   ├── cookbook-service/        # 레시피북, 피드백 (8003)
│   ├── ai-agent-service/        # AI 에이전트 (8004)
│   ├── embedding-service/       # 벡터 임베딩 (8005)
│   ├── search-service/          # 검색 (8006)
│   ├── notification-service/    # 알림 (8007)
│   ├── analytics-service/       # 분석 (8008)
│   └── ingestion-service/       # 수집 (8009)
├── shared/                      # 공통 패키지
│   ├── proto/                   # gRPC 프로토콜 정의
│   ├── schemas/                 # 공통 Pydantic 스키마
│   └── utils/                   # 공통 유틸리티
├── docker/                      # Docker 설정
└── scripts/                     # 개발 스크립트
```

## 빠른 시작

### 사전 요구사항

- Python 3.11+
- Docker Desktop (또는 Docker Engine + Docker Compose)
- uv (Python 패키지 관리자)

### 환경 설정

```bash
# 1. 저장소 클론
git clone https://github.com/your-org/naecipe-backend.git
cd naecipe-backend

# 2. 개발 환경 설정
make setup

# 3. 로컬 인프라 시작
make infra-up

# 4. 서비스 시작
make dev-service SERVICE=recipe-service

# 5. 헬스체크 확인
curl http://localhost:8001/health
```

자세한 내용은 [Quickstart 가이드](specs/001-project-setup/quickstart.md)를 참조하세요.

## 주요 명령어

```bash
# 개발 환경
make setup              # 개발 환경 설정
make dev                # 전체 서비스 시작
make dev-service        # 특정 서비스만 시작

# 인프라
make infra-up           # 인프라 컨테이너 시작
make infra-down         # 인프라 컨테이너 중지
make infra-logs         # 인프라 로그 확인

# 테스트/품질
make test               # 전체 테스트 실행
make lint               # 코드 품질 검사
make format             # 코드 포매팅

# 데이터베이스
make migrate            # 마이그레이션 적용
make migrate-create     # 마이그레이션 생성
make migrate-rollback   # 마이그레이션 롤백
```

## 기술 스택

- **언어**: Python 3.11+
- **프레임워크**: FastAPI 0.100+
- **ORM**: SQLAlchemy 2.0+
- **데이터베이스**: PostgreSQL 15+ (pgvector)
- **캐시**: Redis 7+
- **검색**: Elasticsearch 8+
- **메시지 큐**: Apache Kafka 3.5+
- **테스트**: pytest, pytest-asyncio
- **코드 품질**: Ruff, Black, mypy

## 문서

- [Quickstart 가이드](specs/001-project-setup/quickstart.md)
- [API 명세](specs/001-project-setup/contracts/)
- [기술 결정](specs/001-project-setup/research.md)

## 라이선스

MIT License
