# CLAUDE.md

이 파일은 Claude Code (claude.ai/code)가 이 저장소에서 작업할 때 참고하는 가이드입니다.

## 커뮤니케이션 언어

**모든 소통은 한국어로 진행합니다.** 코드 주석, 커밋 메시지, 문서 작성 시 한국어를 사용하세요. 단, 코드 내 변수명, 함수명 등은 영문을 유지합니다.

## 프로젝트 개요

**내시피(Naecipe) 백엔드** - AI 기반 맞춤형 레시피 보정 서비스의 **백엔드 전용** 저장소입니다.

> **중요**: 이 저장소는 **백엔드(서버) 코드만** 관리합니다. 프론트엔드, 모바일 앱, 인프라 코드는 별도 저장소에서 관리됩니다.

- **역할**: REST API, 도메인 모듈, 비동기 작업 처리, AI 에이전트 등 서버 사이드 로직
- **Core Loop**: 검색 → 레시피 상세 → 조리/사용 → 피드백 입력 → AI 보정 → 보정 레시피 저장
- **아키텍처**: Python FastAPI 기반 모듈러 모놀리스 (v2.0, 2025.12.10)
- **워크플로우**: spec-kit 명세 기반 개발 (specify → clarify → plan → tasks → implement)

## Spec-Kit 워크플로우 명령어

> **⚠️ 중요**: 스펙 생성 전 **반드시** `SPECKIT_TODO.md`를 먼저 참조하세요. 이 문서에는 전체 스펙 목록(SPEC-000~021), 도메인 용어 정의, ERD, 비동기 이벤트, 캐시 전략, 보안 요구사항 등이 정의되어 있습니다.

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
| I. API-First | OpenAPI 명세 먼저, 구현 나중 |
| II. Modular Monolith | 도메인 모듈 분리, 스키마 분리 (단일 PostgreSQL) |
| III. TDD | Contract/Integration 테스트 필수 |
| IV. Async Task | BackgroundTasks 기반 비동기 처리 |
| V. Security | OWASP Top 10 대응, Pydantic 검증 |
| VI. Observability | 구조화 로깅 (CloudWatch), 메트릭 |
| VII. Simplicity | YAGNI, 최소 추상화 |

## 기술 스택

| 구분 | 기술 |
|------|------|
| Backend | Python 3.11+, FastAPI |
| Database | PostgreSQL 15+ (pgvector, 스키마 분리), Redis 7+ |
| Async Processing | FastAPI BackgroundTasks (필요 시 SQS) |
| AI Agent | LangGraph + OpenAI/Anthropic |
| Infrastructure | AWS ECS Fargate, CloudWatch |

## 프로젝트 구조 (모듈러 모놀리스 v2.0)

```
app/                           # 단일 FastAPI 앱
├── core/                      # 공유 설정, 보안, 의존성
│   ├── config.py
│   ├── security.py
│   └── dependencies.py
├── infra/                     # 인프라 레이어 (DB, Redis, S3)
│   ├── database.py
│   ├── redis.py
│   └── s3.py
├── recipes/                   # 레시피 도메인 모듈
│   ├── models.py
│   ├── schemas.py
│   ├── services.py
│   └── router.py
├── users/                     # 사용자 도메인 모듈
├── cookbooks/                 # 레시피북/피드백 모듈
├── ai_agent/                  # AI 보정 모듈
├── knowledge/                 # 임베딩/검색 모듈
├── notifications/             # 알림 모듈
├── analytics/                 # 분석 모듈
├── ingestion/                 # 크롤링 수신 모듈
└── main.py                    # FastAPI 앱 진입점

shared/
├── schemas/    # 공통 Pydantic 모델
└── utils/      # 공통 유틸리티
```

## 핵심 원칙 (Spec-Kit)

- **SPECKIT_TODO.md 필수 참조**: 스펙 생성 전 `SPECKIT_TODO.md`를 읽어 해당 SPEC의 요구사항, 의존성, DB 테이블, API 명세를 확인
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

- 모듈러 모놀리스 구조 생성 (app/ + 8개 도메인 모듈)
- Docker Compose 인프라 설정
- shared 패키지 (schemas, utils)
- Alembic 마이그레이션 설정
- GitHub Actions CI 워크플로우

🤖 Generated with Claude Code
Co-Authored-By: Claude <noreply@anthropic.com>
```

## Active Technologies

**Core Stack (모듈러 모놀리스)**:
- Python 3.11+ + FastAPI 0.100+
- SQLAlchemy 2.0+ + Pydantic 2.0+ + Alembic
- PostgreSQL 15+ (단일 DB, 스키마 분리, pgvector)
- Redis 7+ (단일 인스턴스, 세션/캐시)

**모듈별 추가 기술**:
- users: python-jose, passlib[bcrypt], httpx (OAuth)
- recipes: redis[hiredis] (캐싱)
- ai_agent: LangGraph (예정)

## Recent Changes
- 006-modular-monolith-refactoring: 마이크로서비스 → 모듈러 모놀리스 전환
  - 9개 독립 서비스 → 단일 FastAPI 앱 (8개 도메인 모듈)
  - Kafka/Zookeeper 제거 → FastAPI BackgroundTasks
  - 분리 DB → 단일 PostgreSQL (스키마 분리)
