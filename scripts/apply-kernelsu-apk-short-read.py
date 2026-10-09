#!/usr/bin/env python3
"""Apply short-read checks to the pinned legacy KernelSU-Next APK verifier."""
from pathlib import Path

path = Path("KernelSU-Next/kernel/manager/apk_sign.c")
s = path.read_text()
replacements = [
    ("\tksu_kernel_read_compat(fp, size4, 0x4, pos); // signer-sequence length",
     "\tif (ksu_kernel_read_compat(fp, size4, 0x4, pos) != 0x4) return false; // signer-sequence length"),
    ("\tksu_kernel_read_compat(fp, size4, 0x4, pos); // signer length",
     "\tif (ksu_kernel_read_compat(fp, size4, 0x4, pos) != 0x4) return false; // signer length"),
    ("\tksu_kernel_read_compat(fp, size4, 0x4, pos); // signed data length",
     "\tif (ksu_kernel_read_compat(fp, size4, 0x4, pos) != 0x4) return false; // signed data length"),
    ("\tksu_kernel_read_compat(fp, size4, 0x4, pos); // digests-sequence length",
     "\tif (ksu_kernel_read_compat(fp, size4, 0x4, pos) != 0x4) return false; // digests-sequence length"),
    ("\tksu_kernel_read_compat(fp, size4, 0x4, pos); // certificates length",
     "\tif (ksu_kernel_read_compat(fp, size4, 0x4, pos) != 0x4) return false; // certificates length"),
    ("\tksu_kernel_read_compat(fp, size4, 0x4, pos); // certificate length",
     "\tif (ksu_kernel_read_compat(fp, size4, 0x4, pos) != 0x4) return false; // certificate length"),
    ("\t\tksu_kernel_read_compat(fp, cert, *size4, pos);",
     "\t\tif (ksu_kernel_read_compat(fp, cert, *size4, pos) != *size4) {\n\t\t\tpr_info(\"read cert failed\\n\");\n\t\t\treturn false;\n\t\t}"),
    ("\tksu_kernel_read_compat(fp, eocd_buffer, search_size, &pos);",
     "\tif (ksu_kernel_read_compat(fp, eocd_buffer, search_size, &pos) != search_size) {\n\t\t\tkvfree(eocd_buffer);\n\t\t\tgoto clean;\n\t\t}"),
    ("\tksu_kernel_read_compat(fp, &size4, 0x4, &pos);",
     "\tif (ksu_kernel_read_compat(fp, &size4, 0x4, &pos) != 0x4) goto clean;"),
    ("\tksu_kernel_read_compat(fp, &size8, 0x8, &pos);\n\tksu_kernel_read_compat(fp, buffer, 0x10, &pos);",
     "\tif (ksu_kernel_read_compat(fp, &size8, 0x8, &pos) != 0x8) goto clean;\n\tif (ksu_kernel_read_compat(fp, buffer, 0x10, &pos) != 0x10) goto clean;"),
    ("\tksu_kernel_read_compat(fp, &size_of_block, 0x8, &pos);",
     "\tif (ksu_kernel_read_compat(fp, &size_of_block, 0x8, &pos) != 0x8) goto clean;"),
    ("\t\tksu_kernel_read_compat(fp, &size8, 0x8,\n\t\t\t\t\t&pos); // sequence length",
     "\t\tif (ksu_kernel_read_compat(fp, &size8, 0x8, &pos) != 0x8) { // sequence length\n\t\t\tv2_signing_valid = false;\n\t\t\tgoto clean;\n\t\t}"),
    ("\t\tksu_kernel_read_compat(fp, &id, 0x4, &pos); // id",
     "\t\tif (ksu_kernel_read_compat(fp, &id, 0x4, &pos) != 0x4) { // id\n\t\t\tv2_signing_valid = false;\n\t\t\tgoto clean;\n\t\t}"),
]
for old, new in replacements:
    if old not in s:
        raise SystemExit("Expected source pattern missing: " + repr(old))
    s = s.replace(old, new, 1)
path.write_text(s)
print("Applied %d APK short-read checks" % len(replacements))
