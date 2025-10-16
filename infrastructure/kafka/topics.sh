#!/bin/bash
# infrastructure/k8s/kafka/topics.sh
# Kafka Topics Configuration for AI Code Review

set -e

echo "=========================================="
echo "Kafka Topics Initialization"
echo "=========================================="

# Wait for Kafka to be ready
echo ""
echo "⏳ Waiting for Kafka to be ready..."
max_attempts=30
attempt=0

while [ $attempt -lt $max_attempts ]; do
    if docker-compose exec -T kafka kafka-broker-api-versions --bootstrap-server localhost:9092 > /dev/null 2>&1; then
        echo "✅ Kafka is ready!"
        break
    fi
    attempt=$((attempt + 1))
    echo "  Attempt $attempt/$max_attempts..."
    sleep 2
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ Kafka failed to start in time"
    exit 1
fi

echo ""
echo "🔧 Creating Kafka topics..."
echo ""

# Create code-uploads topic (PRIMARY - REQUIRED)
echo "1. Creating topic: code-uploads"
docker-compose exec -T kafka kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic code-uploads \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=gzip \
  --if-not-exists

if [ $? -eq 0 ]; then
    echo "   ✅ code-uploads created successfully"
else
    echo "   ⚠️  code-uploads already exists or failed"
fi

# Create review-results topic (PRIMARY - REQUIRED)
echo "2. Creating topic: review-results"
docker-compose exec -T kafka kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic review-results \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=2592000000 \
  --config compression.type=gzip \
  --if-not-exists

if [ $? -eq 0 ]; then
    echo "   ✅ review-results created successfully"
else
    echo "   ⚠️  review-results already exists or failed"
fi

# Create notifications topic (OPTIONAL)
echo "3. Creating topic: notifications"
docker-compose exec -T kafka kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic notifications \
  --partitions 2 \
  --replication-factor 1 \
  --config retention.ms=259200000 \
  --config compression.type=gzip \
  --if-not-exists

if [ $? -eq 0 ]; then
    echo "   ✅ notifications created successfully"
else
    echo "   ⚠️  notifications already exists or failed"
fi

# Create metrics topic (OPTIONAL)
echo "4. Creating topic: metrics"
docker-compose exec -T kafka kafka-topics --create \
  --bootstrap-server localhost:9092 \
  --topic metrics \
  --partitions 1 \
  --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=gzip \
  --if-not-exists

if [ $? -eq 0 ]; then
    echo "   ✅ metrics created successfully"
else
    echo "   ⚠️  metrics already exists or failed"
fi

echo ""
echo "=========================================="
echo "📋 Listing all topics:"
echo "=========================================="
docker-compose exec -T kafka kafka-topics --list --bootstrap-server localhost:9092

echo ""
echo "=========================================="
echo "📊 Topic details:"
echo "=========================================="
docker-compose exec -T kafka kafka-topics --describe \
  --bootstrap-server localhost:9092 \
  --topic code-uploads,review-results

echo ""
echo "=========================================="
echo "✨ Kafka topics setup complete!"
echo "=========================================="
# 👇 CRITICAL FIX: Add a propagation delay
echo "💤 Waiting 15 seconds for topic metadata to propagate to all brokers and clients..."
sleep 15 
echo "✅ Topic propagation delay complete. Services should now recognize 'code-uploads'."


echo ""
echo "Topic Configuration Summary:"
echo "  • code-uploads:    7 days retention, 3 partitions (high throughput)"
echo "  • review-results: 30 days retention, 3 partitions"
echo "  • notifications:   3 days retention, 2 partitions"
echo "  • metrics:         7 days retention, 1 partition"
echo ""