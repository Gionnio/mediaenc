# Mediaenc 🎞️

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/macOS-000000?style=for-the-badge&logo=apple&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)
![License](https://img.shields.io/github/license/gionnio/mediaenc?style=for-the-badge)
![AI](https://img.shields.io/badge/AI-Assisted-blueviolet?style=for-the-badge&logo=openai&logoColor=white)

**Mediaenc** is a professional-grade, terminal-based video encoding automation tool developed in Python, optimized for **Apple Silicon (M1/M2/M3)**. It wraps FFmpeg with a smart, interactive UI to handle complex workflows like Batch Encoding, Quality Benchmarking, and Smart Audio handling.

![Pixel](https://github.com/user-attachments/assets/9eea1b45-e8d4-4410-8317-cc5daf818913)

## ✨ Features

* **🚀 Optimized Presets:**
    * **4K/1080p VideoToolbox:** Blazing fast GPU encoding (Main10, CQ 65).
    * **4K CPU Universal:** x265 Software (CRF 18) for archival grain preservation.
    * **High Bitrate VBR:** Variable bitrate targeting high quality standards (24-35 Mbps).
* **🧠 Smart Audio Logic:**
    * **Passthrough:** Keeps original Dolby Atmos/TrueHD.
    * **Smart Surround:** Converts DTS/TrueHD to **EAC3 (Dolby Digital Plus)** while preserving 7.1 channels.
    * **Stereo Saver:** High-efficiency AAC 2.0 downmix.
* **🏆 The "Triathlon" Benchmark:**
    * Test multiple presets on a 45s sample before encoding the whole movie.
    * Calculates **VMAF** and **SSIM** scores.
    * Shows **Efficiency** (Quality points per GB) and estimated file size (Video + Audio).
* **📊 Scientific Quality Check:**
    * Compare encoded file against source (Reference vs Distorted).
    * Automatic resolution/bit-depth alignment.
    * Human-readable verdicts (e.g., "EXCELLENT", "POOR").
* **✂️ Auto-Crop Detection:** Analyzes the video to detect and remove black bars automatically.

## 🚀 Requirements
- macOS 12.0 (Monterey) or later (Optimized for Apple Silicon).
- **FFmpeg** installed (via Homebrew).

## 🛠 Setup
1.  Install FFmpeg:
    ```bash
    brew install ffmpeg
    ```
2.  Download the project.
3.  Run the installation script:
    ```bash
    sudo ./install.sh
    ```
4.  Run the tool from any folder:
    ```bash
    mediaenc
    ```

## ⚙️ Presets Overview

| ID | Name | Type | Description |
| :--- | :--- | :--- | :--- |
| **1** | **4K VideoToolbox (CQ 65)** | GPU | **Speed & Quality.** Hardware acceleration with constant quality. |
| **2** | **1080p VideoToolbox (CQ 65)** | GPU | **Space Saving.** Downscales to 1080p while maintaining HDR/10-bit. |
| **3** | **4K CPU x265 (Medium - CRF 18)** | CPU | **Archival Master.** Software encoding for highest fidelity and grain. |
| **4** | **4K VideoToolbox (VBR 24Mbps)** | GPU | **High Quality.** Targets 24-35 Mbps variable bitrate. |

## 🧠 Smart Audio Strategy

One of the key features of Mediaenc is its **Hierarchical Audio Logic**. When starting an encode, you choose a *Strategy* that overrides individual codec settings.

| Strategy Choice | Input is AC3/EAC3 | Input is Lossless (TrueHD/DTS-HD) | Goal |
| :--- | :--- | :--- | :--- |
| **[1] Passthrough** | **COPY** | **COPY** | Keeps the original audio bit-perfect. |
| **[2] Smart Surround** | **COPY** | **CONVERT to EAC3** | **The Smart Choice.** Converts heavy tracks to **EAC3**, preserving **7.1 channels**. |
| **[3] Stereo Saver** | **CONVERT** | **CONVERT** | Downmixes everything to efficient **AAC 2.0**. |

## 🤖 AI Acknowledgment
This application was developed with the assistance of Artificial Intelligence for code generation, logic optimization, and problem-solving.

---
Created with AI, ❤️ and Python.
