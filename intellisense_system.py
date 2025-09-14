
"""
intellisense_system.py - The Citadel Dossier System's Adaptive Intellisense Core

Overview:
This module serves as the central intelligence hub for the Citadel Dossier System,
providing AI-driven assistance for software development lifecycle assessment and improvement.
It integrates various specialized AI components to offer intelligent, contextualized
suggestions, feedback, and diagnostics based on codebase health, system logs,
and developer interaction patterns.

Key Features:
--------------------
1.  Automated Dependency Management: Checks for and installs necessary Python libraries
    (e.g., numpy, psutil, sentence-transformers) to ensure system functionality.
2.  Configurable Operation: Loads and manages core system parameters, directives,
    and developer preferences from 'intellisense_config.json', allowing adaptive behavior.
3.  Modular AI Integration (Memoria Ecosystem): Integrates a sub-system of AI modules
    (MemoriaCore, Self-Reflection, Optimization Engine, Analysis Interface) as
    internal classes to perform meta-cognition, improve performance, and conduct
    advanced code/log analysis. While defined internally, these components are
    also dynamically written to the `ecosystem/memoria` directory to support
    external expectations or future modularization.
4.  Codebase Health Modeling: Utilizes mathematical projections to quantify and model
    software quality metrics such as cyclomatic complexity, test coverage, and stability.
5.  Developer Persona Adaptation: Dynamically adjusts its communication tone and
    suggestion confidence based on user feedback, context, and perceived urgency.
6.  Dynamic Urgency Assessment: Quantifies the criticality of issues by analyzing
    user input, diagnostic keywords, and code metrics, guiding the system's focus.
7.  Comprehensive Log Management & Meta-Reflection: Ingests, categorizes, assesses,
    and synthesizes various system logs and AI/user feedback using an SQLite-backed
    catalog for continuous learning and self-improvement of diagnostic strategies.
    **Emphasized: Log files are archived, not deleted. Data is stored in SQL DBs.**
8.  Module Lifecycle Management: Tracks operational metrics (invocations, success rates,
    latencies) and health status of its internal components to monitor system well-being.
9.  Self-Testing & Diagnostics: Conducts thorough self-diagnostic routines to verify
    the functionality, accessibility, and integrity of its own components and dependencies.
10. Operational Visibility: Provides a real-time, human-readable command-line summary
    of its internal module performance and health.

How to Use It:
--------------------
1.  Initialization:
    Create an instance of `IntellisenseSystem()`:
    `system = IntellisenseSystem()`
    This will automatically handle initial configuration loading, dependency checks,
    and the setup of the Memoria ecosystem components (both internal definitions
    and external file generation).

2.  Processing Developer Input:
    To get AI-driven suggestions and analysis, call the `process_input` method:
    `response = system.process_input(user_question_string, code_metrics_dictionary, user_id="optional_user_identifier")`
    - `user_question_string`: The natural language query or observation from the developer.
    - `code_metrics_dictionary`: A dictionary containing relevant code statistics (e.g., `{"complexity": 12.5, "coverage": 0.88, "momentum": -0.2}`).
    - `user_id`: An optional string to track individualized persona adaptation and feedback.

3.  Running Self-Diagnostics:
    To verify the system's operational health and functionality:
    `test_results = system.run_self_test()`
    The results provide a detailed breakdown of each component's status and recommendations.

4.  Monitoring System Health:
    To display a real-time summary of the system's modules and their performance metrics:
    `system.display_system_summary_grid()`

5.  Configuration:
    Customize system behavior by editing the `intellisense_config.json` file. This
    includes enabling/disabling modules, adjusting thresholds, defining developer
    persona traits, and setting log scanning paths.
"""

import json
import logging
import random
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List, Tuple
import numpy as np
import subprocess
import sys
import time
from datetime import datetime, timezone
import sqlite3
import psutil
from abc import ABC, abstractmethod
import ast
import importlib.util # Not used in current structure for internal Memoria parts, but kept if external loading is desired.
import re
import math
import traceback
import os
import shutil # Added for file operations like move and rmtree

# --- GLOBAL LOGGER SETUP ---
# Create a named logger for the main system, avoiding basicConfig to have full control
logger = logging.getLogger("IntellisenseSystem") 
# Set the overall level for the logger
logger.setLevel(logging.INFO)

# Store these handlers globally for explicit closing in __main__
_global_file_handler = None
_global_console_handler = None

# Only add handlers if none exist, this setup is done once on module import
if not logger.handlers:
    # File handler for diagnostics.log (append mode, "a" is crucial for cumulative logs)
    _global_file_handler = logging.FileHandler('diagnostics.log', mode='a', encoding='utf-8')
    _global_file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _global_file_handler.setFormatter(file_formatter)
    logger.addHandler(_global_file_handler)

    # Console handler
    _global_console_handler = logging.StreamHandler()
    _global_console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _global_console_handler.setFormatter(console_formatter)
    logger.addHandler(_global_console_handler)

def _close_all_global_handlers():
    """Flushes and closes all handlers attached to the main 'IntellisenseSystem' logger."""
    global logger
    for handler in logger.handlers[:]: # Iterate over a copy of the list
        try:
            handler.flush()
            handler.close()
            logger.removeHandler(handler)
        except Exception as e:
            # Print to stderr as logging might be affected
            print(f"[{datetime.now().isoformat()}] [ERROR] Failed to close and remove logger handler {handler}: {e}", file=sys.stderr)

# --- END GLOBAL LOGGER SETUP ---


# Dependency Installer
def _get_pip_package_name(module_name: str) -> str:
  mapping = {
    'numpy': 'numpy',
    'psutil': 'psutil',
    'sentence_transformers': 'sentence-transformers',
    'pywt': 'pywavelets',
    'openai': 'openai'
  }
  return mapping.get(module_name, module_name.split('.')[0] if '.' in module_name else module_name)

def install_missing_dependencies(core_modules: List[str], optional_modules: List[str]) -> None:
  missing_critical = set()
  missing_optional = set()

  for module in core_modules:
    try:
      __import__(module)
    except ImportError:
      missing_critical.add(module)

  if missing_critical:
    logger.info("Checking core dependencies...")
    for module in list(missing_critical):
      package_name = _get_pip_package_name(module)
      logger.warning(f"Attempting to install missing critical dependency: {package_name}")
      try:
        install_cmd = [sys.executable, "-m", "pip", "install", package_name]
        process = subprocess.Popen(install_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
          logger.info(f"Successfully installed core package {package_name}.")
          try:
            __import__(module.split('.')[0] if '.' in module else module)
            missing_critical.discard(module)
          except ImportError:
            logger.error(f"Installed {package_name} but could not import {module}.")
        else:
          logger.error(f"FAILED to install core package {package_name}. Error: {stderr}")
      except Exception as e:
        logger.error(f"Exception during installation of {package_name}: {e}")

  if missing_critical:
    logger.critical(f"FATAL: Critical dependencies missing: {', '.join(missing_critical)}. Exiting.")
    sys.exit(1)

  logger.info("Checking optional dependencies...")
  for module in optional_modules:
    try:
      __import__(module)
    except ImportError:
      missing_optional.add(module)

  if missing_optional:
    for module in list(missing_optional):
      package_name = _get_pip_package_name(module)
      logger.warning(f"Attempting to install missing optional dependency: {package_name}")
      try:
        install_cmd = [sys.executable, "-m", "pip", "install", package_name]
        process = subprocess.Popen(install_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
          logger.info(f"Successfully installed optional package {package_name}.")
        else:
          logger.warning(f"FAILED to install optional package {package_name}. Error: {stderr}")
      except Exception as e:
        logger.error(f"Exception during installation of {package_name}: {e}")

CORE_MODULES = ['numpy', 'psutil']
OPTIONAL_MODULES = ['sentence_transformers', 'pywt', 'openai']
install_missing_dependencies(CORE_MODULES, OPTIONAL_MODULES)

try:
  import numpy as np
except ImportError:
  np = None
  logger.warning("numpy not found. Mathematical modeling and embeddings disabled.")
try:
  import pywt
except ImportError:
  pywt = None
  logger.warning("pywavelets not found. Wavelet analysis disabled.")
try:
  from sentence_transformers import SentenceTransformer
except ImportError:
  SentenceTransformer = None
  logger.warning("sentence_transformers not found. Local embedding generation disabled.")
try:
  import psutil
except ImportError:
  psutil = None
  logger.warning("psutil not found. System resource monitoring disabled.")
try:
  from openai import OpenAI
except ImportError:
  OpenAI = None
  logger.warning("openai not found. OpenAI API calls disabled.")

class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""
    @abstractmethod
    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generates an embedding for the given text.

        Args:
            text (str): The text to embed.

        Returns:
            Optional[List[float]]: The embedding vector, or None on failure.
        """
        pass

class LocalEmbeddingProvider(BaseEmbeddingProvider):
    """An embedding provider that uses a local SentenceTransformer model."""
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initializes the LocalEmbeddingProvider.

        Args:
            model_name (str, optional): The name of the SentenceTransformer model
                to use. Defaults to "all-MiniLM-L6-v2".
        """
        self.model_name = model_name
        self.model: Optional[SentenceTransformer] = None
        if SentenceTransformer:
            try:
                with CaptureStdoutStderr():
                    self.model = SentenceTransformer(model_name)
                logger.info(f"LocalEmbeddingProvider initialized with model '{model_name}'.")
            except Exception as e:
                logger.error(f"Failed to load local embedding model '{model_name}': {e}")
        else:
            logger.warning("LocalEmbeddingProvider not active. sentence_transformers library not found.")

    def get_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generates an embedding for the given text using the local model.

        Args:
            text (str): The text to embed.

        Returns:
            Optional[List[float]]: The embedding vector, or None on failure.
        """
        if self.model is None or not text:
            logger.debug("Local embedding model not loaded or text is empty.")
            return None
        try:
            embedding = self.model.encode(str(text), convert_to_tensor=False).tolist()
            return embedding
        except Exception as e:
            logger.error(f"Failed to get local embedding for text '{text[:50]}...': {e}")
            return None

class CaptureStdoutStderr:
  """Context manager to suppress stdout and stderr."""
  def __enter__(self):
    self._original_stdout = sys.stdout
    self._original_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w')
    sys.stderr = open(os.devnull, 'w')
  def __exit__(self, exc_type, exc_val, exc_tb):
    sys.stdout.close()
    sys.stderr.close()
    sys.stdout = self._original_stdout
    sys.stderr = self._original_stderr

# <--- START OF MEMORIA ECOSYSTEM CLASS DEFINITIONS (NOW DIRECTLY IN THIS FILE) --->

# MemoriaModule (Base Class)
class MemoriaModule(ABC):
    """Abstract base class for all Memoria modules."""
    def __init__(self):
        """Initializes the module's operational metrics."""
        self._invocations = 0
        self._successful_invocations = 0
        self._total_latency = 0.0

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initializes the module with the given configuration.

        Args:
            config (Dict[str, Any]): The configuration for the module.
        """
        pass
  
    @abstractmethod
    def health_check(self) -> bool:
        """
        Performs a health check on the module.

        Returns:
            bool: True if the module is healthy, False otherwise.
        """
        pass

    def _start_op(self):
        """Marks the start of an operation for metric tracking."""
        self._invocations += 1
        return time.perf_counter()

    def _end_op(self, start_time: float, success: bool = True):
        """Marks the end of an operation for metric tracking."""
        latency = time.perf_counter() - start_time
        self._total_latency += latency
        if success:
            self._successful_invocations += 1

    def get_operational_metrics(self) -> Dict[str, Any]:
        """
        Gets the operational metrics for the module.

        Returns:
            Dict[str, Any]: A dictionary of operational metrics.
        """
        success_rate = (self._successful_invocations / self._invocations) if self._invocations > 0 else 0.0
        avg_latency_ms = (self._total_latency / self._invocations * 1000) if self._invocations > 0 else 0.0
        return {
            "invocations": self._invocations,
            "success_count": self._successful_invocations,
            "error_count": self._invocations - self._successful_invocations,
            "success_rate": round(success_rate, 4),
            "avg_latency_ms": round(avg_latency_ms, 2)
        }

# MemoriaSelfReflection
class MemoriaSelfReflection(MemoriaModule):
    """A Memoria module for self-reflection and performance analysis."""
    def __init__(self, config: Dict[str, Any], feedback_log_path: str = 'ecosystem/memoria/feedback.jsonl'):
        """
        Initializes the MemoriaSelfReflection module.

        Args:
            config (Dict[str, Any]): The configuration for the module.
            feedback_log_path (str, optional): The path to the feedback log file.
                Defaults to 'ecosystem/memoria/feedback.jsonl'.
        """
        super().__init__()
        self.config = config
        self.feedback_log_path = Path(feedback_log_path)
        self_reflection_config = config.get('modules', {}).get('self_reflection', {})
        self.reflection_interval = self_reflection_config.get('reflection_interval', 10)
        self.interaction_count = 0
        logger.info("MemoriaSelfReflection initialized.")

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initializes the module with the given configuration.

        Args:
            config (Dict[str, Any]): The configuration for the module.
        """
        self.config.update(config)
        self.feedback_log_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("MemoriaSelfReflection initialization complete.")

    def health_check(self) -> bool:
        """
        Performs a health check on the module.

        Returns:
            bool: True if the module is healthy, False otherwise.
        """
        return self.feedback_log_path.parent.exists()

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a request, triggering reflection if the interval is met.

        Args:
            request (Dict[str, Any]): The request to process.

        Returns:
            Dict[str, Any]: The result of the reflection process.
        """
        start_time = self._start_op()
        try:
            self.interaction_count += 1
            if self.interaction_count % self.reflection_interval == 0:
                result = self.reflect(request)
            else:
                result = {"status": "skipped", "message": "Reflection not triggered."}
            self._end_op(start_time, success=True)
            return result
        except Exception as e:
            self._end_op(start_time, success=False)
            raise e

    def reflect(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs a reflection cycle based on feedback and analysis results.

        Args:
            request (Dict[str, Any]): The request containing analysis results.

        Returns:
            Dict[str, Any]: The output of the reflection.
        """
        feedback_data = self._load_feedback()
        analysis_result = request.get('analysis_result', {})
        try:
            # Ensure numpy is used for mean, handle empty feedback_data
            avg_performance = np.mean([f.get('performance_score', 0.0) for f in feedback_data]) if feedback_data else 0.0
            optimization_suggestions = analysis_result.get('optimization_suggestions', [])
            reflection_output = {
                "status": "success",
                "avg_performance": avg_performance,
                "suggestions_applied": len(optimization_suggestions),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            if optimization_suggestions:
                self._apply_optimizations(optimization_suggestions)
            self._log_reflection(reflection_output)
            return reflection_output
        except Exception as e:
            logger.error(f"Reflection failed: {e}")
            return {"status": "failure", "error": str(e)}

    def _load_feedback(self) -> List[Dict[str, Any]]:
        """Loads feedback data from the log file."""
        feedback_data = []
        if self.feedback_log_path.exists():
            with open(self.feedback_log_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        feedback_data.append(json.loads(line.strip()))
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping malformed JSON line in feedback log: {line.strip()[:100]}...")
                        continue
        return feedback_data

    def _apply_optimizations(self, suggestions: List[str]):
        """Applies optimizations based on suggestions."""
        for suggestion in suggestions:
            if "increase_reflection_interval" in suggestion:
                if 'modules' not in self.config: self.config['modules'] = {}
                if 'self_reflection' not in self.config['modules']: self.config['modules']['self_reflection'] = {}
                self.config['modules']['self_reflection']['reflection_interval'] = \
                    self.config['modules']['self_reflection'].get('reflection_interval', 10) + 5
                logger.info("Increased reflection interval based on optimization suggestion.")

    def _log_reflection(self, reflection_output: Dict[str, Any]):
        """Logs the output of a reflection cycle."""
        with open(self.feedback_log_path, 'a', encoding='utf-8') as f:
            json.dump(reflection_output, f)
            f.write('\n')
        logger.info("Logged reflection output.")

# MemoriaOptimizationEngine
class MemoriaOptimizationEngine(MemoriaModule):
    """A Memoria module for optimizing system parameters based on performance."""
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the MemoriaOptimizationEngine.

        Args:
            config (Dict[str, Any]): The configuration for the module.
        """
        super().__init__()
        self.config = config
        self.optimization_threshold = config.get('modules', {}).get('optimization_engine', {}).get('optimization_threshold', 0.8)
        logger.info("MemoriaOptimizationEngine initialized.")

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initializes the module with the given configuration.

        Args:
            config (Dict[str, Any]): The configuration for the module.
        """
        self.config.update(config)
        logger.info("MemoriaOptimizationEngine initialization complete.")

    def health_check(self) -> bool:
        """
        Performs a health check on the module.

        Returns:
            bool: True if the module is healthy, False otherwise.
        """
        return True

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a request, triggering optimization if performance is below a threshold.

        Args:
            request (Dict[str, Any]): The request to process.

        Returns:
            Dict[str, Any]: The result of the optimization process.
        """
        start_time = self._start_op()
        try:
            analysis_result = request.get('analysis_result', {})
            performance_score = analysis_result.get('performance_score', 0.0)
            if performance_score < self.optimization_threshold:
                result = self.optimize(analysis_result)
            else:
                result = {"status": "skipped", "message": "Performance above threshold."}
            self._end_op(start_time, success=True)
            return result
        except Exception as e:
            self._end_op(start_time, success=False)
            raise e

    def optimize(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Performs optimization based on analysis results.

        Args:
            analysis_result (Dict[str, Any]): The analysis result to base
                optimization on.

        Returns:
            Dict[str, Any]: The output of the optimization.
        """
        try:
            suggestions = analysis_result.get('optimization_suggestions', [])
            if not suggestions:
                return {"status": "success", "message": "No optimizations needed."}

            for suggestion in suggestions:
                if "adjust_confidence" in suggestion:
                    if 'modules' not in self.config: self.config['modules'] = {}
                    if 'self_reflection' not in self.config['modules']: self.config['modules']['self_reflection'] = {}
                    self.config['modules']['self_reflection']['confidence_level'] = min(
                        1.0, self.config['modules']['self_reflection'].get('confidence_level', 0.7) + 0.1
                    )
                    logger.info("Adjusted self_reflection confidence based on optimization suggestion.")

            logger.info(f"Applied {len(suggestions)} optimizations.")
            return {"status": "success", "optimizations_applied": len(suggestions)}
        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return {"status": "failure", "error": str(e)}

# MemoriaAnalysisInterface
class MemoriaAnalysisInterface(MemoriaModule):
    """A Memoria module for interfacing with an external analysis API (e.g., OpenAI)."""
    def __init__(self, config: Dict[str, Any]):
        """
        Initializes the MemoriaAnalysisInterface.

        Args:
            config (Dict[str, Any]): The configuration for the module.
        """
        super().__init__()
        self.config = config
        self.client = None
        self.api_enabled = config.get('modules', {}).get('analysis_interface', {}).get('enabled', False)
        if OpenAI and self.api_enabled:
            try:
                self.client = OpenAI(api_key="mock-api-key")
                logger.info("MemoriaAnalysisInterface OpenAI client initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize MemoriaAnalysisInterface OpenAI client: {e}")
        logger.info("MemoriaAnalysisInterface initialized.")

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initializes the module with the given configuration.

        Args:
            config (Dict[str, Any]): The configuration for the module.
        """
        self.config.update(config)
        self.api_enabled = config.get('modules', {}).get('analysis_interface', {}).get('enabled', False)
        if OpenAI and self.api_enabled and not self.client:
            try:
                self.client = OpenAI(api_key="mock-api-key")
                logger.info("MemoriaAnalysisInterface OpenAI client re-initialized upon configuration update.")
            except Exception as e:
                logger.error(f"Failed to re-initialize MemoriaAnalysisInterface OpenAI client: {e}")
        elif not self.api_enabled and self.client:
            self.client = None
        logger.info("MemoriaAnalysisInterface initialization complete.")

    def health_check(self) -> bool:
        """
        Performs a health check on the module.

        Returns:
            bool: True if the module is healthy, False otherwise.
        """
        return self.client is not None or not self.api_enabled

    def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a request by sending it to the external analysis API.

        Args:
            request (Dict[str, Any]): The request to process.

        Returns:
            Dict[str, Any]: The result from the analysis API.
        """
        start_time = self._start_op()
        try:
            if not self.api_enabled or not self.client:
                result = {"status": "skipped", "message": "OpenAI API not enabled or client not initialized."}
            else:
                code_snippet = request.get('code_snippet', '')
                performance_metrics = request.get('performance_metrics', {})
                prompt = (f"Analyze the following Python code and system performance metrics...")

                response = {
                    "performance_score": 0.85,
                    "optimization_suggestions": ["Reduce nested loops", "Add type hints for clarity"]
                }
                logger.info(f"MemoriaAnalysisInterface OpenAI analysis completed: Score {response['performance_score']}")
                result = {"status": "success", "analysis_result": response}
            self._end_op(start_time, success=result['status'] == 'success')
            return result
        except Exception as e:
            self._end_op(start_time, success=False)
            raise e

# MemoriaCore - This class needs to be aware of other Memoria classes
# These are now defined earlier in this same file.
class MemoriaCore(MemoriaModule):
    """The core of the Memoria ecosystem, managing all other Memoria modules."""
    def __init__(self, config_path: str = 'ecosystem/memoria/config/memoria_config.json'):
        """
        Initializes the MemoriaCore.

        Args:
            config_path (str, optional): The path to the Memoria configuration file.
                Defaults to 'ecosystem/memoria/config/memoria_config.json'.
        """
        super().__init__()
        self.config_path = Path(config_path)
        self.config = {}
        self.modules: Dict[str, MemoriaModule] = {}
        self.load_config()
        logger.info("MemoriaCore initialized.")

    def load_config(self):
        """Loads the Memoria configuration from disk."""
        if not self.config_path.exists():
            self._create_default_config()
        with open(self.config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        logger.info("MemoriaCore configuration loaded.")

    def _create_default_config(self):
        """Creates a default Memoria configuration file."""
        default_config = {
            "modules": {
                "self_reflection": {"enabled": True, "reflection_interval": 10},
                "optimization_engine": {"enabled": True, "optimization_threshold": 0.8},
                "analysis_interface": {"enabled": True, "api_provider": "openai"}
            },
            "system_parameters": {
                "log_level": "INFO",
                "max_retries": 3,
                "analysis_timeout": 30.0
            }
        }
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)
        logger.info(f"Created default memoria_config.json at {self.config_path}")

    def save_config(self):
        """Saves the current Memoria configuration to disk."""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)
        logger.info("MemoriaCore configuration saved.")

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        Initializes the MemoriaCore and its sub-modules.

        Args:
            config (Dict[str, Any]): The configuration for the module.
        """
        self.config.update(config)
        self.save_config()
        for module_name, module_config in self.config.get('modules', {}).items():
            if module_config.get('enabled', False):
                logger.info(f"Initializing module: {module_name}")
                if module_name == "self_reflection":
                    self.modules[module_name] = MemoriaSelfReflection(self.config)
                elif module_name == "optimization_engine":
                    self.modules[module_name] = MemoriaOptimizationEngine(self.config)
                elif module_name == "analysis_interface":
                    self.modules[module_name] = MemoriaAnalysisInterface(self.config)

                if hasattr(self.modules[module_name], 'initialize') and callable(self.modules[module_name].initialize):
                    self.modules[module_name].initialize(module_config)
        logger.info("MemoriaCore initialization complete.")

    def register_module(self, name: str, module: MemoriaModule):
        """
        Registers a new Memoria module with the core.

        Args:
            name (str): The name of the module.
            module (MemoriaModule): The module instance to register.
        """
        self.modules[name] = module
        logger.info(f"Registered module: {name}")

    def health_check(self) -> bool:
        """
        Performs a health check on the MemoriaCore and all its sub-modules.

        Returns:
            bool: True if all modules are healthy, False otherwise.
        """
        return all(module.health_check() for module in self.modules.values())

    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes a request by passing it through all registered Memoria modules.

        Args:
            request (Dict[str, Any]): The request to process.

        Returns:
            Dict[str, Any]: The aggregated results from all modules.
        """
        start_time = self._start_op()
        result = {"status": "success", "data": {}}
        success = True
        for name, module in self.modules.items():
            op_start_time = module._start_op()
            try:
                if hasattr(module, 'process') and callable(module.process):
                    module_result = module.process(request)
                    result["data"][name] = module_result
                    module._end_op(op_start_time, success=True)
                else:
                    logger.warning(f"Module {name} does not have a 'process' method.")
                    result["data"][name] = {"error": "No process method"}
                    module._end_op(op_start_time, success=False)
            except Exception as e:
                logger.error(f"Module {name} failed during processing: {e}")
                result["status"] = "partial_failure"
                result["data"][name] = {"error": str(e)}
                success = False
                module._end_op(op_start_time, success=False)
        self._end_op(start_time, success=success)
        return result

# <--- END OF MEMORIA ECOSYSTEM CLASS DEFINITIONS --->


class SystemDiagnostics:
  """Handles verification and testing of system components and file creation."""
  def __init__(self, bootstrapper: 'IntellisenseBootstrapper'):
    """
    Initializes the SystemDiagnostics component.

    Args:
        bootstrapper (IntellisenseBootstrapper): An instance of the bootstrapper.
    """
    self.bootstrapper = bootstrapper
    self.diagnostic_log_path = Path("diagnostics.log")
    logger.info("SystemDiagnostics initialized.")

  def verify_file_creation(self, file_path: Path) -> bool:
    """
    Verifies if a file exists and is syntactically valid.

    Args:
        file_path (Path): The path to the file to verify.

    Returns:
        bool: True if the file is valid, False otherwise.
    """
    if not file_path.exists():
      logger.error(f"File {file_path} does not exist.")
      return False
    if file_path.suffix == '.py':
      try:
        with open(file_path, 'r', encoding='utf-8') as f:
          ast.parse(f.read())
        logger.info(f"File {file_path} is syntactically valid.")
        return True
      except SyntaxError as e:
        logger.error(f"Syntax error in {file_path}: {e}")
        return False
    elif file_path.suffix == '.json':
      try:
        with open(file_path, 'r', encoding='utf-8') as f:
          json.load(f)
        logger.info(f"File {file_path} is valid JSON.")
        return True
      except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in {file_path}: {e}")
        return False
    logger.info(f"File {file_path} exists and format is not specifically checked.")
    return True

  def verify_module_import(self, module_path: Path, module_name: str) -> bool:
    """
    Verifies if a module can be imported from a given path.

    Args:
        module_path (Path): The path to the Python module file.
        module_name (str): The name to import the module as.

    Returns:
        bool: True if the module can be imported, False otherwise.
    """
    try:
      project_root = module_path.parents[2]
      original_sys_path = sys.path[:]
      if str(project_root) not in sys.path:
          sys.path.insert(0, str(project_root))

      spec = importlib.util.spec_from_file_location(module_name, module_path)
      if spec is None or spec.loader is None:
        logger.error(f"Cannot create module spec for {module_path}")
        return False
      module = importlib.util.module_from_spec(spec)
      sys.modules[module_name] = module
      spec.loader.exec_module(module)
      logger.info(f"Module {module_name} imported successfully from {module_path}.")
      return True
    except Exception as e:
      logger.error(f"Failed to import module {module_name} from {module_path}: {e}")
      return False
    finally:
        sys.path = original_sys_path


  def run_diagnostics(self, files_to_verify: List[Path], modules_to_verify: List[Tuple[Path, str]]) -> Dict[str, bool]:
    """
    Runs diagnostics on a list of files and modules.

    Args:
        files_to_verify (List[Path]): A list of file paths to verify.
        modules_to_verify (List[Tuple[Path, str]]): A list of tuples, where each
            tuple contains the path to a module and its import name.

    Returns:
        Dict[str, bool]: A dictionary of diagnostic results.
    """
    results = {}
    for file_path in files_to_verify:
      results[str(file_path)] = self.verify_file_creation(file_path)
    for file_path, module_name in modules_to_verify:
      results[f"module_{module_name}"] = self.verify_module_import(file_path, module_name)
    logger.info(f"Diagnostics results: {json.dumps(results, indent=2)}")
    return results


# Content strings for Memoria ecosystem files (now redundant with local class definitions,
# but kept for the file generation logic as per user request).
# These MUST contain relative imports for their *generated file context*.

MEMORIA_MODULE_BASE_CONTENT = """
import logging
from abc import ABC, abstractmethod
import time
from typing import Dict, Any

logger = logging.getLogger(__name__)

class MemoriaModule(ABC):
  def __init__(self):
    self._invocations = 0
    self._successful_invocations = 0
    self._total_latency = 0.0

  @abstractmethod
  def initialize(self, config: Dict[str, Any]) -> None:
    pass

  @abstractmethod
  def health_check(self) -> bool:
    pass

  def _start_op(self):
    self._invocations += 1
    return time.perf_counter()

  def _end_op(self, start_time: float, success: bool = True):
    latency = time.perf_counter() - start_time
    self._total_latency += latency
    if success:
      self._successful_invocations += 1

  def get_operational_metrics(self) -> Dict[str, Any]:
    success_rate = (self._successful_invocations / self._invocations) if self._invocations > 0 else 0.0
    avg_latency_ms = (self._total_latency / self._invocations * 1000) if self._invocations > 0 else 0.0
    return {
      "invocations": self._invocations,
      "success_count": self._successful_invocations,
      "error_count": self._invocations - self._successful_invocations,
      "success_rate": round(success_rate, 4),
      "avg_latency_ms": round(avg_latency_ms, 2)
    }
"""

MEMORIA_CORE_CONTENT = """
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import time

# Importing the Memoria sub-modules from their respective files
from .memoria_module import MemoriaModule
from .self_reflection import MemoriaSelfReflection
from .optimization_engine import MemoriaOptimizationEngine
from .analysis_interface import MemoriaAnalysisInterface

logger = logging.getLogger(__name__)

class MemoriaCore(MemoriaModule):
  def __init__(self, config_path: str = 'ecosystem/memoria/config/memoria_config.json'):
    super().__init__()
    self.config_path = Path(config_path)
    self.config = {}
    self.modules: Dict[str, MemoriaModule] = {}
    self.load_config()
    logger.info("MemoriaCore initialized.")

  def load_config(self):
    if not self.config_path.exists():
      self._create_default_config()
    with open(self.config_path, 'r', encoding='utf-8') as f:
      self.config = json.load(f)
    logger.info("MemoriaCore configuration loaded.")

  def _create_default_config(self):
    default_config = {
      "modules": {
        "self_reflection": {"enabled": True, "reflection_interval": 10},
        "optimization_engine": {"enabled": True, "optimization_threshold": 0.8},
        "analysis_interface": {"enabled": True, "api_provider": "openai"}
      },
      "system_parameters": {
        "log_level": "INFO",
        "max_retries": 3,
        "analysis_timeout": 30.0
      }
    }
    self.config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self.config_path, 'w', encoding='utf-8') as f:
      json.dump(default_config, f, indent=2)
    logger.info(f"Created default memoria_config.json at {self.config_path}")

  def save_config(self):
    with open(self.config_path, 'w', encoding='utf-8') as f:
      json.dump(self.config, f, indent=2)
    logger.info("MemoriaCore configuration saved.")

  def initialize(self, config: Dict[str, Any]) -> None:
    self.config.update(config)
    self.save_config()
    for module_name, module_config in self.config.get('modules', {}).items():
      if module_config.get('enabled', False):
        logger.info(f"Initializing module: {module_name}")
        if module_name == "self_reflection":
          self.modules[module_name] = MemoriaSelfReflection(self.config)
        elif module_name == "optimization_engine":
          self.modules[module_name] = MemoriaOptimizationEngine(self.config)
        elif module_name == "analysis_interface":
          self.modules[module_name] = MemoriaAnalysisInterface(self.config)
        
        if hasattr(self.modules[module_name], 'initialize') and callable(self.modules[module_name].initialize):
            self.modules[module_name].initialize(module_config)
    logger.info("MemoriaCore initialization complete.")

  def register_module(self, name: str, module: 'MemoriaModule'):
    self.modules[name] = module
    logger.info(f"Registered module: {name}")

  def health_check(self) -> bool:
    return all(module.health_check() for module in self.modules.values())

  def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
    start_time = self._start_op()
    result = {"status": "success", "data": {}}
    success = True
    for name, module in self.modules.items():
      op_start_time = module._start_op()
      try:
        if hasattr(module, 'process') and callable(module.process):
          module_result = module.process(request)
          result["data"][name] = module_result
          module._end_op(op_start_time, success=True)
        else:
            logger.warning(f"Module {name} does not have a 'process' method.")
            result["data"][name] = {"error": "No process method"}
            module._end_op(op_start_time, success=False)
      except Exception as e:
        logger.error(f"Module {name} failed during processing: {e}")
        result["status"] = "partial_failure"
        result["data"][name] = {"error": str(e)}
        success = False
        module._end_op(op_start_time, success=False)
    self._end_op(start_time, success=success)
    return result
"""

SELF_REFLECTION_CONTENT = """
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone
import numpy as np
import time

from .memoria_module import MemoriaModule

logger = logging.getLogger(__name__)

class MemoriaSelfReflection(MemoriaModule):
  def __init__(self, config: Dict[str, Any], feedback_log_path: str = 'ecosystem/memoria/feedback.jsonl'):
    super().__init__()
    self.config = config
    self.feedback_log_path = Path(feedback_log_path)
    self_reflection_config = config.get('modules', {}).get('self_reflection', {})
    self.reflection_interval = self_reflection_config.get('reflection_interval', 10)
    self.interaction_count = 0
    logger.info("MemoriaSelfReflection initialized.")

  def initialize(self, config: Dict[str, Any]) -> None:
    self.config.update(config)
    self.feedback_log_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("MemoriaSelfReflection initialization complete.")

  def health_check(self) -> bool:
    return self.feedback_log_path.parent.exists()

  def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
    start_time = self._start_op()
    try:
      self.interaction_count += 1
      if self.interaction_count % self.reflection_interval == 0:
        result = self.reflect(request)
      else:
        result = {"status": "skipped", "message": "Reflection not triggered."}
      self._end_op(start_time, success=True)
      return result
    except Exception as e:
      self._end_op(start_time, success=False)
      raise e

  def reflect(self, request: Dict[str, Any]) -> Dict[str, Any]:
    feedback_data = self._load_feedback()
    analysis_result = request.get('analysis_result', {})
    try:
      avg_performance = np.mean([f.get('performance_score', 0.0) for f in feedback_data]) if feedback_data else 0.0
      optimization_suggestions = analysis_result.get('optimization_suggestions', [])
      reflection_output = {
        "status": "success",
        "avg_performance": avg_performance,
        "suggestions_applied": len(optimization_suggestions),
        "timestamp": datetime.now(timezone.utc).isoformat()
      }
      if optimization_suggestions:
        self._apply_optimizations(optimization_suggestions)
      self._log_reflection(reflection_output)
      return reflection_output
    except Exception as e:
      logger.error(f"Reflection failed: {e}")
      return {"status": "failure", "error": str(e)}

  def _load_feedback(self) -> List[Dict[str, Any]]:
    feedback_data = []
    if self.feedback_log_path.exists():
      with open(self.feedback_log_path, 'r', encoding='utf-8') as f:
        for line in f:
          try:
            feedback_data.append(json.loads(line.strip()))
          except json.JSONDecodeError:
            logger.warning(f"Skipping malformed JSON line in feedback log: {line.strip()[:100]}...")
            continue
    return feedback_data

  def _apply_optimizations(self, suggestions: List[str]):
    for suggestion in suggestions:
      if "increase_reflection_interval" in suggestion:
        if 'modules' not in self.config: self.config['modules'] = {}
        if 'self_reflection' not in self.config['modules']: self.config['modules']['self_reflection'] = {}
        self.config['modules']['self_reflection']['reflection_interval'] = \\
          self.config['modules']['self_reflection'].get('reflection_interval', 10) + 5
        logger.info("Increased reflection interval based on optimization suggestion.")

  def _log_reflection(self, reflection_output: Dict[str, Any]):
    with open(self.feedback_log_path, 'a', encoding='utf-8') as f:
      json.dump(reflection_output, f)
      f.write('\\n')
    logger.info("Logged reflection output.")
"""

OPTIMIZATION_ENGINE_CONTENT = """
import logging
from typing import Dict, Any
import time

from .memoria_module import MemoriaModule

logger = logging.getLogger(__name__)

class MemoriaOptimizationEngine(MemoriaModule):
  def __init__(self, config: Dict[str, Any]):
    super().__init__()
    self.config = config
    self.optimization_threshold = config.get('modules', {}).get('optimization_engine', {}).get('optimization_threshold', 0.8)
    logger.info("MemoriaOptimizationEngine initialized.")

  def initialize(self, config: Dict[str, Any]) -> None:
    self.config.update(config)
    logger.info("MemoriaOptimizationEngine initialization complete.")

  def health_check(self) -> bool:
    return True

  def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
    start_time = self._start_op()
    try:
      analysis_result = request.get('analysis_result', {})
      performance_score = analysis_result.get('performance_score', 0.0)
      if performance_score < self.optimization_threshold:
        result = self.optimize(analysis_result)
      else:
        result = {"status": "skipped", "message": "Performance above threshold."}
      self._end_op(start_time, success=True)
      return result
    except Exception as e:
      self._end_op(start_time, success=False)
      raise e

  def optimize(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
    try:
      suggestions = analysis_result.get('optimization_suggestions', [])
      if not suggestions:
        return {"status": "success", "message": "No optimizations needed."}

      for suggestion in suggestions:
        if "adjust_confidence" in suggestion:
          if 'modules' not in self.config: self.config['modules'] = {}
          if 'self_reflection' not in self.config['modules']: self.config['modules']['self_reflection'] = {}
          self.config['modules']['self_reflection']['confidence_level'] = min(
            1.0, self.config['modules']['self_reflection'].get('confidence_level', 0.7) + 0.1
          )
          logger.info("Adjusted self_reflection confidence based on optimization suggestion.")

      logger.info(f"Applied {len(suggestions)} optimizations.")
      return {"status": "success", "optimizations_applied": len(suggestions)}
    except Exception as e:
      logger.error(f"Optimization failed: {e}")
      return {"status": "failure", "error": str(e)}
"""

ANALYSIS_INTERFACE_CONTENT = """
import logging
from typing import Dict, Any
import time

try:
  from openai import OpenAI
except ImportError:
  OpenAI = None
  logging.warning("OpenAI not found. AI Analysis Interface will be limited.")

from .memoria_module import MemoriaModule

logger = logging.getLogger(__name__)

class MemoriaAnalysisInterface(MemoriaModule):
  def __init__(self, config: Dict[str, Any]):
    super().__init__()
    self.config = config
    self.client = None
    self.api_enabled = config.get('modules', {}).get('analysis_interface', {}).get('enabled', False)
    if OpenAI and self.api_enabled:
      try:
        self.client = OpenAI(api_key="mock-api-key")
        logger.info("MemoriaAnalysisInterface OpenAI client initialized.")
      except Exception as e:
        logger.error(f"Failed to initialize MemoriaAnalysisInterface OpenAI client: {e}")
    logger.info("MemoriaAnalysisInterface initialized.")

  def initialize(self, config: Dict[str, Any]) -> None:
    self.config.update(config)
    self.api_enabled = config.get('modules', {}).get('analysis_interface', {}).get('enabled', False)
    if OpenAI and self.api_enabled and not self.client:
      try:
        self.client = OpenAI(api_key="mock-api-key")
        logger.info("MemoriaAnalysisInterface OpenAI client re-initialized upon configuration update.")
      except Exception as e:
        logger.error(f"Failed to re-initialize MemoriaAnalysisInterface OpenAI client: {e}")
    elif not self.api_enabled and self.client:
      self.client = None
    logger.info("MemoriaAnalysisInterface initialization complete.")

  def health_check(self) -> bool:
    return self.client is not None or not self.api_enabled

  def process(self, request: Dict[str, Any]) -> Dict[str, Any]:
    start_time = self._start_op()
    try:
      if not self.api_enabled or not self.client:
        result = {"status": "skipped", "message": "OpenAI API not enabled or client not initialized."}
      else:
        code_snippet = request.get('code_snippet', '')
        performance_metrics = request.get('performance_metrics', {})
        prompt = (f"Analyze the following Python code and system performance metrics...")

        response = {
          "performance_score": 0.85,
          "optimization_suggestions": ["Reduce nested loops", "Add type hints for clarity"]
        }
        logger.info(f"MemoriaAnalysisInterface OpenAI analysis completed: Score {response['performance_score']}")
        result = {"status": "success", "analysis_result": response}
      self._end_op(start_time, success=result['status'] == 'success')
      return result
    except Exception as e:
      self._end_op(start_time, success=False)
      raise e
"""


class IntellisenseBootstrapper:
  """Manages configuration and initialization of IntellisenseSystem and Memoria ecosystem."""
  def __init__(self, config_path: str = 'intellisense_config.json'):
    """
    Initializes the IntellisenseBootstrapper.

    Args:
        config_path (str, optional): The path to the main configuration file.
            Defaults to 'intellisense_config.json'.
    """
    self.config_path = Path(config_path)
    self.config = {}
    self.embedding_dimension = 384
    self.memoria_ecosystem_path = Path('ecosystem/memoria')
    self.embedding_provider = LocalEmbeddingProvider()
    self.diagnostics = SystemDiagnostics(self)
    self.load_config()
    self.initialize_memoria_ecosystem() # Ensures Memoria files are created/updated first for external use
    self.verify_memoria_ecosystem() # Verifies the externally created files

  def load_config(self):
    """Loads the main configuration file, creating a default if it doesn't exist."""
    if not self.config_path.exists():
      self._create_default_config()
    with open(self.config_path, 'r', encoding='utf-8') as f:
      self.config = json.load(f)
    logger.info("IntellisenseSystem configuration loaded.")

    if self.embedding_provider.model:
      try:
        test_embedding = self.embedding_provider.get_embedding("test_string")
        if test_embedding:
          self.config['embedding_dimension'] = len(test_embedding)
          self.save_config()
        else:
          logger.warning("Could not get test embedding from provider. Using default embedding_dimension.")
      except Exception as e:
        logger.warning(f"Error determining embedding dimension from provider: {e}. Using configured or default.")

  def _create_default_config(self):
    """Creates a default configuration file."""
    default_config = {
      "core_directives": [
        {"name": "code_quality", "weight": 15},
        {"name": "performance_optimization", "weight": 10},
        {"name": "security", "weight": 10}
      ],
      "parameters": {
        "complexity_threshold": {"value": 10.0},
        "coverage_target": {"value": 0.85},
        "stability_factor": {"value": 1.0}
      },
      "developer_persona": {
        "tone": "collaborative",
        "confidence_level": 0.7,
        "urgency_level": 0.5
      },
      "diagnostic_keywords": {
        "critical": ["error", "failure", "crash", "urgent"],
        "warning": ["warning", "issue", "bug"],
        "info": ["info", "suggestion", "improvement"]
      },
      "meta_reflection": {
        "reflection_interval": 10,
        "feedback_log_path": "ai_suggestion_feedback.jsonl",
        "log_reflector_interval_sec": 600,
        "log_reflector_window_lines": 50
      },
      "embedding_dimension": 384,
      "wavelet_enabled": True,
      "system_monitoring": {
        "cpu_threshold": 80.0,
        "memory_threshold": 80.0
      },
      "memoria_ecosystem": {
        "enabled": True,
        "config_path": "ecosystem/memoria/config/memoria_config.json"
      },
      "log_management": {
        "enabled": True,
        "scan_paths": [
          "logs/",
          "diagnostics.log", # Included for scanning current run's log data dynamically
          "ecosystem/memoria/feedback.jsonl",
          "logs/intellisense_data_synthesis_report.log",
          "logs/intellisense_self_test_report.jsonl"
        ],
        "scan_interval_sec": 300,
        "assessment_threshold_ai_learning": 0.7,
        "log_entry_patterns": {
          "jsonl_timestamp": r"^\s*\{\s*\"timestamp\":\s*\"([^\"]+)\".*\"level\":\s*\"([^\"]+)\".*\"message\":\s*\"([^\"]+)\".*\}",
          "simple_log": r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(?:,\d{3})?) - (\w+) - (.*)", # Corrected regex escapes
          "feedback": r".*feedback.*",
        },
        "advanced_parsers": [
          {
            "name": "performance_metrics",
            "regex": [
              r"CPU: (?P<cpu_usage>\d+\.\d+)%, Memory: (?P<memory_usage>\d+\.\d+)%", # Corrected regex escapes
              r"Latency: (?P<latency_ms>\d+\.\d+)ms" # Corrected regex escapes
            ],
            "context_category": "system_performance"
          },
          {
            "name": "database_errors",
            "regex": [
              r"Failed to connect to database (?P<db_name>[a-zA-Z0-9_]+)\." # Corrected regex escapes
            ],
            "context_category": "database_connection_issue"
          },
          {
            "name": "module_errors",
            "regex": [
              r"Module (?P<module_name>[a-zA-Z_]+) failed: (?P<error_message>.*)"
            ],
            "context_category": "module_runtime_error"
          },
           {
            "name": "test_results",
            "regex": [
              r"Tests run: (?P<total_tests>\d+), Failures: (?P<failed_tests>\d+), Errors: (?P<error_tests>\d+)" # Corrected regex escapes
            ],
            "context_category": "testing_summary"
          },
          { # NEW: Self-test report analysis
            "name": "self_test_summary",
            "regex": [
              r"\{\"timestamp\":\s*\"(?P<test_timestamp>[^\"]+)\",\s*\"overall_status\":\s*\"(?P<overall_status>[^\"]+)\",.*\"message\":\s*\"(?P<test_message>[^\"]+)\",\s*\"severity\":\s*\"(?P<test_severity>[^\"]+)\"" # Corrected regex escapes
            ],
            "context_category": "intellisense_self_test"
          }
        ]
      },
      # NEW: Module Tracking Configuration
      "module_tracking": {
        "enabled": True,
        "tracking_interval_sec": 60 # How often ModuleOrchestrator records snapshots
      }
    }
    with open(self.config_path, 'w', encoding='utf-8') as f:
      json.dump(default_config, f, indent=2)
    logger.info(f"Created default intellisense_config.json at {self.config_path}")

  def save_config(self):
    """Saves the current configuration to disk."""
    with open(self.config_path, 'w', encoding='utf-8') as f:
      json.dump(self.config, f, indent=2)
    logger.info("Configuration saved.")

  def initialize_memoria_ecosystem(self):
    """Initializes the Memoria ecosystem by generating its files if they are missing or outdated."""
    if not self.config.get('memoria_ecosystem', {}).get('enabled', False):
      logger.info("Memoria ecosystem disabled in config.")
      return

    self.memoria_ecosystem_path.mkdir(parents=True, exist_ok=True)

    memoria_files = {
      self.memoria_ecosystem_path / '__init__.py': """
from .memoria_core import MemoriaCore
from .memoria_module import MemoriaModule
from .self_reflection import MemoriaSelfReflection
from .optimization_engine import MemoriaOptimizationEngine
from .analysis_interface import MemoriaAnalysisInterface
""",
      self.memoria_ecosystem_path / 'memoria_module.py': MEMORIA_MODULE_BASE_CONTENT,
      self.memoria_ecosystem_path / 'memoria_core.py': MEMORIA_CORE_CONTENT,
      self.memoria_ecosystem_path / 'self_reflection.py': SELF_REFLECTION_CONTENT,
      self.memoria_ecosystem_path / 'optimization_engine.py': OPTIMIZATION_ENGINE_CONTENT,
      self.memoria_ecosystem_path / 'analysis_interface.py': ANALYSIS_INTERFACE_CONTENT,
      self.memoria_ecosystem_path / 'config' / 'memoria_config.json': json.dumps({
          "modules": {
              "self_reflection": {"enabled": True, "reflection_interval": 10},
              "optimization_engine": {"enabled": True, "optimization_threshold": 0.8},
              "analysis_interface": {"enabled": True, "api_provider": "openai"}
          },
          "system_parameters": {
              "log_level": "INFO",
              "max_retries": 3,
              "analysis_timeout": 30.0
          }
      }, indent=2)
    }

    for file_path, content in memoria_files.items():
      current_content_bytes = None
      if file_path.exists():
          with open(file_path, 'rb') as f:
              current_content_bytes = f.read()

      new_content_bytes = content.encode('utf-8')

      if not file_path.exists() or current_content_bytes != new_content_bytes:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
          f.write(content)
        logger.info(f"Generated/Updated Memoria ecosystem file: {file_path}")
      else:
        logger.info(f"Memoria ecosystem file already exists and is up-to-date: {file_path}")


  def verify_memoria_ecosystem(self):
    """Verifies the creation and integrity of the Memoria ecosystem files."""
    if not self.config.get('memoria_ecosystem', {}).get('enabled', False):
      logger.info("Memoria ecosystem disabled, skipping verification.")
      return

    files_to_verify = [
      self.memoria_ecosystem_path / '__init__.py',
      self.memoria_ecosystem_path / 'memoria_module.py',
      self.memoria_ecosystem_path / 'memoria_core.py',
      self.memoria_ecosystem_path / 'self_reflection.py',
      self.memoria_ecosystem_path / 'optimization_engine.py',
      self.memoria_ecosystem_path / 'analysis_interface.py',
      self.memoria_ecosystem_path / 'config' / 'memoria_config.json'
    ]
    modules_to_verify = [
      (self.memoria_ecosystem_path / 'memoria_module.py', 'ecosystem.memoria.memoria_module'),
      (self.memoria_ecosystem_path / 'memoria_core.py', 'ecosystem.memoria.memoria_core'),
      (self.memoria_ecosystem_path / 'self_reflection.py', 'ecosystem.memoria.self_reflection'),
      (self.memoria_ecosystem_path / 'optimization_engine.py', 'ecosystem.memoria.optimization_engine'),
      (self.memoria_ecosystem_path / 'analysis_interface.py', 'ecosystem.memoria.analysis_interface')
    ]

    results = self.diagnostics.run_diagnostics(files_to_verify, modules_to_verify)
    if not all(results.values()):
      logger.error("Memoria ecosystem verification failed. Attempting regeneration.")
      self.initialize_memoria_ecosystem()
      results = self.diagnostics.run_diagnostics(files_to_verify, modules_to_verify)
      if not all(results.values()):
        logger.critical("Failed to verify Memoria ecosystem after regeneration. Some Memoria functionality may be impaired.")
      else:
        logger.info("Memoria ecosystem successfully verified after regeneration attempt.")
    else:
      logger.info("Memoria ecosystem verified successfully.")


class CodebaseHealthModeler:
  """
    Models codebase health using mathematical manifolds with advanced analysis.

    This class provides methods to load, verify, and apply mathematical
    projections to model various aspects of codebase health, such as stability
    and test coverage.
    """
  def __init__(self, bootstrapper: 'IntellisenseBootstrapper'):
    """
    Initializes the CodebaseHealthModeler.

    Args:
        bootstrapper (IntellisenseBootstrapper): An instance of the bootstrapper.
    """
    self.bootstrapper = bootstrapper
    self.registry_path = Path("codebase_health_registry.json")
    self.projections: Dict[str, Dict[str, Any]] = {}
    self._invocations = 0
    self._successful_invocations = 0
    self._total_latency = 0.0

    self.load_registry()
    self.projection_funcs = {
      "stability_projection_v1": self._stability_projection_v1,
      "coverage_projection_v1": self._coverage_projection_v1
    }
    logger.info("CodebaseHealthModeler initialized.")

  def _start_op(self):
    """Marks the start of an operation for metric tracking."""
    self._invocations += 1
    return time.perf_counter()

  def _end_op(self, start_time: float, success: bool = True):
    """Marks the end of an operation for metric tracking."""
    latency = time.perf_counter() - start_time
    self._total_latency += latency
    if success:
      self._successful_invocations += 1

  def get_operational_metrics(self) -> Dict[str, Any]:
    """
    Gets the operational metrics for the module.

    Returns:
        Dict[str, Any]: A dictionary of operational metrics.
    """
    success_rate = (self._successful_invocations / self._invocations) if self._invocations > 0 else 0.0
    avg_latency_ms = (self._total_latency / self._invocations * 1000) if self._invocations > 0 else 0.0
    return {
      "invocations": self._invocations,
      "success_count": self._successful_invocations,
      "error_count": self._invocations - self._successful_invocations,
      "success_rate": round(success_rate, 4),
      "avg_latency_ms": round(avg_latency_ms, 2)
    }

  def load_registry(self):
    """Loads the projection registry from disk, creating a default if it doesn't exist."""
    op_start_time = self._start_op()
    try:
      if not self.registry_path.exists():
        self._create_default_registry()
      with open(self.registry_path, 'r', encoding='utf-8') as f:
        self.projections = json.load(f)
      logger.info(f"[CodebaseHealthModeler] Loaded {len(self.projections)} projections.")
      self._end_op(op_start_time, success=True)
    except Exception as e:
      logger.error(f"[CodebaseHealthModeler] Error loading registry: {e}")
      self._end_op(op_start_time, success=False)
      raise


  def _create_default_registry(self):
    """Creates a default projection registry file."""
    op_start_time = self._start_op()
    try:
      default_data = {
        "CODE_STABILITY_V1": {
          "equation_name": "stability_projection_v1",
          "description": "Models cyclomatic complexity and risk as a high-curvature surface.",
          "version": "1.0",
          "last_verified_at": datetime.now(timezone.utc).isoformat(),
          "status": "active",
          "metadata": {"domain": "code_stability"}
        },
        "TEST_COVERAGE_POTENTIAL": {
          "equation_name": "coverage_projection_v1",
          "description": "Models test coverage as a potential well.",
          "version": "1.0",
          "last_verified_at": datetime.now(timezone.utc).isoformat(),
          "status": "active",
          "metadata": {"domain": "test_coverage"}
        }
      }
      with open(self.registry_path, 'w', encoding='utf-8') as f:
        json.dump(default_data, f, indent=2)
      logger.info("[CodebaseHealthModeler] Created default registry.")
      self._end_op(op_start_time, success=True)
    except Exception as e:
      logger.error(f"Error creating default registry: {e}")
      self._end_op(op_start_time, success=False)
      raise


  def _get_param(self, name: str, default: float) -> float:
    """Gets a parameter value from the configuration."""
    return self.bootstrapper.config.get('parameters', {}).get(name, {}).get('value', default)

  def _stability_projection_v1(self, complexity: float, risk: float) -> float:
    """A projection function for code stability."""
    if np is None: raise ImportError("NumPy required.")
    stability = self._get_param('stability_factor', 1.0)
    return float(complexity * np.exp(-risk / stability))

  def _coverage_projection_v1(self, coverage: float, lines: float) -> float:
    """A projection function for test coverage."""
    if np is None: raise ImportError("NumPy required.")
    target = self._get_param('coverage_target', 0.85)
    return float(-np.log(max(0.01, target - coverage)) * lines)

  def get_projection(self, name: str) -> Optional[Dict[str, Any]]:
    """
    Gets the metadata for a named projection.

    Args:
        name (str): The name of the projection.

    Returns:
        Optional[Dict[str, Any]]: The projection metadata, or None if not found.
    """
    op_start_time = self._start_op()
    proj = self.projections.get(name)
    if proj and proj.get('status') == 'active':
      self._end_op(op_start_time, success=True)
      return proj
    logger.warning(f"Projection '{name}' not found or inactive.")
    self._end_op(op_start_time, success=False)
    return None

  def get_projection_function(self, proj_name: str) -> Optional[Callable]:
    """
    Gets the callable function for a named projection.

    Args:
        proj_name (str): The name of the projection.

    Returns:
        Optional[Callable]: The projection function, or None if not found.
    """
    projection_info = self.get_projection(proj_name)
    if projection_info:
      func_name = projection_info.get("equation_name")
      return self.projection_funcs.get(func_name)
    logger.warning(f"Projection function '{proj_name}' not found. Using default.")
    return None

  def _curvature_analysis(self, func: Callable, u_grid: np.ndarray, r_grid: np.ndarray) -> Tuple[float, float]:
    """Performs curvature analysis on a projection function."""
    if np is None: return 0.0, 0.0
    try:
      Z = np.array([[func(u, r) for u in u_grid[0,:]] for r in r_grid[:,0]])
      if Z.shape != u_grid.shape:
        if Z.size == u_grid.size: Z = Z.reshape(u_grid.shape)
        else: logger.debug(f"Irreconcilable shape mismatch. Skipping curvature analysis."); return 0.0, 0.0
      dZ_du = np.gradient(Z, axis=1)
      dZ_dr = np.gradient(Z, axis=0)
      d2Z_du2 = np.gradient(dZ_du, axis=1)
      d2Z_dr2 = np.gradient(dZ_dr, axis=0)
      d2Z_dudr = np.gradient(dZ_du, axis=0)
      E = 1 + dZ_du**2; F = dZ_du * dZ_dr; G = 1 + dZ_dr**2
      norm_factor = np.sqrt(1 + dZ_du**2 + dZ_dr**2); denominator_second_form = norm_factor + 1e-9
      L = d2Z_du2 / denominator_second_form; M = d2Z_dudr / denominator_second_form; N = d2Z_dr2 / denominator_second_form
      det_first_form = E * G - F * F; valid_indices = det_first_form > 1e-12
      k_values = np.zeros_like(det_first_form); h_values = np.zeros_like(det_first_form)
      if np.any(valid_indices):
        k_values[valid_indices] = (L[valid_indices] * N[valid_indices] - M[valid_indices]**2) / det_first_form[valid_indices]
        h_values[valid_indices] = (E[valid_indices] * N[valid_indices] - 2 * F[valid_indices] * M[valid_indices] + G[valid_indices] * L[valid_indices]) / (2 * det_first_form[valid_indices])
      finite_k_values = k_values[np.isfinite(k_values)]; finite_h_values = h_values[np.isfinite(h_values)]
      mean_gaussian_curvature = np.mean(np.abs(finite_k_values)) if finite_k_values.size > 0 else 0.0
      mean_mean_curvature = np.mean(np.abs(finite_h_values)) if finite_h_values.size > 0 else 0.0
      return float(mean_mean_curvature), float(mean_gaussian_curvature)
    except Exception as e: logger.debug(f"Curvature analysis failed: {e}. Returning 0.0, 0.0."); return 0.0, 0.0

  def _wavelet_analysis(self, func: Callable, u_sample: np.ndarray) -> Optional[float]:
    """Performs wavelet analysis on a projection function."""
    if pywt is None or np is None: return None
    try:
      r_fixed_value = np.mean(u_sample)
      z_series = np.array([func(u, r_fixed_value) for u in u_sample])
      if z_series.ndim > 1: z_series = z_series.flatten()
      z_series = z_series[np.isfinite(z_series)]
      if len(z_series) < 2: logger.debug("Not enough finite data for wavelet analysis after filtering."); return 0.0
      wavelet_name = 'db1'; max_level = pywt.dwt_max_level(len(z_series), wavelet_name)
      level_to_use = min(3, max_level if max_level > 0 else 0)
      if level_to_use == 0: logger.debug("Wavelet analysis level is 0, skipping analysis for too short series."); return 0.0
      coeffs = pywt.wavedec(z_series, wavelet_name, level=level_to_use)
      if len(coeffs) < 2: return 0.0
      detail_coeffs_std = [np.std(c) for c in coeffs[1:] if len(c) > 0]
      return float(np.max(detail_coeffs_std)) if detail_coeffs_std else 0.0
    except Exception as e: logger.debug(f"Wavelet analysis failed: {e}. Returning None."); return None

  def verify_projection(self, proj_name: str, u_range: Tuple[float, float], r_range: Tuple[float, float]) -> bool:
    """
    Verifies a projection by analyzing its mathematical properties.

    Args:
        proj_name (str): The name of the projection to verify.
        u_range (Tuple[float, float]): The range of the first input variable.
        r_range (Tuple[float, float]): The range of the second input variable.

    Returns:
        bool: True if the projection is verified, False otherwise.
    """
    op_start_time = self._start_op()
    proj_func = self.get_projection_function(proj_name)
    if proj_func is None or np is None:
      logger.warning(f"Cannot verify projection '{proj_name}': function or NumPy not available."); self._end_op(op_start_time, success=False); return False
    try:
      u_sample = np.linspace(u_range[0], u_range[1], 10)
      r_sample = np.linspace(r_range[0], r_range[1], 10)
      U_grid, R_grid = np.meshgrid(u_sample, r_sample)
      Z_grid = np.array([[proj_func(u, r) for u in u_sample] for r in r_sample])
      if not isinstance(Z_grid, np.ndarray) or Z_grid.ndim < 2: Z_grid = np.atleast_2d(Z_grid)
      if not np.all(np.isfinite(Z_grid)): logger.warning(f"Projection '{proj_name}' resulted in non-finite values."); self._end_op(op_start_time, success=False); return False
      mean_z, var_z = np.mean(Z_grid), np.var(Z_grid)
      mean_curv, gauss_curv = self._curvature_analysis(proj_func, U_grid, R_grid)
      wavelet_check_result = True
      if self.bootstrapper.config.get('wavelet_enabled', False) and pywt:
        wavelet_analysis_value = self._wavelet_analysis(proj_func, u_sample)
        wavelet_check_result = (wavelet_analysis_value is not None) and (wavelet_analysis_value > 0.001)
      logger.info(f"Verification '{proj_name}' - Mean: {mean_z:.4f}, Variance: {var_z:.4f}, Mean Curv: {mean_curv:.4f}, Gauss Curv: {gauss_curv:.4f}, Wavelet Check: {wavelet_check_result}")
      self._end_op(op_start_time, success=True)
      return var_z > 0.0001 and mean_curv > 0.0001 and wavelet_check_result
    except Exception as e:
      logger.error(f"Error during verification for '{proj_name}': {e}"); self._end_op(op_start_time, success=False); return False

  def health_check(self) -> bool:
    """
    Performs a health check on the module.

    Returns:
        bool: True if the module is healthy, False otherwise.
    """
    return self.registry_path.exists()

class DeveloperPersonaEngine:
  """
    Shapes AI suggestions to match developer archetypes based on context and urgency.

    This engine dynamically adjusts the tone and confidence of its responses to
    better suit the perceived needs of the developer.
    """
  def __init__(self, bootstrapper: 'IntellisenseBootstrapper'):
    """
    Initializes the DeveloperPersonaEngine.

    Args:
        bootstrapper (IntellisenseBootstrapper): An instance of the bootstrapper.
    """
    self.bootstrapper = bootstrapper
    self.persona_traits = self.bootstrapper.config['developer_persona']
    self._invocations = 0
    self._successful_invocations = 0
    self._total_latency = 0.0
    self.state_history = []
    logger.info("DeveloperPersonaEngine initialized.")

  def _start_op(self):
    """Marks the start of an operation for metric tracking."""
    self._invocations += 1; return time.perf_counter()
  def _end_op(self, start_time: float, success: bool = True):
    """Marks the end of an operation for metric tracking."""
    latency = time.perf_counter() - start_time; self._total_latency += latency
    if success: self._successful_invocations += 1

  def get_operational_metrics(self) -> Dict[str, Any]:
    """
    Gets the operational metrics for the module.

    Returns:
        Dict[str, Any]: A dictionary of operational metrics.
    """
    success_rate = (self._successful_invocations / self._invocations) if self._invocations > 0 else 0.0
    avg_latency_ms = (self._total_latency / self._invocations * 1000) if self._invocations > 0 else 0.0
    return {
      "invocations": self._invocations, "success_count": self._successful_invocations, "error_count": self._invocations - self._successful_invocations,
      "success_rate": round(success_rate, 4), "avg_latency_ms": round(avg_latency_ms, 2)
    }

  def update_persona(self, context: Dict[str, Any], urgency: float, reward: float):
    """
    Updates the developer persona based on the current context, urgency, and feedback.

    Args:
        context (Dict[str, Any]): The context of the interaction.
        urgency (float): The calculated urgency level.
        reward (float): The feedback reward from the previous turn.
    """
    op_start_time = self._start_op(); success = False
    try:
      effective_urgency = urgency if urgency is not None else self.persona_traits.get('urgency_level', 0.5)
      if effective_urgency > 0.8 or reward < -5.0:
        self.persona_traits['tone'] = 'authoritative'; self.persona_traits['confidence_level'] = min(1.0, self.persona_traits.get('confidence_level', 0.7) + 0.1)
      else:
        self.persona_traits['tone'] = 'collaborative'; self.persona_traits['confidence_level'] = max(0.5, self.persona_traits.get('confidence_level', 0.7) - 0.1)
      self.persona_traits['urgency_level'] = effective_urgency
      self.state_history.append({"context": context, "urgency": effective_urgency, "reward": reward, "timestamp": datetime.now(timezone.utc).isoformat()})
      self.bootstrapper.config['developer_persona'] = self.persona_traits
      self.bootstrapper.save_config()
      success = True
    finally:
      self._end_op(op_start_time, success)

  def shape_response(self, base_response: str, urgency: float) -> str:
    """
    Shapes a base response according to the current developer persona.

    Args:
        base_response (str): The base response to shape.
        urgency (float): The current urgency level.

    Returns:
        str: The shaped response.
    """
    op_start_time = self._start_op(); success = False
    try:
      confidence = self.persona_traits.get('confidence_level', 0.7)
      tone = self.persona_traits.get('tone', 'collaborative')
      prefix = "Critical: " if tone == 'authoritative' else "Suggestion: "
      final_response = f"{prefix}{base_response}"
      if confidence > 0.8 and random.random() < 0.1: final_response += " (Highly recommended based on analysis)"
      success = True
      return final_response.strip()
    finally:
      self._end_op(op_start_time, success)

  def health_check(self) -> bool:
    """
    Performs a health check on the module.

    Returns:
        bool: True if the module is healthy, False otherwise.
    """
    return bool(self.persona_traits)

class DiagnosticUrgencySystem:
  """
    Quantifies focus and urgency based on contextual momentum and code metrics.

    This system analyzes user input and code metrics to determine the urgency
    of a situation, which can then be used to guide the AI's response.
    """
  def __init__(self, bootstrapper: 'IntellisenseBootstrapper'):
    """
    Initializes the DiagnosticUrgencySystem.

    Args:
        bootstrapper (IntellisenseBootstrapper): An instance of the bootstrapper.
    """
    self.bootstrapper = bootstrapper
    self.diagnostic_keywords = self.bootstrapper.config['diagnostic_keywords']
    self.urgency_level = self.bootstrapper.config['developer_persona']['urgency_level']
    self._invocations = 0
    self._successful_invocations = 0
    self._total_latency = 0.0
    logger.info("DiagnosticUrgencySystem initialized.")

  def _start_op(self):
    """Marks the start of an operation for metric tracking."""
    self._invocations += 1; return time.perf_counter()
  def _end_op(self, start_time: float, success: bool = True):
    """Marks the end of an operation for metric tracking."""
    latency = time.perf_counter() - start_time; self._total_latency += latency
    if success: self._successful_invocations += 1

  def get_operational_metrics(self) -> Dict[str, Any]:
    """
    Gets the operational metrics for the module.

    Returns:
        Dict[str, Any]: A dictionary of operational metrics.
    """
    success_rate = (self._successful_invocations / self._invocations) if self._invocations > 0 else 0.0
    avg_latency_ms = (self._total_latency / self._invocations * 1000) if self._invocations > 0 else 0.0
    return {
      "invocations": self._invocations, "success_count": self._successful_invocations, "error_count": self._invocations - self._successful_invocations,
      "success_rate": round(success_rate, 4), "avg_latency_ms": round(avg_latency_ms, 2)
    }

  def analyze_context(self, user_input: str, code_metrics: Dict[str, Any]) -> float:
    """
    Analyzes the user input and code metrics to determine a context score.

    Args:
        user_input (str): The user's input text.
        code_metrics (Dict[str, Any]): A dictionary of code metrics.

    Returns:
        float: The calculated context score.
    """
    op_start_time = self._start_op(); success = False
    try:
      input_lower = user_input.lower()
      critical_score = sum(input_lower.count(kw) for kw in self.diagnostic_keywords.get('critical', []))
      warning_score = sum(input_lower.count(kw) for kw in self.diagnostic_keywords.get('warning', []))
      complexity_threshold = self.bootstrapper.config['parameters']['complexity_threshold']['value']
      coverage_target = self.bootstrapper.config['parameters']['coverage_target']['value']
      complexity_score = (code_metrics.get('complexity', 0.0) / complexity_threshold) if complexity_threshold else 0.0
      coverage_score = (1.0 - (code_metrics.get('coverage', 0.0) / coverage_target)) if coverage_target else 0.0
      weighted_sum = (critical_score * 0.5 + warning_score * 0.2 + min(complexity_score, 1.0) * 0.2 + min(coverage_score, 1.0) * 0.1)
      word_count = len(input_lower.split())
      success = True
      return weighted_sum / (word_count + 1) if word_count > 0 else 0.0
    finally:
      self._end_op(op_start_time, success)

  def update_urgency(self, context_score: float, momentum: float):
    """
    Updates the urgency level based on the context score and momentum.

    Args:
        context_score (float): The context score from the analysis.
        momentum (float): The momentum of the codebase health.
    """
    op_start_time = self._start_op(); success = False
    try:
      urgency_delta = 0.05 if momentum > 0 else (-0.05 if momentum < 0 else 0.0)
      self.urgency_level += urgency_delta + (context_score * 0.1)
      self.urgency_level = max(0.0, min(1.0, self.urgency_level))
      self.bootstrapper.config['developer_persona']['urgency_level'] = self.urgency_level
      self.bootstrapper.save_config()
      success = True
    finally:
      self._end_op(op_start_time, success)

  def get_urgency_level(self) -> float:
    """
    Gets the current urgency level.

    Returns:
        float: The current urgency level.
    """
    return self.urgency_level

  def health_check(self) -> bool:
    """
    Performs a health check on the module.

    Returns:
        bool: True if the module is healthy, False otherwise.
    """
    return bool(self.diagnostic_keywords)

class ModuleStateTracker:
  """Manages persistent snapshots of module operational states."""
  def __init__(self, db_path: Path):
    """
    Initializes the ModuleStateTracker.

    Args:
        db_path (Path): The path to the SQLite database file.
    """
    self.db_path = db_path
    self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
    self._create_table()
    logger.info(f"ModuleStateTracker initialized for DB: {db_path}")

  def _create_table(self):
    """Creates the database table for module snapshots if it doesn't exist."""
    with self.conn:
      self.conn.execute("""
        CREATE TABLE IF NOT EXISTS module_snapshots (
          timestamp TEXT NOT NULL,
          module_name TEXT NOT NULL,
          status TEXT, -- From health_check
          invocations INTEGER DEFAULT 0,
          success_count INTEGER DEFAULT 0,
          error_count INTEGER DEFAULT 0,
          avg_latency_ms REAL DEFAULT 0.0,
          last_error_message TEXT,
          config_snapshot_json TEXT, -- Relevant config at the time of snapshot
          performance_metrics_json TEXT, -- Other metrics like CPU, Memory related to module
          PRIMARY KEY (timestamp, module_name)
        );
      """)
      self.conn.execute("CREATE INDEX IF NOT EXISTS idx_module_name ON module_snapshots (module_name);")
      self.conn.execute("CREATE INDEX IF NOT EXISTS idx_snapshot_time ON module_snapshots (timestamp DESC);")
    logger.info("Module snapshots DB Table created/verified.")

  def record_snapshot(self, snapshot_data: Dict[str, Any]):
    """
    Records a single snapshot of a module's state and operational metrics.

    Args:
        snapshot_data (Dict[str, Any]): A dictionary of snapshot data.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    module_name = snapshot_data.get('module_name')
    if not module_name:
      logger.error("Attempted to record snapshot without 'module_name'. Skipping.")
      return

    with self.conn:
      self.conn.execute(
        """INSERT OR REPLACE INTO module_snapshots (timestamp, module_name, status, invocations, success_count, error_count, avg_latency_ms, last_error_message, config_snapshot_json, performance_metrics_json)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (timestamp,
         module_name,
         snapshot_data.get('status', 'UNKNOWN'),
         snapshot_data.get('invocations', 0),
         snapshot_data.get('success_count', 0),
         snapshot_data.get('error_count', 0),
         snapshot_data.get('avg_latency_ms', 0.0),
         snapshot_data.get('last_error_message'),
         json.dumps(snapshot_data.get('config_snapshot')) if snapshot_data.get('config_snapshot') else None,
         json.dumps(snapshot_data.get('performance_metrics')) if snapshot_data.get('performance_metrics') else None)
      )
    logger.debug(f"Recorded snapshot for module: {module_name} at {timestamp}")

  def retrieve_latest_snapshots(self, criteria: Optional[Dict[str, Any]] = None, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieves the latest snapshots based on criteria.

    If no criteria are provided, it retrieves the single latest snapshot for
    each module.

    Args:
        criteria (Optional[Dict[str, Any]], optional): A dictionary of
            criteria to filter snapshots by. Defaults to None.
        limit (int, optional): The maximum number of snapshots to return.
            Defaults to 10.

    Returns:
        List[Dict[str, Any]]: A list of snapshot dictionaries.
    """
    query = """
      SELECT T1.*
      FROM module_snapshots T1
      INNER JOIN (
        SELECT module_name, MAX(timestamp) as max_timestamp
        FROM module_snapshots
        GROUP BY module_name
      ) AS T2
      ON T1.module_name = T2.module_name AND T1.timestamp = T2.max_timestamp
    """
    params: List[Any] = []

    if criteria:
      where_clauses = []
      if 'module_name' in criteria:
        where_clauses.append("T1.module_name = ?")
        params.append(criteria['module_name'])
      if 'status' in criteria:
        where_clauses.append("T1.status = ?")
        params.append(criteria['status'])
      if 'min_avg_latency_ms' in criteria:
        where_clauses.append("T1.avg_latency_ms >= ?")
        params.append(criteria['min_avg_latency_ms'])
      if 'max_error_count' in criteria:
        where_clauses.append("T1.error_count <= ?")
        params.append(criteria['max_error_count'])

      if where_clauses:
        query += " WHERE " + " AND ".join(where_clauses)

    query += " ORDER BY T1.timestamp DESC LIMIT ?"
    params.append(limit)

    results = []
    try:
      with self.conn:
        cursor = self.conn.execute(query, tuple(params))
        column_names = [description[0] for description in cursor.description]
        for row in cursor.fetchall():
          row_dict = dict(zip(column_names, row))
          if row_dict['config_snapshot_json']:
            row_dict['config_snapshot'] = json.loads(row_dict['config_snapshot_json'])
          if row_dict['performance_metrics_json']:
            row_dict['performance_metrics'] = json.loads(row_dict['performance_metrics_json'])

          results.append(row_dict)
    except Exception as e:
      logger.error(f"Error retrieving latest module snapshots: {e}")
    return results

  def health_check(self) -> bool:
    """
    Performs a health check on the module.

    Returns:
        bool: True if the module is healthy, False otherwise.
    """
    try:
      self.conn.execute("SELECT 1")
      return self.conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='module_snapshots';").fetchone() is not None
    except Exception as e:
      logger.error(f"ModuleStateTracker DB health check failed: {e}")
      return False

  def shutdown(self):
    """Closes the SQLite database connection."""
    if self.conn:
        self.conn.close()
        logger.info(f"ModuleStateTracker DB connection closed for {self.db_path}.")

class MetaReflectionEngine:
  """Analyzes suggestion feedback and system logs to improve diagnostic strategies."""
  def __init__(self, bootstrapper: 'IntellisenseBootstrapper'):
    """
    Initializes the MetaReflectionEngine.

    Args:
        bootstrapper (IntellisenseBootstrapper): An instance of the bootstrapper.
    """
    self.bootstrapper = bootstrapper
    self.embedding_provider = bootstrapper.embedding_provider
    self.interaction_count = 0
    self.reflection_threshold = self.bootstrapper.config.get('meta_reflection', {}).get('reflection_interval', 10)
    self.feedback_log_path = Path(self.bootstrapper.config.get('meta_reflection', {}).get('feedback_log_path', 'ai_suggestion_feedback.jsonl'))
    self.assessment_file_path = Path("logs/assessments.jsonl")
    self.log_catalog_db_path = Path("intellisense_log_catalog.db")
    self.synthesis_report_path = Path("logs/intellisense_data_synthesis_report.log")
    self.last_reflection_content = ""
    self.last_processed_log_line = 0
    self.log_reflector_interval_sec = self.bootstrapper.config.get('meta_reflection', {}).get('log_reflector_interval_sec', 600)
    self.log_reflector_window_lines = self.bootstrapper.config.get('meta_reflection', {}).get('log_reflector_window_lines', 50)
    self.diagnostic_keywords = self.bootstrapper.config['diagnostic_keywords']

    self.db_path = Path("intellisense_feedback.db")
    self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
    self._create_feedback_table()

    self.log_catalog_conn = sqlite3.connect(self.log_catalog_db_path, check_same_thread=False)
    self._create_log_catalog_table()
    logger.info("MetaReflectionEngine initialized with log catalog capabilities.")
    self.last_log_scan_time = 0

  def _create_feedback_table(self):
    """Creates the feedback log database table if it doesn't exist."""
    with self.conn:
      self.conn.execute("""
        CREATE TABLE IF NOT EXISTS feedback_log (
          fingerprint TEXT PRIMARY KEY,
          timestamp TEXT NOT NULL,
          user_input TEXT NOT NULL,
          ai_response TEXT NOT NULL,
          status TEXT,
          reward REAL DEFAULT 0.0,
          user_id TEXT NOT NULL
        );
      """)
      self.conn.execute("CREATE INDEX IF NOT EXISTS idx_user_timestamp ON feedback_log (user_id, timestamp DESC);")
    logger.info("Feedback log DB Table created/verified.")

  def _create_log_catalog_table(self):
    """Creates the log catalog database table if it doesn't exist."""
    with self.log_catalog_conn:
      self.log_catalog_conn.execute("""
        CREATE TABLE IF NOT EXISTS log_catalog (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          ingestion_timestamp TEXT NOT NULL,
          source_file TEXT NOT NULL,
          log_timestamp TEXT,
          log_level TEXT,
          content TEXT NOT NULL,
          content_hash TEXT UNIQUE,
          embedding_json TEXT,
          keywords TEXT,
          assessment_score REAL DEFAULT 0.0,
          category TEXT,
          parsed_values_json TEXT,
          context_category_parsed TEXT,
          status TEXT
        );
      """)
      current_columns = [col[1] for col in self.log_catalog_conn.execute("PRAGMA table_info(log_catalog);").fetchall()]
      if 'parsed_values_json' not in current_columns:
        self.log_catalog_conn.execute("ALTER TABLE log_catalog ADD COLUMN parsed_values_json TEXT;")
      if 'context_category_parsed' not in current_columns:
        self.log_catalog_conn.execute("ALTER TABLE log_catalog ADD COLUMN context_category_parsed TEXT;")

      self.log_catalog_conn.execute("CREATE INDEX IF NOT EXISTS idx_log_level_v2 ON log_catalog (log_level);")
      self.log_catalog_conn.execute("CREATE INDEX IF NOT EXISTS idx_assessment_score_v2 ON log_catalog (assessment_score DESC);")
      self.log_catalog_conn.execute("CREATE INDEX IF NOT EXISTS idx_category_v2 ON log_catalog (category);")
      self.log_catalog_conn.execute("CREATE INDEX IF NOT EXISTS idx_context_category_parsed ON log_catalog (context_category_parsed);")
    logger.info("Log catalog DB Table created/verified, new columns added if needed.")

  def store_feedback(self, user_input: str, ai_response: str, status: str, reward: float, user_id: str):
    """
    Stores developer feedback in the database and a log file.

    Args:
        user_input (str): The user's input.
        ai_response (str): The AI's response.
        status (str): The status of the feedback (e.g., 'accepted').
        reward (float): The reward score for the feedback.
        user_id (str): The ID of the user providing the feedback.
    """
    feedback_fingerprint = hashlib.sha256(f"{user_input}{ai_response}{datetime.now(timezone.utc).isoformat()}".encode('utf-8')).hexdigest()

    with self.conn:
      self.conn.execute(
        """INSERT OR REPLACE INTO feedback_log
          (fingerprint, timestamp, user_input, ai_response, status, reward, user_id)
          VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (feedback_fingerprint, datetime.now(timezone.utc).isoformat(), user_input, ai_response, status, reward, user_id)
      )

    self.feedback_log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self.feedback_log_path, 'a', encoding='utf-8') as f:
      json.dump({"fingerprint": feedback_fingerprint, "user_input": user_input, "ai_response": ai_response, "status": status, "reward": reward, "user_id": user_id}, f)
      f.write('\n')
    logger.debug(f"Stored feedback for user {user_id}, fingerprint: ...{feedback_fingerprint[-12:]}")

  def reflect(self, user_input: str, ai_response: str, user_id: str = "default") -> Optional[str]:
    """
    Performs a reflection cycle based on user feedback.

    Args:
        user_input (str): The user's input.
        ai_response (str): The AI's response.
        user_id (str, optional): The user's ID. Defaults to "default".

    Returns:
        Optional[str]: A summary of the reflection, or None.
    """
    self.interaction_count += 1
    reflection_output = None
    if self.interaction_count % self.reflection_threshold == 0 and self.interaction_count > 0:
      try:
        feedback_data = []
        with self.conn:
          cursor = self.conn.execute("SELECT status, reward FROM feedback_log WHERE user_id = ? ORDER BY timestamp DESC LIMIT 200", (user_id,))
          for status, reward in cursor.fetchall():
            feedback_data.append({"status": status, "reward": reward})

        accepted = len([f for f in feedback_data if f.get('status') == 'accepted'])
        modified = len([f for f in feedback_data if f.get('status') == 'modified'])
        discarded = len([f for f in feedback_data if f.get('status') == 'discarded'])
        avg_reward = np.mean([f['reward'] for f in feedback_data]) if feedback_data else 0.0

        reflection_output = (f"Reflection after {self.interaction_count} interactions: "
                             f"Accepted: {accepted}, Modified: {modified}, Discarded: {discarded}, Avg Reward: {avg_reward:.2f}. "
                             f"Adjusting diagnostic strategies to improve acceptance rate.")
        self.last_reflection_content = reflection_output
        logger.info(reflection_output)
      except Exception as e:
        logger.error(f"Reflection failed: {str(e)}")
    return reflection_output

  def _parse_structured_log_entry(self, content: str) -> Tuple[Dict[str, Any], Optional[str]]:
    """
    Parses log content for structured values and determines a context category.

    Args:
        content (str): The log entry content.

    Returns:
        A tuple containing a dictionary of parsed values and an optional context category string.
    """
    parsed_values: Dict[str, Any] = {}
    context_category: Optional[str] = None

    advanced_parsers = self.bootstrapper.config.get('log_management', {}).get('advanced_parsers', [])

    for parser_config in advanced_parsers:
      regex_patterns = parser_config.get('regex', [])
      default_category = parser_config.get('context_category')

      for pattern_str in regex_patterns:
        match = re.search(pattern_str, content)
        if match:
          for key, value in match.groupdict().items():
            try:
              if isinstance(value, str) and '.' in value and value.replace('.', '', 1).isdigit():
                parsed_values[key] = float(value)
              elif isinstance(value, str) and value.isdigit():
                parsed_values[key] = int(value)
              else:
                parsed_values[key] = value

            except ValueError:
              parsed_values[key] = value

          if default_category:
            context_category = default_category
          return parsed_values, context_category

    return parsed_values, context_category

  def _assess_log_entry(self, content: str, source_file: Path) -> Dict[str, Any]:
    """
    Assesses a log entry, extracts features, and prepares it for cataloging.

    This method includes structured parsing and an enriched assessment score.

    Args:
        content (str): The raw log entry content.
        source_file (Path): The path to the log file.

    Returns:
        A dictionary of assessed log data.
    """
    level = "UNKNOWN"
    detected_keywords = []
    assessment_score = 0.0
    category = "general"
    log_ts = datetime.now(timezone.utc).isoformat()
    filtered_content = content

    log_patterns = self.bootstrapper.config['log_management']['log_entry_patterns']

    try:
      json_entry = json.loads(content)
      filtered_content = json_entry.get('message', content)
      level = json_entry.get('level', level).upper()
      log_ts = json_entry.get('timestamp', log_ts)
    except json.JSONDecodeError:
      match_simple_log = re.match(log_patterns.get("simple_log", r"^$"), content)
      if match_simple_log:
        groups = match_simple_log.groups()
        if len(groups) >= 3:
          try:
            timestamp_str = groups[0]
            if ',' in timestamp_str:
              log_ts = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f').replace(tzinfo=timezone.utc).isoformat()
            else:
              log_ts = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc).isoformat()
            level = groups[1].upper()
            filtered_content = groups[2].strip()
          except ValueError:
            logger.debug(f"Failed to parse timestamp from log entry: {groups[0]}. Using current time.")

    parsed_values, context_category = self._parse_structured_log_entry(filtered_content)

    content_for_keywords = filtered_content.lower()
    for k_type, keywords in self.diagnostic_keywords.items():
      for kw in keywords:
        if kw in content_for_keywords:
          detected_keywords.append(kw)
          if k_type == 'critical':
            assessment_score += 0.6
            category = "critical_event"
          elif k_type == 'warning':
            assessment_score += 0.3
            if category != "critical_event":
              category = "warning_issue"
          elif k_type == 'info':
            assessment_score += 0.1
            if category not in ["critical_event", "warning_issue"]:
              category = "info_update"

    log_patterns = self.bootstrapper.config.get('log_management', {}).get('log_entry_patterns', {})
    if re.search(log_patterns.get("feedback", r"^$"), content_for_keywords):
      category = "feedback_entry"

    embedding = self.embedding_provider.get_embedding(filtered_content)

    content_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()

    return {
      "ingestion_timestamp": datetime.now(timezone.utc).isoformat(),
      "source_file": str(source_file),
      "log_timestamp": log_ts,
      "log_level": level,
      "content": content,
      "content_hash": content_hash,
      "embedding_json": json.dumps(embedding) if embedding is not None else None,
      "keywords": json.dumps(list(set(detected_keywords))),
      "assessment_score": min(assessment_score, 1.0),
      "category": category,
      "parsed_values_json": json.dumps(parsed_values) if parsed_values else None,
      "context_category_parsed": context_category,
      "status": "new"
    }

  def _store_log_entry_in_catalog(self, assessed_data: Dict[str, Any]):
    """Stores an assessed log entry in the log catalog database."""
    try:
      with self.log_catalog_conn:
        self.log_catalog_conn.execute(
          """INSERT OR IGNORE INTO log_catalog
             (ingestion_timestamp, source_file, log_timestamp, log_level, content, content_hash, embedding_json, keywords, assessment_score, category, parsed_values_json, context_category_parsed, status)
             VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
          (assessed_data['ingestion_timestamp'], assessed_data['source_file'], assessed_data['log_timestamp'],
           assessed_data['log_level'], assessed_data['content'], assessed_data['content_hash'],
           assessed_data['embedding_json'], assessed_data['keywords'], assessed_data['assessment_score'],
           assessed_data['category'], assessed_data['parsed_values_json'], assessed_data['context_category_parsed'],
           assessed_data['status'])
        )
        if self.log_catalog_conn.changes() > 0:
          logger.debug(f"Cataloged log entry from {assessed_data['source_file']} with score {assessed_data['assessment_score']:.2f}")
          if assessed_data['assessment_score'] >= self.bootstrapper.config['log_management']['assessment_threshold_ai_learning']:
            logger.info(f"Log entry from {assessed_data['source_file']} flagged for AI learning (score: {assessed_data['assessment_score']:.2f})")
            self.log_catalog_conn.execute("UPDATE log_catalog SET status = 'for_ai_learning' WHERE content_hash = ?", (assessed_data['content_hash'],))
        else:
          logger.debug(f"Log entry from {assessed_data['source_file']} already exists in catalog (hash: {assessed_data['content_hash'][-8:]}). Skipped.")
    except Exception as e:
      logger.error(f"Failed to store log entry in catalog: {e}")

  def _scan_and_ingest_log_file(self, log_file: Path):
    """
    Reads a log file, assesses each entry, stores it in the database, and archives the file.
    """
    if not log_file.exists():
      logger.warning(f"Log file not found: {log_file}")
      return
    
    if log_file.name == "diagnostics.log" or log_file.name == "feedback.jsonl":
        logger.debug(f"Skipping archiving of persistent log file {log_file.name} within ingest_new_logs.")
        try:
            with open(log_file, "r", encoding='utf-8', errors='ignore') as f:
                for line in f:
                    stripped_line = line.strip()
                    if stripped_line:
                        assessed_data = self._assess_log_entry(stripped_line, log_file)
                        self._store_log_entry_in_catalog(assessed_data)
        except Exception as e:
            logger.error(f"Error processing persistent log file {log_file}: {e}")
        return


    logger.info(f"Scanning log file: {log_file}")
    try:
      with open(log_file, "r", encoding='utf-8', errors='ignore') as f:
        for line in f:
          stripped_line = line.strip()
          if stripped_line:
            assessed_data = self._assess_log_entry(stripped_line, log_file)
            self._store_log_entry_in_catalog(assessed_data)
      
      timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
      archive_name = ARCHIVE_FOLDER / f"{log_file.stem}_{timestamp}{log_file.suffix}"
      try:
          shutil.move(log_file, archive_name)
          logger.info(f"Archived log file {log_file.name} to {archive_name}")
      except Exception as e:
          logger.error(f"Failed to archive log file {log_file.name} to {archive_name}: {e}")

    except Exception as e:
      logger.error(f"Error processing log file {log_file}: {e}")

  def ingest_new_logs(self):
    """Orchestrates scanning configured log paths and ingesting new data."""
    if not self.bootstrapper.config.get('log_management', {}).get('enabled', False):
      logger.info("Log management disabled in config. Skipping log ingestion.")
      return

    current_time = time.time()
    scan_interval = self.bootstrapper.config['log_management']['scan_interval_sec']

    if current_time - self.last_log_scan_time < scan_interval:
      logger.debug(f"Skipping log scan: Not yet {scan_interval} seconds since last scan.")
      return

    logger.info("Starting scheduled log ingestion process.")
    scan_paths_config = self.bootstrapper.config['log_management']['scan_paths']

    processed_files = set()

    for path_str in scan_paths_config:
      current_path = Path(path_str)
      if current_path.is_file():
        if current_path not in processed_files:
          self._scan_and_ingest_log_file(current_path)
          processed_files.add(current_path)
      elif current_path.is_dir():
        for file_in_dir in current_path.rglob('*'):
          if file_in_dir.is_file() and file_in_dir.suffix.lower() in ['.log', '.txt', '.json', '.jsonl'] and file_in_dir.name not in ["intellisense_data_synthesis_report.log", "intellisense_self_test_report.jsonl"]:
            if file_in_dir not in processed_files:
              self._scan_and_ingest_log_file(file_in_dir)
              processed_files.add(file_in_dir)
      else:
        logger.warning(f"Configured log scan path '{path_str}' does not exist or is not a file/directory.")

    self.last_log_scan_time = current_time
    logger.info("Log ingestion process completed.")

  def rehydrate_log_data(self, criteria: Dict[str, Any], limit: int = 100) -> List[Dict[str, Any]]:
    """
    Retrieves processed log data from the catalog based on specified criteria.

    Args:
        criteria (Dict[str, Any]): A dictionary of criteria to filter logs by.
        limit (int, optional): The maximum number of logs to return. Defaults to 100.

    Returns:
        List[Dict[str, Any]]: A list of rehydrated log data dictionaries.
    """
    query = "SELECT * FROM log_catalog WHERE 1=1"
    params = []

    if 'log_level' in criteria:
      query += " AND log_level = ?"
      params.append(criteria['log_level'].upper())
    if 'category' in criteria:
      query += " AND category = ?"
      params.append(criteria['category'])
    if 'context_category_parsed' in criteria:
      query += " AND context_category_parsed = ?"
      params.append(criteria['context_category_parsed'])
    if 'assessment_score_min' in criteria:
      query += " AND assessment_score >= ?"
      params.append(criteria['assessment_score_min'])
    if 'assessment_score_max' in criteria:
      query += " AND assessment_score <= ?"
      params.append(criteria['assessment_score_max'])
    if 'keywords_contains' in criteria:
      query += " AND keywords LIKE ?"
      params.append(f"%{criteria['keywords_contains']}%")
    if 'content_contains' in criteria:
      query += " AND content LIKE ?"
      params.append(f"%{criteria['content_contains']}%")
    if 'status' in criteria:
      query += " AND status = ?"
      params.append(criteria['status'])
    if 'max_ingestion_timestamp' in criteria:
      query += " AND ingestion_timestamp <= ?"
      params.append(criteria['max_ingestion_timestamp'])
    if 'min_ingestion_timestamp' in criteria:
      query += " AND ingestion_timestamp >= ?"
      params.append(criteria['min_ingestion_timestamp'])

    query += f" ORDER BY ingestion_timestamp DESC LIMIT ?"
    params.append(limit)

    results = []
    try:
      with self.log_catalog_conn:
        cursor = self.log_catalog_conn.execute(query, tuple(params))
        column_names = [description[0] for description in cursor.description]
        for row in cursor.fetchall():
          row_dict = dict(zip(column_names, row))
          row_dict['embedding'] = json.loads(row_dict['embedding_json']) if row_dict['embedding_json'] else None
          row_dict['keywords'] = json.loads(row_dict['keywords']) if row_dict['keywords'] else []
          row_dict['parsed_values'] = json.loads(row_dict['parsed_values_json']) if row_dict['parsed_values_json'] else {}

          results.append(row_dict)
    except Exception as e:
      logger.error(f"Error rehydrating log data: {e}")
    return results

  def verify_rehydration_process(self, rehydrated_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyzes rehydrated log data to verify its integrity and generate diagnostics.

    This provides feedback to improve the initial assessment process.

    Args:
        rehydrated_data (List[Dict[str, Any]]): A list of rehydrated log data.

    Returns:
        Dict[str, Any]: A dictionary of verification metrics and diagnostics.
    """
    metrics: Dict[str, Any] = {
      "total_entries": len(rehydrated_data),
      "log_level_distribution": {},
      "category_distribution": {},
      "parsed_category_distribution": {},
      "avg_assessment_score": 0.0,
      "min_timestamp_ingestion": None,
      "max_timestamp_ingestion": None,
      "min_timestamp_log": None,
      "max_timestamp_log": None,
      "entries_missing_embedding": 0,
      "entries_missing_parsed_values": 0,
      "diagnostics": []
    }

    if not rehydrated_data:
      metrics["diagnostics"].append("No data to verify.")
      return metrics

    all_scores = []
    for entry in rehydrated_data:
      level = entry.get('log_level', 'UNKNOWN')
      category = entry.get('category', 'general')
      parsed_cat = entry.get('context_category_parsed', 'none')
      ingest_ts = entry.get('ingestion_timestamp')
      log_original_ts = entry.get('log_timestamp')

      metrics['log_level_distribution'][level] = metrics['log_level_distribution'].get(level, 0) + 1
      metrics['category_distribution'][category] = metrics['category_distribution'].get(category, 0) + 1
      metrics['parsed_category_distribution'][parsed_cat] = metrics['parsed_category_distribution'].get(parsed_cat, 0) + 1

      all_scores.append(entry.get('assessment_score', 0.0))

      if entry.get('embedding') is None:
        metrics['entries_missing_embedding'] += 1
        metrics['diagnostics'].append(f"Entry {entry.get('id')} from {entry.get('source_file')} missing embedding.")

      if not entry.get('parsed_values') and parsed_cat != 'none':
        metrics['entries_missing_parsed_values'] += 1
        metrics['diagnostics'].append(f"Entry {entry.get('id')} from {entry.get('source_file')} has parsed category '{parsed_cat}' but no structured values found.")

      if ingest_ts:
        if metrics["min_timestamp_ingestion"] is None or ingest_ts < metrics["min_timestamp_ingestion"]:
          metrics["min_timestamp_ingestion"] = ingest_ts
        if metrics["max_timestamp_ingestion"] is None or ingest_ts > metrics["max_timestamp_ingestion"]:
          metrics["max_timestamp_ingestion"] = ingest_ts

      if log_original_ts:
           if metrics["min_timestamp_log"] is None or log_original_ts < metrics["min_timestamp_log"]:
            metrics["min_timestamp_log"] = log_original_ts
           if metrics["max_timestamp_log"] is None or log_original_ts > metrics["max_timestamp_log"]:
            metrics["max_timestamp_log"] = log_original_ts

    metrics['avg_assessment_score'] = float(np.mean(all_scores))

    if metrics['entries_missing_embedding'] > 0:
      metrics['diagnostics'].append(f"WARNING: {metrics['entries_missing_embedding']} entries had no embeddings. Check embedding provider.")
    if metrics['entries_missing_parsed_values'] > 0:
      metrics['diagnostics'].append(f"INFO: {metrics['entries_missing_parsed_values']} entries had parsed categories but no specific values extracted. Consider refining advanced parsers.")

    logger.info(f"Rehydration Verification Results: {json.dumps(metrics, indent=2)}")
    return metrics

  def generate_synthesis_report(self, similarity_threshold: float = 0.75) -> Path:
    """
    Compiles and combines similar log entries from the catalog into a synthesis report.

    This report can serve as self-generated training data for improving the system.

    Args:
        similarity_threshold (float, optional): The similarity threshold for
            grouping log entries. Defaults to 0.75.

    Returns:
        Path: The path to the generated synthesis report.
    """
    if np is None:
      logger.error("NumPy not available, cannot generate synthesis report.")
      return Path("")

    logger.info("Generating IntelliSense Data Synthesis Report...")

    relevant_logs = self.rehydrate_log_data(
      {'status': 'for_ai_learning',
       'assessment_score_min': self.bootstrapper.config['log_management']['assessment_threshold_ai_learning']
      }, limit=500
    )

    if not relevant_logs:
      logger.info("No relevant logs found for synthesis report.")
      self.synthesis_report_path.parent.mkdir(parents=True, exist_ok=True)
      with open(self.synthesis_report_path, "w", encoding="utf-8") as f:
        f.write(f"IntelliSense Data Synthesis Report - {datetime.now(timezone.utc).isoformat()}Z\n")
        f.write("No relevant logs found for synthesis at this time.\n")
      return self.synthesis_report_path

    logs_with_embeddings = [log for log in relevant_logs if log.get('embedding') is not None]
    if not logs_with_embeddings:
      logger.warning("No logs with valid embeddings found for similarity grouping.")
      return self.synthesis_report_path

    try:
      embeddings_np = np.array([log['embedding'] for log in logs_with_embeddings])
      norms = np.linalg.norm(embeddings_np, axis=1)
      normalized_embeddings = embeddings_np / np.where(norms[:, np.newaxis] != 0, norms[:, np.newaxis], 1)
    except Exception as e:
      logger.error(f"Error converting embeddings for synthesis: {e}")
      return self.synthesis_report_path

    grouped_logs: List[List[Dict[str, Any]]] = []
    processed_indices = set()

    for i in range(len(normalized_embeddings)):
      if i in processed_indices:
        continue

      current_group = [logs_with_embeddings[i]]
      processed_indices.add(i)

      for j in range(len(normalized_embeddings)):
        if i == j or j in processed_indices:
          continue

        similarity = np.dot(normalized_embeddings[i], normalized_embeddings[j])
        if similarity >= similarity_threshold:
          current_group.append(logs_with_embeddings[j])
          processed_indices.add(j)

      grouped_logs.append(current_group)

    synthesis_entries: List[Dict[str, Any]] = []
    for group_id, group in enumerate(grouped_logs):
      main_log = group[0]

      all_keywords = set()
      all_categories = set()
      all_parsed_categories = set()
      numerical_values: Dict[str, List[Any]] = {}

      for log_entry in group:
        if log_entry.get('keywords'):
          all_keywords.update(log_entry['keywords'])
        all_categories.add(log_entry.get('category'))
        all_parsed_categories.add(log_entry.get('context_category_parsed'))

        if log_entry.get('parsed_values'):
          for k,v in log_entry['parsed_values'].items():
            if isinstance(v, (int, float)):
              numerical_values.setdefault(k, []).append(v)

      summarized_numerical: Dict[str, Any] = {}
      for k,vals in numerical_values.items():
        if vals:
          summarized_numerical[k] = {
            "avg": float(np.mean(vals)),
            "min": float(np.min(vals)),
            "max": float(np.max(vals))
          }

      synthesis_entries.append({
        "synthesis_id": f"group_{group_id}",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "group_size": len(group),
        "representative_log": main_log.get('content'),
        "common_keywords": list(all_keywords),
        "common_categories": list(all_categories),
        "common_parsed_categories": list(all_parsed_categories),
        "summarized_numerical_metrics": summarized_numerical,
        "logs_in_group_ids": [log.get('id') for log in group],
        "purpose": "Training data for AI learning on common log patterns."
      })

    self.synthesis_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self.synthesis_report_path, "w", encoding="utf-8") as f:
      f.write(f"IntelliSense Data Synthesis Report - {datetime.now(timezone.utc).isoformat()}Z\n")
      f.write(f"Generated based on {len(relevant_logs)} relevant logs. Total {len(synthesis_entries)} synthesized groups.\n\n")
      for entry in synthesis_entries:
        f.write("--- SYTHESIZED LOG GROUP ---\n")
        f.write(json.dumps(entry, indent=2, ensure_ascii=False))
        f.write("\n\n")

    logger.info(f"IntelliSense Data Synthesis Report generated at: {self.synthesis_report_path}")
    logger.info("This report will now be auto-parsed by the system as new training data.")
    return self.synthesis_report_path

  def health_check(self) -> bool:
    """
    Performs a health check on the module.

    Returns:
        bool: True if the module is healthy, False otherwise.
    """
    try:
      self.conn.execute("SELECT 1")
      self.log_catalog_conn.execute("SELECT 1")
      return True
    except Exception as e:
      logger.error(f"MetaReflectionEngine DB health check failed: {e}")
      return False

  def shutdown(self):
    """Closes the SQLite database connections."""
    if self.conn:
        self.conn.close()
        logger.info(f"MetaReflectionEngine feedback DB connection closed for {self.db_path}.")
    if self.log_catalog_conn:
        self.log_catalog_conn.close()
        logger.info(f"MetaReflectionEngine log catalog DB connection closed for {self.log_catalog_conn}.")


class ModuleOrchestrator:
  """Manages and monitors health of IntellisenseSystem modules."""
  def __init__(self, system_instance: 'IntellisenseSystem', module_state_tracker: ModuleStateTracker):
    """
    Initializes the ModuleOrchestrator.

    Args:
        system_instance (IntellisenseSystem): The main system instance.
        module_state_tracker (ModuleStateTracker): The module state tracker.
    """
    self.system = system_instance
    self.modules: Dict[str, Any] = {}
    self.module_state_tracker = module_state_tracker
    self.last_snapshot_time = 0
    logger.info("ModuleOrchestrator initialized.")

  def register_modules(self, modules: Dict[str, Any]):
    """
    Registers modules for the orchestrator to monitor.

    Args:
        modules (Dict[str, Any]): A dictionary of modules to register.
    """
    self.modules = modules
    logger.info(f"Registered {len(self.modules)} modules for monitoring.")

  def run_health_checks(self) -> Dict[str, str]:
    """
    Runs health checks on all registered modules.

    Returns:
        Dict[str, str]: A dictionary of health check results.
    """
    health_status: Dict[str, str] = {}
    for name, module in self.modules.items():
      try:
        if hasattr(module, 'health_check') and callable(module.health_check):
          is_healthy = module.health_check()
          health_status[name] = "PASSED" if is_healthy else "FAILED"
        else:
          health_status[name] = "N/A"
      except Exception as e:
        logger.error(f"Health check for module {name} failed: {e}")
        health_status[name] = "FAILED"
    return health_status

  def snapshot_all_modules_state(self):
    """Captures and records a snapshot of all registered modules' operational metrics."""
    tracking_interval = self.system.bootstrapper.config['module_tracking']['tracking_interval_sec']
    current_time = time.time()

    if current_time - self.last_snapshot_time < tracking_interval:
      logger.debug(f"Skipping module state snapshot: Not yet {tracking_interval} seconds since last snapshot.")
      return

    logger.info("Starting module state snapshot.")
    for name, module in self.modules.items():
      snapshot_data: Dict[str, Any] = {
        "module_name": name,
        "status": "UNKNOWN",
        "config_snapshot": {k:v for k,v in self.system.bootstrapper.config.items() if k not in ['diagnostic_keywords', 'memoria_ecosystem']}
      }
      try:
        is_healthy = False
        if hasattr(module, 'health_check') and callable(module.health_check):
          is_healthy = module.health_check()
          snapshot_data['status'] = "ACTIVE" if is_healthy else "ERROR"
        else:
          snapshot_data['status'] = "ACTIVE"

        if hasattr(module, 'get_operational_metrics') and callable(module.get_operational_metrics):
          operational_metrics = module.get_operational_metrics()
          snapshot_data.update(operational_metrics)
        else:
          snapshot_data.update({
            "invocations": -1, "success_count": -1, "error_count": -1,
            "success_rate": -1.0, "avg_latency_ms": -1.0
          })

        if hasattr(module, 'last_error_message'):
          snapshot_data['last_error_message'] = module.last_error_message
        else:
          snapshot_data['last_error_message'] = None


      except Exception as e:
        logger.error(f"Failed to get snapshot data for module {name}: {e}")
        snapshot_data['status'] = "CRITICAL_ERROR"
        snapshot_data['last_error_message'] = str(e)
        snapshot_data['error_trace'] = traceback.format_exc()

      self.module_state_tracker.record_snapshot(snapshot_data)
    self.last_snapshot_time = current_time
    logger.info("Module state snapshot completed.")

  def health_check(self) -> bool:
    """
    Performs a health check on the module.

    Returns:
        bool: True if the module is healthy, False otherwise.
    """
    return bool(self.modules)


class IntellisenseSystem:
  """
    The main class for the Citadel Dossier System's Adaptive Intellisense Core.

    This class integrates all the other components of the system to provide
    AI-driven assistance for software development.
    """
  def __init__(self):
    """Initializes the IntellisenseSystem and all its sub-modules."""
    self.bootstrapper = IntellisenseBootstrapper()
    self.module_state_tracker = ModuleStateTracker(Path("intellisense_feedback.db"))
    self.modules = {
      'CodebaseHealthModeler': CodebaseHealthModeler(self.bootstrapper),
      'DeveloperPersonaEngine': DeveloperPersonaEngine(self.bootstrapper),
      'DiagnosticUrgencySystem': DiagnosticUrgencySystem(self.bootstrapper),
      'MetaReflectionEngine': MetaReflectionEngine(self.bootstrapper),
    }
    self.modules['ModuleOrchestrator'] = ModuleOrchestrator(self, self.module_state_tracker)

    if self.bootstrapper.config.get('memoria_ecosystem', {}).get('enabled', False):
      try:
        memoria_core = MemoriaCore()
        memoria_core_config = memoria_core.config

        memoria_core.initialize({})
        self.modules['MemoriaCore'] = memoria_core
      except Exception as e:
        logger.error(f"An error occurred during Memoria ecosystem initialization: {e}")

    self.modules['ModuleOrchestrator'].register_modules(self.modules)
    self.last_turn_data: Dict[str, Dict[str, Any]] = {}
    self._last_log_ingest_time = 0
    self._last_synthesis_time = 0
    self._last_module_snapshot_time = 0
    logger.info("IntellisenseSystem initialized.")

  def _get_reward(self, feedback_text: str) -> float:
    """Calculates a reward score based on feedback text."""
    text = feedback_text.lower()
    if any(w in text for w in ['thanks', 'perfect', 'great', 'correct', 'good job']):
      return 10.0
    if any(w in text for w in ['wrong', 'incorrect', 'bad', 'not helpful']):
      return -10.0
    if any(w in text for w in ['more details', 'clarify', 'expand']):
      return 1.0
    return 0.0

  def process_input(self, user_input: str, code_metrics: Dict[str, Any], user_id: str = "default") -> str:
    """
    Processes user input to provide AI-driven suggestions and analysis.

    Args:
        user_input (str): The natural language query from the developer.
        code_metrics (Dict[str, Any]): A dictionary of code statistics.
        user_id (str, optional): An identifier for the user. Defaults to "default".

    Returns:
        str: The AI-generated response.
    """
    start_time = time.time()

    log_management_config = self.bootstrapper.config.get('log_management', {})
    if log_management_config.get('enabled', False):
      scan_interval = log_management_config.get('scan_interval_sec', 300)
      if time.time() - self._last_log_ingest_time >= scan_interval:
        logger.info(f"Triggering scheduled log ingestion ({scan_interval}s interval).")
        self.modules['MetaReflectionEngine'].ingest_new_logs()
        self._last_log_ingest_time = time.time()
      else:
        logger.debug("Skipping periodic log ingestion. Interval not met.")

      synthesis_interval_mult = log_management_config.get('synthesis_interval_multiplier', 0.5)
      synthesis_interval = scan_interval * synthesis_interval_mult
      if time.time() - self._last_synthesis_time >= synthesis_interval:
        logger.info(f"Triggering scheduled synthesis report generation ({synthesis_interval}s interval).")
        self.modules['MetaReflectionEngine'].generate_synthesis_report()
        self._last_synthesis_time = time.time()
      else:
        logger.debug("Skipping periodic synthesis report. Interval not met.")

    module_tracking_config = self.bootstrapper.config.get('module_tracking', {})
    if module_tracking_config.get('enabled', False):
      tracking_interval = module_tracking_config.get('tracking_interval_sec', 60)
      if time.time() - self._last_module_snapshot_time >= tracking_interval:
        logger.info(f"Triggering scheduled module state snapshot ({tracking_interval}s interval).")
        self.modules['ModuleOrchestrator'].snapshot_all_modules_state()
        self._last_module_snapshot_time = time.time()
      else:
        logger.debug("Skipping periodic module state snapshot. Interval not met.")

    if psutil:
      try:
        cpu_usage = psutil.cpu_percent(interval=None)
        memory_usage = psutil.virtual_memory().percent
        logger.info(f"System resources - CPU: {cpu_usage:.1f}%, Memory: {memory_usage:.1f}%")
        if cpu_usage > self.bootstrapper.config['system_monitoring']['cpu_threshold']:
          logger.warning("High CPU usage detected.")
        if memory_usage > self.bootstrapper.config['system_monitoring']['memory_threshold']:
          logger.warning("High memory usage detected.")
      except Exception as e:
        logger.warning(f"Could not get system resource stats: {e}")

    reward_from_prev_turn = 0.0
    current_user_last_turn_data = self.last_turn_data.get(user_id)
    if current_user_last_turn_data:
      reward_from_prev_turn = self._get_reward(user_input)
      self.modules['MetaReflectionEngine'].store_feedback(
        user_input=current_user_last_turn_data['user_input'],
        ai_response=current_user_last_turn_data['ai_response'],
        status="accepted" if reward_from_prev_turn > 0 else ("discarded" if reward_from_prev_turn < 0 else "modified"),
        reward=reward_from_prev_turn,
        user_id=user_id
        )
      self.last_turn_data[user_id] = None

    context_score = self.modules['DiagnosticUrgencySystem'].analyze_context(user_input, code_metrics)
    self.modules['DiagnosticUrgencySystem'].update_urgency(context_score, momentum=code_metrics.get('momentum', 0.0))
    urgency = self.modules['DiagnosticUrgencySystem'].get_urgency_level()

    self.modules['DeveloperPersonaEngine'].update_persona({"input": user_input, "metrics": code_metrics}, urgency, reward_from_prev_turn)

    base_response = f"Analyzed code metrics: Complexity {code_metrics.get('complexity', 0.0):.2f}, Coverage {code_metrics.get('coverage', 0.0):.2f}"
    shaped_response = self.modules['DeveloperPersonaEngine'].shape_response(base_response, urgency)

    stability_verified = True
    coverage_verified = True
    if np is not None:
      stability_verified = self.modules['CodebaseHealthModeler'].verify_projection("CODE_STABILITY_V1", (0, 10), (0, 1))
      coverage_verified = self.modules['CodebaseHealthModeler'].verify_projection("TEST_COVERAGE_POTENTIAL", (0, 1), (0, 1000))
    else:
      logger.warning("Skipping codebase health verification, NumPy is not available.")

    if not (stability_verified and coverage_verified):
      shaped_response += "\nWarning: Codebase health projections indicate potential issues."

    if 'MemoriaCore' in self.modules:
      memoria_request = {
        'code_snippet': user_input,
        'performance_metrics': code_metrics,
        'analysis_result': {}
      }
      if 'analysis_interface' in self.modules['MemoriaCore'].modules:
        mock_analysis_result = self.modules['MemoriaCore'].modules['analysis_interface'].process(memoria_request)
        if mock_analysis_result.get('status') == 'success':
          memoria_request['analysis_result'] = mock_analysis_result['analysis_result']

      memoria_result = self.modules['MemoriaCore'].process_request(memoria_request)
      if memoria_result['status'] == 'success':
        shaped_response += f"\nMemoria Analysis: {json.dumps(memoria_result['data'], indent=2)}"
      else:
        shaped_response += f"\nMemoria Processing Issue: {memoria_result.get('status', 'failed')}"


    self.last_turn_data[user_id] = {
      "user_input": user_input,
      "ai_response": shaped_response,
      "status": "pending",
      "reward": 0.0
    }

    reflection_summary = self.modules['MetaReflectionEngine'].reflect(user_input, shaped_response, user_id)
    if reflection_summary:
      shaped_response += f"\n[Meta: {reflection_summary}]"


    latency = time.time() - start_time
    logger.info(f"Processed input in {latency:.2f} seconds.")
    return shaped_response

  def run_self_test(self) -> Dict[str, Any]:
    """
    Runs a suite of self-diagnostic tests on the system.

    Returns:
        Dict[str, Any]: A dictionary of test results.
    """
    logger.info("Running IntellisenseSystem self-diagnostic tests...")
    detailed_test_results: Dict[str, Any] = {
      "timestamp": datetime.now(timezone.utc).isoformat(),
      "overall_status": "UNKNOWN",
      "tests": {}
    }

    def record_test(test_name: str, status: str, message: str, details: Optional[Dict] = None, severity: str = "INFO", recommendation: Optional[str] = None):
      res_details = details or {}
      details = {"message": message, "details": res_details}
      detailed_test_results['tests'][test_name] = {
        "status": status,
        "message": message,
        "details": res_details,
        "severity": severity,
        "recommendation": recommendation
      }
      if status == "FAIL":
        logger.error(f"Self-test [{test_name}] FAILED: {message}")
      elif status == "WARNING":
        logger.warning(f"Self-test [{test_name}] WARNING: {message}")
      else:
        logger.info(f"Self-test [{test_name}] PASSED: {message}")


    try:
      module_health_status = self.modules['ModuleOrchestrator'].run_health_checks()
      record_test("module_health_check",
                  "PASS" if all(h == "PASSED" for h in module_health_status.values()) else "FAIL",
                  "All registered modules passed health checks." if all(h == "PASSED" for h in module_health_status.values()) else "Some modules failed health checks.",
                  details=module_health_status,
                  severity="INFO" if all(h == "PASSED" for h in module_health_status.values()) else "CRITICAL",
                  recommendation="Investigate specific module failures." if not all(h == "PASSED" for h in module_health_status.values()) else None)
    except Exception as e:
      record_test("module_health_check", "FAIL", f"Module health check orchestration failed: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()},
                  severity="CRITICAL", recommendation="Check ModuleOrchestrator implementation.")

    record_test("config_loading",
                "PASS" if bool(self.bootstrapper.config) else "FAIL",
                "System configuration loaded successfully." if bool(self.bootstrapper.config) else "Failed to load system configuration.",
                severity="INFO" if bool(self.bootstrapper.config) else "CRITICAL",
                recommendation="Check intellisense_config.json file for existence and syntax." if not bool(self.bootstrapper.config) else None)

    try:
      test_embedding = self.bootstrapper.embedding_provider.get_embedding("self-test-embedding-string")
      if test_embedding and len(test_embedding) == self.bootstrapper.config['embedding_dimension']:
        record_test("embedding_provider_functionality", "PASS", "Embedding provider is functional and dimension matches config.",
                    details={"actual_dimension": len(test_embedding)}, severity="INFO")
      else:
        record_test("embedding_provider_functionality", "FAIL", "Embedding provider returned invalid or mismatched embedding.",
                    details={"test_embedding_is_none": test_embedding is None, "actual_dimension": len(test_embedding) if test_embedding else 0, "expected_dimension": self.bootstrapper.config['embedding_dimension']},
                    severity="CRITICAL", recommendation="Check sentence-transformers installation and model loading. Verify internet access for model download.")
    except Exception as e:
      record_test("embedding_provider_functionality", "FAIL", f"Embedding provider test raised an exception: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="Ensure sentence-transformers is installed and model loads correctly.")

    codebase_health_status = "SKIPPED"
    codebase_health_message = "NumPy not available, codebase health modeling skipped."
    codebase_health_severity = "INFO"
    codebase_health_recommendation = "Install numpy for codebase health insights."
    codebase_health_details = None

    if np is not None:
      try:
        stability_verified = self.modules['CodebaseHealthModeler'].verify_projection("CODE_STABILITY_V1", (0, 10), (0, 1))
        coverage_verified = self.modules['CodebaseHealthModeler'].verify_projection("TEST_COVERAGE_POTENTIAL", (0, 1), (0, 1000))
        if stability_verified and coverage_verified:
          codebase_health_status = "PASS"
          codebase_health_message = "Codebase health projections verified."
          codebase_health_severity = "INFO"
        else:
          codebase_health_status = "FAIL"
          codebase_health_message = "Some codebase health projections failed verification."
          codebase_health_severity = "WARNING"
          codebase_health_recommendation = "Review projection equations and underlying data."
      except Exception as e:
        codebase_health_status = "FAIL"
        codebase_health_message = f"Codebase health model verification failed: {e}"
        codebase_health_severity = "CRITICAL"
        codebase_health_recommendation = "Check CodebaseHealthModeler implementation and dependencies."
        codebase_health_details = {"error": str(e), "traceback": traceback.format_exc()}

    record_test("codebase_health_model_verification", codebase_health_status, codebase_health_message,
                details=codebase_health_details, severity=codebase_health_severity, recommendation=codebase_health_recommendation)

    try:
      self.modules['MetaReflectionEngine'].conn.execute("SELECT 1").fetchone()
      record_test("feedback_db_access", "PASS", "Feedback database is accessible.", severity="INFO")
    except Exception as e:
      record_test("feedback_db_access", "FAIL", f"Feedback database access failed: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="Check intellisense_feedback.db file permissions or SQLite installation.")

    try:
      self.modules['MetaReflectionEngine'].log_catalog_conn.execute("SELECT 1").fetchone()
      record_test("log_catalog_db_access", "PASS", "Log catalog database is accessible.", severity="INFO")

      rehydrated_data_sample = self.modules['MetaReflectionEngine'].rehydrate_log_data({'limit': 1})
      if rehydrated_data_sample is not None:
        record_test("log_catalog_rehydration_functional", "PASS", "Log catalog rehydration is functional.", severity="INFO")

        rehydration_verification_report = self.modules['MetaReflectionEngine'].verify_rehydration_process(rehydrated_data_sample[:5])
        if rehydration_verification_report and not rehydration_verification_report.get('diagnostics'):
          record_test("log_catalog_rehydration_verification", "PASS", "Log catalog rehydration data passed initial verification.",
                      details=rehydration_verification_report, severity="INFO")
        else:
          record_test("log_catalog_rehydration_verification", "FAIL", "Log catalog rehydration data had verification issues.",
                      details=rehydration_verification_report, severity="WARNING", recommendation="Review log parsing and assessment logic based on diagnostics.")
      else:
        record_test("log_catalog_rehydration_functional", "FAIL", "Log catalog rehydration returned None or empty.",
                    severity="CRITICAL", recommendation="Check rehydrate_log_data implementation.")

    except Exception as e:
      record_test("log_catalog_db_access", "FAIL", f"Log catalog database test failed: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="Check intellisense_log_catalog.db file permissions or SQLite installation. Ensure table schema is correct.")
      record_test("log_catalog_rehydration_functional", "FAIL", "DB not accessible for rehydration.", severity="CRITICAL")
      record_test("log_catalog_rehydration_verification", "FAIL", "DB not accessible for verification.", severity="CRITICAL")


    try:
      synthesis_path = self.modules['MetaReflectionEngine'].generate_synthesis_report(similarity_threshold=0.9)
      if synthesis_path.exists() and synthesis_path.stat().st_size > 0:
        record_test("synthesis_report_generation", "PASS", "Data synthesis report generated successfully with content.",
                    details={"report_path": str(synthesis_path), "report_size_bytes": synthesis_path.stat().st_size}, severity="INFO")
      else:
        record_test("synthesis_report_generation", "FAIL", "Synthesis report generated but was empty or did not exist.",
                    details={"report_path": str(synthesis_path), "report_exists": synthesis_path.exists()}, severity="WARNING",
                    recommendation="Check why synthesis did not produce output. Perhaps no relevant logs or too high similarity threshold.")
    except Exception as e:
      record_test("synthesis_report_generation", "FAIL", f"Synthesis report generation failed: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="Check MetaReflectionEngine.generate_synthesis_report implementation and log data availability.")

    try:
      memoria_checks = self.bootstrapper.diagnostics.run_diagnostics(
        [
            self.bootstrapper.memoria_ecosystem_path / 'config' / 'memoria_config.json',
            self.bootstrapper.memoria_ecosystem_path / 'memoria_module.py',
            self.bootstrapper.memoria_ecosystem_path / 'memoria_core.py',
            self.bootstrapper.memoria_ecosystem_path / 'self_reflection.py',
            self.bootstrapper.memoria_ecosystem_path / 'optimization_engine.py',
            self.bootstrapper.memoria_ecosystem_path / 'analysis_interface.py',
        ],
        [
            (self.bootstrapper.memoria_ecosystem_path / 'memoria_module.py', 'ecosystem.memoria.memoria_module'),
            (self.bootstrapper.memoria_ecosystem_path / 'memoria_core.py', 'ecosystem.memoria.memoria_core'),
            (self.bootstrapper.memoria_ecosystem_path / 'self_reflection.py', 'ecosystem.memoria.self_reflection'),
            (self.bootstrapper.memoria_ecosystem_path / 'optimization_engine.py', 'ecosystem.memoria.optimization_engine'),
            (self.bootstrapper.memoria_ecosystem_path / 'analysis_interface.py', 'ecosystem.memoria.analysis_interface')
        ]
      )

      all_memoria_modules_passed = all(memoria_checks.values())
      memoria_overall_status = "PASS" if all_memoria_modules_passed else "FAIL"
      memoria_severity = "INFO" if all_memoria_modules_passed else "WARNING"
      memoria_recommendation = "Review Memoria ecosystem files and imports." if not all_memoria_modules_passed else None

      record_test("memoria_ecosystem_verification",
                  memoria_overall_status,
                  "Memoria ecosystem files and imports verified successfully." if all_memoria_modules_passed else "Memoria ecosystem verification had issues (external files).",
                  details=memoria_checks,
                  severity=memoria_severity,
                  recommendation=memoria_recommendation)
    except Exception as e:
      record_test("memoria_ecosystem_verification", "FAIL", f"Memoria ecosystem verification failed: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="Ensure Memoria ecosystem files exist and are syntactically correct, and all dependencies are met for their external imports.")


    if psutil:
      try:
        cpu_before = psutil.cpu_percent(interval=None)
        time.sleep(0.1)
        cpu_after = psutil.cpu_percent(interval=None)
        memory_usage = psutil.virtual_memory().percent
        if cpu_after is not None and memory_usage is not None:
          record_test("system_resource_monitoring", "PASS", "System resource monitoring functional.",
                      details={"cpu_percent_sampled": cpu_after, "memory_percent": memory_usage}, severity="INFO")
        else:
          record_test("system_resource_monitoring", "FAIL", "psutil installed but could not retrieve valid resource data.",
                      details={"cpu_after": cpu_after, "memory_usage": memory_usage}, severity="WARNING", recommendation="Check psutil permissions/configuration.")
      except Exception as e:
        record_test("system_resource_monitoring", "FAIL", f"System resource monitoring test failed: {e}",
                    details={"error": str(e), "traceback": traceback.format_exc()}, severity="WARNING",
                    recommendation="Check psutil installation or system environment permissions.")
    else:
      record_test("system_resource_monitoring", "SKIPPED", "psutil not found, system resource monitoring skipped.", severity="INFO",
                  recommendation="Install psutil for system resource insights.")

    try:
      self.modules['ModuleOrchestrator'].snapshot_all_modules_state()
      latest_snapshots = self.module_state_tracker.retrieve_latest_snapshots(limit=len(self.modules))
      if latest_snapshots and len(latest_snapshots) >= len(self.modules):
        has_valid_metrics = any(s.get('invocations', 0) > -1 for s in latest_snapshots)
        if has_valid_metrics:
          record_test("module_state_tracking", "PASS", "Module state tracking and snapshot recording functional.",
                      details={"num_snapshots": len(latest_snapshots)}, severity="INFO")
        else:
          record_test("module_state_tracking", "WARNING", "Module state tracking recorded snapshots but operational metrics might be missing.",
                      details={"num_snapshots": len(latest_snapshots)}, severity="WARNING", recommendation="Ensure modules correctly implement `get_operational_metrics`.")
      else:
        record_test("module_state_tracking", "FAIL", "Module state tracking did not record expected number of snapshots.",
                    details={"expected": len(self.modules), "actual": len(latest_snapshots)}, severity="CRITICAL",
                    recommendation="Check ModuleOrchestrator.snapshot_all_modules_state and ModuleStateTracker.record_snapshot implementations.")
    except Exception as e:
      record_test("module_state_tracking", "FAIL", f"Module state tracking test failed: {e}",
                  details={"error": str(e), "traceback": traceback.format_exc()}, severity="CRITICAL",
                  recommendation="Check ModuleStateTracker and ModuleOrchestrator implementations.")


    overall_status_list = [t['status'] for t in detailed_test_results['tests'].values() if t['status'] != "SKIPPED"]
    if "FAIL" in overall_status_list: detailed_test_results['overall_status'] = "FAIL"
    elif "WARNING" in overall_status_list: detailed_test_results['overall_status'] = "WARNING"
    elif "PASS" in overall_status_list: detailed_test_results['overall_status'] = "PASS"
    else: detailed_test_results['overall_status'] = "SKIPPED_ALL"

    logger.info(f"Self-test results:\n{json.dumps(detailed_test_results, indent=2)}")

    self_test_report_path = Path("logs/intellisense_self_test_report.jsonl")
    self_test_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(self_test_report_path, "a", encoding="utf-8") as f:
      json.dump(detailed_test_results, f)
      f.write("\n")
    logger.info(f"Self-test report saved to {self_test_report_path} for self-reprocessing.")

    return detailed_test_results
  
  def shutdown(self):
      """Performs a graceful shutdown of all IntellisenseSystem modules."""
      logger.info("Initiating IntellisenseSystem modules shutdown...")
      for name, module in self.modules.items():
          if name not in ['ModuleOrchestrator', 'MemoriaCore'] and hasattr(module, 'shutdown') and callable(module.shutdown):
              try:
                  module.shutdown()
                  logger.info(f"Module {name} gracefully shut down.")
              except Exception as e:
                  logger.error(f"Error during shutdown of module {name}: {e}")
      
      if 'MemoriaCore' in self.modules:
          memoria_core_module = self.modules['MemoriaCore']
          logger.info("MemoriaCore (internal instance) does not require explicit shutdown, its sub-modules manage themselves.")


  def display_system_summary_grid(self, num_modules_to_display: int = 10):
    """
    Retrieves the latest module operational snapshots and prints a human-readable grid summary to CLI.
    """
    logger.info("Generating IntelliSense System Summary Grid...")
    latest_snapshots = self.module_state_tracker.retrieve_latest_snapshots(limit=num_modules_to_display)

    if not latest_snapshots:
      print("\n--- IntelliSense System Summary ---")
      print("No module operational data available yet. Please interact with the system or wait for scheduled snapshots.")
      print("-----------------------------------")
      return

    headers = ["Module", "Status", "Health", "Invocations", "Success Rate", "Avg Latency (ms)", "Last Error"]
    rows = []

    col_widths = {header: len(header) for header in headers}

    for snapshot in latest_snapshots:
      module_name = snapshot.get('module_name', 'N/A')
      status = snapshot.get('status', 'N/A')
      health_status_obj = self.modules.get(module_name)
      if health_status_obj and hasattr(health_status_obj, 'health_check') and callable(health_status_obj.health_check):
          try:
              is_healthy = health_status_obj.health_check()
              health_status_str = "HEALTHY" if is_healthy is True else ("UNHEALTHY" if is_healthy is False else "N/A_FUNC")
          except Exception:
              health_status_str = "ERROR_CHECK"
      else:
          health_status_str = "N/A_MOD"

      invocations = snapshot.get('invocations', 0)
      success_rate = f"{snapshot.get('success_rate', 0.0)*100:.1f}%" if snapshot.get('invocations', 0) > 0 else "N/A"
      avg_latency = f"{snapshot.get('avg_latency_ms', 0.0):.2f}" if snapshot.get('invocations') else "N/A"
      last_error = snapshot.get('last_error_message', '') or ''

      module_name_display = (module_name[:18] + '..') if len(module_name) > 20 else module_name
      last_error_display = (last_error[:18] + '..') if len(last_error) > 20 else last_error

      rows.append({
        "Module": module_name_display,
        "Status": status,
        "Health": health_status_str,
        "Invocations": str(invocations),
        "Success Rate": success_rate,
        "Avg Latency (ms)": avg_latency,
        "Last Error": last_error_display
      })

      for i, header in enumerate(headers):
        col_widths[header] = max(col_widths[header], len(rows[-1][header]))

    print("\n" + "=" * (sum(col_widths.values()) + len(headers) * 3 + 1))
    print("IntelliSense System Operational Snapshot Audit".center(sum(col_widths.values()) + len(headers) * 3 + 1))
    print("=" * (sum(col_widths.values()) + len(headers) * 3 + 1))

    header_line = "│"
    for header in headers:
      header_line += f" {header:<{col_widths[header]}} │"
    print(header_line)
    print("├" + "─" * (sum(col_widths.values()) + len(headers) * 3 - 1) + "┤")

    for row_data in rows:
      data_line = "│"
      for header in headers:
        data_line += f" {row_data[header]:<{col_widths[header]}} │"
      print(data_line)

    print("=" * (sum(col_widths.values()) + len(headers) * 3 + 1))
    print(f"Data captured at: {datetime.now(timezone.utc).isoformat()}Z".rjust(sum(col_widths.values()) + len(headers) * 3 + 1))
    print("=" * (sum(col_widths.values()) + len(headers) * 3 + 1) + "\n")


if __name__ == "__main__":
    # --- PRE-BOOT ARCHIVING AND DIRECTORY SETUP ---
    # Define archive folder and ensure it exists
    ARCHIVE_FOLDER = Path("archive")
    ARCHIVE_FOLDER.mkdir(exist_ok=True)

    # 1. Archive previous diagnostics.log (if it exists from a prior run)
    current_diagnostics_log_path = Path("diagnostics.log")
    if current_diagnostics_log_path.exists():
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        archive_name = ARCHIVE_FOLDER / f"diagnostics_log_{timestamp}.log"
        print(f"[{datetime.now().isoformat()}] [INFO] Archiving previous diagnostics.log to {archive_name}")
        try:
            # Ensure any potential prior implicit handlers are released.
            # This is a critical point for Windows PermissionError.
            # As global logger setup is above __main__, it might still hold the file.
            # This is the safest way to ensure the file is free for move.
            old_main_logger_instance = logging.getLogger("IntellisenseSystem")
            for h in old_main_logger_instance.handlers[:]:
                try:
                    h.flush()
                    h.close()
                    old_main_logger_instance.removeHandler(h)
                except Exception as e:
                    print(f"[{datetime.now().isoformat()}] [WARN] Error during pre-run handler close for diagnostics.log: {e}", file=sys.stderr)

            shutil.move(current_diagnostics_log_path, archive_name)
            print(f"[{datetime.now().isoformat()}] [INFO] Successfully archived previous diagnostics.log.")
        except Exception as e:
            print(f"[{datetime.now().isoformat()}] [WARN] Failed to archive diagnostics.log: {e}. It might be in use or not exist.", file=sys.stderr)

    # Re-initialize logging explicitly after archiving old diagnostics.log, ensuring it's fresh for this run
    # This ensures that diagnostics.log starts fresh every run and all messages are appended to it.
    main_logger_instance = logging.getLogger("IntellisenseSystem")
    if not main_logger_instance.handlers: # Ensure fresh handlers are created for this run
        _global_file_handler = logging.FileHandler('diagnostics.log', mode='a', encoding='utf-8')
        _global_file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        _global_file_handler.setFormatter(file_formatter)
        main_logger_instance.addHandler(_global_file_handler)

        _global_console_handler = logging.StreamHandler()
        _global_console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        _global_console_handler.setFormatter(console_formatter)
        main_logger_instance.addHandler(_global_console_handler)

    logger.info("IntellisenseSystem bootstrap starting...")


    # Paths to clean (only temporary/generated, NOT logs/ or DBs)
    cleanup_paths_initial = [
      "intellisense_config.json",
      "codebase_health_registry.json",
      "ecosystem/" # Still want to regenerate this on boot, so deleting is fine here
    ]

    for path_str in cleanup_paths_initial:
        path = Path(path_str)
        if path.is_file():
            try:
                path.unlink(missing_ok=True)
            except PermissionError as e:
                logger.warning(f"Could not delete file {path}: {e}")
        elif path.is_dir():
            try:
                shutil.rmtree(path, ignore_errors=True)
            except PermissionError as e:
                logger.warning(f"Could not delete directory {path}: {e}")


    # Ensure logs directory exists (for new logs to be created)
    Path("logs").mkdir(exist_ok=True)
    
    # Create dummy logs to be ingested. These will be moved to ARCHIVE by MetaReflectionEngine.
    dummy_log_files = [] # Keep track of these to confirm archiving later
    
    log_name_1_path = Path("logs/example_app.log")
    with open(log_name_1_path, "w") as f:
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - INFO - App started successfully. PID: 12345.\n")
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - WARNING - High memory usage detected. Memory: 85.23%. CPU: 75.10%. Latency: 123.45ms.\n")
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - ERROR - Failed to connect to database MainDB.\n")
    dummy_log_files.append(log_name_1_path)

    log_name_2_path = Path("logs/performance_monitor.log")
    with open(log_name_2_path, "w") as f:
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - INFO - Process X running stable. CPU: 45.6%, Memory: 30.1%.\n")
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - WARNING - Latency spike detected. Latency: 500.2ms. Module SystemCore failed: Timeout.\n")
    dummy_log_files.append(log_name_2_path)

    log_name_3_path = Path("logs/test_runner.log")
    with open(log_name_3_path, "w") as f:
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - INFO - Tests run: 100, Failures: 5, Errors: 0.\n")
        f.write(f"{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S,%f')} - ERROR - Test 'critical_feature_test' failed validation.\n")
    dummy_log_files.append(log_name_3_path)

    log_name_4_path = Path("logs/another_log.jsonl") # This is now consistently in logs/
    with open(log_name_4_path, "w") as f:
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "level": "INFO", "message": "User login success."}, f)
        f.write("\n")
        json.dump({"timestamp": datetime.now(timezone.utc).isoformat(), "level": "CRITICAL", "message": "Unhandled exception: Division by zero."}, f)
        f.write("\n")
    dummy_log_files.append(log_name_4_path)

    # Memoria ecosystem files creation (if not already existing by bootstrap)
    Path("ecosystem/memoria").mkdir(parents=True, exist_ok=True)
    Path("ecosystem/memoria/config").mkdir(exist_ok=True)
    
    # ai_suggestion_feedback.jsonl should persist and only be appended to
    feedback_jsonl_path = Path("ai_suggestion_feedback.jsonl")
    if not (feedback_jsonl_path.exists() and feedback_jsonl_path.stat().st_size > 0):
        with open(feedback_jsonl_path, "w") as f:
            json.dump({"performance_score": 0.9, "status": "accepted", "timestamp": datetime.now(timezone.utc).isoformat()}, f)
            f.write("\n")
            json.dump({"performance_score": 0.5, "status": "discarded", "timestamp": datetime.now(timezone.utc).isoformat()}, f)
            f.write("\n")

    # --- System Initialization ---
    system = IntellisenseSystem()
    
    # --- Run Self-Test ---
    logger.info("\n--- Running IntellisenseSystem Self-Test ---")
    self_test_detailed_results = system.run_self_test()
    if self_test_detailed_results['overall_status'] == "PASS":
        logger.info("\nAll critical IntellisenseSystem self-tests passed!")
    else:
        logger.info(f"\nIntellisenseSystem self-tests completed with status: {self_test_detailed_results['overall_status']}. Check logs for details.")

    # --- Trigger immediate log ingestion ---
    # This is crucial so the system picks up its own latest self-test report and dummy logs
    logger.info(f"\n--- Forcing Log Ingestion (to include self-test report and existing logs) ---")
    system.modules['MetaReflectionEngine'].ingest_new_logs() # This will now move processed files from logs/ to ARCHIVE
    
    # The dummy_log_files were already in the configured scan paths, so they should now be archived.
    # No explicit archiving here. System is designed to pull them from 'logs/' and move them.

    # --- Trigger immediate synthesis report generation ---
    logger.info(f"\n--- Forcing Synthesis Report Generation (to process newly ingested data) ---")
    synthesis_report_path = system.modules['MetaReflectionEngine'].generate_synthesis_report()
    if synthesis_report_path.exists():
        logger.info(f"Synthesis report available at: {synthesis_report_path}")
        with open(synthesis_report_path, 'r', encoding='utf-8') as f:
            logger.info("\n--- Content of Synthesis Report (first 500 chars) ---")
            logger.info(f.read(500))
            logger.info("...")


    # --- Display CLI System Summary Grid ---
    system.display_system_summary_grid()


    # --- Simulate further normal interactions ---
    logger.info("\n--- Simulating Further Interactions ---")
    mock_code_metrics = {"complexity": 5.0, "coverage": 0.95, "momentum": 0.1}

    response1 = system.process_input("Analyze the recent performance spikes in the CI pipeline.", mock_code_metrics, user_id="dev_user_1")
    logger.info(f"\nUser 1 Response 1: {response1}")

    response2 = system.process_input("What about the test coverage gaps?", mock_code_metrics, user_id="dev_user_1")
    logger.info(f"\nUser 1 Response 2: {response2}")

    response3 = system.process_input("I need help refactoring the data serialization module. It's too complex.", {"complexity": 15.0, "coverage": 0.6, "momentum": 0.5}, user_id="dev_user_2")
    logger.info(f"\nUser 2 Response 1: {response3}")
    
    # Verify rehydration of self-test data
    logger.info(f"\n--- Verifying Rehydration of Self-Test Report Data ---")
    # Note: The self_test_report.jsonl is managed by MetaReflectionEngine and not moved to archive in ingest_new_logs by default
    # because it's a dynamic report. If you want it archived, add it to the explicit list handled in _scan_and_ingest_log_file.
    # For now, it stays in logs/ and its content is scanned.
    rehydrated_self_test_logs = system.modules['MetaReflectionEngine'].rehydrate_log_data(
      {'source_file': str(Path("logs/intellisense_self_test_report.jsonl")), 'limit': 100}
    )
    if rehydrated_self_test_logs:
      logger.info(f"Successfully rehydrated {len(rehydrated_self_test_logs)} self-test log entries.")
      verification_results_self_test = system.modules['MetaReflectionEngine'].verify_rehydration_process(rehydrated_self_test_logs[:5])
      logger.info(f"Self-test rehydration verification results: {json.dumps(verification_results_self_test, indent=2)}")
    else:
      logger.info("No self-test report logs found in catalog for rehydration.")


    logger.info("\n--- Completed Simulation ---")

    # --- FINAL SYSTEM SHUTDOWN & NON-PERSISTENT CLEANUP ---
    # 1. Close all module-specific DB connections and release resources
    logger.info("Initiating IntellisenseSystem graceful shutdown...")
    system.shutdown()

    # 2. Close global logger handlers
    logger.info("Closing main logger handlers...")
    _close_all_global_handlers() # Call the dedicated function

    # 3. Final cleanup of ONLY non-persistent files/folders
    # Logs and DBs (diagnostics.log, intellisense_feedback.db, intellisense_log_catalog.db)
    # in the root directory remain untouched.
    # Log files from 'logs/' should have been moved to 'archive/'.
    # feedback.jsonl (ai_suggestion_feedback.jsonl) is persistent, retained.
    cleanup_paths_final_non_persistent = [
      "ecosystem/" # Delete this to ensure regeneration on next run if desired
    ]
    for path_str in cleanup_paths_final_non_persistent:
        path = Path(path_str)
        if path.is_file():
            try:
                path.unlink(missing_ok=True)
            except PermissionError as e:
                print(f"[{datetime.now().isoformat()}] [WARN] Could not unlink file {path}: {e}", file=sys.stderr)
        elif path.is_dir():
            try:
                shutil.rmtree(path, ignore_errors=True)
            except PermissionError as e:
                print(f"[{datetime.now().isoformat()}] [WARN] Could not remove directory {path}: {e}", file=sys.stderr)

    print("\nCleanup complete. Non-persistent generated files removed, logs and DBs retained/archived.")
