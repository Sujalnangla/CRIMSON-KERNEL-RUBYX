#include <linux/lsm_hooks.h>
#include <linux/uidgid.h>
#include <linux/version.h>
#include <linux/binfmts.h>
#include <linux/err.h>
#include <linux/atomic.h>

#include "klog.h" // IWYU pragma: keep
#include "runtime/ksud_boot.h"
#include "compat/kernel_compat.h"
#include "setuid_hook.h"
#include "manager/throne_tracker.h"

#ifdef CONFIG_KSU_SUSFS
#include <linux/susfs.h>
#include <linux/susfs_def.h>
#include "selinux/selinux.h"
#endif

#ifndef KSU_KPROBES_HOOK

#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 10, 0) ||                           \
	defined(CONFIG_IS_HW_HISI) || defined(CONFIG_KSU_ALLOWLIST_WORKAROUND)
struct key *init_session_keyring = NULL;

static int ksu_key_permission(key_ref_t key_ref, const struct cred *cred,
			      unsigned perm)
{
	if (init_session_keyring != NULL) {
		return 0;
	}
	if (strcmp(current->comm, "init")) {
		// we are only interested in `init` process
		return 0;
	}
	init_session_keyring = cred->session_keyring;
	pr_info("kernel_compat: got init_session_keyring\n");
	return 0;
}
#endif

#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 3, 0)
static int ksu_inode_rename(struct mnt_idmap *idmap, struct inode *old_dir, struct dentry *old_dentry,
			    struct inode *new_dir, struct dentry *new_dentry)
#elif LINUX_VERSION_CODE >= KERNEL_VERSION(5, 12, 0)
static int ksu_inode_rename(struct user_namespace *mnt_userns, struct inode *old_dir, struct dentry *old_dentry,
			    struct inode *new_dir, struct dentry *new_dentry)
#else
static int ksu_inode_rename(struct inode *old_dir, struct dentry *old_dentry,
			    struct inode *new_dir, struct dentry *new_dentry)
#endif
{
	// skip kernel threads
	if (!current->mm) {
		return 0;
	}

	// skip non system uid
	if (current_uid().val != 1000) {
		return 0;
	}

	if (!old_dentry || !new_dentry) {
		return 0;
	}

	// Use d_name.name instead of the dangerous d_iname 
	// which can cause OOPS when the dentry is in an inconsistent state during rename
	if (strcmp(new_dentry->d_name.name, "packages.list")) {
		return 0;
	}

	char path[128];
	char *buf = dentry_path_raw(new_dentry, path, sizeof(path));
	if (IS_ERR(buf)) {
		pr_err("dentry_path_raw failed.\n");
		return 0;
	}

	if (!strstr(buf, "/system/packages.list")) {
		return 0;
	}

	// Do not track anything until the system has fully booted.
	// Parsing files during early boot from an LSM hook can causes VFS deadlocks
	if (!ksu_boot_completed) {
		return 0;
	}

	pr_debug("renameat: %s -> %s, new path: %s\n", old_dentry->d_name.name,
			new_dentry->d_name.name, buf);

	// Thread-safe execution using atomic operations to prevent race conditions
	// if system_server threads execute this hook concurrently.
	static atomic_t first_time = ATOMIC_INIT(1);

	// atomic_xchg swaps the value to 0 and returns the old value.
	// If the old value was 1, we are the first thread to reach here.
	if (atomic_xchg(&first_time, 0) == 1) {
		track_throne(true);
	} else {
		track_throne(false);
	}

	return 0;
}

static int ksu_task_fix_setuid(struct cred *new, const struct cred *old,
			       int flags)
{
	kuid_t new_uid = new->uid;
	kuid_t new_euid = new->euid;

	return ksu_handle_setresuid((uid_t)new_uid.val, (uid_t)new_euid.val,
				    (uid_t)new_uid.val);
}

#ifndef DEVPTS_SUPER_MAGIC
#define DEVPTS_SUPER_MAGIC	0x1cd1
#endif

extern int __ksu_handle_devpts(struct inode *inode); // sucompat.c

#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 3, 0)
int ksu_inode_permission(struct mnt_idmap *idmap, struct inode *inode, int mask)
#elif LINUX_VERSION_CODE >= KERNEL_VERSION(5, 12, 0)
int ksu_inode_permission(struct user_namespace *mnt_userns, struct inode *inode, int mask)
#else
int ksu_inode_permission(struct inode *inode, int mask)
#endif
{
	if (unlikely(inode && inode->i_sb && inode->i_sb->s_magic == DEVPTS_SUPER_MAGIC)) {
		__ksu_handle_devpts(inode);
	}
	return 0;
}

#ifdef CONFIG_KSU_SUSFS

#define KERNEL_SU_OPTION 0xDEADBEEF

static long do_susfs_add_sus_path(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_add_sus_path(&user_info);
	return 0;
}

static long do_susfs_add_sus_path_loop(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_add_sus_path_loop(&user_info);
	return 0;
}

static long do_susfs_hide_sus_mnts_for_non_su_procs(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_set_hide_sus_mnts_for_non_su_procs(&user_info);
	return 0;
}

static long do_susfs_add_sus_kstat(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_add_sus_kstat(&user_info);
	return 0;
}

static long do_susfs_update_sus_kstat(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_update_sus_kstat(&user_info);
	return 0;
}

static long do_susfs_add_sus_kstat_statically(unsigned long arg3)
{
	return -ENOTTY;
}

static long do_susfs_enable_log(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_enable_log(&user_info);
	return 0;
}

static long do_susfs_set_cmdline_or_bootconfig(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_set_cmdline_or_bootconfig(&user_info);
	return 0;
}

static long do_susfs_add_open_redirect(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_add_open_redirect(&user_info);
	return 0;
}

static long do_susfs_show_version(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_show_version(&user_info);
	return 0;
}

static long do_susfs_show_enabled_features(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_get_enabled_features(&user_info);
	return 0;
}

static long do_susfs_show_variant(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_show_variant(&user_info);
	return 0;
}

static long do_susfs_enable_avc_log_spoofing(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_set_avc_log_spoofing(&user_info);
	return 0;
}

static long do_susfs_add_sus_map(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_add_sus_map(&user_info);
	return 0;
}

static long do_susfs_set_uname(unsigned long arg3)
{
	void __user *user_info = (void __user *)arg3;
	if (!user_info)
		return -EFAULT;
	susfs_set_uname(&user_info);
	return 0;
}

static int ksu_task_prctl(int option, unsigned long arg2, unsigned long arg3,
                          unsigned long arg4, unsigned long arg5)
{
	if (option != KERNEL_SU_OPTION)
		return 0;

	if (!is_ksu_domain())
		return -EPERM;

	long ret = 0;

	switch (arg2) {
	case CMD_SUSFS_ADD_SUS_PATH:
		ret = do_susfs_add_sus_path(arg3);
		break;
	case CMD_SUSFS_ADD_SUS_PATH_LOOP:
		ret = do_susfs_add_sus_path_loop(arg3);
		break;
	case CMD_SUSFS_HIDE_SUS_MNTS_FOR_NON_SU_PROCS:
		ret = do_susfs_hide_sus_mnts_for_non_su_procs(arg3);
		break;
	case CMD_SUSFS_ADD_SUS_KSTAT:
		ret = do_susfs_add_sus_kstat(arg3);
		break;
	case CMD_SUSFS_UPDATE_SUS_KSTAT:
		ret = do_susfs_update_sus_kstat(arg3);
		break;
	case CMD_SUSFS_ADD_SUS_KSTAT_STATICALLY:
		ret = do_susfs_add_sus_kstat_statically(arg3);
		break;
	case CMD_SUSFS_SET_UNAME:
		ret = do_susfs_set_uname(arg3);
		break;
	case CMD_SUSFS_ENABLE_LOG:
		ret = do_susfs_enable_log(arg3);
		break;
	case CMD_SUSFS_SET_CMDLINE_OR_BOOTCONFIG:
		ret = do_susfs_set_cmdline_or_bootconfig(arg3);
		break;
	case CMD_SUSFS_ADD_OPEN_REDIRECT:
		ret = do_susfs_add_open_redirect(arg3);
		break;
	case CMD_SUSFS_SHOW_VERSION:
		ret = do_susfs_show_version(arg3);
		break;
	case CMD_SUSFS_SHOW_ENABLED_FEATURES:
		ret = do_susfs_show_enabled_features(arg3);
		break;
	case CMD_SUSFS_SHOW_VARIANT:
		ret = do_susfs_show_variant(arg3);
		break;
	case CMD_SUSFS_ENABLE_AVC_LOG_SPOOFING:
		ret = do_susfs_enable_avc_log_spoofing(arg3);
		break;
	case CMD_SUSFS_ADD_SUS_MAP:
		ret = do_susfs_add_sus_map(arg3);
		break;
	default:
		ret = -ENOTTY;
		break;
	}

	if (arg5) {
		int err = ret < 0 ? ret : 0;
		if (put_user(err, (int __user *)arg5)) {
			if (ret == 0)
				ret = -EFAULT;
		}
	}

	return ret;
}

#endif /* CONFIG_KSU_SUSFS */

static struct security_hook_list ksu_hooks[] = {
#if LINUX_VERSION_CODE < KERNEL_VERSION(4, 10, 0) ||                           \
	defined(CONFIG_IS_HW_HISI) || defined(CONFIG_KSU_ALLOWLIST_WORKAROUND)
	LSM_HOOK_INIT(key_permission, ksu_key_permission),
#endif
	LSM_HOOK_INIT(inode_permission, ksu_inode_permission),
	LSM_HOOK_INIT(inode_rename, ksu_inode_rename),
	LSM_HOOK_INIT(task_fix_setuid, ksu_task_fix_setuid),
#ifdef CONFIG_KSU_SUSFS
	LSM_HOOK_INIT(task_prctl, ksu_task_prctl),
#endif
};

#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 8, 0)
static const struct lsm_id ksu_lsmid = {
	.name = "ksu",
	.id = 912,
};
#endif

void __init ksu_lsm_hook_init(void)
{
#if LINUX_VERSION_CODE >= KERNEL_VERSION(6, 8, 0)
	security_add_hooks(ksu_hooks, ARRAY_SIZE(ksu_hooks), &ksu_lsmid);
#elif LINUX_VERSION_CODE >= KERNEL_VERSION(4, 11, 0)
	security_add_hooks(ksu_hooks, ARRAY_SIZE(ksu_hooks), "ksu");
#else
	// https://elixir.bootlin.com/linux/v4.10.17/source/include/linux/lsm_hooks.h#L1892
	security_add_hooks(ksu_hooks, ARRAY_SIZE(ksu_hooks));
#endif
	pr_info("LSM hooks initialized.\n");
}
#else
void __init ksu_lsm_hook_init(void)
{
	return;
}
#endif
