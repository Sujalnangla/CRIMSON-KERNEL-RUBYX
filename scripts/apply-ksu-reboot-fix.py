from pathlib import Path

path = Path("kernel/reboot.c")
s = path.read_text()

anchor = '''\tstruct pid_namespace *pid_ns = task_active_pid_ns(current);\n\tchar buffer[256];\n\tint ret = 0;\n'''
if anchor not in s:
    raise SystemExit("reboot syscall local-variable anchor missing")

hook = 'if (magic1 == KSU_INSTALL_MAGIC1)'
cap = 'if (!ns_capable(pid_ns->user_ns, CAP_SYS_BOOT))'

# The source patch may already have placed the KSU hook correctly. In that
# case this script is a no-op so the CI integration step remains idempotent.
hook_count = s.count(hook)
cap_count = s.count(cap)
if hook_count == 1 and cap_count == 1 and s.index(hook) < s.index(cap):
    print("KSU reboot supercall is already before CAP_SYS_BOOT; nothing to do")
    raise SystemExit(0)

old = '''\t/* We only trust the superuser with rebooting the system. */\n\tif (!ns_capable(pid_ns->user_ns, CAP_SYS_BOOT))\n\t\treturn -EPERM;\n\n\t#ifdef CONFIG_KSU\n\tif (magic1 == KSU_INSTALL_MAGIC1)\n\t\treturn ksu_handle_sys_reboot(magic1, magic2, cmd, &arg);\n\t#endif\n'''
new = '''#ifdef CONFIG_KSU\n\t/* KernelSU supercall must be intercepted before Android's CAP_SYS_BOOT\n\t * check; otherwise untrusted_app seccomp kills libksud on reboot(142). */\n\tif (magic1 == KSU_INSTALL_MAGIC1)\n\t\treturn ksu_handle_sys_reboot(magic1, magic2, cmd, &arg);\n#endif\n\n\t/* We only trust the superuser with rebooting the system. */\n\tif (!ns_capable(pid_ns->user_ns, CAP_SYS_BOOT))\n\t\treturn -EPERM;\n'''

if s.count(old) != 1:
    raise SystemExit(
        f"expected exactly one misplaced KSU reboot hook, found {s.count(old)}"
    )
s = s.replace(old, new, 1)
path.write_text(s)
