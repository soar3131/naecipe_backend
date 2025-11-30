#!/usr/bin/env bash
# ==============================================================================
# 내시피(Naecipe) 백엔드 개발 서버 시작 스크립트
# ==============================================================================

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 서비스 포트 매핑
declare -A SERVICE_PORTS=(
    ["recipe-service"]=8001
    ["user-service"]=8002
    ["cookbook-service"]=8003
    ["ai-agent-service"]=8004
    ["embedding-service"]=8005
    ["search-service"]=8006
    ["notification-service"]=8007
    ["analytics-service"]=8008
    ["ingestion-service"]=8009
)

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 서비스 이름을 Python 패키지 이름으로 변환
get_package_name() {
    local service_name=$1
    echo "${service_name//-/_}"
}

# 단일 서비스 시작
start_service() {
    local service_name=$1
    local port=${SERVICE_PORTS[$service_name]:-}

    if [ -z "$port" ]; then
        log_error "알 수 없는 서비스: $service_name"
        log_info "사용 가능한 서비스: ${!SERVICE_PORTS[*]}"
        exit 1
    fi

    local service_dir="services/$service_name"
    if [ ! -d "$service_dir" ]; then
        log_error "서비스 디렉토리가 존재하지 않습니다: $service_dir"
        exit 1
    fi

    local package_name=$(get_package_name "$service_name")

    log_info "서비스 시작: $service_name (포트: $port)"

    cd "$service_dir"
    uv run uvicorn "src.${package_name}.main:app" --reload --host 0.0.0.0 --port "$port"
}

# 전체 서비스 시작 (백그라운드)
start_all_services() {
    log_info "전체 서비스 시작 중..."

    for service_name in "${!SERVICE_PORTS[@]}"; do
        local service_dir="services/$service_name"
        if [ -d "$service_dir" ]; then
            local port=${SERVICE_PORTS[$service_name]}
            local package_name=$(get_package_name "$service_name")

            log_info "시작: $service_name (포트: $port)"

            (
                cd "$service_dir"
                uv run uvicorn "src.${package_name}.main:app" --reload --host 0.0.0.0 --port "$port"
            ) &
        fi
    done

    log_success "모든 서비스가 백그라운드에서 시작되었습니다."
    log_info "중지하려면 Ctrl+C를 누르세요."

    # 모든 백그라운드 프로세스 대기
    wait
}

# 도움말 표시
show_help() {
    echo "사용법: $0 [SERVICE_NAME]"
    echo ""
    echo "인자:"
    echo "  SERVICE_NAME    시작할 서비스 이름 (선택, 미지정 시 전체 시작)"
    echo ""
    echo "사용 가능한 서비스:"
    for service_name in "${!SERVICE_PORTS[@]}"; do
        echo "  $service_name (포트: ${SERVICE_PORTS[$service_name]})"
    done | sort
    echo ""
    echo "예시:"
    echo "  $0 recipe-service    # recipe-service만 시작"
    echo "  $0                   # 전체 서비스 시작"
}

# 메인 실행
main() {
    if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
        show_help
        exit 0
    fi

    if [ $# -eq 0 ]; then
        start_all_services
    else
        start_service "$1"
    fi
}

main "$@"
