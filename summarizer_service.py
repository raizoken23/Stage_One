# D:/CITADEL/citadel_dossier_system/services/summarizer_service.py

"""
Citadel Dossier System - Advanced Summarizer Service
File Version: 1.2.2 - Corrected Logger Scope for Backoff | Last Updated: 2025-05-28

This module provides a robust and extensible interface to Language Models (LLMs)
for generating concise summaries or digests. It features configurable retry logic,
caching, detailed metrics logging, and a foundation for multi-provider support.
It relies on dependency injection for its specific configuration, KeyManager, and
the parent system configuration for broader context (e.g., service endpoints).
"""

# ─── Environment Setup ────────────────────────────────────────────────────────
import sys
from pathlib import Path
import logging

_SUMMARIZER_SERVICE_FILE = Path(__file__).resolve()
_CDS_ROOT_SUMMARIZER = _SUMMARIZER_SERVICE_FILE.parent.parent # services -> citadel_dossier_system
_PROJECT_ROOT_SUMMARIZER = _CDS_ROOT_SUMMARIZER.parent     # citadel_dossier_system -> CITADEL_ROOT

if str(_PROJECT_ROOT_SUMMARIZER) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT_SUMMARIZER))

# ─── Standard Library ─────────────────────────────────────────────────────────
import os
import time
import hashlib
import asyncio 
from typing import Optional, Dict, Any, List, Tuple, Callable, Union, Type 
from abc import ABC, abstractmethod
import json
from datetime import datetime, timezone
import re # For backoff logger fix in OpenAIProvider
from openai import OpenAI
from openai.types.chat import ChatCompletion
from openai import AuthenticationError, BadRequestError, RateLimitError, APIConnectionError, APIError
import logging
# ─── Third-Party ──────────────────────────────────────────────────────────────
import backoff 
try:
    from openai import OpenAI, APIError, RateLimitError, AuthenticationError, APIConnectionError, BadRequestError
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    OpenAI = APIError = RateLimitError = AuthenticationError = APIConnectionError = BadRequestError = None # type: ignore

# ─── Citadel Core ─────────────────────────────────────────────────────────────
CDS_IMPORTS_OK = False
logger_summarizer_init = logging.getLogger(f"CDS.{Path(__file__).stem}_Init") 

# Pydantic BaseModel for fallback definitions
class BaseModelStub: pass # Simple stub if Pydantic isn't available during initial parse
try: from pydantic import BaseModel as PydanticBaseModelImport
except ImportError: PydanticBaseModelImport = BaseModelStub

try:
    from citadel_dossier_system.config.schemas import (
        DossierSystemConfigSchema, VDPacketDataSchema, ServiceEndpointSchema, 
        SummarizerServiceConfigSchema 
    )
    from citadel_dossier_system.utils import constants as cds_constants
    from citadel_dossier_system.utils.common_utils import create_deterministic_fingerprint
    from citadel_dossier_system.utils.citadel_keys import KeyManager 
    CDS_IMPORTS_OK = True
except ImportError as e_cds_summarizer:
    logger_summarizer_init.critical(
        f"CRITICAL CDS Import Error: {e_cds_summarizer}. Service may be non-functional.",
        exc_info=True
    )

    # === Fallback Type Stubs (Using PydanticBaseModelImport if Pydantic is unavailable) ===

    class SummarizerServiceConfigSchema(PydanticBaseModelImport):
        default_provider: str = "openai"
        cache_max_size: int = 1000
        enable_caching: bool = True
        default_target_tokens: int = 150
        default_temperature: float = 0.3
        default_max_input_chars: int = 7500
        prompt_templates: dict = {}  # type: ignore


    class KeyManager(PydanticBaseModelImport):
        def get_key(self, service_tag: str) -> Optional[Dict[str, str]]:
            return None  # type: ignore


    class DossierSystemConfigSchema(PydanticBaseModelImport):
        service_endpoints: Optional[Dict[str, Any]] = None
        summarizer_config: Optional[SummarizerServiceConfigSchema] = None  # type: ignore


    class VDPacketDataSchema(PydanticBaseModelImport):
        domain_primary: Optional[str] = None  # type: ignore


    class ServiceEndpointSchema(PydanticBaseModelImport):
        pass  # type: ignore


    class cds_constants:
        PLACEHOLDER_TEXT_EMPTY = "[SUMMARY SKIPPED: EMPTY INPUT]"
        DEFAULT_OPENAI_MODEL_FOR_DIGEST = "gpt-4o-mini"
        ENV_VAR_OPENAI_API_KEY = "OPENAI_API_KEY"  # type: ignore


    def create_deterministic_fingerprint(text: str, length: int) -> str:
        return hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:length]  # type: ignore

# Module-level logger
logger = logging.getLogger(f"CDS.{Path(__file__).stem}")
if not logger.handlers: 
    _sh = logging.StreamHandler(sys.stdout); _sf = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s'); _sh.setFormatter(_sf)
    logger.addHandler(_sh); logger.setLevel(logging.INFO)

# Logger name for backoff decorator
_BACKOFF_LOGGER_NAME = f"CDS.{Path(__file__).stem}.BackoffHandler"
_backoff_event_logger = logging.getLogger(_BACKOFF_LOGGER_NAME)
if not _backoff_event_logger.hasHandlers() and not logger.hasHandlers(): # Only add if no parent handler will catch it
    _bh = logging.StreamHandler(sys.stdout)
    _bf = logging.Formatter('%(asctime)s - %(name)s [%(levelname)s] - %(message)s') # Simpler for backoff
    _bh.setFormatter(_bf)
    _backoff_event_logger.addHandler(_bh)
    _backoff_event_logger.setLevel(logging.WARNING) # Backoff typically logs warnings/errors


# --- Base LLM Provider Interface ---
class BaseLLMProvider(ABC):
    """Abstract base class for Large Language Model (LLM) providers."""
    def __init__(self, provider_config: Dict[str, Any], service_name: str, key_manager_instance: Optional[KeyManager]):
        """
        Initializes the BaseLLMProvider.

        Args:
            provider_config (Dict[str, Any]): Configuration for the provider.
            service_name (str): The name of the service.
            key_manager_instance (Optional[KeyManager]): An instance of the KeyManager.
        """
        self.provider_config = provider_config
        self.service_name = service_name
        self.key_manager = key_manager_instance
        self.is_configured = False
        self.default_model_name: Optional[str] = None
        logger.info(f"Initializing {self.service_name} provider for SummarizerService.")

    @abstractmethod
    def initialize_client(self) -> bool:
        """Initializes the API client for the provider."""
        pass

    @abstractmethod
    def generate(
        self, prompt: str, model_name: str, max_tokens: int, temperature: float,
        stop_sequences: Optional[List[str]] = None,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Generates a response from the LLM.

        Args:
            prompt (str): The prompt to send to the LLM.
            model_name (str): The name of the model to use.
            max_tokens (int): The maximum number of tokens to generate.
            temperature (float): The temperature for the generation.
            stop_sequences (Optional[List[str]], optional): A list of stop sequences.
                Defaults to None.

        Returns:
            A tuple containing the generated text and a dictionary of metrics.
        """
        pass

    def is_ready(self) -> bool:
        """
        Checks if the provider is ready to use.

        Returns:
            bool: True if the provider is ready, False otherwise.
        """
        return self.is_configured

# --- OpenAI Provider Implementation ---
class OpenAIProvider(BaseLLMProvider):
    """An LLM provider for OpenAI models."""
    def __init__(self, provider_config_dict: Dict[str, Any], key_manager_instance: Optional[KeyManager]): 
        """
        Initializes the OpenAIProvider.

        Args:
            provider_config_dict (Dict[str, Any]): Configuration for the provider.
            key_manager_instance (Optional[KeyManager]): An instance of the KeyManager.
        """
        super().__init__(provider_config_dict, "OpenAI", key_manager_instance)

        self.client: Optional[OpenAI] = None
        self.service_tag_for_key: str = provider_config_dict.get("key_service_tag", "openai_summarizer")
        self.base_url: Optional[str] = provider_config_dict.get("base_url")
        
        self.default_model_name: str = provider_config_dict.get("default_model", getattr(cds_constants, 'DEFAULT_OPENAI_MODEL_FOR_DIGEST', 'gpt-4o-mini'))
        self.timeout_seconds: int = provider_config_dict.get("timeout_seconds", 30)

        if not OPENAI_AVAILABLE or OpenAI is None:
            logger.error("OpenAI library not installed or OpenAI class not available. OpenAIProvider cannot be initialized.")
            return
        self.initialize_client()

    def initialize_client(self) -> bool:
        """
        Initializes the OpenAI API client.

        Returns:
            bool: True if the client was initialized successfully, False otherwise.
        """
        api_key_value: Optional[str] = None
        if self.key_manager:
            key_data = self.key_manager.get_key(self.service_tag_for_key)
            if key_data and isinstance(key_data, dict) and key_data.get("key"):
                api_key_value = key_data["key"]
                logger.info(f"OpenAIProvider: Retrieved API key via KeyManager for service tag '{self.service_tag_for_key}'.")
            else:
                logger.warning(f"OpenAIProvider: KeyManager did not provide valid key data for tag '{self.service_tag_for_key}'. Checking ENV.")
        
        if not api_key_value:
            api_key_env_var_name = self.provider_config.get("api_key_env_var", getattr(cds_constants, 'ENV_VAR_OPENAI_API_KEY', 'OPENAI_API_KEY'))
            api_key_value = os.getenv(api_key_env_var_name)
            if api_key_value:
                logger.info(f"OpenAIProvider: Retrieved API key via ENV var '{api_key_env_var_name}'.")
            else:
                 logger.error(f"OpenAI API key not found via KeyManager (tag: '{self.service_tag_for_key}') or ENV var ('{api_key_env_var_name}'). OpenAIProvider disabled.")
                 self.is_configured = False
                 return False
        
        effective_base_url = self.base_url
        if not effective_base_url and self.provider_config.get("base_url_env_var"):
            base_url_env_name = self.provider_config["base_url_env_var"]
            effective_base_url = os.getenv(base_url_env_name)
            if effective_base_url: logger.info(f"OpenAIProvider: Using base_url from ENV var '{base_url_env_name}'.")

        try:
            self.client = OpenAI(api_key=api_key_value, base_url=effective_base_url, timeout=float(self.timeout_seconds))
            self.is_configured = True
            logger.info(f"OpenAIProvider initialized. Default model: '{self.default_model_name}'. Base URL: '{effective_base_url or 'Default OpenAI'}'.")
            return True
        except AuthenticationError as e: 
            logger.critical(f"OpenAI AuthenticationError: {e}. Key source: {'KeyManager' if self.key_manager else 'ENV'}. OpenAIProvider DISABLED.", exc_info=False)
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
        self.is_configured = False
        return False

    @backoff.on_exception(
        backoff.expo,
        (RateLimitError, APIConnectionError, APIError), 
        max_tries=3, 
        jitter=backoff.full_jitter, 
        logger=_BACKOFF_LOGGER_NAME,
        on_backoff=lambda details: logging.getLogger(details.get('logger') or _BACKOFF_LOGGER_NAME).warning(
            f"Backing off {details['wait']:.1f}s after {details['tries']} tries calling {details['target'].__name__} due to {details['exception']}"
        ),
        on_giveup=lambda details: logging.getLogger(details.get('logger') or _BACKOFF_LOGGER_NAME).error(
            f"Gave up calling {details['target'].__name__} after {details['tries']} tries due to {details['exception']}"
        )
    )

    def generate(
        self, prompt: str, model_name: str, max_tokens: int, temperature: float,
        stop_sequences: Optional[List[str]] = None
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Generates a response from the OpenAI API.

        Args:
            prompt (str): The prompt to send to the LLM.
            model_name (str): The name of the model to use.
            max_tokens (int): The maximum number of tokens to generate.
            temperature (float): The temperature for the generation.
            stop_sequences (Optional[List[str]], optional): A list of stop sequences.
                Defaults to None.

        Returns:
            A tuple containing the generated text and a dictionary of metrics.
        """
        if not self.is_ready() or not self.client:
            logger.error("OpenAIProvider.generate: Provider not ready or client not initialized.")
            return None, {"error": "OpenAIProvider not ready or client not initialized."}

        metrics: Dict[str, Any] = { 
            "provider": self.service_name,
            "model_name": model_name,
            "prompt_chars": len(prompt),
            "target_max_tokens": max_tokens,
            "temperature": temperature,
            "request_timestamp": datetime.now(timezone.utc).isoformat()
        }

        start_time = time.perf_counter()

        try:
            response: ChatCompletion = self.client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                stop=stop_sequences
            )

            duration_ms = (time.perf_counter() - start_time) * 1000
            metrics["duration_ms"] = round(duration_ms)

            if response.choices:
                choice = response.choices[0]
                content = choice.message.content.strip() if choice.message and choice.message.content else None
                metrics["finish_reason"] = choice.finish_reason
                if hasattr(response, "usage"):
                    metrics["prompt_tokens"] = response.usage.prompt_tokens
                    metrics["completion_tokens"] = response.usage.completion_tokens
                    metrics["total_tokens"] = response.usage.total_tokens
                logger.debug(f"OpenAI response: {content[:100] if content else 'None'}... Metrics: {metrics}")
                return content, metrics
            else:
                logger.warning(f"OpenAI call to '{model_name}' returned no choices.")
                metrics["error"] = "No choices returned"
                return None, metrics

        except BadRequestError as e:
            logger.error(f"OpenAI BadRequestError with model '{model_name}': {e}. Prompt: '{prompt[:200]}...'")
            error_body = getattr(e, 'body', {})
            metrics["error"] = f"BadRequestError: {error_body.get('message', str(e))}"
            metrics["error_type"] = error_body.get('type')
            metrics["error_code"] = error_body.get('code')

        except AuthenticationError as e:
            logger.critical(f"OpenAI AuthenticationError during generate: {e}. OpenAIProvider likely misconfigured.", exc_info=False)
            self.is_configured = False
            metrics["error"] = "AuthenticationError"

        except (RateLimitError, APIConnectionError, APIError) as e_retryable:
            logger.warning(f"OpenAI Retriable Error ({type(e_retryable).__name__}) with model '{model_name}': {e_retryable}. Backoff will handle.")
            metrics["error"] = f"RetriableError: {type(e_retryable).__name__}: {str(e_retryable)}"
            raise

        except Exception as e:
            logger.error(f"Unexpected error during OpenAI generate with model '{model_name}': {e}", exc_info=True)
            metrics["error"] = f"UnexpectedError: {str(e)}"

        metrics.setdefault("duration_ms", round((time.perf_counter() - start_time) * 1000))
        return None, metrics


class SummarizerService:
    """A service for generating summaries of text using an LLM."""
    _cache: Dict[str, Tuple[Optional[str], Dict[str, Any]]] = {} 
    _cache_max_size: int = 1000 

    def __init__(self, 
                 config: Optional[SummarizerServiceConfigSchema] = None, 
                 key_manager: Optional[KeyManager] = None,
                 system_config_parent: Optional[DossierSystemConfigSchema] = None):
        """
        Initializes the SummarizerService.

        Args:
            config (Optional[SummarizerServiceConfigSchema], optional): Configuration
                for the service. Defaults to None.
            key_manager (Optional[KeyManager], optional): An instance of the
                KeyManager. Defaults to None.
            system_config_parent (Optional[DossierSystemConfigSchema], optional):
                The parent system configuration. Defaults to None.
        """
        if config:
            self.service_config = config
        elif CDS_IMPORTS_OK and SummarizerServiceConfigSchema:
            self.service_config = SummarizerServiceConfigSchema()
        else: 
            self.service_config = SummarizerServiceConfigSchema(**{})

        self.key_manager = key_manager
        self.system_config_parent = system_config_parent 
        
        self.active_provider: Optional[BaseLLMProvider] = None
        
        self.default_provider_name: str = getattr(self.service_config, 'default_provider', 'openai')
        self._cache_max_size = int(getattr(self.service_config, 'cache_max_size', self._cache_max_size))
        self.enable_caching_flag = bool(getattr(self.service_config, 'enable_caching', True))

        logger.info(f"Initializing SummarizerService (Provider: {self.default_provider_name}). Cache Enabled: {self.enable_caching_flag}, Cache Max Size: {self._cache_max_size}")

        if self.default_provider_name == "openai":
            openai_ep_config_dict: Dict[str, Any] = {} 
            if self.system_config_parent and \
               hasattr(self.system_config_parent, 'service_endpoints') and \
               self.system_config_parent.service_endpoints and \
               isinstance(self.system_config_parent.service_endpoints, dict) and \
               "openai" in self.system_config_parent.service_endpoints:
                
                openai_ep_config_obj = self.system_config_parent.service_endpoints.get("openai")
                if openai_ep_config_obj and isinstance(openai_ep_config_obj, PydanticBaseModelImport):
                     openai_ep_config_dict = openai_ep_config_obj.model_dump(exclude_none=True)
                     logger.debug(f"Summarizer: OpenAI endpoint config from system_config_parent (Pydantic): {openai_ep_config_dict}")
                elif isinstance(openai_ep_config_obj, dict): 
                     openai_ep_config_dict = dict(openai_ep_config_obj)
                     logger.debug(f"Summarizer: OpenAI endpoint config from system_config_parent (dict): {openai_ep_config_dict}")
                elif openai_ep_config_obj is None:
                     logger.warning("Summarizer: 'openai' key found in service_endpoints but value is None.")
            elif OPENAI_AVAILABLE :
                 logger.warning("Summarizer: OpenAI provider selected, but no 'service_endpoints.openai' config in system_config_parent. Using defaults.")
            
            if OPENAI_AVAILABLE:
                self.active_provider = OpenAIProvider(openai_ep_config_dict, self.key_manager)
            else:
                logger.error("Summarizer: OpenAI provider selected, but OpenAI library NOT available.")
        
        if not self.active_provider or not self.active_provider.is_ready():
            logger.error(
                f"SummarizerService: Provider '{self.default_provider_name}' FAILED to initialize or is not ready. Service will be non-operational."
            )
        else:
            provider_name = getattr(self.active_provider, 'service_name', 'UnknownProvider')
            model_name = getattr(self.active_provider, 'default_model_name', 'Not Set')
            logger.info(f"SummarizerService initialized successfully. Active provider: {provider_name}, Default Model: {model_name}")

    def is_available(self) -> bool:
        """
        Checks if the service is available and ready.

        Returns:
            bool: True if the service is available, False otherwise.
        """
        return self.active_provider is not None and self.active_provider.is_ready()

    def _generate_cache_key(self, text: str, model: str, prompt_template_id: str, context_hash: str, target_tokens: int, temp: float) -> str:
        """Generates a cache key for a given request."""
        key_material = f"{text}|{model}|{prompt_template_id}|{context_hash}|{target_tokens}|{temp}"
        if CDS_IMPORTS_OK and callable(create_deterministic_fingerprint):
            return create_deterministic_fingerprint(key_material, length=32)
        return hashlib.sha256(key_material.encode('utf-8', 'ignore')).hexdigest()[:32]


    def _get_from_cache(self, cache_key: str) -> Optional[Tuple[Optional[str], Dict[str, Any]]]:
        """Gets a result from the cache."""
        if cache_key in self._cache: logger.debug(f"Cache hit for key: {cache_key}"); return self._cache[cache_key]
        logger.debug(f"Cache miss for key: {cache_key}"); return None

    def _put_in_cache(self, cache_key: str, summary: Optional[str], metrics: Dict[str, Any]):
        """Puts a result in the cache."""
        if len(self._cache) >= self._cache_max_size:
            try: self._cache.pop(next(iter(self._cache))); logger.debug("Cache full, evicted oldest item.")
            except StopIteration: pass
            except Exception as e_cache_pop: logger.warning(f"Summarizer: Error during cache eviction: {e_cache_pop}")
        self._cache[cache_key] = (summary, metrics); logger.debug(f"Cached result for key: {cache_key}")

    def _build_default_prompt(self, text_segment: str, domain: str, tier: str) -> str:
        """Builds a default prompt for the summarization task."""
        return (
            "You are an expert summarization assistant tasked with creating a concise reflection digest "
            "for an entry in a knowledge dossier. Focus on extracting the core essence, key insights, "
            "or main conclusions from the provided text segment. Format your output as clear Markdown, "
            "using bullet points for distinct ideas or a short, dense paragraph for narrative summaries.\n\n"
            f"Dossier Context: Domain='{domain}', Entry Tier='{tier}'\n\n"
            "Instructions:\n"
            "- Be direct and highly concise.\n"
            "- Avoid introductory phrases like 'This text is about...'.\n"
            "- Capture the most impactful information.\n"
            "- If the text is conversational or a log, summarize the key outcomes or decisions.\n\n"
            f"TEXT SEGMENT TO SUMMARIZE:\n----------------------------\n{text_segment}\n----------------------------\n"
            "CONCISE REFLECTION DIGEST (Markdown format):"
        )

    def generate_digest(
        self,
        text_to_summarize: str,
        context_metadata: Optional[Union[Dict[str, Any], VDPacketDataSchema]] = None,
        max_input_chars_override: Optional[int] = None,
        target_summary_tokens_override: Optional[int] = None,
        model_name_override: Optional[str] = None,
        temperature_override: Optional[float] = None,
        custom_prompt_template: Optional[str] = None,
        prompt_template_id: str = "default_v1",
        use_cache: bool = True,
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Generates a summary digest for the given text.

        Args:
            text_to_summarize (str): The text to summarize.
            context_metadata (Optional[Union[Dict[str, Any], VDPacketDataSchema]], optional):
                Metadata to provide context for the summarization. Defaults to None.
            max_input_chars_override (Optional[int], optional): The maximum number of
                input characters to use. Defaults to None.
            target_summary_tokens_override (Optional[int], optional): The target number
                of tokens for the summary. Defaults to None.
            model_name_override (Optional[str], optional): The name of the model to
                use. Defaults to None.
            temperature_override (Optional[float], optional): The temperature for the
                generation. Defaults to None.
            custom_prompt_template (Optional[str], optional): A custom prompt template
                to use. Defaults to None.
            prompt_template_id (str, optional): The ID of a predefined prompt
                template to use. Defaults to "default_v1".
            use_cache (bool, optional): Whether to use the cache. Defaults to True.

        Returns:
            A tuple containing the generated summary and a dictionary of metrics.
        """
        provider_name_for_metrics = self.active_provider.service_name if self.active_provider else "N/A"
        if not self.is_available() or not self.active_provider:
            msg = "SummarizerService is not available or provider not ready."
            logger.error(msg)
            return None, {"error": msg, "status": "service_unavailable", "provider_name": provider_name_for_metrics}

        if not text_to_summarize or not text_to_summarize.strip():
            placeholder_text = getattr(cds_constants, 'PLACEHOLDER_TEXT_EMPTY', "[SUMMARY SKIPPED: EMPTY INPUT]") if CDS_IMPORTS_OK else "[SUMMARY SKIPPED: EMPTY INPUT]"
            metrics_empty = {"error": "Empty input text.", "input_chars": 0, "provider_name": provider_name_for_metrics}
            logger.debug(metrics_empty["error"])
            return placeholder_text, metrics_empty

        active_model_name = model_name_override or getattr(self.service_config, 'default_model', self.active_provider.default_model_name or 'gpt-4o-mini')
        target_tokens = target_summary_tokens_override or getattr(self.service_config, 'default_target_tokens', 150)
        temperature = temperature_override if temperature_override is not None else getattr(self.service_config, 'default_temperature', 0.3)
        max_input_chars = max_input_chars_override or getattr(self.service_config, 'default_max_input_chars', 7500)
        
        domain_str = "general"; tier_str = "N/A"; context_fingerprint_material = {}
        if context_metadata:
            if CDS_IMPORTS_OK and VDPacketDataSchema and isinstance(context_metadata, VDPacketDataSchema):
                domain_str = context_metadata.domain_primary or "general"; context_fingerprint_material["domain"] = domain_str
                tier_str = getattr(context_metadata, 'vault_tier', "N/A")
                context_fingerprint_material["tier"] = tier_str
            elif isinstance(context_metadata, dict):
                domain_str = str(context_metadata.get("domain_primary", context_metadata.get("domain", "general")))
                tier_str = str(context_metadata.get("vault_tier", "N/A"))
                context_fingerprint_material["domain"] = domain_str; context_fingerprint_material["tier"] = tier_str
        context_hash = self._generate_cache_key(json.dumps(context_fingerprint_material, sort_keys=True), "", "", "", 0, 0.0)[:16] if context_fingerprint_material else "no_context"

        cache_key = ""; effective_use_cache = use_cache and self.enable_caching_flag
        if effective_use_cache:
            cache_key = self._generate_cache_key(text_to_summarize, active_model_name, prompt_template_id, context_hash, target_tokens, temperature)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                cached_summary, cached_metrics = cached_result
                cached_metrics["retrieved_from_cache"] = True; cached_metrics["cache_key"] = cache_key
                return cached_summary, cached_metrics
        
        truncated_text = text_to_summarize; original_len = len(text_to_summarize)
        if original_len > max_input_chars:
            truncated_text = text_to_summarize[:max_input_chars] + "\n... (truncated for digest generation)"
            logger.debug(f"Input text truncated from {original_len} to {len(truncated_text)} chars for digest (max: {max_input_chars}).")

        final_prompt: str; current_prompt_template_id_for_log = prompt_template_id
        prompt_fill_data_base = {"text_to_summarize": truncated_text, "domain_context": domain_str, "tier_context": tier_str}
        context_meta_dict_for_prompt = {}
        if context_metadata:
            if CDS_IMPORTS_OK and VDPacketDataSchema and isinstance(context_metadata, VDPacketDataSchema):
                context_meta_dict_for_prompt = context_metadata.model_dump(exclude_none=True)
            elif isinstance(context_metadata, dict):
                context_meta_dict_for_prompt = context_metadata
        prompt_fill_data = {**prompt_fill_data_base, **context_meta_dict_for_prompt}


        if custom_prompt_template:
            try:
                final_prompt = custom_prompt_template.format(**prompt_fill_data)
                current_prompt_template_id_for_log = f"custom_{self._generate_cache_key(custom_prompt_template, '', '', '', 0, 0.0)[:8]}"
            except KeyError as e:
                logger.error(f"Custom prompt template missing key: {e}. Using default. Original ID: '{prompt_template_id}'"); current_prompt_template_id_for_log = "default_v1_fallback_custom_error"
                final_prompt = self._build_default_prompt(truncated_text, domain_str, tier_str)
        else:
            prompt_templates_from_config: Dict[str,str] = getattr(self.service_config, 'prompt_templates', {}) 
            if isinstance(prompt_templates_from_config, dict) and prompt_template_id in prompt_templates_from_config:
                 template_str = prompt_templates_from_config[prompt_template_id]
                 final_prompt = template_str.format(**prompt_fill_data)
            else:
                logger.warning(f"Unknown prompt_template_id: '{prompt_template_id}'. Using default_v1."); final_prompt = self._build_default_prompt(truncated_text, domain_str, tier_str)
                current_prompt_template_id_for_log = "default_v1_fallback_unknown_id"
        
        log_prompt_info = {"template_id_used": current_prompt_template_id_for_log, "model_name": active_model_name, "input_text_original_chars": original_len, "input_text_truncated_chars": len(truncated_text), "prompt_final_chars": len(final_prompt), "target_summary_tokens": target_tokens, "temperature": temperature, "context_domain": domain_str, "context_tier": tier_str, "context_hash": context_hash}
        logger.debug(f"SummarizerService: Final prompt details: {log_prompt_info}")

        summary_text, llm_metrics = self.active_provider.generate(prompt=final_prompt, model_name=active_model_name, max_tokens=target_tokens, temperature=temperature)
        full_metrics = {**log_prompt_info, **llm_metrics}; full_metrics["cache_key"] = cache_key if effective_use_cache else "cache_disabled"; full_metrics["retrieved_from_cache"] = False

        if summary_text is None or not summary_text.strip():
            logger.warning(f"Provider '{provider_name_for_metrics}' model '{active_model_name}' returned empty/None summary. LLM Metrics: {llm_metrics}")
            full_metrics["summary_status"] = "empty_or_failed"
            placeholder_failed = getattr(cds_constants, 'PLACEHOLDER_TEXT_EMPTY', "[SUMMARY GENERATION FAILED OR EMPTY]") if CDS_IMPORTS_OK else "[SUMMARY FAILED]"
            return placeholder_failed if summary_text is None else summary_text, full_metrics

        full_metrics["summary_status"] = "success"; full_metrics["summary_output_chars"] = len(summary_text)
        if effective_use_cache: self._put_in_cache(cache_key, summary_text, full_metrics)
        logger.info(f"Digest generated. Provider: {full_metrics.get('provider')}, Model: {active_model_name}, Status: Success. Tokens: {full_metrics.get('total_tokens', 'N/A')}")
        return summary_text, full_metrics
# --- Self-Test Block (Updated for Real System Usage) ---

# --- Self-Test Block (Updated for Real System Usage) ---
if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    # This bootstrap is critical for standalone execution
    try:
        # Go up two levels from `services` to the project root `CITADEL`
        _project_root = Path(__file__).resolve().parents[2]
        if str(_project_root) not in sys.path:
            sys.path.insert(0, str(_project_root))
        from citadel_dossier_system.config.config_loader import ConfigLoader
        from citadel_dossier_system.citadel_hub import CitadelHub
        from citadel_dossier_system.utils.citadel_keys import KeyManager
        from citadel_dossier_system.config.schemas import DossierSystemConfigSchema, SummarizerServiceConfigSchema, VDPacketDataSchema
    except ImportError as e:
        print(f"CRITICAL: Could not bootstrap Citadel modules for live test. Error: {e}")
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO, 
        format='%(asctime)s - %(name)s [%(levelname)s] - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s'
    )
    test_logger = logging.getLogger("SummarizerService_LiveTest")

    test_logger.info("🚀 SummarizerService Live Integration Self-Test Initializing...")
    
    summarizer_instance: Optional[SummarizerService] = None
    hub_instance: Optional[CitadelHub] = None
    
    try:
        test_logger.info("Initializing CitadelHub to load dependencies...")
        # Initialize the hub and force-load all services to ensure dependencies are met.
        hub_instance = CitadelHub(init_services_on_load=True)
        if not hub_instance.is_ready(check_all_services=True):
            test_logger.error("Hub is not ready after explicit service loading. See diagnostics below.")
            hub_instance.get_diagnostic_grid()
            raise RuntimeError("Hub failed to become ready for the test.")

        # The SummarizerService is initialized by the Hub itself. We fetch it.
        test_logger.info("Fetching SummarizerService from Hub...")
        summarizer_instance = hub_instance.get_service("SummarizerService")
        
        if not summarizer_instance or not summarizer_instance.is_available():
            raise RuntimeError("SummarizerService is not available from the Hub. Check API keys and service logs.")
        
        test_logger.info("✅ SummarizerService fetched and is available.")
        
        # --- Run Test Case ---
        long_text_for_test = (
            "The James Webb Space Telescope (JWST) is a space telescope designed primarily to conduct infrared astronomy. "
            "As the largest optical telescope in space, its significantly improved infrared resolution and sensitivity allow it to view objects "
            "too old, distant, or faint for the Hubble Space Telescope."
        )
        
        summary_text, summary_metrics = summarizer_instance.generate_digest(
            text_to_summarize=long_text_for_test,
            use_cache=False 
        )
        
        test_logger.info("\n📝 === Summary Result ===\n" + str(summary_text))
        test_logger.info("\n📊 === Full Metrics ===\n" + json.dumps(summary_metrics, indent=2, default=str))

        assert summary_text is not None
        assert "error" not in summary_metrics
        assert summary_metrics.get("summary_status") == "success"
        test_logger.info("\n✅✅✅ SummarizerService Live Test PASSED ✅✅✅")

    except Exception as e:
        test_logger.critical(f"❌❌❌ SummarizerService Live Test FAILED: {e}", exc_info=True)
        if hub_instance:
            print("\n--- Hub Diagnostic Grid on Failure ---")
            hub_instance.get_diagnostic_grid()
        sys.exit(1)
    finally:
        if hub_instance:
            hub_instance.shutdown()
        test_logger.info("🏁 SummarizerService Live Test Complete.")
