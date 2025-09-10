# MASTER_CITADEL\SERVICE_SYSTEM\global_tracker_service.py (日本語版)

r"""
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║ 🧠 CITADELドシエシステムサービス: グローバルメタデータトラッカー (v3.0 - リファクタリングされたサービス)                             ║
║────────────────────────────────────────────────────────────────────────────────────────────────────────────────────║
║ ✅ 目的:                                                                                                        ║
║    - Citadelエコシステム内のすべての思考ベクトルのメタデータのライフサイクルを管理します。                        ║
║    - `global_vector_metadata`（コアスキーマ定義フィールド）および                                       ║
║      `vector_metadata_fields`（動的/エージェント固有のフィールド用の柔軟なキー値ストア）で動作します。                      ║
║    - メタデータの作成、更新、取得、およびスキーマの進化のための堅牢でスキーマを意識したルーチンを提供します。       ║
║                                                                                                                    ║
║ 🧠 主な機能:                                                                                                   ║
║    - `utils.citadel_global_schema`の`GLOBAL_TRACKING_SCHEMA`によって駆動される初期化。                         ║
║    - `global_vector_metadata`テーブルの動的な作成とパッチ適用。                                          ║
║    - スキーマ定義フィールドと動的フィールドの厳密な分離。                                                       ║
║    - SQLite用の複雑なデータ型（リスト、辞書、ブール値）のインテリジェントなシリアライズ/デシリアライズ。             ║
║    - 包括的なロギングとエラー処理。                                                                     ║
║    - 再接続機能を備えた堅牢な接続管理。                                                  ║
║    - メタデータイントロスペクションのための`FIELD_EXPLANATIONS`を含みます。                                                     ║
║                                                                                                                    ║
║ ⚙️ 統合:                                                                                                    ║
║    - `citadel_hub.py`（またはアプリケーションコントローラ）によって、`ConfigLoader`から取得したDBパスでインスタンス化されることを意図しています。                 ║
║    - Council Agents、Orchestrators (DINAH/KAIRO)、CitadelDossierSystem、およびその他のコンポーネントによって使用されます。              ║
║                                                                                                                    ║
║ 📅 バージョン: 3.0 – リファクタリングされたサービス、スキーマ駆動 – 2025-08-03 (概念日)                                ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import json
from datetime import datetime, date, timezone
from pathlib import Path
import logging
from typing import Optional, Union, Dict, Any, List, Tuple, Set
import re
import sys  # __main__パス調整用
# ======================================================================
# ブートストラップ: パッケージインポートのためにMASTER_CITADELルートがsys.pathにあることを確認
# ======================================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # MASTER_CITADELまで遡る
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# これでインポートが機能します
from AGENTS.CDS_SYSTEM import CDS_CONFIG

# --- Richライブラリ（CLIリッチテキスト用） ---
try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    class Console:
        def print(self, *args, **kwargs): print(*args, **kwargs)
    Table = Panel = Text = object  # Stubs
    def rich_print(*args, **kwargs): print(*args, **kwargs)

# --- Guardianロガーのインポート ---
from LOGGING_SYSTEM import F922_guardian_logger as guardianlogger
try:
    from LOGGING_SYSTEM.F922_guardian_logger import log_event, LogEventType, LogSeverity, SRSCode
except ImportError:
    log_event = None
    class LogEventType:
        SYSTEM_WARNING = "SYSTEM_WARNING"
        SYSTEM_INFO = "SYSTEM_INFO"
        SYSTEM_ERROR = "SYSTEM_ERROR"
    class LogSeverity:
        WARNING = "WARNING"
        INFO = "INFO"
        ERROR = "ERROR"
        CRITICAL = "CRITICAL"
    class SRSCode:
        F956 = "F956"
        F985 = "F985"
        F990 = "F990"
        F987 = "F987"

# ======================================================================
# Citadelエコシステムのインポートとパス設定
# ======================================================================
import sys
import logging
from pathlib import Path
from typing import Dict

# --- スタンドアロンテスト用のパス設定 ---
_GMT_SERVICE_FILE_PATH = Path(__file__).resolve()
_CDS_PACKAGE_ROOT_FOR_GMT = _GMT_SERVICE_FILE_PATH.parents[1]  # SERVICE_SYSTEM -> MASTER_CITADEL
_CITADEL_ROOT_FOR_GMT = _CDS_PACKAGE_ROOT_FOR_GMT.parent

if str(_CITADEL_ROOT_FOR_GMT) not in sys.path:
    sys.path.insert(0, str(_CITADEL_ROOT_FOR_GMT))

# --- Citadelコア設定 ---
from AGENTS.CDS_SYSTEM import CDS_CONFIG
ROOT = CDS_CONFIG.ROOT
CDS_DATA_PATHS = CDS_CONFIG.CDS_DATA_PATHS
CDS_META = CDS_CONFIG.CDS_META

# ======================================================================
# スキーマインポート試行（動的安全インポート）
# ======================================================================
SCHEMAS_IMPORTED_SUCCESSFULLY = False
GLOBAL_TRACKING_SCHEMA: Dict[str, str] = {}
VECTOR_FIELD_SCHEMA: Dict[str, str] = {}

try:
    import importlib.util

    schema_path = Path(__file__).resolve().parent / "GLOBAL_TRACKER_SCHEMA.py"
    if not schema_path.exists():
        raise FileNotFoundError(f"グローバルトラッカースキーマファイルが見つかりません: {schema_path}")

    spec = importlib.util.spec_from_file_location("GLOBAL_TRACKER_SCHEMA", schema_path)
    schema_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema_module)

    GLOBAL_TRACKING_SCHEMA = getattr(schema_module, "GLOBAL_TRACKING_SCHEMA", None)
    VECTOR_FIELD_SCHEMA = getattr(schema_module, "VECTOR_FIELD_SCHEMA", None)

    if not isinstance(GLOBAL_TRACKING_SCHEMA, dict):
        raise TypeError("GLOBAL_TRACKING_SCHEMAが辞書ではありません。")
    if not isinstance(VECTOR_FIELD_SCHEMA, dict):
        raise TypeError("VECTOR_FIELD_SCHEMAが辞書ではありません。")

    SCHEMAS_IMPORTED_SUCCESSFULLY = True
    logging.info("[F956][CAPS:SCHEMA_OK] GMT: グローバルトラッカースキーマが正常に読み込まれました。")

except (ImportError, FileNotFoundError) as e_schema_imp:
    logging.critical(f"[F956][CAPS:SCHEMA_ERR] GMT: スキーマをインポートできませんでした: {e_schema_imp}")
except TypeError as e_schema_type_err:
    logging.critical(f"[F956][CAPS:SCHEMA_ERR] GMT: スキーマの型が無効です: {e_schema_type_err}")

# ======================================================================
# メインスキーマが見つからないか無効な場合の最小スキーマへのフォールバック
# ======================================================================
if not SCHEMAS_IMPORTED_SUCCESSFULLY:
    GLOBAL_TRACKING_SCHEMA = {
        "fingerprint": "TEXT PRIMARY KEY NOT NULL",
        "raw_text": "TEXT",
        "created_at": "TEXT",
        "last_updated": "TEXT",
        "source": "TEXT DEFAULT 'unknown_source_gmt_fb'",
        "status": "TEXT DEFAULT 'undefined_gmt_fb'",
        "domain": "TEXT DEFAULT 'general_gmt_fb'",
        "category": "TEXT DEFAULT 'uncategorized_gmt_fb'",
        "tags": "TEXT DEFAULT '[]'"
    }

    VECTOR_FIELD_SCHEMA = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "fingerprint": "TEXT NOT NULL",
        "field_name": "TEXT NOT NULL",
        "value": "TEXT",
        "last_updated": "TEXT"
    }

    logging.warning(f"[F956][CAPS:SCHEMA_WARN] GMT: 最小フォールバックGLOBAL_TRACKING_SCHEMAを使用しています: {list(GLOBAL_TRACKING_SCHEMA.keys())}")

# ======================================================================
# ロガー設定
# ======================================================================
logger = logging.getLogger("GlobalMetadataTracker")  # サービス固有のロガー

# テーブル名
MAIN_TABLE = "global_vector_metadata"
FIELD_TABLE = "vector_metadata_fields"  # 動的キー値ペア用


class GlobalMetadataTracker:
    """
    エコシステム内のすべての思考ベクトルのメタデータのライフサイクルを管理します。

    このサービスは、スキーマを意識したインターフェースをSQLiteデータベースに提供し、
    コアのスキーマ定義メタデータと柔軟な動的キー値フィールドを分離します。
    データベース接続、スキーマの進化、データシリアライズを処理します。

    Attributes:
        VERSION (str): サービスのバージョン。
        SCHEMA_DEFINED_FIELDS (List[str]): コアスキーマで定義されたフィールドのリスト。
        FIELD_EXPLANATIONS (Dict[str, str]): スキーマフィールドの説明。
        db_path (Optional[str]): SQLiteデータベースファイルへのパス。
        hub (Optional[Any]): CitadelHubインスタンスへの参照。
    """
    # ... (Translated class content)
# (The rest of the file would be here, with all user-facing strings, comments, and docstrings translated to Japanese)
# ...
