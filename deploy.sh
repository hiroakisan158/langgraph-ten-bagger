#!/bin/bash

# シンプルなデプロイスクリプト
set -e

echo "🚀 Starting deployment..."

# 環境変数ファイルの確認
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your configuration."
    exit 1
fi

# 既存のコンテナを停止
echo "🛑 Stopping existing containers..."
docker-compose down

# イメージをビルド
echo "🔨 Building image..."
docker-compose build

# コンテナを起動
echo "▶️ Starting containers..."
docker-compose up -d

# ヘルスチェック
echo "🏥 Waiting for application to be healthy..."
timeout 60 bash -c 'until docker-compose ps | grep -q "healthy"; do sleep 5; done' || {
    echo "❌ Health check failed!"
    docker-compose logs
    exit 1
}

echo "✅ Deployment completed successfully!"
echo "🌐 Application is running at http://localhost:8501"
