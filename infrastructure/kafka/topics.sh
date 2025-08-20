#!/bin/bash
# Kafka Topics Configuration for AI Code Review

# Wait for Kafka to be ready
echo "⏳ Waiting for Kafka to be ready..."
sleep 30

# Create topics with appropriate partitions and replication
echo "🔧 Creating Kafka topics..."

# code-commits: For webhook events
kafka-topics --bootstrap-server localhost:9092 --create --topic code-commits \
  --partitions 3 --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=gzip \
  --if-not-exists

echo "✅ Created topic: code-commits"

# review-results: For AI analysis results
kafka-topics --bootstrap-server localhost:9092 --create --topic review-results \
  --partitions 3 --replication-factor 1 \
  --config retention.ms=2592000000 \
  --config compression.type=gzip \
  --if-not-exists

echo "✅ Created topic: review-results"

# notifications: For alerts and notifications
kafka-topics --bootstrap-server localhost:9092 --create --topic notifications \
  --partitions 2 --replication-factor 1 \
  --config retention.ms=259200000 \
  --config compression.type=gzip \
  --if-not-exists

echo "✅ Created topic: notifications"

# metrics: For system monitoring
kafka-topics --bootstrap-server localhost:9092 --create --topic metrics \
  --partitions 1 --replication-factor 1 \
  --config retention.ms=604800000 \
  --config compression.type=gzip \
  --if-not-exists

echo "✅ Created topic: metrics"

# dead-letter-queue: For failed messages
kafka-topics --bootstrap-server localhost:9092 --create --topic dead-letter-queue \
  --partitions 1 --replication-factor 1 \
  --config retention.ms=2592000000 \
  --if-not-exists

echo "✅ Created topic: dead-letter-queue"

# List all topics
echo "📋 Current topics:"
kafka-topics --bootstrap-server localhost:9092 --list

echo "🎉 Kafka topics setup complete!"

# Topic Configuration Details:
# - code-commits: 7 days retention, 3 partitions (high throughput expected)
# - review-results: 30 days retention, 3 partitions 
# - notifications: 3 days retention, 2 partitions
# - metrics: 7 days retention, 1 partition
# - dead-letter-queue: 30 days retention, 1 partition