# citadel/agents/janus_ai.py
#
#
# ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                  **CITADEL GOVERNANCE & METADATA TEMPLATE (CGMT) v1.0**                                                ║
# ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
# ║                                                                                                                    ║
# ║   **FILE:**         janus_ai.py                                                                                    ║
# ║   **AGENT:**        JanusAI                                                                                        ║
# ║   **ARCHETYPE:**    SIMULATOR                                                                                      ║
# ║   **VERSION:**      0.1.0 (Stub)                                                                                   ║
# ║   **STATUS:**       Conceptual                                                                                     ║
# ║   **CREATED:**      2025-09-14                                                                                     ║
# ║   **LAST_UPDATE:**  2025-09-14                                                                                     ║
# ║   **AUTHOR:**       Jules (AI Software Engineer)                                                                   ║
# ║                                                                                                                    ║
# ║   **PURPOSE:**                                                                                                     ║
# ║     This file defines the `JanusAI` agent, a specialized AI responsible for creating, managing, and                ║
# ║     executing simulations within a "Digital Twin" of the Citadel ecosystem. It allows for safe,                  ║
# ║     sandboxed testing of architectural changes, agent interactions, and emergent behaviors.                        ║
# ║                                                                                                                    ║
# ║   **REFERENCE:**                                                                                                   ║
# ║     - FEATURES.md, Feature 1: The "Digital Twin" Testbed                                                           ║
# ║     - OGA-003 (Blueprint-Driven Development)                                                                       ║
# ║     - DKA-002 (Canonical Schemas & Centralized Management)                                                         ║
# ║                                                                                                                    ║
# ╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝


# --- IMPORTS ---
import json
import uuid
import time
import logging
import subprocess
from pathlib import Path
from enum import Enum, auto
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Type

# Pydantic is a core dependency for schema enforcement as per DKA-002
try:
    from pydantic import BaseModel, Field
except ImportError:
    print("Pydantic not found. Please install: pip install pydantic")
    # Mock BaseModel for environments where Pydantic isn't installed.
    class BaseModel:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
        def model_dump_json(self, indent=None):
            import json
            return json.dumps(self.__dict__, indent=indent)

# Docker is the conceptual choice for containerizing twin components.
try:
    import docker
    from docker.models.containers import Container
except ImportError:
    print("Docker SDK not found. Simulations will be mocked. Please install: pip install docker")
    docker = None
    Container = None

# --- LOGGING SETUP ---
# In a real Citadel implementation, this would use a centralized logger from the CitadelHub.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger("JanusAI")


# --- ENUMERATIONS ---
# Defines the possible states of a digital twin environment.
class EnvironmentStatus(str, Enum):
    """Enumeration for the lifecycle status of a Digital Twin Environment."""
    PENDING = "PENDING"
    BUILDING = "BUILDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    DEGRADED = "DEGRADED"
    ERROR = "ERROR"
    DESTROYED = "DESTROYED"

# Defines the possible outcomes of a simulation run.
class SimulationOutcome(str, Enum):
    """Enumeration for the final outcome of a simulation."""
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    INCOMPLETE = "INCOMPLETE"
    ABORTED = "ABORTED"
    TIMED_OUT = "TIMED_OUT"

# SRS-aligned enumeration for resource types.
class ResourceType(str, Enum):
    """Enumeration for virtual resource types."""
    CPU_CORES = "CPU_CORES"
    MEMORY_GB = "MEMORY_GB"
    STORAGE_GB = "STORAGE_GB"
    GPU_COUNT = "GPU_COUNT"

# SRS-aligned enumeration for scenario complexity.
class ScenarioComplexity(str, Enum):
    """Defines the complexity and potential impact of a simulation scenario."""
    LOW = "LOW"             # Simple, isolated component test
    MEDIUM = "MEDIUM"         # Interaction between 2-3 components
    HIGH = "HIGH"           # Complex interaction between multiple components
    SYSTEM_WIDE = "SYSTEM_WIDE" # Full ecosystem stress test


# --- PYDANTIC SCHEMAS (DKA-002 Compliance) ---
# These schemas define the data structures for blueprints, reports, and configurations.

class VirtualResourceSpec(BaseModel):
    """Specification for a virtual resource within the twin (e.g., CPU, Memory)."""
    type: ResourceType = Field(..., description="Type of the resource.")
    limit: float = Field(..., description="The allocated limit for this resource.")
    usage: float = Field(0.0, description="Current usage of the resource (monitored during simulation).")

class AgentSpec(BaseModel):
    """Specification for an AI agent to be instantiated within the twin."""
    agent_id: str = Field(..., description="Unique identifier for the agent instance.")
    agent_class: str = Field(..., description="The Python class name of the agent, e.g., 'DevPartnerAI'.")
    source_file: Path = Field(..., description="Path to the agent's source code file.")
    config: Dict[str, Any] = Field({}, description="Configuration dictionary for the agent.")
    dependencies: List[str] = Field([], description="List of other service/agent IDs it depends on.")
    container_id: Optional[str] = None # Populated at runtime

class ServiceSpec(BaseModel):
    """Specification for a core service (like a VDS or API Kernel) in the twin."""
    service_id: str = Field(..., description="Unique identifier for the service instance.")
    service_type: str = Field(..., description="Type of service, e.g., 'VDS_FAISS', 'API_KERNEL_FASTAPI'.")
    port_mapping: Dict[int, int] = Field({}, description="Host-to-container port mappings.")
    volume_mapping: Dict[Path, Path] = Field({}, description="Host-to-container volume mappings.")
    container_id: Optional[str] = None # Populated at runtime

class EnvironmentBlueprint(BaseModel):
    """
    Defines the complete architecture of a Digital Twin Environment.
    This serves as the "blueprint" mandated by OGA-003.
    """
    blueprint_id: str = Field(default_factory=lambda: f"blueprint-{uuid.uuid4().hex[:8]}")
    description: str = Field(..., description="A human-readable description of the blueprint's purpose.")
    agents: List[AgentSpec] = Field([], description="List of AI agents to deploy.")
    services: List[ServiceSpec] = Field([], description="List of core services to deploy.")
    resources: List[VirtualResourceSpec] = Field([], description="List of global resource constraints.")
    complexity: ScenarioComplexity = Field(ScenarioComplexity.MEDIUM, description="The estimated complexity of simulations run with this blueprint.")

class SimulationStep(BaseModel):
    """A single action or event to be executed within a simulation scenario."""
    step_id: int
    action: str = Field(..., description="The action to perform, e.g., 'API_CALL', 'PROPOSE_REFACTOR'.")
    target_id: str = Field(..., description="The ID of the agent/service to perform the action.")
    payload: Dict[str, Any] = Field({}, description="Data associated with the action.")
    expected_outcome: str = Field("", description="A description of the expected result for validation.")
    actual_outcome: Optional[str] = None
    passed: Optional[bool] = None

class SimulationScenario(BaseModel):
    """A sequence of steps that defines a test case to be run in the environment."""
    scenario_id: str = Field(default_factory=lambda: f"scenario-{uuid.uuid4().hex[:8]}")
    description: str
    steps: List[SimulationStep]
    complexity: ScenarioComplexity = Field(ScenarioComplexity.MEDIUM, description="The complexity level of this specific scenario.")

class MDAO_Scores(BaseModel):
    """Data structure for holding MDAO results."""
    simulation_cost: float = Field(..., description="Calculated cost of the simulation based on resources and duration.")
    risk_score: float = Field(..., description="Calculated risk score based on complexity and potential for failure.")
    confidence: float = Field(..., description="Confidence in the simulation outcome.")

class SimulationReport(BaseModel):
    """
    A structured report summarizing the results of a simulation run.
    This adheres to the principles of OGA-002 (Universal Reporting Standard).
    """
    report_id: str = Field(default_factory=lambda: f"report-{uuid.uuid4().hex[:8]}")
    blueprint_id: str
    scenario_id: str
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    outcome: SimulationOutcome
    mdao_scores: MDAO_Scores
    summary: str
    steps: List[SimulationStep]
    logs: List[str] = Field([], description="Captured logs from all components during the simulation.")


# --- MDAO FORMULARY ---
class MDAO_Formulary:
    """
    Houses Multidisciplinary Design Analysis and Optimization (MDAO) formulas.
    These functions calculate key metrics like cost, risk, and confidence for a simulation.
    """
    @staticmethod
    def calculate_simulation_cost(blueprint: EnvironmentBlueprint, duration_seconds: float) -> float:
        """
        Calculates a cost score for a simulation.
        Best case: Few resources, short duration -> Low cost.
        Worst case: Many complex resources, long duration -> High cost.
        """
        cost = 0.0
        # Cost per resource type (weights are arbitrary for the stub)
        cost_weights = {
            ResourceType.CPU_CORES: 0.1,
            ResourceType.MEMORY_GB: 0.05,
            ResourceType.STORAGE_GB: 0.01,
            ResourceType.GPU_COUNT: 1.0, # GPUs are expensive
        }
        for resource in blueprint.resources:
            cost += resource.limit * cost_weights.get(resource.type, 0.0)

        # Duration is a major factor
        cost *= (duration_seconds / 60.0) # Normalize to cost per minute
        return round(cost, 4)

    @staticmethod
    def calculate_risk_score(blueprint: EnvironmentBlueprint, scenario: SimulationScenario) -> float:
        """
        Calculates a risk score for a simulation.
        Best case: Low complexity, few components -> Low risk.
        Worst case: High complexity, many interacting components -> High risk.
        """
        complexity_weights = {
            ScenarioComplexity.LOW: 0.1,
            ScenarioComplexity.MEDIUM: 0.4,
            ScenarioComplexity.HIGH: 0.7,
            ScenarioComplexity.SYSTEM_WIDE: 1.0,
        }

        # Risk increases with the number of components and their interactions
        num_components = len(blueprint.agents) + len(blueprint.services)
        interaction_factor = max(1, num_components / 2.0)

        complexity_score = complexity_weights.get(scenario.complexity, 0.4)

        risk = complexity_score * interaction_factor
        return round(min(risk, 1.0), 4) # Cap risk at 1.0


# --- CORE CLASSES ---

class DigitalTwinEnvironment:
    """
    Represents a single, isolated Digital Twin instance.
    It manages the lifecycle and resources of all virtualized components.
    """
    def __init__(self, blueprint: EnvironmentBlueprint):
        self.env_id = f"twin-{uuid.uuid4().hex[:12]}"
        self.blueprint = blueprint
        self.status = EnvironmentStatus.PENDING
        self.containers: Dict[str, Container] = {}
        self.network = None
        self.docker_client = None
        if docker:
            try:
                self.docker_client = docker.from_env()
            except Exception as e:
                logger.error(f"Failed to connect to Docker daemon: {e}")
                self.docker_client = None
        logger.info(f"[F753:SIMULATION_ENV_INIT] Initialized DigitalTwinEnvironment {self.env_id} from blueprint {blueprint.blueprint_id}")

    def build(self):
        """Builds and starts all components defined in the blueprint."""
        if not self.docker_client:
            logger.warning("[F751:RESOURCE_ALLOCATION_SKIPPED] Docker not available. Simulating build process.")
            self.status = EnvironmentStatus.RUNNING
            time.sleep(2) # Simulate build time
            return

        logger.info(f"[{self.env_id}] [F753:SIMULATION_ENV_BUILD_START] Building environment...")
        self.status = EnvironmentStatus.BUILDING
        try:
            # 1. Create isolated network for the twin
            self.network = self.docker_client.networks.create(f"{self.env_id}-net")
            logger.info(f"[{self.env_id}] [F751:NETWORK_RESOURCE_CREATED] Network '{self.network.name}' created.")

            # 2. Build and run services
            for service_spec in self.blueprint.services:
                logger.info(f"[{self.env_id}] [F751:RESOURCE_ALLOCATION_START] Starting service: {service_spec.service_id}")
                container = self.docker_client.containers.run(
                    "alpine:latest",
                    name=f"{self.env_id}-{service_spec.service_id}",
                    command=["sleep", "3600"],
                    network=self.network.name,
                    detach=True,
                )
                service_spec.container_id = container.id
                self.containers[service_spec.service_id] = container
                logger.info(f"[{self.env_id}] [F751:RESOURCE_ALLOCATION_SUCCESS] Service '{service_spec.service_id}' running in container {container.short_id}.")

            # 3. Build and run agents
            for agent_spec in self.blueprint.agents:
                logger.info(f"[{self.env_id}] [F751:RESOURCE_ALLOCATION_START] Starting agent: {agent_spec.agent_id}")
                container = self.docker_client.containers.run(
                    "python:3.9-slim",
                    name=f"{self.env_id}-{agent_spec.agent_id}",
                    command=["sleep", "3600"],
                    network=self.network.name,
                    detach=True,
                )
                agent_spec.container_id = container.id
                self.containers[agent_spec.agent_id] = container
                logger.info(f"[{self.env_id}] [F751:RESOURCE_ALLOCATION_SUCCESS] Agent '{agent_spec.agent_id}' running in container {container.short_id}.")


            self.status = EnvironmentStatus.RUNNING
            logger.info(f"[{self.env_id}] [F753:SIMULATION_ENV_BUILD_COMPLETE] Environment build complete. Status: {self.status}")

        except Exception as e:
            logger.error(f"[{self.env_id}] [F753:SIMULATION_ENV_BUILD_FAILURE] Failed to build environment: {e}")
            self.status = EnvironmentStatus.ERROR
            self.destroy() # Clean up on failure

    def get_logs(self) -> List[str]:
        """Collects logs from all containers in the environment."""
        all_logs = []
        if not self.docker_client:
            return ["[F700:LOG_READ_FAILURE] Log collection skipped: Docker not available."]

        for component_id, container in self.containers.items():
            try:
                logs = container.logs().decode('utf-8').strip().split('\n')
                for log_line in logs:
                    all_logs.append(f"[{component_id}] {log_line}")
            except Exception as e:
                all_logs.append(f"[{component_id}] [F700:LOG_READ_FAILURE] Failed to retrieve logs: {e}")
        return all_logs

    def destroy(self):
        """Stops and removes all containers and networks associated with the environment."""
        logger.info(f"[{self.env_id}] [F751:RESOURCE_DEALLOCATION_START] Destroying environment...")
        if not self.docker_client:
            logger.warning("[F751:RESOURCE_DEALLOCATION_SKIPPED] Docker not available. Simulating destruction.")
            self.status = EnvironmentStatus.DESTROYED
            return

        for container in self.containers.values():
            try:
                container.stop()
                container.remove()
            except docker.errors.NotFound:
                pass # Already gone
            except Exception as e:
                logger.error(f"[F751:RESOURCE_DEALLOCATION_FAILURE] Failed to stop/remove container {container.id}: {e}")

        if self.network:
            try:
                self.network.remove()
            except docker.errors.NotFound:
                pass
            except Exception as e:
                logger.error(f"[F751:NETWORK_RESOURCE_FAILURE] Failed to remove network {self.network.name}: {e}")

        self.status = EnvironmentStatus.DESTROYED
        logger.info(f"[{self.env_id}] [F753:SIMULATION_ENV_DESTROYED] Environment destroyed.")


class JanusAI:
    """
    The JanusAI Agent: The master simulator for the Citadel ecosystem.
    """
    def __init__(self, citadel_hub: Optional[Any] = None):
        """
        Initializes JanusAI.
        Args:
            citadel_hub: A (mocked) instance of the CitadelHub for accessing system-wide configs and services.
        """
        self.citadel_hub = citadel_hub  # In a real scenario, this would be injected.
        self.active_environments: Dict[str, DigitalTwinEnvironment] = {}
        self.mdao_formulary = MDAO_Formulary()
        logger.info("JanusAI Agent is online. Ready to run simulations.")

    def health_check(self) -> Dict[str, Any]:
        """Performs a health check on JanusAI and its dependencies."""
        docker_ok = False
        if docker:
            try:
                docker.from_env().ping()
                docker_ok = True
            except Exception:
                docker_ok = False
        return {
            "status": "HEALTHY" if docker_ok else "DEGRADED",
            "dependencies": {
                "docker_sdk": "Connected" if docker_ok else "Disconnected",
            },
            "active_environments": len(self.active_environments),
            "srs_compliance": "F75x Series Integrated"
        }

    def create_environment_from_blueprint(self, blueprint: EnvironmentBlueprint) -> DigitalTwinEnvironment:
        """
        Creates and builds a new digital twin environment from a blueprint.
        """
        logger.info(f"[F753:SIMULATION_TASK_RECEIVED] Received request to create environment from blueprint: {blueprint.blueprint_id}")
        env = DigitalTwinEnvironment(blueprint)
        env.build()
        if env.status == EnvironmentStatus.RUNNING:
            self.active_environments[env.env_id] = env
            logger.info(f"[F753:SIMULATION_ENV_CREATE_SUCCESS] Successfully created and registered environment {env.env_id}")
        else:
            logger.error(f"[F753:SIMULATION_ENV_CREATE_FAILURE] Failed to create environment from blueprint {blueprint.blueprint_id}")
        return env

    def run_simulation(self, env: DigitalTwinEnvironment, scenario: SimulationScenario) -> SimulationReport:
        """
        Executes a simulation scenario within a given environment.
        """
        logger.info(f"[{env.env_id}] [F753:SIMULATION_TASK_STARTED] Starting simulation for scenario: {scenario.scenario_id}")
        start_time = datetime.now(timezone.utc)
        outcome = SimulationOutcome.SUCCESS

        if env.status != EnvironmentStatus.RUNNING:
            logger.error(f"[{env.env_id}] [F753:SIMULATION_TASK_FAILURE] Cannot run simulation, environment is not running (status: {env.status}).")
            outcome = SimulationOutcome.FAILURE
        else:
            for step in scenario.steps:
                try:
                    self._execute_simulation_step(env, step)
                    if not step.passed:
                        outcome = SimulationOutcome.FAILURE
                        break # Stop on first failed step
                except Exception as e:
                    logger.error(f"[{env.env_id}] [F752:PERFORMANCE_EVENT_ERROR] Step {step.step_id} failed with an exception: {e}")
                    step.actual_outcome = f"Execution Error: {e}"
                    step.passed = False
                    outcome = SimulationOutcome.FAILURE
                    break

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        # MDAO Calculation
        cost = self.mdao_formulary.calculate_simulation_cost(env.blueprint, duration)
        risk = self.mdao_formulary.calculate_risk_score(env.blueprint, scenario)
        confidence = 1.0 - risk # Simple confidence model for the stub
        mdao_scores = MDAO_Scores(simulation_cost=cost, risk_score=risk, confidence=confidence)

        report = SimulationReport(
            blueprint_id=env.blueprint.blueprint_id,
            scenario_id=scenario.scenario_id,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration,
            outcome=outcome,
            mdao_scores=mdao_scores,
            summary=f"Simulation {scenario.scenario_id} completed with outcome: {outcome.value}. Risk score: {risk}, Cost: {cost}",
            steps=scenario.steps,
            logs=env.get_logs()
        )
        logger.info(f"[{env.env_id}] [F753:SIMULATION_TASK_COMPLETED] Simulation finished. Outcome: {outcome.value}")
        return report

    def _execute_simulation_step(self, env: DigitalTwinEnvironment, step: SimulationStep):
        """
        (Mock) Executes a single step of a simulation scenario.
        In a real implementation, this would involve `docker exec` or API calls to containers.
        """
        logger.info(f"[{env.env_id}] [F752:PERFORMANCE_EVENT_START] Executing Step {step.step_id}: {step.action} on {step.target_id}")

        step_start_time = time.perf_counter()
        # Placeholder logic: We'll just mock the outcomes.
        time.sleep(0.5) # Simulate execution time

        # Find the target component in the blueprint
        target_component = next((c for c in env.blueprint.agents + env.blueprint.services if c.agent_id == step.target_id or c.service_id == step.target_id), None)
        if not target_component:
            step.actual_outcome = f"Target '{step.target_id}' not found in environment."
            step.passed = False
            logger.warning(f"[{env.env_id}] [F752:PERFORMANCE_EVENT_FAILURE] Step {step.step_id} failed: Target not found.")
            return

        # Mock different actions
        if step.action == "API_CALL":
            step.actual_outcome = "Received HTTP 200 OK."
            step.passed = True
        elif step.action == "PROPOSE_REFACTOR":
            step.actual_outcome = "Refactor proposal submitted and awaiting review."
            step.passed = True
        elif step.action == "TRIGGER_SECURITY_ALERT":
            # Simulate a failure case
            step.actual_outcome = "Security alert was triggered as expected, but SentinelAI failed to respond."
            step.passed = False # Let's say this is a test failure
        else:
            step.actual_outcome = f"Action '{step.action}' executed successfully (mocked)."
            step.passed = True

        step_latency = (time.perf_counter() - step_start_time) * 1000
        logger.info(f"[{env.env_id}] [F752:PERFORMANCE_EVENT_END] Step {step.step_id} finished in {step_latency:.2f}ms. Passed: {step.passed}")


    def destroy_environment(self, env_id: str):
        """Finds an active environment by ID and destroys it."""
        if env_id in self.active_environments:
            env = self.active_environments[env_id]
            env.destroy()
            del self.active_environments[env_id]
            logger.info(f"[F753:SIMULATION_ENV_DESTROY_SUCCESS] Environment {env_id} has been destroyed and deregistered.")
        else:
            logger.warning(f"[F753:SIMULATION_ENV_DESTROY_FAILURE] Attempted to destroy non-existent environment: {env_id}")


# --- SELF-TEST BLOCK (TSP-MDP-003 Compliance) ---
if __name__ == "__main__":
    """
    This self-test block demonstrates the core functionality of JanusAI,
    including the MDAO calculations and SRS-coded logging.
    """
    logger.info("="*50)
    logger.info("Executing JanusAI Self-Test & Demonstration (v1.1 with MDAO & SRS)")
    logger.info("="*50)

    # 1. Instantiate JanusAI
    janus_agent = JanusAI()

    # 2. Create a mock Environment Blueprint
    mock_blueprint = EnvironmentBlueprint(
        description="A simple test environment with a DevPartner and a VDS.",
        agents=[
            AgentSpec(
                agent_id="dev_partner_01",
                agent_class="DevPartnerAI",
                source_file=Path("citadel/agents/dev_partner.py")
            )
        ],
        services=[
            ServiceSpec(
                service_id="vds_main",
                service_type="VDS_FAISS",
                port_mapping={6379: 6379}
            )
        ],
        resources=[
            VirtualResourceSpec(type=ResourceType.CPU_CORES, limit=4),
            VirtualResourceSpec(type=ResourceType.MEMORY_GB, limit=8),
        ],
        complexity=ScenarioComplexity.HIGH
    )
    logger.info(f"Created mock blueprint:\n{mock_blueprint.model_dump_json(indent=2)}")

    # 3. Create the Digital Twin Environment from the blueprint
    test_environment = None
    try:
        test_environment = janus_agent.create_environment_from_blueprint(mock_blueprint)

        if test_environment.status != EnvironmentStatus.RUNNING:
            raise RuntimeError("Environment failed to reach RUNNING state.")

        # 4. Define a simple Simulation Scenario
        test_scenario = SimulationScenario(
            description="Test basic interaction between DevPartner and VDS.",
            complexity=ScenarioComplexity.HIGH,
            steps=[
                SimulationStep(
                    step_id=1,
                    action="API_CALL",
                    target_id="vds_main",
                    payload={"query": "SELECT * FROM logs;"},
                    expected_outcome="VDS returns a list of logs."
                ),
                SimulationStep(
                    step_id=2,
                    action="PROPOSE_REFACTOR",
                    target_id="dev_partner_01",
                    payload={"file": "main.py", "lines": [10, 25]},
                    expected_outcome="A refactor proposal is created."
                ),
                SimulationStep(
                    step_id=3,
                    action="TRIGGER_SECURITY_ALERT",
                    target_id="dev_partner_01",
                    payload={"type": "SQL_INJECTION"},
                    expected_outcome="SentinelAI should intercept and block the action."
                )
            ]
        )
        logger.info(f"Created test scenario:\n{test_scenario.model_dump_json(indent=2)}")

        # 5. Run the simulation
        final_report = janus_agent.run_simulation(test_environment, test_scenario)

        # 6. Print the final report
        logger.info("-" * 50)
        logger.info("Final Simulation Report:")
        logger.info("-" * 50)
        # Using model_dump_json for clean, structured output
        print(final_report.model_dump_json(indent=2))
        logger.info("-" * 50)

    except Exception as e:
        logger.critical(f"JanusAI self-test failed: {e}")

    finally:
        # 7. Clean up and destroy the environment
        if test_environment:
            logger.info(f"Cleaning up environment {test_environment.env_id}...")
            janus_agent.destroy_environment(test_environment.env_id)
        logger.info("="*50)
        logger.info("JanusAI Self-Test Finished")
        logger.info("="*50)
