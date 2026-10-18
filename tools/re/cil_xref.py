"""Minimal CIL cross-reference: for each method, list called members and ldstr strings.
Usage: python -I cil_xref.py <dll> <out_txt>"""
import sys, struct, dnfile

path, out = sys.argv[1], sys.argv[2]
pe = dnfile.dnPE(path)
md = pe.net.mdtables
us_heap = pe.net.user_strings

# opcode operand sizes (single-byte opcodes)
SZ = {}
for op in range(0x100):
    SZ[op] = 0
for op in (0x0E, 0x0F, 0x10, 0x11, 0x12, 0x13, 0x1F, 0x2B, 0x2C, 0x2D, 0x2E, 0x2F, 0x30, 0x31, 0x32,
           0x33, 0x34, 0x35, 0x36, 0x37, 0xDE):
    SZ[op] = 1
for op in (0x20, 0x22, 0x28, 0x29, 0x27, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40, 0x41,
           0x42, 0x43, 0x44, 0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x79, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F,
           0x80, 0x81, 0x8C, 0x8D, 0x8F, 0xA3, 0xA4, 0xA5, 0xC2, 0xC6, 0xD0, 0xDD):
    SZ[op] = 4
SZ[0x21] = 8; SZ[0x23] = 8
SZ2 = {0x06: 4, 0x07: 4, 0x09: 2, 0x0A: 2, 0x0B: 2, 0x0C: 2, 0x0D: 2, 0x0E: 2, 0x12: 1, 0x15: 4,
       0x16: 4, 0x19: 1, 0x1C: 4, 0x1D: 0}

def owner_name(tbl_row):
    try:
        return f"{tbl_row.TypeNamespace}.{tbl_row.TypeName}"
    except Exception:
        return "?"

# map method rid -> type name
mrid_type = {}
for td in (md.TypeDef.rows if md.TypeDef else []):
    for m in (td.MethodList or []):
        mrid_type[m.row_index] = f"{td.TypeNamespace}.{td.TypeName}"

def resolve(tok):
    tbl, rid = tok >> 24, tok & 0xFFFFFF
    try:
        if tbl == 0x06:
            r = md.MethodDef.rows[rid - 1]
            return f"{mrid_type.get(rid,'?')}::{r.Name}"
        if tbl == 0x0A:
            r = md.MemberRef.rows[rid - 1]
            cls = r.Class.row
            return f"{owner_name(cls)}::{r.Name}"
        if tbl == 0x2B:
            r = md.MethodSpec.rows[rid - 1]
            return "spec:" + resolve(r.Method.table.number << 24 | r.Method.row_index) if hasattr(r.Method, 'table') else "spec"
        if tbl == 0x04:
            r = md.Field.rows[rid - 1]
            return f"field:{r.Name}"
    except Exception as e:
        return f"tok{tok:08x}"
    return f"tok{tok:08x}"

def us(tok):
    try:
        return us_heap.get(tok & 0xFFFFFF).value
    except Exception:
        return f"us{tok:08x}"

lines = []
for i, m in enumerate(md.MethodDef.rows if md.MethodDef else []):
    rid = i + 1
    if not m.Rva:
        continue
    off = pe.get_offset_from_rva(m.Rva)
    data = pe.__data__
    h = data[off]
    if h & 3 == 2:
        code_off, size = off + 1, h >> 2
    else:
        size = struct.unpack_from("<I", data, off + 4)[0]
        code_off = off + (struct.unpack_from("<H", data, off)[0] >> 12) * 4
    code = data[code_off:code_off + size]
    lines.append(f"## {mrid_type.get(rid,'?')}::{m.Name}")
    p = 0
    while p < len(code):
        op = code[p]; p += 1
        if op == 0xFE:
            op2 = code[p]; p += 1
            p += SZ2.get(op2, 0)
            continue
        if op == 0x45:
            n = struct.unpack_from("<I", code, p)[0]; p += 4 + 4 * n
            continue
        n = SZ.get(op, 0)
        if n == 4 and op in (0x28, 0x6F, 0x73):
            tok = struct.unpack_from("<I", code, p)[0]
            lines.append(f"    call {resolve(tok)}")
        elif op == 0x72:
            tok = struct.unpack_from("<I", code, p)[0]
            s = us(tok)
            lines.append(f"    str  {str(s)[:120]!r}")
        elif op in (0x7B, 0x7D, 0x7E, 0x80):
            tok = struct.unpack_from("<I", code, p)[0]
            lines.append(f"    fld  {resolve(tok)}")
        p += n
open(out, "w", encoding="utf-8").write("\n".join(lines))
print("methods:", sum(1 for l in lines if l.startswith("##")))
