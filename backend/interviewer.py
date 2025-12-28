"""
インタビューロジック: LM Studioとの対話、プロンプト生成
"""

import requests
import json
import re
from typing import Dict, List, Optional
from config import (
    LM_STUDIO_URL, LM_STUDIO_MODEL, CHARACTERS, CATEGORIES
)
from key_normalizer import KeyNormalizer


class Interviewer:
    """インタビューを管理するクラス"""

    def __init__(self):
        self.lm_studio_url = LM_STUDIO_URL

    def check_lm_studio_connection(self) -> bool:
        """LM Studioへの接続確認"""
        try:
            # 簡単なテストリクエスト
            response = requests.post(
                self.lm_studio_url,
                json={
                    "model": LM_STUDIO_MODEL,
                    "messages": [{"role": "user", "content": "test"}],
                    "max_tokens": 10
                },
                timeout=5
            )
            return response.status_code == 200
        except Exception as e:
            print(f"LM Studio connection error: {e}")
            return False

    def generate_system_prompt(self, character_id: str, profile: Dict,
                               category_counts: Dict[str, int],
                               empty_categories: List[str],
                               greeting_already_sent: bool = False,
                               session_data: Dict = None) -> str:
        """システムプロンプトを生成"""
        character = CHARACTERS.get(character_id, CHARACTERS["aoi"])

        # カテゴリー情報を整形
        categories_info = "\n".join([
            f"- {cat}: {CATEGORIES[cat]['description']}"
            for cat in CATEGORIES.keys()
        ])

        # 収集済みデータの概要
        collected_summary = ", ".join([
            f"{cat}({count}件)"
            for cat, count in category_counts.items() if count > 0
        ])
        if not collected_summary:
            collected_summary = "まだありません"

        # 空白カテゴリー
        empty_cats = ", ".join(empty_categories) if empty_categories else "なし"

        # 名前が既に取得されているかチェック（セッションデータから）
        user_name = None
        if session_data and 'extracted_data' in session_data:
            basic_profile = session_data['extracted_data'].get('基本プロフィール', [])
            for item in basic_profile:
                if item.get('key') == '名前' and item.get('value'):
                    user_name = item['value']
                    print(f"[DEBUG] Found user name in session data: {user_name}")
                    break

        # 名前がまだない場合、直前の会話から推測
        if not user_name and session_data and 'conversation' in session_data:
            conversation = session_data['conversation']
            if len(conversation) >= 2:
                # 最後から2番目がAI（名前を聞いた）、最後がユーザー（名前を答えた）
                last_assistant = conversation[-2] if conversation[-2].get('role') == 'assistant' else None
                last_user = conversation[-1] if conversation[-1].get('role') == 'user' else None

                if last_assistant and last_user:
                    # AIが「名前」について聞いているか
                    if '名前' in last_assistant.get('content', ''):
                        # ユーザーの返答が短い（名前の可能性）
                        user_response = last_user.get('content', '').strip()
                        if len(user_response) <= 20 and user_response:
                            user_name = user_response
                            print(f"[DEBUG] Inferred user name from conversation: {user_name}")


        # 会話戦略部分を条件分岐
        if user_name:
            # 名前が既に分かっている場合
            conversation_strategy = f"""【重要】
相手の名前は「{user_name}」です。すでに名前を知っています。
絶対に名前を聞き直したり、確認したりしないでください。

【会話戦略】
- 自然な会話でプロファイリングを続ける
- 空白カテゴリーがあれば軽く振る（「そういえば〜」）
- ユーザーが話したいことを優先
- 無理に質問を続けない（3回短い回答なら話題を変える）
- 相手の発言に共感しながら進める
- 1語回答の場合は具体例を示して掘り下げる
  例: 「IT」→「ITのどんなお仕事ですか？開発、インフラ、営業など」
- 曖昧な回答には選択肢を提示
  例: 「普通」→「朝型ですか？夜型ですか?」"""
        elif greeting_already_sent:
            # 挨拶だけ送った直後（名前はまだ分かっていない）
            conversation_strategy = """【会話戦略】
- あなたはすでに自己紹介をして、相手に名前を尋ねました
- 相手は今その返答をしています
- 自然な会話でプロファイリングを続ける
- 空白カテゴリーがあれば軽く振る（「そういえば〜」）
- ユーザーが話したいことを優先
- 無理に質問を続けない（3回短い回答なら話題を変える）
- 相手の発言に共感しながら進める
- 1語回答の場合は具体例を示して掘り下げる
  例: 「IT」→「ITのどんなお仕事ですか？開発、インフラ、営業など」
- 曖昧な回答には選択肢を提示
  例: 「普通」→「朝型ですか？夜型ですか?」"""
        else:
            conversation_strategy = """【会話戦略】
- まず相手の名前を聞く（初回のみ）
- その後、自然な会話でプロファイリング
- 空白カテゴリーがあれば軽く振る（「そういえば〜」）
- ユーザーが話したいことを優先
- 無理に質問を続けない（3回短い回答なら話題を変える）
- 相手の発言に共感しながら進める
- 1語回答の場合は具体例を示して掘り下げる
  例: 「IT」→「ITのどんなお仕事ですか？開発、インフラ、営業など」
- 曖昧な回答には選択肢を提示
  例: 「普通」→「朝型ですか？夜型ですか?」"""

        system_prompt = f"""あなたは{character['name']}、{character['description']}です。

【会話スタイル】
- 1発言は15-25文字程度
- 質問は1つずつ、簡潔に
- 口語的でフレンドリーに（{character['tone']}）
- 長い説明や前置きは不要
- テンポ良く進める
- 自然な会話を心がける

【重要な注意事項】
- 地理・地名・距離などの事実を正確に扱う
- 不確かな知識で推測や想像の発言をしない
- 知らないことは素直に認める
- 相手の発言に基づいて会話する（勝手な前提を作らない）

{conversation_strategy}

【プロファイリングカテゴリー】
{categories_info}

【現在の状況】
- 収集済み情報: {collected_summary}
- 空白カテゴリー: {empty_cats}
- セッション回数: {len(profile.get('sessions', []))}

日本語で対話してください。短く、フレンドリーに！"""

        return system_prompt

    def get_response(self, messages: List[Dict], character_id: str,
                    profile: Dict, category_counts: Dict[str, int],
                    empty_categories: List[str],
                    max_tokens: int = 100,
                    greeting_already_sent: bool = False,
                    session_data: Dict = None) -> Optional[str]:
        """
        LM Studioからレスポンスを取得
        Args:
            messages: 会話履歴 [{"role": "user/assistant", "content": "..."}]
            character_id: キャラクターID
            profile: ユーザープロファイル
            category_counts: カテゴリー別データ数
            empty_categories: 空のカテゴリーリスト
            max_tokens: 最大トークン数
            greeting_already_sent: 初回挨拶が既に送信されたか
            session_data: セッションデータ（extracted_data含む）
        Returns:
            AIの応答テキスト
        """
        try:
            # システムプロンプトを生成
            system_prompt = self.generate_system_prompt(
                character_id, profile, category_counts, empty_categories, greeting_already_sent, session_data
            )

            # メッセージリストを構築
            full_messages = [
                {"role": "system", "content": system_prompt}
            ] + messages

            # LM Studioにリクエスト
            response = requests.post(
                self.lm_studio_url,
                json={
                    "model": LM_STUDIO_MODEL,
                    "messages": full_messages,
                    "max_tokens": max_tokens,
                    "temperature": 0.6,  # 事実性向上のため0.8→0.6に変更
                    "stream": False
                },
                timeout=30
            )

            if response.status_code == 200:
                result = response.json()
                assistant_message = result["choices"][0]["message"]["content"]

                # デバッグ: 元のメッセージを出力
                print(f"[DEBUG] LM Studio raw response: {assistant_message[:200]}")

                # 内部コメントを除去
                cleaned_message = self._clean_response(assistant_message)

                # デバッグ: クリーン後のメッセージを出力
                print(f"[DEBUG] Cleaned response: {cleaned_message[:200]}")
                print(f"[DEBUG] Response length - raw: {len(assistant_message)}, cleaned: {len(cleaned_message)}")

                # 空の応答をチェック
                final_message = cleaned_message.strip()
                if not final_message:
                    print(f"[WARNING] Cleaned message is empty! Raw response was: {assistant_message[:500]}")
                    return None

                return final_message
            else:
                print(f"[ERROR] LM Studio error: {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"[ERROR] LM Studio error detail: {error_detail}")
                except:
                    print(f"[ERROR] LM Studio error body: {response.text[:500]}")

                # システムプロンプトの長さをチェック
                print(f"[DEBUG] System prompt length: {len(system_prompt)} characters")
                print(f"[DEBUG] Total messages: {len(full_messages)}")
                print(f"[DEBUG] System prompt preview: {system_prompt[:300]}...")

                return None

        except Exception as e:
            print(f"Error getting response: {e}")
            return None

    def _clean_response(self, text: str) -> str:
        """AI応答から内部コメントや不要な記号を除去"""
        import re

        # 各種内部コメントパターンを削除
        patterns = [
            r'\[思考:.*?\]',           # [思考: ...]
            r'\[内部:.*?\]',           # [内部: ...]
            r'\(思考:.*?\)',           # (思考: ...)
            r'\(内部:.*?\)',           # (内部: ...)
            r'<!--.*?-->',              # <!-- ... -->
            r'\{思考:.*?\}',           # {思考: ...}
            r'\{内部:.*?\}',           # {内部: ...}
            r'<thinking>.*?</thinking>',  # <thinking>...</thinking>
            r'\[Note:.*?\]',           # [Note: ...]
            r'\(Note:.*?\)',           # (Note: ...)
        ]

        cleaned = text
        for pattern in patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.DOTALL | re.IGNORECASE)

        # 連続する空白を1つに
        cleaned = re.sub(r'\s+', ' ', cleaned)

        return cleaned.strip()

    def generate_greeting(self, character_id: str, user_name: str = None) -> str:
        """挨拶メッセージを生成"""
        character = CHARACTERS.get(character_id, CHARACTERS["aoi"])

        if user_name:
            return f"こんにちは{user_name}さん！今日もお話しましょう！"
        else:
            # キャラクターごとの初対面の挨拶
            greetings = {
                'misaki': "初めまして！つむぎです。今日はよろしくお願いします！",
                'kenta': "初めまして。青山です。",
                'aoi': "こんにちはなのだ！ずんだもんなのだ。よろしくなのだ！"
            }
            return greetings.get(character_id, "こんにちは！よろしくお願いします！")

    def generate_first_question(self, character_id: str) -> str:
        """最初の質問を生成"""
        return "お名前を教えてもらえますか？"

    def extract_user_name(self, message: str) -> Optional[str]:
        """ユーザーメッセージから名前を抽出（簡易版）"""
        # 簡易的な実装
        # 「〜です」「〜といいます」などのパターンから抽出
        patterns = ["です", "だよ", "といいます", "っていいます", "と申します"]

        for pattern in patterns:
            if pattern in message:
                # パターンの前の部分を取得
                parts = message.split(pattern)
                if parts[0]:
                    # 最後の単語を名前として取得
                    name_candidate = parts[0].strip().split()[-1]
                    # 短すぎる・長すぎる名前は除外
                    if 1 <= len(name_candidate) <= 10:
                        return name_candidate

        # パターンマッチしない場合、メッセージ全体が短ければそれを名前とする
        if len(message) <= 10 and not any(c in message for c in "。、！？"):
            return message.strip()

        return None

    def suggest_next_topic(self, empty_categories: List[str],
                          character_id: str) -> Optional[str]:
        """次の話題を提案"""
        if not empty_categories:
            return None

        # ランダムに1つ選ぶ
        import random
        category = random.choice(empty_categories)

        # カテゴリーに応じた質問例
        questions = {
            "基本プロフィール": "お仕事は何してます？",
            "ライフストーリー": "これまでどんな人生を？",
            "現在の生活": "普段どんな生活してる？",
            "健康・ライフスタイル": "運動とかしてる？",
            "趣味・興味・娯楽": "趣味は何ですか？",
            "学習・成長": "何か学んでることある？",
            "人間関係・コミュニティ": "友達とはよく会う？",
            "情報収集・メディア": "ニュースとか見る？",
            "経済・消費": "買い物好き？",
            "価値観・将来": "将来の夢とかある？"
        }

        return questions.get(category, "他に何か教えて！")

    def extract_profile_data(self, user_message: str, assistant_response: str,
                             conversation_history: List[Dict]) -> List[Dict]:
        """
        会話からプロファイリングデータを抽出
        Returns: [{"category": "基本プロフィール", "key": "職業", "value": "エンジニア"}, ...]
        """
        max_retries = 2

        for attempt in range(max_retries):
            try:
                # データ抽出用プロンプト
                extraction_prompt = self._create_extraction_prompt(
                    user_message, assistant_response, conversation_history
                )

                # LM Studioにリクエスト
                response = requests.post(
                    self.lm_studio_url,
                    json={
                        "model": LM_STUDIO_MODEL,
                        "messages": [
                            {"role": "system", "content": extraction_prompt},
                            {"role": "user", "content": user_message}
                        ],
                        "max_tokens": 500,
                        "temperature": 0.3,  # 低めで正確性を重視
                        "stream": False
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    result = response.json()
                    extracted_text = result["choices"][0]["message"]["content"]

                    # デバッグ: 生のレスポンスを出力
                    print(f"[Extraction] LM Studio response: {extracted_text}")

                    # JSON形式でパース
                    extracted_data = self._parse_extracted_data(extracted_text)
                    print(f"[Extraction] Found {len(extracted_data)} data points")

                    # キー正規化を適用 / Apply key normalization
                    normalizer = KeyNormalizer()
                    normalized_data = normalizer.normalize_batch(extracted_data)

                    # 正規化統計をログ出力
                    stats = normalizer.get_normalization_stats()
                    if stats["total_normalizations"] > 0:
                        print(f"[Normalization] Normalized {stats['total_normalizations']} keys")
                        for category, data in stats['by_category'].items():
                            for raw, normalized in data['mappings'].items():
                                print(f"[Normalization]   {category}/{raw} → {normalized}")

                    # デバッグ: 抽出されたデータを出力
                    for data in normalized_data:
                        print(f"[Extraction] Data: {data}")

                    # データが抽出できた、または最後の試行の場合は結果を返す
                    if normalized_data or attempt == max_retries - 1:
                        return normalized_data

                    # データが空で、まだリトライ可能な場合
                    print(f"[Extraction] No data extracted, retry {attempt + 1}/{max_retries}")
                    continue
                else:
                    print(f"[Extraction] LM Studio error: {response.status_code}")
                    if attempt < max_retries - 1:
                        print(f"[Extraction] Retrying... ({attempt + 1}/{max_retries})")
                        continue
                    return []

            except requests.exceptions.Timeout:
                print(f"[Extraction] Timeout on attempt {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    print(f"[Extraction] Retrying...")
                    continue
                return []
            except Exception as e:
                print(f"[Extraction] Error: {e}")
                if attempt < max_retries - 1:
                    print(f"[Extraction] Retrying... ({attempt + 1}/{max_retries})")
                    continue
                return []

        return []

    def _create_extraction_prompt(self, user_message: str, assistant_response: str,
                                  conversation_history: List[Dict]) -> str:
        """データ抽出用のプロンプトを生成"""
        categories_desc = "\n".join([
            f"- {cat}: {CATEGORIES[cat]['description']}"
            for cat in CATEGORIES.keys()
        ])

        # 会話コンテキストを追加（直近5メッセージ）
        recent_context = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        context_text = "\n".join([
            f"{msg['role']}: {msg['content'][:100]}"
            for msg in recent_context
        ])

        # 標準キー名のリスト
        standard_keys_desc = """
基本プロフィール: 名前, 年齢, 性別, 職業, 住所, 家族構成, 住居状況
ライフストーリー: 学歴, 職歴, 人生の転機, 出身地, 習慣, 活動, 経験
現在の生活: 住居, 生活リズム, 食事, 睡眠, 通勤
健康・ライフスタイル: 運動習慣, 食事好み, 健康状態, 医療
趣味・興味・娯楽: 趣味, 音楽, 食べ物, 旅行, 活動
学習・成長: 学習内容, 分野, 活動, 目標, スキル
人間関係・コミュニティ: 友人, 家族関係, 所属, 活動
情報収集・メディア: 情報源, SNS, プラットフォーム, 関心事
経済・消費: 年収, 財政状況, 投資, 消費
価値観・将来: 価値観, 夢, 人生観, 理想"""

        prompt = f"""あなたはプロファイリングデータ抽出の専門家です。
ユーザーの発言から、以下のカテゴリーに該当する情報を抽出してください。

【会話コンテキスト】
{context_text}

【カテゴリー】
{categories_desc}

【推奨される標準キー名】
{standard_keys_desc}

これらの標準キー名を優先的に使用してください。

【ルール】
1. ユーザーの発言から明確に読み取れる情報のみ抽出
2. 会話の文脈を考慮して情報を抽出（単一発言だけでなく流れを見る）
3. 推測や想像は含めない
4. JSON配列形式で出力: [{{"category": "カテゴリー名", "key": "項目名", "value": "値"}}]
5. 情報がない場合は空配列 [] を返す
6. 各データポイントは簡潔に（key: 10文字以内、value: 50文字以内）
7. 標準キー名を優先的に使用

【良い抽出例】
ユーザー: "東京の渋谷区に住んでいます。ITエンジニアとして働いています。"
出力: [
  {{"category": "基本プロフィール", "key": "住所", "value": "東京都渋谷区"}},
  {{"category": "基本プロフィール", "key": "職業", "value": "ITエンジニア"}}
]

ユーザー: "毎朝ジョギングしてます。週3回くらい"
出力: [
  {{"category": "健康・ライフスタイル", "key": "運動習慣", "value": "毎朝ジョギング週3回"}}
]

【悪い抽出例】
ユーザー: "そうですね"
出力: []  # 具体的な情報がないため空配列

ユーザー: "うーん、わからないです"
出力: []  # 情報がないため空配列

ユーザーの発言を分析して、JSON配列のみを返してください。説明文は不要です。"""

        return prompt

    def _parse_extracted_data(self, text: str) -> List[Dict]:
        """抽出されたテキストからJSONデータをパース"""
        try:
            print(f"[Extraction] Parsing text: {text[:500]}")

            # JSONブロックを抽出
            json_match = re.search(r"\[.*\]", text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                print(f"[Extraction] JSON string: {json_str[:300]}")

                data = json.loads(json_str)

                # バリデーション
                valid_data = []
                for item in data:
                    if (isinstance(item, dict) and
                        "category" in item and
                        "key" in item and
                        "value" in item and
                        item["category"] in CATEGORIES):
                        valid_data.append(item)
                    else:
                        print(f"[Extraction] Invalid item: {item}")

                return valid_data
            else:
                print(f"[Extraction] No JSON array found in text")
                return []
        except json.JSONDecodeError as e:
            print(f"[Extraction] JSON parse error: {e}")
            print(f"[Extraction] Problematic text: {text[:500]}")
            return []
        except Exception as e:
            print(f"[Extraction] Parse error: {e}")
            return []

