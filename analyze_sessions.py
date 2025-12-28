#!/usr/bin/env python3
"""
面接セッション分析スクリプト
Interview Session Analysis Script

全セッションファイルを読み込み、プロファイリング情報を抽出してレポートを生成します。
Reads all session files, extracts profiling information, and generates a report.
"""

import json
import os
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

# セッションディレクトリ / Session directory
SESSIONS_DIR = Path("data/sessions")
OUTPUT_DIR = Path("analyzed_sessions")

def load_all_sessions():
    """全セッションファイルを読み込む / Load all session files"""
    sessions = []
    session_files = sorted(SESSIONS_DIR.glob("*.json"))

    print(f"📁 Found {len(session_files)} session files")

    for session_file in session_files:
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                sessions.append(session_data)
        except Exception as e:
            print(f"⚠️ Error reading {session_file.name}: {e}")

    return sessions

def analyze_extracted_data(sessions):
    """抽出データを分析 / Analyze extracted data"""

    # カテゴリ別の統計 / Statistics by category
    category_stats = defaultdict(lambda: {
        'total_items': 0,
        'sessions_with_data': 0,
        'unique_keys': set(),
        'all_entries': []
    })

    # 全体の統計 / Overall statistics
    total_sessions = len(sessions)
    sessions_with_data = 0
    sessions_without_data = 0

    for session in sessions:
        extracted = session.get('extracted_data', {})
        has_data = False

        for category, items in extracted.items():
            if items:  # カテゴリにデータがある場合
                has_data = True
                category_stats[category]['total_items'] += len(items)
                category_stats[category]['sessions_with_data'] += 1

                for item in items:
                    if isinstance(item, dict):
                        key = item.get('key', '')
                        value = item.get('value', '')
                        timestamp = item.get('timestamp', '')

                        category_stats[category]['unique_keys'].add(key)
                        category_stats[category]['all_entries'].append({
                            'key': key,
                            'value': value,
                            'timestamp': timestamp,
                            'session_id': session.get('session_id'),
                            'user_id': session.get('user_id')
                        })

        if has_data:
            sessions_with_data += 1
        else:
            sessions_without_data += 1

    return {
        'category_stats': category_stats,
        'total_sessions': total_sessions,
        'sessions_with_data': sessions_with_data,
        'sessions_without_data': sessions_without_data
    }

def analyze_conversation_quality(sessions):
    """会話の質を分析 / Analyze conversation quality"""

    conversation_stats = []

    for session in sessions:
        conv = session.get('conversation', [])
        user_messages = [msg for msg in conv if msg.get('role') == 'user']
        assistant_messages = [msg for msg in conv if msg.get('role') == 'assistant']

        # イベント / Events
        events = session.get('events_triggered', [])

        # リアクション / Reactions
        reactions = session.get('reactions', {})
        total_reactions = sum(reactions.values())

        # 抽出データ数 / Number of extracted data items
        extracted = session.get('extracted_data', {})
        total_extracted = sum(len(items) for items in extracted.values())

        conversation_stats.append({
            'session_id': session.get('session_id'),
            'user_id': session.get('user_id'),
            'date': session.get('date'),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'total_messages': len(conv),
            'events_triggered': events,
            'total_reactions': total_reactions,
            'reactions': reactions,
            'extracted_items': total_extracted
        })

    return conversation_stats

def generate_profiling_insights(category_stats):
    """プロファイリングの洞察を生成 / Generate profiling insights"""

    insights = []

    # カテゴリ別の洞察 / Insights by category
    for category, stats in sorted(category_stats.items(),
                                   key=lambda x: x[1]['total_items'],
                                   reverse=True):
        if stats['total_items'] > 0:
            insights.append({
                'category': category,
                'total_items': stats['total_items'],
                'sessions_covered': stats['sessions_with_data'],
                'unique_keys': len(stats['unique_keys']),
                'keys_list': sorted(list(stats['unique_keys'])),
                'sample_entries': stats['all_entries'][:5]  # 最初の5件のサンプル
            })

    return insights

def generate_recommendations(analysis_results):
    """改善提案を生成 / Generate recommendations"""

    recommendations = []

    category_stats = analysis_results['category_stats']

    # 1. データ抽出率が低いカテゴリの特定
    low_coverage_categories = []
    for category, stats in category_stats.items():
        coverage_rate = (stats['sessions_with_data'] / analysis_results['total_sessions']) * 100
        if coverage_rate < 10 and coverage_rate > 0:
            low_coverage_categories.append({
                'category': category,
                'coverage': f"{coverage_rate:.1f}%"
            })

    if low_coverage_categories:
        recommendations.append({
            'type': '低カバレッジカテゴリ / Low Coverage Categories',
            'priority': 'HIGH',
            'description': '以下のカテゴリはデータ抽出率が低いです。質問の改善や会話フローの見直しを検討してください。',
            'details': low_coverage_categories
        })

    # 2. 空のカテゴリ
    empty_categories = [cat for cat, stats in category_stats.items()
                       if stats['total_items'] == 0]

    if empty_categories:
        recommendations.append({
            'type': '未使用カテゴリ / Unused Categories',
            'priority': 'MEDIUM',
            'description': '以下のカテゴリにはデータが全く抽出されていません。カテゴリの見直しや質問設計の改善が必要です。',
            'details': empty_categories
        })

    # 3. データの一貫性
    recommendations.append({
        'type': 'データ品質 / Data Quality',
        'priority': 'HIGH',
        'description': '抽出データの品質向上のための提案',
        'details': [
            'keyの命名規則を統一する（例：「住所」「住居状況」など）',
            'データの検証ルールを追加する（例：年収は数値のみ）',
            'タイムスタンプの正確性を確保する',
            '重複データの排除メカニズムを実装する'
        ]
    })

    # 4. 追加すべきカテゴリ/キー
    recommendations.append({
        'type': '追加提案 / Additional Suggestions',
        'priority': 'MEDIUM',
        'description': 'より詳細なプロファイリングのための追加項目',
        'details': [
            '年齢・性別などの基本情報',
            '職業・業種の詳細',
            '教育背景',
            '家族構成の詳細（配偶者、子供の年齢など）',
            'デジタルリテラシー',
            'ストレスレベル・メンタルヘルス指標',
            '将来の目標・夢'
        ]
    })

    # 5. 会話セッションの改善
    no_data_rate = (analysis_results['sessions_without_data'] / analysis_results['total_sessions']) * 100

    if no_data_rate > 50:
        recommendations.append({
            'type': '会話エンゲージメント / Conversation Engagement',
            'priority': 'CRITICAL',
            'description': f'全セッションの{no_data_rate:.1f}%でデータが抽出されていません。会話の質と継続性の改善が必要です。',
            'details': [
                'ユーザーの初回体験を改善する',
                'より自然な会話フローを設計する',
                'ユーザーが答えやすい質問形式を使用する',
                'エラー処理と回復メカニズムを強化する'
            ]
        })

    return recommendations

def save_report(analysis_results, conversation_stats, insights, recommendations):
    """レポートを保存 / Save report"""

    # 出力ディレクトリを作成
    OUTPUT_DIR.mkdir(exist_ok=True)

    # JSONレポート
    report = {
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_sessions': analysis_results['total_sessions'],
            'sessions_with_data': analysis_results['sessions_with_data'],
            'sessions_without_data': analysis_results['sessions_without_data'],
            'data_extraction_rate': f"{(analysis_results['sessions_with_data'] / analysis_results['total_sessions'] * 100):.1f}%"
        },
        'category_insights': insights,
        'conversation_statistics': conversation_stats,
        'recommendations': recommendations
    }

    report_file = OUTPUT_DIR / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n✅ JSONレポートを保存しました: {report_file}")

    # マークダウンレポート
    md_content = generate_markdown_report(analysis_results, conversation_stats, insights, recommendations)
    md_file = OUTPUT_DIR / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(md_file, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"✅ マークダウンレポートを保存しました: {md_file}")

    return report_file, md_file

def generate_markdown_report(analysis_results, conversation_stats, insights, recommendations):
    """マークダウン形式のレポートを生成 / Generate markdown report"""

    md = []
    md.append("# 面接セッション分析レポート")
    md.append("# Interview Session Analysis Report\n")
    md.append(f"**生成日時 / Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    md.append("---\n")

    # サマリー
    md.append("## 📊 サマリー / Summary\n")
    md.append(f"- **総セッション数 / Total Sessions:** {analysis_results['total_sessions']}")
    md.append(f"- **データあり / Sessions with Data:** {analysis_results['sessions_with_data']}")
    md.append(f"- **データなし / Sessions without Data:** {analysis_results['sessions_without_data']}")
    rate = (analysis_results['sessions_with_data'] / analysis_results['total_sessions'] * 100)
    md.append(f"- **データ抽出率 / Data Extraction Rate:** {rate:.1f}%\n")

    # カテゴリ別分析
    md.append("## 📋 カテゴリ別分析 / Category Analysis\n")

    for insight in insights:
        md.append(f"### {insight['category']}\n")
        md.append(f"- **抽出アイテム数 / Total Items:** {insight['total_items']}")
        md.append(f"- **カバーするセッション数 / Sessions Covered:** {insight['sessions_covered']}")
        md.append(f"- **ユニークキー数 / Unique Keys:** {insight['unique_keys']}")
        md.append(f"- **キー一覧 / Keys:** {', '.join(insight['keys_list'])}\n")

        if insight['sample_entries']:
            md.append("**サンプルデータ / Sample Data:**\n")
            for i, entry in enumerate(insight['sample_entries'][:3], 1):
                md.append(f"{i}. **{entry['key']}:** {entry['value']}")
            md.append("")

    # 会話統計
    md.append("## 💬 会話統計 / Conversation Statistics\n")

    # セッションを抽出アイテム数でソート
    top_sessions = sorted(conversation_stats, key=lambda x: x['extracted_items'], reverse=True)[:10]

    md.append("### トップ10セッション（抽出データ数順）/ Top 10 Sessions by Extracted Data\n")
    md.append("| セッションID | ユーザーメッセージ | 抽出データ数 | イベント | リアクション |")
    md.append("|---|---|---|---|---|")

    for stat in top_sessions:
        session_id_short = stat['session_id'][:8]
        md.append(f"| {session_id_short}... | {stat['user_messages']} | {stat['extracted_items']} | {', '.join(stat['events_triggered']) if stat['events_triggered'] else '-'} | {stat['total_reactions']} |")

    md.append("")

    # 改善提案
    md.append("## 💡 改善提案 / Recommendations\n")

    for rec in recommendations:
        priority_emoji = {
            'CRITICAL': '🔴',
            'HIGH': '🟡',
            'MEDIUM': '🟢',
            'LOW': '⚪'
        }.get(rec['priority'], '⚪')

        md.append(f"### {priority_emoji} {rec['type']} (優先度: {rec['priority']})\n")
        md.append(f"{rec['description']}\n")

        if isinstance(rec['details'], list):
            if rec['details'] and isinstance(rec['details'][0], dict):
                for detail in rec['details']:
                    md.append(f"- **{detail.get('category', '')}**: {detail.get('coverage', '')}")
            else:
                for detail in rec['details']:
                    md.append(f"- {detail}")
        md.append("")

    # データ品質の問題
    md.append("## ⚠️ 検出された問題 / Detected Issues\n")

    category_stats = analysis_results['category_stats']

    # 重複キーの検出
    md.append("### 重複・類似キーの可能性 / Potential Duplicate Keys\n")
    all_keys = []
    for stats in category_stats.values():
        all_keys.extend(stats['unique_keys'])

    key_counter = Counter(all_keys)
    duplicate_keys = [(k, v) for k, v in key_counter.items() if v > 1]

    if duplicate_keys:
        for key, count in sorted(duplicate_keys, key=lambda x: x[1], reverse=True):
            md.append(f"- **{key}**: {count}回出現")
    else:
        md.append("- 重複なし / No duplicates detected")

    md.append("")

    return "\n".join(md)

def main():
    """メイン処理 / Main process"""

    print("🚀 面接セッション分析を開始します...")
    print("🚀 Starting interview session analysis...\n")

    # セッション読み込み
    print("📖 セッションファイルを読み込んでいます...")
    sessions = load_all_sessions()
    print(f"✅ {len(sessions)} セッションを読み込みました\n")

    # データ分析
    print("🔍 抽出データを分析しています...")
    analysis_results = analyze_extracted_data(sessions)
    print("✅ データ分析完了\n")

    # 会話品質分析
    print("💬 会話品質を分析しています...")
    conversation_stats = analyze_conversation_quality(sessions)
    print("✅ 会話分析完了\n")

    # インサイト生成
    print("💡 プロファイリングインサイトを生成しています...")
    insights = generate_profiling_insights(analysis_results['category_stats'])
    print("✅ インサイト生成完了\n")

    # 改善提案生成
    print("📝 改善提案を生成しています...")
    recommendations = generate_recommendations(analysis_results)
    print("✅ 改善提案生成完了\n")

    # レポート保存
    print("💾 レポートを保存しています...")
    report_file, md_file = save_report(analysis_results, conversation_stats, insights, recommendations)

    print("\n" + "="*60)
    print("🎉 分析完了！ / Analysis Complete!")
    print("="*60)
    print(f"\n📄 レポートファイル:")
    print(f"   - JSON: {report_file}")
    print(f"   - Markdown: {md_file}")
    print("\n")

if __name__ == "__main__":
    main()
