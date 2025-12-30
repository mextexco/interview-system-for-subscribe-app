"""
Flask メインアプリケーション: REST API エンドポイント
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import sys
import threading

# 現在のディレクトリをパスに追加
sys.path.append(os.path.dirname(__file__))

from profile_manager import ProfileManager
from interviewer import Interviewer
from gamification import GamificationManager
from config import CHARACTERS, BADGES, RANDOM_EVENTS

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app)

# マネージャーインスタンス
profile_manager = ProfileManager()
interviewer = Interviewer()
gamification = GamificationManager()


@app.route('/')
def index():
    """メインページ"""
    return send_from_directory(app.static_folder, 'index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """ヘルスチェック"""
    from config import LM_STUDIO_MODEL
    lm_studio_connected = interviewer.check_lm_studio_connection()
    return jsonify({
        'status': 'ok',
        'lm_studio': 'connected' if lm_studio_connected else 'disconnected',
        'model': LM_STUDIO_MODEL
    })


@app.route('/api/characters', methods=['GET'])
def get_characters():
    """キャラクター一覧を取得"""
    return jsonify(CHARACTERS)


@app.route('/api/user/create', methods=['POST'])
def create_user():
    """新規ユーザーを作成"""
    data = request.json
    name = data.get('name', '名無し')
    gender = data.get('gender', 'その他')

    # 性別からキャラクターを選択（修正版）
    character_map = {
        '男性': 'kenta',      # 青山（男性キャラ）
        '女性': 'misaki',     # つむぎ（女性キャラ）
        'その他': 'aoi'        # ずんだもん（中性的）
    }
    character = character_map.get(gender, 'aoi')

    # ユーザー作成
    profile = profile_manager.create_user(name, gender, character)

    return jsonify({
        'success': True,
        'user_id': profile['user_id'],
        'profile': profile
    })


@app.route('/api/user/<user_id>', methods=['GET'])
def get_user(user_id):
    """ユーザープロファイルを取得"""
    profile = profile_manager.get_user(user_id)
    if not profile:
        return jsonify({'error': 'User not found'}), 404

    # カテゴリー別データ数を取得
    category_counts = profile_manager.get_category_data_count(user_id)

    # 総データ数を計算してプロファイルに追加（リアルタイム計算）
    profile['total_data_count'] = sum(category_counts.values())

    return jsonify({
        'profile': profile,
        'category_counts': category_counts
    })


@app.route('/api/session/create', methods=['POST'])
def create_session():
    """新規セッションを作成"""
    data = request.json
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'user_id required'}), 400

    # プロファイル確認
    profile = profile_manager.get_user(user_id)
    if not profile:
        return jsonify({'error': 'User not found'}), 404

    # セッション作成
    session = profile_manager.create_session(user_id)

    # 挨拶メッセージ
    character_id = profile['character']
    # 名前が「名無し」の場合は名前なしで挨拶
    user_name = profile.get('name')
    if user_name == '名無し':
        user_name = None
    greeting = interviewer.generate_greeting(character_id, user_name)
    first_question = interviewer.generate_first_question(character_id)

    # 初期メッセージを統合して追加（LM Studioはroleが交互である必要があるため）
    combined_message = f"{greeting}\n{first_question}"
    profile_manager.add_message(session['session_id'], 'assistant', combined_message, 'smile')

    # ランダムイベントチェック
    event = gamification.should_trigger_event()
    if event:
        session['events_triggered'].append(event['name'])
        profile_manager.update_session(session['session_id'], session)

    # 更新されたセッションを取得
    session = profile_manager.get_session(session['session_id'])

    return jsonify({
        'success': True,
        'session': session,
        'event': event
    })


@app.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """セッションを取得"""
    session = profile_manager.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    return jsonify({'session': session})


@app.route('/api/chat', methods=['POST'])
def chat():
    """チャットメッセージを送信"""
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('message')

    if not session_id or not user_message:
        return jsonify({'error': 'session_id and message required'}), 400

    # セッション取得（1回のみ）
    session = profile_manager.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    # ユーザー取得
    user_id = session['user_id']
    profile = profile_manager.get_user(user_id)
    if not profile:
        return jsonify({'error': 'User not found'}), 404

    # 削除リクエスト検出（「今の削除して」「やめます」など）
    is_deletion_request = interviewer.detect_deletion_request(user_message)

    if is_deletion_request:
        print(f"[Deletion] User is requesting to delete previous response - auto-undoing last turn")
        # 前のターンを自動的に取り消す
        undo_result = profile_manager.undo_last_turn(session_id)

        if undo_result['success']:
            print(f"[Deletion] Auto-undo successful, removed {undo_result['removed_data_count']} data points")

            # 更新されたプロファイルを取得
            profile = profile_manager.get_user(user_id)

            # 削除リクエストメッセージ自体は保存せず、確認メッセージのみ返す
            return jsonify({
                'success': True,
                'response': '承知しました！前の回答を削除しました。',
                'expression': 'smile',
                'reaction': 'none',
                'badges': [],
                'profile': profile,
                'deletion_request': True,  # 削除リクエストフラグ
                'removed_count': undo_result['removed_data_count']
            })
        else:
            return jsonify({
                'success': False,
                'error': undo_result['message']
            }), 400

    # 訂正検出（ユーザーが前の回答を訂正している場合）
    is_correction = interviewer.detect_correction(user_message, session['conversation'])

    if is_correction:
        print(f"[Correction] User is correcting previous response - auto-undoing last turn")
        # 前のターンを自動的に取り消す
        undo_result = profile_manager.undo_last_turn(session_id)
        if undo_result['success']:
            print(f"[Correction] Auto-undo successful, removed {undo_result['removed_data_count']} data points")
        else:
            print(f"[Correction] Auto-undo failed: {undo_result['message']}")

    # ユーザーメッセージを保存
    profile_manager.add_message(session_id, 'user', user_message)

    # セッションを再取得（ユーザーメッセージが追加された最新の状態を取得）
    session = profile_manager.get_session(session_id)

    # メッセージ分析
    message_analysis = gamification.analyze_message_for_data(user_message)

    # リアクション判定
    reaction_tier = gamification.determine_reaction(user_message, message_analysis)

    # セッションにリアクション記録
    if reaction_tier != "none":
        session['reactions'][reaction_tier] = session['reactions'].get(reaction_tier, 0) + 1
        profile_manager.update_session(session_id, session)

    # 表情選択
    expression = gamification.get_expression_for_reaction(reaction_tier, message_analysis)

    # カテゴリー別データ数と空カテゴリーを取得
    category_counts = profile_manager.get_category_data_count(user_id)
    empty_categories = profile_manager.get_empty_categories(user_id)

    # 会話履歴を構築（最新のsessionオブジェクトを使用）
    messages = []
    greeting_already_sent = False
    for i, msg in enumerate(session['conversation']):
        role = msg['role']
        content = msg['content']

        # 最初のメッセージがassistantの場合はスキップ（LM Studioは user から始まる必要がある）
        if i == 0 and role == 'assistant':
            print(f"[DEBUG] Skipping first assistant message for LM Studio compatibility")
            greeting_already_sent = True
            continue

        messages.append({'role': role, 'content': content})

    # LM Studioからレスポンス取得
    print(f"[DEBUG] Calling get_response with {len(messages)} messages, character: {profile['character']}")
    print(f"[DEBUG] Category counts: {category_counts}")
    print(f"[DEBUG] Empty categories: {empty_categories}")
    print(f"[DEBUG] Greeting already sent: {greeting_already_sent}")

    try:
        assistant_response = interviewer.get_response(
            messages,
            profile['character'],
            profile,
            category_counts,
            empty_categories,
            greeting_already_sent=greeting_already_sent,
            session_data=session
        )
        print(f"[DEBUG] get_response returned: {assistant_response if assistant_response else 'EMPTY/NONE'}")
    except Exception as e:
        print(f"[ERROR] get_response failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': 'LM Studioとの接続でエラーが発生しました。LM Studioが起動しているか確認してください。'
        }), 503

    if not assistant_response:
        print("[ERROR] No response from LM Studio")
        # LM Studio接続確認
        if not interviewer.check_lm_studio_connection():
            return jsonify({
                'success': False,
                'error': 'LM Studioとの接続が切れました。LM Studioが起動しているか確認してください。'
            }), 503
        else:
            return jsonify({
                'success': False,
                'error': 'LM Studioから応答がありませんでした。モデルが読み込まれているか確認してください。'
            }), 500

    # アシスタントメッセージを保存
    profile_manager.add_message(session_id, 'assistant', assistant_response, expression)

    # バッジチェック（軽量処理なので同期的に実行）
    newly_earned_badges = gamification.check_badges(profile, message_analysis)
    for badge_name in newly_earned_badges:
        profile_manager.add_badge(user_id, badge_name)

    # 更新されたプロファイルを取得
    profile = profile_manager.get_user(user_id)

    # 🚀 非同期処理: データ抽出をバックグラウンドで実行
    def extract_data_async():
        """バックグラウンドでデータ抽出を実行"""
        try:
            # 最新のセッションデータを取得
            updated_session = profile_manager.get_session(session_id)

            # プロファイリングデータ抽出
            extracted_data = interviewer.extract_profile_data(
                user_message,
                assistant_response,
                updated_session['conversation']
            )

            # 抽出したデータを保存
            for data_point in extracted_data:
                try:
                    profile_manager.add_extracted_data(
                        session_id,
                        data_point['category'],
                        data_point['key'],
                        data_point['value']
                    )
                    print(f"[Data] Saved: {data_point['category']} - {data_point['key']}: {data_point['value']}")
                except Exception as e:
                    print(f"[Data] Error saving data point: {e}")

            print(f"[Async] Data extraction completed for session {session_id}")
        except Exception as e:
            print(f"[Async] Error in background data extraction: {e}")
            import traceback
            traceback.print_exc()

    # バックグラウンドスレッドでデータ抽出を開始
    extraction_thread = threading.Thread(target=extract_data_async, daemon=True)
    extraction_thread.start()
    print(f"[Async] Started background data extraction for session {session_id}")

    # すぐにレスポンスを返す（データ抽出の完了を待たない）
    return jsonify({
        'success': True,
        'response': assistant_response,
        'expression': expression,
        'reaction': reaction_tier,
        'badges': newly_earned_badges,
        'profile': profile,
        'correction_detected': is_correction  # 訂正が検出されたかをフロントエンドに通知
    })


@app.route('/api/badges', methods=['GET'])
def get_badges():
    """バッジ一覧を取得"""
    return jsonify(BADGES)


@app.route('/api/events', methods=['GET'])
def get_events():
    """ランダムイベント一覧を取得"""
    return jsonify(RANDOM_EVENTS)


@app.route('/api/undo', methods=['POST'])
def undo_last_turn():
    """最後のやりとりを取り消す"""
    data = request.json
    session_id = data.get('session_id')

    if not session_id:
        return jsonify({'error': 'session_id required'}), 400

    try:
        result = profile_manager.undo_last_turn(session_id)

        if not result['success']:
            return jsonify(result), 400

        # 更新されたプロファイルを取得
        session = result['session']
        profile = profile_manager.get_user(session['user_id'])

        return jsonify({
            'success': True,
            'message': result['message'],
            'removed_data_count': result['removed_data_count'],
            'session': session,
            'profile': profile
        })

    except Exception as e:
        print(f"[ERROR] Undo failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    print("=" * 50)
    print("Interview System Backend Starting...")
    print("=" * 50)
    print("LM Studio URL:", interviewer.lm_studio_url)
    print("Checking LM Studio connection...")

    if interviewer.check_lm_studio_connection():
        print("✓ LM Studio is connected!")
    else:
        print("✗ LM Studio is NOT connected!")
        print("Please start LM Studio at http://localhost:1234")

    print("=" * 50)
    print("Server starting at http://localhost:5001")
    print("=" * 50)

    app.run(debug=True, host='0.0.0.0', port=5001)
