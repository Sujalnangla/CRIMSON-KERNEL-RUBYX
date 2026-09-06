/* SPDX-License-Identifier: GPL-2.0+ */
#ifndef _LINUX_XARRAY_H
#define _LINUX_XARRAY_H
/*
 * eXtensible Arrays
 * Copyright (c) 2017 Microsoft Corporation
 * Author: Matthew Wilcox <mawilcox@microsoft.com>
 */

#include <linux/spinlock.h>
#include <linux/radix-tree.h>

#define xa_trylock(xa)		spin_trylock(&(xa)->xa_lock)
#define xa_lock(xa)		spin_lock(&(xa)->xa_lock)
#define xa_unlock(xa)		spin_unlock(&(xa)->xa_lock)
#define xa_lock_bh(xa)		spin_lock_bh(&(xa)->xa_lock)
#define xa_unlock_bh(xa)	spin_unlock_bh(&(xa)->xa_lock)
#define xa_lock_irq(xa)		spin_lock_irq(&(xa)->xa_lock)
#define xa_unlock_irq(xa)	spin_unlock_irq(&(xa)->xa_lock)
#define xa_lock_irqsave(xa, flags) \
				spin_lock_irqsave(&(xa)->xa_lock, flags)
#define xa_unlock_irqrestore(xa, flags) \
				spin_unlock_irqrestore(&(xa)->xa_lock, flags)

/*
 * Minimal XArray compatibility shim for the incomplete MGLRU/XArray
 * backport. This tree lacks the full XArray implementation, but
 * mm/memory.c and mm/swap_state.c call xa_is_value() to distinguish
 * tagged exceptional entries from ordinary pointers.
 *
 * In this tree the radix-tree uses bit 1 (RADIX_TREE_EXCEPTIONAL_ENTRY)
 * for exceptional entries, so test that bit rather than the upstream
 * XArray bit-0 convention.
 */
static inline bool xa_is_value(void *item)
{
	return ((unsigned long)item & RADIX_TREE_EXCEPTIONAL_ENTRY) != 0;
}

#endif /* _LINUX_XARRAY_H */
