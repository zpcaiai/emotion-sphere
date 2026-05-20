#!/usr/bin/env python3
"""Deep validation of seed_all.sql PostgreSQL syntax."""
import re
from pathlib import Path

SQL_PATH = Path('/Users/stephen/Documents/python/emotion-sphere/backend/seed_all.sql')

def tokenize(sql):
    """Tokenize SQL, respecting strings and dollar-quoted blocks."""
    tokens = []
    i = 0
    n = len(sql)
    while i < n:
        c = sql[i]
        if c == "'":
            # String literal
            j = i + 1
            while j < n:
                if sql[j] == "'" and j + 1 < n and sql[j+1] == "'":
                    j += 2
                elif sql[j] == "'":
                    j += 1
                    break
                else:
                    j += 1
            tokens.append(('STRING', sql[i:j]))
            i = j
        elif c == '"':
            j = i + 1
            while j < n and sql[j] != '"':
                j += 1
            j += 1
            tokens.append(('IDENT', sql[i:j]))
            i = j
        elif c == '$':
            m = re.match(r'\$([A-Za-z_][A-Za-z0-9_]*)?\$', sql[i:])
            if m:
                tag = m.group(1) or ''
                start = i + len(m.group(0))
                end_tag = '$' + tag + '$'
                j = sql.find(end_tag, start)
                if j == -1:
                    tokens.append(('ERROR', sql[i:i+20]))
                    i += 1
                else:
                    tokens.append(('DOLLAR', sql[i:j+len(end_tag)]))
                    i = j + len(end_tag)
            else:
                tokens.append(('SYM', c))
                i += 1
        elif c.isspace():
            j = i + 1
            while j < n and sql[j].isspace():
                j += 1
            tokens.append(('WS', sql[i:j]))
            i = j
        elif c.isalnum() or c == '_':
            j = i + 1
            while j < n and (sql[j].isalnum() or sql[j] == '_'):
                j += 1
            tokens.append(('WORD', sql[i:j]))
            i = j
        else:
            tokens.append(('SYM', c))
            i += 1
    return tokens


def split_statements(text):
    """Split SQL into statements by semicolons outside quotes/dollar blocks."""
    tokens = tokenize(text)
    statements = []
    current = []
    for t in tokens:
        if t[0] == 'SYM' and t[1] == ';':
            stmt = ''.join(tok[1] for tok in current).strip()
            if stmt:
                statements.append(stmt)
            current = []
        else:
            current.append(t)
    if current:
        stmt = ''.join(tok[1] for tok in current).strip()
        if stmt:
            statements.append(stmt)
    return statements


def validate_statement(stmt):
    """Validate a single SQL statement."""
    errors = []
    warnings = []
    
    tokens = tokenize(stmt)
    non_ws = [t for t in tokens if t[0] != 'WS']
    
    if not non_ws:
        return errors, warnings
    
    first_word = non_ws[0][1].upper()
    
    # Paren balance
    paren_depth = 0
    for t in tokens:
        if t[0] == 'SYM':
            for c in t[1]:
                if c == '(':
                    paren_depth += 1
                elif c == ')':
                    paren_depth -= 1
                    if paren_depth < 0:
                        errors.append("Unbalanced parentheses: extra closing ')'")
                        break
    if paren_depth > 0:
        errors.append(f"Unclosed parentheses: {paren_depth} open '('")
    if paren_depth < 0:
        errors.append("Unbalanced parentheses")
    
    # String balance check
    string_tokens = [t for t in tokens if t[0] == 'STRING']
    for st in string_tokens:
        s = st[1]
        # Check for unescaped single quotes inside string
        inner = s[1:-1]  # Remove outer quotes
        if "'" in inner:
            # Must be escaped as ''
            # Simple check: every single quote in inner must be followed by another single quote
            i = 0
            while i < len(inner):
                if inner[i] == "'":
                    if i + 1 >= len(inner) or inner[i+1] != "'":
                        errors.append(f"Unescaped single quote in string: {s[:60]}...")
                        break
                    i += 2
                else:
                    i += 1
    
    # CREATE TABLE checks
    if first_word == 'CREATE':
        if len(non_ws) > 2 and non_ws[2][1].upper() == 'TABLE':
            # Check trailing comma before )
            # Remove dollar blocks for simplicity
            clean = re.sub(r'\$[^$]*\$', '', stmt)
            if re.search(r',\s*\)', clean):
                warnings.append("Trailing comma before closing ')'")
    
    # INSERT checks
    if first_word == 'INSERT':
        # Check VALUES keyword exists
        has_values = any(t[1].upper() == 'VALUES' for t in non_ws)
        if not has_values:
            warnings.append("INSERT without VALUES keyword")
        
        # Check column count vs value count roughly
        cols_match = re.search(r'\(\s*([^)]+)\s*\)\s*VALUES', stmt, re.I)
        if cols_match:
            cols = cols_match.group(1)
            # Count non-empty comma-separated items
            col_count = len([c.strip() for c in cols.split(',') if c.strip()])
            # Find first VALUES list
            vals_match = re.search(r'VALUES\s*\(([^)]+)\)', stmt, re.I)
            if vals_match:
                vals = vals_match.group(1)
                val_count = len([v.strip() for v in vals.split(',') if v.strip()])
                if col_count != val_count:
                    errors.append(f"Column count ({col_count}) != Value count ({val_count})")
    
    return errors, warnings


def main():
    text = SQL_PATH.read_text(encoding='utf-8')
    statements = split_statements(text)
    
    print(f"Total statements: {len(statements)}")
    
    all_errors = []
    all_warnings = []
    
    for i, stmt in enumerate(statements):
        errs, warns = validate_statement(stmt)
        for e in errs:
            all_errors.append(f"Stmt {i+1}: {e}\n  >> {stmt[:120]}...")
        for w in warns:
            all_warnings.append(f"Stmt {i+1}: {w}\n  >> {stmt[:120]}...")
    
    if all_errors:
        print(f"\n❌ {len(all_errors)} ERRORS:")
        for e in all_errors:
            print(f"  {e}")
    else:
        print("\n✅ No syntax errors detected")
    
    if all_warnings:
        print(f"\n⚠️  {len(all_warnings)} WARNINGS:")
        for w in all_warnings:
            print(f"  {w}")
    else:
        print("\n✅ No warnings")

if __name__ == '__main__':
    main()
