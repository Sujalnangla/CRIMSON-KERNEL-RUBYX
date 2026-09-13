#!/usr/bin/env python3
"""Apply the missing SUSFS v2.2.0 VFS/proc integration used by Crimson CI.

The Crimson tree already contains the SUSFS core (fs/susfs.c + headers). This
script ports only the missing integration hunks from the pinned Rajdeep
KernelSU/SUSFS integration commit; it deliberately does not replace SUSFS
core files or device-specific files wholesale.

Crimson has diverged from Rajdeep in several older 4.19 VFS files. The
normal Git patch therefore cannot always match its surrounding context. We
first try the normal patch and, for those already-diverged files, retry with
zero-context hunks. Zero-context mode is still exact about the lines being
added/removed; it only removes unrelated surrounding context from the match.
"""
from pathlib import Path
import subprocess
import tempfile

RAJDEEP_REPO = "https://github.com/rajdeep-3305/kernel_xiaomi_mt6877.git"
RAJDEEP_COMMIT = "d07fe787f959464a653596f3a23b5e88c4510644"
RAJDEEP_PARENT = "bff45a69404e25fd5a1904ffe11ab8c1e6ce1604"

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


def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True)


def check_patch(patch_path, cwd, *extra):
    return subprocess.run(
        ["git", "apply", "--check", "--whitespace=nowarn", *extra, str(patch_path)],
        cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )


def main():
    defconfig = Path("arch/arm64/configs/ruby_defconfig")
    if not defconfig.exists():
        raise SystemExit("ruby_defconfig not found")

    # Rajdeep follow-up hardening: KPROBES off for manual hooks + ThinLTO/SCS.
    cfg = defconfig.read_text()
    if "CONFIG_KPROBES=y" in cfg:
        defconfig.write_text(cfg.replace("CONFIG_KPROBES=y", "# CONFIG_KPROBES is not set", 1))
        print("defconfig: CONFIG_KPROBES disabled")
    elif "# CONFIG_KPROBES is not set" in cfg:
        print("defconfig: CONFIG_KPROBES already disabled")
    else:
        raise SystemExit("defconfig: KPROBES setting not found")

    with tempfile.TemporaryDirectory(prefix="crimson-susfs-") as td:
        repo = Path(td) / "rajdeep"
        run("git", "init", "-q", str(repo))
        run("git", "remote", "add", "origin", RAJDEEP_REPO, cwd=repo)
        run("git", "fetch", "--no-tags", "--depth=1", "origin", RAJDEEP_COMMIT, RAJDEEP_PARENT, cwd=repo)

        patch = subprocess.run(
            ["git", "diff", RAJDEEP_PARENT, RAJDEEP_COMMIT, "--", *FILES],
            cwd=repo, check=True, text=True, stdout=subprocess.PIPE,
        ).stdout
        if not patch.strip():
            raise SystemExit("SUSFS integration: selected Rajdeep diff is empty")

        patch_path = repo / "susfs-integration.patch"
        patch_path.write_text(patch)

        # First use the normal patch, preserving as much context checking as
        # possible. Crimson's namei/open/proc-base files are known to have
        # diverged from Rajdeep's parent, so a zero-context retry is provided
        # for those exact additions/removals.
        check = check_patch(patch_path, repo)
        if check.returncode == 0:
            run("git", "apply", "--whitespace=nowarn", str(patch_path))
            print("SUSFS integration: normal patch applied")
        else:
            print(check.stdout, end="")
            zero_patch = repo / "susfs-integration-zero-context.patch"
            zero = subprocess.run(
                ["git", "diff", "-U0", RAJDEEP_PARENT, RAJDEEP_COMMIT, "--", *FILES],
                cwd=repo, check=True, text=True, stdout=subprocess.PIPE,
            ).stdout
            zero_patch.write_text(zero)
            zero_check = check_patch(zero_patch, repo, "--unidiff-zero")
            if zero_check.returncode != 0:
                print(zero_check.stdout, end="")
                raise SystemExit(
                    "SUSFS integration: normal and zero-context patches both fail; "
                    "manual integration is required for a remaining Crimson divergence"
                )
            run("git", "apply", "--unidiff-zero", "--whitespace=nowarn", str(zero_patch))
            print("SUSFS integration: zero-context patch applied for Crimson-diverged VFS files")

    print("SUSFS v2.2.0 VFS/proc integration applied")


if __name__ == "__main__":
    main()
