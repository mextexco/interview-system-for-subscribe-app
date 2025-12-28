# Interview System - 音声対話型プロファイリングインタビューシステム

会話を通じて「一人の人間」を形成していくゲーミフィケーション要素付きインタビューシステム

## 概要

ユーザーとAIキャラクターが自然な会話を重ね、プロファイリングデータを収集しながら、
右ペインで「人間像」が徐々に形成されていく様子を可視化するインタラクティブシステムです。

## 技術スタック

- **Backend**: Python 3.10+, Flask
- **LLM**: LM Studio (http://localhost:1234/v1/chat/completions)
  - 推奨モデル: Qwen2.5:7b, Gemma2:9b
- **Frontend**: HTML/CSS/JavaScript (バニラJS + React)
- **Visualization**: ReactFlow (インタラクティブマインドマップ)
- **音声**: VOICEVOX + Web Speech API

## セットアップ

### 必要要件

- Python 3.10以上
- Node.js 18以上 (プロファイルビジュアライザーのビルド用)
- LM Studio (起動済み、ポート1234で待機)
- VOICEVOX (音声合成用、オプション)

### インストール

```bash
# Python依存パッケージのインストール
pip install -r requirements.txt

# Node.js依存パッケージのインストール
npm install

# Reactコンポーネントのビルド
npm run build

# Flaskサーバーの起動
python backend/app.py
```

### 使い方

1. LM Studioを起動し、推奨モデル（Qwen2.5:7bまたはGemma2:9b）をロード
2. ブラウザで `http://localhost:5000` を開く
3. 性別を選択してインタビュー開始
4. AIキャラクターとの会話を楽しみながらプロファイリングを進める

## 機能

### プロファイルビジュアライゼーション

- **インタラクティブマインドマップ**: ReactFlowによるリアルタイム可視化
  - 円形レイアウトとウォーターフォールレイアウトの切り替え
  - ノードの折りたたみ/展開機能
  - 新規データの自動フォーカス&アニメーション
  - カテゴリー → サブカテゴリー → 値の3階層表示

### ゲーミフィケーション要素

- **バッジシステム**: 10種類の獲得可能バッジ
- **ランダムイベント**: 会話を盛り上げるミニゲーム
- **リアクション演出**: 3段階のビジュアルフィードバック

### プロファイリングカテゴリー（10項目）

1. 基本プロフィール
2. ライフストーリー
3. 現在の生活
4. 健康・ライフスタイル
5. 趣味・興味・娯楽
6. 学習・成長
7. 人間関係・コミュニティ
8. 情報収集・メディア
9. 経済・消費
10. 価値観・将来

### キャラクター

- **美咲**: 女性、20代後半、明るく聞き上手（男性ユーザー向け）
- **健太**: 男性、30代前半、落ち着いて知的（女性ユーザー向け）
- **あおい**: 中性的（その他のユーザー向け）

各キャラクター6種類の表情差分あり

## ディレクトリ構成

```
interview-system/
├── backend/                 # Flaskバックエンド
│   ├── app.py              # メインアプリケーション
│   ├── interviewer.py      # LLMインタビューロジック
│   ├── profile_manager.py  # プロファイル管理
│   └── ...
├── frontend/               # フロントエンド
│   ├── index.html         # メインHTML
│   ├── css/               # スタイルシート
│   ├── js/                # Vanilla JavaScript
│   ├── react/             # Reactコンポーネント (ソース)
│   │   ├── ProfileVisualizer.jsx
│   │   └── main.jsx
│   └── dist/              # Reactビルド出力
│       └── assets/
├── data/                   # ユーザーデータ保存先
├── requirements.txt        # Python依存パッケージ
├── package.json           # Node.js依存パッケージ
├── vite.config.js         # Viteビルド設定
└── README.md              # このファイル
```

## ライセンス

MIT License

## 開発

- Python 3.10+
- Flask開発サーバー使用
- ローカル環境専用（セキュリティは最小限）
