# Citadelサービス利用ガイド

このドキュメントは、Citadelエコシステム内の様々なサービスの使用方法について説明します。

## faiss_management_service.py

`FAISSManagementService`は、ベクトルインデックスを管理するための高レベルAPIを提供します。このサービスは、低レベルのFAISS操作を`VectorStorageService`に委任し、オプションで`GlobalMetadataTracker`と統合して、ベクトルに関連付けられた豊富なメタデータを管理できます。

### 主な機能

- **add_vector**: 指定されたFAISSインデックスにベクトルを追加します。
- **search_vectors**: 指定されたインデックスで最も類似したベクトルを検索します。
- **reconstruct_vector**: フィンガープリントを使用してインデックスからベクトルを再構築します。
- **get_vector_metadata**: 特定のベクトルのメタデータを取得します。
- **update_vector_metadata**: 特定のベクトルのメタデータを更新します。
- **remove_vector**: インデックスからベクトルを削除します。

### 使用例（概念）

```python
import numpy as np
from vector_storage_service import VectorStorageService
from faiss_management_service import FAISSManagementService

# サービスの初期化（CitadelHub経由での取得を想定）
# vss = hub.get_service("VectorStorageService")
# fms = hub.get_service("FAISSManagementService")

# スタンドアロンでの概念的な初期化
# 実際のシステム設定とVSSインスタンスが必要
system_config = {
    "paths": {
        "faiss_service_paths": {
            "default_faiss_root_dir": "./faiss_indexes"
        }
    },
    "default_faiss_index_config": {
        "vector_dim": 1536,
        "metric_type": "L2"
    }
}
vss = VectorStorageService(vector_indexes_base_dir="./faiss_indexes")
fms = FAISSManagementService(system_config=system_config, vector_storage_service=vss)

if fms.is_ready():
    index_name = "my_test_index"
    fingerprint = "doc_001"
    vector = np.random.rand(1, 1536).astype("float32")
    metadata = {"source": "test_document.txt"}

    # ベクトルの追加
    added = fms.add_vector(index_name, fingerprint, vector, metadata)
    if added:
        print(f"ベクトル '{fingerprint}' がインデックス '{index_name}' に追加されました。")

    # ベクトルの検索
    results = fms.search_vectors(index_name, vector, k=1)
    if results:
        print(f"検索結果: {results}")

    # メタデータの取得
    retrieved_metadata = fms.get_vector_metadata(index_name, fingerprint)
    if retrieved_metadata:
        print(f"取得されたメタデータ: {retrieved_metadata}")

else:
    print("FAISS Management Serviceの準備ができていません。")

```
---

## summarizer_service.py

`SummarizerService`は、言語モデル（LLM）を使用してテキストの簡潔な要約やダイジェストを生成するための堅牢で拡張可能なインターフェースを提供します。設定可能なリトライロジック、キャッシング、詳細なメトリクスロギング、マルチプロバイダーサポートの基盤を備えています。

### 主な機能

- **generate_digest**: 与えられたテキストの要約ダイジェストを生成します。要約プロセスを制御するためのさまざまなオプションパラメータを受け入れます。
- **is_available**: サービスが利用可能で準備ができているかどうかをチェックします。

### 使用例（概念）

```python
# from summarizer_service import SummarizerService
# from citadel_hub import CitadelHub # Mock

# サービスの初期化（CitadelHub経由での取得を想定）
# hub = CitadelHub() # 設定済みのハブインスタンス
# summarizer = hub.get_service("SummarizerService")

# if summarizer and summarizer.is_available():
#     text_to_summarize = (
#         "ジェイムズ・ウェッブ宇宙望遠鏡（JWST）は、主に赤外線天文学を行うために設計された宇宙望遠鏡です。"
#         "宇宙で最大の光学望遠鏡として、その大幅に改善された赤外線解像度と感度により、"
#         "ハッブル宇宙望遠鏡では観測するには古すぎたり、遠すぎたり、暗すぎたりする天体を見ることができます。"
#     )
#
#     summary, metrics = summarizer.generate_digest(
#         text_to_summarize=text_to_summarize,
#         use_cache=False
#     )
#
#     print("--- 生成された要約 ---")
#     print(summary)
#     print("\n--- メトリクス ---")
#     print(metrics)
#
# else:
#     print("Summarizer Serviceが利用できません。")

```
---

## global_tracker_service.py

`GlobalMetadataTracker`は、Citadelエコシステム内のすべての思考ベクトルのメタデータのライフサイクルを管理します。SQLiteデータベースを使用して、スキーマ定義されたコアフィールドと動的なキーバリューフィールドの両方を扱います。

### 主な機能

- **insert_new_vector**: 新しいベクトルレコードをメインのメタデータテーブルに挿入します。
- **bulk_update_fields**: ベクトルの複数のメタデータフィールドを一度に更新します。
- **get_metadata**: 指定されたベクトルフィンガープリントのすべてのメタデータを取得します。
- **print_metadata_summary**: ベクトルのメタデータの整形された要約を出力します。
- **build**: 新しいベクトルのメタデータを構築して挿入するためのヘルパーメソッドです。

### 使用例（概念）

```python
# from global_tracker_service import GlobalMetadataTracker
# from citadel_hub import CitadelHub # Mock

# サービスの初期化（CitadelHub経由での取得を想定）
# hub = CitadelHub() # 設定済みのハブインスタンス
# gmt = hub.get_service("GlobalMetadataTracker")

# スタンドアロンでの概念的な初期化
# db_path = "./gmt_database.db"
# gmt = GlobalMetadataTracker(db_path=db_path)

# if gmt.is_ready():
#     fingerprint = "gmt_test_vector_01"
#     initial_data = {
#         "raw_text": "これはGMTのテストです。",
#         "source": "test_script",
#         "domain": "testing",
#         "tags": ["gmt", "test"]
#     }
#
#     # 新しいベクトルの挿入
#     gmt.insert_new_vector(fingerprint, initial_data)
#     print(f"ベクトル '{fingerprint}' が挿入されました。")
#
#     # メタデータの更新
#     updates = {
#         "status": "processed",
#         "importance_score": 0.9,
#         "dynamic_agent_id": "agent_x" # 動的フィールド
#     }
#     gmt.bulk_update_fields(fingerprint, updates)
#     print(f"ベクトル '{fingerprint}' が更新されました。")
#
#     # メタデータの取得と表示
#     metadata = gmt.get_metadata(fingerprint)
#     if metadata:
#         gmt.print_metadata_summary(fingerprint)
#
#     gmt.close()
#
# else:
#     print("Global Metadata Trackerの準備ができていません。")

```
---

## memory_context_service.py

`MemoryContextService`は、AIエージェントのためのリッチな文脈的プロンプトの組み立てを調整する、より複雑なサービスです。さまざまなデータサービスを統合して、AIエージェントの対話のための関連性があり、一貫性のある、連続的なコンテキストを提供します。

### 主な機能

- **build_full_context**: このサービスのコアメソッドです。プロンプト、エージェントID、ユーザーID、セッションID、その他のメタデータを受け取り、AIのための詳細な文脈ブロックを構築します。
- **is_text_growth_related**: テキストが成長に関連しているかどうかをチェックします。
- **get_curiosity_question_text**: 好奇心を刺激する質問を取得します。
- **inject_ai_specific_external_reflection**: 外部からのリフレクションをシステムに注入します。
- **process_batch_external_reflections**: 外部からのリフレクションのバッチを処理します。
- **get_enriched_context_basic**: クエリに対して基本的なエンリッチ化されたコンテキストを取得します。

### 使用例（概念）

```python
# CitadelHubと他のモックサービスをインポートしたと仮定
# from citadel_hub import CitadelHub
# from ... (mock services)

# サービスの初期化（CitadelHub経由での取得を想定）
# hub = CitadelHub() # 設定済みのハブインスタンス
# mcs = hub.get_service("MemoryContextService")

# スタンドアロンでの概念的な初期化
# このサービスは多くの他のサービスに依存しているため、
# スタンドアロンでの使用は非常に複雑です。
# 以下は、主要なメソッドの呼び出し方を示すための概念的なスニペットです。

# if mcs and mcs.is_ready():
#     prompt = "プロジェクトアルファについて詳しく教えてください。"
#     ai_agent_id = "agent_007"
#     user_id = "user_01"
#     session_id = "session_12345"
#
#     full_context_prompt = mcs.build_full_context(
#         prompt=prompt,
#         ai_agent_id=ai_agent_id,
#         user_id=user_id,
#         session_id=session_id
#     )
#
#     print("--- 完全なコンテキストプロンプト ---")
#     print(full_context_prompt)
#
# else:
#     print("Memory Context Serviceの準備ができていないか、初期化に失敗しました。")

```
---

## vector_storage_service.py

`VectorStorageService`は、FAISSベースのベクトルメモリの管理を担当し、埋め込みの保存、検索、メタデータ、および信頼性の高いベクトル再構築に関連する低レベルの操作を処理します。

### 主な機能

- **add_vector**: ベクトルを一意のフィンガープリントとメタデータとともにFAISSインデックスに追加します。
- **search_vectors**: インデックス内で類似のベクトルを検索します。
- **get_vector_by_fingerprint**: フィンガープリントを使用してベクトルを取得します。
- **get_metadata**: ベクトルのメタデータを取得します。
- **update_metadata**: ベクトルのメタデータを更新します。
- **remove_vector**: インデックスからベクトルをソフトまたはハードデリートします。
- **purge_deleted**: ソフトデリートされたすべてのベクトルを完全に削除します。
- **count_vectors**: インデックス内のベクトル数をカウントします。
- **list_fingerprints**: インデックス内のすべてのベクトルフィンガープリントをリストします。

### 使用例（概念）

```python
import numpy as np
from vector_storage_service import VectorStorageService

# サービスの初期化
vss = VectorStorageService(vector_indexes_base_dir="./faiss_storage", embedding_dim=1536)

if vss.is_ready():
    index_name = "my_vss_index"
    fingerprint = "vss_doc_001"
    # np.ndarrayの代わりにリストを使用
    vector = np.random.rand(1536).astype("float32").tolist()
    metadata = {"source": "vss_test.txt"}

    # ベクトルの追加
    added = vss.add_vector(index_name, fingerprint, vector, metadata)
    if added:
        print(f"ベクトル '{fingerprint}' がインデックス '{index_name}' に追加されました。")

    # ベクトルの検索
    # np.ndarrayの代わりにリストを使用
    query_vector = np.random.rand(1536).astype("float32").tolist()
    results = vss.search_vectors(index_name, query_vector, top_k=1)
    if results:
        print(f"検索結果: {results}")

    # ベクトルの取得
    retrieved_vector = vss.get_vector_by_fingerprint(index_name, fingerprint)
    if retrieved_vector is not None:
        print(f"取得されたベクトルの形状: {retrieved_vector.shape}")

else:
    print("Vector Storage Serviceの準備ができていません。")

```
---
