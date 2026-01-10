#!/bin/bash
# run all e2e tests with server management

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# parse arguments
HEADLESS=true
while [[ $# -gt 0 ]]; do
    case $1 in
        --ui)
            HEADLESS=false
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--ui]"
            echo "  --ui    Run tests with visible browser (chromium UI)"
            exit 1
            ;;
    esac
done

# set headless mode
if [ "$HEADLESS" = "false" ]; then
    export E2E_HEADLESS=false
    echo "🖥️  Running tests with visible browser UI"
else
    export E2E_HEADLESS=true
    echo "🤖 Running tests in headless mode"
fi

echo "🧪 Running DataGenFlow E2E Tests"
echo "================================"
echo ""

# check if playwright is installed
if ! uv run python -c "import playwright" 2>/dev/null; then
    echo "❌ Playwright not installed"
    echo "Install with: uv pip install playwright && uv run playwright install chromium"
    exit 1
fi

echo "✓ Playwright installed"
echo ""

# define server commands
BACKEND_CMD="uv run uvicorn app:app --host 0.0.0.0 --port 8000"
FRONTEND_CMD="cd frontend && yarn dev"

# run each test suite
echo "📋 Test Suite 1: Pipelines"
echo "-------------------------"
uv run python "$PROJECT_ROOT/scripts/with_server.py" \
    --server "$BACKEND_CMD" --port 8000 \
    --server "$FRONTEND_CMD" --port 5173 \
    -- uv run python "$SCRIPT_DIR/test_pipelines_e2e.py"
echo ""

echo "📋 Test Suite 2: Generator"
echo "-------------------------"
uv run python "$PROJECT_ROOT/scripts/with_server.py" \
    --server "$BACKEND_CMD" --port 8000 \
    --server "$FRONTEND_CMD" --port 5173 \
    -- uv run python "$SCRIPT_DIR/test_generator_e2e.py"
echo ""

echo "📋 Test Suite 3: Review"
echo "-------------------------"
uv run python "$PROJECT_ROOT/scripts/with_server.py" \
    --server "$BACKEND_CMD" --port 8000 \
    --server "$FRONTEND_CMD" --port 5173 \
    -- uv run python "$SCRIPT_DIR/test_review_e2e.py"
echo ""

echo "✅ All E2E tests completed!"
echo ""
echo "📸 Screenshots saved to /tmp/"
echo "   - /tmp/pipelines_page.png"
echo "   - /tmp/generator_page.png"
echo "   - /tmp/review_page.png"
echo "   - ... and more"
