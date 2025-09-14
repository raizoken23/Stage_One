# citadel/vds/ontology_weaver_ai.py
#
#
# ╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                  **CITADEL GOVERNANCE & METADATA TEMPLATE (CGMT) v1.0**                                                ║
# ╠════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╣
# ║                                                                                                                    ║
# ║   **FILE:**         ontology_weaver_ai.py                                                                          ║
# ║   **AGENT:**        OntologyWeaverAI                                                                               ║
# ║   **ARCHETYPE:**    CARTOGRAPHER / LIBRARIAN                                                                       ║
# ║   **VERSION:**      0.1.0 (Stub)                                                                                   ║
# ║   **STATUS:**       Conceptual                                                                                     ║
# ║   **CREATED:**      2025-09-14                                                                                     ║
# ║   **LAST_UPDATE:**  2025-09-14                                                                                     ║
# ║   **AUTHOR:**       Jules (AI Software Engineer)                                                                   ║
# ║                                                                                                                    ║
# ║   **PURPOSE:**                                                                                                     ║
# ║     This file defines the `OntologyWeaverAI`, an agent that transforms the Vector Document System (VDS)            ║
# ║     from a simple document store into a rich, queryable knowledge graph. It analyzes new VDS entries,              ║
# ║     creates explicit, typed links between them, and proposes updates to the VDS ontology itself.                   ║
# ║                                                                                                                    ║
# ║   **REFERENCE:**                                                                                                   ║
# ║     - FEATURES.md, Feature 5: "Ontology Weaver" for the VDS                                                        ║
# ║     - DKA-004 (Semantic Enrichment & Linking as Standard)                                                          ║
# ║     - DKA-002 (Canonical Schemas & Centralized Management)                                                         ║
# ║                                                                                                                    ║
# ╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝


# --- IMPORTS ---
import json
import logging
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Core dependency for schema validation
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

# Mock imports for other Citadel components
class MockVDSClient:
    """A mock client for the Vector Document System."""
    def __init__(self):
        self.docs: Dict[str, Any] = {}
        self.links: List[Dict] = []

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self.docs.get(doc_id)

    def insert_document(self, doc: Dict[str, Any]):
        self.docs[doc['doc_id']] = doc

    def add_link(self, link: Dict[str, Any]):
        self.links.append(link)

    def get_links_for_doc(self, doc_id: str) -> List[Dict]:
        return [l for l in self.links if l['subject_id'] == doc_id or l['object_id'] == doc_id]

# --- LOGGING SETUP ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger("OntologyWeaverAI")


# --- ENUMERATIONS ---
class EntityType(str, Enum):
    """Known types of entities (documents) in the VDS."""
    CODE_COMMIT = "CODE_COMMIT"
    AGENT_BLUEPRINT = "AGENT_BLUEPRINT"
    LOG_ENTRY = "LOG_ENTRY"
    VULNERABILITY_REPORT = "VULNERABILITY_REPORT"
    PATCH_PROPOSAL = "PATCH_PROPOSAL"
    SIMULATION_REPORT = "SIMULATION_REPORT"
    CAP_DOCUMENT = "CAP_DOCUMENT"
    USER_CONVERSATION = "USER_CONVERSATION"
    UNKNOWN = "UNKNOWN"

class RelationshipType(str, Enum):
    """Known types of relationships (links) between entities."""
    REFERENCES = "REFERENCES"           # A general link
    BASED_ON = "BASED_ON"               # e.g., a commit is based on a blueprint
    GENERATED_FROM = "GENERATED_FROM"   # e.g., code generated from a CAP
    FIXES = "FIXES"                     # e.g., a commit fixes a vulnerability
    LOGGED_DURING = "LOGGED_DURING"     # e.g., a log was created during a simulation
    DETECTED = "DETECTED"               # e.g., a simulation detected a vulnerability
    PROPOSES = "PROPOSES"               # e.g., a Sentinel proposes a patch

class LinkEvidenceType(str, Enum):
    """The type of evidence used to justify a link's creation."""
    REGEX_MATCH = "REGEX_MATCH"         # e.g., finding 'vuln-xxxx' in text
    KEYWORD_CO_OCCURRENCE = "KEYWORD_CO_OCCURRENCE" # e.g., 'fix' and 'vulnerability'
    LLM_INFERENCE = "LLM_INFERENCE"     # The link was inferred by a language model

class SchemaUpdateStatus(str, Enum):
    """Lifecycle status for a proposed schema update."""
    PROPOSED = "PROPOSED"
    IN_REVIEW = "IN_REVIEW"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    IMPLEMENTED = "IMPLEMENTED"

# --- PYDANTIC SCHEMAS ---
class VdsDocument(BaseModel):
    """A simplified representation of a document in the VDS."""
    doc_id: str = Field(description="Unique identifier for the document, e.g., 'commit-abc123', 'vuln-def456'.")
    entity_type: EntityType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class OntologicalLink(BaseModel):
    """Represents a typed, directional link between two VDS documents."""
    link_id: str = Field(default_factory=lambda: f"link-{uuid.uuid4().hex[:8]}")
    subject_id: str = Field(description="The ID of the source document.")
    relationship: RelationshipType = Field(description="The type of relationship (the predicate).")
    object_id: str = Field(description="The ID of the target document.")
    confidence: float = Field(1.0, description="The confidence score of the discovered link.")
    created_by: str = "OntologyWeaverAI"

class DiscoveredPattern(BaseModel):
    """Stores information about a newly discovered, recurring relationship pattern."""
    pattern_id: str = Field(default_factory=lambda: f"pattern-{uuid.uuid4().hex[:8]}")
    subject_type: EntityType
    object_type: EntityType
    context_keywords: List[str]
    occurrence_count: int = 1
    proposed_relationship_name: Optional[str] = None

class VDSSchemaUpdateProposal(BaseModel):
    """A structured proposal to add a new type to the VDS ontology."""
    proposal_id: str = Field(default_factory=lambda: f"sup-{uuid.uuid4().hex[:8]}")
    status: SchemaUpdateStatus = SchemaUpdateStatus.PROPOSED
    update_type: str = Field(description="Either 'EntityType' or 'RelationshipType'.")
    new_type_name: str
    description: str
    based_on_pattern_id: str


# --- MDAO FORMULARY ---
class MDAO_Formulary:
    """Houses MDAO formulas for the ontology weaving process."""

    @staticmethod
    def calculate_link_confidence(evidence: List[Tuple[LinkEvidenceType, float]]) -> float:
        """
        Calculates a confidence score for an ontological link based on the evidence found.
        Best case: Multiple strong evidence types -> High confidence.
        Worst case: Single, weak evidence type -> Low confidence.
        """
        evidence_weights = {
            LinkEvidenceType.REGEX_MATCH: 0.8,
            LinkEvidenceType.KEYWORD_CO_OCCURRENCE: 0.5,
            LinkEvidenceType.LLM_INFERENCE: 0.9,
        }

        # Combine evidence scores (using a simple weighted average for this stub)
        total_score = sum(strength * evidence_weights.get(etype, 0.3) for etype, strength in evidence)
        total_weight = sum(evidence_weights.get(etype, 0.3) for etype, _ in evidence)

        return round(total_score / total_weight if total_weight > 0 else 0, 4)


# --- CORE AGENT CLASS ---
class OntologyWeaverAI:
    """
    The OntologyWeaverAI Agent: Weaves the fabric of knowledge in the VDS.
    """
    def __init__(self, citadel_hub: Optional[Any] = None):
        """
        Initializes the OntologyWeaverAI.
        Args:
            citadel_hub: A (mocked) instance of the CitadelHub for service and schema access.
        """
        self.citadel_hub = citadel_hub
        # In a real system, this client would be provided by the hub.
        self.vds_client = MockVDSClient()
        self.mdao_formulary = MDAO_Formulary()
        self.known_entity_types: Set[str] = {e.value for e in EntityType}
        self.known_relationship_types: Set[str] = {r.value for r in RelationshipType}

        # Regex patterns to find entity IDs in text content.
        # This is a crucial part of the "identification" logic.
        self.entity_id_patterns = {
            EntityType.VULNERABILITY_REPORT: re.compile(r'\b(vuln-[a-f0-9]{8})\b', re.IGNORECASE),
            EntityType.CODE_COMMIT: re.compile(r'\b(commit-[a-f0-9]{7,12})\b', re.IGNORECASE),
            EntityType.PATCH_PROPOSAL: re.compile(r'\b(patch-[a-f0-9]{8})\b', re.IGNORECASE),
            # Add more patterns for other entity types...
        }

        logger.info("OntologyWeaverAI is online. Ready to weave the knowledge graph.")

    def health_check(self) -> Dict[str, Any]:
        return {
            "status": "HEALTHY",
            "known_entity_types": len(self.known_entity_types),
            "known_relationship_types": len(self.known_relationship_types),
            "vds_client_status": "OK" if self.vds_client else "MISSING",
            "srs_compliance": "F72x Series Integrated"
        }

    def process_new_vds_entry(self, doc: VdsDocument):
        """
        The main entry point for processing a new document added to the VDS.
        """
        logger.info(f"[F724:KNOWLEDGE_GRAPH_UPDATE_START] Processing new VDS entry: {doc.doc_id} (Type: {doc.entity_type})")

        # 1. Identify potential relationships in the document's content.
        identified_links = self._identify_relationships(doc)

        # 2. If relationships are found, create the ontological links in the VDS.
        if identified_links:
            logger.info(f"Found {len(identified_links)} potential relationships for {doc.doc_id}.")
            self._create_ontological_links(identified_links)
        else: # F724:KNOWLEDGE_GRAPH_UPDATE_SKIPPED
            logger.info(f"No new relationships identified for {doc.doc_id}.")

        # 3. (Future stub) Detect new, untyped patterns for schema evolution.
        self._detect_new_patterns(doc, identified_links)

    def _identify_relationships(self, doc: VdsDocument) -> List[OntologicalLink]:
        """
        Analyzes a document's content to find references to other entities.
        This is the core "Natural Language Understanding" part of the agent.
        """
        links = []
        content_lower = doc.content.lower()

        # --- Rule-based relationship identification ---

        # Example 1: A CODE_COMMIT that "fixes" a VULNERABILITY_REPORT
        if doc.entity_type == EntityType.CODE_COMMIT:
            if "fix" in content_lower or "close" in content_lower or "resolve" in content_lower:
                vuln_pattern = self.entity_id_patterns[EntityType.VULNERABILITY_REPORT]
                for match in vuln_pattern.finditer(content_lower):
                    # We found a direct ID match and contextual keywords
                    evidence = [
                        (LinkEvidenceType.REGEX_MATCH, 1.0),
                        (LinkEvidenceType.KEYWORD_CO_OCCURRENCE, 0.8)
                    ]
                    vuln_id = match.group(1)
                    links.append(OntologicalLink(
                        subject_id=doc.doc_id,
                        relationship=RelationshipType.FIXES,
                        object_id=vuln_id,
                        confidence=self.mdao_formulary.calculate_link_confidence(evidence)
                    ))

        # Example 2: A PATCH_PROPOSAL that is "based on" a VULNERABILITY_REPORT
        if doc.entity_type == EntityType.PATCH_PROPOSAL:
            vuln_pattern = self.entity_id_patterns[EntityType.VULNERABILITY_REPORT]
            for match in vuln_pattern.finditer(content_lower):
                evidence = [(LinkEvidenceType.REGEX_MATCH, 1.0)]
                vuln_id = match.group(1)
                links.append(OntologicalLink(
                    subject_id=doc.doc_id,
                    relationship=RelationshipType.BASED_ON,
                    object_id=vuln_id,
                    confidence=self.mdao_formulary.calculate_link_confidence(evidence)
                ))

        # --- General reference identification ---
        # Look for any known entity ID format in the text.
        for entity_type, pattern in self.entity_id_patterns.items():
            # Avoid self-references or re-linking what's already found
            if doc.entity_type == entity_type: continue

            for match in pattern.finditer(content_lower):
                object_id = match.group(1)
                evidence = [(LinkEvidenceType.REGEX_MATCH, 0.7)] # Lower base strength for generic match
                # Check if this link already exists to avoid duplicates
                if not any(l.relationship == RelationshipType.REFERENCES and l.object_id == object_id for l in links):
                    links.append(OntologicalLink(
                        subject_id=doc.doc_id,
                        relationship=RelationshipType.REFERENCES,
                        object_id=object_id,
                        confidence=self.mdao_formulary.calculate_link_confidence(evidence)
                    ))

        return links

    def _create_ontological_links(self, links: List[OntologicalLink]):
        """Persists a list of new ontological links to the VDS."""
        for link in links:
            logger.info(f"[F724:KNOWLEDGE_GRAPH_LINK_CREATED] Creating link: ({link.subject_id}) -[{link.relationship.value}]-> ({link.object_id}) with confidence {link.confidence:.2%}")
            # In a real system, this would write to a dedicated graph DB or a special VDS index.
            self.vds_client.add_link(link.model_dump())

    def _detect_new_patterns(self, doc: VdsDocument, existing_links: List[OntologicalLink]):
        """
        (Stub) Analyzes a document to find recurring but currently untyped relationships.
        """
        # This is a highly complex task that would likely involve an LLM.
        # Placeholder logic: If a "REFERENCES" link is found and the content
        # contains a specific keyword, we might detect a new pattern.
        for link in existing_links:
            if link.relationship == RelationshipType.REFERENCES:
                referenced_doc = self.vds_client.get_document(link.object_id)
                if not referenced_doc: continue

                # Example: A commit message that says "updates blueprint..."
                if "update" in doc.content.lower() and "blueprint" in doc.content.lower() \
                   and doc.entity_type == EntityType.CODE_COMMIT \
                   and referenced_doc['entity_type'] == EntityType.AGENT_BLUEPRINT:

                    logger.warning("[F724:NEW_RELATIONSHIP_PATTERN_DETECTED] Discovered a potential new relationship pattern: CODE_COMMIT 'UPDATES' AGENT_BLUEPRINT")
                    # In a real system, we would store this pattern and increment its count.
                    # If the count exceeds a threshold, we would trigger a schema update proposal.
                    self._propose_schema_update(DiscoveredPattern(
                        subject_type=EntityType.CODE_COMMIT,
                        object_type=EntityType.AGENT_BLUEPRINT,
                        context_keywords=["update", "blueprint"]
                    ))
                    break # Only propose one update per doc for now

    def _propose_schema_update(self, pattern: DiscoveredPattern):
        """
        (Stub) Generates and submits a proposal to update the VDS ontology.
        """
        new_relationship_name = "UPDATES" # Derived from keywords

        proposal = VDSSchemaUpdateProposal(
            update_type="RelationshipType",
            new_type_name=new_relationship_name,
            description=f"Proposing new relationship '{new_relationship_name}' based on observed pattern between {pattern.subject_type} and {pattern.object_type} with keywords {pattern.context_keywords}.",
            based_on_pattern_id=pattern.pattern_id
        )
        logger.info(f"[F724:ONTOLOGY_UPDATE_PROPOSED] Submitting new schema update proposal: {proposal.proposal_id}")
        # self.citadel_hub.get_governance_service().submit_schema_proposal(proposal.model_dump())
        print("\n--- SCHEMA UPDATE PROPOSAL ---")
        print(proposal.model_dump_json(indent=2))
        print("----------------------------\n")

    def get_entity_graph(self, start_doc_id: str, depth: int = 2) -> Dict[str, Any]:
        """Retrieves and constructs a subgraph of entities and their relationships."""
        graph = {"nodes": {}, "edges": []}
        nodes_to_visit = {start_doc_id}
        visited_nodes = set()

        for i in range(depth):
            if not nodes_to_visit: break
            current_id = nodes_to_visit.pop()
            if current_id in visited_nodes: continue

            visited_nodes.add(current_id)
            doc = self.vds_client.get_document(current_id)
            if doc:
                graph["nodes"][current_id] = doc

            links = self.vds_client.get_links_for_doc(current_id)
            for link in links:
                graph["edges"].append(link)
                if link['subject_id'] not in visited_nodes:
                    nodes_to_visit.add(link['subject_id'])
                if link['object_id'] not in visited_nodes:
                    nodes_to_visit.add(link['object_id'])

        return graph


# --- SELF-TEST BLOCK (TSP-MDP-003 Compliance) ---
if __name__ == "__main__":
    """
    This self-test block demonstrates the OntologyWeaverAI's ability to process
    new documents and create links between them in the VDS.
    """
    logger.info("="*50)
    logger.info("Executing OntologyWeaverAI Self-Test & Demonstration (v1.1 with MDAO & SRS)")
    logger.info("="*50)

    # 1. Instantiate the agent
    weaver = OntologyWeaverAI()
    mock_vds = weaver.vds_client

    # 2. Populate the mock VDS with some sample documents
    vuln_report = VdsDocument(
        doc_id="vuln-a1b2c3d4",
        entity_type=EntityType.VULNERABILITY_REPORT,
        content="Critical vulnerability: SQL injection possible in login form."
    )
    mock_vds.insert_document(vuln_report.model_dump())

    blueprint_doc = VdsDocument(
        doc_id="bp-user-auth-v2",
        entity_type=EntityType.AGENT_BLUEPRINT,
        content="Blueprint for the UserAuthentication agent, version 2."
    )
    mock_vds.insert_document(blueprint_doc.model_dump())

    commit_doc = VdsDocument(
        doc_id="commit-f0e1d2c",
        entity_type=EntityType.CODE_COMMIT,
        content="""feat: Add parameterized queries to login

This commit resolves the SQL injection issue.
Fixes vuln-a1b2c3d4.

This change also updates the agent based on bp-user-auth-v2.
"""
    )
    mock_vds.insert_document(commit_doc.model_dump())

    logger.info(f"Mock VDS populated with {len(mock_vds.docs)} documents.")

    # 3. Process the new commit document
    logger.info("\n--- Processing new commit document ---")
    weaver.process_new_vds_entry(commit_doc)
    logger.info("------------------------------------")

    # 4. Verify the created links
    logger.info(f"\n--- Verifying links for commit: {commit_doc.doc_id} ---")
    graph_data = weaver.get_entity_graph(commit_doc.doc_id)

    print(json.dumps(graph_data, indent=2))

    # Assertions for the test
    found_fixes_link = any(
        e['relationship'] == RelationshipType.FIXES.value and e['object_id'] == vuln_report.doc_id
        for e in graph_data['edges']
    )
    found_based_on_link = any(
        e['relationship'] == RelationshipType.REFERENCES.value and e['object_id'] == blueprint_doc.doc_id
        for e in graph_data['edges']
    )

    if found_fixes_link:
        logger.info("SUCCESS: Correctly created 'FIXES' link to vulnerability.")
    else:
        logger.error("FAILURE: Did not create 'FIXES' link.")

    if found_based_on_link:
        logger.info("SUCCESS: Correctly created 'REFERENCES' link to blueprint.")
    else:
        logger.error("FAILURE: Did not create 'REFERENCES' link.")

    logger.info("-------------------------------------------\n")

    # 5. Demonstrate pattern detection and schema proposal
    logger.info("--- Demonstrating Pattern Detection ---")
    # We manually trigger the logic here for demonstration
    weaver._detect_new_patterns(commit_doc, weaver.vds_client.get_links_for_doc(commit_doc.doc_id))
    logger.info("-------------------------------------\n")


    logger.info("="*50)
    logger.info("OntologyWeaverAI Self-Test Finished")
    logger.info("="*50)
