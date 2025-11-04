#!/bin/bash

# Gemini Image Generator (通常版) 起動スクリプト

echo "🚀 Gemini Image Generator (通常版) を起動します..."
echo ""

# 仮想環境の確認（存在する場合は有効化）
if [ -d "venv" ]; then
    echo "📦 仮想環境を有効化しています..."
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo "📦 仮想環境を有効化しています..."
    source .venv/bin/activate
fi

# .envファイルの確認
if [ ! -f ".env" ]; then
    echo "⚠️  警告: .envファイルが見つかりません"
    echo "📝 .env.exampleをコピーして.envファイルを作成してください"
    echo ""
    read -p "今すぐ作成しますか？ (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp .env.example .env
        echo "✅ .envファイルを作成しました"
        echo "📝 テキストエディタで.envファイルを開いてGEMINI_API_KEYを設定してください"
        echo ""
        read -p "設定が完了したらEnterキーを押してください..."
    else
        echo "❌ .envファイルがないため起動できません"
        exit 1
    fi
fi

# 依存関係の確認
echo "🔍 依存関係を確認しています..."
if ! python -c "import gradio" 2>/dev/null; then
    echo "⚠️  必要なパッケージがインストールされていません"
    echo "📦 依存関係をインストールしますか？"
    read -p "インストールする (y/n): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install -r requirements.txt
    else
        echo "❌ 依存関係がないため起動できません"
        exit 1
    fi
fi

# アプリケーションを起動
echo ""
echo "✨ アプリケーションを起動しています..."
echo "💬 シンプルな単一画像生成モード"
echo ""

python run.py
