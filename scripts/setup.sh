#!/usr/bin/env bash
# ==============================================================================
# 내시피(Naecipe) 백엔드 개발 환경 설정 스크립트
# ==============================================================================

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Python 버전 확인
check_python_version() {
    log_info "Python 버전 확인 중..."

    if ! command -v python3 &> /dev/null; then
        log_error "Python3가 설치되어 있지 않습니다."
        exit 1
    fi

    PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    REQUIRED_VERSION="3.11"

    if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
        log_error "Python $REQUIRED_VERSION 이상이 필요합니다. 현재 버전: $PYTHON_VERSION"
        exit 1
    fi

    log_success "Python $PYTHON_VERSION 확인 완료"
}

# uv 설치 확인
check_uv() {
    log_info "uv 설치 확인 중..."

    if ! command -v uv &> /dev/null; then
        log_warning "uv가 설치되어 있지 않습니다. 설치를 시작합니다..."
        curl -LsSf https://astral.sh/uv/install.sh | sh

        # PATH에 uv 추가 (현재 세션)
        export PATH="$HOME/.cargo/bin:$PATH"

        if ! command -v uv &> /dev/null; then
            log_error "uv 설치에 실패했습니다. 수동으로 설치해주세요: https://docs.astral.sh/uv/"
            exit 1
        fi
    fi

    UV_VERSION=$(uv --version)
    log_success "uv 확인 완료: $UV_VERSION"
}

# Docker 설치 확인
check_docker() {
    log_info "Docker 설치 확인 중..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker가 설치되어 있지 않습니다."
        log_error "Docker Desktop을 설치해주세요: https://www.docker.com/products/docker-desktop"
        exit 1
    fi

    if ! docker info &> /dev/null; then
        log_error "Docker 데몬이 실행되고 있지 않습니다. Docker Desktop을 시작해주세요."
        exit 1
    fi

    DOCKER_VERSION=$(docker --version)
    log_success "Docker 확인 완료: $DOCKER_VERSION"
}

# 가상환경 생성 및 의존성 설치
setup_venv() {
    log_info "Python 가상환경 설정 중..."

    # 루트 프로젝트 설정
    if [ ! -d ".venv" ]; then
        uv venv
        log_success "가상환경 생성 완료"
    else
        log_info "기존 가상환경 사용"
    fi

    # 의존성 동기화
    log_info "의존성 설치 중..."
    uv sync

    log_success "의존성 설치 완료"
}

# 환경 변수 파일 설정
setup_env() {
    log_info "환경 변수 파일 확인 중..."

    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            log_success ".env 파일 생성 완료 (템플릿에서 복사)"
            log_warning "필요에 따라 .env 파일을 수정해주세요."
        else
            log_warning ".env.example 파일이 없습니다."
        fi
    else
        log_info "기존 .env 파일 사용"
    fi
}

# 메인 실행
main() {
    echo ""
    echo "=================================================="
    echo "  내시피(Naecipe) 백엔드 개발 환경 설정"
    echo "=================================================="
    echo ""

    check_python_version
    check_uv
    check_docker
    setup_venv
    setup_env

    echo ""
    echo "=================================================="
    log_success "개발 환경 설정 완료!"
    echo "=================================================="
    echo ""
    echo "다음 단계:"
    echo "  1. 로컬 인프라 시작: make infra-up"
    echo "  2. 개발 서버 시작: make dev-service SERVICE=recipe-service"
    echo "  3. 헬스체크 확인: curl http://localhost:8001/health"
    echo ""
}

main "$@"
