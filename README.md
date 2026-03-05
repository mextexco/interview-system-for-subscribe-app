# Interview System - 音声対話型プロファイリングインタビューシステム

会話を通じて「一人の人間」を形成していくゲーミフィケーション要素付きインタビューシステム

## 概要

ユーザーとAIキャラクターが自然な会話を重ね、プロファイリングデータを収集しながら、
右ペインで「人間像」が徐々に形成されていく様子を可視化するインタラクティブシステムです。

## 技術スタック

| 役割 | ローカル環境 | クラウド環境 |
|------|------------|------------|
| **LLM** | LM Studio (localhost:1234) | Gemini API (gemini-2.0-flash-lite) |
| **TTS** | VOICEVOX (localhost:50021) | Google Cloud TTS (Wavenet) |
| **STT** | Web Speech API (ブラウザ標準) | Web Speech API (ブラウザ標準) |
| **Backend** | Flask (port 5001) | gunicorn + Flask (port 8080) |
| **Frontend** | バニラJS + React (ReactFlow) | 同左 |
| **ホスティング** | - | Render.com |

## ローカル開発セットアップ

### 必要要件

- Python 3.10以上
- Node.js 18以上（Reactビルド用）
- LM Studio（起動済み・ポート1234）
- VOICEVOX（任意・音声合成用）

### インストール

```bash
pip install -r requirements.txt
npm install
npm run build
python backend/app.py
```

ブラウザで `http://localhost:5001` を開く。

## クラウドデプロイ（Render）

### 環境変数（Renderダッシュボード > Environment）

| 変数名 | 説明 | 取得先 |
|--------|------|--------|
| `LLM_API_URL` | `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions` | 固定値 |
| `LLM_MODEL` | `gemini-2.0-flash-lite` | 固定値 |
| `LLM_API_KEY` | Gemini APIキー | https://aistudio.google.com |
| `GOOGLE_TTS_API_KEY` | Google Cloud TTS APIキー | https://console.cloud.google.com |

`.env.example` を参照。

### デプロイ手順

1. Render.com でGitHubリポジトリを接続
2. Runtime: `Docker` を選択
3. 上記環境変数を設定
4. Deploy

### 注意事項

- 無料プランは15分無アクセスでスリープ（初回アクセスに30秒〜1分かかる）
- セッションデータはコンテナ再起動で消える（`💾 保存`ボタンでDL可能）
- Google Cloud TTS: 月100万文字まで無料（要クレジットカード登録）
- 未設定時はブラウザ標準のWeb Speech APIにフォールバック

## 機能

### プロファイルビジュアライゼーション

- **インタラクティブマインドマップ**: ReactFlowによるリアルタイム可視化
- 円形レイアウト / ウォーターフォールレイアウト切り替え
- ノードの折りたたみ/展開
- カテゴリー → サブカテゴリー → 値の階層表示

### ヒアリングコース（9種類）

基本情報のみ / 健康・ウェルネス / エンタメ・趣味 / 旅行・おでかけ /
サブスク棚卸し / 日常のモヤモヤ発見 / 消費行動診断 / キャリア・仕事 /
一日のリズム / 学習・知的好奇心

### キャラクター

- **つむぎちゃん**: 女性・20代後半・明るく聞き上手
- **青山くん**: 男性・30代前半・落ち着いて知的
- **ずんだもん**: 中性的・親しみやすい

## ディレクトリ構成

```
interview-system/
├── backend/
│   ├── app.py              # Flask APIエンドポイント
│   ├── interviewer.py      # LLMインタビューロジック
│   ├── profile_manager.py  # プロファイル管理
│   ├── config.py           # 設定（env var対応）
│   └── ...
├── frontend/
│   ├── index.html
│   ├── css/
│   ├── js/
│   │   ├── chat.js
│   │   ├── voice.js        # TTS/STT（VoiceVox→GoogleTTS→WebSpeech）
│   │   └── ...
│   └── dist/               # Reactビルド出力（要コミット）
├── data/                   # セッション・プロファイルデータ（gitignore）
├── Dockerfile
├── requirements.txt
├── .env.example
└── README.md
```

## ライセンス

MIT License
