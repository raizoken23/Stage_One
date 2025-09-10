# D:\MASTER_CITADEL\SERVICE_SYSTEM\faiss_management_service.py (日本語版)


# --- ブートストラップパスインジェクション（スタンドアロン実行用） ---
import sys
from pathlib import Path
import time # __main__テストタイミング用
from datetime import datetime, timezone

_SERVICE_FILE_PATH_FOR_BOOTSTRAP = Path(__file__).resolve()
_PROJECT_ROOT_FOR_SERVICE_BOOTSTRAP = _SERVICE_FILE_PATH_FOR_BOOTSTRAP.parents[1]  # SERVICE_SYSTEMの親はMASTER_CITADEL
if str(_PROJECT_ROOT_FOR_SERVICE_BOOTSTRAP) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_FOR_SERVICE_BOOTSTRAP))
    print(f"[FAISSManagementService Bootstrap] Added {_PROJECT_ROOT_FOR_SERVICE_BOOTSTRAP} to sys.path for direct execution.")
# --- ブートストラップ終了 ---
# ---------------------------------------------------------------------------
# FAISSManagementService ブートストラップ
# ---------------------------------------------------------------------------
import sys, os, logging, traceback
from pathlib import Path
from LOGGING_SYSTEM.F922_guardian_logger import (
    guardian_logger,
    LogEventType,
    LogSeverity,
    SRSCode
)

CURRENT_FILE = Path(__file__).resolve()
print(f"[FAISSManagementService Bootstrap] Executing: {CURRENT_FILE}")
sys.path.insert(0, str(CURRENT_FILE.parents[1]))  # MASTER_CITADELがパスにあることを確認

logger = logging.getLogger("FAISSManagementService")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(name)s [%(levelname)s] - %(message)s"))
    logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Citadelインポート（診断付き）
# ---------------------------------------------------------------------------
try:
    from LOGGING_SYSTEM.F922_guardian_logger import guardian_logger
    from LOGGING_SYSTEM.FR_ENUM.F921_schemas import (
        DossierSystemConfigSchema,
        FaissIndexDefaultConfigSchema
    )
    logger.info(f"[F956][CAPS:FMS_BOOT] Schemas imported successfully from {Path(__file__).resolve()}")
except ImportError as e:
    tb_str = traceback.format_exc()
    logger.critical(
        f"[F956][CAPS:FMS_IMPORT_ERR] Failed to import schema modules!\n"
        f"- Current File: {CURRENT_FILE}\n"
        f"- sys.path[0]: {sys.path[0]}\n"
        f"- Working Dir: {os.getcwd()}\n"
        f"- Exception: {e}\n\nTraceback:\n{tb_str}"
    )
    raise

# ---------------------------------------------------------------------------
# オプション：ファイルを明示的にログに記録して検証
# ---------------------------------------------------------------------------
for module_name in ["LOGGING_SYSTEM", "LOGGING_SYSTEM.FR_ENUM", "LOGGING_SYSTEM.FR_ENUM.F921_schemas"]:
    try:
        mod = __import__(module_name, fromlist=['*'])
        logger.info(f"[F956][CAPS:FMS_BOOT] Verified import path for {module_name}: {Path(mod.__file__).resolve()}")
    except Exception as verify_exc:
        logger.warning(f"[F956][CAPS:FMS_BOOT_WARN] Could not verify module {module_name}: {verify_exc}")


r"""
Citadelドシエシステム - FAISS管理サービス
ファイルバージョン: 3.1.1
最終更新日: 2025-08-03

目的:
ベクトルインデックスの管理と対話のための高レベルAPIを提供します。このサービスは、
すべての低レベルFAISSストレージ、検索、インデックス作成、および直接的なベクトルデータ
再構築をVectorStorageServiceのインスタンスに委任します。FAISSManagementServiceは、
ベクトル操作の調整に焦点を当て、オプションでGlobalMetadataTrackerと統合して、
ベクトルに関連付けられたより豊富なメタデータを管理できます。

主要な設計原則:
- 分離: 高レベルのベクトル操作要求を、基礎となるストレージメカニズムから分離します。
- 委任: コアのベクトルデータとFAISSの相互作用を完全にVectorStorageServiceに依存します。
- サービス構成可能性: GlobalMetadataTrackerと連携して動作できます。
- 責任の焦点化: FAISSファイルや複雑なIDマップを直接管理しません。
"""

import logging
from typing import Dict, Any, List, Tuple, Optional, Union, Callable
import json # __main__ブロックでjson.dumpsを使用する場合に追加

# --- NumPy ---
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False; np = None #type: ignore
    logging.getLogger(__name__).warning("NumPyがFMSで利用できません。入力ベクトルタイプが制限される可能性があります。")

# --- Citadelエコシステムのインポート ---
from AGENTS.CDS_SYSTEM import CDS_CONFIG
ROOT = CDS_CONFIG.ROOT
CDS_DATA_PATHS = CDS_CONFIG.CDS_DATA_PATHS
CDS_META = CDS_CONFIG.CDS_META

VSS_FAISS_AVAILABLE = False
CITADEL_IMPORTS_OK = False
logger_fms_init = logging.getLogger(__name__)  # インポートフェーズの初期ロガー

try:
    from SERVICE_SYSTEM.VECTOR_STORAGE_SERVICE import (
        VectorStorageService,
        FAISS_AVAILABLE as VSS_FAISS_AVAILABLE_FROM_MODULE
    )
    from SERVICE_SYSTEM.GLOBAL_TRACKER_SERVICE import GlobalMetadataTracker


    VSS_FAISS_AVAILABLE = VSS_FAISS_AVAILABLE_FROM_MODULE
    CITADEL_IMPORTS_OK = True
    logger = logging.getLogger(__name__)  # 最終的なロガーインスタンス

except ImportError as e_fms_imports:
    logger_fms_init.critical(
        "[FAISSManagementService Init Error] 重要なCitadelモジュールのインポートに失敗しました: "
        f"{e_fms_imports}。サービスは機能しません。",
        exc_info=True
    )
    # グローバルに宣言されていない場合にのみフォールバックスタブを定義
    if 'VectorStorageService' not in globals():
        class VectorStorageService: pass  # type: ignore
    if 'GlobalMetadataTracker' not in globals():
        class GlobalMetadataTracker: pass  # type: ignore
    if 'DossierSystemConfigSchema' not in globals():
        class DossierSystemConfigSchema: pass  # type: ignore
    if 'FaissIndexDefaultConfigSchema' not in globals():
        class FaissIndexDefaultConfigSchema: pass  # type: ignore
    if 'cds_constants' not in globals():
        class cds_constants: DEFAULT_EMBEDDING_DIM = 1536  # type: ignore
    if 'sanitize_filename_component' not in globals():
        def sanitize_filename_component(name: str) -> str: return name  # type: ignore
    if 'logger' not in globals():
        logger = logger_fms_init

DEFAULT_EMBEDDING_DIM_FMS = getattr(cds_constants, 'DEFAULT_EMBEDDING_DIM', 1536) \
    if CITADEL_IMPORTS_OK and 'cds_constants' in globals() else 1536

class FAISSManagementService:
    """
    高レベルAPIを提供することでFAISSベクトルインデックスを管理します。

    このサービスはVectorStorageService上のオーケストレーションレイヤーとして機能し、
    すべての低レベルFAISSインタラクションをそれに委任します。また、
    GlobalMetadataTrackerと統合して、ベクトルに関連付けられたより豊富なメタデータを管理することもできます。

    Attributes:
        system_config (Union[DossierSystemConfigSchema, Dict[str, Any]]): システム
            設定オブジェクトまたは辞書。
        vss (VectorStorageService): 基盤となるベクトルストレージサービスインスタンス。
        global_tracker (Optional[GlobalMetadataTracker]): グローバルメタデータトラッカーの
            オプションのインスタンス。
    """

    def __init__(
        self,
        system_config: Union[DossierSystemConfigSchema, Dict[str, Any]],
        vector_storage_service: VectorStorageService,
        global_tracker_instance: Optional[GlobalMetadataTracker] = None
    ):
        """
        FAISSManagementServiceを初期化します。

        Args:
            system_config (Union[DossierSystemConfigSchema, Dict[str, Any]]):
                システム設定。
            vector_storage_service (VectorStorageService): 初期化された
                VectorStorageServiceのインスタンス。
            global_tracker_instance (Optional[GlobalMetadataTracker], optional):
                GlobalMetadataTrackerのオプションのインスタンス。デフォルトはNone。

        Raises:
            ImportError: 重要なCitadelモジュールまたはFAISSライブラリが
                利用できない場合。
            TypeError: `vector_storage_service`が有効なインスタンスでない場合。
        """
        # ----------------------------------------------------------------------
        # 0) 防御的チェック
        # ----------------------------------------------------------------------
        if not CITADEL_IMPORTS_OK:
            raise ImportError(
                "FAISSManagementServiceは、不足しているCitadelモジュールのインポートのため初期化できません。"
            )
        if not VSS_FAISS_AVAILABLE:
            raise ImportError(
                "FAISSライブラリが利用できません。FMSはFAISSなしでは動作できません。"
            )
        if not isinstance(vector_storage_service, VectorStorageService):
            raise TypeError(
                f"FAISSManagementServiceにはVectorStorageServiceが必要ですが、{type(vector_storage_service)}が指定されました"
            )

        # ----------------------------------------------------------------------
        # 1) コア属性
        # ----------------------------------------------------------------------
        self.system_config = system_config or {}
        self.vss = vector_storage_service
        self.global_tracker = global_tracker_instance

        # ----------------------------------------------------------------------
        # 2) デフォルトのFAISS設定（次元+メトリック）を解決
        # ----------------------------------------------------------------------
        default_faiss_cfg_payload: Optional[
            Union[FaissIndexDefaultConfigSchema, Dict[str, Any]]
        ] = None

        logger.info(
            f"[F956][CAPS:FMS_INIT] FAISS設定を解決中 | "
            f"system_config_type={type(system_config)}"
        )

        # 安全なランタイム処理：TypedDictはisinstanceを使用できない
        if hasattr(system_config, "default_faiss_index_config"):
            # Pydantic/dataclassブランチ
            default_faiss_cfg_payload = getattr(system_config, "default_faiss_index_config")
            logger.info("[F956][CAPS:FMS_INIT] FAISS設定にオブジェクトの属性を使用")
        elif isinstance(system_config, dict):
            default_faiss_cfg_payload = system_config.get("default_faiss_index_config")
            logger.info("[F956][CAPS:FMS_INIT] FAISS設定にdict.getを使用")
        else:
            logger.warning(
                "[F956][CAPS:FMS_INIT_WARN] system_configの型がサポートされていません "
                f"{type(system_config)}; VSSのデフォルトで続行します。"
            )

        # VSSへのフォールバック付きでデフォルトを解決
        self.fms_default_dim_ref = (
            getattr(default_faiss_cfg_payload, "vector_dim", None)
            or (default_faiss_cfg_payload.get("vector_dim") if isinstance(default_faiss_cfg_payload, dict) else None)
            or self.vss.embedding_dim
        )

        self.fms_default_metric_ref = (
            getattr(default_faiss_cfg_payload, "metric_type", None)
            or (default_faiss_cfg_payload.get("metric_type") if isinstance(default_faiss_cfg_payload, dict) else None)
            or self.vss.default_metric_type
        )
        self.fms_default_metric_ref = self.fms_default_metric_ref.upper()




        # ----------------------------------------------------------------------
        # 3) ロギング/テレメトリ
        # ----------------------------------------------------------------------
        logger.info(
            f"[F956][CAPS:FMS_INIT] FAISSManagementServiceが初期化されました。"
            f"VectorStorageService: dim={self.vss.embedding_dim}, metric={self.vss.default_metric_type}. "
            f"FMS Default: dim={self.fms_default_dim_ref}, metric={self.fms_default_metric_ref}."
        )

        if self.global_tracker:
            logger.info("[F956][CAPS:FMS_INIT] FMSは拡張メタデータ操作のためにGlobalMetadataTrackerと統合されました。")
        else:
            logger.warning("[F956][CAPS:FMS_INIT] FMSはGlobalMetadataTrackerなしで初期化されました。メタデータ操作は制限されます。")

        # オプションのGuardianLoggerイベント
        try:
            guardian_logger.log_event(
                component="FAISSManagementService",
                event_type=LogEventType.COMPONENT_INITIALIZED,
                message=f"FAISSManagementService online (default_dim={self.fms_default_dim_ref}, metric={self.fms_default_metric_ref})",
                srs_code=SRSCode.F956,
                severity=LogSeverity.INFO,
                context={
                    "vss_dim": self.vss.embedding_dim,
                    "vss_metric": self.vss.default_metric_type,
                    "fms_dim": self.fms_default_dim_ref,
                    "fms_metric": self.fms_default_metric_ref,
                    "global_tracker_enabled": bool(self.global_tracker),
                },
            )
        except Exception as log_exc:
            logger.error(f"[F956][CAPS:FMS_INIT_ERR] GuardianLogger log_eventに失敗しました: {log_exc}")

    # ----------------------------------------------------------------------
    # 準備完了チェック
    # ----------------------------------------------------------------------
    def is_ready(self) -> bool:
        """
        サービスとその依存関係が準備完了かどうかを確認します。

        Returns:
            bool: サービスが使用準備完了の場合はTrue、そうでない場合はFalse。
        """
        ready = getattr(self.vss, "_initialized_successfully", False) and VSS_FAISS_AVAILABLE
        logger.debug(f"[F956][CAPS:FMS_READY] FAISSManagementService.is_ready -> {ready}")
        return ready

    def _preprocess_vector_input(self, vector: np.ndarray, fingerprint: str, operation: str) -> Optional[List[float]]:
        """NumPyベクトル入力を前処理して検証します。"""
        if not NUMPY_AVAILABLE or np is None:
             logger.error(f"FMS {operation} Error: NumPyが'{fingerprint}'のベクトル処理に利用できません。"); return None
        if not isinstance(vector, np.ndarray):
            logger.error(f"FMS {operation} Error: '{fingerprint}'の入力'vector'はNumPy配列である必要がありますが、{type(vector)}が指定されました。")
            return None
        vector_list: List[float]
        if vector.ndim == 1: vector_list = vector.tolist()
        elif vector.ndim == 2 and vector.shape[0] == 1: vector_list = vector[0].tolist()
        else:
            logger.error(f"FMS {operation} Error: '{fingerprint}'の入力'vector'はサポートされていない形状{vector.shape}です。1Dまたは(1, N)が期待されます。")
            return None
        if len(vector_list) != self.vss.embedding_dim:
            logger.error(f"FMS {operation} Error: '{fingerprint}'のベクトル次元が不一致です。VSSは次元{self.vss.embedding_dim}を期待していますが、{len(vector_list)}が指定されました。")
            return None
        return vector_list

    def add_vector(self, index_name: str, fingerprint: str, vector: np.ndarray, metadata: Optional[Dict[str, Any]] = None,
                   save_after: bool = True) -> bool:
        """
        指定されたFAISSインデックスにベクトルを追加します。

        Args:
            index_name (str): ベクトルを追加するインデックスの名前。
            fingerprint (str): ベクトルの一意の識別子。
            vector (np.ndarray): NumPy配列として追加するベクトル。
            metadata (Optional[Dict[str, Any]], optional): ベクトルに関連付けるメタデータ。
                デフォルトはNone。
            save_after (bool, optional): ベクトル追加後にインデックスをディスクに保存するかどうか。
                デフォルトはTrue。

        Returns:
            bool: ベクトルが正常に追加された場合はTrue、そうでない場合はFalse。
        """
        logger.debug(f"FMS: インデックス'{index_name}'のFP '{fingerprint}'にベクトルを追加しようとしています。")
        vector_list = self._preprocess_vector_input(vector, fingerprint, "Add")
        if vector_list is None: return False

        fms_operational_meta = metadata.copy() if metadata else {}
        fms_operational_meta.setdefault("_fms_operation_timestamp_utc", datetime.now(timezone.utc).isoformat())
        fms_operational_meta.setdefault("_fms_origin", "FAISSManagementService") # FMSによって追加されたメタデータをマーク

        success = self.vss.add_vector(
            index_name=index_name, fingerprint=fingerprint, vector_embedding=vector_list,
            metadata=fms_operational_meta, save_after=save_after
        )

        if success: logger.info(f"FMS: VSSを介してベクトル'{fingerprint}'を'{index_name}'に正常に追加しました。")
        else: logger.warning(f"FMS: VSSを介してベクトル'{fingerprint}'を'{index_name}'に追加できませんでした。")
        # FMSがこのフィンガープリントのメタデータのためにGTMと対話する必要がある場合：
        # if self.global_tracker and success:
        #     self.global_tracker.bulk_update_fields(fingerprint, {"fms_last_add_status": "success", "last_updated_by_fms": datetime.now(timezone.utc).isoformat()})
        return success

    def search_vectors(self, index_name: str, query_vector: np.ndarray, k: int = 5,
                       filter_metadata_fn: Optional[Callable[[Dict[str, Any]], bool]] = None
                       ) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        指定されたインデックスで最も類似したベクトルを検索します。

        Args:
            index_name (str): 検索するインデックスの名前。
            query_vector (np.ndarray): 検索するベクトル。
            k (int, optional): 返す最近傍の数。
                デフォルトは5。
            filter_metadata_fn (Optional[Callable[[Dict[str, Any]], bool]], optional):
                メタデータに基づいて結果をフィルタリングする関数。デフォルトはNone。

        Returns:
            List[Tuple[str, float, Dict[str, Any]]]: 各タプルがフィンガープリント、
                類似度スコア、および一致するベクトルのメタデータを含むタプルのリスト。
        """
        logger.debug(f"FMS: インデックス'{index_name}'でトップ{k}個のベクトルを検索リクエスト。")
        query_list = self._preprocess_vector_input(query_vector, "query_vector", "Search")
        if query_list is None: return []

        results = self.vss.search_vectors(
            index_name=index_name, query_vector_embedding=query_list, top_k=k, filter_metadata_fn=filter_metadata_fn
        )
        logger.debug(f"FMS: VSSを介した'{index_name}'での検索で{len(results)}件の結果が返されました。")
        return results

    def reconstruct_vector(self, index_name: str, fingerprint: str) -> Optional[np.ndarray]:
        """
        フィンガープリントを使用してインデックスからベクトルを再構築します。

        Args:
            index_name (str): インデックスの名前。
            fingerprint (str): 再構築するベクトルのフィンガープリント。

        Returns:
            Optional[np.ndarray]: 再構築されたベクトルをNumPy配列として、または
                見つからない場合はNone。
        """
        logger.debug(f"FMS: インデックス'{index_name}'のFP '{fingerprint}'の再構築リクエスト。")
        reconstructed_vec_np = self.vss.get_vector_by_fingerprint(index_name=index_name, fingerprint=fingerprint)
        if reconstructed_vec_np is None:
            logger.info(f"FMS: VSSによってインデックス'{index_name}'でフィンガープリント'{fingerprint}'のベクトルが見つかりませんでした。")
        else:
            logger.info(f"FMS: VSSからインデックス'{index_name}'のフィンガープリント'{fingerprint}'のベクトルが正常に再構築されました。")
        return reconstructed_vec_np

    def get_vector_metadata(self, index_name: str, fingerprint: str) -> Optional[Dict[str,Any]]:
        """
        特定のベクトルのメタデータを取得します。

        Args:
            index_name (str): インデックスの名前。
            fingerprint (str): ベクトルのフィンガープリント。

        Returns:
            Optional[Dict[str,Any]]: メタデータ辞書、または見つからない場合はNone。
        """
        logger.debug(f"FMS: インデックス'{index_name}'のFP '{fingerprint}'のメタデータ取得リクエスト。")
        # これはVSSによって保存されたメタデータを取得します（FMSが追加時にVSSに渡したものを含む）
        vss_metadata = self.vss.get_metadata(index_name=index_name, fingerprint=fingerprint)

        # 例：FMSがGTMデータとオーバーレイまたは結合する場合：
        # if self.global_tracker and vss_metadata is not None:
        #     gtm_metadata = self.global_tracker.get_metadata(fingerprint, include_dynamic_fields=True)
        #     if gtm_metadata:
        #         combined_metadata = gtm_metadata.copy() # GTMデータから開始
        #         combined_metadata.update(vss_metadata)  # VSS固有のメタデータをオーバーレイ/追加
        #         # キーの衝突に注意し、マージ戦略を決定する
        #         return combined_metadata
        return vss_metadata

    def update_vector_metadata(self, index_name: str, fingerprint: str, updates: Dict[str, Any], save_after: bool = True) -> bool:
        """
        特定のベクトルのメタデータを更新します。

        Args:
            index_name (str): インデックスの名前。
            fingerprint (str): 更新するベクトルのフィンガープリント。
            updates (Dict[str, Any]): 更新するメタデータフィールドの辞書。
            save_after (bool, optional): 更新後にインデックスを保存するかどうか。
                デフォルトはTrue。

        Returns:
            bool: 更新が成功した場合はTrue、そうでない場合はFalse。
        """
        logger.debug(f"FMS: インデックス'{index_name}'のFP '{fingerprint}'のメタデータ更新試行。")
        # FMSは更新を前処理したり、VSS管理のメタデータで更新が発生していることをGTMにログ記録したりする場合があります
        # updates["_fms_last_meta_update_utc"] = datetime.now(timezone.utc).isoformat()
        return self.vss.update_metadata(index_name=index_name, fingerprint=fingerprint, metadata_updates=updates, save_after=save_after)

    def remove_vector(self, index_name: str, fingerprint: str, save_after: bool = True) -> bool:
        """
        インデックスからベクトルを削除します。

        Args:
            index_name (str): インデックスの名前。
            fingerprint (str): 削除するベクトルのフィンガープリント。
            save_after (bool, optional): 削除後にインデックスを保存するかどうか。
                デフォルトはTrue。

        Returns:
            bool: ベクトルが正常に削除された場合はTrue、そうでない場合はFalse。
        """
        logger.debug(f"FMS: インデックス'{index_name}'のFP '{fingerprint}'のベクトル削除試行。")
        success = self.vss.remove_vector(index_name=index_name, fingerprint=fingerprint, save_after=save_after)
        # if self.global_tracker and success:
        #     self.global_tracker.update_record_status(fingerprint, "REMOVED_FROM_VSS_INDEX", {"index_name": index_name}) # 仮説的なGTMメソッド
        return success

    def count_vectors_in_index(self, index_name: str) -> int:
        """
        インデックス内のベクトル数をカウントします。

        Args:
            index_name (str): インデックスの名前。

        Returns:
            int: インデックス内のベクトル数。
        """
        return self.vss.count_vectors(index_name=index_name)

    def list_all_fingerprints_in_index(self, index_name: str) -> List[str]:
        """
        インデックス内のすべてのベクトルフィンガープリントをリストします。

        Args:
            index_name (str): インデックスの名前。

        Returns:
            List[str]: インデックス内のすべてのフィンガープリントのリスト。
        """
        return self.vss.list_fingerprints(index_name=index_name)

    def save_specific_index(self, index_name: str) -> bool:
        """
        特定のインデックスを明示的にディスクに保存します。

        Args:
            index_name (str): 保存するインデックスの名前。

        Returns:
            bool: 成功した場合はTrue、そうでない場合はFalse。
        """
        logger.info(f"FMS: インデックス'{index_name}'の明示的な保存リクエスト。VSSに委任します。")
        try:
            # VSSが公開メソッドを持っているか、これがVSSの_save_index_componentsに委任すると仮定
            # VSSが変更時に自動的に保存する場合、これはno-opまたは明示的なフラッシュ用かもしれません。
            self.vss._save_index_components(index_name) # または公開のvss.save_index(name)
            return True
        except Exception as e:
            logger.error(f"FMS: VSSを介してインデックス'{index_name}'を明示的に保存中にエラー: {e}", exc_info=True)
            return False

    def save_all_indexes(self):
        """管理されているすべてのインデックスをディスクに保存します。"""
        logger.info("FMS: すべてのインデックスを保存するリクエスト。VSSに委任します。")
        self.vss.save_all_managed_indexes()

    def get_index_statistics(self, index_name: str) -> Optional[Dict[str, Any]]:
        """
        特定のインデックスの統計情報を取得します。

        Args:
            index_name (str): インデックスの名前。

        Returns:
            Optional[Dict[str, Any]]: 統計情報の辞書、またはインデックスが
                存在しない場合はNone。
        """
        return self.vss.get_index_stats(index_name=index_name)

    def run_health_check(self) -> Dict[str, Any]:
        """
        サービスとその依存関係のヘルスチェックを実行します。

        Returns:
            Dict[str, Any]: サービスとそのコンポーネントのヘルスステータスを
                含む辞書。
        """
        logger.info("FMSはヘルスチェックを実行し、VSSとGMTのヘルスを含めます。")
        vss_health = self.vss.health_check()
        fms_imports_ok = CITADEL_IMPORTS_OK and NUMPY_AVAILABLE and VSS_FAISS_AVAILABLE

        is_gmt_ok = True  # トラッカーが存在しない場合はOKと仮定
        gmt_health_status = "NOT_CONFIGURED"
        if self.global_tracker:
            if hasattr(self.global_tracker, 'is_ready') and callable(self.global_tracker.is_ready):
                is_gmt_ok = self.global_tracker.is_ready()
                gmt_health_status = "READY" if is_gmt_ok else "NOT_READY"
            else:
                gmt_health_status = "STATUS_UNKNOWN" # 準備完了チェックメソッドなし

        is_vss_ok = vss_health.get("overall_health_status") == "HEALTHY"

        fms_status = {
            "fms_overall_status": "OPERATIONAL" if fms_imports_ok and is_vss_ok and is_gmt_ok else "DEGRADED",
            "fms_imports_ok": fms_imports_ok,
            "fms_numpy_available": NUMPY_AVAILABLE,
            "vss_dependency_health": vss_health,
            "gmt_dependency_status": gmt_health_status
        }
        return fms_status
    def close(self):
        """正常なシャットダウンメソッドのプレースホルダー。"""
        logger.info("FAISSManagementService close()が呼び出されました。基盤となるVSSのライフサイクルは通常Hubによって管理されます。")
        pass # VSSインスタンスは外部（例：Hub）で管理される

    def __del__(self):
        pass

# --- メインテストブロック（以前提供された時間と詳細ロギングを含むものを使用）---
if __name__ == "__main__":
    # <<< ここに以前のメッセージから__main__ブロックを貼り付け >>>
    # 以下で始まるもの：
    # import time
    # logging.basicConfig(...)
    # そして、fms_instance_for_test_mainなどを閉じるfinallyブロックで終わるもの。
    # これは重要です：すでに持っていて確認済みの__main__ブロックを使用してください。
    # この応答の完全性のために、最新の__main__を貼り付けます。

    import time
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')

    TestFMS_DossierSysConfig_main: Any = dict
    TestFMS_VSS_main: Any = None
    TestFMS_GTM_main: Any = None
    TestFMS_cds_constants_main: Any = None
    TestFMS_sanitize_filename_main: Any = lambda name: name

    try:
        from config.schemas import DossierSystemConfigSchema as Actual_DossierSysConfig_main
        from SERVICE_SYSTEM.VECTOR_STORAGE_SERVICE import VectorStorageService as Actual_VSS_main # 明確化のために名前変更
        from SERVICE_SYSTEM.global_tracker_service import GlobalMetadataTracker as Actual_GTM_main
        from utils import constants as Actual_cds_constants_main
        from utils.common_utils import sanitize_filename_component as actual_sanitize_filename_component_main

        TestFMS_DossierSysConfig_main = Actual_DossierSysConfig_main
        TestFMS_VSS_main = Actual_VSS_main # テスト用に特別にインポートされたVSSを使用
        TestFMS_GTM_main = Actual_GTM_main
        TestFMS_cds_constants_main = Actual_cds_constants_main
        TestFMS_sanitize_filename_main = actual_sanitize_filename_component_main
        logger.info("FMSセルフテストのために実際のCitadelモジュールを正常にインポートしました。")
    except ImportError as e_main_imports_fms:
        logger.critical(f"FMSセルフテスト: 致命的なインポートエラー({e_main_imports_fms})。フォールバックを使用します。テストは大幅に制限されるか、失敗します。", exc_info=True)
        class TestFMS_cds_constants_fallback_main_cls:
            DEFAULT_EMBEDDING_DIM = DEFAULT_EMBEDDING_DIM_FMS
            DEFAULT_FAISS_INDEX_FILENAME_BASE = 'index'; DEFAULT_FAISS_INDEX_FILENAME_SUFFIX = '.faiss'
            DEFAULT_FAISS_MAP_FILENAME_BASE = 'id_map'; DEFAULT_FAISS_MAP_FILENAME_SUFFIX = '.index_map.json'
        TestFMS_cds_constants_main = TestFMS_cds_constants_fallback_main_cls()

    main_config_title_fms = "FMS Test Config (AI Diagnostics Enabled)"
    logger.info(f"--- FAISSManagementService Self-Test Suite (using VSS) ({main_config_title_fms}) ---")

    if not VSS_FAISS_AVAILABLE:
        logger.critical("CRITICAL: FAISS not available for VSS. FMS tests cannot run. Exiting.")
        sys.exit(1)
    if not NUMPY_AVAILABLE:
        logger.critical("CRITICAL: NumPy not available. FMS tests cannot run. Exiting.")
        sys.exit(1)
    if TestFMS_VSS_main is None or not isinstance(TestFMS_VSS_main, type):
        logger.critical("CRITICAL: VectorStorageService class (TestFMS_VSS_main) could not be imported/set. Cannot run FMS tests. Exiting.")
        sys.exit(1)

    temp_test_root_fms = ROOT / "LEDGER" / "SYSTEM_SERVICE_LEDGER" / "faiss_management_service_tests"
    temp_test_root_fms.mkdir(parents=True, exist_ok=True)

    mock_fms_paths_data_main = {
        "faiss_service_paths": { "default_faiss_root_dir": str(temp_test_root_fms / "vss_indexes_for_fms_test") },
        "council_specific_paths": { "gmt_database_path": str(temp_test_root_fms / "fms_gtm_data" / "gmt.db") }
    }
    _default_dim_for_test_main_val = getattr(TestFMS_cds_constants_main, 'DEFAULT_EMBEDDING_DIM', DEFAULT_EMBEDDING_DIM_FMS)
    mock_fms_default_index_config_data_main = { "vector_dim": _default_dim_for_test_main_val, "metric_type": "L2"}
    mock_fms_system_config_input_main = { "paths": mock_fms_paths_data_main, "default_faiss_index_config": mock_fms_default_index_config_data_main }

    mock_fms_config_obj_main: Union[DossierSystemConfigSchema, Dict[str, Any]]
    if TestFMS_DossierSysConfig_main is not dict and hasattr(TestFMS_DossierSysConfig_main, 'model_validate'):
        try: mock_fms_config_obj_main = TestFMS_DossierSysConfig_main.model_validate(mock_fms_system_config_input_main)
        except Exception as e_pydantic_val_fms:
            logger.warning(f"FMSモック設定のPydantic検証に失敗しました: {e_pydantic_val_fms}。辞書にフォールバックします。")
            mock_fms_config_obj_main = mock_fms_system_config_input_main
    else: mock_fms_config_obj_main = mock_fms_system_config_input_main

    vss_instance_for_fms_test_main = None
    fms_instance_for_test_main = None
    gtm_instance_for_fms_test_main = None

    try:
        vss_base_dir_main = Path(mock_fms_paths_data_main["faiss_service_paths"]["default_faiss_root_dir"])
        vss_base_dir_main.mkdir(parents=True, exist_ok=True)
        test_idx_name_for_fms_cleanup_main = "fms_test_idx_via_vss"
        sanitized_cleanup_name_main = TestFMS_sanitize_filename_main(test_idx_name_for_fms_cleanup_main)
        vss_idx_dir_cleanup_main = vss_base_dir_main / sanitized_cleanup_name_main
        if (vss_idx_dir_cleanup_main / f"{sanitized_cleanup_name_main}.index").exists(): (vss_idx_dir_cleanup_main / f"{sanitized_cleanup_name_main}.index").unlink()
        if (vss_idx_dir_cleanup_main / f"{sanitized_cleanup_name_main}_fp_data_map.json").exists(): (vss_idx_dir_cleanup_main / f"{sanitized_cleanup_name_main}_fp_data_map.json").unlink()
        vss_idx_dir_cleanup_main.mkdir(parents=True, exist_ok=True)
        logger.info(f"FMSテストクリーンアップ: VSSインデックス'{test_idx_name_for_fms_cleanup_main}'のファイルが{vss_idx_dir_cleanup_main}でクリアされていることを確認しました。")

        vss_instance_for_fms_test_main = TestFMS_VSS_main(vector_indexes_base_dir=vss_base_dir_main, embedding_dim=_default_dim_for_test_main_val)
        logger.info(f"FMSテスト用にVectorStorageServiceインスタンスが作成されました。ベースディレクトリ: {vss_base_dir_main}")

        if TestFMS_GTM_main is not None and hasattr(TestFMS_GTM_main, '__call__'):
            gtm_db_path_fms_main = Path(mock_fms_paths_data_main["council_specific_paths"]["gmt_database_path"])
            gtm_db_path_fms_main.parent.mkdir(parents=True, exist_ok=True)
            if gtm_db_path_fms_main.exists(): gtm_db_path_fms_main.unlink()
            gtm_instance_for_fms_test_main = TestFMS_GTM_main(db_path=str(gtm_db_path_fms_main))
            logger.info(f"FMSテスト用にGlobalMetadataTrackerインスタンスが作成されました。DB: {gtm_db_path_fms_main}")
            # >>> この行を追加: <<<
            if gtm_instance_for_fms_test_main and hasattr(gtm_instance_for_fms_test_main, 'connect'):
                gtm_instance_for_fms_test_main.connect()
        fms_instance_for_test_main = FAISSManagementService(
            system_config=mock_fms_config_obj_main,
            vector_storage_service=vss_instance_for_fms_test_main,
            global_tracker_instance=gtm_instance_for_fms_test_main
        )
        logger.info("テスト用にFAISSManagementServiceインスタンスが作成されました。")

        logger.info("\n--- FMSテスト: ヘルスチェック ---")
        health_status_main = fms_instance_for_test_main.run_health_check()
        assert health_status_main.get("fms_overall_status") == "OPERATIONAL", f"FMSヘルスチェックに失敗しました: {health_status_main}"
        logger.info(f"FMSヘルスチェック: {health_status_main.get('fms_overall_status')}, VSSヘルス: {health_status_main.get('vss_dependency_health', {}).get('overall_health_status')}")

        test_idx_name_main = "fms_test_idx_via_vss"
        test_dim_main = mock_fms_default_index_config_data_main['vector_dim']
        fp1_main = "fms_vss_fp001"
        vec1_np_main = np.random.rand(1, test_dim_main).astype("float32") # type: ignore
        meta1_main = {"description": "Test vector for FMS via VSS", "val": 1, "fms_test_marker": True}

        logger.info(f"\n--- FMSテスト: ベクトル'{fp1_main}'を'{test_idx_name_main}'に追加 ---")
        logger.debug(f"DEBUG (Add): fp='{fp1_main}', vec_norm={np.linalg.norm(vec1_np_main):.4f}, head={vec1_np_main[0, :5]}, tail={vec1_np_main[0, -5:]}") #type: ignore
        t_start_main = time.time()
        add_ok_main = fms_instance_for_test_main.add_vector(test_idx_name_main, fp1_main, vec1_np_main, meta1_main)
        logger.debug(f"経過時間(追加): {(time.time() - t_start_main):.3f}s")
        assert add_ok_main, f"FMSはベクトル{fp1_main}の追加に失敗しました"
        logger.info(f"FMS: ベクトル{fp1_main}はVSSを介して正常に追加されました。")
        assert fms_instance_for_test_main.count_vectors_in_index(test_idx_name_main) == 1

        logger.info(f"\n--- FMSテスト: '{fp1_main}'のベクトルメタデータを取得 ---")
        retrieved_meta_main = fms_instance_for_test_main.get_vector_metadata(test_idx_name_main, fp1_main)
        assert retrieved_meta_main is not None, f"FMS get_vector_metadataが{fp1_main}で失敗しました"
        assert retrieved_meta_main.get("fms_test_marker") is True, "FMSメタデータマーカーが見つかりません。"
        # VSS管理のメタデータでFMSが追加した運用メタデータを直接フラットなメタデータ辞書で確認
        assert "_fms_operation_timestamp_utc" in retrieved_meta_main, \
            "FMS追加タイムスタンプがメタデータにありません（GMTからのフラットな構造が期待されます）。"

        logger.info(
            f"FMS: '{fp1_main}'のメタデータがFMSマーカー付きで正常に取得されました:\n{json.dumps(retrieved_meta_main, indent=2)}"
        )


        logger.info(f"\n--- FMSテスト: ベクトル'{fp1_main}'を再構築 ---")
        t_start_main = time.time()
        recon_vec1_main = fms_instance_for_test_main.reconstruct_vector(test_idx_name_main, fp1_main)
        logger.debug(f"経過時間(再構築): {(time.time() - t_start_main):.3f}s")
        assert recon_vec1_main is not None, f"FMSの{fp1_main}の再構築がNoneを返しました"
        assert recon_vec1_main.shape == (1, test_dim_main), f"FMSの{fp1_main}の再構築形状が不一致です、取得値: {recon_vec1_main.shape}"
        assert np.allclose(recon_vec1_main, vec1_np_main, atol=1e-6), f"FMSの{fp1_main}の再構築内容が不一致です"
        logger.info(f"FMS: ✅ ベクトル{fp1_main}が正常に再構築されました。")

        logger.info(f"\n--- FMSテスト: ベクトル'{fp1_main}'を検索 ---")
        t_start_main = time.time()
        search_res_main = fms_instance_for_test_main.search_vectors(test_idx_name_main, vec1_np_main, k=1)
        logger.debug(f"経過時間(検索): {(time.time() - t_start_main):.3f}s")
        assert len(search_res_main) == 1, f"FMSの{fp1_main}の検索が1件の結果を返しませんでした、取得値: {len(search_res_main)}"
        s_fp_main, s_score_main, s_meta_main = search_res_main[0]
        assert s_fp_main == fp1_main, f"FMSの検索が間違ったフィンガープリントを返しました: {s_fp_main}、期待値: {fp1_main}"
        assert s_score_main > 0.999, f"FMSの完全一致検索の類似度スコアが低すぎます: {s_score_main}"
        assert s_meta_main.get("fms_test_marker") is True, "FMSメタデータマーカーが検索結果にありません。"
        logger.info(f"FMS: ✅ {fp1_main}の検索成功、スコア: {s_score_main:.4f}")

        logger.info(f"\n--- FAISSManagementService Self-Test Suite ({main_config_title_fms}) Complete ---")

    except Exception as e_main_fms_test:
        logger.critical(f"FAISSManagementService (using VSS) __main__実行中に致命的なエラーが発生しました: {e_main_fms_test}", exc_info=True)
    finally:
        if fms_instance_for_test_main and hasattr(fms_instance_for_test_main, 'close'): # closeが存在するか確認
            fms_instance_for_test_main.close()
        elif vss_instance_for_fms_test_main:
            vss_instance_for_fms_test_main.close()

        if gtm_instance_for_fms_test_main and hasattr(gtm_instance_for_fms_test_main, 'close'):
            gtm_instance_for_fms_test_main.close()

        # import shutil
        # temp_fms_test_dir_path_main = _PROJECT_ROOT_FOR_SERVICE_BOOTSTRAP / "TEMP_FMS_WITH_VSS_TESTS"
        # if temp_fms_test_dir_path_main.exists() and "KEEP_TEMP_FMS_FILES" not in os.environ:
        #     logger.info(f"Cleaning up FMS test directory: {temp_fms_test_dir_path_main}")
        #     # shutil.rmtree(temp_fms_test_dir_path_main)
