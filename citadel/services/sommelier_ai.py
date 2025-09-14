# citadel/services/sommelier_ai.py
#
#
# ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                  **CITADEL GOVERNANCE & METADATA TEMPLATE (CGMT) v1.0**                                                ║
# ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
# ║                                                                                                                    ║
# ║   **FILE:**         sommelier_ai.py                                                                                ║
# ║   **AGENT:**        SommelierAI                                                                                    ║
# ║   **ARCHETYPE:**    CURATOR / TRAINER                                                                              ║
# ║   **VERSION:**      0.1.0 (Stub)                                                                                   ║
# ║   **STATUS:**       Conceptual                                                                                     ║
# ║   **CREATED:**      2025-09-14                                                                                     ║
# ║   **LAST_UPDATE:**  2025-09-14                                                                                     ║
# ║   **AUTHOR:**       Jules (AI Software Engineer)                                                                   ║
# ║                                                                                                                    ║
# ║   **PURPOSE:**                                                                                                     ║
# ║     This file defines the `SommelierAI` agent and the `ZayaraManagedService`. Together, they form the              ║
# ║     "Zayara Proving Ground," a system for automatically fine-tuning, benchmarking, and managing a                  ║
# ║     stable of specialized LLMs for the Citadel ecosystem.                                                          ║
# ║                                                                                                                    ║
# ║   **REFERENCE:**                                                                                                   ║
# ║     - FEATURES.md, Feature 3: The "Zayara Proving Ground" for Automated Fine-Tuning                                ║
# ║     - DKA-001 (VDS as Universal Knowledge Substrate)                                                               ║
# ║     - OGA-004 (Continuous Learning & Adaptation via VDS Feedback Loops)                                            ║
# ║                                                                                                                    ║
# ╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝


# --- IMPORTS ---
import json
import logging
import subprocess
import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Core dependencies for schema validation, API interaction, and model downloading
try:
    from pydantic import BaseModel, Field
except ImportError:
    print("Pydantic not found. Please install: pip install pydantic")
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump_json(self, indent=None):
            import json
            return json.dumps(self.__dict__, indent=indent)

try:
    from huggingface_hub import snapshot_download
except ImportError:
    print("huggingface_hub not found. Please install: pip install huggingface_hub")
    snapshot_download = None

# Mock imports for other Citadel components this service would interact with
# In a real system, these would be proper client libraries provided by the CitadelHub.
class MockVDSClient:
    def query(self, query: str) -> List[Dict[str, Any]]:
        print(f"MOCK VDS QUERY: {query}")
        return [{"log_content": "Error in module X", "metadata": {}}, {"log_content": "User feedback: great suggestion", "metadata": {}}]

class MockJanusAI:
    def create_benchmark_environment(self, model_path: Path):
        print(f"MOCK JANUSAI: Creating benchmark environment for model {model_path}")
        return "twin-benchmark-123"
    def run_benchmark_scenario(self, env_id: str):
        print(f"MOCK JANUSAI: Running benchmark scenario in {env_id}")
        return {"accuracy": 0.95, "tps": 50.5}
    def destroy_environment(self, env_id: str):
        print(f"MOCK JANUSAI: Destroying environment {env_id}")

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger("SommelierAI")


# --- ENUMERATIONS ---
class FineTuningJobStatus(str, Enum):
    PENDING = "PENDING"
    PREPARING_DATA = "PREPARING_DATA"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class ModelLifecycleStatus(str, Enum):
    EXPERIMENTAL = "EXPERIMENTAL"       # Newly fine-tuned, awaiting benchmark
    BENCHMARKING = "BENCHMARKING"       # Currently undergoing benchmark tests
    STAGING = "STAGING"                 # Passed benchmarks, ready for promotion
    PRODUCTION = "PRODUCTION"           # The active, best-performing model for a task
    DEPRECATED = "DEPRECATED"           # Outperformed by a newer model
    ARCHIVED = "ARCHIVED"               # No longer in use, files may be offloaded

class BenchmarkDimension(str, Enum):
    """Dimensions for evaluating model performance."""
    ACCURACY = "ACCURACY"
    LATENCY = "LATENCY"
    TOKENS_PER_SECOND = "TOKENS_PER_SECOND"
    INFERENCE_COST = "INFERENCE_COST" # e.g., GPU memory usage

class TuningCostFactor(str, Enum):
    """Factors contributing to the cost of a fine-tuning job."""
    GPU_HOURS = "GPU_HOURS"
    DATASET_SIZE_MB = "DATASET_SIZE_MB"
    MODEL_PARAMETERS_BILLIONS = "MODEL_PARAMETERS_BILLIONS"


# --- PYDANTIC SCHEMAS ---
class FineTuningConfig(BaseModel):
    """Configuration for a single fine-tuning job."""
    base_model_repo: str = Field("Qwen/Qwen2.5-Coder-7B-Instruct-GGUF", description="The Hugging Face repo of the base model.")
    dataset_path: Path = Field(..., description="Path to the training dataset file (.jsonl).")
    hyperparameters: Dict[str, Any] = Field({
        "learning_rate": 2e-5,
        "epochs": 3,
        "lora_r": 8,
        "lora_alpha": 16,
    }, description="Key-value pairs for fine-tuning hyperparameters.")

class FineTuningJob(BaseModel):
    """Represents and tracks a single fine-tuning task."""
    job_id: str = Field(default_factory=lambda: f"ftj-{uuid.uuid4().hex[:8]}")
    status: FineTuningJobStatus = Field(FineTuningJobStatus.PENDING)
    config: FineTuningConfig
    submitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    output_model_path: Optional[Path] = None
    job_logs: List[str] = []
    job_cost: Optional[float] = Field(None, description="Calculated MDAO cost score for the tuning job.")

class BenchmarkMetrics(BaseModel):
    """Stores the results of a model benchmark."""
    scores: Dict[BenchmarkDimension, float] = Field({}, description="Scores for each benchmark dimension.")
    report_url: Optional[str] = None # Link to a detailed report from JanusAI

class ManagedModel(BaseModel):
    """Represents a model in the SommelierAI's stable."""
    model_id: str = Field(default_factory=lambda: f"model-{uuid.uuid4().hex[:8]}")
    model_path: Path
    base_model: str
    fine_tuning_job_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    lifecycle_status: ModelLifecycleStatus = ModelLifecycleStatus.EXPERIMENTAL
    benchmark_results: Optional[BenchmarkMetrics] = None
    fine_tuning_roi: Optional[float] = Field(None, description="MDAO-calculated Return on Investment for this model.")


# --- MDAO FORMULARY ---
class MDAO_Formulary:
    """Houses MDAO formulas for the model fine-tuning process."""

    @staticmethod
    def calculate_tuning_cost(job: FineTuningJob) -> float:
        """
        Calculates a cost score for a fine-tuning job.
        Worst case: Large model, large dataset, many hours -> High cost.
        Best case: Small model, small dataset, few hours -> Low cost.
        """
        cost_weights = {
            TuningCostFactor.GPU_HOURS: 10.0,
            TuningCostFactor.DATASET_SIZE_MB: 0.1,
            TuningCostFactor.MODEL_PARAMETERS_BILLIONS: 5.0,
        }

        # These would be measured during the actual fine-tuning process.
        # For this stub, we'll use estimates based on the config.
        estimated_gpu_hours = job.config.hyperparameters.get("epochs", 3) * 2 # Mock: 2 hours per epoch
        dataset_size_mb = job.config.dataset_path.stat().st_size / (1024 * 1024) if job.config.dataset_path.exists() else 0
        model_params_b = 7 # For a 7B model

        cost = (
            estimated_gpu_hours * cost_weights[TuningCostFactor.GPU_HOURS] +
            dataset_size_mb * cost_weights[TuningCostFactor.DATASET_SIZE_MB] +
            model_params_b * cost_weights[TuningCostFactor.MODEL_PARAMETERS_BILLIONS]
        )
        return round(cost, 4)

    @staticmethod
    def calculate_finetuning_roi(
        base_model_metrics: BenchmarkMetrics,
        tuned_model_metrics: BenchmarkMetrics,
        tuning_cost: float
    ) -> float:
        """
        Calculates the Return on Investment (ROI) for a fine-tuning job.
        Compares the performance gain against the tuning cost.
        """
        if tuning_cost == 0:
            return float('inf') # Avoid division by zero

        gain_weights = {
            BenchmarkDimension.ACCURACY: 100.0, # High importance
            BenchmarkDimension.TOKENS_PER_SECOND: 10.0,
            BenchmarkDimension.LATENCY: -5.0, # Negative because lower is better
            BenchmarkDimension.INFERENCE_COST: -20.0, # Negative because lower is better
        }

        total_gain = 0.0
        for dim, tuned_score in tuned_model_metrics.scores.items():
            base_score = base_model_metrics.scores.get(dim, 0)
            # Calculate relative improvement
            if base_score != 0:
                improvement = (tuned_score - base_score) / base_score
            else:
                improvement = tuned_score # If base was 0, any gain is infinite; simplify to just the score.

            total_gain += improvement * gain_weights.get(dim, 0.0)

        roi = (total_gain - tuning_cost) / tuning_cost
        return round(roi, 4)


# --- SERVICES ---
class ZayaraManagedService:
    """
    An abstraction layer over the `zayara.py` logic.
    Manages the lifecycle of a local LLM instance for training and serving.
    """
    def __init__(self, models_root: Path, binaries_root: Path):
        self.models_root = models_root
        self.binaries_root = binaries_root
        self.models_root.mkdir(parents=True, exist_ok=True)
        self.binaries_root.mkdir(parents=True, exist_ok=True)
        self.active_server_process: Optional[subprocess.Popen] = None
        logger.info(f"ZayaraManagedService initialized. Models at: {self.models_root}")

    def health_check(self) -> Dict[str, Any]:
        server_running = self.active_server_process and self.active_server_process.poll() is None
        return {
            "status": "HEALTHY" if server_running else "DEGRADED",
            "active_server_pid": self.active_server_process.pid if server_running else None,
            "models_root_exists": self.models_root.exists(),
            "binaries_root_exists": self.binaries_root.exists(),
        }

    def download_model(self, repo_id: str, allow_patterns: List[str]) -> Path:
        """Downloads a model from Hugging Face."""
        if not snapshot_download:
            raise ImportError("huggingface_hub is required to download models.")
        logger.info(f"[F724:MODEL_DOWNLOAD_START] Downloading model '{repo_id}' with patterns {allow_patterns}...")
        local_dir = self.models_root / repo_id.replace("/", "_")
        try:
            downloaded_path = snapshot_download(
                repo_id=repo_id,
                allow_patterns=allow_patterns,
                local_dir=local_dir,
                local_dir_use_symlinks=False # Use copies for stability
            )
            logger.info(f"[F724:MODEL_DOWNLOAD_SUCCESS] Model downloaded successfully to {downloaded_path}")
            return Path(downloaded_path)
        except Exception as e:
            logger.error(f"[F724:MODEL_DOWNLOAD_FAILURE] Failed to download model {repo_id}: {e}")
            raise

    def run_fine_tuning(self, job: FineTuningJob) -> Path:
        """
        (Stub) Runs the fine-tuning process.
        This would invoke a training script like `train.py` from llama.cpp or `transformers`.
        """
        logger.info(f"[F724:MODEL_TRAINING_START] Starting fine-tuning job: {job.job_id}")

        # --- Placeholder Logic ---
        # 1. Locate the training script.
        # 2. Construct the command with hyperparameters from job.config.
        # 3. Launch the subprocess and stream logs.

        # Simulate a long-running process
        logger.info("Simulating fine-tuning process... (this would take hours in reality)")
        job.job_logs.append("[F724:LEARNING_CYCLE_START] Starting training script...")
        time.sleep(5)
        job.job_logs.append("Epoch 1/3 completed. Loss: 0.87")
        time.sleep(5)
        job.job_logs.append("Epoch 2/3 completed. Loss: 0.65")
        time.sleep(5)
        job.job_logs.append("Epoch 3/3 completed. Loss: 0.58")
        time.sleep(2)
        job.job_logs.append("[F724:LEARNING_CYCLE_END] Training complete. Saving adapter model...")

        # Create a dummy adapter/model file
        output_model_dir = self.models_root / job.job_id
        output_model_dir.mkdir(exist_ok=True)
        output_model_path = output_model_dir / "adapter_model.safetensors"
        output_model_path.touch()

        logger.info(f"[F724:MODEL_TRAINING_SUCCESS] Fine-tuning job {job.job_id} complete. Output at: {output_model_path}")
        return output_model_path

    def start_service(self, model_path: Path) -> bool:
        """(Stub) Starts a llama-server instance for the given model."""
        if self.active_server_process:
            logger.warning("An active server is already running. Please stop it first.")
            return False

        server_binary = self.binaries_root / "llama-server"
        if not server_binary.exists():
            logger.error(f"llama-server binary not found at {server_binary}")
            return False

        cmd = [
            str(server_binary),
            "--model", str(model_path),
            "--port", "8088", # Use a non-default port for the proving ground
            "--n-gpu-layers", "32" # Example argument
        ]
        logger.info(f"[F721:LLM_API_CALL_START] Starting model server: {' '.join(cmd)}")
        try:
            self.active_server_process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            # In a real system, we'd wait for a health check endpoint.
            time.sleep(10)
            logger.info(f"[F721:LLM_API_CALL_SUCCESS] Model server started with PID: {self.active_server_process.pid}")
            return True
        except Exception as e:
            logger.error(f"[F721:LLM_API_CALL_FAILURE] Failed to start model server: {e}")
            return False

    def stop_service(self):
        """Stops the active llama-server instance."""
        if self.active_server_process:
            logger.info(f"Stopping model server with PID: {self.active_server_process.pid}")
            self.active_server_process.terminate()
            try:
                self.active_server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.active_server_process.kill()
            self.active_server_process = None
            logger.info("Model server stopped.")


class SommelierAI:
    """
    The SommelierAI Agent: Curates and improves LLMs for the Citadel.
    """
    def __init__(self, citadel_hub: Optional[Any] = None, models_root: Path = Path("./zayara_proving_ground")):
        self.citadel_hub = citadel_hub
        self.service = ZayaraManagedService(
            models_root=models_root / "models",
            binaries_root=models_root / "bin"
        )
        # In a real system, these clients would be provided by the CitadelHub
        self.vds_client = MockVDSClient()
        self.janus_client = MockJanusAI()
        self.mdao_formulary = MDAO_Formulary()

        self.model_registry: Dict[str, ManagedModel] = {}
        self.active_jobs: Dict[str, FineTuningJob] = {}
        logger.info("SommelierAI Agent is online. Ready to manage the model stable.")

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "HEALTHY",
            "managed_service_health": self.service.health_check(),
            "active_fine_tuning_jobs": len(self.active_jobs),
            "models_in_registry": len(self.model_registry),
            "srs_compliance": "F72x Series Integrated"
        }

    def create_dataset_from_vds(self, query: str, output_path: Path) -> Path:
        """
        Queries the VDS for relevant data and formats it into a fine-tuning dataset.
        """
        logger.info(f"[F724:KNOWLEDGE_EXTRACTION_START] Creating dataset from VDS with query: '{query}'")
        job_status = self.active_jobs.get(list(self.active_jobs.keys())[-1])
        if job_status:
            job_status.status = FineTuningJobStatus.PREPARING_DATA

        # 1. Query VDS
        vds_records = self.vds_client.query(query)

        # 2. Transform records into instruction/response format
        dataset = []
        for record in vds_records:
            # This logic is highly dependent on the data schema in the VDS
            instruction = record.get("metadata", {}).get("prompt", "Analyze this:")
            response = record.get("log_content", "")
            dataset.append({"instruction": instruction, "response": response})

        # 3. Save to .jsonl file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open('w', encoding='utf-8') as f:
            for item in dataset:
                f.write(json.dumps(item) + "\n")

        logger.info(f"[F724:KNOWLEDGE_EXTRACTION_SUCCESS] Successfully created dataset with {len(dataset)} entries at {output_path}")
        return output_path

    def submit_fine_tuning_job(self, config: FineTuningConfig) -> str:
        """Submits and starts a new fine-tuning job."""
        job = FineTuningJob(config=config)
        self.active_jobs[job.job_id] = job
        logger.info(f"[F724:LEARNING_EVENT] Submitted new fine-tuning job: {job.job_id}")

        # In a real system, this would run asynchronously
        self._run_job(job.job_id)

        return job.job_id

    def _run_job(self, job_id: str):
        """(Private) The core logic for executing a job."""
        job = self.active_jobs[job_id]
        job.status = FineTuningJobStatus.RUNNING

        try:
            # This is a synchronous call for the stub's simplicity
            output_path = self.service.run_fine_tuning(job)
            job.output_model_path = output_path
            job.status = FineTuningJobStatus.COMPLETED
            job.completed_at = datetime.now(timezone.utc)
            job.job_cost = self.mdao_formulary.calculate_tuning_cost(job)
            logger.info(f"[F991:SCORE] Calculated tuning cost for job {job.job_id}: {job.job_cost}")

            # Register the new model
            new_model = ManagedModel(
                model_path=job.output_model_path,
                base_model=job.config.base_model_repo,
                fine_tuning_job_id=job.job_id
            )
            self.model_registry[new_model.model_id] = new_model
            logger.info(f"New model {new_model.model_id} registered from completed job {job.job_id}")

        except Exception as e:
            logger.error(f"[F724:MODEL_TRAINING_FAILURE] Fine-tuning job {job_id} failed: {e}")
            job.status = FineTuningJobStatus.FAILED
            job.job_logs.append(f"FATAL ERROR: {e}")

    def run_benchmark_on_model(self, model_id: str) -> Optional[BenchmarkMetrics]:
        """Orchestrates benchmarking a model using ZayaraService and JanusAI."""
        if model_id not in self.model_registry:
            logger.error(f"Model ID {model_id} not found in registry.")
            return None

        model = self.model_registry[model_id]
        model.lifecycle_status = ModelLifecycleStatus.BENCHMARKING
        logger.info(f"[F724:MODEL_BENCHMARK_START] Starting benchmark for model: {model_id}")

        # 1. Use JanusAI to create a dedicated, clean benchmark environment
        # This ensures benchmarks are isolated and reproducible.
        benchmark_env_id = self.janus_client.create_benchmark_environment(model.model_path)

        # 2. Run the standardized benchmark scenario
        # This scenario would be defined in the Citadel's testing protocols.
        results = self.janus_client.run_benchmark_scenario(benchmark_env_id)

        # 3. Clean up the environment
        self.janus_client.destroy_environment(benchmark_env_id)

        # 4. Store the results
        # In a real system, results would be more detailed. We mock it here.
        metrics = BenchmarkMetrics(scores={
            BenchmarkDimension.ACCURACY: results.get("accuracy", 0),
            BenchmarkDimension.TOKENS_PER_SECOND: results.get("tps", 0),
            BenchmarkDimension.LATENCY: 1000 / results.get("tps", 1) if results.get("tps") else 500
        })
        model.benchmark_results = metrics
        model.lifecycle_status = ModelLifecycleStatus.STAGING
        logger.info(f"[F724:MODEL_BENCHMARK_SUCCESS] Benchmark for model {model_id} complete. Results: {metrics.model_dump_json()}")
        return metrics

    def promote_model(self, model_id_to_promote: str):
        """Promotes a model to PRODUCTION if its fine-tuning ROI is positive."""
        if model_id_to_promote not in self.model_registry:
            logger.error(f"Cannot promote non-existent model: {model_id_to_promote}")
            return

        candidate_model = self.model_registry[model_id_to_promote]
        if not candidate_model.benchmark_results:
            logger.warning(f"Cannot promote model {model_id_to_promote}: no benchmark results.")
            return

        job = self.active_jobs.get(candidate_model.fine_tuning_job_id)
        if not job or not job.job_cost:
            logger.warning(f"Cannot calculate ROI for {model_id_to_promote}: tuning job or cost not found.")
            return

        # Find current production model to compare against. If none, compare against a default baseline.
        base_metrics = BenchmarkMetrics(scores={
            BenchmarkDimension.ACCURACY: 0.90, # Baseline for a 7B model
            BenchmarkDimension.TOKENS_PER_SECOND: 40.0,
        })
        current_prod_model = next((m for m in self.model_registry.values() if m.lifecycle_status == ModelLifecycleStatus.PRODUCTION), None)
        if current_prod_model and current_prod_model.benchmark_results:
            base_metrics = current_prod_model.benchmark_results

        # Calculate ROI using the MDAO formula
        roi = self.mdao_formulary.calculate_finetuning_roi(base_metrics, candidate_model.benchmark_results, job.job_cost)
        candidate_model.fine_tuning_roi = roi
        logger.info(f"[F991:SCORE] Calculated ROI for model {candidate_model.model_id}: {roi:.2%}")

        if roi > 0:
            logger.info(f"[F723:COGNITIVE_SELF_CORRECTION_APPLIED] Positive ROI detected. Promoting model {candidate_model.model_id}.")
            if current_prod_model:
                current_prod_model.lifecycle_status = ModelLifecycleStatus.DEPRECATED
                logger.info(f"Deprecating old production model: {current_prod_model.model_id}")
            candidate_model.lifecycle_status = ModelLifecycleStatus.PRODUCTION
            logger.info(f"PROMOTING new model to PRODUCTION: {candidate_model.model_id}")
            # In a real system, this would update the ModelSelectorService via the CitadelHub
            # self.citadel_hub.get_service("ModelSelector").set_production_model("code_generation", candidate_model.model_id)
        else:
            logger.info(f"Negative ROI. Candidate model {model_id_to_promote} will not be promoted.")
            candidate_model.lifecycle_status = ModelLifecycleStatus.DEPRECATED


# --- SELF-TEST BLOCK (TSP-MDP-003 Compliance) ---
if __name__ == "__main__":
    """
    This self-test block demonstrates the core workflow of the Zayara Proving Ground.
    """
    logger.info("="*50)
    logger.info("Executing SommelierAI Self-Test & Demonstration (v1.1 with MDAO & SRS)")
    logger.info("="*50)

    # Use a temporary directory for the demonstration
    temp_root = Path("./temp_proving_ground")

    # 1. Instantiate SommelierAI
    sommelier_agent = SommelierAI(models_root=temp_root)

    # 2. Create a mock dataset
    mock_dataset_path = temp_root / "datasets" / "mock_dataset.jsonl"
    mock_dataset_path.parent.mkdir(parents=True, exist_ok=True)
    with mock_dataset_path.open('w') as f:
        f.write(json.dumps({"text": "example"}) + "\n") # Give it some size

    # 3. Submit a fine-tuning job
    ft_config = FineTuningConfig(dataset_path=mock_dataset_path)
    job_id = sommelier_agent.submit_fine_tuning_job(ft_config)

    # 4. Check job and model status
    job = sommelier_agent.active_jobs[job_id]
    if job.status == FineTuningJobStatus.COMPLETED:
        logger.info(f"Job {job_id} completed successfully with calculated cost: {job.job_cost}")
        new_model = next((m for m in sommelier_agent.model_registry.values() if m.fine_tuning_job_id == job_id), None)
        if new_model:
            logger.info(f"New model created: {new_model.model_id} with status {new_model.lifecycle_status}")

            # 5. Run benchmark on the new model
            # We'll mock the results for the self-test
            new_model.benchmark_results = BenchmarkMetrics(scores={
                BenchmarkDimension.ACCURACY: 0.96, # 1% better than baseline
                BenchmarkDimension.TOKENS_PER_SECOND: 45.0, # Better than baseline
            })
            new_model.lifecycle_status = ModelLifecycleStatus.STAGING
            logger.info(f"Mock benchmark complete for model {new_model.model_id}")

            # 6. Attempt to promote the model based on ROI
            sommelier_agent.promote_model(new_model.model_id)

            # 7. Display final state of the model registry
            logger.info("\n" + "-"*50)
            logger.info("Final Model Registry State:")
            for model in sommelier_agent.model_registry.values():
                print(model.model_dump_json(indent=2))
            logger.info("-" * 50)

    else:
        logger.error(f"Job {job_id} failed with status {job.status}")

    # Clean up temporary directory
    import shutil
    shutil.rmtree(temp_root)
    logger.info(f"Cleaned up temporary directory: {temp_root}")

    logger.info("="*50)
    logger.info("SommelierAI Self-Test Finished")
    logger.info("="*50)
