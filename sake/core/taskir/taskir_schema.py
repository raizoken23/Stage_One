# sake/core/taskir/taskir_schema.py
#
#
# ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                  **CITADEL GOVERNANCE & METADATA TEMPLATE (CGMT) v1.0**                                                ║
# ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
# ║                                                                                                                    ║
# ║   **FILE:**         taskir_schema.py                                                                               ║
# ║   **COMPONENT:**    TaskIR Schema Definition (Kousaki)                                                             ║
# ║   **ARCHETYPE:**    SCHEMA                                                                                         ║
# ║   **VERSION:**      1.0.0                                                                                          ║
# ║   **STATUS:**       Canonical                                                                                      ║
# ║   **CREATED:**      2025-09-14                                                                                     ║
# ║   **LAST_UPDATE:**  2025-09-14                                                                                     ║
# ║   **AUTHOR:**       Jules (AI Software Engineer)                                                                   ║
# ║                                                                                                                    ║
# ║   **PURPOSE:**                                                                                                     ║
# ║     This file defines the canonical Pydantic schema for the 13-block TaskIR (Task Intermediate                     ║
# ║     Representation). The TaskIR is a language-agnostic, structured representation of a task that                   ║
# ║     captures its intent, logic, contracts, and tests. It is the core payload of a SAKE envelope.                   ║
# ║                                                                                                                    ║
# ║   **REFERENCE:**                                                                                                   ║
# ║     - SAKE Ecosystem Documentation by Kousaki & Dmitry                                                             ║
# ║     - DKA-002 (Canonical Schemas & Centralized Management)                                                         ║
# ║                                                                                                                    ║
# ╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

# --- IMPORTS ---
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional

try:
    from pydantic import BaseModel, Field
except ImportError:
    print("Pydantic not found. Please install: pip install pydantic")
    # Provide a mock for environments where Pydantic isn't installed.
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump_json(self, indent=None):
            import json
            return json.dumps(self.__dict__, indent=indent)

# --- TASKIR SUB-MODELS ---
# These models define the structure of the individual blocks within the TaskIR.

class IOSpec(BaseModel):
    """Defines the input and output parameters of a task."""
    name: str = Field(..., description="The name of the input or output parameter.")
    type: str = Field(..., description="The expected data type (e.g., 'path', 'str', 'int', 'dict').")
    description: Optional[str] = Field(None, description="A brief description of the parameter.")

class ContractSpec(BaseModel):
    """Defines a specific contract or guarantee the task must fulfill."""
    contract_type: str = Field(..., description="The type of contract, e.g., 'result_contains_keys', 'file_exists'.")
    details: Dict[str, Any] = Field(..., description="The specific details of the contract to be validated.")

class TestSpec(BaseModel):
    """Defines a single test case for the task."""
    case_name: str = Field(..., description="A unique name for the test case.")
    description: Optional[str] = Field(None, description="A description of what the test case covers.")
    inputs: Dict[str, Any] = Field(..., description="A dictionary of inputs for this test case.")
    expected_outcome: Dict[str, Any] = Field(..., description="A dictionary describing the expected results to assert against.")

class RuntimeHint(BaseModel):
    """Provides hints to the execution environment about how to run the task."""
    hint_name: str = Field(..., description="The name of the hint, e.g., 'batch_size', 'device_preference'.")
    value: Any = Field(..., description="The value of the hint.")

class MetricSpec(BaseModel):
    """Defines a performance or quality metric to be measured."""
    metric_name: str = Field(..., description="The name of the metric, e.g., 'SLA_ms', 'max_mem_mb'.")
    target: float = Field(..., description="The target value for the metric.")
    operator: str = Field("<=", description="The comparison operator (e.g., '<=', '>=', '==').")

class StateSpec(BaseModel):
    """Defines metadata about the TaskIR's version and ownership."""
    version: str = Field(..., description="The version of the TaskIR spec (e.g., 'r8', '1.2.0').")
    owner: str = Field(..., description="The team or agent responsible for this task, e.g., 'ops/reflex'.")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)

# --- THE CANONICAL 13-BLOCK TASKIR SCHEMA ---
class TaskIR(BaseModel):
    """
    The TaskIR (Task Intermediate Representation) schema by Kousaki.
    This is a language-agnostic, 13-block structure that captures the full
    semantic essence of a unit of work.
    """
    # Block 1: Identification
    task_name: str = Field(..., description="A unique, machine-readable name for the task, e.g., 'image_dedup_v2'.")

    # Block 2: Intent
    intent: str = Field(..., description="A clear, human-readable description of the task's purpose and goal.")

    # Block 3: Inputs
    inputs: List[IOSpec] = Field(..., description="A list of all required input parameters for the task.")

    # Block 4: Outputs
    outputs: List[IOSpec] = Field(..., description="A list of all expected outputs produced by the task.")

    # Block 5: Algorithm
    algorithm: str = Field(..., description="A high-level, human-readable description of the method or process used to accomplish the task.")

    # Block 6: Pseudocode (Optional but Recommended)
    pseudocode: Optional[str] = Field(None, description="A more detailed, step-by-step description of the algorithm in a structured, code-like format.")

    # Block 7: Constraints
    constraints: List[str] = Field([], description="A list of rules or limitations that the task must operate under, e.g., 'must be deterministic', 'no network calls'.")

    # Block 8: Contracts
    contracts: List[ContractSpec] = Field([], description="A list of explicit, verifiable guarantees about the task's behavior or results.")

    # Block 9: Tests
    tests: List[TestSpec] = Field(..., description="A list of test cases that can be used to verify the correctness of the task's implementation.")

    # Block 10: Runtime Hints
    runtime_hints: List[RuntimeHint] = Field([], description="A list of non-binding suggestions for the execution environment, e.g., preferred batch size.")

    # Block 11: Metrics
    metrics: List[MetricSpec] = Field([], description="A list of Service Level Objectives (SLOs) or performance targets for the task.")

    # Block 12: Artifacts
    artifacts: List[str] = Field([], description="A list of file paths for any additional files that are generated or required by the task, e.g., 'dedup_report.md'.")

    # Block 13: State & Notes
    state: StateSpec = Field(..., description="Metadata about the TaskIR itself, including version and ownership.")
    notes: Optional[str] = Field(None, description="Free-form text for additional context, developer notes, or documentation links.")

    class Config:
        title = "Citadel TaskIR Schema"
        json_schema_extra = {
            "example": {
                "task_name": "image_deduplication",
                "intent": "Find and remove near-duplicate images from a specified directory.",
                "inputs": [{"name": "images_dir", "type": "path", "description": "Directory containing images to process."}],
                "outputs": [{"name": "manifest_json", "type": "path", "description": "JSON file listing kept and removed images."}],
                "algorithm": "Compute perceptual hashes for all images, find clusters of images with a Hamming distance below a threshold, and keep only one image from each cluster.",
                "pseudocode": "for img in images_dir:\n  hash = pHash(img)\n  ... (etc)",
                "constraints": ["must be deterministic on same inputs", "no network calls during processing"],
                "contracts": [{"contract_type": "result_contains_keys", "details": {"keys": ["kept_files", "removed_files"]}}],
                "tests": [{"case_name": "five_images_two_dups", "inputs": {"images_dir": "/test/data/5_imgs"}, "expected_outcome": {"removed_count": 2}}],
                "runtime_hints": [{"hint_name": "batch_size", "value": 128}],
                "metrics": [{"metric_name": "SLA_ms_per_100_images", "target": 5000, "operator": "<="}],
                "artifacts": ["deduplication_report.md"],
                "state": {"version": "1.0.0", "owner": "citadel/media-ops"},
                "notes": "Uses the pHash algorithm. Threshold is configurable via runtime hints."
            }
        }

# --- SELF-TEST BLOCK ---
if __name__ == "__main__":
    """
    This block demonstrates the usage of the TaskIR schema and validates
    that the example provided in the schema itself is compliant.
    """
    print("="*50)
    print("Validating TaskIR Schema against its own example...")
    print("="*50)

    example_data = TaskIR.Config.json_schema_extra["example"]

    try:
        # Create a TaskIR instance from the example data
        task_ir_instance = TaskIR(**example_data)

        print("Validation Successful! The example data conforms to the TaskIR schema.")
        print("\n--- Example TaskIR Instance (JSON) ---")
        print(task_ir_instance.model_dump_json(indent=2))
        print("------------------------------------")

        # Further validation checks
        assert task_ir_instance.task_name == "image_deduplication"
        assert len(task_ir_instance.tests) == 1
        assert task_ir_instance.tests[0].case_name == "five_images_two_dups"
        assert task_ir_instance.state.owner == "citadel/media-ops"

        print("\nField access and data integrity checks passed.")

    except Exception as e:
        print(f"Validation FAILED: {e}")

    print("="*50)
    print("TaskIR Schema Self-Test Finished.")
    print("="*50)
