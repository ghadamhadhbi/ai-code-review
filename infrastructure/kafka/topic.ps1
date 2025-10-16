# topics.ps1 - Kafka Topics Configuration for AI Code Review (Windows/PowerShell)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Kafka Topics Initialization" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# Wait for Kafka to be ready
Write-Host ""
Write-Host "⏳ Waiting for Kafka to be ready..." -ForegroundColor Yellow

$maxAttempts = 30
$attempt = 0
$kafkaReady = $false

while ($attempt -lt $maxAttempts) {
    docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > $null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Kafka is ready!" -ForegroundColor Green
        $kafkaReady = $true
        break
    }
    $attempt++
    Write-Host "  Attempt $attempt/$maxAttempts..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

if (-not $kafkaReady) {
    Write-Host "❌ Kafka failed to start in time" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🔧 Creating Kafka topics..." -ForegroundColor Yellow
Write-Host ""

# Function to create a Kafka topic
function New-KafkaTopic {
    param(
        [string]$Name,
        [int]$Partitions,
        [string]$RetentionMs,
        [string]$Description
    )
    
    Write-Host "$Description" -ForegroundColor Cyan
    
    docker-compose exec -T kafka kafka-topics --create `
        --bootstrap-server localhost:9092 `
        --topic $Name `
        --partitions $Partitions `
        --replication-factor 1 `
        --config retention.ms=$RetentionMs `
        --config compression.type=gzip `
        --if-not-exists > $null 2>&1
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ $Name created successfully" -ForegroundColor Green
    }
    else {
        Write-Host "   ⚠️  $Name already exists or failed" -ForegroundColor Yellow
    }
}

# Create required topics
New-KafkaTopic -Name "code-uploads" -Partitions 3 -RetentionMs "604800000" -Description "1. Creating topic: code-uploads"
New-KafkaTopic -Name "review-results" -Partitions 3 -RetentionMs "2592000000" -Description "2. Creating topic: review-results"

# Create optional topics
New-KafkaTopic -Name "notifications" -Partitions 2 -RetentionMs "259200000" -Description "3. Creating topic: notifications"
New-KafkaTopic -Name "metrics" -Partitions 1 -RetentionMs "604800000" -Description "4. Creating topic: metrics"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "📋 Listing all topics:" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

docker-compose exec -T kafka kafka-topics --list --bootstrap-server localhost:9092

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "📊 Topic details:" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

docker-compose exec -T kafka kafka-topics --describe `
    --bootstrap-server localhost:9092 `
    --topic code-uploads, review-results

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✨ Kafka topics setup complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

Write-Host ""
Write-Host "Topic Configuration Summary:" -ForegroundColor White
Write-Host "  • code-uploads:    7 days retention, 3 partitions (high throughput)" -ForegroundColor Gray
Write-Host "  • review-results: 30 days retention, 3 partitions" -ForegroundColor Gray
Write-Host "  • notifications:   3 days retention, 2 partitions" -ForegroundColor Gray
Write-Host "  • metrics:         7 days retention, 1 partition" -ForegroundColor Gray
Write-Host ""
