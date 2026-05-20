#!/usr/bin/env python3
"""Comprehensive check of seed_all.sql for PostgreSQL execution readiness."""
import re

SQL_PATH = '/Users/stephen/Documents/python/emotion-sphere/backend/seed_all.sql'

with open(SQL_PATH) as f:
    text = f.read()
    lines = text.split('\n')

issues = []

# 1. CREATE TABLE must have IF NOT EXISTS
for i, line in enumerate(lines, 1):
    s = line.strip()
    if s.startswith('--'):
        continue
    if 'CREATE TABLE ' in line and 'IF NOT EXISTS' not in line:
        issues.append(f'Line {i}: CREATE TABLE without IF NOT EXISTS')

# 2. CREATE INDEX must have IF NOT EXISTS
for i, line in enumerate(lines, 1):
    s = line.strip()
    if s.startswith('--'):
        continue
    if re.search(r'CREATE (UNIQUE )?INDEX ', line) and 'IF NOT EXISTS' not in line:
        issues.append(f'Line {i}: CREATE INDEX without IF NOT EXISTS: {s[:60]}')

# 3. CREATE TRIGGER must have DROP TRIGGER IF EXISTS before it
for i, line in enumerate(lines, 1):
    if 'CREATE TRIGGER ' in line:
        parts = line.strip().split('CREATE TRIGGER ')
        trigger_name = parts[-1].split()[0]
        found_drop = False
        if 'DROP TRIGGER IF EXISTS ' + trigger_name in line:
            found_drop = True
        for j in range(max(0, i - 4), i - 1):
            if 'DROP TRIGGER IF EXISTS ' + trigger_name in lines[j]:
                found_drop = True
        if not found_drop:
            issues.append(f'Line {i}: CREATE TRIGGER {trigger_name} without DROP IF EXISTS')

# 4. BEGIN/COMMIT balance
begins = sum(1 for l in lines if l.strip() == 'BEGIN;')
commits = sum(1 for l in lines if l.strip() == 'COMMIT;')
if begins != commits:
    issues.append(f'BEGIN/COMMIT mismatch: {begins} vs {commits}')

# 5. No nested BEGIN
depth = 0
for i, line in enumerate(lines, 1):
    s = line.strip()
    if s == 'BEGIN;':
        depth += 1
        if depth > 1:
            issues.append(f'Line {i}: Nested BEGIN (depth {depth})')
    elif s == 'COMMIT;':
        depth -= 1
        if depth < 0:
            issues.append(f'Line {i}: COMMIT without BEGIN')

# 6. Double semicolons
for i, line in enumerate(lines, 1):
    if ';;' in line:
        issues.append(f'Line {i}: Double semicolons')

# 7. Unescaped quotes (odd count of single quotes in INSERT/value lines)
in_insert = False
for i, line in enumerate(lines, 1):
    s = line.strip()
    if s.startswith('INSERT INTO'):
        in_insert = True
    if in_insert:
        count = 0
        j = 0
        while j < len(line):
            if line[j] == "'":
                if j + 1 < len(line) and line[j + 1] == "'":
                    j += 2  # escaped quote
                else:
                    count += 1
                    j += 1
            else:
                j += 1
        if count % 2 != 0:
            issues.append(f'Line {i}: Odd quotes ({count}) - possible unescaped quote')
        if s.endswith(';'):
            in_insert = False

# 8. FK dependency: REFERENCES to table not yet created
created = []
for i, line in enumerate(lines, 1):
    m = re.search(r'CREATE TABLE IF NOT EXISTS (\w+)', line)
    if m:
        tbl = m.group(1)
        refs = re.findall(r'REFERENCES (\w+)\(', line)
        for ref in refs:
            if ref not in created and ref != tbl:
                issues.append(f'Line {i}: {tbl} REFERENCES {ref} (not yet created)')
        created.append(tbl)

# 9. INSERT targets must have corresponding CREATE TABLE
schema_tables = set(re.findall(r'CREATE TABLE IF NOT EXISTS (\w+)', text))
insert_tables = set(re.findall(r'INSERT INTO (\w+)', text))
missing = insert_tables - schema_tables
if missing:
    issues.append(f'INSERT into non-existent tables: {missing}')

# 10. JSONB[] columns should use ARRAY[...]::JSONB[], not string literal
for i, line in enumerate(lines, 1):
    if 'INSERT INTO system_state_definitions' in line:
        continue  # header line
    # Check for JSONB array passed as string: pattern '[{"
    if 'system_state_definitions' in text[text.find('-- Data for: system_state_definitions'):]:
        pass  # handled below

# Check system_state_definitions data specifically
in_ssd = False
for i, line in enumerate(lines, 1):
    if '-- Data for: system_state_definitions' in line:
        in_ssd = True
    elif line.strip().startswith('-- Data for:') and in_ssd:
        in_ssd = False
    if in_ssd and "STATE_" in line:
        # trigger_conditions should be ARRAY[...]::JSONB[]
        if "'[{" in line:
            issues.append(f"Line {i}: JSONB[] as string literal (should use ARRAY[...]::JSONB[])")

# 11. Check CONSTRAINT names - ON CONFLICT may fail if constraint doesn't exist
# (informational only)

# Report
if issues:
    print(f'Found {len(issues)} issue(s):\n')
    for iss in issues:
        print(f'  \u274c {iss}')
else:
    print('\u2705 All checks passed! seed_all.sql should execute cleanly.\n')

print(f'\nSummary:')
print(f'  Tables defined: {len(schema_tables)}')
print(f'  Tables with data: {len(insert_tables)}')
print(f'  Transactions: {begins} BEGIN / {commits} COMMIT')
print(f'  Total lines: {len(lines)}')
