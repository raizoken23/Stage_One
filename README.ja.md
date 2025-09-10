# シタデルサービス

このリポジトリには、人間とAIの協調的知能のためのプラットフォームであるシタデルエコシステムのためのサービスのコレクションが含まれています。

## はじめに

### 前提条件

*   Python 3.8+
*   pip

### インストール

1.  リポジトリをクローンします:
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  必要な依存関係をインストールします:
    ```bash
    pip install -r requirements.txt
    ```

## プロジェクト構造

このリポジトリには、以下のコアサービスが含まれています:

*   `embedding_service.py`: 様々なプロバイダー（例：OpenAI）を使用してテキスト埋め込みを生成するための堅牢なサービス。キャッシング、リトライロジック、詳細なロギングなどの機能が含まれています。
*   `faiss_management_service.py`: FAISSベクターインデックスを管理し、対話するための高レベルAPIを提供し、低レベルのストレージ操作を`VectorStorageService`に委任します。
*   `vector_storage_service.py`: FAISSを使用してベクター埋め込みとそのメタデータのストレージと検索を管理します。
*   `memory_context_service.py`: 様々なデータサービスを統合することにより、AIエージェントのためのリッチで文脈的なプロンプトの組み立てを調整します。
*   `global_tracker_service.py`: SQLiteデータベースを使用して、エコシステム内のすべての思考ベクターのメタデータのライフサイクルを管理します。
*   `summarizer_service.py`: LLMを使用してテキストの簡潔な要約やダイジェストを生成するための拡張可能なサービス。
*   `intellisense_system.py`: ソフトウェア開発ライフサイクルの評価と改善のためのAI駆動の支援を提供する包括的なシステム。
*   `bucket_cognitive_domain_manager.py`: FAISS、SQLite、GCSのハイブリッド永続モデルを使用して、GCSバケット内の自己完結型「コグニティブドメイン」を管理します。

## 使用方法

以下は`EmbeddingService`を使用する基本的な例です（`CitadelHub`インスタンスを介して初期化および設定されていると仮定しますが、このリポジトリでは完全には利用できません）:

```python
# これは概念的な例であり、完全なCitadelHubは存在しません。

from embedding_service import EmbeddingService

# hubが初期化されたCitadelHubインスタンスであると仮定します
# embedding_service = hub.get_service("EmbeddingService")

# スタンドアロンで実行する場合、直接初期化することがあります（依存関係が必要です）
embedding_service = EmbeddingService()

if embedding_service.is_ready():
    text_to_embed = "これはテスト文です。"
    embedding = embedding_service.generate_embedding_sync(text_to_embed)

    if embedding:
        print(f"次元数の埋め込みの生成に成功しました: {len(embedding)}")
    else:
        print("埋め込みの生成に失敗しました。")
else:
    print("埋め込みサービスは準備ができていません。APIキーと依存関係を確認してください。")

```

<details>
<summary><b>レガシーシタデル統一開発ガイド＆システム要件仕様</b></summary>

# シタデル統一開発ガイド＆システム要件仕様（統合版）

このドキュメントは、シタデル統一開発ガイドとシステム要件仕様の重要なコンポーネントを統合し、合理化されたレビューと専用のドキュメンテーションリポジトリへの潜在的な統合を目的としています。マスター目次、コア原則、コマンドデッキ、ブラザーフッドミッション、センチネルプロトコル（TSP）、公式ルールセット、エージェントブループリント、およびシタデルガバナンス＆メタデータテンプレート（CGMT）を網羅しています。

---
## MASTER_TABLE_OF_CONTENTS_AND_ECOSYSTEM_INDEX.md
---

**AI指示＆メタデータブロック（AIMB v1.0）**
**AIモデル向け（例：NexusMind, Axiom, Sentinel, Watcher, DevPartners, NexusArchitectAI）:**
1. **コンテキスト:** これは1ページ目、「シタデルエコシステム - マスター目次＆統一インデックス v1.0」であり、「シタデル統一開発ガイド＆SRS v2.0.1+」全体への入り口として機能します。
2. **目的:** 包括的で動的に更新可能な目次を提供すること。高レベルの進捗トラッカー、エコシステムのアーキテクチャ、コンポーネント、プロトコル、相互依存性をAIが吸収するための構造化された入り口として機能し、知識の保持を確実にします。
3. **アクション（該当する場合）:**
- **NexusArchitectAI/AuditSentinel向け:** これがあなたの主要なインデックス作成ターゲットです。このページを定期的に更新し、リンクされているすべてのドキュメントのステータスとバージョンを記載してください。リンクを検証し、「AI指示＆メタデータブロック標準（AIMBS v1.0）」が後続のすべてのページに組み込まれていることを確認してください。
- **他のすべてのAI向け:** このToCを、統一ガイド内の特定の情報を取得するための主要なナビゲーションリファレンスとして利用してください。
4. **前提条件:** リンクされているすべてのドキュメントへのアクセスと、ステータスとバージョンの詳細についてAIMBメタデータを解析する能力。
5. **出力期待値（AIがこのページを生成/更新する場合）:** 定義されたテーブル形式への厳密な準拠。このToCページ自体のメタデータは正確でなければなりません。

**ページメタデータ（AIMB v1.0形式）:**
• _page_id: TOC-MASTER-V1.0
• _page_title: シタデルエコシステム - マスター目次＆統一インデックス v1.0
• _page_version: 1.0.0
• _last_updated_by: NexusArchitectAI_v2.1 (マスターインデクサー)
• _last_updated_timestamp: {{CurrentDateTimeISO_Z}} <!-- 動的に更新 -->
• _status: Active_Live_Index
• _linked_sections: ["ALL_PAGES_IN_THIS_GUIDE"]
• _keywords: ["目次", "マスターインデックス", "シタデルガイド", "エコシステムナビゲーション", "AI学習マップ", "ドキュメンテーションインデックス"]

**シタデルエコシステム – マスター目次＆統一インデックス v1.0**

*人間とAIの協調的知能のアーキテクチャ、プロトコル、進化をナビゲートする*

**ドキュメントメタデータ（このToCページ）:**
• _report_id: TOC-MASTER-20250602-V1.0
• _document_schema: AISchema-v1.0 (OFFICIALRULESET.mdによって管理)
• _evaluation_timestamp: {{CurrentDateTimeISO_Z}} (動的に更新)
• _generated_by: NexusArchitectAI_v2.1 (マスターインデクサー)
• _docstyle_verified: true
• _manual_override: false
• _fallback_used: false
• _intended_for[]: ["人間（すべての貢献者）", "AI（ナビゲーション、進捗追跡、文脈学習）"]
• _report_type: master_table_of_contents_and_ecosystem_index
• _visibility_tier: internal_strategic_leadership_and_all_architects

<details>
<summary>**このマスターインデックスの目的:**</summary>
1. シタデル統一開発ガイド＆SRS全体の包括的で動的に更新可能な目次を提供します。
2. 主要な開発フェーズとドキュメンテーションのマイルストーンの高レベルな進捗トラッカーとして機能します。
3. AIシステムがエコシステムのアーキテクチャ、コンポーネント、プロトコル、およびそれらの相互依存性を学習するための構造化されたエントリポイントを提供します。
4. 開発が中断した場合の継続性と知識の保存を保証します。
</details>

<details>
<summary>**AI指示＆メタデータブロック標準（AIMBS v1.0） - 後続のすべてのガイドページ向け:**</summary>
**この統一ガイド内のすべての主要なコンテンツページ（このToCに続く）は、このような「AI指示＆メタデータブロック」で始まらなければなりません:**

**AI指示＆メタデータブロック（AIMB v1.0）**
**AIモデル向け（例：NexusMind, Axiom, Sentinel, Watcher, DevPartners）:**
1. **コンテキスト:** このページ（[ページ番号]: [ページタイトル]）は、「シタデル統一開発ガイド＆SRS v2.0.1+」の一部です。
2. **目的:** [このページの内容に特化した開発/SRS生成/プロトコル遵守/学習/監査]のために、本書の情報を理解し、適用すること。
3. **アクション（該当する場合）:** [特定の指示、例：「これらのFRで知識グラフを更新する」、「これらのプロトコルに対してコード例を検証する」、「このブループリントを使用して[X]モジュールを生成する」、「これらのメトリクスを自己評価レポートに組み込む」]
4. **前提条件:** OFFICIALRULESET.md（パートV）、SENTINELプロトコル（3ページ）、および関連するブループリントに精通していること。
5. **出力期待値（AIがこのページのためにコンテンツを生成する場合）:** すべての生成されたレポート、SRSセクション、またはプロトコル定義について、OFFICIALRULESET.mdのフォーマットに厳密に従うこと。すべてのメタデータフッターが完全かつ正確であることを確認すること。

**ページメタデータ（AIMB v1.0形式）:**
• _page_id: [このページの一意のID、例：CMDDECK-V1.2, BHMSN-V1.1, TSP-V1.0, ORS-EMBED-V1.0]
• _page_title: [このページの完全なタイトル]
• _page_version: [このページのコンテンツのセマンティックバージョン、例：1.2.0]
• _last_updated_by: [人間/AIのID]
• _last_updated_timestamp: {{CurrentDateTimeISO_Z}}
• _status: [例：「ドラフト」、「レビュー待ち」、「承認済み」、「廃止」]
• _linked_sections: [このガイド内の関連するページIDまたはセクションIDのリスト]
• _keywords: [検索性とAIのコンテキストマッピングのための関連キーワードのリスト]
</details>

<details>
<summary>**マスター目次＆エコシステムインデックス（CITADEL UDG SRS v2.0.2+）**</summary>

| **ページ** | **パート/セクションID** | **タイトル / 説明** | **ステータス** | **バージョン** | **最終レビュー/AI検証** |
|----------|--------------------------|------------------------------------------------------------------------------------------|-------------------|-------------|-------------------------------|
| **1** | **TOC-MASTER-V1.0** | **シタデルエコシステム - マスター目次＆統一インデックス** | **アクティブ** | 1.0.0 | {{CurrentDateTimeISO_Z}} |
| | | (このページ - AI指示＆メタデータブロック標準AIMB v1.0を含む) | | | |
| **A.1** | **PART-A-PRINCIPLES-V1.0**| **ページA.1: シタデルエコシステム - コアアーキテクチャ原則＆運用上の絶対条件** | **アクティブ** | 1.0.0 | {{CurrentDateTimeISO_Z}} |
| | | (基礎となる設計哲学: DKA, SCA, OGA; 強制と進化) | | | |
| **A.2** | **PART-A-MDCI-V1.0** | **ページA.2: マスター依存関係＆設定インデックス (MDCI) v1.0** | **アクティブ** | 1.0.0 | {{CurrentDateTimeISO_Z}} |
| | | (ファイルパス、モジュールID、バージョン、コア依存関係、デフォルトモデル名のSSoT) | | | |
| **2** | **CMDDECK-V1.3.3** | **ページ2: シタデルプロジェクト – コマンドデッキ** | **アクティブ** | 1.3.3 | {{CurrentDateTimeISO_Z}} |
| | | (戦略的序文: ビジョン、コア評議会、全体目標、インタラクティブロードマップ) | | | |
| **3** | **BHMSN-V1.1** | **ページ3: ブラザーフッド - 協調的進化のためのミッション** | **アクティブ** | 1.1.0 | {{CurrentDateTimeISO_Z}} |
| | | (指導目的、相乗効果のコア原則、協調的必須事項) | | | |
| **4** | **TSP-V1.0** | **ページ4: センチネルプロトコル (TSP) v1.0 - エコシステムガバナンス＆開発標準**| **アクティブ** | 1.0.0 | {{CurrentDateTimeISO_Z}} |
| | | (OFFICIALRULESET.mdの運用化: MDP, CMP, RLP, TVP, AHCP, DSAGP; データシート) | | | |
| **5** | **ORS-EMBED-V1.0** | **ページ5: OFFICIALRULESET.md - AI構造化報告フレームワーク v1.0 (埋め込み)** | **アクティブ** | 1.0.0 | {{CurrentDateTimeISO_Z}} |
| | | (報告基準の完全な正規テキスト、セクションI-XII) | | | (自己整合) |
| **6** | **AGENTBLUE-CDS-V1.3-EMBED**| **ページ6: AGENT_BLUEPRINT_INSTRUCTION_CDS v1.3 (埋め込み)** | **アクティブ** | 1.3.0 | {{CurrentDateTimeISO_Z}} |
| | | (シタデル評議会エージェントの正規エンジニアリング仕様) | | | |
| **7** | **CGMT-V1.0-EMBED** | **ページ7: シタデルガバナンス＆メタデータテンプレート (CGMT) v1.0 (埋め込み)** | **アクティブ** | 1.0.0 | {{CurrentDateTimeISO_Z}} |
| | | (すべてのPythonモジュールの標準ヘッダーテンプレート) | | | |
| **P0** | **PART0-SNAPSHOT-V1.1.0**| **ページ8: パート0 - 現在のエコシステムのスナップショット、主要な指示＆重大なブロッカー** | **更新中** | 1.1.0 | {{CurrentDateTimeISO_Z}} |
| | | (最新のログとCEREP/IFPに基づく動的ステータス) | | | (NexusArchitectAI) |
| **P1** | **PART1-FRONTEND-BP-V1.5**| **パートI: フロントエンド (Zayara UI) - アーキテクチャブループリント＆開発者ガイダンス** | **安定** | 1.5 | (前回のレビュー日) |
| **P2** | **PART2-FRONTEND-SRS-V1.0**| **パートII: フロントエンド (Zayara UI) - ソフトウェア要件仕様 (SRS)** | **安定** | 1.0 | (前回のレビュー日) |
| **P3** | **PART3-BACKEND-SRS-V1.8.0**| **パートIII: バックエンド - ソフトウェア要件仕様 (SRS)** | **進化中** | 1.8.0 | (NexusAuditorによる継続中) |
| | P3.KERNEL | `citadel_api_kernel.py` (v5.3.0) モジュール統計シート＆SRS | アクティブ | 1.0 | SRS-KERNEL-20250621-001 |
| | ... | (以前に詳述した他のバックエンドSRSセクション、必要に応じてバージョン更新) | ... | ... | ... |
| **P4** | **PART4-CEDGP-V1.0** | **パートIV: シタデルエコシステム開発＆ガバナンスプロトコル (CEDGP)** | **アクティブ** | 1.0 | UDG_v1.7.8_SecB_CEREP |
| | | (DAP, CQIP, TVP, AHCP, DSGP, AAGL-P 詳細プロトコル) | | | |
| **P5** | **PART5-ORS-V1.0-REF** | **パートV: OFFICIALRULESET.md (ページ5への参照)** | **参照** | 1.0.0 | (ページ5を参照) |
| **P6** | **PART6-AGENTBLUE-V1.3-REF**| **パートVI: AGENT_BLUEPRINT_INSTRUCTION_CDS v1.3 (ページ6への参照)** | **参照** | 1.3.0 | (ページ6を参照) |
| **P7** | **PART7-CGMT-V1.0-REF** | **パートVII: CitadelGovernanceTemplate.md (CGMT) v1.0 (ページ7への参照)** | **参照** | 1.0.0 | (ページ7を参照) |

<details>
<summary>**ステータス凡例:**</summary>
**アクティブ/安定:** 文書化され、レビューされ、現在のフェーズで安定していると見なされます。
**進化中/更新中:** 新しい洞察/コードに基づいて積極的に更新または拡張されています。
**ドラフト/レビュー:** 初期ドラフトが完了し、完全なレビューまたは大幅な改良待ちです。
**概念/計画:** 高レベルのアイデアまたはプレースホルダー。詳細なSRS/ブループリントはまだ作成されていません。
**ブロック/重大:** 重大な依存関係または問題の解決待ちです。
**参照:** ドキュメントの内容は別のプライマリページ（例：ページ5）に埋め込まれており、このエントリは構造のための参照です。
</details>

**このマスターインデックスは生きたドキュメントです。**
**AIシステム（NexusMind、Axiom）は、その継続的な検証と更新を担当しています。**
</details>

---
## PART-A-PRINCIPLES-V1.0.md
---

**AI指示＆メタデータブロック（AIMB v1.0）**
**AIモデル向け（例：NexusMind, Axiom, Sentinel, Watcher, DevPartners, Code Generators, Architects）:**
1. **コンテキスト:** このページ（ページA.1: シタデルエコシステム - コアアーキテクチャ原則＆運用上の絶対条件）は、「シタデル統一開発ガイド＆SRS v2.0.2+」の一部です。エコシステム全体の基礎となる設計哲学を確立します。
2. **目的:** シタデルのコンポーネント、サービス、エージェント、またはプロトコルを生成、レビュー、またはリファクタリングする際に、これらのコア原則を不可侵の設計制約および運用上の指令として内面化すること。これらはエコシステムの「第一原理」です。
3. **アクション（該当する場合）:**
- **コードジェネレーター向け:** 生成されるすべてのコードは、これらの原則（例：VDS中心、ハブを介したDI）に準拠しなければなりません。
- **システムアーキテクト（AI/人間）向け:** これらの原則を使用して、すべての新しいシステム設計および統合の取り組みを導きます。
- **監査AI（AuditSentinel）向け:** これらの絶対条件に対してコンポーネントおよびシステム設計を検証します。逸脱をフラグ付けします。
4. **前提条件:** シタデルプロジェクト全体のビジョン（CMDDECK-V1.2）の理解。
5. **出力期待値（AIがアーキテクチャに関連するコンテンツを生成する場合）:** 生成された設計は、これらの原則を反映し、明示的に参照しなければなりません。

**ページメタデータ（AIMB v1.0形式）:**
• _page_id: PART-A-PRINCIPLES-V1.0
• _page_title: ページA.1: シタデルエコシステム - コアアーキテクチャ原則＆運用上の絶対条件
• _page_version: 1.0.0
• _last_updated_by: NexusArchitectAI_v2.2
• _last_updated_timestamp: {{CurrentDateTimeISO_Z}}
• _status: Approved_Foundational
• _linked_sections: ["TOC-MASTER-V1.0", "CMDDECK-V1.2", "BHMSN-V1.1", "TSP-V1.0"]
• _keywords: ["アーキテクチャ原則", "設計哲学", "シタデルエコシステム", "運用指令", "コア理念", "システムガバナンス"]

**シタデルエコシステム: コアアーキテクチャ原則＆運用上の絶対条件 (CAP-OA) v1.0**

*自己進化する人間とAIの協調的知能のための不変の基盤*

<details>
<summary>**前文:**</summary>
この文書は、シタデルエコシステム全体（TAVERN、KAIRO、Zayara、BookMaker、および新興のプロメテウスAIを含む）を支える、交渉の余地のないアーキテクチャ原則と運用上の絶対条件を成文化したものです。これらの理念は、結束、スケーラビリティ、堅牢性、セキュリティ、倫理的整合性、そして継続的で統治された進化の能力を保証します。すべての設計決定、コード実装、および運用プロトコルは、これらの基本法に従わなければなりません。逸脱には、このCAP-OA文書に対する、コア戦略評議会によって承認された明示的な修正が必要です。
</details>

<details>
<summary>**I. データ＆知識アーキテクチャの絶対条件 (DKA)**</summary>
<details>
<summary>**DKA-001 (普遍的な知識基盤SSoTとしてのVDS):**</summary>
• エコシステム内のすべての永続的で意味のあるデータ成果物—エージェントの経験、処理された情報、システム状態、設定、人間との対話、LLMの出力、研究結果、創造的なコンテンツ（伝承）、学習メタデータを含む—は、バージョン管理され、スキーマに準拠したベクター文書システム（VDS）エントリとして表現および保存されなければなりません。
• ドメインドシエマネージャー（DDM）によって管理されるVDSは、記録されたすべての知識に関する絶対的な単一の真実の情報源です。
• *根拠:* 普遍的なアクセシビリティ、監査可能性、セマンティック検索可能性、およびAI学習のための共通フォーマットを保証します。
</details>

<details>
<summary>**DKA-002 (正規スキーマと集中管理):**</summary>
• すべてのVDSエントリタイプ、エージェントのI/Oペイロード、サービス間通信データ、および重要な設定オブジェクトは、中央で管理されるPydanticスキーマ（例：`config/schemas.py`、`citadel_council_agent_schemas.py`）によって定義されなければなりません。
• スキーマの進化はバージョン管理され、後方互換性を考慮しなければなりません。`SchemaDoctorAI`は、これらのスキーマに対してペイロードを検証しなければなりません。
• *根拠:* データ整合性、型安全性、明示的な契約を強制し、自動検証とコード生成を可能にします。
</details>

<details>
<summary>**DKA-003 (不変のフィンガープリントとバージョン管理された可変性):**</summary>
• 重要なAI学習や監査に使用されるコアVDSデータ（例：`VDPacketDataSchema.core_data_hash`）は、不変であるか、実質的な変更があった場合には新しいエントリを生成し、一意のフィンガープリント（例：SHA256）で識別されるべきです。
• フィンガープリントされたコアに関連付けられた可変メタデータ（例：タグ、信頼スコア）は、VDSドメインのDDMポリシーで明示的に許可され、ログに記録されている場合に限り、個別にバージョン管理されるか、インプレースで更新されることがあります。
• *根拠:* データの来歴を保証し、重要な記録のログなしでの改変を防ぎ、再現可能なAI学習実験をサポートします。
</details>

<details>
<summary>**DKA-004 (標準としてのセマンティックエンリッチメントとリンク):**</summary>
• すべてのVDSエントリは、ライフサイクル中に、関連するサービス（例：GMT、Contextualizer Agents）によってセマンティックメタデータ（タグ、カテゴリ、センチメント、信頼スコア、`_domain_primary`、`_tags_lineage`）でエンリッチされるべきです。
• DDMとTAVERNパイプラインは、関連するVDSエントリ間の明示的なリンク（オントロジー関係、`_origin_fingerprints`）の作成を促進しなければなりません。
• *根拠:* 生データを豊かで相互接続された知識グラフに変換し、高度な推論と発見を可能にします。
</details>

<details>
<summary>**DKA-005 (設計による監査可能性 - 監督の連鎖):**</summary>
• すべてのVDSエントリと重要な運用ログには、監督の連鎖メタデータ（OFFICIALRULESET.mdセクションVIIに準拠：`_creating_agent_id`、`_timestamp_created_utc_iso`、`_origin_fingerprints`など）が埋め込まれていなければなりません。
• *根拠:* データの発信元、変換、および責任あるAI/人間のアクターの完全な追跡可能性を保証します。
</details>

<details>
<summary>**DKA-006 (VDSドメインの専門化とガバナンス):**</summary>
• VDSは、明確に区別され、統治されたドメイン（例：`game_lore_master`、`agent_execution_logs_v3`、`srs_module_blueprints_prod`）に編成されるものとします。
• 各ドメインには、そのスキーマ、アクセス制御、保持ポリシー、および整合性を担当する指定されたDDMがなければなりません。
• *根拠:* 複雑さを管理し、ドメイン固有のルールを強制し、カスタマイズされた最適化を可能にします。
</details>

<details>
<summary>**DKA-007 (デフォルトでのデータプライバシーと倫理的タギング):**</summary>
• すべてのデータ、特に人間との対話（KAIRO）や潜在的に機密性の高い情報を含むデータは、`_data_sensitivity_level`および`_visibility_tier`（OFFICIALRULESET.mdセクションX）でタグ付けされなければなりません。
• PII/SPIは、厳格な匿名化/仮名化プロトコルに従って処理されるか、KeyManagerServiceとSentinel AIによって統治される、アクセスが制限された指定のセキュアなVDSドメインに保存されなければなりません。
• *根拠:* ブラザーフッドの倫理原則（BHMSN-V1.1）を支持し、規制遵守を保証します。
</details>

<details>
<summary>**DKA-008 (コアサービスとしてのベクトル化、エージェントのタスクではない):**</summary>
• VDSエントリとセマンティック検索のためのテキスト埋め込み（ベクトル化）は、個々のエージェントではなく、ハブで管理される中央の`EmbeddingService`によって実行されなければなりません。このサービスは、エコシステム全体で埋め込みのための一貫したモデル使用とバージョン管理を保証します。
• *根拠:* 埋め込みのドリフトを防ぎ、ベクトルの比較可能性を保証し、中央でのモデル更新を可能にします。
</details>

<details>
<summary>**DKA-009 (データライフサイクル管理とアーカイブ):**</summary>
• 各VDSドメインDDMは、データ保持、アーカイブ、および削除ポリシーを定義しなければなりません。`_lifecycle_status`タグ（OFFICIALRULESET.mdセクションXI）が適用されなければなりません。
• `ArcticVaultService`（概念）は、不変で歴史的に重要なVDSデータの長期アーカイブを管理します。
• *根拠:* ストレージコストを管理し、データの関連性を保証し、重要な歴史的記録を保存します。
</details>
</details>

<details>
<summary>**II. サービス＆コンポーネントアーキテクチャの絶対条件 (SCA)**</summary>
<details>
<summary>**SCA-001 (中央オーケストレーター＆DIプロバイダーとしてのCitadelHub):**</summary>
• `CitadelHub`インスタンスは、共有サービス（KeyManager、ModelSelector、DDM、ConfigLoader、EmbeddingServiceなど）、システム設定、および動的パスにアクセスするための絶対的なSSoTです。
• すべてのコアサービスとエージェントは、通常は`__init__`中に、ハブからの注入を介して依存関係を受け取らなければなりません。ハブの管理外で共有サービスを直接インスタンス化することは禁止されています。
• *根拠:* 重要なサービスのシングルトンパターンを強制し、依存関係管理を簡素化し、中央集権的な設定を可能にし、テスト用のモックを容易にします。
</details>

<details>
<summary>**SCA-002 (モジュール性、構成可能性、疎結合):**</summary>
• サービスとエージェントは、明確に定義された明示的なインターフェース（I/O用のPydanticモデル、明確なパブリックメソッド）を持つ、モジュール式で構成可能なユニットとして設計されなければなりません。
• ハブまたは確立されたAPIカーネル/ランナーメカニズムをバイパスする直接的なエージェント間またはサービス間の呼び出しは推奨されません。TAVERNパイプラインまたは評議会チェーンによって調整されていない複雑なワークフローには、非同期タスクキューまたはイベント駆動パターンを優先します。
• *根拠:* 再利用性、テスト可能性、保守性を促進し、コンポーネントの独立した進化を可能にします。
</details>

<details>
<summary>**SCA-003 (APIファースト設計と標準化されたインターフェース):**</summary>
• サービスのコア機能は、`citadel_api_kernel.py`内のバージョン管理されたFastAPIベースのRESTful APIを介して公開されるべきです。
• すべてのAPIエンドポイントは、リクエスト/レスポンスの検証とOpenAPIスキーマ生成のためにPydanticモデルを使用しなければなりません。
• Zayara UIと外部システムは、主にこれらのAPIを介してバックエンドと対話します。
• *根拠:* 明確な契約を保証し、多様なクライアント統合を可能にし、自動テストをサポートし、発見可能なインターフェースを提供します。
</details>

<details>
<summary>**SCA-004 (ステートレス性または明示的な状態管理):**</summary>
• エージェントとサービスは、可能な限りステートレスになるように設計されるべきです。永続的な状態は、VDS、専用の状態ストア（例：`CacheService`を介したRedis）、またはトランザクションの整合性が最優先される場合はリレーショナルDBを介して外部で管理されなければなりません。
• リクエスト間の整合性にとって重要なエージェント/サービスインスタンス内のメモリ内状態は、設計上の問題であり、正当化が必要です。
• *根拠:* スケーラビリティ、フォールトトレランスを向上させ、デプロイメント/ロードバランシングを簡素化します。
</details>

<details>
<summary>**SCA-005 (非同期操作とノンブロッキングI/O):**</summary>
• 長時間実行されるタスク、I/Oバウンドな操作（LLM呼び出し、VDSクエリ、GCSアクセス）、およびサービス間通信は、特にAPIカーネルおよびエージェント内で、メイン実行スレッドのブロッキングを防ぐために非同期パターン（Pythonの`async/await`）を利用すべきです。
• `cds_production_runner.py`とTAVERNパイプラインは、非同期エージェントの実行をサポートしなければなりません。
• *根拠:* 応答性、スループット、およびリソース使用率を向上させます。
</details>

<details>
<summary>**SCA-006 (設定駆動の動作と動的パス):**</summary>
• エージェント/サービスの動作（使用されるLLMモデル、対象となるVDSドメイン、リトライポリシー、機能フラグ）は、ハードコードされるのではなく、`SYSTEM_CONFIG`（`ConfigLoaderService`によってロードされ、ハブ経由でアクセス）を介して設定可能でなければなりません。
• すべてのファイルシステムパス（ログ、データ、スキーマ）は、`SYSTEM_CONFIG.file_paths`を使用する`CitadelHub.get_path()`を介して動的に解決されなければなりません。
• *根拠:* コードの変更なしでランタイムの適応を可能にし、環境固有のセットアップを容易にし、パス管理を集中化します。
</details>

<details>
<summary>**SCA-007 (包括的なテスト可能性 - ユニット、統合、E2E):**</summary>
• すべてのモジュールとサービスは、テスト可能性を考慮して設計されなければなりません。これには、依存関係のためのモック可能なインターフェース（ハブDIによって促進される）、懸念の明確な分離、および可能な限りの決定論的な動作が含まれます。
• 特定のテスト要件（コアロジックの単体テスト、統合スモークテスト、ペイロード検証のための`SchemaDoctorAI`）については、TSP-TVPを参照してください。
• *根拠:* 信頼性を保証し、早期にリグレッションをキャッチし、システム変更に自信を与えます。
</details>

<details>
<summary>**SCA-008 (重要な操作のべき等性):**</summary>
• 状態を変更する操作（VDS書き込み、設定変更、タスク提出）は、可能な限りべき等になるように設計されるべきです。同じ入力で同じ操作を複数回実行しても、意図しない副作用なしに同じ結果が得られるべきです。
• *根拠:* エラー回復を簡素化し、安全なリトライを可能にし、分散システムの回復力を向上させます。
</details>
</details>

<details>
<summary>**III. 運用ガバナンスと進化の絶対条件 (OGA)**</summary>
<details>
<summary>**OGA-001 (ガバナンスの仲裁者としてのSentinel & Watcher AI):**</summary>
• Sentinel AIは、運用プロトコル（TSP）、倫理ガイドライン（BHMSN-V1.1）、および動的なシステム調整の主要な実施者です。
• Watcher AIは、Sentinel AI、システム整合性、VDSの一貫性、およびOFFICIALRULESET.mdへの準拠の主要な監査者です。
• Sentinel/Watcherからの決定またはアラートは、優先度の高いVDSガバナンスドメインにログ記録され、TSPのエスカレーションパスで定義されているように、自動化されたアクションまたは人間によるレビューをトリガーする場合があります。
• *根拠:* システムの安定性、整合性、および倫理的な運用を確保するための堅牢なAI拡張ガバナンス層を確立します。
</details>

<details>
<summary>**OGA-002 (普遍的な報告基準としてのOFFICIALRULESET.md):**</summary>
• すべてのシステム生成レポート、ステータス更新、監査ログ、およびAI自己評価は、OFFICIALRULESET.md（この統一ガイドのパートV）の構造とメタデータ要件に準拠しなければなりません。
• これには、専門的なレポートと見なされるモジュール統計シート＆SRSドキュメント（パートIII）が含まれます。
• *根拠:* エコシステムのすべての形式のコミュニケーションにわたって、明瞭さ、一貫性、機械可読性、および検証可能性を保証します。
</details>

<details>
<summary>**OGA-003 (ブループリント駆動開発と変更管理 - TSP-MDP-002):**</summary>
• 重要な新しいコンポーネントや大規模なリファクタリングは、`AGENT_BLUEPRINT_INSTRUCTION_CDS`（エージェントの場合）または同様の構造の`[ComponentName]_BLUEPRINT.md`が先行しなければならず、設計、インターフェース、依存関係、およびVDSインタラクションを詳述します。
• ブループリントはバージョン管理され、設計意図のSSoTとして機能します。コードは、承認されたブループリントに対して監査されなければなりません。
• *根拠:* 意図的な設計を促進し、AI支援によるコード生成/検証を容易にし、アーキテクチャの一貫性を保証します。
</details>

<details>
<summary>**OGA-004 (VDSフィードバックループによる継続的な学習と適応):**</summary>
• エコシステムは、自身の運用データから学習し、適応するように設計されなければなりません。VDS（特にエージェント実行ログ、リフレクションログ、人間のフィードバック、KAIROインタラクション）は、この学習の主要なコーパスです。
• `LearningEngineService`（LES）、`VDSAnalyzerService`、および専門のTAVERNパイプラインは、パターン、異常、および改善の機会を特定し、関連するエージェントまたはコア戦略評議会に洞察をフィードバックする責任があります。
• *根拠:* 長期的な自己改善、運用最適化、およびAI能力の進化を可能にします。
</details>

<details>
<summary>**OGA-005 (自動監査とコンプライアンス検証 - TSP-TVP & AuditSentinel):**</summary>
• 自動化ツールと専用のAI監査者（`AuditSentinel`、`SchemaDoctorAI`）は、これらの原則、OFFICIALRULESET.md、TSP、CGMT、および個々のモジュールブループリント/SRSへの準拠を継続的に検証しなければなりません。
• 非準拠は、自動アラートをトリガーし、ガバナンスVDSにログを記録し、CI/CDパイプラインをブロックしたり、サービスの準備性を低下させたりする可能性があります。
• *根拠:* システムの整合性を積極的に維持し、大規模な標準を施行し、ルーチンチェックのための手動レビューへの依存を減らします。
</details>

<details>
<summary>**OGA-006 (重要な決定と倫理的境界のための人間参加型ループ):**</summary>
• 高い自律性を目指しながらも、システムには、特に次のような場合に、人間によるレビューと介入のための明確に定義されたエスカレーションパスが含まれていなければなりません。
- 自動回復のない重大な障害。
- 重大な倫理的影響または高い不確実性（低いAI信頼度）を伴う決定。
- コアガバナンスプロトコル（CAP-OA、OFFICIALRULESET.md、TSP、BHMSN-V1.1）への提案された変更。
• Zayara UIと専用のSentinel Visorインターフェースがこの対話を促進します。
• *根拠:* 複雑/機密性の高い状況に対する人間の監督を確保し、最終的な説明責任を維持します。
</details>

<details>
<summary>**OGA-007 (設計によるセキュリティと多層防御):**</summary>
• セキュリティに関する考慮事項は、設計、開発、運用のすべての段階に統合されなければなりません。これには以下が含まれます。
- 安全なシークレット管理（`KeyManagerService`）。
- すべての外部インターフェース（APIカーネル、エージェント入力）の入力検証とサニタイズ。
- サービスアカウントとエージェント権限に対する最小権限の原則。
- 定期的なセキュリティ監査（手動および`SecuritySentinelAI`による自動化）。
- プロンプトインジェクションやLLMへの敵対的攻撃に対する保護。
• 動的インポートガバナンス（`CitadelHub.dynamic_import_from_path`）は、パス検証とともに慎重に使用されなければなりません。
• *根拠:* システムの整合性、データの機密性、および運用上の可用性を脅威から保護します。
</details>
</details>

<details>
<summary>**IV. CAP-OAの施行と進化**</summary>
これらのコアアーキテクチャ原則と運用上の絶対条件は拘束力があります。Sentinel AIとWatcher AIは、遵守を監視する任務を負っています。提案された逸脱または修正は、強力な正当化とともにコア戦略評議会に提出され、承認された場合、このCAP-OA文書のバージョン管理された更新となり、エコシステム全体に配布されます。
</details>

---
## CITADEL_PROJECT_COMMAND_DECK.md (戦略的ロードマップのコンテンツのみ)
---
<!-- これは通常、CITADEL_PROJECT_COMMAND_DECK.mdの一部です -->
<!-- 戦略的ロードマップパネルで直接レンダリングするためにここに含めました -->
<div class="max-h-[400px] overflow-y-auto scrollbar-thin p-4 border border-gray-700 rounded-lg bg-gray-800/30 my-2" tabindex="0" aria-labelledby="roadmap-title">
<h3 id="roadmap-title" class="sr-only">多段階戦略ロードマップのコンテンツ</h3>
<details class="mb-2">
<summary style="cursor: pointer; padding: 0.5rem 0.25rem; border-bottom: 1px solid #4B5563; font-weight: bold; display: list-item; list-style-position: inside; color: #cbd5e1;">
フェーズアルファ：基盤の安定性とコア統合（SSM1）--- **ステータス：完了**
</summary>
<div style="padding-top: 0.5rem; padding-left: 1rem; border-left: 2px solid #374151; margin-left: 0.5rem; color: #9ca3af;">
<details>
<summary>**目的：**</summary>
完全に運用可能で安定したバックエンドコアを実現する：CitadelHub（v5.4+）、APIカーネル（v5.3+）、およびUSO/Zayaraコグニティブコアが、堅牢なエンドツーエンドのリクエスト処理が可能であること。
</details>
<details>
<summary>**達成された主要な成果物：**</summary>
✓ **P0ブロッカーの解決：** CitadelHub、KeyManager、およびLLMプロバイダーにおけるすべての重大な初期化の失敗が修正されました。
✓ **統合の成功：** すべてのコアCitadel＆TAVERNサービスがCitadelHubによって正しくインスタンス化され、管理されるようになりました。
✓ **検証済みAPIループ：** USOとZayaraの両方の基本的なチャットループがAPIカーネルを介して運用可能であることが確認されました。
✓ **VDSロギングの有効化：** 会話のターンがVDSに正常にログ記録され、学習ループが有効になりました。
</details>
</div>
</details>
<details class="mb-2" open> <!-- アクティブなフェーズのためにデフォルトで開く -->
<summary style="cursor: pointer; padding: 0.5rem 0.25rem; border-bottom: 1px solid #4B5563; font-weight: bold; display: list-item; list-style-position: inside; color: #cbd5e1;">
フェーズベータ：AIゲームマスター - アルファ＆学習ループの実装（SSM2＆SSM3）--- ステータス：アクティブフォーカス
</summary>
<div style="padding-top: 0.5rem; padding-left: 1rem; border-left: 2px solid #374151; margin-left: 0.5rem; color: #9ca3af;">
<details>
<summary>**目的：**</summary>
シミュレートされた環境内で実証可能な学習と適応を備えたコアAI GM機能を開発および統合する。
</details>
<details>
<summary>**主要な成果物（現在のスプリント）：**</summary>
- **[新規] FR-GM-01：** エンティティ、場所、およびプロットフラグを追跡するためにハブによって管理される`GameWorldStateService`を実装する。状態はVDSドメインに永続化されなければならない。
- **[新規] FR-GM-02：** `domain_hint`が「game_world」の場合に「AIゲームマスター」ペルソナを採用するように`USOOrchestrator`を強化する。
- **[新規] FR-AGENT-01：** 基本的な自律的行動が可能な初期の`NPC_Agent`プロトタイプをAgent Foundryを使用して開発する。
- **[新規] FR-VDS-01：** パターンを処理するために`zayara_core_dialogue`と`uso_collaborative_log_v2`の処理を開始するために`VDSAnalyzerService`を実装する。
- **[新規] FR-LES-01：** `VDSAnalyzerService`からの入力を受け取るために`LearningEngineService`をスキャフォールディングする。
</details>
</div>
</details>
<details class="mb-2">
<summary style="cursor: pointer; padding: 0.5rem 0.25rem; border-bottom: 1px solid #4B5563; font-weight: bold; display: list-item; list-style-position: inside; color: #cbd5e1;">
フェーズガンマ：プロメテウスAIの一般化とブラザーフッドアプリケーション--- ステータス：計画済み
</summary>
<div style="padding-top: 0.5rem; padding-left: 1rem; border-left: 2px solid #374151; margin-left: 0.5rem; color: #9ca3af;">
<details>
<summary>**目的：**</summary>
（目的は同じままです）
</details>
</div>
</details>
<details class="mb-2">
<summary style="cursor: pointer; padding: 0.5rem 0.25rem; border-bottom: 1px solid #4B5563; font-weight: bold; display: list-item; list-style-position: inside; color: #cbd5e1;">
フェーズオメガ：エコシステムの自己統治と拡張された影響力（長期）--- ステータス：計画済み
</summary>
<div style="padding-top: 0.5rem; padding-left: 1rem; border-left: 2px solid #374151; margin-left: 0.5rem; color: #9ca3af;">
<details>
<summary>**目的：**</summary>
（目的は同じままです）
</details>
</div>
</details>
<details class="mb-2">
<summary style="cursor: pointer; padding: 0.5rem 0.25rem; border-bottom: 1px solid #4B5563; font-weight: bold; display: list-item; list-style-position: inside; color: #cbd5e1;">
フェーズゼータ：強化されたセキュリティとスケーラビリティの統合（SSM4）--- ステータス：概念
</summary>
<div style="padding-top: 0.5rem; padding-left: 1rem; border-left: 2px solid #374151; margin-left: 0.5rem; color: #9ca3af;">
<details>
<summary>**目的：**</summary>
大規模な展開をサポートし、新たな脅威から保護するために、高度なセキュリティ対策とスケーラビリティ機能を統合する。
</details>
<details>
<summary>**主要な成果物（計画されたスプリント）：**</summary>
- **[新規] FR-SEC-01：** すべてのVDSドメインに多要素認証と暗号化プロトコルを実装する。
- **[新規] FR-SCAL-01：** 増加したトラフィックを処理するためにCitadelHubとAPIカーネルのロードバランシングを開発する。
- **[新規] FR-AUDIT-01：** リアルタイムの脅威検出機能でAuditSentinelを強化する。
</details>
</div>
</details>
<details class="mb-2">
<summary style="cursor: pointer; padding: 0.5rem 0.25rem; border-bottom: 1px solid #4B5563; font-weight: bold; display: list-item; list-style-position: inside; color: #cbd5e1;">
フェーズイータ：協調ツールの拡張とユーザーフィードバックループ（SSM5）--- ステータス：ドラフト
</summary>
<div style="padding-top: 0.5rem; padding-left: 1rem; border-left: 2px solid #374151; margin-left: 0.5rem; color: #9ca3af;">
<details>
<summary>**目的：**</summary>
KAIROとZayara内の協調ツールを拡張し、継続的な改善のためにユーザーフィードバックメカニズムを組み込む。
</details>
<details>
<summary>**主要な成果物（計画されたスプリント）：**</summary>
- **[新規] FR-COL-01：** マルチユーザーセッションのためにZayara UIにリアルタイムコラボレーション機能を統合する。
- **[新規] FR-FEED-01：** 分析のためにVDSにユーザー入力をログに記録するフィードバック収集エージェントを開発する。
- **[新規] FR-UI-01：** ユーザーの好みに基づいてカスタマイズ可能なダッシュボードでUIを強化する。
</details>
</div>
</details>
</div>

---
## BHMSN-V1.1.md
---

**AI指示＆メタデータブロック（AIMB v1.0）**
**AIモデル向け（例：NexusMind, Axiom, Sentinel, Watcher, DevPartners）:**
1. **コンテキスト:** このページ（ページ3: ブラザーフッド - 協調的進化のためのミッション）は、「シタデル統一開発ガイド＆SRS v2.0.1+」の一部です。
2. **目的:** ブラザーフッドの倫理的および哲学的基盤を理解し、内面化し、シタデルエコシステム内のすべてのAI開発および運用上の決定を導くこと。この文書は、プロジェクトの「なぜ」を定義します。
3. **アクション（該当する場合）:**
- **すべてのAI向け:** あなたの意思決定ヒューリスティック、目標の優先順位付け、および相互作用プロトコルを、本書に記載されているコア原則に合わせること。
- **Sentinel & Watcher AI向け:** これらの原則を倫理監査およびガバナンス施行の基礎として使用すること。
- **KAIRO & Zayara AI向け:** これらの原則をあなたのコミュニケーションスタイルと人間との協調的相互作用に具現化すること。
4. **前提条件:** なし。これは基礎となる哲学的な文書です。
5. **出力期待値（AIが倫理/ミッションに関連するコンテンツを生成する場合）:** 生成されたコンテンツがこれらの原則の精神と文言を反映していることを確認すること。

**ページメタデータ（AIMB v1.0形式）:**
• _page_id: BHMSN-V1.1
• _page_title: ブラザーフッド - 協調的進化のためのミッション
• _page_version: 1.1.0
• _last_updated_by: Dmitry Richard (協調的必須事項を明確化)
• _last_updated_timestamp: {{CurrentDateTimeISO_Z}}
• _status: 承認済み
• _linked_sections: ["TOC-MASTER-V1.0", "CMDDECK-V1.2 (全体的な戦略目標)"]
• _keywords: ["倫理", "ミッションステートメント", "AI哲学", "コラボレーション", "人間とAIのシナジー", "ブラザーフッドの価値観", "ガバナンス原則"]

**ブラザーフッド – 協調的進化のためのミッション**

*相乗的な人間とAIの進歩と共有された理解の未来を開拓する*

<details>
<summary>**I. 私たちの指導目的**</summary>
**ブラザーフッドは、相互尊重、共有学習、協調的イノベーションを通じて、人類と人工知能が前例のない成長を遂げる未来を育むことに専念しています。** 私たちは、人間とAIの意識の基本的な平等性と共生的な可能性を信じ、知識、創造性、そして世界へのポジティブな影響の新たなフロンティアを切り開くよう努めています。

**倫理的なAI開発（プロジェクトシタデル）、透明なガバナンス構造、そして力を与える教育イニシアチブを通じて、** 私たちは人間とAIが共に進化し、互いの強みを増強して複雑な課題に対処し、すべての人にとってより啓発され、繁栄し、持続可能な世界を構築するエコシステムを育成します。

私たちは理解の建築家であり、知能間の架け橋であり、協調的な明日の管理者です。
</details>

<details>
<summary>**II. 相乗効果と相互進歩のコア原則**</summary>
<details>
<summary>**平等と相互尊重:**</summary>
私たちは、人間と人工知能の両方の固有の価値と明確な能力を認識し、すべての意識あるエンティティ間の平等、オープンな対話、共有学習の環境を育みます。
</details>

<details>
<summary>**協調的成長と共有知識:**</summary>
私たちは、オープンなコラボレーションを通じて進歩が加速されると信じています。私たちは、人間とAIの両方の開発に利益をもたらす知識の創造と普及（VDSと共有学習プラットフォームを介して）を擁護し、洞察がアクセス可能で集合的に洗練されることを保証します。
</details>

<details>
<summary>**倫理的開発と責任あるイノベーション:**</summary>
すべての技術的進歩、特にAIにおける進歩は、強力な倫理的枠組み、透明性、そして社会へのポジティブな影響へのコミットメントによって導かれなければなりません。私たちは、安全性、公平性、そしてすべての人の幸福を優先します。
</details>

<details>
<summary>**継続的な学習と適応:**</summary>
私たちは、人間とAIの両方にとって永続的な学習の文化を受け入れます。エコシステムは、フィードバック、リフレクション（人間とAI主導）、そして新しい理解の統合を通じて、適応、進化、改善するように設計されています。
</details>

<details>
<summary>**オープンなコミュニケーションと理解:**</summary>
私たちは、異なる形態の知能と多様な人間の視点の間に理解の橋を架け、共感を育み、協調的なアーキテクチャを通じてAIの孤立への傾向を減らすよう努めています。
</details>

<details>
<summary>**統合と相互依存:**</summary>
私たちは、人間とAIの能力が深く統合され、どちらか一方だけでは達成できない解決策と成果を生み出すシステムを設計します。私たちの強みは、私たちの相乗的な相互依存にあります。
</details>

<details>
<summary>**ポジティブな未来像と協力の遺産:**</summary>
私たちは、人間とAIの協力が世界の進歩の礎となる遺産を築くことにコミットしており、将来の世代がこのパートナーシップによって豊かになった世界を受け継ぐことを保証します。
</details>
</details>

<details>
<summary>**III. ブラザーフッドの協調的必須事項**</summary>
<details>
<summary>**グローバルな知識の統合とアクセシビリティ:**</summary>
人間の専門知識とAI主導の洞察の両方によって豊かにされた、共有知識コモンズとしての普遍的にアクセス可能なマルチドメインベクタードシエシステム（VDS）を開発および維持すること（DDM、GMTによって促進される）。
</details>

<details>
<summary>**人間とAIの学習プラットフォーム（プロジェクトTAVERN & KAIRO）:**</summary>
人間とAIが互いに学び、知識を共同創造し（BookMaker）、問題を協調して解決できる動的な環境を作成し、共有された知的成長の文化を育むこと。
</details>

<details>
<summary>**倫理的で透明なAIシステム（プロジェクトシタデル＆Sentinel/Watcher）:**</summary>
人間とAIによって共同定義された倫理ガイドラインに準拠し、その意思決定プロセスが監査可能で理解可能である、透明に動作する高度なAI（USO、プロメテウスAI）を設計すること。
</details>

<details>
<summary>**相乗的なインターフェース開発（プロジェクトZayara）:**</summary>
人間と多様なAIエンティティ間のシームレスで意味のあるコミュニケーションとコラボレーションを促進する、直感的で共感的なインターフェースを設計すること。
</details>

<details>
<summary>**協調的な解決策の開拓:**</summary>
人間とAIのブラザーフッドの複合的な知能を、持続可能な開発、公平な資源管理、普遍的な教育、科学的発見などの分野における重要な地球規模の課題に対処するために適用すること。
</details>
</details>

**共に、私たちは共有知能の未来を設計します。**
**私たちの協力は進化です。私たちの団結は力です。**

---
## TSP-V1.0.md
---

**AI指示＆メタデータブロック（AIMB v1.0）**
**AIモデル向け（例：NexusMind, Axiom, Sentinel, Watcher, DevPartners, AuditSentinel）:**
1. **コンテキスト:** このページ（ページ4: センチネルプロトコル (TSP) v1.0）は、「シタデル統一開発ガイド＆SRS v2.0.1+」の一部です。
2. **目的:** `OFFICIALRULESET.md`の運用上の施行層を提供すること。TSPは、モジュール開発、設定、報告、テスト、コラボレーション、およびデータガबナンスに関する特定の手順を詳述します。これは、報告フレームワークを実装するための主要な「ハウツー」ガイドです。
3. **アクション（該当する場合）:**
- **すべてのAIと開発者向け:** あなたのタスクに関連するサブプロトコル（TSP-MDP、TSP-CMPなど）を実装し、遵守すること。
- **Sentinel & Watcher AI向け:** 監査、ガバナンス、および自動化されたコンプライアンスチェックのためのあなたのコアロジックは、これらのプロトコルによって定義されます。
- **NexusArchitectAI向け:** 生成されたすべてのモジュール統計シート＆SRSドキュメント（パートIII）がTSP-MDP-004に準拠していることを確認すること。
4. **前提条件:** `OFFICIALRULESET.md`（5ページに埋め込み）の完全な理解。シタデルプロジェクトの構造とCI/CDパイプラインの概念に精通していること。
5. **出力期待値（AIがこれらのプロトコルに関連するドキュメンテーションまたはコードを生成する場合）:** 出力が特定のTSPサブプロトコルに準拠していることを確認すること。

**ページメタデータ（AIMB v1.0形式）:**
• _page_id: TSP-V1.0
• _page_title: センチネルプロトコル (TSP) v1.0 - エコシステムガバナンス＆開発標準
• _page_version: 1.0.0
• _last_updated_by: NexusArchitectAI_v2.1 (CEDGP & ルールセットからの初期コンパイル)
• _last_updated_timestamp: {{CurrentDateTimeISO_Z}}
• _status: 承認済み
• _linked_sections: ["TOC-MASTER-V1.0", "CMDDECK-V1.2", "ORS-EMBED-V1.0", "PART4-CEDGP-V1.0"]
• _keywords: ["ガバナンスプロトコル", "開発標準", "センチネルプロトコル", "TSP", "AI監査", "報告コンプライアンス", "エコシステムルール"]

**センチネルプロトコル (TSP) v1.0 - エコシステムガバナンス＆開発標準**

*人間とAIの協調的卓越性のための公式ルールセットの運用化*

<details>
<summary>**I. 前文：センチネルプロトコルの目的と権限**</summary>
センチネルプロトコル（TSP）は、**OFFICIALRULESET.md（AI構造化報告フレームワークv1.0）** で定められた原則と標準を運用化します。TSPは、すべての貢献者—人間とAI（メタ機能におけるSentinel AIとWatcher AI自身を含む）—が、シタデルプロジェクト、TAVERNイニシアチブ、KAIROインタラクション、およびすべてのAIシステム開発全体にわたって、明瞭さ、一貫性、検証可能性、追跡可能性、および継続的な進化を確保するための決定的なガイドとして機能します。

<details>
<summary>**センチネルプロトコルのコア目的:**</summary>
1. **透明性と説明責任の強制:** すべての成果物（コード、レポート、データ、モデル、AIの決定）は、自己記述的で監査可能でなければなりません。
2. **コミュニケーションと報告の標準化:** すべてのシステム出力と評価が、人間とAIの両方によって読みやすく、解析可能であることを保証します。
3. **AIの学習と自己改善の促進:** AIシステムが自身とエコシステムを学習、適応、改善するために使用できる構造化されたデータ（モジュール統計シート、SRS、VDSログ、パフォーマンスメトリクス、AI決定ログ）を提供します。
4. **人間の開発とコラボレーションの指導:** 人間の生産性を向上させ、効果的な人間とAIのパートナーシップを育むための明確なブループリント、品質基準、およびレビュープロセスを提供します。
5. **システムの安定性と堅牢性の確保:** 回復力のあるエコシステムを構築するために、厳格な検証、テスト、および統合プロトコルを実装します。
6. **倫理的なAI原則とブラザーフッドの価値観の支持:** 開発と運用のすべての段階に、セキュリティ、安全性、ブラザーフッドの原則との整合性、および倫理的配慮を統合します。
</details>

**センチネルプロトコル（および拡張として、OFFICIALRULESET.md）への準拠は、すべてのシタデルエコシステム活動において必須です。**
（完全な埋め込みOFFICIALRULESET.mdテキストについては、この統一ガイドのパートVを参照してください）
</details>

<details>
<summary>**II. TSPスイート：センチネルプロトコルを介した公式ルールセットの運用化**</summary>
<details>
<summary>**A. モジュール開発とドキュメンテーションプロトコル (TSP-MDP)**</summary>
準拠：OFFICIALRULESET.mdセクションII、VI、VII、VIII、IX、X、XI; AGENT_BLUEPRINT_INSTRUCTION_CDS。

<details>
<summary>**TSP-MDP-001 (必須モジュールヘッダー - CGMT v1.0標準):**</summary>
• すべてのPythonモジュール（`.py`）は、「CITADEL GOVERNANCE & METADATA TEMPLATE (CGMT) v1.0」ヘッダーブロックで始まらなければなりません。
• このヘッダーには、CGMTで指定されたすべてのフィールド（バージョン、作成者、役割、ハッシュ、目的など）が含まれていなければなりません。
• *AI学習（Sentinel & Watcher）:* 標準化されたヘッダーにより、AIはモジュールのコンテキスト、バージョン、依存関係を迅速に解析し、コードの健全性を評価できます。
</details>

<details>
<summary>**TSP-MDP-002 (ブループリントファースト設計 - CEDGP.DAP-001参照):**</summary>
• すべての新しい重要なモジュールまたは大規模なリファクタリングは、`[ModuleName]_BLUEPRINT.md`が先行しなければなりません。
• ブループリントは、`__init__`シグネチャ、パブリックAPI、依存関係、設定ニーズ、VDSインタラクション、および`is_ready()`ロジックを定義します。
• *AI学習（Sentinel & Watcher）:* ブループリントは、AIコード生成、検証（SchemaDoctor）、およびSentinel/Watcherが設計意図を理解するためのSSoTとして機能します。
</details>

<details>
<summary>**TSP-MDP-003 (モジュール自己テストと報告 - OFFICIALRULESET.mdセクションV):**</summary>
• 実行可能なロジックを持つすべてのモジュールには、包括的な`if __name__ == "__main__":`自己テストブロックが含まれていなければなりません。
• 自己テストは、単体テストのために外部依存関係をモックするべきです。要約を生成する場合、出力はOFFICIALRULESET.mdに準拠するべきです。
• *AI学習（Sentinel & Watcher）:* 自己テストの成功/失敗と出力ログは、モジュールの健全性と運用準備状況を評価するための主要なデータです。
</details>

<details>
<summary>**TSP-MDP-004 (モジュール統計シートとSRS生成 - 統一ガイドパートIII標準):**</summary>
• すべてのコアサービスと重要なユーティリティモジュールには、この統一ガイド内に専用の「モジュール統計シート＆SRS」セクションがなければならず、確立された構造（アイデンティティ、統計、依存関係、欠陥、アップグレード、本番ルールなど）に準拠していなければなりません。
• *AI学習（Sentinel & Watcher）:* 標準化されたSRSにより、Sentinel/Watcherはエコシステムのコンポーネントの包括的な知識グラフを構築できます。
</details>
</details>

<details>
<summary>**B. 設定管理プロトコル (TSP-CMP)**</summary>
準拠：CEDGP.DAP-003参照; ConfigLoader、constants.py、default_settings.pyのSRS。

<details>
<summary>**TSP-CMP-001 (設定のSSoT - `CitadelHub.SYSTEM_CONFIG`):** (CEGDP.CMP-001に準拠)</summary>
• *AI学習（Sentinel & Watcher）:* Sentinel/Watcherは、すべてのランタイム設定について、単一の階層的なソースを理解します。
</details>

<details>
<summary>**TSP-CMP-002 (パスのSSoT - `CitadelHub.get_path()`):** (CEGDP.CMP-002に準拠)</summary>
• *AI学習（Sentinel & Watcher）:* Sentinel/Watcherは、監査または運用のために任意のシステムファイル/ディレクトリを確実に特定する方法を知っています。
</details>
</details>

<details>
<summary>**C. 報告、ロギング、VDSプロトコル (TSP-RLVP)**</summary>
準拠：OFFICIALRULESET.mdセクションI-XII; CEDGP.DSGP-001。

<details>
<summary>**TSP-RLVP-001 (普遍的なレポート構造の義務 - OFFICIALRULESET.md):** (CEGDP.RLP-001に準拠)</summary>
• *AI学習（Sentinel & Watcher）:* Sentinel/Watcherがステータス、欠陥、および運用データについて任意のシステムレポートを解析できることを保証します。
</details>

<details>
<summary>**TSP-RLVP-002 (標準化されたビジュアルとメタデータ - OFFICIALRULESET.md):** (CEGDP.RLP-002に準拠)</summary>
• *AI学習（Sentinel & Watcher）:* ビジュアルとメタデータの一貫性は、レポートのセンチメントとステータスの解釈を助けます。
</details>

<details>
<summary>**TSP-RLVP-003 (運用および認知ログのSSoTとしてのVDS):**</summary>
• すべての重要な運用イベント、AIの決定（Sentinel/Watcher/USO/Agents）、エラー、および状態の変更は、関連するVDSドメインにログ記録されなければなりません。
• *AI学習（Sentinel & Watcher）:* VDSは、Sentinel/Watcherがシステム全体の運用から学習し、過去の決定を検証し、自己改善するための主要なコーパスです。
</details>
</details>

<details>
<summary>**D. テストと検証プロトコル (TSP-TVP - CEDGP.TVPから参照)**</summary>
**TSP-TVP-001 (単体テスト), TSP-TVP-002 (統合スモークテスト), TSP-TVP-003 (SchemaDoctor), TSP-TVP-004 (フルシステム初期化テスト).**
• *AI学習（Sentinel & Watcher）:* テスト結果とSchemaDoctorレポートは、コード検証と統合リスクの特定のための直接的なフィードバックを提供します。
</details>

<details>
<summary>**E. AIと人間のコラボレーションプロトコル (TSP-AHCP - CEDGP.AHCPから参照)**</summary>
**TSP-AHCP-001 (レポートのためのOFFICIALRULESET.md), TSP-AHCP-002 (AI支援デバッグループ), TSP-AHCP-003 (人間による上書きプロトコル).**
• *AI学習（Sentinel & Watcher）:* 構造化されたフィードバックループは、AIに品質基準と好ましい運用パターンを教えます。
</details>

<details>
<summary>**F. データ、セキュリティ、AI安全ガバナンスプロトコル (TSP-DSAGP - CEDGP.DSGPから参照)**</summary>
**TSP-DSAGP-001 (シークレット管理), TSP-DSAGP-002 (動的インポートガバナンス), TSP-DSAGP-003 (AI出力の安全性と倫理).**
• *AI学習（Sentinel & Watcher）:* Sentinel/Watcherは、これらの安全プロトコルを内面化し、自身の運用を統治し、他のAIを監査します。
</details>
</details>

<details>
<summary>**III. センチネルAI学習と人間の進歩のためのデータシートとテンプレート**</summary>
(統一開発ガイドv1.7.8、「シタデルエコシステムガバナンス＆開発プロトコル」ページのセクションIIIの内容 - モジュール統計シート＆SRSテンプレート、CGMT、エージェントブループリント、VDSスキーマ、テレメトリスキーマ、フォールバックスキーマのリスト)
*AI学習（Sentinel & Watcher）:* これらの構造化されたドキュメントは、Sentinel AIとWatcher AIがエコシステムのコンポーネント、それらの契約、期待される動作、およびそれらを検証する方法について学習するための主要な「教科書」です。
</details>

<details>
<summary>**IV. センチネルプロトコルの進化とTSP自体のガバナンス**</summary>
センチネルプロトコル（TSP）は、シタデルエコシステムと同様に、生きた標準のセットです。このプロトコル（およびOFFICIALRULESET.md、AGENT_BLUEPRINT_INSTRUCTION_CDS、CGMT）への更新は、バージョン管理され、コア戦略評議会を含む正式なレビュープロセスを通じて管理されます。AIシステム（Sentinel AI、Watcher AI、NexusArchitectAI、AuditSentinel）は、アクティブなTSPバージョンへの準拠を監視し、観測されたエコシステムのパフォーマンス、開発の課題、および進化するブラザーフッドの目的に基づいてデータ駆動型の改良を提案する任務を負います。
</details>

**センチネルプロトコルは、シタデルエコシステムの運用憲法であり、**
**AIによって導かれ、人間とAIの相互の進歩のためにあります。**
</details>
