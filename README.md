# 🎬 MEDIAENC – Ultimate Encoding Suite

**Mediaenc** is a custom-built, command-line video encoding automation tool tailored for **macOS (Apple Silicon)**. 

Developed with the assistance of **Artificial Intelligence**, this suite wraps FFmpeg in an interactive, user-friendly interface designed to streamline personal media archiving. It prioritizes the balance between archival quality, storage efficiency, and broad compatibility.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue?style=flat-square) ![Platform](https://img.shields.io/badge/Platform-Apple%20Silicon%20(M1%2FM2%2FM3)-lightgrey?style=flat-square) ![FFmpeg](https://img.shields.io/badge/Backend-FFmpeg-green?style=flat-square) ![License](https://img.shields.io/badge/License-MIT-orange?style=flat-square)

![Pixel](https://github.com/user-attachments/assets/9eea1b45-e8d4-4410-8317-cc5daf818913)

---

## ✨ Core Philosophy

This tool was created to solve specific personal archiving needs:
1.  **Automation:** Detect crop bars, map audio tracks, and handle subtitles automatically.
2.  **Decision Making:** A unique **Benchmark Mode** allows testing 45s samples with different presets to compare **VMAF**, **SSIM**, and **Efficiency (Quality/GB)** before committing to a full encode.
3.  **Control:** Granular control over audio strategies and video quality without memorizing complex FFmpeg flags.

## ⚙️ The Presets

The suite includes 4 highly tuned presets designed for specific use cases:

| ID | Name | Type | Target Use Case |
| :--- | :--- | :--- | :--- |
| **1** | **4K VideoToolbox (CQ 65)** | GPU | **Speed & Quality.** Uses hardware acceleration with a constant quality factor (CQ 65). Ideal for general 4K archiving. |
| **2** | **1080p VideoToolbox (CQ 65)** | GPU | **Space Saving.** Downscales 4K content to 1080p while maintaining HDR/10-bit properties. |
| **3** | **4K CPU x265 (CRF 18)** | CPU | **Archival Master.** Software encoding. Slower but provides the highest fidelity and grain preservation. |
| **4** | **4K High Bitrate VBR** | GPU | **Premium Streaming.** Targets a high variable bitrate (24-35 Mbps) to mimic high-end digital delivery standards. |

> **Note:** All presets default to **10-bit (Main10)** to prevent color banding and ensure HDR compatibility.

## 🧠 Smart Audio Strategy

One of the key features of Mediaenc is its **Hierarchical Audio Logic**.
When starting an encode, you choose a *Strategy* that overrides individual codec settings.

### The Logic Matrix

| Strategy Choice | Input is AC3/EAC3 | Input is Lossless (TrueHD/DTS-HD/PCM) | Goal |
| :--- | :--- | :--- | :--- |
| **[1] Passthrough** | **COPY** | **COPY** | Keeps the original audio bit-perfect (Filesize: Large). |
| **[2] Smart Surround** | **COPY** | **CONVERT to EAC3** | **The Smart Choice.** Keeps native compressed audio. Converts heavy lossless tracks to **EAC3 (Dolby Digital Plus)**. <br> *Key Feature:* Preserves **7.1 channels** if present. |
| **[3] Stereo Saver** | **CONVERT** | **CONVERT** | Downmixes everything to efficient **AAC 2.0**. |

## 🛠 Features Overview

* **Benchmark "Triathlon":** Runs a 45s test encode on a central chunk of the video (ignoring crop to avoid metric mismatches) and calculates **VMAF**, **SSIM**, and **File Size projection**.
* **Auto-Crop Detection:** Analyzes multiple frames to detect black bars and applies crop filters automatically.
* **Bit-Depth Awareness:** Automatically handles 8-bit vs 10-bit metric comparisons to prevent calculation errors.
* **Detailed Reporting:** Provides a summary of space saved (GB and %) after every job.

## 📥 Installation

1.  **Prerequisites:** Ensure you have FFmpeg installed.
    ```bash
    brew install ffmpeg
    ```
2.  **Install:**
    Run the provided `install.sh` script or manually copy the file:
    ```bash
    sudo cp mediaenc.py /usr/local/bin/mediaenc
    sudo chmod +x /usr/local/bin/mediaenc
    ```

## 🚀 Usage

Simply type `mediaenc` in your terminal from the folder containing your media files.

```bash
mediaenc
