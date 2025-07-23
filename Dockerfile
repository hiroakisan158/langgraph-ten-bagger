# ベースイメージとしてPythonを使用
FROM python:3.10-slim

# 作業ディレクトリを設定
WORKDIR /app

# 必要なライブラリをインストールするためにrequirements.txtをコピー
COPY requirements.txt ./requirements.txt

# ライブラリをインストール
RUN pip install -r requirements.txt

# アプリケーションファイルをコピー
COPY . /app

# Streamlit が使用するポートを開放
EXPOSE 8501

# スタートアップコマンド
CMD ["streamlit", "run", "streamlit_main.py"]