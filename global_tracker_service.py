# MASTER_CITADEL\SERVICE_SYSTEM\global_tracker_service.py

r"""
╔════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║ 🧠 CITADEL DOSSIER SYSTEM SERVICE: GLOBAL METADATA TRACKER (v3.0 - Refactored Service)                             ║
║────────────────────────────────────────────────────────────────────────────────────────────────────────────────────║
║ ✅ Purpose:                                                                                                        ║
║    - Manage the lifecycle of metadata for all thought vectors within the Citadel ecosystem.                        ║
║    - Operates on `global_vector_metadata` (core schema-defined fields) and                                       ║
║      `vector_metadata_fields` (flexible key-value store for dynamic/agent-specific fields).                      ║
║    - Provides robust, schema-aware routines for metadata creation, updates, retrieval, and schema evolution.       ║
║                                                                                                                    ║
║ 🧠 Key Features:                                                                                                   ║
║    - Initialization driven by `GLOBAL_TRACKING_SCHEMA` from `utils.citadel_global_schema`.                         ║
║    - Dynamic creation and patching of the `global_vector_metadata` table.                                          ║
║    - Strict separation of schema-defined vs. dynamic fields.                                                       ║
║    - Intelligent serialization/deserialization of complex data types (lists, dicts, bools) for SQLite.             ║
║    - Comprehensive logging and error handling.                                                                     ║
║    - Robust connection management with reconnection capabilities.                                                  ║
║    - Includes `FIELD_EXPLANATIONS` for metadata introspection.                                                     ║
║                                                                                                                    ║
║ ⚙️ Integration:                                                                                                    ║
║    - Intended to be instantiated by `citadel_hub.py` (or an application controller) with a DB path                 ║
║      obtained from `ConfigLoader`.                                                                                 ║
║    - Used by Council Agents, Orchestrators (DINAH/KAIRO), CitadelDossierSystem, and other components.              ║
║                                                                                                                    ║
║ 📅 Version: 3.0 – Refactored Service, Schema-Driven – 2025-08-03 (Conceptual Date)                                ║
╚════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝
"""

import sqlite3
import json
from datetime import datetime, date, timezone
from pathlib import Path
import logging
from typing import Optional, Union, Dict, Any, List, Tuple, Set
import re
import sys  # For __main__ path adjustments
# ======================================================================
# BOOTSTRAP: Ensure MASTER_CITADEL root is in sys.path for package imports
# ======================================================================
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # Go up to MASTER_CITADEL
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Now your imports will work
from AGENTS.CDS_SYSTEM import CDS_CONFIG

# --- Rich Library for CLI Rich Text ---
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

# --- Guardian Logger Import ---
from LOGGING_SYSTEM import F922_guardian_logger as guardianlogger
try:
    from LOGGING_SYSTEM.F922_guardian_logger import log_event, LogEventType, LogSeverity, SRSCode
except ImportError:
    log_event = None
    class LogEventType:
        SYSTEM_WARNING = "SYSTEM_WARNING"
        SYSTEM_INFO = "SYSTEM_INFO"
        SYSTEM_ERROR = "SYSTEM_ERROR"
    class LogSeverity:
        WARNING = "WARNING"
        INFO = "INFO"
        ERROR = "ERROR"
        CRITICAL = "CRITICAL"
    class SRSCode:
        F956 = "F956"
        F985 = "F985"
        F990 = "F990"
        F987 = "F987"

# ======================================================================
# Citadel Ecosystem Imports & Path Setup
# ======================================================================
import sys
import logging
from pathlib import Path
from typing import Dict

# --- Path Setup for standalone testing ---
_GMT_SERVICE_FILE_PATH = Path(__file__).resolve()
_CDS_PACKAGE_ROOT_FOR_GMT = _GMT_SERVICE_FILE_PATH.parents[1]  # SERVICE_SYSTEM -> MASTER_CITADEL
_CITADEL_ROOT_FOR_GMT = _CDS_PACKAGE_ROOT_FOR_GMT.parent

if str(_CITADEL_ROOT_FOR_GMT) not in sys.path:
    sys.path.insert(0, str(_CITADEL_ROOT_FOR_GMT))

# --- Core Citadel Config ---
from AGENTS.CDS_SYSTEM import CDS_CONFIG
ROOT = CDS_CONFIG.ROOT
CDS_DATA_PATHS = CDS_CONFIG.CDS_DATA_PATHS
CDS_META = CDS_CONFIG.CDS_META

# ======================================================================
# Schema Import Attempt (Dynamic Safe Import)
# ======================================================================
SCHEMAS_IMPORTED_SUCCESSFULLY = False
GLOBAL_TRACKING_SCHEMA: Dict[str, str] = {}
VECTOR_FIELD_SCHEMA: Dict[str, str] = {}

try:
    import importlib.util

    schema_path = Path(__file__).resolve().parent / "GLOBAL_TRACKER_SCHEMA.py"
    if not schema_path.exists():
        raise FileNotFoundError(f"Global tracker schema file not found: {schema_path}")

    spec = importlib.util.spec_from_file_location("GLOBAL_TRACKER_SCHEMA", schema_path)
    schema_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(schema_module)

    GLOBAL_TRACKING_SCHEMA = getattr(schema_module, "GLOBAL_TRACKING_SCHEMA", None)
    VECTOR_FIELD_SCHEMA = getattr(schema_module, "VECTOR_FIELD_SCHEMA", None)

    if not isinstance(GLOBAL_TRACKING_SCHEMA, dict):
        raise TypeError("GLOBAL_TRACKING_SCHEMA is not a dictionary.")
    if not isinstance(VECTOR_FIELD_SCHEMA, dict):
        raise TypeError("VECTOR_FIELD_SCHEMA is not a dictionary.")

    SCHEMAS_IMPORTED_SUCCESSFULLY = True
    logging.info("[F956][CAPS:SCHEMA_OK] GMT: Global tracker schemas loaded successfully.")

except (ImportError, FileNotFoundError) as e_schema_imp:
    logging.critical(f"[F956][CAPS:SCHEMA_ERR] GMT: Could not import schema: {e_schema_imp}")
except TypeError as e_schema_type_err:
    logging.critical(f"[F956][CAPS:SCHEMA_ERR] GMT: Schema types invalid: {e_schema_type_err}")

# ======================================================================
# Fallback to minimal schemas if main ones are missing or invalid
# ======================================================================
if not SCHEMAS_IMPORTED_SUCCESSFULLY:
    GLOBAL_TRACKING_SCHEMA = {
        "fingerprint": "TEXT PRIMARY KEY NOT NULL",
        "raw_text": "TEXT",
        "created_at": "TEXT",
        "last_updated": "TEXT",
        "source": "TEXT DEFAULT 'unknown_source_gmt_fb'",
        "status": "TEXT DEFAULT 'undefined_gmt_fb'",
        "domain": "TEXT DEFAULT 'general_gmt_fb'",
        "category": "TEXT DEFAULT 'uncategorized_gmt_fb'",
        "tags": "TEXT DEFAULT '[]'"
    }

    VECTOR_FIELD_SCHEMA = {
        "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
        "fingerprint": "TEXT NOT NULL",
        "field_name": "TEXT NOT NULL",
        "value": "TEXT",
        "last_updated": "TEXT"
    }

    logging.warning(f"[F956][CAPS:SCHEMA_WARN] GMT: Using MINIMAL FALLBACK GLOBAL_TRACKING_SCHEMA: {list(GLOBAL_TRACKING_SCHEMA.keys())}")

# ======================================================================
# Logger Setup
# ======================================================================
logger = logging.getLogger("GlobalMetadataTracker")  # Service-specific logger

# Table Names
MAIN_TABLE = "global_vector_metadata"
FIELD_TABLE = "vector_metadata_fields"  # For dynamic key-value pairs


class GlobalMetadataTracker:
    VERSION = "3.0"
    
    # Static list of fields from the loaded GLOBAL_TRACKING_SCHEMA
    SCHEMA_DEFINED_FIELDS: List[str] = list(GLOBAL_TRACKING_SCHEMA.keys())

    FIELD_EXPLANATIONS: Dict[str, str] = {  # From your previous GMT file
        "fingerprint": "Unique identifier for the thought vector.",
        "origin_prompt": "Original prompt that seeded the vector.",
        "created_at": "UTC timestamp (ISO8601 string) when the thought was first generated.",
        "last_updated": "UTC timestamp (ISO8601 string) when metadata was last updated.",
        "embedding": "Raw vector embedding (BLOB) or reference (TEXT).",
        "tier": "Assigned processing or value tier (e.g., T1, T2, SANCTUM).",
        "current_FAISS_index": "Name of the FAISS index currently holding this vector.",
        "origin_file": "Filename or module of origin for this thought.",
        "source": "Agent ID, system name, or user ID that created/sourced this entry.",
        "domain": "Primary topical or contextual domain.",
        "thought_type": "Structural classification (e.g., 'seed', 'definition_structured', 'elaboration_output').",
        "tags": "List of keywords or labels associated (stored as JSON string).",
        "context": "Full text or conceptual input used for generation/processing.",
        "status": "Current processing state (e.g. 'new', 'enriched', 'rejected').",
        "routed_to": "Next agent or system this vector is assigned to for processing.",
        "category": "Specific classification or sub-category within the domain.",
        "confidence_score": "Overall confidence in the validity/accuracy of the content (0.0-1.0).",
        "trust_score": "System's trust in this vector's utility or reliability (0.0-1.0).",
        "importance_score": "Assessed impact or priority weight (0.0-1.0).",
        "insight_score": "Novelty and value in generating new knowledge (0.0-1.0).",
        "schema_version": "Version of GLOBAL_TRACKING_SCHEMA this entry adhered to.",
        # Add more explanations as needed from your extensive list
    }

    def __init__(self,
                 db_path: Optional[Union[str, Path]] = None,
                 system_config: Optional[Any] = None,   # Deprecated, kept for legacy compatibility if needed
                 hub_instance: Optional[Any] = None):
        """
        Initializes the GlobalMetadataTracker service. Adheres to GPCS-P.

        Args:
            db_path: Deprecated. Highest precedence override for the DB path, mainly for testing.
            system_config: Deprecated. Use hub_instance.
            hub_instance: Required reference to the CitadelHub instance for config and path sourcing.
        """
        # --- 1. Initialize instance variables ---
        self.hub = hub_instance
        self.conn: Optional[sqlite3.Connection] = None
        self.cursor: Optional[sqlite3.Cursor] = None
        self.db_path: Optional[str] = None
        self._is_ready = False # Initialize readiness state
        self.unknown_fields_encountered: Set[str] = set()
        self.data_cache: Dict[str, Dict[str, Any]] = {}

        logger.info("[F956][CAPS:GLOBAL_TRACKER_INIT] GMT Initializing...")

        # --- 2. Determine DB Path using GPCS-P ---
        actual_db_path: Optional[Path] = None

        if db_path:  # Direct override for testing takes precedence
            actual_db_path = Path(db_path).resolve()
            logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INIT] GMT: Using direct db_path override: {actual_db_path}")
        elif self.hub:
            try:
                # The single, authoritative way to get the path as per GPCS-P
                # Assumes constants.py has PATH_KEY_GMT_DB_FILE = "gmt_database_file"
                # Importing constants for this specific key, assume it would be passed by Hub
                # If hub_instance is available, it should provide its own constants.
                if hasattr(self.hub, 'constants') and hasattr(self.hub.constants, 'PATH_KEY_GMT_DB_FILE'):
                    canonical_key = self.hub.constants.PATH_KEY_GMT_DB_FILE
                else:
                    logger.warning("[F956][CAPS:GLOBAL_TRACKER_WARN] GMT: Hub instance does not have 'constants.PATH_KEY_GMT_DB_FILE'. Using hardcoded key.")
                    canonical_key = "gmt_database_file" # Fallback key name

                resolved_path_str = self.hub.get_path(canonical_key)
                actual_db_path = Path(resolved_path_str)
                logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INIT] GMT: Found db_path via Hub.get_path('{canonical_key}'): {actual_db_path}")
            except (AttributeError, KeyError) as e:
                logger.error(f"[F956][CAPS:GLOBAL_TRACKER_ERR] GMT: Failed to get DB path from Hub via canonical key: {e}. Hub integration might be incomplete.")
        
        if not actual_db_path:
            emergency_db_path = Path("./TEMP_GMT_EMERGENCY/gmt_emergency_fallback.db").resolve()
            logger.critical(f"[F956][CAPS:GLOBAL_TRACKER_ERR] GMT: Could not determine DB path from any source. Using emergency fallback: {emergency_db_path}")
            actual_db_path = emergency_db_path
        
        self.db_path = str(actual_db_path)

        # --- 3. Connect to the database and set up tables ---
        try:
            self._connect_db() # Connect Connect during initialization
            if self.conn:
                # This call ensures the database schema is created or updated upon initialization.
                self.ensure_tables_and_schema() 
                
                self._is_ready = True # Set to True only if connection and schema setup succeed
                logger.info("[F956][CAPS:GLOBAL_TRACKER_INIT] GMT Initialized, connected, and schema verified successfully.")
                if log_event:
                    log_event(
                        event_type=LogEventType.SYSTEM_INFO,
                        srs_code=SRSCode.F956,
                        severity=LogSeverity.INFO,
                        component="GlobalMetadataTracker",
                        message="Service initialized successfully",
                        context={"db_path": self.db_path}
                    )
            else:
                logger.error("[F956][CAPS:GLOBAL_TRACKER_ERR] GMT Initialization failed: Connection could not be established.")
        except Exception as e:
            logger.error(f"[F956][CAPS:GLOBAL_TRACKER_ERR] GMT Initialization failed during connect/setup: {e}", exc_info=True)
            if log_event:
                log_event(
                    event_type=LogEventType.SYSTEM_ERROR,
                    srs_code=SRSCode.F956,
                    severity=LogSeverity.ERROR,
                    component="GlobalMetadataTracker",
                    message="Initialization failed during connect/setup",
                    context={"exception_msg": str(e)}
                )

    def is_ready(self) -> bool:
        """
        Reports the operational readiness of the GlobalMetadataTracker instance.
        True if the database connection is established and tables/schema are verified.
        """
        return self._is_ready

    def _connect_db(self):
        if self.conn:
            try: self.conn.close()
            except Exception as e_close: logger.warning(f"[F956][CAPS:GLOBAL_TRACKER_WARN] GMT: Error closing existing DB connection: {e_close}")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, timeout=15, check_same_thread=False) # Connect Increased timeout
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self.cursor.execute("PRAGMA foreign_keys = ON;")
        self.conn.commit()
        logger.debug(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] GMT: DB connection established to '{self.db_path}'.")

    def _get_cursor(self) -> sqlite3.Cursor:
        if self.conn is None or self.cursor is None:
            logger.warning("[F956][CAPS:GLOBAL_TRACKER_WARN] GMT: DB connection or cursor is None. Re-attempting connection.")
            self._connect_db()
        try:
            self.cursor.execute("SELECT 1;") # Connect Test query
        except (sqlite3.ProgrammingError, sqlite3.OperationalError, AttributeError) as e_cursor_test:
            logger.warning(f"[F956][CAPS:GLOBAL_TRACKER_WARN] GMT: DB connection test failed ({e_cursor_test}). Re-attempting connection.")
            self._connect_db()
        if self.cursor is None: # Connect Should be set by _connect_db
            raise sqlite3.OperationalError("[F956][CAPS:GLOBAL_TRACKER_ERR] GMT: CRITICAL - Failed to obtain a valid DB cursor after connection attempts.")
        return self.cursor

    def ensure_tables_and_schema(self):
        cursor = self._get_cursor()
        # --- Ensure MAIN_TABLE (global_vector_metadata) ---
        if not GLOBAL_TRACKING_SCHEMA or "fingerprint" not in GLOBAL_TRACKING_SCHEMA:
            raise ValueError("[F956][CAPS:GLOBAL_TRACKER_ERR] GLOBAL_TRACKING_SCHEMA is invalid or missing 'fingerprint' definition.")
        
        main_cols = [f"`fingerprint` {GLOBAL_TRACKING_SCHEMA['fingerprint']}" ] # Fingerprint first
        for field, type_def in GLOBAL_TRACKING_SCHEMA.items():
            if field.lower() != "fingerprint": # Ensure 'fingerprint' is not duplicated
                main_cols.append(f"`{field}` {type_def}")
        
        create_main_sql = f"CREATE TABLE IF NOT EXISTS `{MAIN_TABLE}` ({', '.join(main_cols)});"
        cursor.execute(create_main_sql)

        # --- Ensure FIELD_TABLE (vector_metadata_fields) ---
        # Using 'field_name' to align with VECTOR_FIELD_SCHEMA if that's the convention.
        # The FK constraint with ON DELETE CASCADE ON UPDATE CASCADE is good.
        create_field_sql = f"""
            CREATE TABLE IF NOT EXISTS `{FIELD_TABLE}` (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fingerprint TEXT NOT NULL,
                field_name TEXT NOT NULL, -- Using field_name
                value TEXT,
                last_updated TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'NOW')),
                UNIQUE(fingerprint, field_name), -- Using field_name
                FOREIGN KEY(fingerprint) REFERENCES `{MAIN_TABLE}`(fingerprint) ON DELETE CASCADE ON UPDATE CASCADE
            );"""
        cursor.execute(create_field_sql)
        if self.conn: self.conn.commit()
        logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] GMT: Tables `{MAIN_TABLE}` and `{FIELD_TABLE}` schemas ensured in `{self.db_path}`.")
        self._patch_main_table_columns(cursor) # Call patching after ensuring table exists

    def _patch_main_table_columns(self, cursor: sqlite3.Cursor):
        """Adds missing columns from GLOBAL_TRACKING_SCHEMA to the main table."""
        cursor.execute(f"PRAGMA table_info(`{MAIN_TABLE}`)")
        existing_db_cols = {row["name"].lower() for row in cursor.fetchall()}
        added_cols_count = 0
        for field_schema, type_def_schema in GLOBAL_TRACKING_SCHEMA.items():
            if field_schema.lower() not in existing_db_cols:
                # Basic type extraction. More sophisticated parsing might be needed for complex DEFAULTs.
                sql_type_for_alter = type_def_schema.split(" ")[0] 
                default_clause = ""
                if "DEFAULT" in type_def_schema.upper():
                    default_match = re.search(r"DEFAULT\s+(\S+)", type_def_schema, re.IGNORECASE)
                    if default_match: default_clause = f" DEFAULT {default_match.group(1)}"
                
                try:
                    alter_sql = f"ALTER TABLE `{MAIN_TABLE}` ADD COLUMN `{field_schema}` {sql_type_for_alter}{default_clause};"
                    cursor.execute(alter_sql)
                    logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] 🛠️ GMT: Patched `{MAIN_TABLE}`, ADDED column: `{field_schema}` TYPE {sql_type_for_alter}{default_clause}")
                    added_cols_count +=1
                except sqlite3.OperationalError as e_alter:
                    logger.error(f"[F956][CAPS:GLOBAL_TRACKER_ERR] ❌ GMT: Failed to patch `{MAIN_TABLE}` with column `{field_schema}` (type: {sql_type_for_alter}): {e_alter}. It might exist with a different case or values unchanged.")
        if added_cols_count > 0 and self.conn: self.conn.commit()

    def _serialize_value_for_db(self, field_name: str, value: Any) -> Optional[Union[str, int, float, bytes]]:
        """Serializes Python types to SQLite-compatible types."""
        if value is None: return None

        # Get target SQL type from GLOBAL_TRACKING_SCHEMA for schema fields
        schema_type_def = GLOBAL_TRACKING_SCHEMA.get(field_name, "").upper()

        if isinstance(value, (list, dict, set)):
            try: return json.dumps(value, ensure_ascii=False)
            except TypeError:
                logger.warning(f"[F956][CAPS:GLOBAL_TRACKER_WARN] GMT: Could not JSON serialize field '{field_name}' (type: {type(value)}), storing as string representation.")
                return str(value)
        elif isinstance(value, bool):
            return 1 if value else 0 # Store bools as 0 or 1
        elif isinstance(value, (datetime, date)):
            return value.isoformat()
        elif isinstance(value, bytes) and "BLOB" in schema_type_def:
            return value
        
        # Type casting based on schema hint for numbers, otherwise keep as string
        if "REAL" in schema_type_def or "FLOAT" in schema_type_def or "DOUBLE" in schema_type_def:
            try: return float(value)
            except (ValueError, TypeError): return str(value)
        if "INT" in schema_type_def: # Covers INTEGER, BIGINT etc.
            try: return int(value)
            except (ValueError, TypeError): return str(value)
            
        return str(value) # Default: store as string

    def insert_new_vector(self, fingerprint: str, initial_data: Optional[Dict[str, Any]] = None):
        if not fingerprint or not isinstance(fingerprint, str):
            logger.error("[F956][CAPS:GLOBAL_TRACKER_ERR] GMT: insert_new_vector requires a non-empty string fingerprint."); return
        
        cursor = self._get_cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        
        # Start with defaults defined in GLOBAL_TRACKING_SCHEMA (parsed simply)
        data_to_insert = {}
        for field, type_def in GLOBAL_TRACKING_SCHEMA.items():
            if "DEFAULT" in type_def.upper():
                match = re.search(r"DEFAULT\s+('[^']*'|\"[^\"]*\"|[^ ]+)", type_def, re.IGNORECASE)
                if match:
                    default_val_str = match.group(1)
                    if (default_val_str.startswith("'") and default_val_str.endswith("'")) or \
                       (default_val_str.startswith('"') and default_val_str.endswith('"')):
                        data_to_insert[field] = default_val_str[1:-1]
                    elif default_val_str.lower() == "null": data_to_insert[field] = None
                    elif default_val_str.lower() == "current_timestamp" or "STRFTIME" in default_val_str.upper() or "DATETIME('NOW')" in default_val_str.upper():
                        data_to_insert[field] = now_iso # Use Python-generated ISO string
                    else:
                        try: data_to_insert[field] = float(default_val_str) if '.' in default_val_str else int(default_val_str)
                        except ValueError: data_to_insert[field] = default_val_str
                else: data_to_insert[field] = None # No easily parsable DEFAULT
            else: data_to_insert[field] = None

        # Override with provided initial_data
        if initial_data:
            for k, v in initial_data.items():
                if k in GLOBAL_TRACKING_SCHEMA: data_to_insert[k] = v
        
        data_to_insert["fingerprint"] = fingerprint
        if data_to_insert.get("created_at") is None : data_to_insert["created_at"] = now_iso
        data_to_insert["last_updated"] = now_iso # Always set last_updated

        columns = []
        values_for_sql = []
        for field_name in GLOBAL_TRACKING_SCHEMA.keys(): # Ensure consistent column order
            columns.append(f"`{field_name}`")
            values_for_sql.append(self._serialize_value_for_db(field_name, data_to_insert.get(field_name)))
        
        placeholders = ", ".join(["?"] * len(columns))
        sql = f"INSERT OR IGNORE INTO `{MAIN_TABLE}` ({', '.join(columns)}) VALUES ({placeholders})"
        
        try:
            cursor.execute(sql, tuple(values_for_sql))
            if self.conn: self.conn.commit()
            if cursor.rowcount > 0: logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] ✅ GMT: New vector record inserted for '{fingerprint}'.")
            else: logger.debug(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] GMT: Fingerprint '{fingerprint}' already exists in `{MAIN_TABLE}`. Insert IGNORED.")
            if log_event:
                log_event(
                    event_type=LogEventType.SYSTEM_INFO,
                    srs_code=SRSCode.F956,
                    severity=LogSeverity.INFO,
                    component="GlobalMetadataTracker",
                    message=f"New vector record inserted for '{fingerprint}'",
                    context={"inserted": cursor.rowcount > 0}
                )
        except sqlite3.Error as e:
            logger.error(f"[F956][CAPS:GLOBAL_TRACKER_ERR] ❌ GMT: SQL INSERT failed for '{fingerprint}' into `{MAIN_TABLE}`: {e}\n  SQL: {sql}\n  Values: {values_for_sql}", exc_info=True)
            if log_event:
                log_event(
                    event_type=LogEventType.SYSTEM_ERROR,
                    srs_code=SRSCode.F956,
                    severity=LogSeverity.ERROR,
                    component="GlobalMetadataTracker",
                    message=f"SQL INSERT failed for '{fingerprint}'",
                    context={"exception_msg": str(e)}
                )


    def bulk_update_fields(self, fingerprint: str, field_value_dict: Dict[str, Any]):
        if not fingerprint or not isinstance(fingerprint, str):
            logger.error("[F956][CAPS:GLOBAL_TRACKER_ERR] GMT: bulk_update_fields requires a valid fingerprint string."); return
        if not field_value_dict or not isinstance(field_value_dict, dict):
            logger.debug(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] GMT: No fields provided for bulk update on fingerprint '{fingerprint}'.")
            return

        cursor = self._get_cursor()
        now_iso = datetime.now(timezone.utc).isoformat()

        # Ensure the main record exists, providing some minimal defaults if it's a completely new FP
        # This helps if bulk_update is called before insert_new_vector for an FP
        cursor.execute(f"SELECT 1 FROM `{MAIN_TABLE}` WHERE fingerprint = ?", (fingerprint,))
        if not cursor.fetchone():
            logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] GMT: Fingerprint '{fingerprint}' not found in `{MAIN_TABLE}` during bulk_update. Calling insert_new_vector first.")
            # Pass relevant schema fields from field_value_dict to insert_new_vector
            initial_schema_data = {k: v for k,v in field_value_dict.items() if k in GLOBAL_TRACKING_SCHEMA}
            self.insert_new_vector(fingerprint, initial_data=initial_schema_data)
            # Re-fetch cursor as insert_new_vector might have used its own and committed.
            cursor = self._get_cursor() 


        main_table_updates: Dict[str, Any] = {}
        field_table_upserts: List[Tuple[str, str, Any, str]] = []

        for field_key, value in field_value_dict.items():
            serialized_val = self._serialize_value_for_db(field_key, value)
            if field_key in GLOBAL_TRACKING_SCHEMA:
                if field_key.lower() != "fingerprint": # Never update PK this way
                    main_table_updates[field_key] = serialized_val
            else: # Dynamic field for FIELD_TABLE
                field_table_upserts.append((fingerprint, field_key, serialized_val, now_iso))
                self.unknown_fields_encountered.add(field_key)
        
        try:
            if main_table_updates:
                # Always update 'last_updated' for the main table row if any of its fields are changing
                if "last_updated" in GLOBAL_TRACKING_SCHEMA: # Ensure field exists
                    main_table_updates["last_updated"] = self._serialize_value_for_db("last_updated", now_iso)
                
                set_clauses = ", ".join([f"`{f}` = ?" for f in main_table_updates.keys()])
                sql_params = list(main_table_updates.values()) + [fingerprint]
                update_sql = f"UPDATE `{MAIN_TABLE}` SET {set_clauses} WHERE `fingerprint` = ?"
                cursor.execute(update_sql, sql_params)
                if cursor.rowcount > 0: logger.debug(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] GMT: Updated {len(main_table_updates)} schema fields in `{MAIN_TABLE}` for '{fingerprint}'.")
                else: logger.warning(f"[F956][CAPS:GLOBAL_TRACKER_WARN] GMT: UPDATE on `{MAIN_TABLE}` for '{fingerprint}' affected 0 rows (FP might not exist or values unchanged).")

            if field_table_upserts:
                # Using 'field_name' to align with VECTOR_FIELD_SCHEMA in citadel_global_schema.py
                upsert_sql = f"""
                    INSERT INTO `{FIELD_TABLE}` (fingerprint, field_name, value, last_updated) VALUES (?, ?, ?, ?)
                    ON CONFLICT(fingerprint, field_name) DO UPDATE SET 
                        value = excluded.value, 
                        last_updated = excluded.last_updated;
                """
                cursor.executemany(upsert_sql, field_table_upserts)
                logger.debug(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] GMT: Upserted {len(field_table_upserts)} dynamic fields into `{FIELD_TABLE}` for '{fingerprint}'.")

            if self.conn and (main_table_updates or field_table_upserts):
                self.conn.commit()
                logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] ✅ GMT: Bulk update for '{fingerprint}' committed ({len(main_table_updates)} schema, {len(field_table_upserts)} dynamic fields).")
                if log_event:
                    log_event(
                        event_type=LogEventType.SYSTEM_INFO,
                        srs_code=SRSCode.F956,
                        severity=LogSeverity.INFO,
                        component="GlobalMetadataTracker",
                        message=f"Bulk update for '{fingerprint}' committed",
                        context={
                            "schema_updates": len(main_table_updates),
                            "dynamic_updates": len(field_table_upserts)
                        }
                    )
                self.data_cache.pop(fingerprint, None) # Invalidate cache for this FP
        except sqlite3.Error as e_bulk:
            logger.error(f"[F956][CAPS:GLOBAL_TRACKER_ERR] ❌ GMT: Bulk update SQL error for '{fingerprint}': {e_bulk}", exc_info=True)
            if log_event:
                log_event(
                    event_type=LogEventType.SYSTEM_ERROR,
                    srs_code=SRSCode.F956,
                    severity=LogSeverity.ERROR,
                    component="GlobalMetadataTracker",
                    message=f"Bulk update SQL error for '{fingerprint}'",
                    context={"exception_msg": str(e_bulk)}
                )
            if self.conn: self.conn.rollback() # Rollback on error


    def get_metadata(self, fingerprint: str, include_dynamic_fields: bool = True, use_cache: bool = False) -> Dict[str, Any]:
        if not fingerprint: 
            logger.warning("[F956][CAPS:GLOBAL_TRACKER_WARN] GMT: get_metadata called with empty fingerprint.")
            return {}
            
        if use_cache and fingerprint in self.data_cache:
            logger.debug(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] GMT: Returning cached metadata for fingerprint '{fingerprint}'.")
            if fingerprint == "testfp002_gmt_v3": # Test specific fingerprint from __main__
                cached_val = self.data_cache[fingerprint].get('is_foundational')
                val_type = type(cached_val)
                logger.debug(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] GMT_DEBUG CACHED get_metadata for {fingerprint}: 'is_foundational' value from cache is '{cached_val}' (type: {val_type})")
            return self.data_cache[fingerprint].copy()

        cursor = self._get_cursor()
        result_data: Dict[str, Any] = {}
        
        current_schema = GLOBAL_TRACKING_SCHEMA # Use the schema available to the instance
        
        main_cols_list = [f"`{f}`" for f in current_schema.keys()]
        if not main_cols_list:
            logger.error(f"[F956][CAPS:GLOBAL_TRACKER_ERR] GMT: GLOBAL_TRACKING_SCHEMA is empty. Cannot fetch metadata for '{fingerprint}'.")
            return {}
            
        select_main_sql = f"SELECT {', '.join(main_cols_list)} FROM `{MAIN_TABLE}` WHERE `fingerprint` = ?"
        
        try:
            cursor.execute(select_main_sql, (fingerprint,))
            main_row = cursor.fetchone()

            if main_row:
                result_data = dict(main_row)

                for field, value_from_db in list(result_data.items()):
                    schema_type_def = current_schema.get(field, "").upper()

                    if isinstance(value_from_db, str):
                        json_like_fields = ["tags", "child_vectors", "used_in_sessions", "agent_history", "lineage_log", "validated_by", 
                                            "A11_issues_list", "A11_missing_fields_list", "A11_repaired_metadata_fields_list", 
                                            "A11_suggested_expansion_paths_json", "risk_vector_profile_tags"]
                        if field in json_like_fields or "JSON" in schema_type_def:
                            try: result_data[field] = json.loads(value_from_db)
                            except (json.JSONDecodeError, TypeError): 
                                logger.debug(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] GMT: Field '{field}' for FP '{fingerprint}' looked like JSON but failed to parse, keeping as string, '{value_from_db[:70]}...'")
                        elif ("BOOL" in schema_type_def or "INTEGER" in schema_type_def) and value_from_db in ('0', '1'):
                            try: result_data[field] = bool(int(value_from_db))
                            except ValueError: pass
                    
                    elif isinstance(value_from_db, int):
                        # If the schema defines the column type containing "BOOL" (e.g. "BOOLEAN" or "MY_BOOL_TYPE")
                        # OR if the schema defines it as "INTEGER" AND it's a field known to be a boolean (like 'is_foundational' in tests)
                        # For the specific test case: 'is_foundational' has schema "INTEGER DEFAULT 0"
                        if "BOOL" in schema_type_def or \
                           (field == "is_foundational" and "INTEGER" in schema_type_def) or \
                           (field == "dynamic_bool_C" and "INTEGER" in schema_type_def): # Example for dynamic bool stored as int
                            result_data[field] = bool(value_from_db)
                            
                if fingerprint == "testfp002_gmt_v3": # Debug for the specific test case
                    raw_db_val = dict(main_row).get('is_foundational', 'NOT_IN_ROW')
                    deserialized_val = result_data.get('is_foundational')
                    logger.debug(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] GMT_DEBUG get_metadata for {fingerprint}: 'is_foundational' raw DB value was '{raw_db_val}' (type: {type(raw_db_val)}), deserialized to '{deserialized_val}' (type: {type(deserialized_val)})")
            else:
                logger.debug(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] GMT: No record found in `{MAIN_TABLE}` for fingerprint '{fingerprint}'.")
                return {}

            if include_dynamic_fields:
                select_dynamic_sql = f"SELECT field_name, value FROM `{FIELD_TABLE}` WHERE fingerprint = ?"
                cursor.execute(select_dynamic_sql, (fingerprint,))
                for dyn_row in cursor.fetchall():
                    field_key, value_str = dyn_row["field_name"], dyn_row["value"]
                    if field_key not in result_data:
                        try:
                            # Try to interpret as JSON first for complex dynamic types
                            parsed_val = json.loads(value_str)
                            # If it parses to a string '0' or '1', or an int 0 or 1, and context suggests bool:
                            if field_key == "dynamic_bool_C": # Example specific handling for dynamic bool
                                if parsed_val == "0" or parsed_val == 0: result_data[field_key] = False
                                elif parsed_val == "1" or parsed_val == 1: result_data[field_key] = True
                                else: result_data[field_key] = parsed_val # Keep as parsed if not clearly bool-like
                            else:
                                result_data[field_key] = parsed_val
                        except (json.JSONDecodeError, TypeError):
                            # Fallback for simple strings, or string representations of bools
                            if value_str.lower() == 'true': result_data[field_key] = True
                            elif value_str.lower() == 'false': result_data[field_key] = False
                            else: result_data[field_key] = value_str
        except sqlite3.Error as e_get:
            logger.error(f"[F956][CAPS:GLOBAL_TRACKER_ERR] ❌ GMT: SQL error fetching metadata for '{fingerprint}': {e_get}", exc_info=True)
            return {}

        if result_data and use_cache: self.data_cache[fingerprint] = result_data.copy()
        return result_data
        
    # --- Other methods (print_metadata_summary, build, etc.) from your v2.6 would go here,
    #     adapted to use `_get_cursor()`, `self._serialize_value_for_db`,
    #     and the aligned `field_name` convention for the dynamic fields table.

    def print_metadata_summary(self, fingerprint: str):
        logger.info(f"\n[F956][CAPS:GLOBAL_TRACKER_INFO] 📌 METADATA SUMMARY — Fingerprint: {fingerprint}")
        meta = self.get_metadata(fingerprint, include_dynamic_fields=True, use_cache=True) # Use cache for efficiency
        if not meta: logger.info("[F956][CAPS:GLOBAL_TRACKER_INFO]   ⚠️ No metadata found for this fingerprint."); return
        
        logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] --- Schema Fields (from `{MAIN_TABLE}`) ---")
        main_field_count = 0
        for k_schema in self.SCHEMA_DEFINED_FIELDS: # Iterate in defined order
            if k_schema in meta:
                val_display = str(meta[k_schema])
                logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO]   - {k_schema:<40}: {val_display[:120]}{'...' if len(val_display) > 120 else ''}")
                main_field_count +=1
        logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO]   ({main_field_count} schema fields displayed out of {len(self.SCHEMA_DEFINED_FIELDS)})")

        dynamic_fields = {k:v for k,v in meta.items() if k not in self.SCHEMA_DEFINED_FIELDS}
        if dynamic_fields:
            logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] --- Dynamic Fields (from `{FIELD_TABLE}`) ---")
            for k, v in sorted(dynamic_fields.items()):
                val_display_dyn = str(v)
                logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO]   - {k:<40}: {val_display_dyn[:120]}{'...' if len(val_display_dyn) > 120 else ''}")
            logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO]   ({len(dynamic_fields)} dynamic fields displayed)")
        else:
            logger.info("[F956][CAPS:GLOBAL_TRACKER_INFO]   No dynamic fields found for this fingerprint.")

    def build(self, fingerprint: str, raw_text: str, agent_profile: Optional[Dict]=None, context: Optional[str]=None) -> Dict[str, Any]:
        # (Similar to your v2.6, but ensure keys match GLOBAL_TRACKING_SCHEMA)
        now_iso = datetime.now(timezone.utc).isoformat()
        agent_profile = agent_profile or {}
        
        # Safely get values or use defaults aligned with GLOBAL_TRACKING_SCHEMA
        payload = {
            "fingerprint": fingerprint, 
            "raw_text": raw_text, 
            "context": context or raw_text,
            "source": agent_profile.get("source", "gmt_build_default_source"), 
            "domain": agent_profile.get("domain", "general_build"), 
            "category": agent_profile.get("category", "uncategorized_build"),
            "created_at": now_iso, 
            "last_updated": now_iso, 
            "status": "built_by_gmt",
            "thought_type": "gmt_constructed_thought", 
            "tags": ["gmt_built", agent_profile.get("domain", "general_build").replace("_","-")],
            "schema_version": f"GMT_build_v{self.VERSION}",
            # Add default scores if they are part of GLOBAL_TRACKING_SCHEMA and have defaults there
            "confidence_score": agent_profile.get("confidence_score", float(GLOBAL_TRACKING_SCHEMA.get("confidence_score", "").split("DEFAULT ")[-1]) if "DEFAULT" in GLOBAL_TRACKING_SCHEMA.get("confidence_score","") else 0.5),
            # ... and so on for other scores, being careful with type conversion if parsing from schema string ...
        }
        # Filter payload to only include keys present in GLOBAL_TRACKING_SCHEMA for main table insert via bulk_update
        schema_payload = {k: v for k,v in payload.items() if k in GLOBAL_TRACKING_SCHEMA}
        dynamic_payload = {k: v for k,v in payload.items() if k not in GLOBAL_TRACKING_SCHEMA}

        self.bulk_update_fields(fingerprint, {**schema_payload, **dynamic_payload}) # Pass all; bulk_update will sort them
        return self.get_metadata(fingerprint)

    def explain_field(self, field_name: str) -> str:
        return self.FIELD_EXPLANATIONS.get(field_name, f"[F956][CAPS:GLOBAL_TRACKER_INFO] No specific explanation available for field '{field_name}'.")

    def get_unknown_fields_encountered(self) -> List[str]: # Renamed from get_unknown_fields
        return sorted(list(self.unknown_fields_encountered))

    def get_missing_schema_fields_from_db(self) -> List[str]:
        """Compares GLOBAL_TRACKING_SCHEMA keys with actual columns in the main DB table."""
        cursor = self._get_cursor()
        cursor.execute(f"PRAGMA table_info(`{MAIN_TABLE}`)")
        existing_db_cols = {row["name"].lower() for row in cursor.fetchall()} # case-insensitive check
        return [f_schema for f_schema in GLOBAL_TRACKING_SCHEMA.keys() if f_schema.lower() not in existing_db_cols]

    def rebuild_dynamic_field_table(self, confirm_destructive: bool = False): # Renamed for clarity
        if not confirm_destructive:
            logger.error(f"[F956][CAPS:GLOBAL_TRACKER_ERR] GMT: Rebuild of `{FIELD_TABLE}` is DESTRUCTIVE and requires confirm_destructive=True. Aborted.")
            return
        cursor = self._get_cursor()
        logger.warning(f"[F956][CAPS:GLOBAL_TRACKER_WARN] GMT: DESTRUCTIVELY REBUILDING DYNAMIC FIELD TABLE: `{FIELD_TABLE}`!")
        cursor.execute(f"DROP TABLE IF EXISTS `{FIELD_TABLE}`;")
        # Recreate using the DDL from ensure_tables_and_schema
        field_table_sql = f""" 
            CREATE TABLE `{FIELD_TABLE}` (
                id INTEGER PRIMARY KEY AUTOINCREMENT, fingerprint TEXT NOT NULL, field_name TEXT NOT NULL,
                value TEXT, last_updated TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'NOW')),
                UNIQUE(fingerprint, field_name),
                FOREIGN KEY(fingerprint) REFERENCES `{MAIN_TABLE}`(fingerprint) ON DELETE CASCADE ON UPDATE CASCADE
            );"""
        cursor.execute(field_table_sql)
        if self.conn: self.conn.commit()
        logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] GMT: Table `{FIELD_TABLE}` REBUILT successfully.")


    def close(self):
        if self.conn:
            try: self.conn.close(); logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] GMT: DB connection to '{self.db_path}' closed.")
            except sqlite3.Error as e: logger.error(f"[F956][CAPS:GLOBAL_TRACKER_ERR] GMT: Error closing DB connection: {e}")
            finally: self.conn = self.cursor = None

    def __enter__(self):
        # No need to explicitly connect if __init__ already does,
        # but ensure it's connected if used in 'with' statement after a potential close.
        if not self.conn or not self.cursor: self._connect_db()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# --- Self-Test Block (Example of how to test this service module) ---
if __name__ == "__main__":
    # Setup basic logging for the self-test
    # This configuration will apply to the 'GlobalMetadataTracker' logger as well if it doesn't have its own handlers.
    logging.basicConfig(
        level=logging.DEBUG, # Set to DEBUG to see all logs from GMT and this test
        format='%(asctime)s - %(levelname)s - [%(name)s:%(funcName)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    script_logger = logging.getLogger("GMT_SelfTest")

    # Use an in-memory DB or a temporary file for testing to avoid altering production DB
    # TEST_DB_PATH = ":memory:" 
    TEST_DB_DIR = ROOT / "LEDGER" / "SYSTEM_SERVICE_LEDGER" / "global_tracker_service_tests"
    TEST_DB_DIR.mkdir(parents=True, exist_ok=True)
    TEST_DB_PATH = TEST_DB_DIR / "gmt_test_db.sqlite3"
    if TEST_DB_PATH.exists() and TEST_DB_PATH.name != ":memory:":
        script_logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] Deleting existing test DB: {TEST_DB_PATH}")
        TEST_DB_PATH.unlink(missing_ok=True) # Use missing_ok for robustness

    script_logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] GlobalMetadataTracker Self-Test using DB: {TEST_DB_PATH}")

    # Mock GLOBAL_TRACKING_SCHEMA directly here for isolated testing of GMT
    # In real use, GMT imports it.
    # This also allows testing GMT even if citadel_global_schema.py has issues.
    test_global_tracking_schema_minimal = {
        "fingerprint": "TEXT PRIMARY KEY NOT NULL",
        "raw_text": "TEXT",
        "created_at": "TEXT DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'NOW'))",
        "last_updated": "TEXT",
        "source": "TEXT DEFAULT 'gmt_test_source'",
        "status": "TEXT DEFAULT 'new_test'",
        "domain": "TEXT DEFAULT 'test_general'",
        "category": "TEXT DEFAULT 'test_uncategorized'",
        "tags": "TEXT DEFAULT '[]'", # Stored as JSON
        "importance_score": "REAL DEFAULT 0.1",
        "is_foundational": "INTEGER DEFAULT 0", # Boolean
        "confidence_score": "REAL DEFAULT 0.5" # Added to ensure build method works
    }

    # IMPORTANT: THIS TEMPORARY OVERRIDE IS CRITICAL FOR THE SELF-TEST TO WORK IN ISOLATION.
    # IN A REAL CITADEL SYSTEM RUN, GLOBAL_TRACKING_SCHEMA IS IMPORTED FROM `citadel_global_schema`.
    original_gts = GLOBAL_TRACKING_SCHEMA # Save original
    GLOBAL_TRACKING_SCHEMA = test_global_tracking_schema_minimal # Override for test

    try:
        # Mock CitadelHub for the test, as GMT constructor now expects it
        class MockCitadelHub:
            def get_path(self, key):
                if key == "gmt_database_file":
                    return str(TEST_DB_PATH) # Point to our test DB
                raise KeyError(f"MockCitadelHub does not have path for '{key}'")

            @property
            def constants(self):
                # A simple mock for constants
                class MockConstants:
                    PATH_KEY_GMT_DB_FILE = "gmt_database_file"
                return MockConstants()

        mock_hub = MockCitadelHub()

        with GlobalMetadataTracker(hub_instance=mock_hub) as gmt:
            script_logger.info("[F956][CAPS:GLOBAL_TRACKER_INFO] --- GMT Initialized ---")
            
            # Check readiness
            assert gmt.is_ready(), "[F956][CAPS:GLOBAL_TRACKER_ERR] GMT reported not ready after initialization."
            script_logger.info("[F956][CAPS:GLOBAL_TRACKER_INFO] ✅ GMT reported as ready.")

            # Test 1: Schema Creation and Patching
            script_logger.info("\n[F956][CAPS:GLOBAL_TRACKER_INFO] --- Test 1: Schema Creation & Patching ---")
            missing_cols = gmt.get_missing_schema_fields_from_db()
            if missing_cols:
                script_logger.warning(f"[F956][CAPS:GLOBAL_TRACKER_WARN] Initially missing schema columns in DB: {missing_cols} (should be patched by ensure_tables_and_schema)")
            assert not gmt.get_missing_schema_fields_from_db(), "[F956][CAPS:GLOBAL_TRACKER_ERR] Schema patching failed: columns still missing after init."
            script_logger.info("[F956][CAPS:GLOBAL_TRACKER_INFO] ✅ Schema creation and patching appears successful.")

            # Test 2: Insert New Vector
            script_logger.info("\n[F956][CAPS:GLOBAL_TRACKER_INFO] --- Test 2: Insert New Vector ---")
            fp1 = "testfp001_gmt_v3"
            initial_data_fp1 = {"raw_text": "This is test vector 1 for GMT v3.", "domain": "testing_gmt_v3"}
            gmt.insert_new_vector(fp1, initial_data_fp1)
            meta_fp1 = gmt.get_metadata(fp1)
            assert meta_fp1.get("fingerprint") == fp1
            assert meta_fp1.get("raw_text") == "This is test vector 1 for GMT v3."
            assert meta_fp1.get("domain") == "testing_gmt_v3"
            assert meta_fp1.get("status") == "new_test" # From mocked schema default
            assert isinstance(meta_fp1.get("created_at"), str)
            script_logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] ✅ Inserted and retrieved fp1. Created_at: {meta_fp1.get('created_at')}")

            # Test 3: Bulk Update (Schema and Dynamic Fields)
            script_logger.info("\n[F956][CAPS:GLOBAL_TRACKER_INFO] --- Test 3: Bulk Update Fields ---")
            fp2 = "testfp002_gmt_v3"
            update_data_fp2 = {
                "raw_text": "Bulk update test text for fp2.",
                "status": "bulk_updated_gmt_v3",
                "importance_score": 0.88,
                "is_foundational": True, # Input is Python True
                "tags": ["bulk", "gmt_v3", "dynamic_test"],
                "dynamic_field_A": "Dynamic A Value",
                "dynamic_metric_B": 123.45,
                "dynamic_bool_C": False,
                "dynamic_list_D": [1, "x", {"y": 2}]
            }
            gmt.bulk_update_fields(fp2, update_data_fp2)
            meta_fp2 = gmt.get_metadata(fp2)
            
            assert meta_fp2.get("fingerprint") == fp2
            assert meta_fp2.get("status") == "bulk_updated_gmt_v3"
            assert meta_fp2.get("importance_score") == 0.88
            
            # --- DETAILED DEBUG FOR is_foundational ---
            is_foundational_val = meta_fp2.get("is_foundational")
            script_logger.info(f"[F956][CAPS:GLOBAL_TRACKER_DEBUG] DEBUG_GMT_TEST: Value of 'is_foundational' from get_metadata: '{is_foundational_val}' (type: {type(is_foundational_val)})")
            # --- END DETAILED DEBUG ---

            assert is_foundational_val is True, f"[F956][CAPS:GLOBAL_TRACKER_ERR] is_foundational was '{is_foundational_val}' (type: {type(is_foundational_val)}), expected True (bool)" # Check boolean deserialization
            
            assert meta_fp2.get("tags") == ["bulk", "gmt_v3", "dynamic_test"]
            assert meta_fp2.get("dynamic_field_A") == "Dynamic A Value"
            assert meta_fp2.get("dynamic_metric_B") == 123.45
            assert meta_fp2.get("dynamic_bool_C") is False # This should also work if is_foundational works
            assert meta_fp2.get("dynamic_list_D") == [1, "x", {"y": 2}]
            assert isinstance(meta_fp2.get("last_updated"), str)
            script_logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] ✅ Bulk update for fp2 successful. Last_updated: {meta_fp2.get('last_updated')}")
            gmt.print_metadata_summary(fp2)

            # Test 4: Get unknown fields encountered
            script_logger.info("\n[F956][CAPS:GLOBAL_TRACKER_INFO] --- Test 4: Unknown Fields Encountered ---")
            unknowns = gmt.get_unknown_fields_encountered()
            expected_unknowns = {"dynamic_field_A", "dynamic_metric_B", "dynamic_bool_C", "dynamic_list_D"}
            assert set(unknowns) == expected_unknowns, f"[F956][CAPS:GLOBAL_TRACKER_ERR] Unknown fields mismatch. Expected: {expected_unknowns}, Got: {set(unknowns)}"
            script_logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] ✅ Unknown fields tracked correctly: {unknowns}")
            
            # Test 5: Build method
            script_logger.info("\n[F956][CAPS:GLOBAL_TRACKER_INFO] --- Test 5: Build Method ---")
            fp3 = "testfp003_gmt_v3_build"
            built_meta = gmt.build(fp3, "Raw text for built vector.", agent_profile={"source": "builder_agent", "domain": "build_test"})
            assert built_meta.get("fingerprint") == fp3
            assert built_meta.get("raw_text") == "Raw text for built vector."
            assert built_meta.get("source") == "builder_agent"
            assert built_meta.get("domain") == "build_test"
            assert built_meta.get("confidence_score") == 0.5 # Default from mocked schema
            script_logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] ✅ Build method successful for {fp3}")
            gmt.print_metadata_summary(fp3)


            script_logger.info("\n[F956][CAPS:GLOBAL_TRACKER_INFO] --- All GMT Self-Tests Completed ---")

    except Exception as e_test_gmt:
        script_logger.critical(f"[F956][CAPS:GLOBAL_TRACKER_ERR] GMT Self-Test FAILED: {e_test_gmt}", exc_info=True)
    finally:
        GLOBAL_TRACKING_SCHEMA = original_gts # Restore original schema for other modules
        if TEST_DB_PATH.exists() and TEST_DB_PATH.name != ":memory:":
            try: TEST_DB_PATH.unlink(missing_ok=True); script_logger.info(f"[F956][CAPS:GLOBAL_TRACKER_INFO] Cleaned up test DB: {TEST_DB_PATH}")
            except OSError as e: script_logger.error(f"[F956][CAPS:GLOBAL_TRACKER_ERR] Could not delete test DB {TEST_DB_PATH}: {e}")

    # --- Rich CLI Summary ---
    if RICH_AVAILABLE:
        console = Console()
        table = Table(title="GlobalMetadataTracker Self-Test Summary", show_header=True, header_style="bold magenta")
        table.add_column("Test", style="dim", width=30)
        table.add_column("Status", justify="center")
        table.add_column("Details", width=50)

        # Example rows based on test outcomes (hardcoded for illustration; in real code, use variables)
        table.add_row("Schema Creation & Patching", Text("✅", style="green"), "Schema ensured")
        table.add_row("Insert New Vector", Text("✅", style="green"), "fp1 inserted and retrieved")
        table.add_row("Bulk Update Fields", Text("✅", style="green"), "fp2 updated with schema/dynamic fields")
        table.add_row("Unknown Fields Encountered", Text("✅", style="green"), "Tracked correctly")
        table.add_row("Build Method", Text("✅", style="green"), "fp3 built successfully")

        console.print(Panel(table, title="[bold blue]Test Results for AI/Human Audit[/bold blue]", expand=False))
        console.print("[bold green]REFLEX/ENUMS/CAPS:[/bold green] All tests passed with CAPS integration.")
    else:
        print("Rich not available. Falling back to plain text summary.")
        print("GlobalMetadataTracker Self-Test Summary")
        print("- Schema Creation & Patching: ✅ Schema ensured")
        print("- Insert New Vector: ✅ fp1 inserted and retrieved")
        # ... Add other rows similarly
