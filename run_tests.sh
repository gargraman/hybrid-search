#!/bin/bash

# Test runner script for hybrid-search project
# This script provides convenient commands for running different test suites

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Help message
show_help() {
    echo "Usage: ./run_tests.sh [OPTION]"
    echo ""
    echo "Run tests for the hybrid-search project"
    echo ""
    echo "Options:"
    echo "  all                Run all tests (default)"
    echo "  unit               Run only unit tests (fast, no services required)"
    echo "  integration        Run only integration tests (requires services)"
    echo "  whoosh             Run tests requiring Whoosh"
    echo "  qdrant             Run tests requiring Qdrant"
    echo "  postgres           Run tests requiring PostgreSQL"
    echo "  coverage           Run tests with coverage report"
    echo "  verbose            Run tests with verbose output"
    echo "  debug              Run tests with debug logging"
    echo "  check-services     Check if required services are running"
    echo "  setup-data         Setup test data (requires services)"
    echo "  help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./run_tests.sh                  # Run all tests"
    echo "  ./run_tests.sh unit             # Run unit tests only"
    echo "  ./run_tests.sh coverage         # Run with coverage report"
    echo "  ./run_tests.sh check-services   # Check service availability"
}

# Check if pytest is installed
check_pytest() {
    if ! command -v pytest &> /dev/null; then
        echo -e "${RED}Error: pytest not found${NC}"
        echo "Install test dependencies with: pip install -r requirements.txt"
        exit 1
    fi
}

# Check service availability
check_services() {
    echo -e "${YELLOW}Checking service availability...${NC}"

    # Check Qdrant
    if curl -s http://localhost:6333/health &> /dev/null; then
        echo -e "${GREEN}✓ Qdrant is running${NC}"
    else
        echo -e "${RED}✗ Qdrant is not running${NC}"
        echo "  Start with: docker-compose up -d"
    fi

    # Check PostgreSQL
    if pg_isready -h localhost -p 5432 &> /dev/null 2>&1 || docker exec hybrid-search_postgres_1 pg_isready &> /dev/null 2>&1; then
        echo -e "${GREEN}✓ PostgreSQL is running${NC}"
    else
        echo -e "${RED}✗ PostgreSQL is not running${NC}"
        echo "  Start with: docker-compose up -d"
    fi

    # Check Whoosh index
    if [ -f "./whoosh_index/_MAIN_1.toc" ]; then
        echo -e "${GREEN}✓ Whoosh index exists${NC}"
    else
        echo -e "${RED}✗ Whoosh index not found${NC}"
        echo "  Create with: python src/ingest.py"
    fi
}

# Setup test data
setup_data() {
    echo -e "${YELLOW}Setting up test data...${NC}"

    # Generate seed data
    if [ ! -d "./input/seed" ] || [ -z "$(ls -A ./input/seed)" ]; then
        echo "Generating seed data..."
        python scripts/generate_seed_data.py
    else
        echo -e "${GREEN}✓ Seed data already exists${NC}"
    fi

    # Ingest to Whoosh
    echo "Ingesting to Whoosh..."
    python src/ingest.py

    # Ingest to Qdrant + PostgreSQL
    echo "Ingesting to Qdrant + PostgreSQL..."
    python src/ingest_qdrant_postgres.py

    echo -e "${GREEN}✓ Test data setup complete${NC}"
}

# Main script
COMMAND=${1:-all}

case $COMMAND in
    help)
        show_help
        exit 0
        ;;

    check-services)
        check_services
        exit 0
        ;;

    setup-data)
        check_services
        setup_data
        exit 0
        ;;

    all)
        check_pytest
        echo -e "${YELLOW}Running all tests...${NC}"
        pytest
        ;;

    unit)
        check_pytest
        echo -e "${YELLOW}Running unit tests...${NC}"
        pytest -m unit
        ;;

    integration)
        check_pytest
        echo -e "${YELLOW}Running integration tests...${NC}"
        check_services
        pytest -m integration
        ;;

    whoosh)
        check_pytest
        echo -e "${YELLOW}Running Whoosh tests...${NC}"
        pytest -m whoosh
        ;;

    qdrant)
        check_pytest
        echo -e "${YELLOW}Running Qdrant tests...${NC}"
        pytest -m qdrant
        ;;

    postgres)
        check_pytest
        echo -e "${YELLOW}Running PostgreSQL tests...${NC}"
        pytest -m postgres
        ;;

    coverage)
        check_pytest
        echo -e "${YELLOW}Running tests with coverage...${NC}"
        pytest --cov=src --cov-report=html --cov-report=term-missing
        echo -e "${GREEN}Coverage report generated: htmlcov/index.html${NC}"
        ;;

    verbose)
        check_pytest
        echo -e "${YELLOW}Running tests with verbose output...${NC}"
        pytest -vv
        ;;

    debug)
        check_pytest
        echo -e "${YELLOW}Running tests with debug logging...${NC}"
        pytest -vv -s --log-cli-level=DEBUG
        ;;

    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

# Check exit status
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Tests completed successfully${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    exit 1
fi
