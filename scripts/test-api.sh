#!/bin/bash
# Скрипт для тестирования подключения к Task Manager API

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Параметры
API_URL="${1:-http://localhost:8000}"
API_KEY="${TASK_MANAGER_API_KEY:-your-secret-key-change-me}"

echo "========================================="
echo "🧪 Тестирование Task Manager API"
echo "========================================="
echo ""
echo "🌐 URL: $API_URL"
echo "🔑 API Key: ${API_KEY:0:20}..."
echo ""

# Функция для тестирования endpoint
test_endpoint() {
    local name="$1"
    local url="$2"
    local method="${3:-GET}"
    local auth="${4:-true}"

    echo -n "Testing $name... "

    if [ "$auth" = "true" ]; then
        response=$(curl -s -w "\n%{http_code}" -X "$method" -H "X-API-Key: $API_KEY" "$url" 2>&1)
    else
        response=$(curl -s -w "\n%{http_code}" "$url" 2>&1)
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ]; then
        echo -e "${GREEN}✓ OK${NC} (HTTP $http_code)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        echo "  Response: $body"
        return 1
    fi
}

# Тесты
echo "📋 Базовые тесты:"
echo "---"

test_endpoint "Health check (no auth)" "$API_URL/" "GET" "false"
test_endpoint "Get tasks" "$API_URL/api/tasks" "GET" "true"
test_endpoint "Get stats" "$API_URL/api/stats" "GET" "true"
test_endpoint "Get settings" "$API_URL/api/settings" "GET" "true"
test_endpoint "Get current points" "$API_URL/api/points/current" "GET" "true"

echo ""
echo "🔒 Тест безопасности:"
echo "---"

echo -n "Testing auth protection... "
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/tasks" 2>&1)
http_code=$(echo "$response" | tail -n1)

if [ "$http_code" = "401" ]; then
    echo -e "${GREEN}✓ OK${NC} (Unauthorized without API key)"
else
    echo -e "${RED}✗ FAIL${NC} (Expected 401, got $http_code)"
fi

echo ""
echo "📊 Детальная информация:"
echo "---"

# Получить stats с деталями
stats=$(curl -s -H "X-API-Key: $API_KEY" "$API_URL/api/stats")
if [ $? -eq 0 ]; then
    echo "Tasks completed today: $(echo $stats | grep -o '"tasks_completed":[0-9]*' | cut -d':' -f2)"
    echo "Habits completed today: $(echo $stats | grep -o '"habits_completed":[0-9]*' | cut -d':' -f2)"
    echo "Current points: $(echo $stats | grep -o '"points":[0-9]*' | cut -d':' -f2)"
fi

echo ""
echo "========================================="
echo "✅ Тестирование завершено"
echo "========================================="
