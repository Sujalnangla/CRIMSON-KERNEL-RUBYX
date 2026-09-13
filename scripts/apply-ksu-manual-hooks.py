#!/usr/bin/env python3
"""Apply the targeted KernelSU manual hooks used by the 4.19 Crimson tree.

SUSFS VFS/proc integration is applied separately by
apply-susfs-vfs-integration.py. This script handles only KernelSU manual hooks.
"""
from pathlib import Path


def replace_once(path, old, new, label):
    p = Path(path)
    s = p.read_text()
    count = s.count(old)
    if count == 0:
        if new in s:
            print(f"{label}: already present")
            return
        raise SystemExit(f"{label}: anchor not found")
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one anchor, found {count}")
    p.write_text(s.replace(old, new, 1))
    print(f"{label}: applied")


def ensure_hook(path, marker, old, new, label):
    s = Path(path).read_text()
    if marker in s:
        print(f"{label}: already present")
        return
    replace_once(path, old, new, label)


ensure_hook(
    "fs/open.c", "ksu_handle_faccessat",
    '#include <linux/compat.h>\n\n#include "internal.h"',
    '#include <linux/compat.h>\n\n#ifdef CONFIG_KSU\n__attribute__((hot))\nextern int ksu_handle_faccessat(int *dfd, const char __user **filename_user,\n\t\tint *mode, int *flags);\n#endif\n\n#include "internal.h"',
    "faccessat hook",
)

ensure_hook(
    "fs/stat.c", "ksu_handle_stat",
    '#include <linux/compat.h>\n',
    '#include <linux/compat.h>\n\n#ifdef CONFIG_KSU\n__attribute__((hot))\nextern int ksu_handle_stat(int *dfd, const char __user **filename_user,\n\t\tint *flags);\n#endif\n',
    "stat hook",
)

ensure_hook(
    "fs/read_write.c", "ksu_handle_sys_read",
    '#include <asm/unistd.h>\n',
    '#include <asm/unistd.h>\n\n#ifdef CONFIG_KSU\nextern bool ksu_vfs_read_hook __read_mostly;\nextern __attribute__((cold)) int ksu_handle_sys_read(unsigned int fd,\n\t\tchar __user **buf_ptr, size_t *count_ptr);\n#endif\n',
    "read hook",
)

ensure_hook(
    "drivers/input/input.c", "ksu_handle_input_handle_event",
    '#include "input-compat.h"\n',
    '#include "input-compat.h"\n\n#ifdef CONFIG_KSU\nextern bool ksu_input_hook __read_mostly;\nextern __attribute__((cold)) int ksu_handle_input_handle_event(\n\t\tunsigned int *type, unsigned int *code, int *value);\n#endif\n',
    "input declaration",
)

# The input anchor must be the input_event() signature, not the generic
# 'unsigned long flags' line (which also occurs in input_inject_event()).
ensure_hook(
    "drivers/input/input.c", "ksu_handle_input_handle_event(&type, &code, &value)",
    'void input_event(struct input_dev *dev,\n\t\t unsigned int type, unsigned int code, int value)\n{\n\tunsigned long flags;\n',
    'void input_event(struct input_dev *dev,\n\t\t unsigned int type, unsigned int code, int value)\n{\n\tunsigned long flags;\n#ifdef CONFIG_KSU\n\tif (unlikely(ksu_input_hook))\n\t\tksu_handle_input_handle_event(&type, &code, &value);\n#endif\n',
    "input hook",
)

print("KSU manual hooks are ready")
