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
# ║   **VERSION:**      0.3.0 (SAKE Compliant)                                                                         ║
# ║   **STATUS:**       Conceptual                                                                                     ║
# ║   **CREATED:**      2025-09-14                                                                                     ║
# ║   **LAST_UPDATE:**  2025-09-14                                                                                     ║
# ║   **AUTHOR:**       Jules (AI Software Engineer)                                                                   ║
# ║                                                                                                                    ║
# ║   **PURPOSE:**                                                                                                     ║
# ║     This file defines the `OntologyWeaverAI`, refactored for SAKE compliance. It is driven by `.sake`               ║
# ║     manifests, analyzing a VDS document from the TaskIR and using the CAPS layer to gate the                       ║
# ║     creation of new knowledge graph links based on a confidence score.                                             ║
# ║                                                                                                                    ║
# ║   **REFERENCE:**                                                                                                   ║
# ║     - SAKE Ecosystem Documentation by Kousaki & Dmitry                                                             ║
# ║     - FEATURES.md, Feature 5: "Ontology Weaver" for the VDS                                                        ║
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

try:
    from pydantic import BaseModel, Field, ValidationError
except ImportError:
    class BaseModel:
        def __init__(self, **kwargs): [setattr(self, k, v) for k, v in kwargs.items()]
        def model_dump_json(self, indent=None): return json.dumps(self.__dict__, indent=indent)
    class ValidationError(Exception): pass

# --- Mock VDS Client for Standalone Testing ---
class MockVDSClient:
    def __init__(self): self.docs: Dict[str, Any] = {}; self.links: List[Dict] = []
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]: return self.docs.get(doc_id)
    def insert_document(self, doc: Dict[str, Any]): self.docs[doc['doc_id']] = doc
    def add_link(self, link: Dict[str, Any]): self.links.append(link)
    def get_links_for_doc(self, doc_id: str) -> List[Dict]: return [l for l in self.links if l['subject_id'] == doc_id or l['object_id'] == doc_id]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s')
logger = logging.getLogger("OntologyWeaverAI")


# --- ENUMERATIONS ---
class EntityType(str, Enum):
    CODE_COMMIT = "CODE_COMMIT"; AGENT_BLUEPRINT = "AGENT_BLUEPRINT"; LOG_ENTRY = "LOG_ENTRY"; VULNERABILITY_REPORT = "VULNERABILITY_REPORT"
    PATCH_PROPOSAL = "PATCH_PROPOSAL"; SIMULATION_REPORT = "SIMULATION_REPORT"; CAP_DOCUMENT = "CAP_DOCUMENT"; UNKNOWN = "UNKNOWN"

class RelationshipType(str, Enum):
    REFERENCES = "REFERENCES"; BASED_ON = "BASED_ON"; GENERATED_FROM = "GENERATED_FROM"; FIXES = "FIXES"
    LOGGED_DURING = "LOGGED_DURING"; DETECTED = "DETECTED"; PROPOSES = "PROPOSES"

class LinkEvidenceType(str, Enum):
    REGEX_MATCH = "REGEX_MATCH"; KEYWORD_CO_OCCURRENCE = "KEYWORD_CO_OCCURRENCE"; LLM_INFERENCE = "LLM_INFERENCE"


# --- PYDANTIC SCHEMAS ---
class VdsDocument(BaseModel):
    doc_id: str; entity_type: EntityType; content: str; metadata: Dict[str, Any] = Field(default_factory=dict)

class OntologicalLink(BaseModel):
    link_id: str = Field(default_factory=lambda: f"link-{uuid.uuid4().hex[:8]}"); subject_id: str; relationship: RelationshipType
    object_id: str; confidence: float = Field(1.0); created_by: str = "OntologyWeaverAI"

class OntologyUpdateReport(BaseModel):
    report_id: str = Field(default_factory=lambda: f"ont-report-{uuid.uuid4().hex[:8]}"); sake_lid: str
    processed_doc_id: str; links_created: int; links_rejected_by_caps: int; summary: str


# --- MDAO FORMULARY ---
class MDAO_Formulary:
    @staticmethod
    def calculate_link_confidence(evidence: List[Tuple[LinkEvidenceType, float]]) -> float:
        evidence_weights = {LinkEvidenceType.REGEX_MATCH: 0.8, LinkEvidenceType.KEYWORD_CO_OCCURRENCE: 0.5, LinkEvidenceType.LLM_INFERENCE: 0.9}
        total_score = sum(strength * evidence_weights.get(etype, 0.3) for etype, strength in evidence)
        total_weight = sum(evidence_weights.get(etype, 0.3) for etype, _ in evidence)
        return round(total_score / total_weight if total_weight > 0 else 0, 4)

    @staticmethod
    def evaluate_caps(confidence_score: float, caps_layer: Dict[str, Any]) -> bool:
        return confidence_score >= caps_layer.get("min_link_confidence", 0.7)


# --- CORE AGENT CLASS ---
class OntologyWeaverAI:
    def __init__(self, citadel_hub: Optional[Any] = None):
        self.citadel_hub = citadel_hub; self.vds_client = MockVDSClient()
        self.mdao_formulary = MDAO_Formulary()
        self.entity_id_patterns = {
            EntityType.VULNERABILITY_REPORT: re.compile(r'\b(vuln-[a-f0-9]{8})\b', re.IGNORECASE),
            EntityType.CODE_COMMIT: re.compile(r'\b(commit-[a-f0-9]{7,12})\b', re.IGNORECASE),
        }
        logger.info("OntologyWeaverAI (SAKE Compliant) is online.")

    def execute_sake_task(self, sake_manifest: Dict[str, Any]) -> OntologyUpdateReport:
        lid = sake_manifest.get('lid', 'N/A')
        logger.info(f"[F724:KNOWLEDGE_GRAPH_UPDATE_START] Received SAKE task: {lid}")
        try:
            doc = VdsDocument(**sake_manifest['taskir']['vds_document'])
            caps = sake_manifest.get('caps', {})
        except (KeyError, ValidationError) as e:
            raise ValueError(f"Invalid SAKE manifest for OntologyWeaverAI: {e}")

        links_created, links_rejected = 0, 0
        potential_links = self._identify_relationships(doc)

        for link in potential_links:
            if self.mdao_formulary.evaluate_caps(link.confidence, caps):
                self.vds_client.add_link(link.model_dump())
                links_created += 1
            else:
                links_rejected += 1
                logger.warning(f"[F724:LINK_REJECTED_BY_CAPS] Link from {link.subject_id} to {link.object_id} rejected. Confidence {link.confidence:.2%} < threshold {caps.get('min_link_confidence', 0.7)}.")

        summary = f"Processing complete. Created {links_created} links. Rejected {links_rejected} links based on CAPS."
        logger.info(f"[F724:KNOWLEDGE_GRAPH_UPDATE_SUCCESS] {summary}")
        return OntologyUpdateReport(sake_lid=lid, processed_doc_id=doc.doc_id, links_created=links_created, links_rejected_by_caps=links_rejected, summary=summary)

    def _identify_relationships(self, doc: VdsDocument) -> List[OntologicalLink]:
        links, content_lower = [], doc.content.lower()
        if doc.entity_type == EntityType.CODE_COMMIT and ("fix" in content_lower or "close" in content_lower):
            for match in self.entity_id_patterns[EntityType.VULNERABILITY_REPORT].finditer(content_lower):
                evidence = [(LinkEvidenceType.REGEX_MATCH, 1.0), (LinkEvidenceType.KEYWORD_CO_OCCURRENCE, 0.8)]
                links.append(OntologicalLink(subject_id=doc.doc_id, relationship=RelationshipType.FIXES, object_id=match.group(1), confidence=self.mdao_formulary.calculate_link_confidence(evidence)))
        return links


# --- SELF-TEST BLOCK ---
if __name__ == "__main__":
    logger.info("="*50)
    logger.info("Executing OntologyWeaverAI Self-Test (v0.3 SAKE Compliant)")
    logger.info("="*50)

    weaver = OntologyWeaverAI()
    mock_vds = weaver.vds_client
    mock_vds.insert_document(VdsDocument(doc_id="vuln-a1b2c3d4", entity_type=EntityType.VULNERABILITY_REPORT, content="...").model_dump())

    commit_doc_content = "feat: Add sanitation. This commit closes the issue. Fixes vuln-a1b2c3d4."
    commit_doc_to_process = VdsDocument(doc_id="commit-f0e1d2c", entity_type=EntityType.CODE_COMMIT, content=commit_doc_content)

    # 1. Test case where CAPS threshold is met
    logger.info("\n--- Test Case 1: Confidence meets CAPS threshold ---")
    sake_manifest_pass = {
        "lid": "LID-TEST-WEAVER-PASS-001",
        "taskir": {"vds_document": commit_doc_to_process.model_dump()},
        "caps": {"min_link_confidence": 0.8}
    }
    try:
        report_pass = weaver.execute_sake_task(sake_manifest_pass)
        print(report_pass.model_dump_json(indent=2))
        assert report_pass.links_created == 1
        assert report_pass.links_rejected_by_caps == 0
        logger.info("Test Case 1 PASSED.")
    except Exception as e:
        logger.critical(f"Test Case 1 FAILED: {e}", exc_info=True)

    # 2. Test case where CAPS threshold is NOT met
    logger.info("\n--- Test Case 2: Confidence fails CAPS threshold ---")
    sake_manifest_fail = {
        "lid": "LID-TEST-WEAVER-FAIL-001",
        "taskir": {"vds_document": commit_doc_to_process.model_dump()},
        "caps": {"min_link_confidence": 0.95} # Set a very high threshold
    }
    try:
        report_fail = weaver.execute_sake_task(sake_manifest_fail)
        print(report_fail.model_dump_json(indent=2))
        assert report_fail.links_created == 0
        assert report_fail.links_rejected_by_caps == 1
        logger.info("Test Case 2 PASSED.")
    except Exception as e:
        logger.critical(f"Test Case 2 FAILED: {e}", exc_info=True)

    logger.info("="*50)
    logger.info("OntologyWeaverAI SAKE-Compliant Self-Test Finished")
    logger.info("="*50)
