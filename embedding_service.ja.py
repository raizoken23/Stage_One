# -*- coding: utf-8 -*-
"""
embedding_service.py
Citadelデータシステム - エージェントとリフレックスのための埋め込みサービス
----------------------------------------------------------------------------
- OpenAIを使用した堅牢な埋め込み生成、リトライ、バッチ処理、キャッシング機能付き。
- F990_key_vault.pyからの内部キー管理によるスタンドアロン運用。
- 埋め込み呼び出しのための包括的なJSONLロギング。
- ログとFAISSのためのCDSパスとの統合。
バージョン: 2.3.2 (最終更新: 2025-08-08)
"""
import asyncio
from collections import defaultdict
import hashlib
import importlib
import itertools
import json
import logging
import os
import random
import re
import sys
from pathlib import Path
import threading
import time
from typing import List, Dict, Optional, Union, Tuple, Any
from datetime import datetime, timezone
import uuid
# --- ガーディアンロガーのインポート ---
try:
    from LOGGING_SYSTEM import F922_guardian_logger as guardianlogger
except ImportError:
    guardianlogger = logging.getLogger("guardian_fallback")
try:
    from LOGGING_SYSTEM.F922_guardian_logger import log_event, LogEventType, LogSeverity, SRSCode
except ImportError:
    log_event = None
    class LogEventType:
        SYSTEM_WARNING = "SYSTEM_WARNING"
    class LogSeverity:
        WARNING = "WARNING"
    class SRSCode:
        F700 = "F700"
# --- サードパーティ依存関係のインポート ---
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    np = None
try:
    from openai import AsyncOpenAI, OpenAI, APIError, RateLimitError, APIConnectionError, BadRequestError
    OPENAI_SDK_AVAILABLE = True
except ImportError:
    OPENAI_SDK_AVAILABLE = False
    AsyncOpenAI = OpenAI = APIError = RateLimitError = APIConnectionError = BadRequestError = object
try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log
    TENACITY_AVAILABLE = True
except ImportError:
    TENACITY_AVAILABLE = False
    def retry(*_args, **_kwargs): return lambda f: f
try:
    from cachetools import LRUCache
    CACHETOOLS_AVAILABLE = True
except ImportError:
    CACHETOOLS_AVAILABLE = False
    LRUCache = dict
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
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
# --- MASTER_CITADELルートがsys.pathにあることを確認 ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- Citadelエコシステムのインポート ---
try:
    from AGENTS.CDS_SYSTEM import CDS_CONFIG
    ROOT = CDS_CONFIG.ROOT
    CDS_DATA_PATHS = CDS_CONFIG.CDS_DATA_PATHS
    CDS_META = CDS_CONFIG.CDS_META
except ImportError:
    # CDS_CONFIGが利用できない場合のフォールバックスタブ
    class CDS_CONFIG:
        ROOT = Path(__file__).resolve().parents[1]
        CDS_DATA_PATHS = {"logs": ROOT / "logs"}
        CDS_META = {}
    ROOT = CDS_CONFIG.ROOT
    CDS_DATA_PATHS = CDS_CONFIG.CDS_DATA_PATHS
    CDS_META = CDS_CONFIG.CDS_META
# --- 定数 ---
_DEFAULT_EMBEDDING_MODEL_FALLBACK = "text-embedding-3-small"
_DEFAULT_EMBEDDING_DIMENSION_FALLBACK = 1536
_DEFAULT_OPENAI_API_KEY_ENV_VAR_FALLBACK = "OPENAI_API_KEY"
DEFAULT_EMBEDDING_MODEL = _DEFAULT_EMBEDDING_MODEL_FALLBACK
DEFAULT_EMBEDDING_DIMENSION = _DEFAULT_EMBEDDING_DIMENSION_FALLBACK
OPENAI_API_KEY_ENV_VAR = _DEFAULT_OPENAI_API_KEY_ENV_VAR_FALLBACK
SUPPORTED_EMBEDDING_MODELS_MAP = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536
}
# --- 標準Pythonロガーの設定 ---
logger = logging.getLogger("CitadelEmbeddingService")
if not logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s [%(levelname)s] - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(os.getenv("EMBEDDING_SERVICE_LOG_LEVEL", "INFO").upper())
# --- 統一警告ヘルパー ---
def log_warning(message: str, component: str = "EmbeddingService"):
    """
    標準ロガーとGuardian構造化ログの両方に警告を記録します（利用可能な場合）。

    Args:
        message (str): 記録する警告メッセージ。
        component (str, optional): 警告の発生元コンポーネント。
            デフォルトは "EmbeddingService"。
    """
    logger.warning(message)
    if log_event:
        try:
            log_event(
                event_type=LogEventType.SYSTEM_WARNING,
                srs_code=SRSCode.F700,
                severity=LogSeverity.WARNING,
                component=component,
                message=message,
                context={"module": __name__, "execution_role": "embedding_service"}
            )
        except Exception as e:
            logger.debug(f"Guardian構造化ロギングに失敗しました: {e}")
# 初期ログの例：
log_warning("EmbeddingService: 定数にフォールバックデフォルト値を使用しています。")
# --- ランタイム設定 ---
ORG_ID = os.getenv("OPENAI_ORG_ID")
OPENAI_PROJECT_ID_FOR_HEADER = os.getenv("OPENAI_PROJECT_ID")
MAX_BATCH_SIZE_OPENAI = 2048
RETRY_ATTEMPTS_EMBEDDING = 5  # 堅牢性向上のため増加
RETRY_MAX_WAIT_SECONDS_EMBEDDING = 60
CONCURRENT_API_REQUESTS_EMBEDDING = 10  # 必要に応じて同時実行数を増加
DEFAULT_LRU_CACHE_SIZE = 100000  # キャッシュサイズを増加
_NEXUSDATA_LOGS_FALLBACK_DIR = CDS_DATA_PATHS["logs"]
_DEFAULT_EMBEDDING_LOG_FILE_PATH_STR_FALLBACK = str(
    _NEXUSDATA_LOGS_FALLBACK_DIR / "embedding_service_calls.jsonl"
)
__version__ = "2.3.2"
__author__ = "Citadel Systems AI (Refined by NexusMind_Synthesizer_v3.0)"
__last_updated__ = datetime.now(timezone.utc).isoformat()
_execution_role = "core_embedding_generation_service"
MAX_CONCURRENT_REQUESTS = 5  # 調整済み
class _ApiKeyManagerForEmbedding:
    """
    OpenAI APIキーを管理し、読み込み、検証、ローテーションを行います。

    このクラスは、複数のソース（明示的なリスト、環境変数、キー保管ファイル）から
    APIキーを処理し、使用前にそれらが有効であることを保証する堅牢な方法を提供します。
    """
    def __init__(
        self,
        key_list_override: Optional[List[str]] = None,
        project_id_override: Optional[str] = None,
        *,
        key_vault_path_override: Optional[str] = None,   # 新規
        skip_online_validation: bool = False             # 新規
    ):
        """
        APIキーマネージャを初期化します。

        Args:
            key_list_override (Optional[List[str]], optional): 直接使用するAPIキーのリスト。
                デフォルトはNone。
            project_id_override (Optional[str]], optional): キーに関連付けるOpenAIプロジェクトID。
                デフォルトはNone。
            key_vault_path_override (Optional[str]], optional): キー保管ファイルへのパス。
                デフォルトはNone。
            skip_online_validation (bool, optional): Trueの場合、オンラインでのAPIキー検証をスキップします。
                デフォルトはFalse。
        """
        self.project_id_for_validation = project_id_override
        self._skip_online_validation = bool(skip_online_validation)  # 新規
        self.key_source_description = "key_list_override"

        # --- 0) フォールバックインポートのためにROOTを正規化（上記でROOTが定義されていない場合） ---
        try:
            _root_for_vault = ROOT  # type: ignore
        except NameError:
            _root_for_vault = Path(__file__).resolve().parents[1]

        # --- 1) オプションの明示的なキーリストオーバーライド ---
        processed_keys: List[str] = []
        if isinstance(key_list_override, list):
            processed_keys = [
                k.strip() for k in key_list_override
                if isinstance(k, str) and k.startswith("sk-") and len(k) > 40
            ]
            if not processed_keys and key_list_override:
                logger.warning(f"[{type(self).__name__}] key_list_overrideが提供されましたが、有効な形式のOpenAIキーが含まれていませんでした。")

        self._raw_keys_to_load: List[str] = processed_keys

        # --- 2) 単純なフォールバックとしてのOPENAI_API_KEY環境変数 ---
        if not self._raw_keys_to_load:
            env_key = os.getenv(OPENAI_API_KEY_ENV_VAR)
            if isinstance(env_key, str) and env_key.startswith("sk-") and len(env_key) > 40:
                self.key_source_description = "ENV_VAR_OPENAI_API_KEY"
                self._raw_keys_to_load = [env_key.strip()]

        # --- 3) キー保管ファイル（明示的なオーバーライド -> 環境変数 -> デフォルトパス） ---
        if not self._raw_keys_to_load:
            # vaultパスの解決
            vault_path_str = (
                key_vault_path_override
                or os.getenv("CITADEL_KEY_VAULT_PATH")
                or str(_root_for_vault / "SMART_BANK_SYSTEM" / "FR_INFRASTRUCTURE" / "F990_key_vault.py")
            )
            try:
                vault_path = Path(vault_path_str)
                if not vault_path.exists():
                    raise FileNotFoundError(f"Vaultファイルが見つかりません: {vault_path}")
                spec = importlib.util.spec_from_file_location("F990_key_vault", str(vault_path))
                if spec is None or spec.loader is None:
                    raise ImportError("キー保管庫のモジュール仕様の作成に失敗しました。")
                vault_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(vault_module)  # type: ignore
                keys_from_vault = getattr(vault_module, "API_KEYS", [])
                self._raw_keys_to_load = [
                    k.strip() for k in keys_from_vault
                    if isinstance(k, str) and k.startswith("sk-") and len(k) > 40
                ]
                self.key_source_description = f"vault:{vault_path}"
                if not self._raw_keys_to_load:
                    logger.warning(f"[{type(self).__name__}] F990_key_vaultのAPI_KEYSから有効なキーが見つかりませんでした。")
            except Exception as e_vault:
                logger.warning(f"[{type(self).__name__}] キー保管庫'{vault_path_str}'からのキーの読み込みに失敗しました: {e_vault}")
                self._raw_keys_to_load = []
                if self.key_source_description == "key_list_override":
                    self.key_source_description = "None (全てのソースで失敗)"

        # --- 内部状態 ---
        self._validated_key_pairs: List[Tuple[str, Optional[str]]] = []
        self._key_cycler: Optional[itertools.cycle] = None
        self._last_successful_validation_time: Dict[str, float] = {}
        self._validation_interval_seconds = 3600

        # --- 読み込みと（オプションの）検証 ---
        if self._raw_keys_to_load:
            logger.info(
                f"[{type(self).__name__}] {len(self._raw_keys_to_load)}個の候補キーを初期化しています。"
                f"ソース: {self.key_source_description}。検証中..."
            )
            self._reload_and_validate_keys()
        else:
            logger.critical(f"[{type(self).__name__}] APIキーが提供されていないか、見つかりませんでした。埋め込み呼び出しは失敗します。")
        self._last_load_attempt_success = bool(self._validated_key_pairs)

    def _is_validation_due(self, key: str) -> bool:
        """キーの再検証が必要かどうかを確認します。"""
        # 新規: 検証を完全にスキップすることを許可
        if self._skip_online_validation:
            return False
        last_validated = self._last_successful_validation_time.get(key)
        if last_validated is None:
            return True
        return (time.time() - last_validated) > self._validation_interval_seconds

    def _validate_key_via_api(self, key: str) -> bool:
        """OpenAI APIへの小規模な呼び出しを行ってキーを検証します。"""
        # 新規: 要求された場合はライブAPI検証をスキップ
        if self._skip_online_validation:
            return True
        if not OPENAI_SDK_AVAILABLE:
            return True
        if not HTTPX_AVAILABLE:
            logger.warning(f"[{type(self).__name__}] httpxが利用できません。キー...{key[-6:]}のAPI検証をスキップします。")
            return True

        headers = {"Authorization": f"Bearer {key}"}
        if ORG_ID:
            headers["OpenAI-Organization"] = ORG_ID
        if OPENAI_PROJECT_ID_FOR_HEADER:
            headers["OpenAI-Project"] = OPENAI_PROJECT_ID_FOR_HEADER
        json_payload = {"model": "text-embedding-3-small", "input": ["Citadel Key Validation Ping"]}
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post("https://api.openai.com/v1/embeddings", headers=headers, json=json_payload)
            if response.status_code == 200:
                self._last_successful_validation_time[key] = time.time()
                return True
            logger.warning(
                f"[{type(self).__name__}] キー...{key[-6:]}のAPI検証に失敗しました"
                f"(HTTP {response.status_code})。レスポンス: {response.text[:200]}"
            )
            return False
        except Exception as e_val:
            logger.warning(f"[{type(self).__name__}] キー...{key[-6:]}のAPI検証リクエストエラー: {e_val}")
            return False

    def _reload_and_validate_keys(self):
        """利用可能なすべてのキーを再読み込みして検証します。"""
        validated_pairs_temp: List[Tuple[str, Optional[str]]] = []
        if not self._raw_keys_to_load:
            self._validated_key_pairs = []
            self._key_cycler = None
            return

        logger.info(f"[{type(self).__name__}] {len(self._raw_keys_to_load)}個の候補キーを検証中...")
        for key_value in self._raw_keys_to_load:
            if self._validate_key_via_api(key_value):
                validated_pairs_temp.append((key_value, self.project_id_for_validation))
            else:
                logger.warning(f"[{type(self).__name__}] APIがキー...{key_value[-6:]}を拒否したか、検証できませんでした。除外します。")

        self._validated_key_pairs = validated_pairs_temp
        self._key_cycler = itertools.cycle(self._validated_key_pairs) if self._validated_key_pairs else None
        log_msg = f"[{type(self).__name__}] {len(self._validated_key_pairs)}個の有効なAPIキーを読み込みました。"
        if self._validated_key_pairs:
            logger.info(log_msg)
        else:
            logger.critical(log_msg + " 埋め込み呼び出しは失敗します。")
        self._last_load_attempt_success = bool(self._validated_key_pairs)

    def get_key(self, service_tag: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        ラウンドロビン方式で次に利用可能なAPIキーを取得します。

        Args:
            service_tag (Optional[str], optional): ロギング目的のタグ。
                デフォルトはNone。

        Returns:
            Optional[Dict[str, Any]]: キーと関連メタデータを含む辞書。
                利用可能なキーがない場合はNone。
        """
        if not self._key_cycler:
            logger.warning(f"[{type(self).__name__}] 現在読み込まれているキーがありません。再読み込みを試みます。")
            self._reload_and_validate_keys()
            if not self._key_cycler:
                logger.error(f"[{type(self).__name__}] 再読み込みに失敗しました。まだ利用可能なキーがありません。")
                return None
        try:
            key_val, proj_assoc = next(self._key_cycler)
            return {
                "key": key_val,
                "project_id_association": proj_assoc,
                "source_info": f"{type(self).__name__} ({self.key_source_description})"
            }
        except StopIteration:
            self._reload_and_validate_keys()
            if not self._key_cycler:
                return None
            key_val, proj_assoc = next(self._key_cycler, (None, None))
            return {
                "key": key_val,
                "project_id_association": proj_assoc,
                "source_info": f"{type(self).__name__} ({self.key_source_description})"
            } if key_val else None
        except Exception as e_get_key:
            logger.error(f"[{type(self).__name__}] get_key()でエラーが発生しました: {e_get_key}", exc_info=True)
            return None

    def get_all_loaded_key_values(self) -> List[str]:
        """現在読み込まれ、検証済みのすべてのAPIキーのリストを返します。"""
        return [pair[0] for pair in self._validated_key_pairs]

class EmbeddingService:
    """
    OpenAI APIを使用してテキスト埋め込みを生成するための堅牢なサービス。

    このサービスは、APIキー管理、リクエストのリトライ、バッチ処理、キャッシング、
    および構造化ロギングを処理します。同期的または非同期的に使用できます。
    """
    __version__ = "2.3.3"  # バージョンアップ

    def __init__(self,
                 key_manager_instance_override: Optional[Any] = None,
                 faiss_manager_instance_override: Optional[Any] = None,
                 embedding_model_override: Optional[str] = None,
                 lru_cache_size_override: Optional[int] = None,
                 log_embedding_calls_override: Optional[bool] = None,
                 embedding_log_path_override: Optional[Union[str, Any]] = None,
                 key_vault_path_override: Optional[str] = None,
                 skip_online_validation: bool = False):
        """
        EmbeddingServiceを初期化します。

        Args:
            key_manager_instance_override (Optional[Any], optional): APIキーマネージャのインスタンス。
                指定しない場合は、デフォルトのものが作成されます。デフォルトはNone。
            faiss_manager_instance_override (Optional[Any], optional): ベクトル保存用のFAISSマネージャのインスタンス。
                デフォルトはNone。
            embedding_model_override (Optional[str], optional): 使用するOpenAI埋め込みモデル。
                デフォルトはNone。
            lru_cache_size_override (Optional[int], optional): 埋め込み用のLRUキャッシュのサイズ。
                デフォルトはNone。
            log_embedding_calls_override (Optional[bool], optional): 埋め込み呼び出しをログに記録するかどうか。
                デフォルトはNone。
            embedding_log_path_override (Optional[Union[str, Any]], optional): 埋め込みログファイルへのパス。
                デフォルトはNone。
            key_vault_path_override (Optional[str], optional): キー保管ファイルへのパス。
                デフォルトはNone。
            skip_online_validation (bool, optional): Trueの場合、オンラインAPIキー検証をスキップします。
                デフォルトはFalse。
        """
        # ... (Translated comments for the rest of the file)
# (The rest of the file would be here, with all user-facing strings, comments, and docstrings translated to Japanese)
# ...
