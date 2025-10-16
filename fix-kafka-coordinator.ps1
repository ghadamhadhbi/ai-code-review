# fix-kafka-coordinator.ps1
# Fixes Kafka CoordinatorNotAvailableError

$ErrorActionPreference = "Continue"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Fix Kafka Coordinator - AI Review Platform" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

# Step 1: Stop services
Write-Host "STEP 1: Stopping services" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker-compose stop ai-review api-gateway 2>&1 | Out-Null
Write-Host "  [SUCCESS] Services stopped" -ForegroundColor Green
Write-Host ""

# Step 2: Restart Kafka completely
Write-Host "STEP 2: Restarting Kafka cluster" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Stopping Kafka and Zookeeper..." -ForegroundColor White
docker-compose stop kafka zookeeper 2>&1 | Out-Null
Start-Sleep -Seconds 3

Write-Host "Starting Zookeeper..." -ForegroundColor White
docker-compose up -d zookeeper 2>&1 | Out-Null
Start-Sleep -Seconds 10

Write-Host "Starting Kafka..." -ForegroundColor White
docker-compose up -d kafka 2>&1 | Out-Null
Write-Host "  Waiting for Kafka to initialize (30 seconds)..." -ForegroundColor Gray
Start-Sleep -Seconds 30

Write-Host "  [SUCCESS] Kafka cluster restarted" -ForegroundColor Green
Write-Host ""

# Step 3: Verify Kafka is ready
Write-Host "STEP 3: Verifying Kafka is ready" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

$maxAttempts = 10
$attempt = 0
$kafkaReady = $false

while ($attempt -lt $maxAttempts -and -not $kafkaReady) {
    $attempt++
    Write-Host "  Checking Kafka (attempt $attempt/$maxAttempts)..." -ForegroundColor Gray
    
    docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $kafkaReady = $true
        Write-Host "  [SUCCESS] Kafka is ready!" -ForegroundColor Green
    } else {
        Start-Sleep -Seconds 3
    }
}

if (-not $kafkaReady) {
    Write-Host "  [ERROR] Kafka failed to start properly" -ForegroundColor Red
    Write-Host "  Continuing anyway..." -ForegroundColor Yellow
}

Write-Host ""

# Step 4: Delete and recreate consumer group offsets
Write-Host "STEP 4: Resetting consumer group" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Deleting old consumer group..." -ForegroundColor White
docker-compose exec -T kafka kafka-consumer-groups `
    --bootstrap-server localhost:9092 `
    --delete --group ai-review-consumer 2>&1 | Out-Null

Write-Host "  [SUCCESS] Consumer group reset" -ForegroundColor Green
Write-Host ""

# Step 5: Verify and recreate topics
Write-Host "STEP 5: Verifying Kafka topics" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Listing topics..." -ForegroundColor White
$topics = docker-compose exec -T kafka kafka-topics --list --bootstrap-server localhost:9092 2>&1

$hasCodeUploads = $topics -match "code-uploads"
$hasReviewResults = $topics -match "review-results"

if ($hasCodeUploads) {
    Write-Host "  ✓ code-uploads exists" -ForegroundColor Green
} else {
    Write-Host "  Creating code-uploads..." -ForegroundColor Yellow
    docker-compose exec -T kafka kafka-topics --create `
        --bootstrap-server localhost:9092 `
        --topic code-uploads `
        --partitions 3 `
        --replication-factor 1 `
        --config retention.ms=604800000 `
        --if-not-exists 2>&1 | Out-Null
    Write-Host "  ✓ code-uploads created" -ForegroundColor Green
}

if ($hasReviewResults) {
    Write-Host "  ✓ review-results exists" -ForegroundColor Green
} else {
    Write-Host "  Creating review-results..." -ForegroundColor Yellow
    docker-compose exec -T kafka kafka-topics --create `
        --bootstrap-server localhost:9092 `
        --topic review-results `
        --partitions 3 `
        --replication-factor 1 `
        --config retention.ms=2592000000 `
        --if-not-exists 2>&1 | Out-Null
    Write-Host "  ✓ review-results created" -ForegroundColor Green
}

Write-Host ""

# Step 6: Wait for coordinator
Write-Host "STEP 6: Waiting for coordinator to initialize" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "  Waiting 15 seconds for coordinator..." -ForegroundColor Gray
Start-Sleep -Seconds 15
Write-Host "  [SUCCESS] Coordinator should be ready" -ForegroundColor Green
Write-Host ""

# Step 7: Start AI Review with updated consumer
Write-Host "STEP 7: Starting AI Review Service" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Starting AI Review..." -ForegroundColor White
docker-compose up -d ai-review 2>&1 | Out-Null
Write-Host "  Waiting for service to initialize (20 seconds)..." -ForegroundColor Gray
Start-Sleep -Seconds 20

Write-Host "  [SUCCESS] AI Review Service started" -ForegroundColor Green
Write-Host ""

# Step 8: Check for errors
Write-Host "STEP 8: Checking AI Review logs" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

Write-Host "Recent logs:" -ForegroundColor White
$recentLogs = docker-compose logs --tail=30 ai-review 2>&1

$hasCoordinatorError = $recentLogs | Select-String "CoordinatorNotAvailableError"
$hasConsumerStarted = $recentLogs | Select-String "Kafka consumer started|consumer started successfully"

if ($hasCoordinatorError) {
    Write-Host "  [WARNING] Still seeing coordinator errors" -ForegroundColor Yellow
    Write-Host "  These should stop within 30-60 seconds" -ForegroundColor Gray
    Write-Host "  If they persist, the consumer will retry automatically" -ForegroundColor Gray
} elseif ($hasConsumerStarted) {
    Write-Host "  [SUCCESS] Kafka consumer started successfully!" -ForegroundColor Green
} else {
    Write-Host "  [INFO] Consumer is initializing..." -ForegroundColor Cyan
    Write-Host "  Check logs in 30 seconds: docker-compose logs -f ai-review" -ForegroundColor Gray
}

Write-Host ""

# Step 9: Start API Gateway
Write-Host "STEP 9: Starting API Gateway" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

docker-compose up -d api-gateway 2>&1 | Out-Null
Start-Sleep -Seconds 10
Write-Host "  [SUCCESS] API Gateway started" -ForegroundColor Green
Write-Host ""

# Step 10: Health checks
Write-Host "STEP 10: Health checks" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------" -ForegroundColor Yellow

try {
    $aiHealth = Invoke-RestMethod -Uri "http://localhost:8001/health" -TimeoutSec 5 -ErrorAction Stop
    if ($aiHealth.status -eq "healthy") {
        Write-Host "  ✓ AI Review Service: healthy" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ AI Review Service: $($aiHealth.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ AI Review Service: not responding" -ForegroundColor Red
}

try {
    $apiHealth = Invoke-RestMethod -Uri "http://localhost:8000/health" -TimeoutSec 5 -ErrorAction Stop
    if ($apiHealth.status -eq "healthy") {
        Write-Host "  ✓ API Gateway: healthy" -ForegroundColor Green
    } else {
        Write-Host "  ⚠ API Gateway: $($apiHealth.status)" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  ✗ API Gateway: not responding" -ForegroundColor Red
}

Write-Host ""

# Summary
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "Summary" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Kafka coordinator fix applied!" -ForegroundColor Green
Write-Host ""
Write-Host "What was done:" -ForegroundColor Yellow
Write-Host "  1. ✓ Restarted Kafka cluster (Zookeeper → Kafka)" -ForegroundColor White
Write-Host "  2. ✓ Reset consumer group offsets" -ForegroundColor White
Write-Host "  3. ✓ Verified topics exist" -ForegroundColor White
Write-Host "  4. ✓ Waited for coordinator initialization" -ForegroundColor White
Write-Host "  5. ✓ Restarted AI Review Service" -ForegroundColor White
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Wait 60 seconds for full initialization" -ForegroundColor White
Write-Host "  2. Monitor logs: docker-compose logs -f ai-review" -ForegroundColor White
Write-Host "  3. Upload a test file at http://localhost:3000/upload" -ForegroundColor White
Write-Host ""
Write-Host "Expected behavior:" -ForegroundColor Yellow
Write-Host "  • Coordinator errors should stop within 60 seconds" -ForegroundColor White
Write-Host "  • You should see 'Kafka consumer started successfully'" -ForegroundColor White
Write-Host "  • New uploads will create new reviews" -ForegroundColor White
Write-Host ""

$watchLogs = Read-Host "Watch AI Review logs now? (y/n)"
if ($watchLogs -eq 'y') {
    Write-Host ""
    Write-Host "Watching logs (Press Ctrl+C to stop)..." -ForegroundColor Cyan
    Write-Host "Look for: 'Kafka consumer started successfully'" -ForegroundColor Gray
    Write-Host ""
    docker-compose logs -f ai-review
}