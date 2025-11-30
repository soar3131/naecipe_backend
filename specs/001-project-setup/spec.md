# Feature Specification: 백엔드 프로젝트 기반 설정

**Feature Branch**: `001-project-setup`
**Created**: 2025-11-30
**Status**: Draft
**Input**: SPEC-000 - 내시피(Naecipe) 백엔드 프로젝트 기반 설정

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 백엔드 개발 환경 구성 (Priority: P1)

백엔드 개발자가 저장소를 클론한 후, 단일 명령어로 Python 개발 환경과 로컬 인프라(DB, Redis, Elasticsearch)를 구성하여 API 개발을 즉시 시작할 수 있어야 한다.

**Why this priority**: 모든 백엔드 개발의 시작점이며, 개발자 온보딩 시간을 최소화한다.

**Independent Test**: 새 개발자가 저장소 클론 후 5분 내에 API 서버를 시작하고 `/health` 엔드포인트가 응답한다.

**Acceptance Scenarios**:

1. **Given** 개발자가 저장소를 클론한 상태, **When** 환경 설정 명령어를 실행하면, **Then** Python 가상환경이 생성되고 모든 의존성이 설치된다.
2. **Given** 환경 설정이 완료된 상태, **When** 로컬 인프라 시작 명령어를 실행하면, **Then** PostgreSQL, Redis, Elasticsearch 컨테이너가 실행되고 연결 가능하다.
3. **Given** 인프라가 실행 중인 상태, **When** API 서버를 시작하면, **Then** 헬스체크 엔드포인트(`/health`)가 200 OK를 반환한다.

---

### User Story 2 - 개별 마이크로서비스 개발 (Priority: P2)

백엔드 개발자가 담당하는 특정 마이크로서비스만 실행하여 API를 개발하고 테스트할 수 있어야 한다.

**Why this priority**: 9개 서비스를 모두 실행하지 않고 담당 서비스만 집중 개발하여 리소스와 시간을 절약한다.

**Independent Test**: recipe-service만 단독 실행하고 `/v1/recipes` API가 정상 응답한다.

**Acceptance Scenarios**:

1. **Given** 로컬 인프라가 실행 중인 상태, **When** 특정 서비스(예: recipe-service)만 시작하면, **Then** 해당 서비스만 실행되고 다른 서비스는 실행되지 않는다.
2. **Given** 서비스가 실행 중인 상태, **When** 해당 서비스의 API를 호출하면, **Then** 정상적으로 응답한다.
3. **Given** 서비스가 실행 중인 상태, **When** Python 코드를 수정하면, **Then** 서버가 자동으로 재시작되어 변경사항이 반영된다.

---

### User Story 3 - 공통 패키지 활용 (Priority: P3)

백엔드 개발자가 여러 서비스에서 공통으로 사용하는 Pydantic 스키마, gRPC proto, 유틸리티 함수를 shared 패키지에서 import하여 사용할 수 있어야 한다.

**Why this priority**: 코드 중복을 방지하고, 서비스 간 데이터 구조의 일관성을 보장한다.

**Independent Test**: shared 패키지의 스키마를 두 개 이상의 서비스에서 import하여 사용할 수 있다.

**Acceptance Scenarios**:

1. **Given** shared 패키지에 Pydantic 스키마가 정의된 상태, **When** 서비스에서 해당 스키마를 import하면, **Then** 정상적으로 사용할 수 있다.
2. **Given** shared 패키지에 gRPC proto가 정의된 상태, **When** Python 코드를 생성하면, **Then** 서비스에서 gRPC 클라이언트/서버 코드로 사용할 수 있다.
3. **Given** shared 패키지를 수정한 상태, **When** 의존 서비스의 테스트를 실행하면, **Then** 변경사항이 즉시 반영된다.

---

### User Story 4 - 데이터베이스 스키마 관리 (Priority: P4)

백엔드 개발자가 SQLAlchemy 모델 변경 시 마이그레이션 파일을 생성하고, 로컬 및 원격 데이터베이스에 안전하게 적용할 수 있어야 한다.

**Why this priority**: 스키마 변경의 버전 관리와 팀 간 동기화, 배포 시 안전한 마이그레이션을 보장한다.

**Independent Test**: 모델에 컬럼을 추가하고 마이그레이션을 생성/적용한 후 롤백하여 이전 상태로 복원할 수 있다.

**Acceptance Scenarios**:

1. **Given** SQLAlchemy 모델이 변경된 상태, **When** 마이그레이션 생성 명령어를 실행하면, **Then** 변경사항을 반영하는 마이그레이션 파일이 생성된다.
2. **Given** 마이그레이션 파일이 있는 상태, **When** 마이그레이션 적용 명령어를 실행하면, **Then** PostgreSQL 스키마가 업데이트된다.
3. **Given** 마이그레이션이 적용된 상태, **When** 롤백 명령어를 실행하면, **Then** 이전 스키마 버전으로 복원된다.

---

### User Story 5 - 환경별 설정 관리 (Priority: P5)

백엔드 개발자가 개발/스테이징/프로덕션 환경별로 다른 설정(DB 연결, API 키 등)을 안전하게 관리할 수 있어야 한다.

**Why this priority**: 환경별 설정 분리로 실수를 방지하고, 민감 정보의 보안을 보장한다.

**Independent Test**: `.env.example`을 복사하여 로컬 `.env`를 생성하고 서비스가 해당 설정으로 시작한다.

**Acceptance Scenarios**:

1. **Given** `.env.example` 템플릿이 있는 상태, **When** 개발자가 `.env` 파일을 생성하면, **Then** 서비스가 해당 환경 변수로 시작된다.
2. **Given** 필수 환경 변수가 누락된 상태, **When** 서비스를 시작하면, **Then** 누락된 변수명과 함께 명확한 오류 메시지가 표시된다.
3. **Given** 환경 변수가 설정된 상태, **When** 서비스가 시작되면, **Then** 비밀번호, API 키 등 민감 정보가 로그에 마스킹되어 표시된다.

---

### Edge Cases

- 포트 충돌(8001-8009) 시 명확한 오류 메시지와 해결 방법 안내
- PostgreSQL/Redis/Elasticsearch 컨테이너 미실행 시 연결 재시도 및 타임아웃 처리
- Python 버전 불일치(3.11 미만) 시 경고 메시지
- 가상환경 미활성화 상태에서 명령어 실행 시 안내 메시지

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 백엔드 저장소는 9개 마이크로서비스를 모노레포 구조로 관리해야 한다 (services/ 디렉토리)
- **FR-002**: 각 서비스는 독립적인 Python 패키지 구조(src/, tests/, pyproject.toml)를 가져야 한다
- **FR-003**: 공통 코드는 shared/ 패키지로 분리하여 서비스 간 공유해야 한다 (proto/, schemas/, utils/)
- **FR-004**: Docker Compose로 로컬 인프라(PostgreSQL, Redis, Elasticsearch, Kafka)를 제공해야 한다
- **FR-005**: Alembic을 사용하여 서비스별 데이터베이스 마이그레이션을 관리해야 한다
- **FR-006**: Pydantic Settings를 사용하여 환경 변수를 검증하고 타입 안전하게 로드해야 한다
- **FR-007**: 각 서비스는 `/health` 및 `/ready` 엔드포인트를 제공해야 한다
- **FR-008**: uvicorn의 `--reload` 옵션으로 코드 변경 시 자동 재시작을 지원해야 한다
- **FR-009**: pytest를 사용하여 unit/integration/contract 테스트를 실행할 수 있어야 한다
- **FR-010**: mypy, ruff, black을 사용하여 코드 품질을 검증해야 한다

### Key Entities

- **Service**: 마이크로서비스 (이름, 포트, 의존 인프라, 담당 도메인)
- **SharedPackage**: 공통 패키지 (proto 정의, Pydantic 스키마, 유틸리티)
- **Migration**: Alembic 마이그레이션 (버전, 변경 내용, 적용 상태)
- **Environment**: 환경 설정 (필수/선택 변수, 기본값, 검증 규칙)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 신규 백엔드 개발자가 저장소 클론 후 5분 내에 API 서버를 시작할 수 있다
- **SC-002**: 단일 서비스 시작 시 30초 내에 `/health` 엔드포인트가 200 OK를 반환한다
- **SC-003**: Python 코드 변경 후 3초 내에 서버가 자동 재시작된다
- **SC-004**: 마이그레이션 생성/적용/롤백이 각각 30초 내에 완료된다
- **SC-005**: 필수 환경 변수 누락 시 서비스 시작 전에 ValidationError가 발생한다
- **SC-006**: 9개 서비스와 로컬 인프라 동시 실행 시 8GB 메모리 내에서 동작한다
- **SC-007**: `pytest`로 전체 테스트 실행 시 5분 내에 완료된다

## Assumptions

- 개발 머신에 Docker Desktop 또는 Docker Engine이 설치되어 있다
- 개발 머신에 Python 3.11 이상이 설치되어 있다
- 개발 머신에 최소 8GB RAM과 20GB 여유 디스크 공간이 있다
- 초기 설정 시 인터넷 연결이 필요하나, 이후 캐시된 의존성으로 오프라인 개발 가능하다
