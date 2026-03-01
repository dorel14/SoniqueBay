#!/bin/bash
# Test script for Supabase services
# Usage: ./test-services.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_DIR"

echo "=== Testing Supabase Services ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Test 1: Check Docker is running
echo "1. Checking Docker..."
if docker info > /dev/null 2>&1; then
    print_status "Docker is running"
else
    print_error "Docker is not running"
    exit 1
fi

# Test 2: Check docker-compose is available
echo ""
echo "2. Checking docker-compose..."
if docker-compose --version > /dev/null 2>&1; then
    print_status "docker-compose is available"
else
    print_error "docker-compose is not available"
    exit 1
fi

# Test 3: Validate docker-compose.yml
echo ""
echo "3. Validating docker-compose.yml..."
if docker-compose config > /dev/null 2>&1; then
    print_status "docker-compose.yml is valid"
else
    print_error "docker-compose.yml is invalid"
    exit 1
fi

# Test 4: Check if .env file exists
echo ""
echo "4. Checking environment file..."
if [ -f ".env" ]; then
    print_status ".env file exists"
else
    print_warning ".env file not found, using .env.supabase.example"
    if [ -f ".env.supabase.example" ]; then
        cp .env.supabase.example .env
        print_status "Created .env from .env.supabase.example"
    else
        print_error "No environment file found"
        exit 1
    fi
fi

# Test 5: Pull Supabase images
echo ""
echo "5. Pulling Supabase images..."
echo "   - supabase/postgres:15.1.0.117"
if docker pull supabase/postgres:15.1.0.117 > /dev/null 2>&1; then
    print_status "PostgreSQL image pulled"
else
    print_error "Failed to pull PostgreSQL image"
fi

echo "   - supabase/gotrue:v2.145.0"
if docker pull supabase/gotrue:v2.145.0 > /dev/null 2>&1; then
    print_status "Auth (GoTrue) image pulled"
else
    print_error "Failed to pull Auth image"
fi

echo "   - supabase/realtime:v2.25.66"
if docker pull supabase/realtime:v2.25.66 > /dev/null 2>&1; then
    print_status "Realtime image pulled"
else
    print_error "Failed to pull Realtime image"
fi

echo "   - supabase/postgres-meta:v0.80.0"
if docker pull supabase/postgres-meta:v0.80.0 > /dev/null 2>&1; then
    print_status "Meta image pulled"
else
    print_error "Failed to pull Meta image"
fi

# Test 6: Start Supabase database only (test core service)
echo ""
echo "6. Starting Supabase database (test mode)..."
docker-compose up -d supabase-db

echo "   Waiting for database to be healthy..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker-compose ps supabase-db | grep -q "healthy"; then
        print_status "Supabase database is healthy"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "   Attempt $RETRY_COUNT/$MAX_RETRIES..."
    sleep 5
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "Database failed to become healthy"
    echo ""
    echo "=== Database Logs ==="
    docker-compose logs --tail=50 supabase-db
    docker-compose stop supabase-db
    exit 1
fi

# Test 7: Test database connection
echo ""
echo "7. Testing database connection..."
if docker-compose exec -T supabase-db pg_isready -U supabase > /dev/null 2>&1; then
    print_status "Database connection successful"
else
    print_error "Database connection failed"
    docker-compose stop supabase-db
    exit 1
fi

# Test 8: Check extensions
echo ""
echo "8. Checking PostgreSQL extensions..."
EXTENSIONS=$(docker-compose exec -T supabase-db psql -U supabase -d postgres -t -c "SELECT extname FROM pg_extension WHERE extname IN ('uuid-ossp', 'pg_trgm', 'pgcrypto', 'vector');" 2>/dev/null || echo "")

if echo "$EXTENSIONS" | grep -q "uuid-ossp"; then
    print_status "uuid-ossp extension installed"
else
    print_warning "uuid-ossp extension not found"
fi

if echo "$EXTENSIONS" | grep -q "pg_trgm"; then
    print_status "pg_trgm extension installed"
else
    print_warning "pg_trgm extension not found"
fi

if echo "$EXTENSIONS" | grep -q "pgcrypto"; then
    print_status "pgcrypto extension installed"
else
    print_warning "pgcrypto extension not found"
fi

if echo "$EXTENSIONS" | grep -q "vector"; then
    print_status "vector extension installed"
else
    print_warning "vector extension not found"
fi

# Cleanup
echo ""
echo "9. Stopping test services..."
docker-compose stop supabase-db > /dev/null 2>&1
print_status "Test services stopped"

echo ""
echo "=== Test Summary ==="
print_status "Core Supabase infrastructure is ready"
echo ""
echo "Next steps:"
echo "  1. Run: ./supabase/scripts/start.sh"
echo "  2. Test clients: python -c \"from backend.api.utils.supabase_client import get_supabase_client; print('OK')\""
echo ""
