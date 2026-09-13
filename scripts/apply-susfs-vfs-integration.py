#!/usr/bin/env python3
"""Apply the missing SUSFS v2.2.0 VFS/proc integration used by Crimson CI.

The Crimson tree already contains the SUSFS core (fs/susfs.c + headers). This
script ports only the missing integration hunks from the pinned Rajdeep
KernelSU/SUSFS integration commit; it deliberately does not replace SUSFS
core files or device-specific files wholesale.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

RAJDEEP_REPO = "https://github.com/rajdeep-3305/kernel_xiaomi_mt6877.git"
RAJDEEP_COMMIT = "d07fe787f959464a653596f3a23b5e88c4510644"
RAJDEEP_PARENT = "bff45a69404e25fd5a1904ffe11ab8c1e6ce1604"

# SUSFS integration files only. KSU manual hooks are handled separately.
FILES = [
    "fs/namei.c",
    "fs/readdir.c",
    "fs/stat.c",
    "fs/open.c",
    "fs/statfs.c",
    "fs/proc/base.c",
    "fs/proc/cmdline.c",
    "fs/proc/fd.c",
    "fs/proc/task_mmu.c",
    "fs/proc_namespace.c",
    "fs/notify/fdinfo.c",
    "kernel/sys.c",
    "kernel/kallsyms.c",
]


def run(*args, cwd=None, capture=False):
    return subprocess.run(
        args,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
    )


def main():
    defconfig = Path("arch/arm64/configs/ruby_defconfig")
    if not defconfig.exists():
        raise SystemExit("ruby_defconfig not found")

    # Rajdeep's follow-up hardening explicitly disables KPROBES for the
    # manual-hook + ThinLTO/SCS configuration. Keep this build deterministic.
    cfg = defconfig.read_text()
    if "CONFIG_KPROBES=y" in cfg:
        cfg = cfg.replace("CONFIG_KPROBES=y", "# CONFIG_KPROBES is not set", 1)
        defconfig.write_text(cfg)
        print("defconfig: CONFIG_KPROBES disabled")
    elif "# CONFIG_KPROBES is not set" in cfg:
        print("defconfig: CONFIG_KPROBES already disabled")
    else:
        raise SystemExit("defconfig: CONFIG_KPROBES setting not found")

    with tempfile.TemporaryDirectory(prefix="crimson-susfs-") as td:
        repo = Path(td) / "rajdeep"
        run("git", "init", "-q", str(repo))
        run("git", "remote", "add", "origin", RAJDEEP_REPO, cwd=repo)
        run("git", "fetch", "--no-tags", "--depth=1", "origin", RAJDEEP_COMMIT, RAJDEEP_PARENT, cwd=repo)

        patch = subprocess.run(
            ["git", "diff", RAJDEEP_PARENT, RAJDEEP_COMMIT, "--", *FILES],
            cwd=repo,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
        ).stdout

        if not patch.strip():
            raise SystemExit("SUSFS integration: selected Rajdeep diff is empty")

        patch_path = repo / "susfs-integration.patch"
        patch_path.write_text(patch)

        # Check first so a context mismatch cannot leave a partially modified
        # kernel tree. --3way is useful where Crimson has harmless local drift.
        check = subprocess.run(
            ["git", "apply", "--check", "--3way", "--whitespace=nowarn", str(patch_path)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if check.returncode != 0:
            print(check.stdout, end="")
            raise SystemExit("SUSFS integration: Rajdeep VFS/proc patch does not apply cleanly")

        run("git", "apply", "--3way", "--whitespace=nowarn", str(patch_path))

    print("SUSFS v2.2.0 VFS/proc integration applied")


if __name__ == "__main__":
    main()
