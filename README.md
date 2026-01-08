# Mediaenc 🎞️

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/macOS-000000?style=for-the-badge&logo=apple&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-orange?style=for-the-badge)
![Views](https://komarev.com/ghpvc/?username=gionnio-mediaenc&style=for-the-badge&label=VIEWS&color=7F00FF)
![Downloads](https://img.shields.io/github/downloads/gionnio/mediaenc/total?style=for-the-badge&color=success)
![AI](https://img.shields.io/badge/AI-Assisted-blueviolet?style=for-the-badge&logo=openai&logoColor=white)

**Mediaenc** is a professional-grade, terminal-based video encoding automation tool developed in Python, optimized for **Apple Silicon (M1/M2/M3)**. It wraps FFmpeg with a smart, interactive UI to handle complex workflows like Batch Encoding, Quality Benchmarking, and Smart Audio handling.

![Pixel](https://github.com/user-attachments/assets/9eea1b45-e8d4-4410-8317-cc5daf818913)

## ✨ Core Philosophy
This tool was born from **personal necessity** to streamline media library optimization. It was designed to **eliminate the repetitive manual configuration steps** that I found unavoidable in standard GUI software:

1.  **Automation:** Detect crop bars, map audio tracks, and handle subtitles automatically without user intervention per file.
2.  **Decision Making:** A unique **Benchmark Mode** allows testing 45s samples with different presets to compare **VMAF**, **SSIM**, and **Efficiency (Quality/GB)** before committing to a full encode.
3.  **Control:** Granular control over audio strategies and video quality without memorizing complex FFmpeg flags.

## 🚀 Features
- **Queue Manager (New in v9.2):** Build complex batches by mixing different presets in the same run. Export queues to JSON for later use or to resume work.
- **Optimized Presets:** Includes specialized modes for GPU Speed (VideoToolbox), CPU Archival (x265), and High-Bitrate VBR.
- **Smart Audio Logic:** Automatically detects audio types. Copies efficient tracks (AC3/EAC3 or Stereo AAC) and converts lossless ones (TrueHD/DTS) to **EAC3** only when beneficial (preserving 5.1/7.1 channels).
- **Triathlon Benchmark:** Runs 45s test encodes comparing **VMAF**, **SSIM**, and **Efficiency** (Quality/GB) before the full job.
- **Scientific Quality Check:** Compares the encoded file against the source using objective metrics, handling resolution and bit-depth mismatches automatically.
- **Auto-Crop Detection:** Analyzes multiple frames to detect and remove black bars automatically.
- **Detailed Reporting:** Provides a summary of space saved (GB and %) after every job.

## ⚙️ Presets Overview

The suite includes 5 highly tuned presets designed for specific use cases:

| ID | Name | Type | Target Use Case |
| :--- | :--- | :--- | :--- |
| **0** | **Remux (Passthrough)** | COPY | **Pure Cleaning.** Copies video 1:1 (Instant speed). Useful to remove unwanted audio/subs or convert audio (e.g. DTS -> EAC3) without re-encoding video. |
| **1** | **4K VideoToolbox (CQ 65)** | GPU | **Speed & Quality.** Uses hardware acceleration with a constant quality factor (CQ 65). Ideal for general 4K archiving. |
| **2** | **1080p VideoToolbox (CQ 65)** | GPU | **Space Saving.** Downscales 4K content to 1080p while maintaining HDR/10-bit properties. |
| **3** | **4K CPU x265 (Medium - CRF 18)** | CPU | **Archival Master.** Software encoding. Slower but provides the highest fidelity and grain preservation. |
| **4** | **4K High Bitrate VBR** | GPU | **High Quality VBR.** Targets a high variable bitrate (24-35 Mbps) to mimic high-end digital delivery standards. |

> **Note:** All presets default to **10-bit (Main10)** to prevent color banding and ensure HDR compatibility.

## 🛠 Advanced Workflow

### Queue Management
Mediaenc v9.2 introduces a powerful Queue Manager.
1.  **Build a Queue:** Select files and settings for a batch.
2.  **Append:** Instead of starting immediately, you can choose `[a] Append` to add more files with **different settings** (e.g., process 5 movies with GPU preset, then add 2 movies with CPU preset in the same run).
3.  **Export/Import:** Save your work plan to a JSON file (`[e] Export`) and load it later (`[4] Import Queue` from main menu) to resume processing.

## 🚀 Requirements
- macOS 12.0 (Monterey) or later (Optimized for Apple Silicon).
- **FFmpeg** installed (via Homebrew).

## 📥 Installation & Setup

1.  **Install FFmpeg:**
    ```bash
    brew install ffmpeg
    ```
2.  **Download the project** (Code > Download ZIP or via git).
3.  **Install the script:**
    Choose your preferred language (`mediaenc.py` for Italian, `mediaenc_en.py` for English) and copy it to your bin folder (rename it to `mediaenc` for easier access):
    ```bash
    # Example for English version
    sudo cp mediaenc_en.py /usr/local/bin/mediaenc
    sudo chmod +x /usr/local/bin/mediaenc
    ```
4.  **Run:**
    Simply type `mediaenc` in your terminal from any folder containing your media files.
    ```bash
    mediaenc
    ```

## 📄 License

Distributed under the MIT License.

## 🤖 AI Acknowledgment
This application was developed with the assistance of Artificial Intelligence for code generation, logic optimization, and problem-solving.

---
Created with AI, ❤️ and Python.
