#!/bin/bash
# startup.sh - Complete startup script for AI Code Review platform

echo "======================================"
echo "AI Code Review Platform - Startup"
echo "======================================"

# Step 1: Clean up
echo ""
echo "Step 1: Cleaning up old containers and volumes..."
docker-compose down -v
docker system prune -f

# Step 2: Build images
echo ""
echo "Step 2: Building Docker images..."
docker-compose build --no-cache

# Step 3: Start infrastructure services first
echo ""
echo "Step 3: Starting infrastructure (PostgreSQL, Zookeeper, Kafka)..."
docker-compose up -d postgres zookeeper

# Wait for PostgreSQL
echo "Waiting for PostgreSQL to be ready..."
sleep 10

# Start Kafka
docker-compose up -d kafka

# Wait for Kafka to be healthy
echo "Waiting for Kafka to be ready (this may take 1-2 minutes)..."
for i in {1..60}; do
    if docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
        echo "✓ Kafka is ready!"
        break
    fi
    echo "  Waiting for Kafka... ($i/60)"
    sleep 2
done

# Step 4: Create Kafka topics
echo ""
echo "Step 4: Creating Kafka topics..."
docker-compose exec -T kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --topic code-uploads \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists

docker-compose exec -T kafka kafka-topics --create \
    --bootstrap-server localhost:9092 \
    --topic review-results \
    --partitions 3 \
    --replication-factor 1 \
    --if-not-exists

echo "✓ Kafka topics created"

# List topics to verify
echo ""
echo "Verifying Kafka topics:"
docker-compose exec -T kafka kafka-topics --list --bootstrap-server localhost:9092

# Step 5: Start application services
echo ""
echo "Step 5: Starting application services..."
docker-compose up -d ai-review api-gateway metrics notification

# Wait for services to be healthy
echo "Waiting for services to be healthy..."
sleep 15

# Step 6: Start frontend
echo ""
echo "Step 6: Starting frontend..."
docker-compose up -d frontend

# Step 7: Show status
echo ""
echo "======================================"
echo "Checking service status..."
echo "======================================"
docker-compose ps

echo ""
echo "======================================"
echo "Service URLs:"
echo "======================================"
echo "Frontend:     http://localhost:3000"
echo "API Gateway:  http://localhost:8003"
echo "AI Review:    http://localhost:8001"
echo "Metrics:      http://localhost:8002"
echo ""
echo "Health Checks:"
curl -s http://localhost:8003/health | jq '.' 2>/dev/null || echo "API Gateway: Not responding"
curl -s http://localhost:8001/health | jq '.' 2>/dev/null || echo "AI Review: Not responding"
curl -s http://localhost:8002/health | jq '.' 2>/dev/null || echo "Metrics: Not responding"

echo ""
echo "======================================"
echo "Startup complete! Watching logs..."
echo "Press Ctrl+C to stop following logs"
echo "======================================"
echo ""

# Follow logs
docker-compose logs -f --tail=100