#!/usr/bin/env python3
"""Apply the missing SUSFS v2.2.0 VFS/proc integration used by Crimson CI.

The Crimson tree already contains the SUSFS core. The pinned Rajdeep commit
contains the reference VFS/proc integration, but several Crimson files have
diverged enough that a normal textual patch does not apply. Prefer Git's
three-way merge machinery so only the actual SUSFS changes are merged while
retaining Crimson's surrounding code.
"""
from pathlib import Path
import subprocess
import tempfile

RAJDEEP_REPO = "https://github.com/rajdeep-3305/kernel_xiaomi_mt6877.git"
RAJDEEP_COMMIT = "d07fe787f959464a653596f3a23b5e88c4510644"
RAJDEEP_PARENT = "bff45a69404e25fd5a1904ffe11ab8c1e6ce1604"

FILES = [
    "fs/namei.c", "fs/readdir.c", "fs/stat.c", "fs/open.c", "fs/statfs.c",
    "fs/proc/base.c", "fs/proc/cmdline.c", "fs/proc/fd.c",
    "fs/proc/task_mmu.c", "fs/proc_namespace.c", "fs/notify/fdinfo.c",
    "kernel/sys.c", "kernel/kallsyms.c",
]


def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True)


def check_patch(patch_path, target, *extra):
    return subprocess.run(
        ["git", "apply", "--check", "--whitespace=nowarn", *extra, str(patch_path)],
        cwd=target, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )


def main():
    target = Path.cwd()
    defconfig = target / "arch/arm64/configs/ruby_defconfig"
    if not defconfig.exists():
        raise SystemExit("ruby_defconfig not found")

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
            ["git", "diff", "--full-index", RAJDEEP_PARENT, RAJDEEP_COMMIT, "--", *FILES],
            cwd=repo, check=True, text=True, stdout=subprocess.PIPE,
        ).stdout
        if not patch.strip():
            raise SystemExit("SUSFS integration: selected Rajdeep diff is empty")

        patch_path = Path(td) / "susfs-integration.patch"
        patch_path.write_text(patch)

        # First try the ordinary patch path for files that still match Crimson.
        check = check_patch(patch_path, target)
        if check.returncode == 0:
            run("git", "apply", "--whitespace=nowarn", str(patch_path), cwd=target)
            print("SUSFS integration: normal patch applied")
            print("SUSFS v2.2.0 VFS/proc integration applied")
            return

        print("SUSFS integration: normal patch does not apply; trying three-way merge")
        print(check.stdout, end="")

        # Git three-way application is appropriate here: the patch records the
        # exact Rajdeep parent blob, allowing Git to merge the SUSFS additions
        # into a locally diverged Crimson file instead of replacing the file.
        threeway = subprocess.run(
            ["git", "apply", "--3way", "--whitespace=nowarn", str(patch_path)],
            cwd=target, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        if threeway.returncode == 0:
            print(threeway.stdout, end="")
            print("SUSFS integration: three-way merge applied")
            print("SUSFS v2.2.0 VFS/proc integration applied")
            return

        print(threeway.stdout, end="")
        raise SystemExit(
            "SUSFS integration: normal patch and three-way merge both failed; "
            "the remaining files require targeted source integration"
        )


if __name__ == "__main__":
    main()
