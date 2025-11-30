# SPECKIT_TODO.md - 내시피(Naecipe) 백엔드 스펙 구현 계획

이 문서는 spec-kit 워크플로우를 사용하여 FastAPI 백엔드를 단계적으로 구현하기 위한 스펙 분리 계획입니다.

---

## 개요

**프로젝트**: 내시피(Naecipe) - AI 기반 맞춤형 레시피 보정 서비스
**Core Loop**: 검색 → 레시피 상세 → 조리/사용 → 피드백 입력 → AI 보정 → 보정 레시피 저장

**백엔드 서비스 목록** (FastAPI 기반):
| 서비스 | 포트 | 역할 |
|--------|------|------|
| Recipe Service | 8001 | 레시피 CRUD, 검색 |
| User Service | 8002 | 인증, 사용자 관리 |
| Cookbook Service | 8003 | 레시피북, 피드백 |
| AI Agent Service | 8004 | LangGraph 기반 AI 처리 |
| Embedding Service | 8005 | 벡터 임베딩 생성 |
| Search Service | 8006 | Elasticsearch 연동 |
| Notification Service | 8007 | 푸시, 이메일 발송 |
| Analytics Service | 8008 | 이벤트 집계, 통계 |
| Recipe Ingestion Service | 8009 | 크롤링 레시피 수신, 중복 검사 |

---

## 스펙 구현 순서 (의존성 기반)

### Phase 0: 프로젝트 기반 설정
> `/speckit.specify` 실행 전 프로젝트 기본 구조 설정

- [ ] **SPEC-000**: 프로젝트 기반 설정
  - FastAPI 프로젝트 구조 (모노레포 vs 멀티레포)
  - 공통 라이브러리 (shared 패키지)
  - Docker 개발 환경
  - PostgreSQL + Redis + Elasticsearch 로컬 설정
  - Alembic 마이그레이션 설정
  - 환경 변수 관리 (.env)

---

### Phase 1: Core Services (핵심 서비스)

#### 1-1. User Service (인증/사용자 - 최우선)
> 모든 서비스가 인증에 의존하므로 가장 먼저 구현

- [ ] **SPEC-001**: 사용자 인증 기본
  - 이메일 회원가입 / 로그인
  - JWT 토큰 발급 (Access + Refresh)
  - 비밀번호 해싱 (bcrypt)
  - 세션 관리 (Redis)
  - **관련 API**: `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `POST /auth/refresh`
  - **DB 테이블**: `users`, `sessions`

- [ ] **SPEC-002**: OAuth 소셜 로그인
  - Google OAuth
  - Kakao OAuth
  - Naver OAuth
  - **관련 API**: `POST /auth/oauth/:provider`
  - **DB 테이블**: `oauth_accounts`

- [ ] **SPEC-003**: 사용자 프로필 및 취향 설정
  - 프로필 조회/수정
  - 식이 제한, 알레르기 설정
  - 맛 취향 프로파일 (단맛, 짠맛, 매운맛, 신맛)
  - **관련 API**: `GET /users/me`, `PUT /users/me`, `PUT /users/me/preferences`
  - **DB 테이블**: `user_profiles`, `taste_preferences`

---

#### 1-2. Recipe Service (레시피 - Core Loop 시작점)
> 검색과 상세 조회가 Core Loop의 시작

- [ ] **SPEC-004**: 레시피 기본 CRUD
  - 레시피 상세 조회
  - 레시피 목록 조회 (페이지네이션)
  - 인기 레시피 조회
  - **관련 API**: `GET /recipes/:id`, `GET /recipes`, `GET /recipes/popular`
  - **DB 테이블**: `recipes`, `ingredients`, `cooking_steps`, `tags`, `recipe_tags`
  - **캐시**: Redis (recipe:{id})

- [ ] **SPEC-005**: 레시피 검색
  - 키워드 검색 (제목, 설명, 재료)
  - 필터링 (난이도, 조리시간, 태그)
  - 정렬 (종합 스코어, 최신순, 조리시간순)
  - Cursor 기반 페이지네이션
  - **관련 API**: `GET /recipes/search`
  - **연동**: Elasticsearch

- [ ] **SPEC-006**: 유사 레시피 추천
  - 콘텐츠 기반 유사 레시피
  - 태그 기반 관련 레시피
  - **관련 API**: `GET /recipes/:id/similar`

---

#### 1-3. Cookbook Service (레시피북 - Core Loop 저장)
> 레시피 저장과 피드백이 AI 보정으로 연결

- [ ] **SPEC-007**: 레시피북 기본 CRUD
  - 레시피북 생성/조회/수정/삭제
  - 기본 레시피북 자동 생성
  - **관련 API**: `GET /cookbooks`, `POST /cookbooks`, `GET /cookbooks/:id`, `PUT /cookbooks/:id`, `DELETE /cookbooks/:id`
  - **DB 테이블**: `cookbooks`

- [ ] **SPEC-008**: 레시피북에 레시피 저장
  - 레시피 저장 (원본 레시피 참조)
  - 저장된 레시피 목록 조회
  - 저장 삭제
  - 개인 메모 기능
  - **관련 API**: `POST /cookbooks/:id/recipes`, `GET /cookbooks/:id/recipes`, `DELETE /cookbooks/:id/recipes/:recipeId`
  - **DB 테이블**: `cookbook_recipes`

- [ ] **SPEC-009**: 조리 기록 및 피드백
  - 조리 시작/완료 기록
  - 피드백 제출 (맛 평점, 난이도 평점, 텍스트, 조정 요청)
  - 피드백 제출 시 AI 보정 요청 트리거 (Kafka 이벤트)
  - **관련 API**: `POST /cookbooks/:id/recipes/:recipeId/cook`, `POST /cookbooks/:id/recipes/:recipeId/feedback`
  - **DB 테이블**: `cooking_feedbacks`, `cooking_histories`
  - **이벤트**: `FeedbackSubmitted` → Kafka

- [ ] **SPEC-010**: 레시피 버전 관리
  - 보정 레시피 버전 히스토리
  - 원본 vs 보정 비교
  - 버전 롤백
  - **관련 API**: `GET /cookbooks/:id/recipes/:recipeId/versions`
  - **DB 테이블**: `recipe_versions`

---

### Phase 2: AI Services (AI 서비스)

#### 2-1. AI Agent Service (핵심 AI 기능)
> Core Loop의 핵심 - 피드백 기반 레시피 보정

- [ ] **SPEC-011**: AI 보정 에이전트 (Adjustment Agent)
  - LangGraph 워크플로우 구현
  - 피드백 파싱 → 분석 → 지식 검색 → 보정 계획 → 실행 → 검증
  - OpenAI GPT-4 + Claude Fallback
  - **이벤트 소비**: `FeedbackSubmitted`
  - **이벤트 발행**: `AdjustmentCompleted`
  - **관련 API**: `GET /ai/adjustments/:id`
  - **DB 테이블**: `adjustment_requests`

- [ ] **SPEC-012**: Q&A 에이전트 (Q&A Agent)
  - 조리 중 질문 응답
  - 질문 분류 (레시피 관련, 기술, 대체 재료, 시간, 문제 해결)
  - RAG 기반 지식 검색
  - 대화 히스토리 관리
  - **관련 API**: `POST /ai/qa`, `GET /ai/qa/sessions/:sessionId`
  - **DB 테이블**: `qa_sessions`

---

#### 2-2. Embedding Service (벡터 임베딩)

- [ ] **SPEC-013**: 벡터 임베딩 서비스
  - 레시피 청킹 전략 (개요, 재료, 조리 단계)
  - OpenAI ada-002 임베딩 생성
  - pgvector 저장 및 유사도 검색
  - **DB 테이블**: `knowledge_chunks`
  - **연동**: pgvector

---

### Phase 3: Support Services (지원 서비스)

#### 3-1. Search Service (검색)

- [ ] **SPEC-014**: Elasticsearch 검색 서비스
  - 레시피 인덱싱
  - 한국어 형태소 분석 (nori)
  - 검색 쿼리 빌더
  - 자동완성
  - **연동**: Elasticsearch

---

#### 3-2. Recipe Ingestion Service (레시피 수집)

- [ ] **SPEC-015**: 레시피 수집 API
  - 크롤링된 레시피 수신
  - 중복 검사 (제목+저자, URL, 콘텐츠 해시)
  - 품질/인기도/노출도 스코어 계산
  - 벌크 등록
  - **관련 API**: `POST /ingestion/recipes`, `POST /ingestion/check-duplicate`, `PATCH /ingestion/recipes/:id/scores`, `POST /ingestion/bulk`
  - **DB 테이블**: `recipe_sources`, `recipe_score_history`

---

#### 3-3. Notification Service (알림)

- [ ] **SPEC-016**: 알림 서비스
  - AI 보정 완료 알림
  - 푸시 알림 (FCM)
  - 이메일 알림
  - **이벤트 소비**: `AdjustmentCompleted`

---

#### 3-4. Analytics Service (분석)

- [ ] **SPEC-017**: 이벤트 수집 및 분석
  - 이벤트 수신 (Kafka)
  - TimescaleDB 저장
  - 일별/주별 집계
  - **이벤트 소비**: 모든 도메인 이벤트
  - **DB**: TimescaleDB (`events`, `user_metrics`, `recipe_metrics`)

---

### Phase 4: Infrastructure (인프라)

- [ ] **SPEC-018**: API Gateway (Kong)
  - 라우팅 설정
  - Rate Limiting
  - JWT 검증 플러그인
  - CORS 설정

- [ ] **SPEC-019**: 메시지 큐 (Kafka)
  - 토픽 설정 (`recipe.events`, `user.events`, `cookbook.events`, `feedback.events`, `ai.events`)
  - Consumer Group 설정
  - 이벤트 스키마 정의

- [ ] **SPEC-020**: 서비스 간 통신 (gRPC)
  - Proto 파일 정의
  - Recipe Service gRPC
  - User Service gRPC
  - Cookbook Service gRPC

---

### Phase 5: Crawler Bot (별도 프로젝트)

- [ ] **SPEC-021**: Recipe Crawler Agent
  - LangGraph 기반 크롤러
  - YouTube 크롤러
  - Instagram 크롤러
  - 블로그 크롤러 (네이버, 티스토리)
  - 스케줄러 (APScheduler)
  - **연동**: Ingestion Service API

---

## 권장 구현 순서

```
Phase 0: SPEC-000 (프로젝트 기반 설정)
    ↓
Phase 1-1: SPEC-001 → SPEC-002 → SPEC-003 (User Service)
    ↓
Phase 1-2: SPEC-004 → SPEC-005 → SPEC-006 (Recipe Service)
    ↓
Phase 1-3: SPEC-007 → SPEC-008 → SPEC-009 → SPEC-010 (Cookbook Service)
    ↓
Phase 2: SPEC-013 → SPEC-011 → SPEC-012 (AI Services - Embedding 먼저)
    ↓
Phase 3: SPEC-014 → SPEC-015 → SPEC-016 → SPEC-017 (Support Services)
    ↓
Phase 4: SPEC-018 → SPEC-019 → SPEC-020 (Infrastructure)
    ↓
Phase 5: SPEC-021 (Crawler Bot - 별도)
```

---

## Spec-kit 사용 예시

각 스펙을 구현할 때:

```bash
# 1. 스펙 작성
/speckit.specify SPEC-001: 사용자 인증 기본 - 이메일 회원가입/로그인, JWT 토큰, 세션 관리

# 2. 모호한 부분 명확화
/speckit.clarify

# 3. 기술 계획 수립
/speckit.plan

# 4. 체크리스트 생성 (필요시)
/speckit.checklist api
/speckit.checklist security

# 5. 태스크 분해
/speckit.tasks

# 6. 일관성 분석
/speckit.analyze

# 7. 구현
/speckit.implement
```

---

## 우선순위 표시

| 우선순위 | 스펙 | 이유 |
|---------|------|------|
| P0 | SPEC-000 | 모든 서비스의 기반 |
| P0 | SPEC-001, 002, 003 | 인증은 모든 서비스의 전제 조건 |
| P1 | SPEC-004, 005 | Core Loop 시작점 |
| P1 | SPEC-007, 008, 009 | Core Loop 핵심 (저장, 피드백) |
| P1 | SPEC-011, 013 | Core Loop 핵심 (AI 보정) |
| P2 | SPEC-010, 012 | Core Loop 확장 |
| P2 | SPEC-014, 015 | 검색 품질, 레시피 수집 |
| P3 | SPEC-006, 016, 017 | 부가 기능 |
| P3 | SPEC-018, 019, 020 | 프로덕션 준비 |
| P4 | SPEC-021 | 데이터 확보 (별도 진행 가능) |

---

## 참고 문서

- `../PLANS/2-1REQUIREMENT.md` - 요구사항 정의
- `../PLANS/5-1SERVICE_ARCHITECTURE.md` - 서비스 아키텍처
- `../PLANS/5-1-1_DOMAIN.md` - 도메인 분석
- `../PLANS/5-1-2_SYSTEM.md` - 시스템 아키텍처
- `../PLANS/5-1-3_AI_AGENT.md` - AI 에이전트
- `../PLANS/5-1-4_API.md` - API 설계
- `../PLANS/5-1-7_SECURITY.md` - 보안 및 품질
