
# -*- coding: utf-8 -*-
"""
embedding_service.py
Citadel Data System - Embedding Service for Agents and Reflexes
----------------------------------------------------------------------------
- Robust embedding generation using OpenAI with retry, batching, caching.
- Standalone operation with internal key management from F990_key_vault.py.
- Comprehensive JSONL logging for embedding calls.
- Integration with CDS paths for logs and FAISS.
Version: 2.3.2 (Updated for CDS 2025-08-08)
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
# --- Guardian Logger Import ---
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
# --- Third-Party Dependency Imports ---
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
# --- Rich Library for CLI Rich Rich Text ---
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
# --- Ensure MASTER_CITADEL root is in sys.path ---
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# --- Citadel Ecosystem Imports ---
try:
    from AGENTS.CDS_SYSTEM import CDS_CONFIG
    ROOT = CDS_CONFIG.ROOT
    CDS_DATA_PATHS = CDS_CONFIG.CDS_DATA_PATHS
    CDS_META = CDS_CONFIG.CDS_META
except ImportError:
    # Fallback stubs if CDS_CONFIG not available
    class CDS_CONFIG:
        ROOT = Path(__file__).resolve().parents[1]
        CDS_DATA_PATHS = {"logs": ROOT / "logs"}
        CDS_META = {}
    ROOT = CDS_CONFIG.ROOT
    CDS_DATA_PATHS = CDS_CONFIG.CDS_DATA_PATHS
    CDS_META = CDS_CONFIG.CDS_META
# --- Constants ---
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
# --- Standard Python Logger Setup ---
logger = logging.getLogger("CitadelEmbeddingService")
if not logger.hasHandlers():
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s [%(levelname)s] - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(os.getenv("EMBEDDING_SERVICE_LOG_LEVEL", "INFO").upper())
# --- Unified Warning Helper ---
def log_warning(message: str, component: str = "EmbeddingService"):
    """Log a warning to both standard logger and Guardian structured logs if available."""
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
            logger.debug(f"Guardian structured logging failed: {e}")
# Example initial log:
log_warning("EmbeddingService: Using fallback defaults for constants.")
# --- Runtime Config ---
ORG_ID = os.getenv("OPENAI_ORG_ID")
OPENAI_PROJECT_ID_FOR_HEADER = os.getenv("OPENAI_PROJECT_ID")
MAX_BATCH_SIZE_OPENAI = 2048
RETRY_ATTEMPTS_EMBEDDING = 5  # Increased for better robustness
RETRY_MAX_WAIT_SECONDS_EMBEDDING = 60
CONCURRENT_API_REQUESTS_EMBEDDING = 10  # Adjusted for higher concurrency if needed
DEFAULT_LRU_CACHE_SIZE = 100000  # Increased cache size
_NEXUSDATA_LOGS_FALLBACK_DIR = CDS_DATA_PATHS["logs"]
_DEFAULT_EMBEDDING_LOG_FILE_PATH_STR_FALLBACK = str(
    _NEXUSDATA_LOGS_FALLBACK_DIR / "embedding_service_calls.jsonl"
)
__version__ = "2.3.2"
__author__ = "Citadel Systems AI (Refined by NexusMind_Synthesizer_v3.0)"
__last_updated__ = datetime.now(timezone.utc).isoformat()
_execution_role = "core_embedding_generation_service"
MAX_CONCURRENT_REQUESTS = 5  # Adjusted
class _ApiKeyManagerForEmbedding:
    def __init__(
        self,
        key_list_override: Optional[List[str]] = None,
        project_id_override: Optional[str] = None,
        *,
        key_vault_path_override: Optional[str] = None,   # NEW
        skip_online_validation: bool = False             # NEW
    ):
        self.project_id_for_validation = project_id_override
        self._skip_online_validation = bool(skip_online_validation)  # NEW
        self.key_source_description = "key_list_override"

        # --- 0) Normalize ROOT for fallback imports (in case ROOT isn't defined above) ---
        try:
            _root_for_vault = ROOT  # type: ignore
        except NameError:
            _root_for_vault = Path(__file__).resolve().parents[1]

        # --- 1) Optional explicit key list override ---
        processed_keys: List[str] = []
        if isinstance(key_list_override, list):
            processed_keys = [
                k.strip() for k in key_list_override
                if isinstance(k, str) and k.startswith("sk-") and len(k) > 40
            ]
            if not processed_keys and key_list_override:
                logger.warning(f"[{type(self).__name__}] key_list_override provided but contained no validly formatted OpenAI keys.")

        self._raw_keys_to_load: List[str] = processed_keys

        # --- 2) OPENAI_API_KEY env as simple fallback ---
        if not self._raw_keys_to_load:
            env_key = os.getenv(OPENAI_API_KEY_ENV_VAR)
            if isinstance(env_key, str) and env_key.startswith("sk-") and len(env_key) > 40:
                self.key_source_description = "ENV_VAR_OPENAI_API_KEY"
                self._raw_keys_to_load = [env_key.strip()]

        # --- 3) Key vault file (explicit override -> env -> default path) ---
        if not self._raw_keys_to_load:
            # resolve vault path
            vault_path_str = (
                key_vault_path_override
                or os.getenv("CITADEL_KEY_VAULT_PATH")
                or str(_root_for_vault / "SMART_BANK_SYSTEM" / "FR_INFRASTRUCTURE" / "F990_key_vault.py")
            )
            try:
                vault_path = Path(vault_path_str)
                if not vault_path.exists():
                    raise FileNotFoundError(f"Vault file not found at: {vault_path}")
                spec = importlib.util.spec_from_file_location("F990_key_vault", str(vault_path))
                if spec is None or spec.loader is None:
                    raise ImportError("Failed to create module spec for key vault.")
                vault_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(vault_module)  # type: ignore
                keys_from_vault = getattr(vault_module, "API_KEYS", [])
                self._raw_keys_to_load = [
                    k.strip() for k in keys_from_vault
                    if isinstance(k, str) and k.startswith("sk-") and len(k) > 40
                ]
                self.key_source_description = f"vault:{vault_path}"
                if not self._raw_keys_to_load:
                    logger.warning(f"[{type(self).__name__}] F990_key_vault API_KEYS yielded no valid keys.")
            except Exception as e_vault:
                logger.warning(f"[{type(self).__name__}] Failed to load keys from key vault '{vault_path_str}': {e_vault}")
                self._raw_keys_to_load = []
                if self.key_source_description == "key_list_override":
                    self.key_source_description = "None (All sources failed)"

        # --- Internal state ---
        self._validated_key_pairs: List[Tuple[str, Optional[str]]] = []
        self._key_cycler: Optional[itertools.cycle] = None
        self._last_successful_validation_time: Dict[str, float] = {}
        self._validation_interval_seconds = 3600

        # --- Load & (optionally) validate ---
        if self._raw_keys_to_load:
            logger.info(
                f"[{type(self).__name__}] initializing with {len(self._raw_keys_to_load)} "
                f"candidate keys from: {self.key_source_description}. Validating..."
            )
            self._reload_and_validate_keys()
        else:
            logger.critical(f"[{type(self).__name__}] No API keys provided or found. Embedding calls will fail.")
        self._last_load_attempt_success = bool(self._validated_key_pairs)

    def _is_validation_due(self, key: str) -> bool:
        # NEW: allow skipping validation entirely
        if self._skip_online_validation:
            return False
        last_validated = self._last_successful_validation_time.get(key)
        if last_validated is None:
            return True
        return (time.time() - last_validated) > self._validation_interval_seconds

    def _validate_key_via_api(self, key: str) -> bool:
        # NEW: skip live API validation if requested
        if self._skip_online_validation:
            return True
        if not OPENAI_SDK_AVAILABLE:
            return True
        if not HTTPX_AVAILABLE:
            logger.warning(f"[{type(self).__name__}] httpx not available. Skipping API validation for key ...{key[-6:]}")
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
                f"[{type(self).__name__}] Key ...{key[-6:]} API validation failed "
                f"(HTTP {response.status_code}). Response: {response.text[:200]}"
            )
            return False
        except Exception as e_val:
            logger.warning(f"[{type(self).__name__}] API validation request error for key ...{key[-6:]}: {e_val}")
            return False

    def _reload_and_validate_keys(self):
        validated_pairs_temp: List[Tuple[str, Optional[str]]] = []
        if not self._raw_keys_to_load:
            self._validated_key_pairs = []
            self._key_cycler = None
            return

        logger.info(f"[{type(self).__name__}] Validating {len(self._raw_keys_to_load)} candidate keys...")
        for key_value in self._raw_keys_to_load:
            if self._validate_key_via_api(key_value):
                validated_pairs_temp.append((key_value, self.project_id_for_validation))
            else:
                logger.warning(f"[{type(self).__name__}] API rejected or could not validate key ...{key_value[-6:]}. Excluding.")

        self._validated_key_pairs = validated_pairs_temp
        self._key_cycler = itertools.cycle(self._validated_key_pairs) if self._validated_key_pairs else None
        log_msg = f"[{type(self).__name__}] Loaded {len(self._validated_key_pairs)} valid API keys."
        if self._validated_key_pairs:
            logger.info(log_msg)
        else:
            logger.critical(log_msg + " Embedding calls will fail.")
        self._last_load_attempt_success = bool(self._validated_key_pairs)

    def get_key(self, service_tag: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if not self._key_cycler:
            logger.warning(f"[{type(self).__name__}] No keys currently loaded. Attempting reload.")
            self._reload_and_validate_keys()
            if not self._key_cycler:
                logger.error(f"[{type(self).__name__}] Reload failed, still no keys available.")
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
            logger.error(f"[{type(self).__name__}] Error in get_key(): {e_get_key}", exc_info=True)
            return None

    def get_all_loaded_key_values(self) -> List[str]:
        return [pair[0] for pair in self._validated_key_pairs]

class EmbeddingService:
    __version__ = "2.3.3"  # bump

    def __init__(self,
                 key_manager_instance_override: Optional[Any] = None,
                 faiss_manager_instance_override: Optional[Any] = None,
                 embedding_model_override: Optional[str] = None,
                 lru_cache_size_override: Optional[int] = None,
                 log_embedding_calls_override: Optional[bool] = None,
                 embedding_log_path_override: Optional[Union[str, Any]] = None,
                 # keep your new params; they won't affect keys unless used
                 key_vault_path_override: Optional[str] = None,
                 skip_online_validation: bool = False):
        instance_uuid_short = uuid.uuid4().hex[:6]
        self.logger = logging.getLogger(f"CitadelEmbeddingService.instance.{instance_uuid_short}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.info(f"Initializing EmbeddingService v{self.__version__} (Instance: {instance_uuid_short})...")

        # --- define these EARLY so later checks/logs never AttributeError ---
        self.sync_client = None
        self.async_client = None
        self.embedding_log_file = None
        self.log_embedding_calls = True if log_embedding_calls_override is None else bool(log_embedding_calls_override)

        try:
            self._initialized_successfully = False
            self.init_error_detail: Optional[str] = None

            self.model = embedding_model_override or DEFAULT_EMBEDDING_MODEL
            self.embedding_dimension = SUPPORTED_EMBEDDING_MODELS_MAP.get(self.model, DEFAULT_EMBEDDING_DIMENSION)

            self.lru_cache_size = lru_cache_size_override or DEFAULT_LRU_CACHE_SIZE
            self._cache = LRUCache(maxsize=self.lru_cache_size) if CACHETOOLS_AVAILABLE else {}

            self.max_batch_size = MAX_BATCH_SIZE_OPENAI
            self._semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

            if not OPENAI_SDK_AVAILABLE:
                self.init_error_detail = "OpenAI SDK missing."
                self.logger.critical(self.init_error_detail)
                return

            # ---- KeyManager as you had it (dict-friendly), no behavior change unless provided ----
            if key_vault_path_override is None:
                key_vault_path_override = os.getenv(
                    "CITADEL_KEY_VAULT_PATH",
                    str(ROOT / "SMART_BANK_SYSTEM" / "FR_INFRASTRUCTURE" / "F990_key_vault.py")
                )
            if not skip_online_validation:
                skip_online_validation = os.getenv("CITADEL_SKIP_ONLINE_VALIDATION", "0").lower() in ("1", "true", "yes")

            km = key_manager_instance_override
            if isinstance(km, dict):
                km = _ApiKeyManagerForEmbedding(
                    key_list_override=km.get("keys"),
                    project_id_override=km.get("project_id"),
                    key_vault_path_override=km.get("key_vault_path") or key_vault_path_override,
                    skip_online_validation=km.get("skip_online_validation", skip_online_validation),
                )
            if km is None or not hasattr(km, "get_key"):
                km = _ApiKeyManagerForEmbedding(
                    key_vault_path_override=key_vault_path_override,
                    skip_online_validation=skip_online_validation
                )
            self.key_manager = km
            self.logger.info(f"KeyManager initialized: {type(self.key_manager).__name__}")

            self.faiss_manager = faiss_manager_instance_override
            if not self.faiss_manager:
                self.logger.info("No FAISS manager available.")

        except Exception as e:
            self.logger.critical(f"EmbeddingService init failed: {e}", exc_info=True)
            self.init_error_detail = str(e)
            return

        # ---- Initialize OpenAI clients (will no-op gracefully if no key) ----
        initial_key_data = self.key_manager.get_key("openai_embeddings_initial") if hasattr(self.key_manager, 'get_key') else None
        initial_key = initial_key_data.get("key") if isinstance(initial_key_data, dict) else None
        if not initial_key:
            self.init_error_detail = "No usable OpenAI API keys available from resolved KeyManager. EmbeddingService initialization failed."
            self.logger.critical(self.init_error_detail)
            return

        self.logger.info(f"🔐 EmbeddingService: Using initial OpenAI key ...{initial_key[-6:]}")
        client_params = {"api_key": initial_key, "timeout": httpx.Timeout(30.0, connect=10.0), "max_retries": 0}
        if ORG_ID: client_params["organization"] = ORG_ID
        if OPENAI_PROJECT_ID_FOR_HEADER: client_params["project"] = OPENAI_PROJECT_ID_FOR_HEADER
        try:
            self.sync_client = OpenAI(**client_params)
            self.async_client = AsyncOpenAI(**client_params)
        except Exception as e_client_init_final_es:
            self.init_error_detail = f"Failed to initialize OpenAI clients: {e_client_init_final_es}"
            self.logger.critical(f"❌ {self.init_error_detail}", exc_info=True)
            return

        # ---- LOG FILE SETUP (do this BEFORE the final info log that references the flag) ----
        _resolved_log_path_final: Optional[Path] = None
        if embedding_log_path_override:
            _resolved_log_path_final = Path(embedding_log_path_override).resolve()
            self.logger.info(f"Using log path from direct override: {_resolved_log_path_final}")
        if not _resolved_log_path_final:
            _resolved_log_path_final = CDS_DATA_PATHS["logs"] / "embedding_service_calls.jsonl"
            self.logger.info(f"Using CDS fallback log path: {_resolved_log_path_final}")
        try:
            self.embedding_log_file = _resolved_log_path_final
            self.embedding_log_file.parent.mkdir(parents=True, exist_ok=True)
            # self.log_embedding_calls already set; leave it as-is
        except Exception as log_path_err_final_es:
            self.log_embedding_calls = False
            self.logger.error(
                f"Failed to init embedding log path '{_resolved_log_path_final}'. Logging DISABLED. Error: {log_path_err_final_es}",
                exc_info=True
            )

        # ---- done ----
        self._initialized_successfully = True
        self.logger.info(
            f"🧠 EmbeddingService v{self.__version__} initialized. "
            f"Model: {self.model}, Dim: {self.embedding_dimension}, "
            f"Cache: {CACHETOOLS_AVAILABLE}, Logging: {'ENABLED' if self.log_embedding_calls else 'DISABLED'}."
        )


    def is_ready(self) -> bool:
        if not self._initialized_successfully: return False
        if not OPENAI_SDK_AVAILABLE: self.logger.warning("ES.is_ready: OpenAI SDK marked unavailable."); return False
        if not self.key_manager: self.logger.warning("ES.is_ready: KeyManager instance is None."); return False
        if hasattr(self.key_manager, 'get_all_loaded_key_values') and not self.key_manager.get_all_loaded_key_values():
            if hasattr(self.key_manager, '_last_load_attempt_success') and not self.key_manager._last_load_attempt_success:
                self.logger.warning("ES.is_ready: KeyManager reported last key load attempt failed.")
            else: self.logger.warning("ES.is_ready: KeyManager has no loaded/validated keys.")
            return False
        elif hasattr(self.key_manager, '_validated_key_pairs') and not self.key_manager._validated_key_pairs:
            self.logger.warning("ES.is_ready: Internal fallback KeyManager has no validated keys.")
            return False
        if not (self.sync_client and self.async_client): self.logger.error("ES.is_ready: OpenAI client(s) not initialized."); return False
        return True
    def _get_next_api_key(self) -> Optional[str]:
        if not self.key_manager or not hasattr(self.key_manager, 'get_key'):
            self.logger.error("❌ No KeyManager available to rotate keys for EmbeddingService.")
            return None
        key_data = self.key_manager.get_key(service_tag="openai_embeddings_rotation")
        new_key = key_data.get("key") if isinstance(key_data, dict) else (key_data[0] if isinstance(key_data, tuple) and key_data else None)
        if not new_key: self.logger.error("❌ KeyManager provided no key value for rotation."); return None
        key_source = type(self.key_manager).__name__
        self.logger.info(f"🔁 EmbeddingService: Rotated API key via {key_source} → ...{new_key[-6:]}")
        if self.sync_client: self.sync_client.api_key = new_key
        if self.async_client: self.async_client.api_key = new_key
        return new_key
    def _write_embedding_log(self, text_preview: str, api_key_used: Optional[str], source_method: str, success: bool, tokens_processed: Optional[int]=None, error_msg: Optional[str]=None, batch_size: Optional[int]=None):
        if not self.log_embedding_calls or not self.embedding_log_file: return
        try:
            log_entry: Dict[str, Any] = {
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "input_preview": text_preview[:200] + "..." if len(text_preview) > 200 else text_preview,
                "api_key_masked": f"sk-...{api_key_used[-4:]}" if api_key_used and len(api_key_used) >=4 else "N/A_or_too_short",
                "source_method": source_method, "model_used": self.model, "call_successful": success,
            }
            if tokens_processed is not None: log_entry["tokens_processed"] = tokens_processed
            if batch_size is not None: log_entry["batch_size_actual"] = batch_size
            if error_msg: log_entry["error_message"] = str(error_msg)[:500]
            with open(self.embedding_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e_log: self.logger.error(f"Failed to write to embedding log: {e_log}")
    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS_EMBEDDING),
        wait=wait_exponential(multiplier=1, min=1, max=RETRY_MAX_WAIT_SECONDS_EMBEDDING),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APIError, BadRequestError) if OPENAI_SDK_AVAILABLE else Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING) if TENACITY_AVAILABLE else None,
    )
    async def _generate_embeddings_batch_attempt_async(self, texts: List[str], current_api_key_for_log: Optional[str]) -> List[List[float]]:
        source_method_log = "async_batch_attempt"
        text_preview_log = texts[0][:50] if texts else "N/A_empty_batch"
        tokens_for_log = sum(len(t.split()) for t in texts)
        try:
            if not texts:
                return []
            processed_texts = [t if t.strip() else " " for t in texts]
            if not self.async_client:
                raise RuntimeError("AsyncOpenAI client not initialized.")
            response = await self.async_client.embeddings.create(model=self.model, input=processed_texts)
            data = getattr(response, "data", None)
            if data is None and isinstance(response, dict) and "data" in response:
                data = response["data"]
            usage_obj = getattr(response, "usage", None)
            token_count = getattr(usage_obj, "total_tokens", tokens_for_log) if usage_obj else tokens_for_log
            if isinstance(response, dict) and "usage" in response and isinstance(response["usage"], dict):
                token_count = response["usage"].get("total_tokens", tokens_for_log)
            self._write_embedding_log(
                text_preview_log, current_api_key_for_log, source_method_log,
                True, tokens_processed=token_count, batch_size=len(texts)
            )
            if data:
                return [getattr(item, "embedding", self._default_vector()) for item in data]
            else:
                raise RuntimeError("Embedding response missing 'data' field.")
        except RateLimitError as e_rl:
            self.logger.warning(f"Rate limit hit for API key ...{current_api_key_for_log[-4:] if current_api_key_for_log else 'N/A'}. Rotating. Error: {e_rl}")
            self._get_next_api_key()
            self._write_embedding_log(text_preview_log, current_api_key_for_log, source_method_log, False, tokens_processed=tokens_for_log, batch_size=len(texts), error_msg=f"RateLimitError: {e_rl}")
            raise
        except BadRequestError as e_br:
            self.logger.error(f"OpenAI BadRequestError (async batch): {e_br} (Texts: {len(texts)}, Preview: '{text_preview_log}')", exc_info=True)
            self._write_embedding_log(text_preview_log, current_api_key_for_log, source_method_log, False, tokens_processed=tokens_for_log, batch_size=len(texts), error_msg=f"BadRequestError: {e_br}")
            raise
        except APIError as e_api:
            self.logger.error(f"OpenAI APIError (async batch): {e_api} (Texts: {len(texts)}, Preview: '{text_preview_log}')", exc_info=True)
            self._write_embedding_log(text_preview_log, current_api_key_for_log, source_method_log, False, tokens_processed=tokens_for_log, batch_size=len(texts), error_msg=f"APIError: {e_api}")
            raise
        except Exception as e_unexp:
            self.logger.exception(f"Unexpected error during async batch embedding: {e_unexp} (Preview: '{text_preview_log}')")
            self._write_embedding_log(text_preview_log, current_api_key_for_log, source_method_log, False, tokens_processed=tokens_for_log, batch_size=len(texts), error_msg=f"Unexpected: {e_unexp}")
            raise
    async def _process_one_batch_async(self, batch_texts: List[str]) -> List[Optional[List[float]]]:
        async with self._semaphore:
            current_api_key_for_this_attempt = str(self.async_client.api_key) if self.async_client and self.async_client.api_key else "N/A"
            try:
                return await self._generate_embeddings_batch_attempt_async(batch_texts, current_api_key_for_this_attempt)
            except Exception as e_final_batch_in_process:
                self.logger.error(f"FINAL ERROR for batch starting with '{batch_texts[0][:40]}...' after retries: {e_final_batch_in_process}")
                if len(batch_texts) > 1:
                    self.logger.warning(f"Batch for '{batch_texts[0][:40]}...' failed. Retrying elements individually (async)...")
                    individual_results: List[Optional[List[float]]] = []
                    for single_text_in_failed_batch in batch_texts:
                        try:
                            result_meta_single = await self.generate_embedding_async_with_metadata(single_text_in_failed_batch, use_cache=False)
                            if "error" not in result_meta_single and result_meta_single.get("vector"):
                                individual_results.append(result_meta_single["vector"])
                            else:
                                self.logger.error(f"Sub-batch retry (single text: '{single_text_in_failed_batch[:40]}...') also failed. Error: {result_meta_single.get('error','Unknown')}")
                                individual_results.append(None)
                        except Exception as e_sub_batch_retry_final:
                            self.logger.error(f"Exception during sub-batch retry (single text: '{single_text_in_failed_batch[:40]}...'): {e_sub_batch_retry_final}")
                            individual_results.append(None)
                    return individual_results
                return [None] * len(batch_texts)
    async def generate_embeddings_batch_async(self, texts: List[str], use_cache: bool = True) -> List[List[float]]:
        if not self.is_ready(): return [self._default_vector()] * len(texts)
        if not texts: return []
        unique_texts_map: Dict[str, List[int]] = defaultdict(list)
        for i, text_content in enumerate(texts): unique_texts_map[text_content].append(i)
        unique_texts_to_process = list(unique_texts_map.keys())
        texts_to_fetch_from_api: List[str] = []
        cache_hits_results: Dict[str, List[float]] = {}
        if use_cache and CACHETOOLS_AVAILABLE:
            for text_val in unique_texts_to_process:
                if text_val in self._cache: cache_hits_results[text_val] = self._cache[text_val]
                else: texts_to_fetch_from_api.append(text_val)
            self.logger.info(f"Batch Async: {len(cache_hits_results)} unique texts from cache, {len(texts_to_fetch_from_api)} unique texts for API.")
        else:
            texts_to_fetch_from_api = unique_texts_to_process
            self.logger.info(f"Batch Async: Cache off/unavailable. {len(texts_to_fetch_from_api)} unique texts for API.")
        api_call_results_map: Dict[str, Optional[List[float]]] = {}
        if texts_to_fetch_from_api:
            api_tasks = []
            for i in range(0, len(texts_to_fetch_from_api), self.max_batch_size):
                batch_for_api = texts_to_fetch_from_api[i:i + self.max_batch_size]
                api_tasks.append((batch_for_api, asyncio.create_task(self._process_one_batch_async(batch_for_api))))
            for original_batch_texts, task_obj_api in api_tasks:
                try:
                    batch_embeddings_from_api: List[Optional[List[float]]] = await task_obj_api
                    for text_idx_in_batch, text_content_api in enumerate(original_batch_texts):
                        embedding_val = batch_embeddings_from_api[text_idx_in_batch]
                        api_call_results_map[text_content_api] = embedding_val
                        if embedding_val and use_cache and CACHETOOLS_AVAILABLE:
                            self._cache[text_content_api] = embedding_val
                except Exception as e_task_await_final:
                    self.logger.error(f"Task for batch '{original_batch_texts[0][:40]}...' failed at await: {e_task_await_final}")
                    for text_content_api in original_batch_texts: api_call_results_map[text_content_api] = None
        final_batch_results: List[List[float]] = [self._default_vector()] * len(texts)
        for unique_text, original_indices in unique_texts_map.items():
            final_embedding_for_text: Optional[List[float]] = None
            if unique_text in cache_hits_results: final_embedding_for_text = cache_hits_results[unique_text]
            elif unique_text in api_call_results_map: final_embedding_for_text = api_call_results_map[unique_text]
            for original_idx in original_indices:
                final_batch_results[original_idx] = final_embedding_for_text if final_embedding_for_text else self._default_vector()
        return final_batch_results
    async def generate_embedding_async_with_metadata(self, text: str, use_cache: bool = True) -> Dict[str, Any]:
        if not self.is_ready(): return {"vector": self._default_vector(), "error": "Service not ready", "model_used": self.model, "cache_hit": False}
        if not isinstance(text, str) or not text.strip():
            return {"vector": self._default_vector(), "error": "Invalid input", "model_used": self.model, "cache_hit": False}
        if use_cache and CACHETOOLS_AVAILABLE and text in self._cache:
            cached_embedding = self._cache[text]
            self.logger.debug(f"Cache HIT (async_meta): '{text[:40]}...'")
            self._write_embedding_log(text[:50], "N/A (cached)", "async_meta_cache_hit", True, tokens_processed=len(text.split()))
            return {"vector": cached_embedding, "cache_hit": True, "source_key_masked": "N/A (cached)", "model_used": self.model}
        self.logger.debug(f"Cache MISS (async_meta): '{text[:40]}...'. API via batch.")
        api_key_at_call_start = str(self.async_client.api_key if self.async_client else "N/A")
        batch_result_list = await self.generate_embeddings_batch_async([text], use_cache=False)
        embedding = batch_result_list[0]
        result_payload: Dict[str, Any] = {
            "vector": embedding, "cache_hit": False, "model_used": self.model,
            "source_key_masked": f"sk-...{api_key_at_call_start[-4:]}" if api_key_at_call_start and len(api_key_at_call_start)>=4 else "N/A"
        }
        if embedding == self._default_vector():
            result_payload["error"] = "Embedding generation failed (async_meta)"
            self.logger.warning(f"Embedding generation failed (async_meta) for '{text[:40]}...'. Key at call start: ...{api_key_at_call_start[-4:]}")
        elif use_cache and CACHETOOLS_AVAILABLE:
            self._cache[text] = embedding
        return result_payload
    async def generate_embedding_async(self, text: str, use_cache: bool = True) -> Optional[List[float]]:
        if not self.is_ready(): return self._default_vector()
        result_meta = await self.generate_embedding_async_with_metadata(text, use_cache)
        return result_meta.get("vector") if "error" not in result_meta else self._default_vector()
    @retry(
        stop=stop_after_attempt(RETRY_ATTEMPTS_EMBEDDING),
        wait=wait_exponential(multiplier=1, min=1, max=RETRY_MAX_WAIT_SECONDS_EMBEDDING),
        retry=retry_if_exception_type((RateLimitError, APIConnectionError, APIError, BadRequestError) if OPENAI_SDK_AVAILABLE else Exception),
        before_sleep=before_sleep_log(logger, logging.WARNING) if TENACITY_AVAILABLE else None,
    )
    def generate_embedding_sync(self, text: str, use_cache: bool = True, return_metadata: bool = False) -> Union[List[float], Dict[str, Any]]:
        if not self.is_ready():
            err_payload_not_ready = {"error": "Service not ready", "model_used": self.model, "cache_hit": False, "vector": self._default_vector()}
            return self._default_vector() if not return_metadata else err_payload_not_ready
        if not OPENAI_SDK_AVAILABLE:
            err_payload_no_sdk = {"error": "OpenAI SDK not available", "model_used": self.model, "cache_hit": False, "vector": self._default_vector()}
            return self._default_vector() if not return_metadata else err_payload_no_sdk
        if not isinstance(text, str) or not text.strip():
            err_payload_invalid_input = {"error": "Invalid input", "model_used": self.model, "cache_hit": False, "vector": self._default_vector()}
            return self._default_vector() if not return_metadata else err_payload_invalid_input
        if use_cache and CACHETOOLS_AVAILABLE and text in self._cache:
            cached_embedding = self._cache[text]
            self.logger.debug(f"Cache HIT (sync): '{text[:40]}...'")
            self._write_embedding_log(text[:50], "N/A (cached)", "sync_single_cache_hit", True, tokens_processed=len(text.split()))
            return cached_embedding if not return_metadata else {"vector": cached_embedding, "cache_hit": True, "source_key_masked": "N/A (cached)", "model_used": self.model}
        self.logger.debug(f"Cache MISS (sync): '{text[:40]}...'. Calling API.")
        api_key_for_this_attempt = str(self.sync_client.api_key) if self.sync_client and self.sync_client.api_key else "N/A"
        tokens_for_log_est = len(text.split())
        try:
            processed_text = text if text.strip() else " "
            if not self.sync_client: raise RuntimeError("Sync OpenAI client not initialized.")
            response = self.sync_client.embeddings.create(model=self.model, input=processed_text)
            embedding = response.data[0].embedding
            actual_tokens = getattr(response.usage, 'total_tokens', tokens_for_log_est) if response.usage else tokens_for_log_est
            self._write_embedding_log(text[:50], api_key_for_this_attempt, "sync_single_api_call", True, tokens_processed=actual_tokens)
            if use_cache and CACHETOOLS_AVAILABLE: self._cache[text] = embedding
            return embedding if not return_metadata else {"vector": embedding, "cache_hit": False, "source_key_masked": f"sk-...{api_key_for_this_attempt[-4:]}" if api_key_for_this_attempt and len(api_key_for_this_attempt)>=4 else "N/A", "model_used": self.model}
        except RateLimitError as e_rl_sync:
            err_msg_rl = f"RateLimitError: {e_rl_sync}"
            self.logger.warning(f"Rate limit hit (sync) for API key ...{api_key_for_this_attempt[-4:]}. Rotating. Error: {e_rl_sync}")
            self._get_next_api_key()
            self._write_embedding_log(text[:50], api_key_for_this_attempt, "sync_single_api_call_rate_limit_retry", False, tokens_processed=tokens_for_log_est, error_msg=err_msg_rl)
            raise
        except (APIError, BadRequestError) as e_api_bad_sync:
            err_msg_api_bad = f"{type(e_api_bad_sync).__name__}: {e_api_bad_sync}"
            self.logger.error(f"OpenAI {type(e_api_bad_sync).__name__} (sync) for '{text[:50]}...': {e_api_bad_sync}", exc_info=self.logger.isEnabledFor(logging.DEBUG))
            self._write_embedding_log(text[:50], api_key_for_this_attempt, "sync_single_api_call_api_error", False, tokens_processed=tokens_for_log_est, error_msg=err_msg_api_bad)
            raise
        except Exception as e_unexp_sync:
            err_msg_unexp = f"Unexpected error in generate_embedding_sync: {e_unexp_sync}"
            self.logger.exception(f"Unexpected error (sync) for '{text[:50]}...': {e_unexp_sync}")
            self._write_embedding_log(text[:50], api_key_for_this_attempt, "sync_single_api_call_unexpected_error", False, tokens_processed=tokens_for_log_est, error_msg=err_msg_unexp)
            error_payload = {"error": err_msg_unexp, "model_used": self.model, "cache_hit": False, "source_key_masked": f"sk-...{api_key_for_this_attempt[-4:]}" if api_key_for_this_attempt and len(api_key_for_this_attempt)>=4 else "N/A", "vector": self._default_vector()}
            return self._default_vector() if not return_metadata else error_payload
        self.logger.warning(f"Embedding generation failed for '{text[:40]}...' after all attempts (sync). Returning default vector.")
        final_err_payload = {"error": "Embedding generation failed after all attempts (sync)", "model_used": self.model, "cache_hit": False, "source_key_masked": f"sk-...{api_key_for_this_attempt[-4:]}" if api_key_for_this_attempt and len(api_key_for_this_attempt)>=4 else "N/A", "vector": self._default_vector()}
        return self._default_vector() if not return_metadata else final_err_payload
    def _default_vector(self) -> List[float]:
        return [0.0] * self.embedding_dimension
    @staticmethod
    def generate_fingerprint(text: str, method: str = "sha256") -> str:
        text_bytes = str(text).encode("utf-8", "ignore")
        if method == "sha256": return hashlib.sha256(text_bytes).hexdigest()
        elif method == "md5": return hashlib.md5(text_bytes).hexdigest()
        elif method == "sha1": return hashlib.sha1(text_bytes).hexdigest()
        else:
            logger.warning(f"Unsupported fingerprint method: '{method}'. Defaulting to sha256.")
            return hashlib.sha256(text_bytes).hexdigest()
    def store_vector_to_faiss(self, thought_document: Dict[str, Any], *, route_name: str = "learning_default") -> bool:
        if not self.faiss_manager:
            self.logger.warning(f"FAISSManagementService not available. Cannot store vector for '{thought_document.get('fingerprint','N/A')}' to FAISS route '{route_name}'.")
            return False
        if not NUMPY_AVAILABLE:
            self.logger.error("NumPy not available. Cannot prepare vector for FAISS storage.")
            return False
        fingerprint = str(thought_document.get("fingerprint") or thought_document.get("thought_id", uuid.uuid4().hex)).strip()
        embedding_data = thought_document.get("embedding_A0_raw_text") or thought_document.get("embedding") or thought_document.get("vector")
        if not fingerprint:
            self.logger.error("FAISS Store: Missing fingerprint in thought_document."); return False
        if not isinstance(embedding_data, list) or not all(isinstance(x, (int, float)) for x in embedding_data):
            self.logger.error(f"FAISS Store: Invalid or non-numeric embedding vector for {fingerprint}. Type: {type(embedding_data)}"); return False
        if len(embedding_data) != self.embedding_dimension:
            self.logger.error(f"FAISS Store: Dimension mismatch for {fingerprint}. Vector Dim: {len(embedding_data)}, Expected Service Dim: {self.embedding_dimension}"); return False
        try:
            vector_np_to_store = np.array(embedding_data, dtype=np.float32).reshape(1, -1)
            faiss_storage_metadata = {
                "original_fingerprint": fingerprint,
                "text_preview": str(thought_document.get("raw_text", thought_document.get("refined_output", "")))[:250],
                "source_domain": str(thought_document.get("domain", thought_document.get("domain_primary", "unknown_domain"))),
                "creation_timestamp_original_utc": str(thought_document.get("timestamp_utc_creation", thought_document.get("created_at", self._current_utc_iso_for_meta()))),
                "stored_to_faiss_by_es_utc": self._current_utc_iso_for_meta(),
                "es_model_used_for_embedding": self.model
            }
            add_success = self.faiss_manager.add_vector(
                index_name=route_name,
                fingerprint=fingerprint,
                vector=vector_np_to_store,
                metadata=faiss_storage_metadata,
                save_after=True
            )
            if add_success:
                self.logger.info(f"EmbeddingService successfully requested FAISS store via FMS for '{fingerprint}' to route '{route_name}'.")
            else:
                self.logger.warning(f"EmbeddingService: FAISS store request for '{fingerprint}' on route '{route_name}' reported failure by FAISSManagementService.")
            return add_success
        except AttributeError as e_fms_attr:
            self.logger.error(f"FAISS Store Error: FAISSManagementService (type: {type(self.faiss_manager)}) is not properly configured or method 'add_vector' missing: {e_fms_attr}", exc_info=True)
        except Exception as e_store_faiss:
            self.logger.error(f"FAISS Store Error (via EmbeddingService) for {fingerprint} (route: {route_name}): {e_store_faiss}", exc_info=True)
        return False
    def _current_utc_iso_for_meta(self) -> str:
        return datetime.now(timezone.utc).isoformat()
    async def confirm_openai_embedding_ready(self) -> bool:
        if not self.is_ready():
            self.logger.error("confirm_openai_embedding_ready: Service is not ready. Aborting health check.")
            return False
        service_version_for_test = getattr(self, '__version__', 'N/A')
        test_text = f"Citadel EmbeddingService (v{service_version_for_test}) Health Check @ {self._current_utc_iso_for_meta()}."
        try:
            result_meta = await self.generate_embedding_async_with_metadata(test_text, use_cache=False)
            vector = result_meta.get("vector")
            if vector and vector != self._default_vector() and "error" not in result_meta:
                self.logger.info(f"✅ OpenAI embedding service is confirmed READY via API ping. Test key (masked): {result_meta.get('source_key_masked')}, Model: {result_meta.get('model_used')}")
                return True
            else:
                err_msg = result_meta.get('error', 'No vector returned or default vector returned.')
                self.logger.error(f"❌ OpenAI embedding health check FAILED. Result: {result_meta}. Error: {err_msg}")
                return False
        except Exception as e_health_final:
            self.logger.exception(f"❌ OpenAI embedding health check CRASHED: {e_health_final}")
            return False
_default_embedding_service_instance: Optional[EmbeddingService] = None
_default_embedding_service_lock = threading.Lock()
def get_default_embedding_service(
    force_new: bool = False,
    key_manager_instance_override: Optional[Any] = None,
    faiss_manager_instance_override: Optional[Any] = None,
    embedding_model_override: Optional[str] = None,
    lru_cache_size_override: Optional[int] = None,
    log_embedding_calls_override: Optional[bool] = None,
    embedding_log_path_override: Optional[Union[str, Path]] = None
) -> Optional[EmbeddingService]:
    global _default_embedding_service_instance
    if not force_new and _default_embedding_service_instance and _default_embedding_service_instance.is_ready():
        return _default_embedding_service_instance
    with _default_embedding_service_lock:
        if not force_new and _default_embedding_service_instance and _default_embedding_service_instance.is_ready():
            return _default_embedding_service_instance
        logger.info(f"Factory: Attempting to initialize default EmbeddingService instance {'(forcing new)' if force_new else ''}...")
        constructor_args: Dict[str, Any] = {}
        if key_manager_instance_override: constructor_args['key_manager_instance_override'] = key_manager_instance_override
        if faiss_manager_instance_override: constructor_args['faiss_manager_instance_override'] = faiss_manager_instance_override
        if embedding_model_override: constructor_args['embedding_model_override'] = embedding_model_override
        if lru_cache_size_override is not None: constructor_args['lru_cache_size_override'] = lru_cache_size_override
        if log_embedding_calls_override is not None: constructor_args['log_embedding_calls_override'] = log_embedding_calls_override
        if embedding_log_path_override: constructor_args['embedding_log_path_override'] = embedding_log_path_override
        newInstance: Optional[EmbeddingService] = None
        try:
            newInstance = EmbeddingService(**constructor_args)
            if newInstance.is_ready():
                logger.info(f"✅ Factory: Default EmbeddingService v{newInstance.__version__} initialized and ready.")
                _default_embedding_service_instance = newInstance
            else:
                init_err = getattr(newInstance, 'init_error_detail', "Service instance reported not ready post-init.")
                logger.critical(f"❌ Factory: Default EmbeddingService instance created but NOT ready. Detail: {init_err}")
                _default_embedding_service_instance = None
        except Exception as e_factory_final:
            logger.critical(f"❌ Factory: CRITICAL - Failed to instantiate EmbeddingService: {e_factory_final}", exc_info=True)
            _default_embedding_service_instance = None
        return _default_embedding_service_instance
async def generate_embedding_async(text: str, use_cache: bool = True, return_metadata: bool = False, **svc_kwargs) -> Union[Optional[List[float]], Dict[str, Any]]:
    service = get_default_embedding_service(**svc_kwargs)
    if not service or not service.is_ready():
        default_vec = [0.0] * (SUPPORTED_EMBEDDING_MODELS_MAP.get(svc_kwargs.get("embedding_model_override", DEFAULT_EMBEDDING_MODEL), DEFAULT_EMBEDDING_DIMENSION))
        return default_vec if not return_metadata else {"error":"EmbeddingService not ready/available", "vector": default_vec, "model_used":svc_kwargs.get("embedding_model_override", DEFAULT_EMBEDDING_MODEL), "cache_hit":False}
    if return_metadata: return await service.generate_embedding_async_with_metadata(text, use_cache)
    return await service.generate_embedding_async(text, use_cache)
async def generate_embeddings_batch_async(texts: List[str], use_cache: bool = True, **svc_kwargs) -> List[List[float]]:
    service = get_default_embedding_service(**svc_kwargs)
    if not service or not service.is_ready():
        default_dim = SUPPORTED_EMBEDDING_MODELS_MAP.get(svc_kwargs.get("embedding_model_override", DEFAULT_EMBEDDING_MODEL), DEFAULT_EMBEDDING_DIMENSION)
        return [[0.0] * default_dim for _ in texts]
    return await service.generate_embeddings_batch_async(texts, use_cache)
def generate_embedding_sync(text: str, use_cache: bool = True, return_metadata: bool = False, **svc_kwargs) -> Union[List[float], Dict[str, Any]]:
    service = get_default_embedding_service(**svc_kwargs)
    if not service or not service.is_ready():
        default_vec = [0.0] * (SUPPORTED_EMBEDDING_MODELS_MAP.get(svc_kwargs.get("embedding_model_override", DEFAULT_EMBEDDING_MODEL), DEFAULT_EMBEDDING_DIMENSION))
        return default_vec if not return_metadata else {"error":"EmbeddingService not ready/available", "vector": default_vec, "model_used":svc_kwargs.get("embedding_model_override", DEFAULT_EMBEDDING_MODEL), "cache_hit":False}
    return service.generate_embedding_sync(text, use_cache, return_metadata)
def embed_text(text: str, **svc_kwargs) -> List[float]:
    service = get_default_embedding_service(**svc_kwargs)
    if not service or not service.is_ready(): return [0.0] * (SUPPORTED_EMBEDDING_MODELS_MAP.get(svc_kwargs.get("embedding_model_override", DEFAULT_EMBEDDING_MODEL), DEFAULT_EMBEDDING_DIMENSION))
    result = service.generate_embedding_sync(text, use_cache=True, return_metadata=False)
    return result if isinstance(result, list) else service._default_vector()
def generate_fingerprint(text: str, method: str = "sha256") -> str:
    return EmbeddingService.generate_fingerprint(text, method)
def store_vector_to_faiss(thought_document: dict, *, route_name: str = "learning_default", **svc_kwargs) -> bool:
    service = get_default_embedding_service(**svc_kwargs)
    if not service or not service.is_ready(): return False
    return service.store_vector_to_faiss(thought_document, route_name=route_name)
async def confirm_openai_embedding_ready(**svc_kwargs) -> bool:
    service = get_default_embedding_service(**svc_kwargs)
    if not service: return False
    return await service.confirm_openai_embedding_ready()
__all__ = [
    "EmbeddingService", "get_default_embedding_service",
    "generate_embedding_async", "generate_embeddings_batch_async",
    "generate_embedding_sync", "embed_text",
    "generate_fingerprint", "store_vector_to_faiss",
    "confirm_openai_embedding_ready",
    "DEFAULT_EMBEDDING_MODEL", "DEFAULT_EMBEDDING_DIMENSION",
    "_ApiKeyManagerForEmbedding", "OPENAI_SDK_AVAILABLE"
]
async def run_embedding_service_tests():
    """
    Redesigned Self-Test for EmbeddingService
    - Minimal legacy variables
    - CAPS & SRS integrated logging
    - Auto fallback to mock mode if keys or API invalid
    """
    # ---------- Setup Logging ----------
    test_logger = logging.getLogger("EmbeddingServiceSelfTest")
    if not test_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] - %(message)s')
        handler.setFormatter(formatter)
        test_logger.addHandler(handler)
    test_logger.setLevel(logging.DEBUG)
    logging.getLogger("CitadelEmbeddingService").setLevel(logging.DEBUG)
    file_ver_for_log = __version__
    test_logger.info("\n" + "⚡️"*3 + f" EMBEDDING SERVICE SELF-TEST (v{file_ver_for_log}) " + "⚡️"*3)
    # ---------- Prepare directories ----------
    test_output_base_dir = ROOT / "LEDGER" / "SYSTEM_SERVICE_LEDGER" / "embedding_service_module_tests"
    temp_log_dir = test_output_base_dir / "logs"
    temp_log_dir.mkdir(parents=True, exist_ok=True)
    test_log_path = temp_log_dir / f"embedding_test_log_v{file_ver_for_log.replace('.','_')}.jsonl"
    # ---------- 1) Load Keys ----------
    raw_keys_to_load: List[str] = []
    kms_source_description_for_test = "KeyManager Not Initialized"
    real_kms_fully_functional = False
    try:
        vault_path = ROOT / "SMART_BANK_SYSTEM" / "FR_INFRASTRUCTURE" / "F990_key_vault.py"
        spec = importlib.util.spec_from_file_location("F990_key_vault", vault_path)
        vault_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vault_module)
        raw_keys_to_load = [
            k for k in getattr(vault_module, "API_KEYS", [])
            if isinstance(k, str) and k.startswith("sk-") and len(k) > 40
        ]
        kms_source_description_for_test = "F990_key_vault API_KEYS"
        if raw_keys_to_load:
            test_logger.info(f"[F990][CAPS:KEY_LOAD] Loaded {len(raw_keys_to_load)} key(s) from KeyVault.")
            real_kms_fully_functional = True
        else:
            test_logger.warning("[F990][CAPS:KEY_WARN] No valid keys found. Falling back to internal KeyManager.")
    except Exception as e_vault:
        test_logger.error(f"[F990][CAPS:KEY_ERROR] Failed to load KeyVault: {e_vault}", exc_info=True)
    # ---------- 2) Prepare KeyManager ----------
    keys_for_test = raw_keys_to_load if real_kms_fully_functional else [
        os.getenv("TEST_OPENAI_API_KEY_EMBEDDING_ES",
        "sk-svcacct-FALLBACK-ONLY-FOR-MOCK-TESTS")
    ]
    key_manager = _ApiKeyManagerForEmbedding(key_list_override=keys_for_test)
    # ---------- 3) Setup Mock FAISS ----------
    class MockFAISSManagementService:
        def __init__(self, temp_dir: Path):
            self.temp_dir = temp_dir; self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.stored_vectors: Dict[str, Dict[str, Any]] = {}
            test_logger.info(f"[F956][CAPS:FAISS_INIT] MockFAISS initialized at {self.temp_dir}")
        def add_vector(self, index_name: str, fingerprint: str, vector: Any, metadata: Dict, save_after: bool) -> bool:
            if not NUMPY_AVAILABLE or not isinstance(vector, np.ndarray):
                test_logger.error("[F956][CAPS:FAISS_ERR] NumPy array expected for vector.")
                return False
            storage_key = f"{index_name}::{fingerprint}"
            self.stored_vectors[storage_key] = {"shape": vector.shape, "metadata": metadata}
            if save_after:
                (self.temp_dir / f"{index_name}.mock_faiss").write_text(f"Stored: {fingerprint}\n", encoding="utf-8")
            test_logger.info(f"[F956][CAPS:FAISS_STORE] Vector stored for {fingerprint} in {index_name}")
            return True
        def is_ready(self) -> bool: return True
    mock_faiss_manager = MockFAISSManagementService(temp_dir=test_output_base_dir / "mock_faiss_storage")
    # ---------- 4) Initialize EmbeddingService ----------
    service_under_test = get_default_embedding_service(
        force_new=True,
        key_manager_instance_override=key_manager,
        faiss_manager_instance_override=mock_faiss_manager,
        log_embedding_calls_override=True,
        embedding_log_path_override=test_log_path
    )
    if not service_under_test or not service_under_test.is_ready():
        test_logger.critical("[F985][CAPS:SERVICE_FAIL] EmbeddingService failed to initialize.")
        return
    test_logger.info("[F985][CAPS:SERVICE_READY] EmbeddingService initialized successfully.")
    # ---------- 5) Health Check ----------
    is_ready = await service_under_test.confirm_openai_embedding_ready()
    if is_ready:
        test_logger.info("[F985][CAPS:HEALTH_PASS] EmbeddingService API ping successful.")
    else:
        test_logger.warning("[F985][CAPS:HEALTH_WARN] Service not ready for live API. Switching to mock mode.")
    # ---------- 6) Sample Embedding ----------
    sample_text = "AI-driven embedding service test for Citadel Master."
    result_meta = await service_under_test.generate_embedding_async_with_metadata(sample_text)
    test_logger.info(f"[F987][CAPS:EMBED_CALL] '{sample_text[:30]}...' Vector dim={len(result_meta.get('vector', []))}, Cache={result_meta.get('cache_hit')}")
    # ---------- 7) FAISS Store Test ----------
    sample_doc = {
        "fingerprint": "selftest_fp_001",
        "raw_text": sample_text,
        "embedding": result_meta["vector"],
        "domain": "self_test",
        "source_agent_id": "EmbeddingServiceSelfTest"
    }
    faiss_ok = service_under_test.store_vector_to_faiss(sample_doc, route_name="self_test_index")
    test_logger.info(f"[F956][CAPS:FAISS_STORE] Store success: {faiss_ok}")
    # ---------- 8) Summary ----------
    test_logger.info("\n" + "="*60)
    test_logger.info(" EMBEDDING SERVICE SELF-TEST COMPLETE")
    test_logger.info(f" - Module Version: {file_ver_for_log}")
    test_logger.info(f" - Keys Loaded: {len(keys_for_test)} ({'Real' if real_kms_fully_functional else 'Fallback'})")
    test_logger.info(f" - Service Ready: {service_under_test.is_ready()}")
    test_logger.info(f" - Health Check: {is_ready}")
    test_logger.info(f" - Log File: {test_log_path}")
    test_logger.info("="*60)
if __name__ == "__main__":
    required_for_test = {
        "OpenAI SDK": OPENAI_SDK_AVAILABLE, "Tenacity": TENACITY_AVAILABLE,
        "Cachetools": CACHETOOLS_AVAILABLE, "NumPy": NUMPY_AVAILABLE,
        "HTTPX": HTTPX_AVAILABLE
    }
    missing_for_test = [name for name, available in required_for_test.items() if not available]
    if missing_for_test:
        main_run_logger = logging.getLogger("EmbeddingServiceSelfTestRunner")
        if not main_run_logger.handlers:
            _mr_h_es_run = logging.StreamHandler(sys.stdout)
            _mr_f_es_run = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] - %(message)s')
            _mr_h_es_run.setFormatter(_mr_f_es_run)
            main_run_logger.addHandler(_mr_h_es_run)
        main_run_logger.setLevel(logging.ERROR)
        main_run_logger.error(
            f"Cannot run full EmbeddingService self-tests due to missing critical dependencies: {', '.join(missing_for_test)}. "
            "Please install them (e.g., pip install openai tenacity cachetools numpy httpx)."
        )
    else:
        asyncio.run(run_embedding_service_tests())
try:
    _module_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
except Exception as e_hash_es_final_run:
    _module_hash = f"hash_calculation_failed_embedding_service_v2.3.2_{e_hash_es_final_run}"
