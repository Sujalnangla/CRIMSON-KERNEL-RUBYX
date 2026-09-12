/*
 *  linux/init/version.c
 *
 *  Copyright (C) 1992  Theodore Ts'o
 *
 *  May be freely distributed as part of Linux.
 */

#include <generated/compile.h>
#include <linux/build-salt.h>
#include <linux/export.h>
#include <linux/uts.h>
#include <linux/utsname.h>
#include <generated/utsrelease.h>
#include <linux/version.h>
#include <linux/proc_ns.h>

#ifndef CONFIG_KALLSYMS
#define version(a) Version_ ## a
#define version_string(a) version(a)

extern int version_string(LINUX_VERSION_CODE);
int version_string(LINUX_VERSION_CODE);
#endif

struct uts_namespace init_uts_ns = {
	.kref = KREF_INIT(2),
	.name = {
		.sysname	= UTS_SYSNAME,
		.nodename	= UTS_NODENAME,
		.release	= UTS_RELEASE,
		.version	= UTS_VERSION,
		.machine	= UTS_MACHINE,
		.domainname	= UTS_DOMAINNAME,
	},
	.user_ns = &init_user_ns,
	.ns.inum = PROC_UTS_INIT_INO,
#ifdef CONFIG_UTS_NS
	.ns.ops = &utsns_operations,
#endif
};
EXPORT_SYMBOL_GPL(init_uts_ns);

/* Crimson Ruby kernel banner. */
const char linux_banner[] =
	"Linux version " UTS_RELEASE " (" LINUX_COMPILE_BY "@"
	LINUX_COMPILE_HOST ") (" LINUX_COMPILER ") " UTS_VERSION "\n"
	"\n"
	"   ____        _                          ____        _     _       \n"
	"  / ___|_ __ _| |_ ___ _ __ ___   ___  |  _ \\ _   _| |__ | |_   \n"
	" | |   | '__| | __/ _ \\ '_ ` _ \\ / _ \\ | |_) | | | | '_ \\| __|  \n"
	" | |___| |  | | ||  __/ | | | | | (_) ||  _ <| |_| | |_) | |_   \n"
	"  \\____|_|  |_|\\__\\___|_| |_| |_|\\___/ |_| \\_\\\\__,_|_.__/ \\__|  \n"
	"\n"
	"                 Crimson Ruby Kernel - By Shu\n";

const char *linux_banner_ptr = linux_banner;
EXPORT_SYMBOL_GPL(linux_banner_ptr);

const char linux_proc_banner[] =
	"%s version %s"
	" (" LINUX_COMPILE_BY "@" LINUX_COMPILE_HOST ")"
	" (" LINUX_COMPILER ") %s\n";

BUILD_SALT;