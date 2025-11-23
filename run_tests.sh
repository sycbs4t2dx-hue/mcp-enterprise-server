#!/bin/bash
# 统一的测试运行脚本

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试目录整理
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  MCP 统一测试运行器${NC}"
echo -e "${BLUE}========================================${NC}"
echo

# 函数：移动测试文件到统一位置
organize_tests() {
    echo -e "${YELLOW}📁 整理测试文件...${NC}"

    # 创建测试目录结构
    mkdir -p tests/unit
    mkdir -p tests/integration
    mkdir -p tests/performance
    mkdir -p tests/fixtures

    # 移动根目录的测试文件到tests目录
    if ls test_*.py 1> /dev/null 2>&1; then
        echo "  移动根目录测试文件..."
        for file in test_*.py; do
            if [ -f "$file" ]; then
                mv "$file" tests/integration/ 2>/dev/null && echo "    ✓ $file → tests/integration/"
            fi
        done
    fi

    echo -e "${GREEN}✅ 测试文件整理完成${NC}"
}

# 函数：运行单元测试
run_unit_tests() {
    echo -e "\n${YELLOW}🧪 运行单元测试...${NC}"
    pytest tests/unit -m "unit" --tb=short -q
    return $?
}

# 函数：运行集成测试
run_integration_tests() {
    echo -e "\n${YELLOW}🔗 运行集成测试...${NC}"
    pytest tests/integration -m "integration" --tb=short -q
    return $?
}

# 函数：运行性能测试
run_performance_tests() {
    echo -e "\n${YELLOW}⚡ 运行性能测试...${NC}"
    pytest tests/performance -m "performance" --tb=short -q
    return $?
}

# 函数：运行所有测试
run_all_tests() {
    echo -e "\n${YELLOW}🚀 运行所有测试...${NC}"
    pytest tests/ --tb=short
    return $?
}

# 函数：运行测试覆盖率
run_coverage() {
    echo -e "\n${YELLOW}📊 生成测试覆盖率报告...${NC}"
    pytest tests/ --cov=src/mcp_core --cov-report=html --cov-report=term
    echo -e "${GREEN}✅ 覆盖率报告已生成: htmlcov/index.html${NC}"
}

# 函数：运行特定标记的测试
run_marked_tests() {
    local mark=$1
    echo -e "\n${YELLOW}🏷️  运行标记为 '$mark' 的测试...${NC}"
    pytest -m "$mark" --tb=short
    return $?
}

# 函数：清理测试缓存
clean_cache() {
    echo -e "\n${YELLOW}🗑️  清理测试缓存...${NC}"
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null
    find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null
    find . -type f -name "*.pyc" -delete 2>/dev/null
    find . -type f -name ".coverage" -delete 2>/dev/null
    echo -e "${GREEN}✅ 缓存清理完成${NC}"
}

# 函数：检查测试环境
check_environment() {
    echo -e "${YELLOW}🔍 检查测试环境...${NC}"

    # 检查Python
    if command -v python3 &> /dev/null; then
        echo -e "  ✓ Python: $(python3 --version)"
    else
        echo -e "  ${RED}✗ Python 未安装${NC}"
        exit 1
    fi

    # 检查pytest
    if python3 -m pytest --version &> /dev/null; then
        echo -e "  ✓ pytest: $(python3 -m pytest --version 2>&1 | head -n1)"
    else
        echo -e "  ${RED}✗ pytest 未安装${NC}"
        echo "  请运行: pip install pytest pytest-cov pytest-asyncio pytest-timeout"
        exit 1
    fi

    # 检查服务
    if docker ps | grep -q redis; then
        echo -e "  ✓ Redis: 运行中"
    else
        echo -e "  ${YELLOW}⚠ Redis: 未运行（某些测试可能失败）${NC}"
    fi

    if docker ps | grep -q milvus; then
        echo -e "  ✓ Milvus: 运行中"
    else
        echo -e "  ${YELLOW}⚠ Milvus: 未运行（某些测试可能失败）${NC}"
    fi

    if docker ps | grep -q mysql; then
        echo -e "  ✓ MySQL: 运行中"
    else
        echo -e "  ${YELLOW}⚠ MySQL: 未运行（某些测试可能失败）${NC}"
    fi
}

# 函数：显示帮助
show_help() {
    echo "使用方法: $0 [命令] [选项]"
    echo
    echo "命令:"
    echo "  organize    整理测试文件到统一位置"
    echo "  unit        运行单元测试"
    echo "  integration 运行集成测试"
    echo "  performance 运行性能测试"
    echo "  all         运行所有测试（默认）"
    echo "  coverage    生成测试覆盖率报告"
    echo "  marked      运行特定标记的测试（需要参数）"
    echo "  clean       清理测试缓存"
    echo "  check       检查测试环境"
    echo "  help        显示此帮助信息"
    echo
    echo "示例:"
    echo "  $0                  # 运行所有测试"
    echo "  $0 unit             # 只运行单元测试"
    echo "  $0 marked slow      # 运行标记为'slow'的测试"
    echo "  $0 coverage         # 生成覆盖率报告"
}

# 主程序
main() {
    # 如果没有参数，运行所有测试
    if [ $# -eq 0 ]; then
        check_environment
        run_all_tests
        exit $?
    fi

    # 处理命令
    case "$1" in
        organize)
            organize_tests
            ;;
        unit)
            check_environment
            run_unit_tests
            ;;
        integration)
            check_environment
            run_integration_tests
            ;;
        performance)
            check_environment
            run_performance_tests
            ;;
        all)
            check_environment
            run_all_tests
            ;;
        coverage)
            check_environment
            run_coverage
            ;;
        marked)
            if [ -z "$2" ]; then
                echo -e "${RED}错误: 'marked' 命令需要指定标记${NC}"
                echo "示例: $0 marked slow"
                exit 1
            fi
            check_environment
            run_marked_tests "$2"
            ;;
        clean)
            clean_cache
            ;;
        check)
            check_environment
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            echo -e "${RED}未知命令: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 运行主程序
main "$@"