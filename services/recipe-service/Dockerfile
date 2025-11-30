# ==============================================================================
# Recipe Service Dockerfile
# ==============================================================================
# 멀티스테이지 빌드로 이미지 크기 최소화
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: 빌더
# ------------------------------------------------------------------------------
FROM python:3.11-slim as builder

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# pip 업그레이드
RUN pip install --no-cache-dir --upgrade pip

# 의존성 설치 (캐시 활용)
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

# ------------------------------------------------------------------------------
# Stage 2: 런타임
# ------------------------------------------------------------------------------
FROM python:3.11-slim as runtime

WORKDIR /app

# 보안: 비-root 사용자 생성
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# 빌더에서 설치된 패키지 복사
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 소스 코드 복사
COPY src/ ./src/

# 소유권 변경
RUN chown -R appuser:appgroup /app

# 비-root 사용자로 전환
USER appuser

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

# 포트 노출
EXPOSE 8001

# 헬스체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8001/health').raise_for_status()" || exit 1

# 서비스 시작
CMD ["uvicorn", "recipe_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
