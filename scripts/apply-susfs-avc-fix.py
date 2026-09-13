#!/usr/bin/env python3
"""Apply only the SUSFS AVC log-spoofing hook used by the Ruby kernel source."""
from pathlib import Path

path = Path("security/selinux/avc.c")
s = path.read_text()

# The Crimson source already contains the SUSFS driver. This script adds only
# the small AVC integration from the authoritative Ruby SUSFS commit.
if "bool susfs_is_avc_log_spoofing_enabled = false;" not in s:
    anchor = "#endif\n\nstruct avc_entry {"
    defs = "#endif\n\n#ifdef CONFIG_KSU_SUSFS\nextern u32 susfs_ksu_sid;\nextern u32 susfs_priv_app_sid;\nbool susfs_is_avc_log_spoofing_enabled = false;\n#endif\n\nstruct avc_entry {"
    if anchor not in s:
        raise SystemExit("SUSFS AVC definition anchor not found")
    s = s.replace(anchor, defs, 1)

marker = "\trc = security_sid_to_context(state, tsid, &scontext, &scontext_len);\n"
if "susfs_is_avc_log_spoofing_enabled))" not in s:
    if s.count(marker) != 1:
        raise SystemExit("SUSFS AVC query anchor is missing or ambiguous")
    hook = marker + "#ifdef CONFIG_KSU_SUSFS\n\tif (unlikely(tsid == susfs_ksu_sid && susfs_is_avc_log_spoofing_enabled)) {\n\t\tif (rc)\n\t\t\taudit_log_format(ab, \" tsid=%d\", susfs_priv_app_sid);\n\t\telse\n\t\t\taudit_log_format(ab, \" tcontext=%s\", \"u:r:priv_app:s0:c512,c768\");\n\t\tgoto bypass_orig_flow;\n\t}\n#endif\n"
    s = s.replace(marker, hook, 1)

# Place the bypass label immediately before the original target-SID audit flow.
label_anchor = "\tBUG_ON(!tclass || tclass >= ARRAY_SIZE(secclass_map));\n"
if "bypass_orig_flow:" not in s:
    if s.count(label_anchor) != 1:
        raise SystemExit("SUSFS AVC bypass label anchor is missing or ambiguous")
    s = s.replace(label_anchor, "#ifdef CONFIG_KSU_SUSFS\nbypass_orig_flow:\n#endif\n\n" + label_anchor, 1)

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
