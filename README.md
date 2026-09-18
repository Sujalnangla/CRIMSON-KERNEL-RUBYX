# Crimson Kernel | Redmi Note 12 Pro 5G (ruby / rubyx)
Crimson Kernel is a custom Android kernel for the **Redmi Note 12 Pro / Pro+ 5G** (`ruby`/`rubyx`, MediaTek Dimensity 1080 / MT6877). Built with an emphasis on low frame-drop rates, memory efficiency via upstream backports, and reduced battery drain without stripping out essential MediaTek hardware abstraction interfaces.
---
## 📱 Device Specifications

| Attribute | Specification |
| :--- | :--- |
| **Device Model** | Redmi Note 12 Pro / Pro+ / Discovery 5G |
| **Codename** | `ruby` / `rubyx` |
| **SoC** | MediaTek Dimensity 1080 (MT6877) |
| **Architecture** | ARM64 (`aarch64`) |
| **Kernel Base** | Linux 5.10.y (Android Common Kernel / MediaTek BSP) |

---
## ⚡ Current Features & Enhancements
### 🧠 Memory Management
- **MGLRU (Multi-Gen LRU):** Fully integrated and active (`CONFIG_LRU_GEN=y`). Greatly reduces kswapd thrashing, improves active memory reclaim, and stops aggressive background app termination.
- **ZRAM Optimizations:** Tuned memory swapping mechanisms to lower UI micro-stutters during heavy multitasking.
### 🚀 Performance & System Latency
- **Scheduler Optimizations:** Refined CFS / PELT behavior tuned to complement MediaTek EAS and frequency scaling governors.
- **IPC Latency Reductions:** Vectorized transaction handling and upstream locking improvements for lower touch-to-display response latency.
- **Filesystem Optimizations:** Modernized F2FS mount and direct I/O routines for improved SQLite read/write speeds across app databases.
### 🛡️ Security & Root Support
- Modern hook integration ready (KernelSU / APatch / SusFS support).
- Upstream Linux 5.10-LTS patches and Android Security Bulletins (ASB) synced.
---
## 🛠️ Build Instructions
### Prerequisites
- Linux build host (Ubuntu 22.04 LTS or Arch Linux recommended)
- Android Clang toolchain (AOSP Clang 14+ or proton-clang)
- Necessary build packages:
  ```bash
  sudo apt install -y git bc bison flex libssl-dev make libc6-dev libncurses5-dev libelf-dev libfl-dev python3
