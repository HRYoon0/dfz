"""Dump .NET metadata (types, fields, methods) and user strings from assemblies.
Usage: python -I dump_meta.py <out_dir> <dll> [<dll> ...]"""
import sys, os, dnfile

out_dir = sys.argv[1]
os.makedirs(out_dir, exist_ok=True)

for path in sys.argv[2:]:
    name = os.path.basename(path)
    pe = dnfile.dnPE(path)
    md = pe.net.mdtables
    lines = []
    typedefs = md.TypeDef.rows if md.TypeDef else []
    for td in typedefs:
        ns = str(td.TypeNamespace or "")
        tn = str(td.TypeName or "")
        ext = ""
        try:
            if td.Extends and td.Extends.row:
                r = td.Extends.row
                ext = " : " + str(getattr(r, "TypeNamespace", "") or "") + "." + str(getattr(r, "TypeName", "") or "")
        except Exception:
            pass
        lines.append(f"type {ns}.{tn}{ext}")
        for f in (td.FieldList or []):
            try:
                lines.append(f"    field {f.row.Name}")
            except Exception:
                pass
        for m in (td.MethodList or []):
            try:
                lines.append(f"    method {m.row.Name}")
            except Exception:
                pass
    with open(os.path.join(out_dir, name + ".types.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))

    us = []
    if pe.net.user_strings:
        data = pe.net.user_strings.__data__
        i = 1
        while i < len(data):
            n = data[i]
            hdr = 1
            if n & 0x80 == 0:
                ln = n
            elif n & 0xC0 == 0x80:
                ln = ((n & 0x3F) << 8) | data[i + 1]; hdr = 2
            else:
                ln = ((n & 0x1F) << 24) | (data[i + 1] << 16) | (data[i + 2] << 8) | data[i + 3]; hdr = 4
            raw = data[i + hdr:i + hdr + ln]
            if ln > 1:
                try:
                    us.append(raw[:-1].decode("utf-16-le"))
                except Exception:
                    pass
            i += hdr + ln
    with open(os.path.join(out_dir, name + ".strings.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(s.replace("\n", "\\n") for s in us))
    print(name, len(lines), "meta lines,", len(us), "strings")
