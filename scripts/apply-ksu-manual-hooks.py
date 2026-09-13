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


replace_once(
    "fs/open.c",
    '#include <linux/compat.h>\n\n#include "internal.h"',
    '#include <linux/compat.h>\n\n#ifdef CONFIG_KSU\n__attribute__((hot))\nextern int ksu_handle_faccessat(int *dfd, const char __user **filename_user,\n\t\tint *mode, int *flags);\n#endif\n\n#include "internal.h"',
    "faccessat declaration",
)
replace_once(
    "fs/open.c",
    'SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)\n{\n\treturn do_faccessat(dfd, filename, mode);\n}',
    'SYSCALL_DEFINE3(faccessat, int, dfd, const char __user *, filename, int, mode)\n{\n#ifdef CONFIG_KSU\n\tksu_handle_faccessat(&dfd, &filename, &mode, NULL);\n#endif\n\treturn do_faccessat(dfd, filename, mode);\n}',
    "faccessat hook",
)

replace_once(
    "fs/stat.c",
    '#include <linux/compat.h>\n',
    '#include <linux/compat.h>\n\n#ifdef CONFIG_KSU\n__attribute__((hot))\nextern int ksu_handle_stat(int *dfd, const char __user **filename_user,\n\t\tint *flags);\n#endif\n',
    "stat declaration",
)
replace_once(
    "fs/stat.c",
    'SYSCALL_DEFINE4(newfstatat, int, dfd, const char __user *, filename,\n\t\tstruct stat __user *, statbuf, int, flag)\n{',
    'SYSCALL_DEFINE4(newfstatat, int, dfd, const char __user *, filename,\n\t\tstruct stat __user *, statbuf, int, flag)\n{\n#ifdef CONFIG_KSU\n\tksu_handle_stat(&dfd, &filename, &flag);\n#endif',
    "newfstatat hook",
)

replace_once(
    "fs/read_write.c",
    '#include <asm/unistd.h>\n',
    '#include <asm/unistd.h>\n\n#ifdef CONFIG_KSU\nextern bool ksu_vfs_read_hook __read_mostly;\nextern __attribute__((cold)) int ksu_handle_sys_read(unsigned int fd,\n\t\tchar __user **buf_ptr, size_t *count_ptr);\n#endif\n',
    "read declaration",
)
replace_once(
    "fs/read_write.c",
    'SYSCALL_DEFINE3(read, unsigned int, fd, char __user *, buf, size_t, count)\n{\n\treturn ksys_read(fd, buf, count);\n}',
    'SYSCALL_DEFINE3(read, unsigned int, fd, char __user *, buf, size_t, count)\n{\n#ifdef CONFIG_KSU\n\tif (unlikely(ksu_vfs_read_hook))\n\t\tksu_handle_sys_read(fd, &buf, &count);\n#endif\n\treturn ksys_read(fd, buf, count);\n}',
    "read hook",
)

replace_once(
    "drivers/input/input.c",
    '#include "input-compat.h"\n',
    '#include "input-compat.h"\n\n#ifdef CONFIG_KSU\nextern bool ksu_input_hook __read_mostly;\nextern __attribute__((cold)) int ksu_handle_input_handle_event(\n\t\tunsigned int *type, unsigned int *code, int *value);\n#endif\n',
    "input declaration",
)
replace_once(
    "drivers/input/input.c",
    'void input_event(struct input_dev *dev,\n\t\t unsigned int type, unsigned int code, int value)\n{\n\tunsigned long flags;\n',
    '#ifdef CONFIG_KSU\nextern bool ksu_input_hook __read_mostly;\nextern __attribute__((cold)) int ksu_handle_input_handle_event(\n unsigned int *type, unsigned int *code, int *value);\n#endif\nvoid input_event(struct input_dev *dev,\n\t\t unsigned int type, unsigned int code, int value)\n{\n\tunsigned long flags;\n#ifdef CONFIG_KSU\n\tif (unlikely(ksu_input_hook))\n\t\tksu_handle_input_handle_event(&type, &code, &value);\n#endif\n',
    "input hook",
)

print("KSU manual hooks are ready")
