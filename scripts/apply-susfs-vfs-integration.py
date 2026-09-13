#!/usr/bin/env python3
"""Apply SUSFS v2.2.0 VFS/proc integration without replacing diverged Crimson files."""
from pathlib import Path
import subprocess
import tempfile

RAJDEEP_REPO = "https://github.com/rajdeep-3305/kernel_xiaomi_mt6877.git"
RAJDEEP_COMMIT = "d07fe787f959464a653596f3a23b5e88c4510644"
RAJDEEP_PARENT = "bff45a69404e25fd5a1904ffe11ab8c1e6ce1604"

# These files are close enough to the Rajdeep base for a per-file patch.
CLEAN_FILES = [
    "fs/readdir.c", "fs/stat.c", "fs/statfs.c",
    "fs/proc/cmdline.c", "fs/proc/fd.c", "fs/proc/task_mmu.c",
    "fs/proc_namespace.c", "fs/notify/fdinfo.c",
    "kernel/sys.c", "kernel/kallsyms.c",
]


def run(*args, cwd=None):
    return subprocess.run(args, cwd=cwd, check=True)


def apply_file_patch(repo, target, path, td):
    patch = subprocess.run(
        ["git", "diff", "--full-index", RAJDEEP_PARENT, RAJDEEP_COMMIT, "--", path],
        cwd=repo, check=True, text=True, stdout=subprocess.PIPE,
    ).stdout
    if not patch.strip():
        raise SystemExit(f"SUSFS integration: empty patch for {path}")
    patch_path = Path(td) / (path.replace("/", "_") + ".patch")
    patch_path.write_text(patch)
    check = subprocess.run(
        ["git", "apply", "--check", "--whitespace=nowarn", str(patch_path)],
        cwd=target, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    if check.returncode != 0:
        raise SystemExit(f"SUSFS integration: clean patch failed for {path}\n{check.stdout}")
    run("git", "apply", "--whitespace=nowarn", str(patch_path), cwd=target)
    print(f"SUSFS integration: {path} applied")


def insert_once(text, anchor, addition, label):
    if addition.strip() in text:
        return text
    count = text.count(anchor)
    if count != 1:
        raise SystemExit(f"SUSFS integration: {label}: expected one anchor, found {count}")
    return text.replace(anchor, addition + anchor, 1)


def patch_namei(target):
    path = target / "fs/namei.c"
    text = path.read_text()
    text = insert_once(
        text,
        "#include <linux/build_bug.h>\n",
        "#if defined(CONFIG_KSU_SUSFS_SUS_PATH)\n#include <linux/susfs_def.h>\n#endif\n",
        "namei include",
    )
    text = insert_once(
        text,
        "#include <trace/events/namei.h>\n",
        "#ifdef CONFIG_KSU_SUSFS_SUS_PATH\nextern bool susfs_is_inode_sus_path(struct inode *inode);\n#endif\n\n",
        "namei extern",
    )
    start = text.find("static struct dentry *lookup_dcache(")
    if start < 0:
        raise SystemExit("SUSFS integration: lookup_dcache not found")
    end = text.find("\n}\n", start)
    if end < 0:
        raise SystemExit("SUSFS integration: lookup_dcache end not found")
    body = text[start:end]
    marker = "\tif (unlikely(!dentry))\n"
    hook = (
        "#ifdef CONFIG_KSU_SUSFS_SUS_PATH\n"
        "\tif (dentry && !IS_ERR(dentry) && dentry->d_inode &&\n"
        "\t\tsusfs_is_inode_sus_path(dentry->d_inode)) {\n"
        "\t\tif (d_in_lookup(dentry))\n"
        "\t\t\td_lookup_done(dentry);\n"
        "\t\tdput(dentry);\n"
        "\t\treturn NULL;\n"
        "\t}\n"
        "#endif\n"
    )
    if "susfs_is_inode_sus_path(dentry->d_inode)" not in body:
        if body.count(marker) != 1:
            raise SystemExit("SUSFS integration: lookup_dcache anchor not unique")
        body = body.replace(marker, hook + marker, 1)
        text = text[:start] + body + text[end:]
    path.write_text(text)
    print("SUSFS integration: fs/namei.c targeted SUS_PATH lookup hook applied")


def patch_open(target):
    path = target / "fs/open.c"
    text = path.read_text()
    text = insert_once(
        text,
        '#include <linux/compat.h>\n',
        '#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\nextern struct filename *susfs_open_redirect_spoof_do_sys_openat(struct inode *inode);\n#endif\n\n',
        "open extern",
    )
    start = text.find("long do_sys_open(")
    if start < 0:
        raise SystemExit("SUSFS integration: Crimson do_sys_open not found")
    end = text.find("\n}\n", start)
    if end < 0:
        raise SystemExit("SUSFS integration: do_sys_open end not found")
    body = text[start:end]
    if "susfs_open_redirect_spoof_do_sys_openat" not in body:
        marker = "\t\tstruct file *f = do_filp_open(dfd, tmp, &op);\n"
        if body.count(marker) != 1:
            raise SystemExit("SUSFS integration: do_sys_open filp_open anchor not unique")
        body = body.replace(marker, marker + (
            "#ifdef CONFIG_KSU_SUSFS_OPEN_REDIRECT\n"
            "\t\tif (f && !IS_ERR(f) &&\n"
            "\t\t    SUSFS_IS_INODE_OPEN_REDIRECT_WITHOUT_UID_CHECK(file_inode(f))) {\n"
            "\t\t\tstruct filename *fake_filename =\n"
            "\t\t\t\tsusfs_open_redirect_spoof_do_sys_openat(file_inode(f));\n"
            "\t\t\tif (fake_filename && !IS_ERR(fake_filename)) {\n"
            "\t\t\t\tfilp_close(f, NULL);\n"
            "\t\t\t\tput_unused_fd(fd);\n"
            "\t\t\t\tputname(tmp);\n"
            "\t\t\t\ttmp = fake_filename;\n"
            "\t\t\t\tgoto retry;\n"
            "\t\t\t}\n"
            "\t\t}\n"
            "#endif\n"
        ), 1)
        body = body.replace("\tfd = get_unused_fd_flags(flags);\n", "retry:\n\tfd = get_unused_fd_flags(flags);\n", 1)
        text = text[:start] + body + text[end:]
    path.write_text(text)
    print("SUSFS integration: fs/open.c targeted OPEN_REDIRECT hook applied")


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
        for path in CLEAN_FILES:
            apply_file_patch(repo, target, path, td)

    patch_namei(target)
    patch_open(target)
    print("SUSFS integration: fs/proc/base.c remains intentionally unmodified because its Crimson layout diverges from Rajdeep's proc readlink implementation")
    print("SUSFS v2.2.0 targeted VFS/proc integration applied")


if __name__ == "__main__":
    main()
