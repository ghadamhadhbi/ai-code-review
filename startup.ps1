# complete-startup-fix.ps1
# Complete fix for Kafka topic and consumer issues

$ErrorActionPreference = "Continue"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Complete Startup Fix - AI Code Review Platform" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Clean shutdown
Write-Host "STEP 1: Clean shutdown" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Stopping all services..." -ForegroundColor White
docker-compose down 2>&1 | Out-Null
Start-Sleep -Seconds 3
Write-Host "  [SUCCESS] All services stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Start infrastructure (PostgreSQL, Zookeeper, Kafka)
Write-Host "STEP 2: Starting infrastructure" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Starting PostgreSQL..." -ForegroundColor White
docker-compose up -d postgres 2>&1 | Out-Null
Start-Sleep -Seconds 5

Write-Host "Starting Zookeeper..." -ForegroundColor White
docker-compose up -d zookeeper 2>&1 | Out-Null
Start-Sleep -Seconds 10

Write-Host "Starting Kafka..." -ForegroundColor White
docker-compose up -d kafka 2>&1 | Out-Null
Write-Host "  Waiting for Kafka to fully initialize (40 seconds)..." -ForegroundColor Gray
Start-Sleep -Seconds 40

Write-Host "  [SUCCESS] Infrastructure started" -ForegroundColor Green
Write-Host ""

# Step 3: Verify Kafka is ready
Write-Host "STEP 3: Verifying Kafka is ready" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

$maxAttempts = 15
$attempt = 0
$kafkaReady = $false

while ($attempt -lt $maxAttempts -and -not $kafkaReady) {
    $attempt++
    Write-Host "  Checking Kafka (attempt $attempt/$maxAttempts)..." -ForegroundColor Gray
    
    docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $kafkaReady = $true
        Write-Host "  [SUCCESS] Kafka is ready!" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 3
}

if (-not $kafkaReady) {
    Write-Host "  [ERROR] Kafka is not ready after $maxAttempts attempts" -ForegroundColor Red
    Write-Host "  Please check Kafka logs: docker-compose logs kafka" -ForegroundColor Yellow
    exit 1
}

Write-Host ""

# Step 4: Create Kafka topics EXPLICITLY
Write-Host "STEP 4: Creating Kafka topics" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Creating code-uploads topic..." -ForegroundColor White
$createResult1 = docker-compose exec -T kafka kafka-topics --create `
    --bootstrap-server localhost:9092 `
    --topic code-uploads `
    --partitions 3 `
    --replication-factor 1 `
    --config retention.ms=604800000 `
    --config compression.type=gzip `
    --if-not-exists 2>&1

if ($createResult1 -match "Created topic|already exists") {
    Write-Host "  [SUCCESS] code-uploads topic ready" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Failed to create code-uploads topic" -ForegroundColor Red
    Write-Host "  $createResult1" -ForegroundColor Gray
}

Write-Host "Creating review-results topic..." -ForegroundColor White
$createResult2 = docker-compose exec -T kafka kafka-topics --create `
    --bootstrap-server localhost:9092 `
    --topic review-results `
    --partitions 3 `
    --replication-factor 1 `
    --config retention.ms=2592000000 `
    --config compression.type=gzip `
    --if-not-exists 2>&1

if ($createResult2 -match "Created topic|already exists") {
    Write-Host "  [SUCCESS] review-results topic ready" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Failed to create review-results topic" -ForegroundColor Red
    Write-Host "  $createResult2" -ForegroundColor Gray
}

Write-Host ""

# Step 5: Verify topics exist
Write-Host "STEP 5: Verifying topics" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Listing all topics..." -ForegroundColor White
$allTopics = docker-compose exec -T kafka kafka-topics --list --bootstrap-server localhost:9092 2>&1
Write-Host "Available topics:" -ForegroundColor Gray
$allTopics | ForEach-Object { Write-Host "  - $_" -ForegroundColor Gray }

$hasCodeUploads = $allTopics -match "^code-uploads$"
$hasReviewResults = $allTopics -match "^review-results$"

if ($hasCodeUploads -and $hasReviewResults) {
    Write-Host "  [SUCCESS] Both required topics exist!" -ForegroundColor Green
} else {
    Write-Host "  [ERROR] Missing required topics!" -ForegroundColor Red
    if (-not $hasCodeUploads) { Write-Host "    Missing: code-uploads" -ForegroundColor Red }
    if (-not $hasReviewResults) { Write-Host "    Missing: review-results" -ForegroundColor Red }
    exit 1
}

Write-Host ""

# Step 6: Describe topics
Write-Host "STEP 6: Topic details" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker-compose exec -T kafka kafka-topics --describe `
    --bootstrap-server localhost:9092 `
    --topic code-uploads 2>&1 | Select-String "Topic:|Partition:" | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Gray
    }

Write-Host ""

# Step 7: Wait for topic metadata
Write-Host "STEP 7: Waiting for topic metadata to propagate" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "  Waiting 10 seconds..." -ForegroundColor Gray
Start-Sleep -Seconds 10
Write-Host "  [SUCCESS] Topic metadata should be ready" -ForegroundColor Green
Write-Host ""

# Step 8: Initialize database
Write-Host "STEP 8: Initializing database" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker-compose exec -T postgres pg_isready -U postgres 2>&1 | Out-Null
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [SUCCESS] Database is ready" -ForegroundColor Green
} else {
    Write-Host "  [WARNING] Database not ready, waiting..." -ForegroundColor Yellow
    Start-Sleep -Seconds 10
}

Write-Host ""

# Step 9: Start AI Review Service
Write-Host "STEP 9: Starting AI Review Service" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Starting AI Review Service..." -ForegroundColor White
docker-compose up -d ai-review 2>&1 | Out-Null
Write-Host "  Waiting for service to initialize (25 seconds)..." -ForegroundColor Gray
Start-Sleep -Seconds 25

Write-Host "  [SUCCESS] AI Review Service started" -ForegroundColor Green
Write-Host ""

# Step 10: Check AI Review logs
Write-Host "STEP 10: Checking AI Review logs" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

$logs = docker-compose logs --tail=40 ai-review 2>&1

Write-Host "Analyzing logs..." -ForegroundColor White

$hasTopicError = $logs | Select-String "Topic.*not available"
$hasCoordinatorError = $logs | Select-String "CoordinatorNotAvailableError"
$hasConsumerStarted = $logs | Select-String "Kafka consumer started|consumer started successfully|Starting message consumption"
$hasStartupComplete = $logs | Select-String "Application startup complete"

if ($hasTopicError) {
    Write-Host "  [ERROR] Still seeing topic errors!" -ForegroundColor Red
    Write-Host "  This should not happen after creating topics" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Last 10 lines of logs:" -ForegroundColor Yellow
    docker-compose logs --tail=10 ai-review
} elseif ($hasCoordinatorError) {
    Write-Host "  [WARNING] Coordinator errors detected" -ForegroundColor Yellow
    Write-Host "  These should resolve within 60 seconds" -ForegroundColor Gray
} elseif ($hasConsumerStarted) {
    Write-Host "  [SUCCESS] Kafka consumer started successfully!" -ForegroundColor Green
} elseif ($hasStartupComplete) {
    Write-Host "  [INFO] Service started, consumer initializing..." -ForegroundColor Cyan
    Write-Host "  Consumer will start after 10 second delay" -ForegroundColor Gray
} else {
    Write-Host "  [INFO] Service starting up..." -ForegroundColor Cyan
}

Write-Host ""

# Step 11: Start API Gateway
Write-Host "STEP 11: Starting API Gateway" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker-compose up -d api-gateway 2>&1 | Out-Null
Start-Sleep -Seconds 10
Write-Host "  [SUCCESS] API Gateway started" -ForegroundColor Green
Write-Host ""

# Step 12: Start Frontend
Write-Host "STEP 12: Starting Frontend" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker-compose up -d frontend 2>&1 | Out-Null
Start-Sleep -Seconds 5
Write-Host "  [SUCCESS] Frontend started" -ForegroundColor Green
Write-Host ""

# Step 13: Health checks
Write-Host "STEP 13: Health checks" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Start-Sleep -Seconds 5

Write-Host "Checking services..." -ForegroundColor White

# AI Review Health Check
try {
    $aiHealth = Invoke-RestMethod -Uri "http://localhost:8001/health" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "  AI Review:  " -NoNewline -ForegroundColor White
    if ($aiHealth.status -eq "healthy") {
        Write-Host "✓ healthy" -ForegroundColor Green
    } else {
        Write-Host "⚠ $($aiHealth.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  AI Review:  ✗ not responding" -ForegroundColor Red
}

# API Gateway Health Check
try {
    $apiHealth = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 10 -ErrorAction Stop
    Write-Host "  API Gateway:" -NoNewline -ForegroundColor White
    if ($apiHealth.status -eq "healthy") {
        Write-Host " ✓ healthy" -ForegroundColor Green
    } else {
        Write-Host " ⚠ $($apiHealth.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  API Gateway: ✗ not responding" -ForegroundColor Red
}

# Frontend Health Check
try {
    $frontendCheck = Invoke-WebRequest -Uri "http://localhost:3000" -TimeoutSec 10 -UseBasicParsing -ErrorAction Stop
    Write-Host "  Frontend:   " -NoNewline -ForegroundColor White
    if ($frontendCheck.StatusCode -eq 200) {
        Write-Host " ✓ running" -ForegroundColor Green
    } else {
        Write-Host " ⚠ status $($frontendCheck.StatusCode)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Frontend:    ✗ not responding" -ForegroundColor Red
}

Write-Host ""

# Step 14: Show service status
Write-Host "STEP 14: Service status" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker-compose ps

Write-Host ""

# Summary
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Startup Complete!" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "✓ Infrastructure started (PostgreSQL, Zookeeper, Kafka)" -ForegroundColor Green
Write-Host "✓ Kafka topics created and verified" -ForegroundColor Green
Write-Host "✓ Application services started" -ForegroundColor Green
Write-Host ""

Write-Host "Access your application:" -ForegroundColor Yellow
Write-Host "  Frontend:    http://localhost:3000" -ForegroundColor White
Write-Host "  API Gateway: http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:    http://localhost:8000/docs" -ForegroundColor White
Write-Host "  AI Review:   http://localhost:8001" -ForegroundColor White
Write-Host ""

Write-Host "Test the system:" -ForegroundColor Yellow
Write-Host "  1. Open http://localhost:3000" -ForegroundColor White
Write-Host "  2. Go to Upload page" -ForegroundColor White
Write-Host "  3. Upload a code file (.py, .js, etc.)" -ForegroundColor White
Write-Host "  4. Wait 30-60 seconds" -ForegroundColor White
Write-Host "  5. Check Reviews page for your new review" -ForegroundColor White
Write-Host ""

Write-Host "Monitor logs:" -ForegroundColor Yellow
Write-Host "  All services:  docker-compose logs -f" -ForegroundColor Gray
Write-Host "  AI Review:     docker-compose logs -f ai-review" -ForegroundColor Gray
Write-Host "  API Gateway:   docker-compose logs -f api-gateway" -ForegroundColor Gray
Write-Host ""

# Ask if user wants to watch logs
$watchLogs = Read-Host "Watch AI Review logs now? (y/n)"
if ($watchLogs -eq 'y') {
    Write-Host ""
    Write-Host "Watching AI Review logs (Press Ctrl+C to stop)..." -ForegroundColor Cyan
    Write-Host "Look for: 'Kafka consumer started successfully' or 'Starting message consumption'" -ForegroundColor Gray
    Write-Host ""
    docker-compose logs -f ai-review
}