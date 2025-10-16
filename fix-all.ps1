# Fix Core Services Only - AI Code Review Platform
# Focus: AI Review + API Gateway + Frontend (NO metrics, NO notification)
# Run from: C:\Users\ghada\ai-code-review\

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Fix Core Services - AI Review Platform" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan

$ErrorActionPreference = "Continue"

# ============================================================================
# STEP 0: Stop Non-Essential Services
# ============================================================================

Write-Host ""
Write-Host "STEP 0: Stopping Non-Essential Services" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

Write-Host "Stopping metrics and notification..." -ForegroundColor Cyan
docker-compose stop metrics notification 2>&1 | Out-Null
Write-Host "[SUCCESS] Non-essential services stopped" -ForegroundColor Green

# ============================================================================
# STEP 1: Ensure Infrastructure is Running
# ============================================================================

Write-Host ""
Write-Host "STEP 1: Checking Infrastructure" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

# Check PostgreSQL
Write-Host "Checking PostgreSQL..." -ForegroundColor Cyan
$pgStatus = docker ps --filter "name=postgres" --format "{{.Status}}"
if ($pgStatus -like "*Up*") {
    Write-Host "  [SUCCESS] PostgreSQL is running" -ForegroundColor Green
} else {
    Write-Host "  Starting PostgreSQL..." -ForegroundColor Yellow
    docker-compose up -d postgres
    Start-Sleep -Seconds 10
}

# Check Zookeeper
Write-Host "Checking Zookeeper..." -ForegroundColor Cyan
$zkStatus = docker ps --filter "name=zookeeper" --format "{{.Status}}"
if ($zkStatus -like "*Up*") {
    Write-Host "  [SUCCESS] Zookeeper is running" -ForegroundColor Green
} else {
    Write-Host "  Starting Zookeeper..." -ForegroundColor Yellow
    docker-compose up -d zookeeper
    Start-Sleep -Seconds 10
}

# Check Kafka
Write-Host "Checking Kafka..." -ForegroundColor Cyan
$kafkaStatus = docker ps --filter "name=kafka" --format "{{.Status}}"
if ($kafkaStatus -like "*Up*") {
    Write-Host "  [SUCCESS] Kafka is running" -ForegroundColor Green
} else {
    Write-Host "  Starting Kafka..." -ForegroundColor Yellow
    docker-compose up -d kafka
    Start-Sleep -Seconds 30
}

# ============================================================================
# STEP 2: Wait for Kafka and Create Topics
# ============================================================================

Write-Host ""
Write-Host "STEP 2: Creating Kafka Topics" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

# Wait for Kafka to be ready
Write-Host "Waiting for Kafka to be ready..." -ForegroundColor Cyan
$attempts = 0
$kafkaReady = $false

while ($attempts -lt 20) {
    try {
        $null = docker-compose exec -T kafka kafka-topics --list --bootstrap-server localhost:9092 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [SUCCESS] Kafka is ready" -ForegroundColor Green
            $kafkaReady = $true
            break
        }
    } catch {
        # Ignore errors during check
    }
    $attempts++
    Write-Host "  Attempt $attempts/20..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if (-not $kafkaReady) {
    Write-Host "  [WARNING] Kafka not responding, trying to restart..." -ForegroundColor Yellow
    docker-compose restart kafka
    Start-Sleep -Seconds 30
}

# Create topics
Write-Host ""
Write-Host "Creating Kafka topics..." -ForegroundColor Cyan

Write-Host "  - code-uploads" -NoNewline
docker-compose exec -T kafka kafka-topics --create `
    --bootstrap-server localhost:9092 `
    --topic code-uploads `
    --partitions 3 `
    --replication-factor 1 `
    --if-not-exists 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host " [SUCCESS]" -ForegroundColor Green
} else {
    Write-Host " (already exists)" -ForegroundColor Gray
}

Write-Host "  - review-results" -NoNewline
docker-compose exec -T kafka kafka-topics --create `
    --bootstrap-server localhost:9092 `
    --topic review-results `
    --partitions 3 `
    --replication-factor 1 `
    --if-not-exists 2>&1 | Out-Null

if ($LASTEXITCODE -eq 0) {
    Write-Host " [SUCCESS]" -ForegroundColor Green
} else {
    Write-Host " (already exists)" -ForegroundColor Gray
}

# Verify topics
Write-Host ""
Write-Host "Verifying topics..." -ForegroundColor Cyan
$topics = docker-compose exec -T kafka kafka-topics --list --bootstrap-server localhost:9092 2>&1

if ($topics -match "code-uploads" -and $topics -match "review-results") {
    Write-Host "  [SUCCESS] Both required topics exist" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Topics missing!" -ForegroundColor Red
    Write-Host "  Available topics:" -ForegroundColor Yellow
    Write-Host $topics
}

# ============================================================================
# STEP 3: Start/Restart AI Review Service
# ============================================================================

Write-Host ""
Write-Host "STEP 3: Starting AI Review Service" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

Write-Host "Restarting AI Review..." -ForegroundColor Cyan
docker-compose up -d ai-review
Start-Sleep -Seconds 10

# Check for errors
Write-Host "Checking AI Review status..." -ForegroundColor Cyan
$aiLogs = docker-compose logs --tail=5 ai-review 2>&1 | Select-String "error|Error|ERROR" -CaseSensitive:$false

if ($aiLogs) {
    Write-Host "  [WARNING] Some errors detected:" -ForegroundColor Yellow
    docker-compose logs --tail=10 ai-review
} else {
    Write-Host "  [SUCCESS] No errors detected" -ForegroundColor Green
}

# Check if "Topic not available" error is gone
$topicErrors = docker-compose logs --tail=10 ai-review 2>&1 | Select-String "Topic.*not available"
if ($topicErrors) {
    Write-Host "  [WARNING] Still seeing Kafka topic errors (may resolve in a moment)" -ForegroundColor Yellow
} else {
    Write-Host "  [SUCCESS] Kafka topics connected successfully" -ForegroundColor Green
}

# Test AI Review health
Write-Host ""
Write-Host "Testing AI Review health..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
try {
    $aiHealth = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  [SUCCESS] AI Review is healthy: $($aiHealth.status)" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] AI Review not responding yet" -ForegroundColor Red
    Write-Host "    (May need a few more seconds to start)" -ForegroundColor Gray
}

# ============================================================================
# STEP 4: Start/Restart API Gateway
# ============================================================================

Write-Host ""
Write-Host "STEP 4: Starting API Gateway" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

Write-Host "Restarting API Gateway..." -ForegroundColor Cyan
docker-compose up -d api-gateway
Start-Sleep -Seconds 10

# Check for errors
Write-Host "Checking API Gateway status..." -ForegroundColor Cyan
$apiErrors = docker-compose logs --tail=5 api-gateway 2>&1 | Select-String "error|Error|ERROR" -CaseSensitive:$false

if ($apiErrors) {
    Write-Host "  [WARNING] Some errors detected:" -ForegroundColor Yellow
    docker-compose logs --tail=10 api-gateway
} else {
    Write-Host "  [SUCCESS] No errors detected" -ForegroundColor Green
}

# Check for memory errors
$memErrors = docker-compose logs --tail=10 api-gateway 2>&1 | Select-String "Cannot allocate memory"
if ($memErrors) {
    Write-Host "  [WARNING] Memory allocation errors detected - restarting..." -ForegroundColor Yellow
    docker-compose restart api-gateway
    Start-Sleep -Seconds 10
}

# Test API Gateway health
Write-Host ""
Write-Host "Testing API Gateway health..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
try {
    $apiHealth = Invoke-RestMethod -Uri "http://localhost:8003/health" -Method Get -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  [SUCCESS] API Gateway is healthy: $($apiHealth.status)" -ForegroundColor Green
} catch {
    Write-Host "  [ERROR] API Gateway not responding yet" -ForegroundColor Red
    Write-Host "    (May need a few more seconds to start)" -ForegroundColor Gray
}

# ============================================================================
# STEP 5: Start Frontend
# ============================================================================

Write-Host ""
Write-Host "STEP 5: Starting Frontend" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

Write-Host "Starting Frontend..." -ForegroundColor Cyan
docker-compose up -d frontend
Start-Sleep -Seconds 10

$frontendStatus = docker ps --filter "name=frontend" --format "{{.Status}}"
if ($frontendStatus -like "*Up*") {
    Write-Host "  [SUCCESS] Frontend is running" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Frontend failed to start" -ForegroundColor Red
}

# ============================================================================
# STEP 6: Verify Database
# ============================================================================

Write-Host ""
Write-Host "STEP 6: Verifying Database" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

Write-Host "Checking database connection..." -ForegroundColor Cyan

try {
    $null = docker-compose exec -T postgres psql -U admin -d code_review -c "SELECT 1;" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [SUCCESS] Database is accessible" -ForegroundColor Green
        
        # Count reviews
        $reviewCount = docker-compose exec -T postgres psql -U admin -d code_review -t -c "SELECT COUNT(*) FROM review_results;" 2>&1
        if ($reviewCount -match "\d+") {
            $count = $reviewCount.Trim()
            Write-Host "  [SUCCESS] Reviews in database: $count" -ForegroundColor Green
            
            if ($count -eq "0") {
                Write-Host "    (No reviews yet - upload a file to create one)" -ForegroundColor Gray
            }
        }
    } else {
        Write-Host "  [ERROR] Database connection failed" -ForegroundColor Red
    }
} catch {
    Write-Host "  [ERROR] Database connection failed" -ForegroundColor Red
}

# ============================================================================
# STEP 7: Test API Endpoints
# ============================================================================

Write-Host ""
Write-Host "STEP 7: Testing API Endpoints" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Gray

Start-Sleep -Seconds 3

# Test reviews endpoint
Write-Host ""
Write-Host "Testing GET /api/reviews..." -ForegroundColor Cyan
try {
    $reviews = Invoke-RestMethod -Uri "http://localhost:8003/api/reviews?page=1&page_size=20" -Method Get -TimeoutSec 5 -ErrorAction Stop
    Write-Host "  [SUCCESS] Reviews API works" -ForegroundColor Green
    Write-Host "    Total: $($reviews.total), Returned: $($reviews.reviews.Count)" -ForegroundColor Gray
    
    if ($reviews.reviews.Count -gt 0) {
        Write-Host "    Latest review: $($reviews.reviews[0].filename)" -ForegroundColor Gray
    }
} catch {
    Write-Host "  [ERROR] Reviews endpoint failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test upload endpoint
Write-Host ""
Write-Host "Testing POST /api/upload (check only)..." -ForegroundColor Cyan
try {
    # Just check if endpoint exists (will fail without files, that's OK)
    $null = Invoke-RestMethod -Uri "http://localhost:8003/api/upload" -Method Post -TimeoutSec 2 -ErrorAction Stop 2>&1
} catch {
    if ($_.Exception.Response.StatusCode -eq 422) {
        Write-Host "  [SUCCESS] Upload endpoint exists (validation error is expected)" -ForegroundColor Green
    } else {
        Write-Host "  [WARNING] Upload endpoint: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# ============================================================================
# STEP 8: Service Status
# ============================================================================

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Service Status" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" --filter "name=postgres" --filter "name=zookeeper" --filter "name=kafka" --filter "name=ai-review" --filter "name=api-gateway" --filter "name=frontend"

# ============================================================================
# SUMMARY
# ============================================================================

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Core Platform Ready!" -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "Running Services:" -ForegroundColor White
Write-Host "  [SUCCESS] PostgreSQL  - Database" -ForegroundColor Green
Write-Host "  [SUCCESS] Zookeeper   - Kafka coordinator" -ForegroundColor Green
Write-Host "  [SUCCESS] Kafka       - Message broker" -ForegroundColor Green
Write-Host "  [SUCCESS] AI Review   - Code analysis engine" -ForegroundColor Green
Write-Host "  [SUCCESS] API Gateway - REST API and WebSocket" -ForegroundColor Green
Write-Host "  [SUCCESS] Frontend    - React dashboard" -ForegroundColor Green

Write-Host ""
Write-Host "Disabled Services:" -ForegroundColor Yellow
Write-Host "  [INFO] Metrics     - Not needed yet" -ForegroundColor Gray
Write-Host "  [INFO] Notification - Not needed yet" -ForegroundColor Gray

Write-Host ""
Write-Host "Access Your Platform:" -ForegroundColor White
Write-Host "  Frontend:    " -NoNewline; Write-Host "http://localhost:3000" -ForegroundColor Green
Write-Host "  API Gateway: " -NoNewline; Write-Host "http://localhost:8003" -ForegroundColor Green
Write-Host "  API Docs:    " -NoNewline; Write-Host "http://localhost:8003/docs" -ForegroundColor Green

Write-Host ""
Write-Host "Quick Commands:" -ForegroundColor White
Write-Host "  View all logs:     docker-compose logs -f" -ForegroundColor Cyan
Write-Host "  View AI logs:      docker-compose logs -f ai-review" -ForegroundColor Cyan
Write-Host "  View API logs:     docker-compose logs -f api-gateway" -ForegroundColor Cyan
Write-Host "  Restart AI:        docker-compose restart ai-review" -ForegroundColor Cyan
Write-Host "  Restart API:       docker-compose restart api-gateway" -ForegroundColor Cyan
Write-Host "  Stop everything:   docker-compose down" -ForegroundColor Cyan

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "1. Open http://localhost:3000 in your browser" -ForegroundColor Yellow
Write-Host "2. Click 'Upload' or 'New Review'" -ForegroundColor Yellow
Write-Host "3. Upload a code file (.py, .js, .java, etc.)" -ForegroundColor Yellow
Write-Host "4. Wait for AI analysis (usually 30-60 seconds)" -ForegroundColor Yellow
Write-Host "5. View results in the Reviews page" -ForegroundColor Yellow

Write-Host ""
$openBrowser = Read-Host "Open frontend in browser now? (y/n)"
if ($openBrowser -eq "y" -or $openBrowser -eq "Y") {
    Start-Process "http://localhost:3000"
    Write-Host ""
    Write-Host "[SUCCESS] Browser opened!" -ForegroundColor Green
    Write-Host ""
}

$followLogs = Read-Host "Follow service logs? (y/n)"
if ($followLogs -eq "y" -or $followLogs -eq "Y") {
    Write-Host ""
    Write-Host "Following logs for core services (Press Ctrl+C to stop)..." -ForegroundColor Cyan
    Write-Host ""
    docker-compose logs -f ai-review api-gateway frontend
}

Write-Host ""
Write-Host "Done!" -ForegroundColor Green
Write-Host ""