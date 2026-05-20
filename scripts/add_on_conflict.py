#!/usr/bin/env python3
"""Add ON CONFLICT DO NOTHING to all INSERT statements in seed_all.sql."""

path = '/Users/stephen/Documents/python/emotion-sphere/backend/seed_all.sql'
with open(path) as f:
    lines = f.readlines()

out = []
changed = 0
i = 0
while i < len(lines):
    line = lines[i]
    stripped = line.strip()

    if stripped.startswith('INSERT INTO'):
        # Collect full statement
        stmt_lines = [line]
        if not stripped.endswith(';') and not stripped.endswith(';\n'):
            i += 1
            while i < len(lines):
                stmt_lines.append(lines[i])
                if lines[i].strip().endswith(';'):
                    break
                i += 1

        full = ''.join(stmt_lines)
        if 'ON CONFLICT' not in full:
            # Replace trailing ;\n with \nON CONFLICT DO NOTHING;\n
            last = stmt_lines[-1]
            last = last.rstrip('\n')
            if last.rstrip().endswith(';'):
                stmt_lines[-1] = last.rstrip()[:-1] + '\nON CONFLICT DO NOTHING;\n'
                changed += 1

        out.extend(stmt_lines)
    else:
        out.append(line)
    i += 1

with open(path, 'w') as f:
    f.writelines(out)

total = sum(1 for l in out if 'ON CONFLICT' in l)
print(f'Added ON CONFLICT DO NOTHING to {changed} INSERT statements')
print(f'Total ON CONFLICT clauses now: {total}')
