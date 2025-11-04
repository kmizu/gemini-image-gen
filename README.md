# 🎨 Gemini Image Generator

Google Gemini APIを使用したインタラクティブな画像生成アプリケーション

## ✨ 特徴

- 💬 **対話型インターフェース** - 会話形式で画像を生成
- 🔢 **バッチ生成** - 1つのプロンプトから複数枚（1-8枚）を同時生成
- ⚡ **並列処理** - 高速な複数画像生成
- 📦 **ZIP一括ダウンロード** - 生成された複数画像を一括保存
- ✏️ **履歴管理** - 会話履歴の編集・削除が可能
- 💾 **保存/読み込み** - 会話をJSON形式で保存・復元
- 📥 **画像ダウンロード** - 生成された画像を直接ダウンロード
- 🎨 **リアルタイム生成** - ストリーミングAPIによる高速な画像生成

## 📋 必要要件

- Python 3.8以上
- Google Gemini API Key

## 🚀 インストール

### 1. リポジトリのクローン

```bash
git clone https://github.com/yourusername/gemini-image-gen.git
cd gemini-image-gen
```

### 2. 依存関係のインストール

```bash
pip install -r requirements.txt
```

または、パッケージとしてインストール：

```bash
pip install -e .
```

### 3. 環境設定

#### .envファイルを使用する方法（推奨）

```bash
# .env.exampleをコピーして.envファイルを作成
cp .env.example .env

# .envファイルを編集してAPI KEYを設定
# GEMINI_API_KEY=your-api-key-here
```

#### 環境変数を直接設定する方法

```bash
export GEMINI_API_KEY="your-api-key-here"
```

## 💻 使用方法

### 簡単起動（シェルスクリプト）

```bash
# バッチ版（複数画像生成、推奨）
./start.sh

# 通常版（単一画像生成）
./start_simple.sh
```

起動スクリプトは以下の機能を持っています：
- 仮想環境の自動検出と有効化
- .envファイルの存在確認と作成サポート
- 依存関係の確認とインストール

### 基本的な起動

```bash
# 標準版（単一画像生成）
python run.py

# バッチ版（複数画像生成、推奨）
python run_batch.py
```

### パッケージとしてインストールした場合

```bash
gemini-image-gen
```

### Pythonコードから使用

```python
from gemini_image_gen import create_app

app = create_app()
app.launch()
```

### プログラマティックな使用

```python
from gemini_image_gen import GeminiImageGenerator

# 画像生成器を初期化
generator = GeminiImageGenerator(api_key="your-api-key")

# 画像を生成
image, response_text = generator.generate(
    prompt="美しい夕日の風景を描いて",
    conversation_history=[]
)

# 画像を保存
if image:
    image.save("generated_image.png")
```

## 📁 プロジェクト構造

```
gemini-image-gen/
├── gemini_image_gen/           # メインパッケージ
│   ├── __init__.py
│   ├── core/                   # コア機能
│   │   ├── __init__.py
│   │   ├── generator.py        # Gemini API統合
│   │   └── conversation.py     # 会話管理
│   ├── ui/                     # UIコンポーネント
│   │   ├── __init__.py
│   │   └── app.py              # Gradioアプリケーション
│   ├── utils/                  # ユーティリティ
│   │   ├── __init__.py
│   │   ├── image_utils.py      # 画像処理
│   │   └── file_utils.py       # ファイル操作
│   └── config/                 # 設定管理
│       ├── __init__.py
│       └── settings.py         # アプリケーション設定
├── setup.py                    # パッケージ設定
├── requirements.txt            # 依存関係
├── README.md                   # ドキュメント
└── .gitignore                  # Git除外設定
```

## ⚙️ 設定

### 環境変数による設定

`.env`ファイルまたは環境変数で以下の設定が可能：

| 変数名 | 説明 | デフォルト値 |
|--------|------|-------------|
| `GEMINI_API_KEY` | Gemini API Key | (必須) |
| `GEMINI_MODEL_NAME` | 使用するGeminiモデル | `gemini-2.5-flash-image` |
| `HOST` | サーバーホスト | `0.0.0.0` |
| `PORT` | サーバーポート | `7860` |
| `SHARE` | Gradio共有リンクを作成 | `false` |
| `MAX_HISTORY_LENGTH` | 保持する最大履歴数 | `20` |
| `EXPORT_DIR` | エクスポートディレクトリ | `./exports` |
| `TEMP_DIR` | 一時ファイルディレクトリ | `./temp` |

### .envファイルの例

```env
GEMINI_API_KEY=your-api-key-here
GEMINI_MODEL_NAME=gemini-2.5-flash-image
HOST=0.0.0.0
PORT=7860
SHARE=false
MAX_HISTORY_LENGTH=20
EXPORT_DIR=./exports
TEMP_DIR=./temp
```

## 🔧 開発

### テストの実行

```bash
pytest tests/
```

### コードフォーマット

```bash
black gemini_image_gen/
isort gemini_image_gen/
```

### 型チェック

```bash
mypy gemini_image_gen/
```

## 📝 ライセンス

MIT License

## 🤝 貢献

プルリクエストを歓迎します。大きな変更の場合は、まずissueを開いて変更内容について議論してください。

## 🐛 バグ報告

バグを見つけた場合は、[GitHub Issues](https://github.com/yourusername/gemini-image-gen/issues)で報告してください。

## 📮 サポート

質問や提案がある場合は、[Discussions](https://github.com/yourusername/gemini-image-gen/discussions)をご利用ください。