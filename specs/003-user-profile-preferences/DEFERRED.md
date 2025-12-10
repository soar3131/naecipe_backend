# SPEC-003 미구현 사항 (Deferred Items)

**작성일**: 2024-12-10
**스펙**: 사용자 프로필 및 취향 설정
**브랜치**: `003-user-profile-preferences`

---

## 개요

SPEC-003 구현 시 핵심 기능(MVP)은 모두 완료되었으나, 성능 최적화 및 시스템 통합 관련 일부 태스크는 의도적으로 연기되었습니다. 이 문서는 해당 항목들의 상세 내용과 구현 시점/방법을 기록합니다.

---

## 1. Redis 캐싱 구현 (T034)

### 태스크 정보
- **ID**: T034
- **우선순위**: 선택적 최적화
- **대상 파일**: `src/user_service/services/profile.py`

### 배경 및 맥락

프로필 조회(`GET /api/v1/users/me`)는 매 API 호출마다 데이터베이스 쿼리를 실행합니다. 현재 구조:

```python
# services/profile.py - 현재 구현
async def get_profile(self, user_id: str) -> Optional[ProfileData]:
    result = await self.db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    # ... 매번 DB 조회
```

### 구현 필요 시점

다음 조건 중 하나라도 해당되면 구현 권장:
- 동시 접속자 100명 이상
- 프로필 조회 API 응답 시간 > 200ms
- 데이터베이스 부하가 병목으로 확인될 때

### 구현 방법

#### 1단계: Redis 키 설계

```python
# 키 패턴
PROFILE_CACHE_KEY = "user:profile:{user_id}"
PROFILE_CACHE_TTL = 300  # 5분

PREFERENCES_CACHE_KEY = "user:preferences:{user_id}"
PREFERENCES_CACHE_TTL = 300  # 5분
```

#### 2단계: 캐시 조회/저장 로직

```python
# services/profile.py 수정 예시
from user_service.db.redis import get_redis
import json

class ProfileService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_profile(self, user_id: str) -> Optional[ProfileData]:
        redis = await get_redis()
        cache_key = f"user:profile:{user_id}"

        # 1. 캐시 확인
        cached = await redis.get(cache_key)
        if cached:
            data = json.loads(cached)
            return ProfileData(**data)

        # 2. DB 조회
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return None

        profile = user.profile
        if not profile:
            profile = await self._create_default_profile(user_id)

        profile_data = ProfileData(
            id=user.id,
            email=user.email,
            displayName=profile.display_name or user.email.split("@")[0],
            profileImageUrl=profile.profile_image_url,
            createdAt=user.created_at,
            updatedAt=profile.updated_at,
        )

        # 3. 캐시 저장
        await redis.setex(
            cache_key,
            300,  # TTL 5분
            profile_data.model_dump_json()
        )

        return profile_data
```

#### 3단계: 캐시 무효화 로직

```python
async def update_profile(self, user_id: str, data: ProfileUpdateRequest) -> Optional[ProfileData]:
    # ... 기존 업데이트 로직 ...

    # 캐시 무효화
    redis = await get_redis()
    await redis.delete(f"user:profile:{user_id}")

    return updated_profile_data
```

### 주의사항

1. **캐시 일관성**: 프로필 수정 시 반드시 캐시 삭제
2. **TTL 설정**: 너무 길면 stale 데이터, 너무 짧으면 캐시 효과 감소
3. **Redis 장애 대응**: Redis 연결 실패 시 DB fallback 필요

### 테스트 시나리오

```python
# tests/test_profile_cache.py
async def test_profile_cache_hit():
    """프로필 조회 시 캐시 히트 확인"""
    # 1. 첫 번째 조회 - DB hit, 캐시 저장
    # 2. 두 번째 조회 - 캐시 hit, DB 미조회
    pass

async def test_profile_cache_invalidation():
    """프로필 수정 시 캐시 무효화 확인"""
    # 1. 프로필 조회 - 캐시 저장
    # 2. 프로필 수정 - 캐시 삭제
    # 3. 프로필 조회 - DB hit (캐시 미스)
    pass
```

---

## 2. UserPreferenceUpdated Kafka 이벤트 발행 (T035)

### 태스크 정보
- **ID**: T035
- **우선순위**: 선택적 최적화
- **대상 파일**: `src/user_service/events/preference.py` (신규 생성)

### 배경 및 맥락

사용자 취향 설정이 변경되면 다른 서비스들이 이를 알아야 합니다:

1. **AI Agent Service**: 레시피 보정 시 최신 취향 반영 필요
2. **Analytics Service**: 취향 변경 추적 및 통계
3. **Recommendation Service**: 추천 알고리즘 재계산

현재 구조에서는 취향 변경 시 이벤트가 발행되지 않아, 다른 서비스들이 변경을 인지하려면 직접 API를 호출해야 합니다.

### 구현 필요 시점

다음 조건 중 하나라도 해당되면 구현 필요:
- AI Agent Service 연동 시작 시 (SPEC-009 이후)
- Analytics Service 취향 변경 추적 요구 시
- 마이크로서비스 간 비동기 통신 필요 시

### 이벤트 설계

#### 이벤트 스키마 (research.md 기반)

```json
{
  "event_type": "UserPreferenceUpdated",
  "event_id": "uuid",
  "timestamp": "2024-12-10T12:00:00Z",
  "user_id": "user-uuid",
  "changes": {
    "dietary_restrictions": {
      "before": ["vegetarian"],
      "after": ["vegetarian", "gluten_free"]
    },
    "taste_preferences": {
      "before": {"overall": {"spiciness": 3}},
      "after": {"overall": {"spiciness": 4}}
    }
  }
}
```

### 구현 방법

#### 1단계: events 디렉토리 및 기본 구조 생성

```bash
mkdir -p services/user-service/src/user_service/events
touch services/user-service/src/user_service/events/__init__.py
```

#### 2단계: Kafka 프로듀서 설정

```python
# events/kafka_producer.py
from aiokafka import AIOKafkaProducer
import json
from user_service.core.config import settings

_producer: AIOKafkaProducer | None = None

async def get_kafka_producer() -> AIOKafkaProducer:
    global _producer
    if _producer is None:
        _producer = AIOKafkaProducer(
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        )
        await _producer.start()
    return _producer

async def close_kafka_producer():
    global _producer
    if _producer:
        await _producer.stop()
        _producer = None
```

#### 3단계: 이벤트 발행 모듈

```python
# events/preference.py
from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

from user_service.events.kafka_producer import get_kafka_producer

TOPIC_USER_PREFERENCE = "user.preference.updated"

async def publish_preference_updated(
    user_id: str,
    changes: Dict[str, Any],
) -> None:
    """사용자 취향 변경 이벤트 발행

    Args:
        user_id: 사용자 UUID
        changes: 변경된 필드 정보 (before/after)
    """
    event = {
        "event_type": "UserPreferenceUpdated",
        "event_id": str(uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "user_id": user_id,
        "changes": changes,
    }

    producer = await get_kafka_producer()
    await producer.send_and_wait(
        topic=TOPIC_USER_PREFERENCE,
        value=event,
        key=user_id.encode('utf-8'),
    )
```

#### 4단계: 서비스 레이어에 이벤트 발행 추가

```python
# services/preference.py 수정
from user_service.events.preference import publish_preference_updated

class PreferenceService:
    async def update_preferences(
        self,
        user_id: str,
        data: PreferencesUpdateRequest,
    ) -> Optional[PreferencesData]:
        # 변경 전 상태 저장
        before = await self.get_preferences(user_id)

        # ... 기존 업데이트 로직 ...

        # 변경 후 상태
        after = await self.get_preferences(user_id)

        # 이벤트 발행 (변경된 경우에만)
        changes = self._compute_changes(before, after)
        if changes:
            await publish_preference_updated(user_id, changes)

        return after

    def _compute_changes(
        self,
        before: PreferencesData,
        after: PreferencesData,
    ) -> Dict[str, Any]:
        """변경된 필드만 추출"""
        changes = {}

        if before.dietary_restrictions != after.dietary_restrictions:
            changes["dietary_restrictions"] = {
                "before": before.dietary_restrictions,
                "after": after.dietary_restrictions,
            }

        if before.allergies != after.allergies:
            changes["allergies"] = {
                "before": before.allergies,
                "after": after.allergies,
            }

        # ... 다른 필드들도 동일하게 ...

        return changes
```

### 설정 추가 필요

```python
# core/config.py에 추가
class Settings(BaseSettings):
    # ... 기존 설정 ...

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_TOPIC_USER_PREFERENCE: str = "user.preference.updated"
```

### 컨슈머 서비스 연동

이벤트를 소비하는 서비스들 (AI Agent, Analytics)에서:

```python
# ai-agent-service/events/handlers.py
from aiokafka import AIOKafkaConsumer

async def handle_preference_updated(event: dict):
    """사용자 취향 변경 이벤트 처리

    - 해당 사용자의 캐시된 취향 정보 무효화
    - 필요 시 추천 모델 재계산 트리거
    """
    user_id = event["user_id"]
    changes = event["changes"]

    # 캐시 무효화
    await invalidate_user_preference_cache(user_id)

    # 알레르기 변경 시 추가 처리
    if "allergies" in changes:
        await update_safety_filters(user_id, changes["allergies"]["after"])
```

### 주의사항

1. **멱등성**: 이벤트 중복 수신 대응 (event_id로 중복 체크)
2. **순서 보장**: 같은 사용자 이벤트는 순서 보장 필요 (user_id를 파티션 키로 사용)
3. **에러 처리**: Kafka 연결 실패 시 로컬 큐잉 또는 재시도 로직
4. **모니터링**: 이벤트 발행/소비 지연 모니터링

### 테스트 시나리오

```python
# tests/test_preference_events.py
async def test_preference_update_publishes_event():
    """취향 변경 시 Kafka 이벤트 발행 확인"""
    # Mock Kafka producer
    # 취향 변경 API 호출
    # 이벤트 발행 확인
    pass

async def test_no_event_when_no_changes():
    """변경 없을 시 이벤트 미발행 확인"""
    # 동일한 값으로 업데이트
    # 이벤트 미발행 확인
    pass
```

---

## 3. Quickstart 시나리오 검증 (T037)

### 태스크 정보
- **ID**: T037
- **우선순위**: 검증
- **참조 파일**: `specs/003-user-profile-preferences/quickstart.md`

### 배경

구현된 API가 quickstart.md에 정의된 시나리오대로 동작하는지 수동 검증이 필요합니다.

### 검증 시나리오 목록

quickstart.md에 정의된 6개 시나리오:

1. **신규 사용자 프로필 설정**
   - 회원가입 → 로그인 → 프로필 조회 → 표시 이름 설정

2. **취향 옵션 조회**
   - 식이 제한 옵션 → 알레르기 옵션 → 요리 카테고리 옵션

3. **유효성 검사 에러**
   - 잘못된 식이 제한 값 → 422 에러 확인

4. **인증 에러**
   - 토큰 없이 요청 → 401 에러 확인

5. **취향 초기화**
   - 빈 배열로 업데이트 → 초기화 확인

6. **전체 취향 설정**
   - 모든 필드 한 번에 설정 → 조회로 확인

### 검증 방법

```bash
# 1. 서비스 실행
cd services/user-service
docker-compose up -d db redis
uvicorn user_service.main:app --reload --port 8002

# 2. 시나리오별 curl 테스트 (quickstart.md 참조)

# 시나리오 1: 신규 사용자 프로필 설정
curl -X POST http://localhost:8002/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "Password123!"}'

# ... (quickstart.md의 curl 명령어 순차 실행)
```

### 자동화 테스트 (향후)

```python
# tests/integration/test_quickstart_scenarios.py
import pytest
import httpx

@pytest.mark.integration
async def test_scenario_1_new_user_profile_setup():
    """시나리오 1: 신규 사용자 프로필 설정"""
    async with httpx.AsyncClient(base_url="http://localhost:8002") as client:
        # 1. 회원가입
        response = await client.post("/api/v1/auth/register", json={
            "email": "test@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 201

        # 2. 로그인
        response = await client.post("/api/v1/auth/login", json={
            "email": "test@example.com",
            "password": "Password123!"
        })
        assert response.status_code == 200
        token = response.json()["access_token"]

        # 3. 프로필 조회
        headers = {"Authorization": f"Bearer {token}"}
        response = await client.get("/api/v1/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["data"]["email"] == "test@example.com"

        # 4. 표시 이름 설정
        response = await client.put("/api/v1/users/me", headers=headers, json={
            "displayName": "홍길동"
        })
        assert response.status_code == 200
        assert response.json()["data"]["displayName"] == "홍길동"
```

---

## 구현 우선순위 권장

| 순위 | 태스크 | 트리거 조건 | 예상 소요 |
|------|--------|-------------|----------|
| 1 | T037 검증 | 배포 전 | 2시간 |
| 2 | T034 Redis 캐싱 | 성능 이슈 발생 시 | 4시간 |
| 3 | T035 Kafka 이벤트 | AI Agent 연동 시 | 8시간 |

---

## 관련 문서

- `specs/003-user-profile-preferences/spec.md` - 기능 명세
- `specs/003-user-profile-preferences/research.md` - 기술 결정 (이벤트 설계 포함)
- `specs/003-user-profile-preferences/tasks.md` - 전체 태스크 목록
- `specs/003-user-profile-preferences/quickstart.md` - 통합 테스트 시나리오
