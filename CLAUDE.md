# CLAUDE.md

이 파일은 Claude Code (claude.ai/code)가 이 저장소에서 작업할 때 참고하는 가이드입니다.

## 커뮤니케이션 언어

**모든 소통은 한국어로 진행합니다.** 코드 주석, 커밋 메시지, 문서 작성 시 한국어를 사용하세요. 단, 코드 내 변수명, 함수명 등은 영문을 유지합니다.

## 프로젝트 개요

**내시피(Naecipe) 백엔드** - AI 기반 맞춤형 레시피 보정 서비스의 **백엔드 전용** 저장소입니다.

> **중요**: 이 저장소는 **백엔드(서버) 코드만** 관리합니다. 프론트엔드, 모바일 앱, 인프라 코드는 별도 저장소에서 관리됩니다.

- **역할**: REST API, gRPC 서비스, 이벤트 처리, AI 에이전트 등 서버 사이드 로직
- **Core Loop**: 검색 → 레시피 상세 → 조리/사용 → 피드백 입력 → AI 보정 → 보정 레시피 저장
- **아키텍처**: Python FastAPI 기반 마이크로서비스 (9개 서비스)
- **워크플로우**: spec-kit 명세 기반 개발 (specify → clarify → plan → tasks → implement)

## Spec-Kit 워크플로우 명령어

`.claude/commands/`에 정의된 슬래시 명령어들:

| 명령어 | 용도 |
|--------|------|
| `/speckit.specify <설명>` | 자연어 설명으로 기능 명세 생성 |
| `/speckit.clarify` | 명세의 모호한 부분 식별 및 해결 (최대 5개 질문) |
| `/speckit.plan` | 기술 계획 생성 (리서치, 데이터 모델, 컨트랙트) |
| `/speckit.tasks` | 계획을 의존성 순서로 정렬된 실행 가능한 태스크로 분해 |
| `/speckit.checklist <도메인>` | 요구사항 품질 체크리스트 생성 (UX, API, 보안 등) |
| `/speckit.analyze` | 구현 전 아티팩트 간 일관성 분석 |
| `/speckit.implement` | tasks.md의 태스크 실행 |

**일반적인 흐름**: specify → clarify → plan → checklist → tasks → analyze → implement

## 기능 디렉토리 구조

각 기능은 브랜치와 `specs/` 내 디렉토리를 생성합니다:

```
specs/[###-feature-name]/
├── spec.md           # 기능 명세 (무엇을 & 왜)
├── plan.md           # 기술 계획 (어떻게)
├── research.md       # 기술 결정 및 근거
├── data-model.md     # 엔티티 및 관계
├── quickstart.md     # 통합 시나리오
├── tasks.md          # 실행 가능한 태스크 목록
├── checklists/       # 요구사항 품질 체크리스트
└── contracts/        # API 명세 (OpenAPI/GraphQL)
```

## Constitution (프로젝트 헌법)

**위치**: `.specify/memory/constitution.md`

모든 개발 활동은 Constitution에 정의된 7가지 핵심 원칙을 준수해야 합니다:

| 원칙 | 핵심 내용 |
|------|----------|
| I. API-First | OpenAPI/gRPC 명세 먼저, 구현 나중 |
| II. Microservice | 도메인별 DB 분리, 독립 배포 가능 |
| III. TDD | Contract/Integration 테스트 필수 |
| IV. Event-Driven | Kafka 기반 비동기 이벤트 전파 |
| V. Security | OWASP Top 10 대응, Pydantic 검증 |
| VI. Observability | 구조화 로깅, 분산 추적, 메트릭 |
| VII. Simplicity | YAGNI, 최소 추상화 |

## 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | Python 3.11+, FastAPI |
| Database | PostgreSQL 15+ (pgvector), Redis 7+ |
| Message Queue | Apache Kafka 3.5+ |
| AI Agent | LangGraph + OpenAI/Anthropic |
| Infrastructure | AWS EKS, Terraform |

## 서비스 구조

```
services/
├── recipe-service (8001)      # 레시피 CRUD, 검색
├── user-service (8002)        # 인증, 사용자 관리
├── cookbook-service (8003)    # 레시피북, 피드백
├── ai-agent-service (8004)    # AI 보정/Q&A
├── embedding-service (8005)   # 벡터 임베딩
├── search-service (8006)      # Elasticsearch
├── notification-service (8007)# 알림
├── analytics-service (8008)   # 이벤트 집계
└── ingestion-service (8009)   # 크롤링 레시피 수신

shared/
├── proto/      # gRPC 정의
├── schemas/    # 공통 Pydantic 모델
└── utils/      # 공통 유틸리티
```

## 핵심 원칙 (Spec-Kit)

- **구현 전 명세 작성**: 코드가 아닌 `/speckit.specify`로 시작
- **유저 스토리는 독립적으로 테스트 가능**: 각 스토리는 MVP 증분으로 독립 구현, 테스트, 배포 가능
- **태스크는 엄격한 형식 준수**: `- [ ] T### [P?] [US#?] 파일 경로와 함께 설명`
  - `[P]` = 병렬 실행 가능 (다른 파일, 의존성 없음)
  - `[US#]` = 명세의 유저 스토리와 매핑
- **체크리스트는 구현이 아닌 요구사항 품질 테스트**: 명세가 완전하고, 명확하고, 일관적인지 검증

## 태스크 실행

`/speckit.implement` 실행 시:
1. Setup 단계 먼저 (프로젝트 구조, 의존성)
2. Foundational 단계는 모든 유저 스토리를 블로킹
3. 유저 스토리는 우선순위 순서로 실행 (P1, P2, P3...)
4. 완료된 태스크는 tasks.md에서 `[X]`로 표시
5. Polish 단계는 마지막 (공통 관심사)
6. **구현 완료 후 자동 커밋**: `/speckit.implement` 종료 시 변경사항을 git commit

## Git Commit 규칙

`/speckit.implement` 완료 후 **반드시** git commit을 수행합니다:

```bash
# 커밋 메시지 형식
feat(###-feature-name): 기능 구현 완료

- 완료된 주요 태스크 요약
- 생성된 파일/디렉토리 요약

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

**예시**:
```bash
feat(001-project-setup): 백엔드 프로젝트 기반 구조 설정

- 9개 마이크로서비스 구조 생성
- Docker Compose 인프라 설정
- shared 패키지 (schemas, utils, proto)
- Alembic 마이그레이션 설정
- GitHub Actions CI 워크플로우

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Active Technologies
- Python 3.11+ + FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.0+, Alembic (001-project-setup)
- PostgreSQL 15+ (pgvector), Redis 7+, Elasticsearch 8+ (001-project-setup)
- Python 3.11+ + FastAPI 0.100+, python-jose, passlib[bcrypt], SQLAlchemy 2.0+, Pydantic 2.0+ (001-user-auth)
- PostgreSQL 15+ (users 테이블), Redis 7+ (세션/블랙리스트) (001-user-auth)
- Python 3.11+ + FastAPI 0.100+, SQLAlchemy, Pydantic, httpx (OAuth HTTP 클라이언트) (002-oauth-social-login)
- PostgreSQL 15+ (user-service DB), Redis 7+ (세션/state 관리) (002-oauth-social-login)
- Python 3.11+ + FastAPI 0.100+, SQLAlchemy, Pydantic, redis[hiredis] (003-recipe-basic-crud)
- PostgreSQL 15+ (Recipe DB), Redis 7+ (캐시) (003-recipe-basic-crud)
- PostgreSQL 15+ (User DB), Redis 7+ (세션 캐시) (003-user-profile-preferences)

## Recent Changes
- 001-project-setup: Added Python 3.11+ + FastAPI 0.100+, SQLAlchemy 2.0+, Pydantic 2.0+, Alembic
