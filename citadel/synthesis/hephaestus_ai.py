# citadel/synthesis/hephaestus_ai.py
#
#
# ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                  **CITADEL GOVERNANCE & METADATA TEMPLATE (CGMT) v1.0**                                                ║
# ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
# ║                                                                                                                    ║
# ║   **FILE:**         hephaestus_ai.py                                                                               ║
# ║   **AGENT:**        HephaestusAI                                                                                   ║
# ║   **ARCHETYPE:**    SYNTHESIZER / BUILDER                                                                          ║
# ║   **VERSION:**      0.3.0 (SAKE Compliant)                                                                         ║
# ║   **STATUS:**       Conceptual                                                                                     ║
# ║   **CREATED:**      2025-09-14                                                                                     ║
# ║   **LAST_UPDATE:**  2025-09-14                                                                                     ║
# ║   **AUTHOR:**       Jules (AI Software Engineer)                                                                   ║
# ║                                                                                                                    ║
# ║   **PURPOSE:**                                                                                                     ║
# ║     This file defines the `HephaestusAI` agent, refactored for SAKE compliance. It is driven by `.sake`             ║
# ║     manifests, interpreting TaskIR blocks to generate code and evaluating synthesis confidence against             ║
# ║     the manifest's CAPS layer.                                                                                     ║
# ║                                                                                                                    ║
# ║   **REFERENCE:**                                                                                                   ║
# ║     - SAKE Ecosystem Documentation by Kousaki & Dmitry                                                             ║
# ║     - FEATURES.md, Feature 2: "CAP-to-Code" Synthesis Engine                                                       ║
# ║                                                                                                                    ║
# ╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝


# --- IMPORTS ---
import logging
import re
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
import uuid
from datetime import datetime, timezone
import hashlib

# Core dependencies for parsing, templating, and schema validation
try:
    import yaml
except ImportError:
    print("PyYAML not found. Please install: pip install pyyaml")
    yaml = None

try:
    from jinja2 import Environment, FileSystemLoader, Template
except ImportError:
    print("Jinja2 not found. Please install: pip install jinja2")
    Environment = None
    Template = None

try:
    from pydantic import BaseModel, Field, ValidationError
except ImportError:
    print("Pydantic not found. Please install: pip install pydantic")
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump(self):
            return self.__dict__
        def model_dump_json(self, indent=None):
            import json
            return json.dumps(self.__dict__, indent=indent)

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger("HephaestusAI")


# --- ENUMERATIONS ---
class CAPClarity(str, Enum):
    CLEAR = "CLEAR"
    AMBIGUOUS = "AMBIGUOUS"
    INCOMPLETE = "INCOMPLETE"

class SynthesisArtifactType(str, Enum):
    AGENT_STUB = "AGENT_STUB"
    TEST_FILE = "TEST_FILE"
    SCHEMA_DEFINITION = "SCHEMA_DEFINITION"
    CONFIGURATION = "CONFIGURATION"


# --- PYDANTIC SCHEMAS for CAP/TaskIR Parsing & Synthesis Reporting ---
# In a real system, these would import from sake.core.taskir.taskir_schema
class TaskIR(BaseModel):
    """A placeholder for the full TaskIR schema for standalone testing."""
    task_name: str
    intent: str
    # Simplified for this stub
    reaction: Dict[str, Any]
    expected_assertions: List[Dict[str, Any]] = []
    payload_schemas: List[Dict[str, Any]] = []


class CAPClarityAnalysis(BaseModel):
    clarity: CAPClarity
    score: float = Field(..., ge=0, le=1)
    issues: List[str] = []

class GeneratedArtifact(BaseModel):
    artifact_type: SynthesisArtifactType
    path: Path
    content_hash: str
    line_count: int

class SynthesisReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"synth-report-{uuid.uuid4().hex[:8]}")
    sake_lid: str
    synthesis_confidence: float
    caps_passed: bool
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    artifacts: List[GeneratedArtifact] = []


# --- MDAO FORMULARY ---
class MDAO_Formulary:
    @staticmethod
    def calculate_synthesis_confidence(clarity_analysis: CAPClarityAnalysis) -> float:
        base_confidence = clarity_analysis.score
        if clarity_analysis.clarity == CAPClarity.AMBIGUOUS:
            base_confidence *= 0.8
        return round(base_confidence, 4)

    @staticmethod
    def evaluate_caps(confidence_score: float, caps_layer: Dict[str, Any]) -> bool:
        return confidence_score >= caps_layer.get("min_confidence", 0.75)


# --- JINJA2 TEMPLATES ---
PYTHON_AGENT_TEMPLATE = """
# Autogenerated by HephaestusAI from SAKE task: {{ taskir.task_name }}
# [F822:CODE_GENERATION_OBJECTIVE]
#
# Intent: {{ taskir.intent }}
#
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel

logger = logging.getLogger("{{ class_name }}")

# --- Schemas (if any) ---
# [F822:SCHEMA_STUB_GENERATED]
{% for schema in schemas %}
class {{ schema.name }}(BaseModel):
    {% for field in schema.fields %}
    {{ field.name }}: {{ field.type }}
    {% endfor %}
{% endfor %}

# --- Agent Class ---
# [F822:AGENT_STUB_GENERATED]
class {{ class_name }}:
    def __init__(self, citadel_hub: Optional[Any] = None):
        self.citadel_hub = citadel_hub
        logger.info("{{ class_name }} initialized.")

    {% for method in methods %}
    def {{ method.name }}(self, {% for arg in method.args %}{{ arg.name }}: {{ arg.type}}{% if not loop.last %}, {% endif %}{% endfor %}) -> {{ method.return_type }}:
        logger.info(f"Method '{{ method.name }}' invoked.")
        # TODO: Implement business logic to fulfill assertions.
        return None
    {% endfor %}
"""

PYTEST_FILE_TEMPLATE = """
# Autogenerated by HephaestusAI from SAKE task: {{ taskir.task_name }}
# [F823:TEST_STUB_GENERATED]
import pytest
from unittest.mock import MagicMock

# TODO: Adjust the import path as needed
from citadel.agents.{{ agent_filename }} import {{ agent_class_name }}

@pytest.fixture
def {{ agent_instance_name }}(mock_citadel_hub):
    return {{ agent_class_name }}(citadel_hub=mock_citadel_hub)

{% for test in tests %}
def test_{{ test.name }}({{ agent_instance_name }}):
    pytest.fail("Test case '{{ test.name }}' is not yet implemented.")
{% endfor %}
"""

# --- CORE SYNTHESIS ENGINE ---
class HephaestusAI:
    def __init__(self, citadel_hub: Optional[Any] = None):
        self.citadel_hub = citadel_hub
        if not Environment:
            raise ImportError("Jinja2 is required.")
        self.jinja_env = Environment()
        self.agent_template = self.jinja_env.from_string(PYTHON_AGENT_TEMPLATE)
        self.pytest_template = self.jinja_env.from_string(PYTEST_FILE_TEMPLATE)
        self.mdao_formulary = MDAO_Formulary()
        logger.info("HephaestusAI Agent (SAKE Compliant) is online.")

    def health_check(self) -> Dict[str, Any]:
        return {"status": "HEALTHY", "srs_compliance": "F82x Series Integrated"}

    def execute_sake_task(self, sake_manifest: Dict[str, Any], output_dir: Path) -> SynthesisReport:
        start_time = datetime.now(timezone.utc)
        lid = sake_manifest.get('lid', 'N/A')
        logger.info(f"[F822:CODE_SYNTHESIS_START] Starting SAKE task: {lid}")

        try:
            taskir = TaskIR(**sake_manifest['taskir'])
            caps = sake_manifest.get('caps', {})
        except (KeyError, ValidationError) as e:
            logger.error(f"[F822:BLUEPRINT_VALIDATION_FAILURE] SAKE manifest parsing failed: {e}")
            raise ValueError(f"Invalid SAKE manifest for HephaestusAI: {e}")

        analysis = self._analyze_taskir(taskir)
        clarity_analysis = self._assess_taskir_clarity(taskir)
        confidence = self.mdao_formulary.calculate_synthesis_confidence(clarity_analysis)
        logger.info(f"[F991:SCORE] MDAO Synthesis Confidence calculated: {confidence:.2%}")

        caps_passed = self.mdao_formulary.evaluate_caps(confidence, caps)
        logger.info(f"CAPS evaluation result: {'PASSED' if caps_passed else 'FAILED'}")

        if not caps_passed:
            logger.warning(f"[F992:VALIDATOR_FAILURE] Confidence {confidence:.2%} is below CAPS threshold {caps.get('min_confidence', 0.75)}. Aborting code generation.")
            # Still generate a report, but with no artifacts
            return SynthesisReport(
                sake_lid=lid, synthesis_confidence=confidence, caps_passed=False,
                start_time=start_time, end_time=datetime.now(timezone.utc),
                duration_seconds=(datetime.now(timezone.utc) - start_time).total_seconds(), artifacts=[]
            )

        report = SynthesisReport(
            sake_lid=lid, synthesis_confidence=confidence, caps_passed=True,
            start_time=start_time, end_time=start_time, duration_seconds=0
        )

        self._generate_artifacts(report, analysis, taskir, output_dir)

        report.end_time = datetime.now(timezone.utc)
        report.duration_seconds = (report.end_time - start_time).total_seconds()
        logger.info(f"[F822:CODE_SYNTHESIS_SUCCESS] Synthesis finished in {report.duration_seconds:.2f} seconds.")
        return report

    def _assess_taskir_clarity(self, taskir: TaskIR) -> CAPClarityAnalysis:
        issues, score = [], 1.0
        if not taskir.expected_assertions:
            issues.append("TaskIR is missing 'expected_assertions'.")
            score -= 0.4
        if not taskir.reaction.get('payload_schema'):
            issues.append("TaskIR reaction is missing a 'payload_schema'.")
            score -= 0.2
        if len(taskir.intent.split()) < 5:
            issues.append("TaskIR intent is very short.")
            score -= 0.1

        clarity = CAPClarity.CLEAR
        if score < 0.5: clarity = CAPClarity.INCOMPLETE
        elif score < 0.9: clarity = CAPClarity.AMBIGUOUS

        return CAPClarityAnalysis(clarity=clarity, score=score, issues=issues)

    def _analyze_taskir(self, taskir: TaskIR) -> Dict[str, Any]:
        target_id = taskir.reaction['target_agent_id']
        class_name = "".join(word.capitalize() for word in target_id.split('_'))
        instance_name = target_id.lower()
        filename_base = instance_name

        method_details = {
            "name": taskir.reaction['target_function'],
            "description": f"Handle task '{taskir.task_name}'",
            "args": [{"name": "payload", "type": taskir.reaction.get('payload_schema', 'Dict[str, Any]')}] if taskir.reaction.get('payload_schema') else [],
            "return_type": "Optional[Dict[str, Any]]"
        }

        test_details = [
            {"name": re.sub(r'[^a-z0-9_]', '', a['description'].lower().replace(' ', '_')), "description": a['description'], "method_to_call": taskir.reaction['target_function']}
            for a in taskir.expected_assertions
        ]

        return {
            "target_agent_class": class_name, "target_agent_instance": instance_name,
            "target_filename_base": filename_base, "methods_to_generate": [method_details],
            "tests_to_generate": test_details, "schemas_to_generate": taskir.payload_schemas
        }

    def _generate_artifacts(self, report: SynthesisReport, analysis: Dict, taskir: TaskIR, output_dir: Path):
        agent_dir = output_dir / "citadel" / "agents"
        test_dir = output_dir / "tests" / "agents"
        agent_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)

        # Generate Agent File
        agent_path = agent_dir / f"{analysis['target_filename_base']}.py"
        agent_code = self.agent_template.render(taskir=taskir, class_name=analysis['target_agent_class'], methods=analysis['methods_to_generate'], schemas=analysis['schemas_to_generate'])
        agent_path.write_text(agent_code)
        report.artifacts.append(GeneratedArtifact(artifact_type=SynthesisArtifactType.AGENT_STUB, path=agent_path, content_hash=hashlib.sha256(agent_code.encode()).hexdigest(), line_count=len(agent_code.splitlines())))
        logger.info(f"[F822:AGENT_STUB_GENERATED] Synthesized agent file: {agent_path}")

        # Generate Test File
        test_path = test_dir / f"test_{analysis['target_filename_base']}.py"
        pytest_code = self.pytest_template.render(taskir=taskir, agent_class_name=analysis['target_agent_class'], agent_instance_name=analysis['target_agent_instance'], agent_filename=analysis['target_filename_base'], tests=analysis['tests_to_generate'])
        test_path.write_text(pytest_code)
        report.artifacts.append(GeneratedArtifact(artifact_type=SynthesisArtifactType.TEST_FILE, path=test_path, content_hash=hashlib.sha256(pytest_code.encode()).hexdigest(), line_count=len(pytest_code.splitlines())))
        logger.info(f"[F823:TEST_STUB_GENERATED] Synthesized test file: {test_path}")


# --- SELF-TEST BLOCK ---
if __name__ == "__main__":
    logger.info("="*50)
    logger.info("Executing HephaestusAI Self-Test (v0.3 SAKE Compliant)")
    logger.info("="*50)

    with tempfile.TemporaryDirectory() as temp_dir_str:
        temp_dir, output_dir = Path(temp_dir_str), Path(temp_dir_str) / "generated_code"
        logger.info(f"Using temporary directory: {temp_dir}")

        mock_sake_manifest = {
            "lid": "LID-TEST-HEPHAESTUS-001",
            "taskir": {
                "task_name": "agent0.assess_proposal.v1",
                "intent": "Defines the mandatory review and approval workflow for significant changes proposed by non-Architect agents.",
                "reaction": {
                    "target_agent_id": "AGENT_0",
                    "target_function": "assess_proposal",
                    "payload_schema": "RefactorProposalPayload"
                },
                "payload_schemas": [{
                    "name": "RefactorProposalPayload",
                    "fields": [{"name": "proposal_id", "type": "str"}, {"name": "impact_score", "type": "float"}]
                }],
                "expected_assertions": [
                    {"description": "Agent 0 must log its decision after assessing the proposal.", "details": {}},
                    {"description": "The proposal's status must be updated to 'APPROVED' or 'REJECTED'.", "details": {}}
                ]
            },
            "caps": {"min_confidence": 0.6}
        }
        logger.info(f"Created mock SAKE manifest:\n{json.dumps(mock_sake_manifest, indent=2)}")

        hephaestus_agent = HephaestusAI()
        try:
            report = hephaestus_agent.execute_sake_task(mock_sake_manifest, output_dir)
            logger.info("\n" + "-"*50)
            logger.info("Synthesis Complete. Final Report:")
            print(report.model_dump_json(indent=2))
            logger.info("-" * 50 + "\n")

            assert report.caps_passed is True
            assert len(report.artifacts) == 2
            logger.info("Self-test validation PASSED.")
        except Exception as e:
            logger.critical(f"HephaestusAI self-test failed: {e}", exc_info=True)

    logger.info("="*50)
    logger.info("HephaestusAI SAKE-Compliant Self-Test Finished")
    logger.info("="*50)
