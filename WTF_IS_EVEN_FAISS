# D:\MASTER_CITADEL\SERVICE_SYSTEM\faiss_management_service.py


# --- Bootstrap Path Injection (For Standalone Execution) ---
import sys
from pathlib import Path
import time # For __main__ test timing
from datetime import datetime, timezone

_SERVICE_FILE_PATH_FOR_BOOTSTRAP = Path(__file__).resolve()
_PROJECT_ROOT_FOR_SERVICE_BOOTSTRAP = _SERVICE_FILE_PATH_FOR_BOOTSTRAP.parents[1]  # SERVICE_SYSTEM parent is MASTER_CITADEL
if str(_PROJECT_ROOT_FOR_SERVICE_BOOTSTRAP) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_FOR_SERVICE_BOOTSTRAP))
    print(f"[FAISSManagementService Bootstrap] Added {_PROJECT_ROOT_FOR_SERVICE_BOOTSTRAP} to sys.path for direct execution.")
# --- End Bootstrap ---
# ---------------------------------------------------------------------------
# FAISSManagementService Bootstrap
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
sys.path.insert(0, str(CURRENT_FILE.parents[1]))  # Ensure MASTER_CITADEL is in path

logger = logging.getLogger("FAISSManagementService")
if not logger.handlers:
    ch = logging.StreamHandler()
    ch.setFormatter(logging.Formatter("%(asctime)s - %(name)s [%(levelname)s] - %(message)s"))
    logger.addHandler(ch)
logger.setLevel(logging.DEBUG)

# ---------------------------------------------------------------------------
# Citadel Imports with Diagnostics
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
# Optional: log the files explicitly to verify
# ---------------------------------------------------------------------------
for module_name in ["LOGGING_SYSTEM", "LOGGING_SYSTEM.FR_ENUM", "LOGGING_SYSTEM.FR_ENUM.F921_schemas"]:
    try:
        mod = __import__(module_name, fromlist=['*'])
        logger.info(f"[F956][CAPS:FMS_BOOT] Verified import path for {module_name}: {Path(mod.__file__).resolve()}")
    except Exception as verify_exc:
        logger.warning(f"[F956][CAPS:FMS_BOOT_WARN] Could not verify module {module_name}: {verify_exc}")


r"""
Citadel Dossier System - FAISS Management Service
File Version: 3.1.1
Last Updated: 2025-08-03

Purpose:
Provides a high-level API for managing and interacting with vector indexes. This service
delegates all low-level FAISS storage, retrieval, indexing, and indexing, and direct vector data
reconstruction to an instance of VectorStorageService. FAISSManagementService focuses on
orchestrating vector operations and can optionally integrate with GlobalMetadataTracker
for managing richer metadata associated with vectors.

Key Design Principles:
- Decoupling: Separates high-level vector operation requests from the underlying storage mechanism.
- Delegation: Relies entirely on VectorStorageService for core vector data and FAISS interactions.
- Service Composability: Can work alongside GlobalMetadataTracker.
- Focused Responsibility: Does not manage FAISS files or complex ID maps directly.
"""

import logging
from typing import Dict, Any, List, Tuple, Optional, Union, Callable
import json # Added for __main__ block if it uses json.dumps

# --- NumPy ---
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False; np = None #type: ignore
    logging.getLogger(__name__).warning("NumPy not available for FMS. Input vector types might be restricted.")

# --- Citadel Ecosystem Imports ---
from AGENTS.CDS_SYSTEM import CDS_CONFIG
ROOT = CDS_CONFIG.ROOT
CDS_DATA_PATHS = CDS_CONFIG.CDS_DATA_PATHS
CDS_META = CDS_CONFIG.CDS_META

VSS_FAISS_AVAILABLE = False
CITADEL_IMPORTS_OK = False
logger_fms_init = logging.getLogger(__name__)  # Initial logger for import phase

try:
    from SERVICE_SYSTEM.VECTOR_STORAGE_SERVICE import (
        VectorStorageService,
        FAISS_AVAILABLE as VSS_FAISS_AVAILABLE_FROM_MODULE
    )
    from SERVICE_SYSTEM.GLOBAL_TRACKER_SERVICE import GlobalMetadataTracker


    VSS_FAISS_AVAILABLE = VSS_FAISS_AVAILABLE_FROM_MODULE
    CITADEL_IMPORTS_OK = True
    logger = logging.getLogger(__name__)  # Final logger instance

except ImportError as e_fms_imports:
    logger_fms_init.critical(
        "[FAISSManagementService Init Error] Failed to import critical Citadel modules: "
        f"{e_fms_imports}. Service will be non-functional.",
        exc_info=True
    )
    # Define fallback stubs only if not already globally declared
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
    FAISS Management Service (FMS)
    ---------------------------------
    - Wraps VectorStorageService with higher-level FAISS index management
    - Optionally integrates GlobalMetadataTracker for metadata operations
    - Emits GuardianLogger CAPS/SRS-compliant telemetry for observability
    """

    def __init__(
        self,
        system_config: Union[DossierSystemConfigSchema, Dict[str, Any]],
        vector_storage_service: VectorStorageService,
        global_tracker_instance: Optional[GlobalMetadataTracker] = None
    ):
        # ----------------------------------------------------------------------
        # 0) Defensive Checks
        # ----------------------------------------------------------------------
        if not CITADEL_IMPORTS_OK:
            raise ImportError(
                "FAISSManagementService cannot initialize due to missing Citadel module imports."
            )
        if not VSS_FAISS_AVAILABLE:
            raise ImportError(
                "FAISS library not available. FMS cannot operate without FAISS."
            )
        if not isinstance(vector_storage_service, VectorStorageService):
            raise TypeError(
                f"FAISSManagementService requires VectorStorageService, got {type(vector_storage_service)}"
            )

        # ----------------------------------------------------------------------
        # 1) Core Attributes
        # ----------------------------------------------------------------------
        self.system_config = system_config or {}
        self.vss = vector_storage_service
        self.global_tracker = global_tracker_instance

        # ----------------------------------------------------------------------
        # 2) Resolve default FAISS config (dim + metric)
        # ----------------------------------------------------------------------
        default_faiss_cfg_payload: Optional[
            Union[FaissIndexDefaultConfigSchema, Dict[str, Any]]
        ] = None

        logger.info(
            f"[F956][CAPS:FMS_INIT] Resolving FAISS config | "
            f"system_config_type={type(system_config)}"
        )

        # Safe runtime handling: TypedDict can't use isinstance
        if hasattr(system_config, "default_faiss_index_config"):
            # Pydantic/dataclass branch
            default_faiss_cfg_payload = getattr(system_config, "default_faiss_index_config")
            logger.info("[F956][CAPS:FMS_INIT] Using attribute from object for FAISS config")
        elif isinstance(system_config, dict):
            default_faiss_cfg_payload = system_config.get("default_faiss_index_config")
            logger.info("[F956][CAPS:FMS_INIT] Using dict.get for FAISS config")
        else:
            logger.warning(
                "[F956][CAPS:FMS_INIT_WARN] system_config is of unsupported type "
                f"{type(system_config)}; proceeding with VSS defaults."
            )

        # Resolve defaults with fallbacks to VSS
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
        # 3) Logging / Telemetry
        # ----------------------------------------------------------------------
        logger.info(
            f"[F956][CAPS:FMS_INIT] FAISSManagementService initialized. "
            f"VectorStorageService: dim={self.vss.embedding_dim}, metric={self.vss.default_metric_type}. "
            f"FMS Default: dim={self.fms_default_dim_ref}, metric={self.fms_default_metric_ref}."
        )

        if self.global_tracker:
            logger.info("[F956][CAPS:FMS_INIT] FMS integrated with GlobalMetadataTracker for extended metadata operations.")
        else:
            logger.warning("[F956][CAPS:FMS_INIT] FMS initialized without GlobalMetadataTracker; metadata ops limited.")

        # Optional GuardianLogger event
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
            logger.error(f"[F956][CAPS:FMS_INIT_ERR] GuardianLogger log_event failed: {log_exc}")

    # ----------------------------------------------------------------------
    # Readiness Check
    # ----------------------------------------------------------------------
    def is_ready(self) -> bool:
        """
        Returns True if FMS is ready:
        - VSS initialized successfully
        - FAISS library available
        - Optional: Global tracker doesn't block readiness
        """
        ready = getattr(self.vss, "_initialized_successfully", False) and VSS_FAISS_AVAILABLE
        logger.debug(f"[F956][CAPS:FMS_READY] FAISSManagementService.is_ready -> {ready}")
        return ready

    def _preprocess_vector_input(self, vector: np.ndarray, fingerprint: str, operation: str) -> Optional[List[float]]:
        if not NUMPY_AVAILABLE or np is None:
             logger.error(f"FMS {operation} Error: NumPy not available for vector processing for '{fingerprint}'."); return None
        if not isinstance(vector, np.ndarray):
            logger.error(f"FMS {operation} Error: input 'vector' for '{fingerprint}' must be a NumPy array, got {type(vector)}.")
            return None
        vector_list: List[float]
        if vector.ndim == 1: vector_list = vector.tolist()
        elif vector.ndim == 2 and vector.shape[0] == 1: vector_list = vector[0].tolist()
        else:
            logger.error(f"FMS {operation} Error: input 'vector' for '{fingerprint}' has unsupported shape {vector.shape}. Expected 1D or (1, N).")
            return None
        if len(vector_list) != self.vss.embedding_dim:
            logger.error(f"FMS {operation} Error: Vector dimension mismatch for '{fingerprint}'. VSS expects dim {self.vss.embedding_dim}, got {len(vector_list)}.")
            return None
        return vector_list

    def add_vector(self, index_name: str, fingerprint: str, vector: np.ndarray, metadata: Optional[Dict[str, Any]] = None,
                   save_after: bool = True) -> bool:
        logger.debug(f"FMS: Add vector attempt for FP '{fingerprint}' in index '{index_name}'.")
        vector_list = self._preprocess_vector_input(vector, fingerprint, "Add")
        if vector_list is None: return False
            
        fms_operational_meta = metadata.copy() if metadata else {}
        fms_operational_meta.setdefault("_fms_operation_timestamp_utc", datetime.now(timezone.utc).isoformat())
        fms_operational_meta.setdefault("_fms_origin", "FAISSManagementService") # Mark metadata added by FMS

        success = self.vss.add_vector(
            index_name=index_name, fingerprint=fingerprint, vector_embedding=vector_list,
            metadata=fms_operational_meta, save_after=save_after
        )
        
        if success: logger.info(f"FMS: Successfully added vector '{fingerprint}' to '{index_name}' via VSS.")
        else: logger.warning(f"FMS: Failed to add vector '{fingerprint}' to '{index_name}' via VSS.")
        # If FMS needs to interact with GTM for this fingerprint's metadata:
        # if self.global_tracker and success:
        #     self.global_tracker.bulk_update_fields(fingerprint, {"fms_last_add_status": "success", "last_updated_by_fms": datetime.now(timezone.utc).isoformat()})
        return success

    def search_vectors(self, index_name: str, query_vector: np.ndarray, k: int = 5,
                       filter_metadata_fn: Optional[Callable[[Dict[str, Any]], bool]] = None
                       ) -> List[Tuple[str, float, Dict[str, Any]]]:
        logger.debug(f"FMS: Search request in index '{index_name}' for top {k} vectors.")
        query_list = self._preprocess_vector_input(query_vector, "query_vector", "Search")
        if query_list is None: return []
        
        results = self.vss.search_vectors(
            index_name=index_name, query_vector_embedding=query_list, top_k=k, filter_metadata_fn=filter_metadata_fn
        )
        logger.debug(f"FMS: Search in '{index_name}' via VSS returned {len(results)} results.")
        return results

    def reconstruct_vector(self, index_name: str, fingerprint: str) -> Optional[np.ndarray]:
        logger.debug(f"FMS: Reconstruct request for FP '{fingerprint}' in index '{index_name}'.")
        reconstructed_vec_np = self.vss.get_vector_by_fingerprint(index_name=index_name, fingerprint=fingerprint)
        if reconstructed_vec_np is None:
            logger.info(f"FMS: Vector for fingerprint '{fingerprint}' not found by VSS in index '{index_name}'.")
        else:
            logger.info(f"FMS: Vector for fingerprint '{fingerprint}' reconstructed successfully from VSS for index '{index_name}'.")
        return reconstructed_vec_np

    def get_vector_metadata(self, index_name: str, fingerprint: str) -> Optional[Dict[str,Any]]:
        logger.debug(f"FMS: Get metadata request for FP '{fingerprint}' in index '{index_name}'.")
        # This gets metadata stored by VSS (which includes what FMS passed to VSS during add)
        vss_metadata = self.vss.get_metadata(index_name=index_name, fingerprint=fingerprint)
        
        # Example: If FMS were to overlay or combine with GTM data:
        # if self.global_tracker and vss_metadata is not None:
        #     gtm_metadata = self.global_tracker.get_metadata(fingerprint, include_dynamic_fields=True)
        #     if gtm_metadata:
        #         combined_metadata = gtm_metadata.copy() # Start with GTM data
        #         combined_metadata.update(vss_metadata)  # Overlay/add VSS specific metadata
        #         # Be mindful of key collisions and decide on merging strategy
        #         return combined_metadata
        return vss_metadata

    def update_vector_metadata(self, index_name: str, fingerprint: str, updates: Dict[str, Any], save_after: bool = True) -> bool:
        logger.debug(f"FMS: Update metadata attempt for FP '{fingerprint}' in index '{index_name}'.")
        # FMS might pre-process updates or log to GTM that an update is occurring on VSS-managed metadata
        # updates["_fms_last_meta_update_utc"] = datetime.now(timezone.utc).isoformat()
        return self.vss.update_metadata(index_name=index_name, fingerprint=fingerprint, metadata_updates=updates, save_after=save_after)

    def remove_vector(self, index_name: str, fingerprint: str, save_after: bool = True) -> bool:
        logger.debug(f"FMS: Remove vector attempt for FP '{fingerprint}' in index '{index_name}'.")
        success = self.vss.remove_vector(index_name=index_name, fingerprint=fingerprint, save_after=save_after)
        # if self.global_tracker and success:
        #     self.global_tracker.update_record_status(fingerprint, "REMOVED_FROM_VSS_INDEX", {"index_name": index_name}) # Hypothetical GTM method
        return success

    def count_vectors_in_index(self, index_name: str) -> int:
        return self.vss.count_vectors(index_name=index_name)

    def list_all_fingerprints_in_index(self, index_name: str) -> List[str]:
        return self.vss.list_fingerprints(index_name=index_name)
        
    def save_specific_index(self, index_name: str) -> bool:
        logger.info(f"FMS: Explicit save request for index '{index_name}'. Delegating to VSS.")
        try:
            # Assuming VSS might have a public method or this delegates to VSS's _save_index_components
            # If VSS saves automatically on modification, this might be a no-op or for explicit flush.
            self.vss._save_index_components(index_name) # Or a public vss.save_index(name)
            return True
        except Exception as e:
            logger.error(f"FMS: Error explicitly saving index '{index_name}' via VSS: {e}", exc_info=True)
            return False

    def save_all_indexes(self):
        logger.info("FMS: Request to save all indexes. Delegating to VSS.")
        self.vss.save_all_managed_indexes()

    def get_index_statistics(self, index_name: str) -> Optional[Dict[str, Any]]:
        return self.vss.get_index_stats(index_name=index_name)

    def run_health_check(self) -> Dict[str, Any]:
        logger.info("FMS performing health check, will include VSS and GMT health.")
        vss_health = self.vss.health_check()
        fms_imports_ok = CITADEL_IMPORTS_OK and NUMPY_AVAILABLE and VSS_FAISS_AVAILABLE
        
        is_gmt_ok = True  # Assume OK if no tracker is present
        gmt_health_status = "NOT_CONFIGURED"
        if self.global_tracker:
            if hasattr(self.global_tracker, 'is_ready') and callable(self.global_tracker.is_ready):
                is_gmt_ok = self.global_tracker.is_ready()
                gmt_health_status = "READY" if is_gmt_ok else "NOT_READY"
            else:
                gmt_health_status = "STATUS_UNKNOWN" # No readiness check method
        
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
        logger.info("FAISSManagementService close() called. Underlying VSS lifecycle typically managed by Hub.")
        pass # VSS instance is managed externally (e.g., by Hub)

    def __del__(self):
        pass

# --- Main Test Block (Use the one you provided previously that includes time and detailed logging) ---
if __name__ == "__main__":
    # <<< PASTE THE __main__ BLOCK FROM YOUR PREVIOUS MESSAGE HERE >>>
    # The one starting with:
    # import time
    # logging.basicConfig(...)
    # And ending with the finally block that closes fms_instance_for_test_main, etc.
    # This is crucial: use the __main__ block you already have and confirmed.
    # For this response's completeness, I am pasting the LATEST __main__ you provided.

    import time
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s [%(levelname)s] [%(module)s.%(funcName)s:%(lineno)d] - %(message)s')

    TestFMS_DossierSysConfig_main: Any = dict
    TestFMS_VSS_main: Any = None
    TestFMS_GTM_main: Any = None
    TestFMS_cds_constants_main: Any = None
    TestFMS_sanitize_filename_main: Any = lambda name: name

    try:
        from config.schemas import DossierSystemConfigSchema as Actual_DossierSysConfig_main
        from SERVICE_SYSTEM.VECTOR_STORAGE_SERVICE import VectorStorageService as Actual_VSS_main # Renamed for clarity
        from SERVICE_SYSTEM.global_tracker_service import GlobalMetadataTracker as Actual_GTM_main
        from utils import constants as Actual_cds_constants_main
        from utils.common_utils import sanitize_filename_component as actual_sanitize_filename_component_main

        TestFMS_DossierSysConfig_main = Actual_DossierSysConfig_main
        TestFMS_VSS_main = Actual_VSS_main # Use the specifically imported VSS for the test
        TestFMS_GTM_main = Actual_GTM_main
        TestFMS_cds_constants_main = Actual_cds_constants_main
        TestFMS_sanitize_filename_main = actual_sanitize_filename_component_main
        logger.info("Successfully imported actual Citadel modules for FMS self-test.")
    except ImportError as e_main_imports_fms:
        logger.critical(f"FMS Self-Test: CRITICAL Import Error ({e_main_imports_fms}). Using fallbacks. Test WILL be severely limited or fail.", exc_info=True)
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
            logger.warning(f"Pydantic validation failed for FMS mock config: {e_pydantic_val_fms}. Falling back to dict.")
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
        logger.info(f"FMS Test Cleanup: Ensured VSS index '{test_idx_name_for_fms_cleanup_main}' files are clear in {vss_idx_dir_cleanup_main}.")

        vss_instance_for_fms_test_main = TestFMS_VSS_main(vector_indexes_base_dir=vss_base_dir_main, embedding_dim=_default_dim_for_test_main_val)
        logger.info(f"VectorStorageService instance created for FMS test. Base dir: {vss_base_dir_main}")

        if TestFMS_GTM_main is not None and hasattr(TestFMS_GTM_main, '__call__'):
            gtm_db_path_fms_main = Path(mock_fms_paths_data_main["council_specific_paths"]["gmt_database_path"])
            gtm_db_path_fms_main.parent.mkdir(parents=True, exist_ok=True)
            if gtm_db_path_fms_main.exists(): gtm_db_path_fms_main.unlink()
            gtm_instance_for_fms_test_main = TestFMS_GTM_main(db_path=str(gtm_db_path_fms_main))
            logger.info(f"GlobalMetadataTracker instance created for FMS test. DB: {gtm_db_path_fms_main}")
            # >>> ADD THIS LINE: <<<
            if gtm_instance_for_fms_test_main and hasattr(gtm_instance_for_fms_test_main, 'connect'):
                gtm_instance_for_fms_test_main.connect()
        fms_instance_for_test_main = FAISSManagementService(
            system_config=mock_fms_config_obj_main,
            vector_storage_service=vss_instance_for_fms_test_main,
            global_tracker_instance=gtm_instance_for_fms_test_main
        )
        logger.info("FAISSManagementService instance created for test.")

        logger.info("\n--- FMS Test: Health Check ---")
        health_status_main = fms_instance_for_test_main.run_health_check()
        assert health_status_main.get("fms_overall_status") == "OPERATIONAL", f"FMS Health Check failed: {health_status_main}"
        logger.info(f"FMS Health Check: {health_status_main.get('fms_overall_status')}, VSS Health: {health_status_main.get('vss_dependency_health', {}).get('overall_health_status')}")

        test_idx_name_main = "fms_test_idx_via_vss"
        test_dim_main = mock_fms_default_index_config_data_main['vector_dim']
        fp1_main = "fms_vss_fp001"
        vec1_np_main = np.random.rand(1, test_dim_main).astype("float32") # type: ignore
        meta1_main = {"description": "Test vector for FMS via VSS", "val": 1, "fms_test_marker": True}

        logger.info(f"\n--- FMS Test: Add vector '{fp1_main}' to '{test_idx_name_main}' ---")
        logger.debug(f"DEBUG (Add): fp='{fp1_main}', vec_norm={np.linalg.norm(vec1_np_main):.4f}, head={vec1_np_main[0, :5]}, tail={vec1_np_main[0, -5:]}") #type: ignore
        t_start_main = time.time()
        add_ok_main = fms_instance_for_test_main.add_vector(test_idx_name_main, fp1_main, vec1_np_main, meta1_main)
        logger.debug(f"Elapsed (Add): {(time.time() - t_start_main):.3f}s")
        assert add_ok_main, f"FMS failed to add vector {fp1_main}"
        logger.info(f"FMS: Vector {fp1_main} added successfully via VSS.")
        assert fms_instance_for_test_main.count_vectors_in_index(test_idx_name_main) == 1

        logger.info(f"\n--- FMS Test: Get Vector Metadata for '{fp1_main}' ---")
        retrieved_meta_main = fms_instance_for_test_main.get_vector_metadata(test_idx_name_main, fp1_main)
        assert retrieved_meta_main is not None, f"FMS get_vector_metadata failed for {fp1_main}"
        assert retrieved_meta_main.get("fms_test_marker") is True, "FMS metadata marker not found."
        # Check for FMS-added operational metadata directly in the flat metadata dict
        assert "_fms_operation_timestamp_utc" in retrieved_meta_main, \
            "FMS add timestamp missing in metadata (expected flat structure from GMT)."

        logger.info(
            f"FMS: Metadata for '{fp1_main}' retrieved successfully with FMS markers:\n{json.dumps(retrieved_meta_main, indent=2)}"
        )


        logger.info(f"\n--- FMS Test: Reconstruct vector '{fp1_main}' ---")
        t_start_main = time.time()
        recon_vec1_main = fms_instance_for_test_main.reconstruct_vector(test_idx_name_main, fp1_main)
        logger.debug(f"Elapsed (Reconstruct): {(time.time() - t_start_main):.3f}s")
        assert recon_vec1_main is not None, f"FMS reconstruct for {fp1_main} returned None"
        assert recon_vec1_main.shape == (1, test_dim_main), f"FMS reconstruct shape mismatch for {fp1_main}, got {recon_vec1_main.shape}" 
        assert np.allclose(recon_vec1_main, vec1_np_main, atol=1e-6), f"FMS reconstruct content mismatch for {fp1_main}" 
        logger.info(f"FMS: ✅ Vector {fp1_main} reconstructed successfully.")

        logger.info(f"\n--- FMS Test: Search for vector '{fp1_main}' ---")
        t_start_main = time.time()
        search_res_main = fms_instance_for_test_main.search_vectors(test_idx_name_main, vec1_np_main, k=1)
        logger.debug(f"Elapsed (Search): {(time.time() - t_start_main):.3f}s")
        assert len(search_res_main) == 1, f"FMS search for {fp1_main} failed to return 1 result, got {len(search_res_main)}"
        s_fp_main, s_score_main, s_meta_main = search_res_main[0]
        assert s_fp_main == fp1_main, f"FMS search returned wrong fingerprint: {s_fp_main}, expected {fp1_main}"
        assert s_score_main > 0.999, f"FMS search similarity for exact match is too low: {s_score_main}"
        assert s_meta_main.get("fms_test_marker") is True, "FMS metadata marker missing in search result."
        logger.info(f"FMS: ✅ Search for {fp1_main} successful, score: {s_score_main:.4f}")

        logger.info(f"\n--- FAISSManagementService Self-Test Suite ({main_config_title_fms}) Complete ---")

    except Exception as e_main_fms_test:
        logger.critical(f"CRITICAL ERROR in FAISSManagementService (using VSS) __main__ run: {e_main_fms_test}", exc_info=True)
    finally:
        if fms_instance_for_test_main and hasattr(fms_instance_for_test_main, 'close'): # Check if close exists
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
