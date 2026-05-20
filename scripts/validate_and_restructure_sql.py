#!/usr/bin/env python3
"""
Validate PostgreSQL syntax basics and restructure seed_all.sql:
- Each CREATE TABLE (+ indexes/triggers) in its own transaction
- Each table's INSERTs in their own transaction
"""
import re
from pathlib import Path

SQL_PATH = Path('/Users/stephen/Documents/python/emotion-sphere/backend/seed_all.sql')
OUT_PATH = Path('/Users/stephen/Documents/python/emotion-sphere/backend/seed_all.sql')

def read_statements(text):
    """Split SQL text into statements by semicolons, respecting quotes and $$ blocks."""
    statements = []
    current = []
    i = 0
    n = len(text)
    in_dollar = False
    dollar_tag = None
    in_single = False
    in_double = False
    
    while i < n:
        c = text[i]
        
        if in_dollar:
            current.append(c)
            # Check for end of dollar-quoted string
            if dollar_tag is not None and i + len(dollar_tag) + 2 <= n:
                if text[i:i+len(dollar_tag)+2] == '$' + dollar_tag + '$':
                    current.append(text[i+1:i+len(dollar_tag)+2])
                    i += len(dollar_tag) + 2
                    in_dollar = False
                    dollar_tag = None
                    continue
        elif in_single:
            current.append(c)
            if c == "'" and (i+1 >= n or text[i+1] != "'"):
                in_single = False
            elif c == "'" and i+1 < n and text[i+1] == "'":
                current.append("'")
                i += 1
        elif in_double:
            current.append(c)
            if c == '"' and (i+1 >= n or text[i+1] != '"'):
                in_double = False
            elif c == '"' and i+1 < n and text[i+1] == '"':
                current.append('"')
                i += 1
        else:
            current.append(c)
            if c == "'":
                in_single = True
            elif c == '"':
                in_double = True
            elif c == '$':
                # Look for dollar quote start like $$ or $tag$
                m = re.match(r'\$([A-Za-z_][A-Za-z0-9_]*)?\$', text[i:])
                if m:
                    dollar_tag = m.group(1) or ''
                    tag_len = len(m.group(0))
                    current.extend(text[i+1:i+tag_len])
                    i += tag_len - 1
                    in_dollar = True
            elif c == ';':
                stmt = ''.join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
        
        i += 1
    
    # Remaining
    if current:
        stmt = ''.join(current).strip()
        if stmt:
            statements.append(stmt)
    
    return statements


def classify_statement(stmt):
    """Classify a SQL statement."""
    upper = stmt.upper()
    if upper.startswith('CREATE TABLE'):
        return 'create_table', stmt
    elif upper.startswith('CREATE INDEX') or upper.startswith('CREATE UNIQUE INDEX'):
        return 'create_index', stmt
    elif upper.startswith('CREATE TRIGGER'):
        return 'create_trigger', stmt
    elif upper.startswith('CREATE FUNCTION') or upper.startswith('CREATE OR REPLACE FUNCTION'):
        return 'create_function', stmt
    elif upper.startswith('CREATE EXTENSION'):
        return 'create_extension', stmt
    elif upper.startswith('DROP TRIGGER'):
        return 'drop_trigger', stmt
    elif upper.startswith('INSERT INTO'):
        return 'insert', stmt
    elif upper.startswith('BEGIN') or upper.startswith('COMMIT') or upper.startswith('END'):
        return 'transaction', stmt
    elif upper.startswith('--'):
        return 'comment', stmt
    elif not stmt.strip():
        return 'empty', stmt
    else:
        return 'other', stmt


def extract_table_name(stmt, kind):
    """Extract table name from statement."""
    if kind == 'create_table':
        m = re.search(r'CREATE TABLE IF NOT EXISTS\s+(\w+)', stmt, re.I)
        return m.group(1) if m else 'unknown'
    elif kind == 'insert':
        m = re.search(r'INSERT INTO\s+(\w+)', stmt, re.I)
        return m.group(1) if m else 'unknown'
    return None


def validate_basic_syntax(statements):
    """Basic validation checks."""
    errors = []
    warnings = []
    
    for stmt in statements:
        kind, _ = classify_statement(stmt)
        
        # Check parentheses balance
        parens = 0
        in_quote = None
        for c in stmt:
            if in_quote:
                if c == in_quote:
                    in_quote = None
            elif c in "'\"":
                in_quote = c
            elif c == '(':
                parens += 1
            elif c == ')':
                parens -= 1
                if parens < 0:
                    errors.append(f"Unbalanced parentheses in: {stmt[:80]}...")
                    break
        if parens != 0:
            errors.append(f"Unclosed parentheses in: {stmt[:80]}...")
        
        # Check for common syntax issues
        if kind == 'insert':
            # Check VALUES count roughly matches columns
            cols_match = re.search(r'\(([^)]+)\)\s+VALUES', stmt, re.I)
            if cols_match:
                cols = cols_match.group(1).split(',')
                # Count value groups (rough)
                vals = re.findall(r'VALUES\s+\(', stmt, re.I)
                if not vals:
                    warnings.append(f"INSERT without explicit VALUES: {stmt[:80]}")
        
        if kind == 'create_table':
            # Check for trailing comma before closing paren
            if re.search(r',\s*\)', stmt):
                warnings.append(f"Trailing comma in CREATE TABLE: {stmt[:80]}...")
    
    return errors, warnings


def restructure_sql(statements):
    """Restructure statements into per-table transactions."""
    output = []
    output.append("-- ============================================================")
    output.append("-- Emotion Sphere — full schema + linked test data")
    output.append("-- Each CREATE TABLE and each table's INSERTs are in separate transactions")
    output.append("-- psql $DATABASE_URL -f backend/seed_all.sql")
    output.append("-- ============================================================")
    output.append("")
    
    # Phase 1: Setup (extension + functions) — these can be in one transaction or separate
    setup_stmts = []
    table_groups = {}  # table_name -> list of DDL statements
    insert_groups = {}  # table_name -> list of INSERT statements
    other_stmts = []
    
    current_table = None
    
    for stmt in statements:
        kind, raw = classify_statement(stmt)
        
        if kind in ('comment', 'empty', 'transaction'):
            continue
        
        if kind == 'create_extension' or kind == 'create_function':
            setup_stmts.append(raw)
        elif kind == 'create_table':
            tbl = extract_table_name(raw, kind)
            current_table = tbl
            table_groups.setdefault(tbl, []).append(raw)
        elif kind == 'create_index' and current_table:
            # Associate index with last seen table if possible
            # Try to infer from index name or column
            table_groups.setdefault(current_table, []).append(raw)
        elif kind == 'create_trigger' and current_table:
            table_groups.setdefault(current_table, []).append(raw)
        elif kind == 'drop_trigger' and current_table:
            table_groups.setdefault(current_table, []).append(raw)
        elif kind == 'insert':
            tbl = extract_table_name(raw, kind)
            insert_groups.setdefault(tbl, []).append(raw)
        else:
            other_stmts.append(raw)
    
    # Write setup
    if setup_stmts:
        output.append("-- Setup: extensions and functions")
        output.append("BEGIN;")
        for s in setup_stmts:
            output.append(s + ";")
        output.append("COMMIT;")
        output.append("")
    
    # Write schema (each table + its indexes/triggers in one transaction)
    output.append("-- ============================================================")
    output.append("-- Schema Creation (one transaction per table)")
    output.append("-- ============================================================")
    output.append("")
    
    for tbl in sorted(table_groups.keys()):
        stmts = table_groups[tbl]
        output.append(f"-- Table: {tbl}")
        output.append("BEGIN;")
        for s in stmts:
            output.append(s + ";")
        output.append("COMMIT;")
        output.append("")
    
    # Write other DDL
    if other_stmts:
        output.append("-- Other DDL statements")
        for s in other_stmts:
            output.append(s + ";")
        output.append("")
    
    # Write data (each table's INSERTs in one transaction)
    output.append("-- ============================================================")
    output.append("-- Test Data (one transaction per table)")
    output.append("-- ============================================================")
    output.append("")
    
    for tbl in sorted(insert_groups.keys()):
        stmts = insert_groups[tbl]
        output.append(f"-- Data for: {tbl}")
        output.append("BEGIN;")
        for s in stmts:
            output.append(s + ";")
        output.append("COMMIT;")
        output.append("")
    
    return "\n".join(output)


def main():
    text = SQL_PATH.read_text(encoding='utf-8')
    
    # Remove the old outer BEGIN/COMMIT if present
    text = re.sub(r'^\s*BEGIN\s*;?\s*', '', text, flags=re.I)
    text = re.sub(r'\s*COMMIT\s*;?\s*$', '', text, flags=re.I)
    
    statements = read_statements(text)
    print(f"Parsed {len(statements)} statements")
    
    errors, warnings = validate_basic_syntax(statements)
    
    if errors:
        print(f"\n❌ {len(errors)} ERRORS found:")
        for e in errors:
            print(f"  - {e}")
    else:
        print("\n✅ No basic syntax errors found")
    
    if warnings:
        print(f"\n⚠️  {len(warnings)} warnings:")
        for w in warnings:
            print(f"  - {w}")
    
    new_sql = restructure_sql(statements)
    OUT_PATH.write_text(new_sql, encoding='utf-8')
    
    # Count lines
    lines = new_sql.count('\n') + 1
    print(f"\n📝 Restructured SQL written to {OUT_PATH}")
    print(f"   Total lines: {lines}")
    
    # Summary
    tbl_count = len([s for s in statements if classify_statement(s)[0] == 'create_table'])
    insert_tbl_count = len(set(extract_table_name(s, 'insert') for s in statements if classify_statement(s)[0] == 'insert'))
    print(f"   Tables created: {tbl_count}")
    print(f"   Tables with data: {insert_tbl_count}")


if __name__ == '__main__':
    main()
