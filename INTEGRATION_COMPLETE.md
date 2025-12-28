# マインドマップ統合完了レポート

## ✅ 完了した作業

### Phase 1: ビルド環境セットアップ
- ✅ package.json 作成
- ✅ Vite + React + ReactFlow インストール
- ✅ vite.config.js 設定
- ✅ ビルドスクリプト追加

### Phase 2: コンポーネント移植
- ✅ ProfileVisualizer.jsx を Antigravity からコピー
- ✅ データ構造を interview-system に適応
  - Antigravity: `{category, subcategory, value}`
  - interview-system: `extracted_data[category][{key, value}]`
  - key → subcategory にマッピング
- ✅ ProfileVisualizer.css 追加
- ✅ main.jsx (エントリーポイント) 作成

### Phase 3: 統合
- ✅ index.html に React ビルドファイル読み込み
- ✅ プロファイルビジュアライザーコンテナを右ペインに追加
- ✅ Vanilla JS と React のデータブリッジ実装
  - `window.initProfileVisualizer()` グローバル関数
  - `visualizer.js` の `updateProfileVisualizer()` 関数
- ✅ CSS スタイル調整

### Phase 4: テスト・ビルド
- ✅ 本番用ビルド実行 (`npm run build`)
- ✅ エラーハンドリングとログ追加
- ✅ .gitignore 更新 (node_modules, frontend/dist)
- ✅ README.md 更新

## 📁 追加されたファイル

```
frontend/react/
  ├── ProfileVisualizer.jsx  (19,970 bytes) - メインコンポーネント
  ├── ProfileVisualizer.css  (556 bytes)    - アニメーションスタイル
  └── main.jsx              (1,316 bytes)  - エントリーポイント

frontend/dist/assets/
  ├── visualizer.js         (346 KB)       - ビルド済みJS
  └── visualizer.css        (7.7 KB)       - ビルド済みCSS

package.json                               - Node.js依存関係
vite.config.js                            - Viteビルド設定
```

## 🔧 変更されたファイル

```
.gitignore                  - Node関連を追加
README.md                   - 技術スタックと使用方法を更新
frontend/index.html         - Reactコンテナと読み込みスクリプト追加
frontend/css/style.css      - プロファイルビジュアライザーセクション追加
frontend/js/visualizer.js   - updateProfileVisualizer() 関数追加
```

## 🎯 機能

### インタラクティブマインドマップ
- **円形レイアウト**: 中心のユーザーノードから放射状に展開
- **ウォーターフォールレイアウト**: 階層的に整列
- **ノード階層**: ユーザー → カテゴリー → サブカテゴリー(key) → 値(value)
- **折りたたみ/展開**: カテゴリー/サブカテゴリーノードをクリック
- **新規データアニメーション**: 新しく追加されたノードが光る
- **自動フォーカス**: 新規データに自動ズーム
- **ドラッグ&ズーム**: マウス操作で自由に移動

## 🚀 使用方法

### 初回セットアップ

```bash
# 依存関係のインストール
npm install

# Reactコンポーネントのビルド
npm run build

# バックエンド起動
python backend/app.py
```

### 開発時

```bash
# Reactコンポーネントを修正した場合
npm run build

# バックエンドを再起動
python backend/app.py
```

### ブラウザでのテスト

1. LM Studio でモデルをロード
2. `http://localhost:5001` を開く
3. キャラクターを選択して会話開始
4. 右ペイン上部のマインドマップを確認
   - 情報が追加されるとリアルタイムで更新される
   - レイアウト切り替えボタンで表示形式を変更
   - 展開ボタンで折りたたまれたノードを全て展開

## 🐛 トラブルシューティング

### マインドマップが表示されない

**ブラウザコンソールを確認:**

```javascript
// 期待されるログ:
[ProfileVisualizer] Module loaded, initProfileVisualizer available
[App] Profile Visualizer initialized
[ProfileVisualizer] Initialized successfully
[Visualizer] Profile visualizer updated with data: {...}
[ProfileVisualizer] update called with data: {...} userName: XXX
```

**よくある問題:**

1. **`initProfileVisualizer not found`**
   - 原因: Reactビルドファイルの読み込み失敗
   - 解決: `npm run build` を実行して `frontend/dist/` を生成

2. **`Container #profileVisualizerContainer not found`**
   - 原因: HTML要素が見つからない
   - 解決: ブラウザをハードリフレッシュ (Cmd+Shift+R)

3. **マインドマップが空白**
   - 原因: データがまだ収集されていない
   - 解決: AIと会話して情報を提供する

4. **ReactFlow のスタイルが適用されない**
   - 原因: CSSファイルの読み込み失敗
   - 解決: `frontend/dist/assets/visualizer.css` が存在するか確認

### ビルドエラー

```bash
# 依存関係を再インストール
rm -rf node_modules package-lock.json
npm install
npm run build
```

## 📊 データフロー

```
1. ユーザーが会話
   ↓
2. backend/app.py が LLM でデータ抽出
   ↓
3. session.extracted_data に保存
   {
     "基本プロフィール": [
       {"key": "名前", "value": "田中太郎", ...}
     ],
     ...
   }
   ↓
4. frontend/js/visualizer.js が updateStatusDisplay() を呼び出し
   ↓
5. updateProfileVisualizer() がセッションデータを取得
   ↓
6. window.profileVisualizer.update(extractedData, userName)
   ↓
7. React コンポーネントが再レンダリング
   ↓
8. ReactFlow がマインドマップを更新表示
```

## 🎨 カスタマイズ

### レイアウト調整

`frontend/react/ProfileVisualizer.jsx` の以下の値を変更:

- `radius1`, `radius2`, `radius3`: ノード間の距離
- `catSpacing`, `subcatSpacing`, `valSpacing`: ウォーターフォールレイアウトの間隔
- `width`, `height`: ノードのサイズ

### 色とスタイル

`frontend/react/ProfileVisualizer.css` で新規データのアニメーションを変更:

```css
.react-flow__node.new-item {
    animation: pulseGlow 1s ease-in-out 2 !important;
    background: linear-gradient(135deg, #a855f7 0%, #ec4899 100%) !important;
    /* 色を変更 */
}
```

### マインドマップのサイズ

`frontend/index.html` の以下を変更:

```html
<div id="profileVisualizerContainer"
     style="width: 100%; height: 500px; ...">
</div>
```

## 📝 次のステップ (オプション)

- [ ] ノードのツールチップ表示 (詳細情報)
- [ ] データのエクスポート機能 (JSON/PNG)
- [ ] 検索・フィルター機能
- [ ] カスタムノード形状 (カテゴリーごとに異なる形)
- [ ] タイムラインビュー (データ追加順に表示)
- [ ] ダークモード対応

## 🎉 完了

マインドマップ統合が完了しました！
ブラウザで http://localhost:5001 を開いて動作確認してください。

問題が発生した場合は、上記のトラブルシューティングを参照してください。
