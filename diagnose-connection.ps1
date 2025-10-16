# Diagnose and Fix ERR_CONNECTION_RESET
# Run from: C:\Users\ghada\ai-code-review\

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Diagnosing ERR_CONNECTION_RESET Error" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

# ============================================================================
# STEP 1: Check if API Gateway is actually running
# ============================================================================

Write-Host ""
Write-Host "STEP 1: Checking API Gateway Status" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

$apiStatus = docker ps --filter "name=api-gateway" --format "{{.Status}}"
Write-Host "API Gateway container status: $apiStatus" -ForegroundColor Cyan

if ($apiStatus -notlike "*Up*") {
    Write-Host "[ERROR] API Gateway is not running!" -ForegroundColor Red
    Write-Host "  Starting API Gateway..." -ForegroundColor Yellow
    docker-compose up -d api-gateway
    Start-Sleep -Seconds 15
} else {
    Write-Host "[SUCCESS] API Gateway container is running" -ForegroundColor Green
}

# ============================================================================
# STEP 2: Check recent API Gateway logs for crashes
# ============================================================================

Write-Host ""
Write-Host "STEP 2: Checking API Gateway Logs for Errors" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

$apiLogs = docker-compose logs --tail=30 api-gateway 2>&1

# Check for memory errors
if ($apiLogs -match "Cannot allocate memory") {
    Write-Host "[ERROR] FOUND: Memory allocation errors!" -ForegroundColor Red
    Write-Host "  This is causing the crashes" -ForegroundColor Yellow
    $memoryIssue = $true
} else {
    Write-Host "[SUCCESS] No memory errors found" -ForegroundColor Green
    $memoryIssue = $false
}

# Check for import errors
if ($apiLogs -match "ImportError|ModuleNotFoundError") {
    Write-Host "[ERROR] FOUND: Import/Module errors!" -ForegroundColor Red
} else {
    Write-Host "[SUCCESS] No import errors" -ForegroundColor Green
}

# Check for database errors
if ($apiLogs -match "database|Database|asyncpg") {
    Write-Host "[WARNING] Database-related messages found" -ForegroundColor Yellow
    Write-Host "  Checking database connection..." -ForegroundColor Cyan
    
    $null = docker-compose exec -T postgres pg_isready -U admin -d code_review 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [SUCCESS] Database is accessible" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] Database connection failed" -ForegroundColor Red
    }
}

# Show recent errors
Write-Host ""
Write-Host "Recent API Gateway logs (last 20 lines):" -ForegroundColor Cyan
docker-compose logs --tail=20 api-gateway

# ============================================================================
# STEP 3: Test API Gateway health endpoint
# ============================================================================

Write-Host ""
Write-Host "STEP 3: Testing API Gateway Health Endpoint" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

Start-Sleep -Seconds 3

try {
    Write-Host "Testing: http://localhost:8003/health" -ForegroundColor Cyan
    $health = Invoke-RestMethod -Uri "http://localhost:8003/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
    Write-Host "[SUCCESS] Health endpoint works!" -ForegroundColor Green
    Write-Host "  Status: $($health.status)" -ForegroundColor Gray
    $healthWorks = $true
} catch {
    Write-Host "[ERROR] Health endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
    $healthWorks = $false
}

# ============================================================================
# STEP 4: Test Reviews Endpoint Directly
# ============================================================================

Write-Host ""
Write-Host "STEP 4: Testing Reviews Endpoint" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

if ($healthWorks) {
    try {
        Write-Host "Testing: http://localhost:8003/api/reviews" -ForegroundColor Cyan
        $reviews = Invoke-RestMethod -Uri "http://localhost:8003/api/reviews?page=1&page_size=5" -Method Get -TimeoutSec 10 -ErrorAction Stop
        Write-Host "[SUCCESS] Reviews endpoint works!" -ForegroundColor Green
        Write-Host "  Total reviews: $($reviews.total)" -ForegroundColor Gray
        Write-Host "  Returned: $($reviews.reviews.Count)" -ForegroundColor Gray
        $reviewsWork = $true
    } catch {
        Write-Host "[ERROR] Reviews endpoint failed!" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        $reviewsWork = $false
        
        # Check if API Gateway crashed
        Write-Host ""
        Write-Host "  Checking if API Gateway crashed..." -ForegroundColor Yellow
        Start-Sleep -Seconds 2
        $newStatus = docker ps --filter "name=api-gateway" --format "{{.Status}}"
        if ($newStatus -notlike "*Up*") {
            Write-Host "  [ERROR] API Gateway CRASHED during request!" -ForegroundColor Red
        }
    }
}

# ============================================================================
# STEP 5: Apply Fixes Based on Diagnosis
# ============================================================================

Write-Host ""
Write-Host "STEP 5: Applying Fixes" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan

if ($memoryIssue) {
    Write-Host ""
    Write-Host "FIX 1: Memory Allocation Error" -ForegroundColor Yellow
    Write-Host "----------------------------------------------------------------" -ForegroundColor Gray
    
    Write-Host "Stopping API Gateway to clear memory..." -ForegroundColor Cyan
    docker-compose stop api-gateway
    Start-Sleep -Seconds 3
    
    Write-Host "Removing old container..." -ForegroundColor Cyan
    docker-compose rm -f api-gateway
    
    Write-Host "Restarting with fresh container..." -ForegroundColor Cyan
    docker-compose up -d api-gateway
    Start-Sleep -Seconds 15
    
    Write-Host "[SUCCESS] API Gateway restarted" -ForegroundColor Green
}

if ((-not $healthWorks) -or (-not $reviewsWork)) {
    Write-Host ""
    Write-Host "FIX 2: Service Not Responding" -ForegroundColor Yellow
    Write-Host "----------------------------------------------------------------" -ForegroundColor Gray
    
    Write-Host "Restarting API Gateway..." -ForegroundColor Cyan
    docker-compose restart api-gateway
    Start-Sleep -Seconds 15
    
    Write-Host "[SUCCESS] API Gateway restarted" -ForegroundColor Green
}

# ============================================================================
# STEP 6: Restart Frontend to Clear Cache
# ============================================================================

Write-Host ""
Write-Host "STEP 6: Restarting Frontend" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

Write-Host "Restarting frontend to clear any cached connections..." -ForegroundColor Cyan
docker-compose restart frontend
Start-Sleep -Seconds 10

Write-Host "[SUCCESS] Frontend restarted" -ForegroundColor Green

# ============================================================================
# STEP 7: Final Verification
# ============================================================================

Write-Host ""
Write-Host "STEP 7: Final Verification" -ForegroundColor Yellow
Write-Host "================================================================" -ForegroundColor Cyan

Start-Sleep -Seconds 5

# Test health again
Write-Host ""
Write-Host "Testing health endpoint..." -ForegroundColor Cyan
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8003/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
    Write-Host "[SUCCESS] Health: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Health check failed" -ForegroundColor Red
}

# Test reviews again
Write-Host ""
Write-Host "Testing reviews endpoint..." -ForegroundColor Cyan
try {
    $reviews = Invoke-RestMethod -Uri "http://localhost:8003/api/reviews?page=1&page_size=5" -Method Get -TimeoutSec 10 -ErrorAction Stop
    Write-Host "[SUCCESS] Reviews endpoint working" -ForegroundColor Green
    Write-Host "  Total: $($reviews.total), Pages: $($reviews.total_pages)" -ForegroundColor Gray
} catch {
    Write-Host "[ERROR] Reviews endpoint still failing" -ForegroundColor Red
    Write-Host ""
    Write-Host "Checking logs again..." -ForegroundColor Yellow
    docker-compose logs --tail=15 api-gateway
}

# Check WebSocket endpoint
Write-Host ""
Write-Host "Checking WebSocket endpoint..." -ForegroundColor Cyan
Write-Host "  WebSocket URL: ws://localhost:8003/api/reviews/ws/reviews" -ForegroundColor Gray
Write-Host "  (WebSocket can only be tested from browser)" -ForegroundColor Gray

# ============================================================================
# SUMMARY
# ============================================================================

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Diagnosis Summary" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

if ($memoryIssue) {
    Write-Host "[WARNING] Memory allocation errors detected and fixed" -ForegroundColor Yellow
}

Write-Host "Current Service Status:" -ForegroundColor White
docker-compose ps --format "table {{.Name}}\t{{.Status}}" --filter "name=api-gateway" --filter "name=frontend"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open http://localhost:3000 in your browser" -ForegroundColor Yellow
Write-Host "2. Open Browser DevTools (F12)" -ForegroundColor Yellow
Write-Host "3. Go to Network tab" -ForegroundColor Yellow
Write-Host "4. Try to view reviews" -ForegroundColor Yellow
Write-Host "5. Check if you still see ERR_CONNECTION_RESET" -ForegroundColor Yellow
Write-Host ""
Write-Host "If error persists:" -ForegroundColor White
Write-Host "  • Check logs: docker-compose logs -f api-gateway" -ForegroundColor Cyan
Write-Host "  • Check database: docker-compose logs postgres" -ForegroundColor Cyan
Write-Host "  • Full restart: docker-compose restart" -ForegroundColor Cyan
Write-Host ""

$openBrowser = Read-Host "Open http://localhost:3000 to test? (y/n)"
if ($openBrowser -eq "y" -or $openBrowser -eq "Y") {
    Start-Process "http://localhost:3000"
    Write-Host ""
    Write-Host "[SUCCESS] Browser opened! Check if reviews load now." -ForegroundColor Green
}

Write-Host ""
Write-Host "Monitor logs in real-time with:" -ForegroundColor White
Write-Host "  docker-compose logs -f api-gateway" -ForegroundColor Cyan
Write-Host ""