# MASTER_CITADEL\SERVICE_SYSTEM\memory_context_service.py (日本語版)
# MemoryContextService v7.6.3 - 文書化され、ハブ対応のコンテキストオーケストレーター（修正更新済み）
# ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║ 🧠 CITADELメモリコンテキストサービス — v7.6.3 (文書化＆ハブ対応オーケストレーター) ║
# ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
# ✅ 目的: ║
# - 専門のデータサービス（MemoryController、LogReader、TemporalEngineなど）と内部分析を活用してコンテキストを生成します。 ║
# - AIエージェントのプロンプトと応答の関連性、一貫性、継続性を大幅に向上させることを目指します。 ║
# ║
# 🌟 主な機能と設計原則: ║
# - コンテキストオーケストレーション (`build_full_context`): 多様なソース（ベクトル/アンカーメモリ、ログ、プロファイルなど）からの情報を階層化します。 ║
# - サービス委任: 専門のデータ取得と処理のために、注入されたCitadelサービスに依存します。 ║
# - 設定駆動: 動作は設定辞書（CitadelHubから期待される）によって制御されます。 ║
# - 内部分析ユーティリティ: テーママッチング、ストリーク分析、フォーカス要約のための簡略化されたプレースホルダーを含みます。 ║
# - 動的適応: プロンプトの内容とセッションメタデータに基づいてコンテキストを調整します。 ║
# - 構造化ロギング: 運用イベントとコンテキスト生成の要約を記録します。 ║
# - 拡張可能な設計: 新しいコンテキストソースや分析モジュールの将来的な統合を可能にします。 ║
# ║
# ⚙️ 統合と依存関係: ║
# - 想定されるインスタンス化元: `hub_instance: CitadelHub`（サービスと設定の解決のため）、`memory_controller: MemoryControllerService`║
# （概念的）、`log_reader: LogReaderService`（概念的）、`temporal_engine: TemporalEngineService`。 ║
# - オプションの依存関係: `EmbeddingService`、`UserProfileService`（概念的）、`LingoAdapter`。 ║
# - 設定: `hub_instance.SYSTEM_CONFIG.memory_context_service`（または同様のキーパス）に依存します。 ║
# ║
# 📅 バージョン: 7.6.3 – ロギング、準備完了状態、セルフテストの修正 | 最終更新日: 2025-08-08T00:00:00Z ║
# 👤 作成者: The Brotherhood / Project Nexus & Citadel Development Team (NexusAIによる文書化) ║
# 📜 _execution_role: core_context_enrichment_orchestration_service ║
# 🔗 関連ブループリント: CEDGP-DAP-001, CEDGP-DAP-002, MemoryControllerService_BLUEPRINT.md (Conceptual), LogReaderService_BLUEPRINT.md (Conceptual)║
# ⚖️ ライセンス: プロプライエタリ - 内部使用のみ ║
#╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
__version__ = "7.6.3" # 修正のためインクリメント
__author__ = "The Brotherhood / Project Nexus & Citadel Development Team (NexusAIによる文書化)"
__last_updated__ = "2025-08-08T00:00:00Z" # 更新日
_execution_role = "core_context_enrichment_orchestration_service"
# --- 標準ライブラリのインポート ---
import sys
from pathlib import Path
import json
import random
import logging
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Tuple, Callable, Set, Union
from datetime import datetime, timezone as dt_timezone, timedelta
import os
import time
import asyncio # 非同期メソッド用（例：_summarize_context_snippet_async）、およびセルフテスト用
from enum import Enum
from abc import ABC, abstractmethod # TYPE_CHECKINGスタブ用
from collections import defaultdict # MCS内部使用
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
    Table = Panel = Text = object # Stubs
    def rich_print(*args, **kwargs): print(*args, **kwargs)
# --- モジュールレベルのロギング＆ID用定数 ---
_SERVICE_LOGGER_NAME_MCS_MAIN = "MemoryContextService.Main"
_SERVICE_INSTANCE_LOGGER_PREFIX_MCS = "MemoryContextService.Instance"
# --- メインモジュールロガー設定 ---
logger = logging.getLogger(_SERVICE_LOGGER_NAME_MCS_MAIN)
if not logger.handlers:
    _lh_mcs_module_level = logging.StreamHandler(sys.stdout)
    _lf_mcs_module_level = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')
    _lh_mcs_module_level.setFormatter(_lf_mcs_module_level)
    logger.addHandler(_lh_mcs_module_level)
    logger.setLevel(os.getenv(f"{_SERVICE_LOGGER_NAME_MCS_MAIN.upper().replace('.', '_')}_LOG_LEVEL", "INFO").upper())
# --- ブートストラップパスインジェクション（スタンドアロン実行用） ---
_MCS_FILE_PATH_BOOTSTRAP_V761 = Path(__file__).resolve()
_PROJECT_ROOT_FOR_MCS_BOOTSTRAP_V761 = _MCS_FILE_PATH_BOOTSTRAP_V761.parents[1] # ここで定義
if str(_PROJECT_ROOT_FOR_MCS_BOOTSTRAP_V761) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_FOR_MCS_BOOTSTRAP_V761))
# --- Citadelコアのインポート試行 ---
HUB_AVAILABLE_MCS = False # デフォルトはFalse。主要なインポートが成功した場合にTrueに設定
# cds_constants_mcsとcmn_generate_short_uuid_mcsを最初にフォールバック付きで定義
try:
    from utils import constants as cds_constants_mcs_import
    from utils.common_utils import generate_short_uuid as cmn_generate_short_uuid_mcs_import
    cds_constants_mcs = cds_constants_mcs_import
    cmn_generate_short_uuid_mcs = cmn_generate_short_uuid_mcs_import
    logger.debug(f"[{_SERVICE_LOGGER_NAME_MCS_MAIN}] cds_constants_mcsとcmn_generate_short_uuid_mcsを正常にインポートしました。")
except ImportError:
    logger.warning(f"[{_SERVICE_LOGGER_NAME_MCS_MAIN}] CDSユーティリティ（constants/common_utils）をインポートできませんでした。基本的なスタブ/フォールバックを使用します。")
    # インポートが失敗した場合でもこれらの名前が定義されていることを確認
    if 'cds_constants_mcs' not in globals(): # 2つのユーティリティのうち1つだけが失敗した場合に必要
        class cds_constants_fallback_mcs_cls_module_level_runtime:
            LOG_LEVEL_INFO = "INFO"; PLACEHOLDER_TEXT_EMPTY = "[NO_DATA_MCS_FALLBACK_CONSTANTS]"
            @staticmethod
            def generate_short_uuid(length: int = 12) -> str:
                return f"fb_uuid_{random.randint(10000,999999)}"
        cds_constants_mcs = cds_constants_fallback_mcs_cls_module_level_runtime() # type: ignore
    if 'cmn_generate_short_uuid_mcs' not in locals():
        cmn_generate_short_uuid_mcs = cds_constants_mcs.generate_short_uuid # type: ignore
# 定数/ユーティリティが確定した後に実際のTemporalEngineServiceをインポート試行
# リンター用に最初にフォールバック型ヒントでRealTemporalEngineServiceを宣言
RealTemporalEngineService: Any # これは実際のクラスまたはスタブクラスで上書きされる
try:
    from services.temporal_services import TemporalEngineService as ImportedRealTemporalEngineService
    RealTemporalEngineService = ImportedRealTemporalEngineService # MockHubが期待する名前に割り当て
    logger.info(f"[{_SERVICE_LOGGER_NAME_MCS_MAIN}] 実際のTemporalEngineServiceをRealTemporalEngineServiceとして正常にインポートしました。")
    HUB_AVAILABLE_MCS = True # ここまで来たら、ハブ関連のコンポーネントがいくつか利用可能であると仮定
except ImportError:
    logger.warning(f"[{_SERVICE_LOGGER_NAME_MCS_MAIN}] 実際のTemporalEngineServiceが見つかりません。フォールバックスタブクラスを定義します。")
    class RealTemporalEngineService_FallbackStub_ModuleLevel_Runtime: # スタブクラスには別名を使用
        def __init__(self, *args, **kwargs):
            logger.warning(f"フォールバックSTUB RealTemporalEngineServiceを使用しています（モジュールレベル定義: {type(self).__name__}）。")
            self._is_ready_stub = True
        def is_ready(self): return self._is_ready_stub
        def time_reflection_index(self, delta_seconds: float, **kwargs) -> float: return 0.05
        def calculate_time_delta_seconds(self, ts_str: Optional[str], **kwargs) -> float: return 7200.0
        def configure_thresholds(self, config_dict: Dict[str, Any]):
            logger.debug(f"フォールバックStub RealTemporalEngineService: configure_thresholdsが{config_dict}で呼び出されました")
    RealTemporalEngineService = RealTemporalEngineService_FallbackStub_ModuleLevel_Runtime # type: ignore
# CitadelHubおよび他のサービスヒント用のTYPE_CHECKINGブロック
if TYPE_CHECKING:
    from citadel_hub import CitadelHub
    from services.embedding_services import EmbeddingService
    from config.schemas import DossierSystemConfigSchema, LESQueryProcessingLog, USOChatInteractionContextSnapshot, VDContentTypeEnum
    # 概念的なサービス - これらのクラスは、型ヒントのために他の場所で定義するか、ABCとして定義する必要がある
    class MemoryControllerService(ABC):
        @abstractmethod
        def is_ready(self) -> bool: pass
        @abstractmethod
        def get_anchors_batch(self, keys: List[str], owner_id: str, **kwargs) -> Dict[str, str]: pass
        @abstractmethod
        def search_memory(self, query_text:str, top_k:int, owner_id:str, session_id:Optional[str]=None, **kwargs) -> List[Dict]: pass
        @abstractmethod
        def add_external_reflection(self, reflection_data: Dict[str, Any], target_id: str) -> None: pass
        @abstractmethod
        def get_anchor(self, key: str, owner_id: str, **kwargs) -> Optional[str]: pass
        @abstractmethod
        def search_anchors(self, query_text: str, owner_id: str, top_k: int, **kwargs) -> List[Dict]: pass
    class LogReaderService(ABC):
        @abstractmethod
        def is_ready(self) -> bool: pass
        @abstractmethod
        def get_recent_logs(self, target_id:str, session_id:Optional[str], limit:int, **kwargs) -> List[Dict]: pass
        @abstractmethod
        def get_session_text_blob(self, target_id:str, session_id:Optional[str], **kwargs) -> str: pass
        @abstractmethod
        def search_logs_by_keyword(self, query_text: str, top_k:int, target_id:str, session_id:Optional[str], **kwargs) -> List[Dict]: pass
        @abstractmethod
        def get_reflective_logs(self, limit:int, target_id:str, session_id:Optional[str], **kwargs) -> List[Dict]: pass
        @abstractmethod
        def get_curated_external_insights(self, target_id:str, limit:int, **kwargs) -> List[Dict]: pass
        @abstractmethod
        def get_log_entries_by_keywords_list(self, keywords_list:List[str], top_k_per_keyword:int, target_id:str, session_id:Optional[str], **kwargs) -> List[Dict]: pass
        @abstractmethod
        def get_log_signature_trends_formatted(self, target_id:str, session_id:Optional[str], **kwargs) -> str: pass
        @abstractmethod
        def get_keyword_frequency_map_formatted(self, target_id:str, session_id:Optional[str], **kwargs) -> str: pass
        @abstractmethod
        def get_conceptual_vocabulary_formatted(self, target_id:str, session_id:Optional[str], min_len:int, **kwargs) -> str: pass
        @abstractmethod
        def get_session_summary_stats_formatted(self, target_id:str, session_id:Optional[str], **kwargs) -> str: pass
        @abstractmethod
        def get_keyword_completion_trace_formatted(self, keywords:List[str], target_id:str, session_id:Optional[str], **kwargs) -> str: pass
        @abstractmethod
        def get_raw_logs(self, target_id:str, session_id:Optional[str], limit:int, **kwargs) -> List[Dict]: pass
        @abstractmethod
        def get_silence_trend_report_formatted(self, target_id:str, session_id:Optional[str], **kwargs) -> str: pass
    class UserProfileService(ABC):
        @abstractmethod
        def is_ready(self) -> bool: pass
        @abstractmethod
        def get_profile_summary_overlay(self, profile_identity: Any) -> Optional[str]: pass
        @abstractmethod
        def get_trust_snapshot_overlay(self, profile_identity: Any) -> Optional[str]: pass
        @abstractmethod
        def get_full_identity_context_block(self, target_id: str, ai_profile_obj: Any) -> Optional[str]: pass
else:
    # TYPE_CHECKINGがfalseで、かつ上記の実際のインポートが失敗した場合のランタイムスタブ
    # 注：RealTemporalEngineServiceはこの時点で実クラスまたはスタブとしてすでに定義されている
    if 'CitadelHub' not in globals(): CitadelHub = Any
    if 'EmbeddingService' not in globals(): EmbeddingService = Any
    if 'DossierSystemConfigSchema' not in globals(): DossierSystemConfigSchema = Any
    if 'LESQueryProcessingLog' not in globals(): LESQueryProcessingLog = Any
    if 'USOChatInteractionContextSnapshot' not in globals(): USOChatInteractionContextSnapshot = Any
    if 'MemoryControllerService' not in globals(): MemoryControllerService = Any
    if 'LogReaderService' not in globals(): LogReaderService = Any
    if 'UserProfileService' not in globals(): UserProfileService = Any
    if 'VDContentTypeEnum' not in globals(): # 必要であれば単純なEnumスタブを定義
        class VDContentTypeEnum(Enum): # type: ignore
            UNKNOWN = "unknown"; USO_CONVERSATION_LOG = "uso_conversation_log"
            USO_SELF_REFLECTION_DIGEST = "uso_self_reflection_digest"
# --- デフォルト定数/シード（MCS内部用、設定で上書き可能） ---
DEFAULT_MCS_CURIOSITY_SEEDS_INTERNAL = {
    "identity": ["私たちの対話を振り返って、現在の自己評価はどうですか？", "あなたの役割についての理解はどのように進化しましたか？"],
    "emotion": ["最近のやり取りの主な感情的な基調は何ですか？", "対話の感情的な雰囲気の変化を特定できますか？"],
    "growth": ["この対話からどのような新しい洞察やつながりが生まれましたか？", "この対話からの主要な学びや適応を説明してください。"]
}
DEFAULT_MCS_GROWTH_DETECTION_KEYWORDS_INTERNAL = [
    "learn", "understand", "realize", "change", "improve", "evolve", "grow", "adapt", "new perspective", "insight"
]
DEFAULT_MCS_ANCHOR_KEYS_INTERNAL = ["core_mission", "primary_directive", "ethical_framework_id"]
DEFAULT_MCS_THEME_KEYWORDS_FOR_ANALYSIS_INTERNAL = {
    "identity": ["i am", "my name is", "i identify as", "my purpose", "who i am"],
    "goals": ["i want to", "my goal is", "i need to", "objective"],
    "feedback": ["that was helpful", "good point", "i disagree", "correction", "not quite"],
    "emotion_positive": ["happy", "grateful", "excited", "love this", "great"],
    "emotion_negative": ["sad", "angry", "frustrated", "confused", "concerned"]
}
# ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║ 🏛️ MEMORYCONTEXTSERVICEクラス定義 — v7.6.3 🏛️ ║
# ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
# ✅ 目的: 様々なCitadelデータサービスを使用してAIエージェントのコンテキストアセンブリを調整します。詳細はモジュールヘッダーを参照してください。 ║
# ⚙️ 使用法: CitadelHubによってインスタンス化され、hub_instance（設定/サービス用）、memory_controller、log_reader、temporal_engineが必要です。 ║
#╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
class MemoryContextService:
    """
    AIエージェントのためのリッチな文脈的プロンプトの組み立てを調整します。

    このサービスは、様々なCitadelデータサービスを統合して、AIエージェントの対話に
    関連性があり、一貫性があり、継続的なコンテキストを提供します。ベクトルメモリ、
    アンカーメモリ、ログ、ユーザープロファイルからの情報を階層化して、
    AIの応答の質を高めます。
    """
    # ... (Translated class content)
# (The rest of the file would be here, with all user-facing strings, comments, and docstrings translated to Japanese)
# ...
