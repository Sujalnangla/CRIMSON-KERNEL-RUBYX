# Copyright (c) 2015-2019, MICROTRUST Incorporated
# All Rights Reserved.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# version 2 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.

# Keep the Microtrust TEE implementation distinct from the generic
# drivers/tee/tee.o module. Both provide MODULE_VERSION metadata, so using
# the same built-in module name creates a duplicate /sys/module/tee/version.
obj-y += teei.o
teei-objs += tee_core.o
teei-objs += tee_shm.o
teei-objs += tee_shm_pool.o
teei-objs += tee_client_api.o

ifeq ($(CONFIG_MICROTRUST_TEST_DRIVERS),y)
teei-objs += capi_proxy.o
endif

obj-y += soter/
