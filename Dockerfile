# Pythonベースイメージ
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なパッケージをインストール
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 環境変数を設定
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8501

# アプリケーションファイルをコピー（pipでインストールする前に）
COPY . .

# Pythonの依存関係をインストール
RUN pip install -e .

# 非rootユーザーを作成
RUN adduser --disabled-password appuser && \
    chown -R appuser:appuser /app
USER appuser

# ポートを開放
EXPOSE 8501

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8501}/_stcore/health || exit 1

# アプリケーションを起動
CMD ["streamlit", "run", "streamlit_main.py", "--server.address", "0.0.0.0", "--server.port", "8501"]
