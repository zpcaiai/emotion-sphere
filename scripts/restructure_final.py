#!/usr/bin/env python3
"""
Final restructure of seed_all.sql:
1. Fix SQL syntax issues (unescaped quotes)
2. Add user_tokens test data
3. Split into per-table transactions with correct FK dependency order
"""
import re
from pathlib import Path
from collections import OrderedDict

SQL_PATH = Path('/Users/stephen/Documents/python/emotion-sphere/backend/seed_all.sql')

# User tokens test data to inject
USER_TOKENS_DATA = """INSERT INTO user_tokens (token, email, data, created_at, expires_at) VALUES
('tok_alice_001', 'alice@example.com', '{"id":1,"nickname":"Alice"}', '2025-01-10 08:05:00', '2025-02-10 08:05:00'),
('tok_bob_001', 'bob@example.com', '{"id":2,"nickname":"Bob"}', '2025-01-15 10:35:00', '2025-02-15 10:35:00'),
('tok_charlie_001', 'charlie@example.com', '{"id":3,"nickname":"Charlie"}', '2025-02-01 14:00:00', '2025-03-01 14:00:00'),
('tok_alice_002', 'alice@example.com', '{"id":1,"nickname":"Alice"}', '2025-03-01 09:00:00', '2025-04-01 09:00:00'),
('tok_diana_001', 'diana@example.com', '{"id":4,"nickname":"Diana"}', '2025-02-20 09:10:00', '2025-03-20 09:10:00');"""

# Schema creation order (FK dependency topological sort)
SCHEMA_ORDER = [
    # Level 0: no FK deps
    "users",
    "security_audit",
    "user_tokens",
    "system_state_definitions",
    "data_bus_events",
    # Level 1: depends on users
    "prayers",
    "evangelism_prayers",
    "devotion_journals",
    "sermon_journals",
    "personal_notes",
    "checkins",
    "emotion_logs",
    "cognitive_schemas",
    "psychological_states",
    "habit_state_machines",
    "execution_paralysis_logs",
    "behavior_regulation_sessions",
    "growth_trajectories",
    "pattern_recognitions",
    "memory_consolidations",
    "self_concept_models",
    "identity_narratives",
    "personality_migrations",
    "user_system_states",
    "user_token_ledgers",
    "state_transition_logs",
    "dynamic_load_configs",
    "implementation_intentions",
    "edge_intervention_analytics",
    "behavioral_triggers",
    # Level 2: depends on level 0+1
    "prayer_amens",
    "evangelism_amens",
    "personality_drivers",
    "behavioral_experiments",
    "habit_execution_logs",
    "micro_scheduler_sessions",
    # Level 3: depends on level 2
    "intervention_logs",
    "token_transactions",
    "identity_reinforcement_logs",
]

# Data insertion order (same logic)
DATA_ORDER = SCHEMA_ORDER[:]


def parse_schema_blocks(lines):
    """Extract CREATE TABLE blocks with their associated indexes/triggers."""
    blocks = OrderedDict()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('CREATE TABLE IF NOT EXISTS'):
            m = re.match(r'CREATE TABLE IF NOT EXISTS (\w+)', line)
            if m:
                tbl = m.group(1)
                block_lines = [lines[i]]
                i += 1
                # Collect subsequent INDEX, TRIGGER, DROP TRIGGER lines
                while i < len(lines):
                    next_line = lines[i].strip()
                    if (next_line.startswith('CREATE INDEX') or 
                        next_line.startswith('CREATE UNIQUE INDEX') or
                        next_line.startswith('CREATE TRIGGER') or
                        next_line.startswith('DROP TRIGGER')):
                        block_lines.append(lines[i])
                        i += 1
                    elif not next_line:
                        i += 1
                        break
                    else:
                        break
                blocks[tbl] = block_lines
            else:
                i += 1
        else:
            i += 1
    return blocks


def parse_insert_statements(lines):
    """Parse INSERT statements, handling multi-line VALUES."""
    table_inserts = OrderedDict()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped.startswith('INSERT INTO'):
            m = re.match(r'INSERT INTO (\w+)', stripped)
            if m:
                tbl = m.group(1)
                stmt_lines = [line]
                
                # Check if it's complete on this line
                if stripped.endswith(';'):
                    table_inserts.setdefault(tbl, []).append('\n'.join(stmt_lines))
                    i += 1
                    continue
                
                # Multi-line statement - collect until ;
                i += 1
                while i < len(lines):
                    next_stripped = lines[i].strip()
                    if not next_stripped:
                        i += 1
                        continue
                    stmt_lines.append(lines[i])
                    if next_stripped.endswith(';'):
                        break
                    i += 1
                
                table_inserts.setdefault(tbl, []).append('\n'.join(stmt_lines))
                i += 1
            else:
                i += 1
        else:
            i += 1
    return table_inserts


def main():
    text = SQL_PATH.read_text(encoding='utf-8')
    
    # Fix unescaped single quotes
    text = text.replace("everyone's expectations", "everyone''s expectations")
    
    lines = text.split('\n')
    
    # Remove outer BEGIN/COMMIT
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped == 'BEGIN;' or stripped == 'COMMIT;':
            continue
        clean_lines.append(line)
    
    # Extract setup (extensions + functions)
    setup_lines = []
    schema_start = 0
    for i, line in enumerate(clean_lines):
        stripped = line.strip()
        if stripped.startswith('CREATE EXTENSION') or stripped.startswith('CREATE OR REPLACE FUNCTION'):
            setup_lines.append(line)
        elif stripped.startswith('CREATE TABLE'):
            schema_start = i
            break
    
    # Parse schema blocks
    schema_blocks = parse_schema_blocks(clean_lines[schema_start:])
    
    # Find where INSERT statements start
    insert_start = 0
    for i, line in enumerate(clean_lines):
        if line.strip().startswith('INSERT INTO'):
            insert_start = i
            break
    
    # Parse INSERT statements
    insert_blocks = parse_insert_statements(clean_lines[insert_start:])
    
    # Add user_tokens data
    insert_blocks.setdefault('user_tokens', []).append(USER_TOKENS_DATA)
    
    # Build final output
    out = []
    out.append("-- ============================================================")
    out.append("-- Emotion Sphere — full schema + linked test data")
    out.append("-- Each CREATE TABLE and each table's INSERTs in separate transactions")
    out.append("-- Tables ordered by FK dependency (parents before children)")
    out.append("-- psql $DATABASE_URL -f backend/seed_all.sql")
    out.append("-- ============================================================")
    out.append("")
    
    # Setup transaction
    out.append("-- Setup: extensions and functions")
    out.append("BEGIN;")
    for line in setup_lines:
        out.append(line)
    out.append("COMMIT;")
    out.append("")
    
    # Schema section
    out.append("-- ============================================================")
    out.append("-- Schema Creation (one transaction per table, dependency-ordered)")
    out.append("-- ============================================================")
    out.append("")
    
    written_schema = set()
    for tbl in SCHEMA_ORDER:
        if tbl in schema_blocks:
            out.append(f"-- Table: {tbl}")
            out.append("BEGIN;")
            for line in schema_blocks[tbl]:
                out.append(line)
            out.append("COMMIT;")
            out.append("")
            written_schema.add(tbl)
    
    # Any schema blocks not in our order
    for tbl in schema_blocks:
        if tbl not in written_schema:
            print(f"WARNING: schema for '{tbl}' not in SCHEMA_ORDER")
            out.append(f"-- Table: {tbl}")
            out.append("BEGIN;")
            for line in schema_blocks[tbl]:
                out.append(line)
            out.append("COMMIT;")
            out.append("")
    
    # Data section
    out.append("-- ============================================================")
    out.append("-- Test Data (one transaction per table, dependency-ordered)")
    out.append("-- ============================================================")
    out.append("")
    
    written_data = set()
    for tbl in DATA_ORDER:
        if tbl in insert_blocks:
            out.append(f"-- Data for: {tbl}")
            out.append("BEGIN;")
            for stmt in insert_blocks[tbl]:
                out.append(stmt)
            out.append("COMMIT;")
            out.append("")
            written_data.add(tbl)
    
    # Any data not in our order
    for tbl in insert_blocks:
        if tbl not in written_data:
            print(f"WARNING: data for '{tbl}' not in DATA_ORDER")
            out.append(f"-- Data for: {tbl}")
            out.append("BEGIN;")
            for stmt in insert_blocks[tbl]:
                out.append(stmt)
            out.append("COMMIT;")
            out.append("")
    
    result = '\n'.join(out) + '\n'
    SQL_PATH.write_text(result, encoding='utf-8')
    
    line_count = result.count('\n')
    print(f"✅ Done. {line_count} lines written.")
    print(f"   Schema tables: {len(schema_blocks)}")
    print(f"   Data tables: {len(insert_blocks)}")
    print(f"\n   Data summary:")
    for tbl in DATA_ORDER:
        if tbl in insert_blocks:
            print(f"   {tbl}: {len(insert_blocks[tbl])} statement(s)")


if __name__ == '__main__':
    main()
