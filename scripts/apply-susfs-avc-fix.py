#!/usr/bin/env python3
"""Apply the SUSFS AVC log-spoofing integration to the 4.19 SELinux AVC."""
from pathlib import Path
import re

path = Path("security/selinux/avc.c")
s = path.read_text()

# This is the exact small integration used by the authoritative Ruby kernel
# source. Keep the transformation structural and fail closed if the source
# shape changes, rather than silently applying a partial patch.
defs = """#ifdef CONFIG_KSU_SUSFS
extern u32 susfs_ksu_sid;
extern u32 susfs_priv_app_sid;
bool susfs_is_avc_log_spoofing_enabled = false;
#endif
"""

if "bool susfs_is_avc_log_spoofing_enabled = false;" not in s:
    pattern = r"(#ifdef CONFIG_SECURITY_SELINUX_AVC_STATS\nDEFINE_PER_CPU\(struct avc_cache_stats, avc_cache_stats\) = \{ 0 \};\n#endif\n)"
    s, n = re.subn(pattern, r"\1\n" + defs, s, count=1)
    if n != 1:
        raise SystemExit("SUSFS AVC definition anchor not found")

query_pattern = re.compile(
    r"(\trc = security_sid_to_context\(state, tsid, &scontext, &scontext_len\);\n)"
    r"(\tif \(rc\)\n\t\taudit_log_format\(ab, \" tsid=%d\", tsid\);\n"
    r"\telse \{\n\t\taudit_log_format\(ab, \" tcontext=%s\", scontext\);\n"
    r"\t\tkfree\(scontext\);\n\t\}\n)"
)

if "if (unlikely(tsid == susfs_ksu_sid && susfs_is_avc_log_spoofing_enabled))" not in s:
    replacement = r'''\1#ifdef CONFIG_KSU_SUSFS
\tif (unlikely(tsid == susfs_ksu_sid && susfs_is_avc_log_spoofing_enabled)) {
\t\tif (rc)
\t\t\taudit_log_format(ab, " tsid=%d", susfs_priv_app_sid);
\t\telse
\t\t\taudit_log_format(ab, " tcontext=%s", "u:r:priv_app:s0:c512,c768");
\t\tgoto bypass_orig_flow;
\t}
#endif

\2
#ifdef CONFIG_KSU_SUSFS
bypass_orig_flow:
#endif
'''
    s, n = query_pattern.subn(replacement, s, count=1)
    if n != 1:
        raise SystemExit("SUSFS AVC query anchor not found")

required = [
    "extern u32 susfs_ksu_sid;",
    "extern u32 susfs_priv_app_sid;",
    "bool susfs_is_avc_log_spoofing_enabled = false;",
    "if (unlikely(tsid == susfs_ksu_sid && susfs_is_avc_log_spoofing_enabled))",
    'audit_log_format(ab, " tsid=%d", susfs_priv_app_sid);',
    '"u:r:priv_app:s0:c512,c768"',
    "bypass_orig_flow:",
]
for item in required:
    if item not in s:
        raise SystemExit(f"SUSFS AVC integration incomplete: {item}")

path.write_text(s)
print("Applied SUSFS AVC log-spoofing integration")
