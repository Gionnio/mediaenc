#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MEDIAENC - Ultimate Encoding Suite
Version: 9.2.1
Description: Professional CLI video encoder optimized for macOS Apple Silicon.
             Changelog 9.2.1: Smarter Audio Logic (No EAC3 bloat for Stereo sources).
"""

import subprocess
import sys
import os
import shutil
import json
import time
import gc
import statistics
import re
from pathlib import Path

# ============================================================
# UI COLORS
# ============================================================
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"

# ============================================================
# CONFIGURATION & PRESETS
# ============================================================
PRESETS = {
    "0": {
        "id": "0",
        "name": "Remux (Video Copy - Audio-Sub Only)",
        "type": "copy",
        "video_opts": [
            "-c:v", "copy"
        ],
        "audio_bitrate": "320k",
        "passthrough": ["aac", "ac3", "eac3", "dtshd", "dts", "mp3", "opus", "truehd", "flac"]
    },
    "1": {
        "id": "1",
        "name": "4K VideoToolbox (CQ 65)",
        "type": "gpu",
        "video_opts": [
            "-c:v", "hevc_videotoolbox",
            "-profile:v", "main10",
            "-pix_fmt", "p010le",
            "-fps_mode", "vfr",
            "-color_range", "tv",
            "-color_primaries", "bt2020",
            "-color_trc", "smpte2084",
            "-colorspace", "bt2020nc",
            "-q:v", "65"
        ],
        "audio_bitrate": "320k",
        "passthrough": ["aac", "ac3", "eac3", "dtshd", "dts", "mp3", "opus", "truehd", "flac"]
    },
    "2": {
        "id": "2",
        "name": "1080p VideoToolbox (CQ 65)",
        "type": "gpu",
        "video_opts": [
            "-c:v", "hevc_videotoolbox",
            "-profile:v", "main10",
            "-pix_fmt", "p010le",
            "-fps_mode", "vfr",
            "-color_range", "tv",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-colorspace", "bt709",
            "-q:v", "65"
        ],
        "audio_bitrate": "256k",
        "passthrough": ["aac", "ac3", "eac3", "dtshd", "dts", "mp3", "truehd"]
    },
    "3": {
        "id": "3",
        "name": "4K CPU x265 (Medium - CRF 18)",
        "type": "cpu",
        "video_opts": [
            "-c:v", "libx265",
            "-preset", "medium",
            "-crf", "18",
            "-profile:v", "main10",
            "-pix_fmt", "yuv420p10le",
            "-x265-params", "sao=0:aq-mode=2:hdr10_opt=1:repeat-headers=1",
            "-color_range", "tv",
            "-color_primaries", "bt2020",
            "-color_trc", "smpte2084",
            "-colorspace", "bt2020nc",
            "-tag:v", "hvc1"
        ],
        "audio_bitrate": "320k",
        "passthrough": ["aac", "ac3", "eac3", "dtshd", "dts", "mp3", "opus", "truehd", "flac"]
    },
    "4": {
        "id": "4",
        "name": "4K High Bitrate VBR (24Mbps)",
        "type": "gpu",
        "video_opts": [
            "-c:v", "hevc_videotoolbox",
            "-profile:v", "main10",
            "-pix_fmt", "p010le",
            "-fps_mode", "vfr",
            "-color_range", "tv",
            "-color_primaries", "bt2020",
            "-color_trc", "smpte2084",
            "-colorspace", "bt2020nc",
            "-tag:v", "hvc1",
            "-b:v", "24000k",
            "-maxrate", "35000k",
            "-bufsize", "35000k"
        ],
        "audio_bitrate": "320k",
        "passthrough": ["aac", "ac3", "eac3", "dtshd", "dts", "mp3", "opus", "truehd", "flac"]
    },
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================
def clean_input_path(path: str) -> str:
    path = path.strip().strip("'").strip('"')
    if os.name != 'nt':
        path = path.replace("\\", "")
    return path

def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def clear_screen():
    print("\033c", end="")

def check_deps():
    for cmd in ["ffmpeg", "ffprobe"]:
        if not shutil.which(cmd):
            print(f"{Colors.FAIL}❌ Errore: Manca {cmd}. Installalo con 'brew install ffmpeg'.{Colors.ENDC}")
            sys.exit(1)

def has_zscale():
    try:
        res = subprocess.run(["ffmpeg", "-filters"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return "zscale" in res.stdout
    except:
        return False

def get_file_info(path):
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_entries", "format=duration",
        str(path)
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return json.loads(res.stdout)
    except Exception as e:
        print(f"{Colors.FAIL}Errore lettura file: {e}{Colors.ENDC}")
        return None

def get_resolution(path):
    info = get_file_info(path)
    if info:
        for s in info.get("streams", []):
            if s.get("codec_type") == "video":
                return int(s.get("width", 0)), int(s.get("height", 0))
    return 0, 0

def is_hdr(streams):
    for s in streams:
        if s.get("codec_type") == "video":
            transfer = s.get("color_transfer", "").lower()
            primaries = s.get("color_primaries", "").lower()
            if transfer in ("smpte2084", "arib-std-b67") or primaries == "bt2020":
                return True
            return False
    return False

# ============================================================
# CROP DETECTION
# ============================================================
def detect_black_bars(input_path: Path, duration: float):
    timestamps = [duration * 0.20, duration * 0.50, duration * 0.75]
    detected_crops = []
    full_path = str(input_path)
    
    print(f"{Colors.BLUE} ⏳ Analisi crop...{Colors.ENDC}")

    orig_w = 0
    orig_h = 0
    info = get_file_info(input_path)
    if info:
        for s in info.get("streams", []):
            if s.get("codec_type") == "video":
                orig_w = int(s.get("width", 0))
                orig_h = int(s.get("height", 0))
                break
    
    if orig_w == 0: return None

    for ts in timestamps:
        cmd = [
            "ffmpeg", "-hide_banner", "-y",
            "-ss", str(ts),
            "-i", full_path,
            "-frames:v", "40",
            r"-vf", r"select=gte(n\,20),cropdetect=0.1:2:0",
            "-f", "null", "-"
        ]
        try:
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
            stdout, stderr = p.communicate()
            if stderr:
                for line in stderr.splitlines():
                    if "crop=" in line:
                        try:
                            c = line.strip().split("crop=")[-1]
                            parts = c.split(":")
                            if len(parts) >= 4:
                                W, H, X, Y = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
                                if W == orig_w and X == 0:
                                    if abs(orig_h - H) > 10:
                                        detected_crops.append((W, H, X, Y))
                        except:
                            pass
        except Exception:
            pass

    if not detected_crops:
        return None

    try:
        heights = [c[1] for c in detected_crops]
        final_h = statistics.mode(heights)
        ys = [c[3] for c in detected_crops if c[1] == final_h]
        final_y = statistics.mode(ys)
        return f"crop={orig_w}:{final_h}:0:{final_y}"
    except:
        last = detected_crops[-1]
        return f"crop={last[0]}:{last[1]}:{last[2]}:{last[3]}"

# ============================================================
# TRACK SELECTION
# ============================================================
def select_tracks(streams, track_type="audio"):
    candidates = [s for s in streams if s.get("codec_type") == track_type]
    if not candidates:
        print(f"{Colors.WARNING}Nessuna traccia {track_type} trovata.{Colors.ENDC}")
        return []

    print(f"\n{Colors.CYAN}--- Selezione {track_type.upper()} ---{Colors.ENDC}")
    map_indices = {}
    for idx, s in enumerate(candidates):
        real_index = s.get("index")
        tags = s.get("tags", {}) or {}
        lang = tags.get("language", "und").lower()
        title = tags.get("title", "-")
        codec = s.get("codec_name", "unknown")
        channels = s.get("channels", 2) # Default to 2 if unknown
        
        info = f"[{idx+1}] {lang.upper()} ({codec})"
        if track_type == "audio":
            info += f" {channels}ch"
        if title != "-":
            info += f" - {title}"
        print(info)
        map_indices[idx+1] = {"index": real_index, "lang": lang, "codec": codec, "channels": channels}

    default_msg = "Default ITA" if track_type == "audio" else "nessuno"
    prompt = f"Scegli tracce (es. 1,3 o Invio per {default_msg}, q=Indietro): "
    choice = input(f"{Colors.BOLD}{prompt}{Colors.ENDC}").strip()
    
    if choice.lower() == 'q': return None

    selected_real_indices = []
    default_indices = [k for k, v in map_indices.items() if v['lang'] == 'ita'] if track_type == "audio" else []
    if not default_indices and track_type == "audio": default_indices = [1]

    if not choice:
        for k in default_indices: selected_real_indices.append(map_indices[k])
    else:
        try:
            for p in choice.replace(",", " ").split():
                k = int(p)
                if k in map_indices: selected_real_indices.append(map_indices[k])
        except:
            for k in default_indices: selected_real_indices.append(map_indices[k])
    return selected_real_indices

# ============================================================
# FFMPEG EXECUTION
# ============================================================
def format_time(seconds):
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

def run_ffmpeg_piped(cmd, total_duration):
    full_cmd = cmd + ["-progress", "pipe:1", "-nostats", "-v", "error"]
    process = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    start_time = time.time()
    out_time_us = 0
    speed_x = 0.0
    fps = 0.0
    calculated_speed = 0.0
    elapsed_str = "00:00:00"
    
    captured_errors = []
    
    try:
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None: break
            if line:
                line = line.strip()
                if "=" in line:
                    key, value = line.split("=", 1)
                    key, value = key.strip(), value.strip()
                    
                    if key == "out_time_us":
                        try: out_time_us = int(value)
                        except: pass
                    elif key == "speed":
                        try: speed_x = float(value.replace("x", ""))
                        except: pass
                    elif key == "fps":
                        try:
                            fps = float(value)
                            if fps > 0: calculated_speed = fps / 23.976
                        except: pass
                    elif key == "progress" and value in ["continue", "end"]:
                        current_sec = out_time_us / 1_000_000
                        pct = min(100, (current_sec / total_duration) * 100) if total_duration > 0 else 0
                        elapsed_str = format_time(time.time() - start_time)
                        final_speed = calculated_speed if calculated_speed > 0 else speed_x
                        eta_str = "--:--:--"
                        if final_speed > 0:
                            remaining_sec = (total_duration - current_sec) / final_speed
                            eta_str = format_time(remaining_sec)
                        
                        bar_str = "#" * int(pct/5) + "." * (20 - int(pct/5))
                        sys.stdout.write(f"\r[{bar_str}] {pct:5.1f}% | Time: {elapsed_str} | ETA: {eta_str} | FPS: {fps:3.0f} | {final_speed:.2f}x")
                        sys.stdout.flush()
    finally:
        if process.stdout: process.stdout.close()
        stderr_output = process.stderr.read()
        if stderr_output:
            captured_errors.append(stderr_output)
        process.wait()
    
    if process.returncode == 0:
        bar_str = "#" * 20
        final_speed = calculated_speed if calculated_speed > 0 else speed_x
        sys.stdout.write(f"\r[{bar_str}] 100.0% | Time: {elapsed_str} | ETA: 00:00:00 | FPS: {fps:3.0f} | {final_speed:.2f}x")
        sys.stdout.flush()
        print()
        return True
    else:
        print(f"\n{Colors.FAIL}❌ FFmpeg Error Log:{Colors.ENDC}")
        for err in captured_errors:
            print(err)
        return False

# ============================================================
# METRICS PARSING
# ============================================================
def parse_ssim_output(output_str):
    lines = output_str.splitlines()
    pattern = r"(?:all|mean|average|All)[:\s]+([0-9\.]+)"
    for line in reversed(lines):
        if "SSIM" in line:
            match = re.search(pattern, line, re.IGNORECASE)
            if match: return match.group(1)
    return "N/A"

def get_quality_verdict(score, metric="VMAF"):
    try: s = float(score)
    except: return "N/A", "N/A", Colors.ENDC
    if metric == "VMAF":
        if s >= 95: return "ECCELLENTE", "Indistinguibile (Trasparente)", Colors.GREEN
        if s >= 93: return "OTTIMO", "Differenze impercettibili", Colors.GREEN
        if s >= 90: return "BUONO", "Alta Qualità", Colors.CYAN
        if s >= 80: return "ACCETTABILE", "Visibile", Colors.WARNING
        return "SCARSO", "Artefatti evidenti", Colors.FAIL
    elif metric == "SSIM":
        if s >= 0.99: return "ECCELLENTE", "Identico", Colors.GREEN
        if s >= 0.98: return "BUONO", "Alta Fedeltà", Colors.CYAN
        if s >= 0.95: return "ACCETTABILE", "Buono", Colors.WARNING
        return "SCARSO", "Diverso", Colors.FAIL
    return "N/A", "", Colors.ENDC

# ============================================================
# MODE: TEST BENCHMARK
# ============================================================
def mode_test_bench():
    print(f"\n{Colors.HEADER}=== TEST BENCHMARK (Sample 45s - Video Only) ==={Colors.ENDC}")
    
    print("\nTrascina il file VIDEO (q=Indietro):")
    raw_path = input("> ").strip()
    if raw_path.lower() == 'q': return
    input_path = Path(clean_input_path(raw_path))
    if not input_path.exists(): print("File non valido."); return

    info = get_file_info(input_path)
    if not info: return
    duration = float(info.get("format", {}).get("duration", 0))
    start_time = duration / 2
    
    while True:
        print(f"\nSeleziona i Preset da confrontare (es. 1,3,4):")
        for pid, pdata in PRESETS.items():
            print(f" [{pid}] {pdata['name']}")
        
        sel = input("> ").strip()
        if sel.lower() == 'q': return
        
        selected_presets = []
        for s in sel.replace(",", " ").split():
            if s in PRESETS: selected_presets.append(PRESETS[s])
        if not selected_presets: print("Nessun preset valido."); continue

        print(f"\n{Colors.BLUE}Generazione Reference (45s)...{Colors.ENDC}")
        ref_file = input_path.parent / f"bench_ref_{input_path.stem[:10]}.mkv"
        cmd_ref = [
            "ffmpeg", "-y", "-flags2", "+ignorecrop", "-ss", str(start_time), "-i", str(input_path),
            "-t", "45", "-map", "0:v:0", "-c:v", "copy", "-an", "-sn", str(ref_file)
        ]
        subprocess.run(cmd_ref, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if not ref_file.exists() or ref_file.stat().st_size < 1024*1024:
            print(f"{Colors.FAIL}Errore creazione Reference.{Colors.ENDC}")
            if ref_file.exists(): os.remove(ref_file)
            return

        results = []

        for preset in selected_presets:
            print(f"\n{Colors.CYAN}--- Testing: {preset['name']} ---{Colors.ENDC}")
            out_file = input_path.parent / f"bench_res_{preset['name'].replace(' ', '_')}.mkv"
            
            cmd = ["ffmpeg", "-y", "-flags2", "+ignorecrop", "-i", str(ref_file)]
            vf = []
            
            is_copy = "-c:v" in preset["video_opts"] and "copy" in preset["video_opts"]
            
            if is_copy:
                pass
            else:
                force_10bit = "p010le" in preset.get("video_opts", [])
                if "1080p" in " ".join(preset.get("video_opts", [])) or "1080p" in preset['name']:
                     vf.append("scale=1920:-2:flags=lanczos,format=p010le" if force_10bit else "scale=1920:-2:flags=lanczos")
                elif preset.get('type') == "gpu":
                     vf.append("format=p010le")
                 
            cmd += ["-map", "0:v:0"]
            cmd += preset["video_opts"]
            if vf: cmd += ["-vf", ",".join(vf)]
            
            cmd.append(str(out_file))
            
            t0 = time.time()
            ok = run_ffmpeg_piped(cmd, 45)
            t_elapsed = time.time() - t0
            
            if not ok or not out_file.exists() or out_file.stat().st_size == 0:
                print(f"{Colors.FAIL}Errore encoding (File nullo).{Colors.ENDC}")
                continue
                
            fps_avg = (45 * 24) / t_elapsed
            
            if is_copy:
                score_vmaf = 100.0
                score_ssim = 1.0000
            else:
                ref_chain = "[1:v]"
                if force_10bit: ref_chain += "format=yuv420p10le,"
                if "1080p" in " ".join(preset.get("video_opts", [])) or "1080p" in preset['name']:
                    ref_chain += "scale=1920:-2:flags=lanczos,"
                ref_chain = ref_chain.rstrip(",")
                
                common_input = ["-flags2", "+ignorecrop", "-i", str(out_file),
                                "-flags2", "+ignorecrop", "-i", str(ref_file)]

                print(f"{Colors.BLUE}Calcolo VMAF...{Colors.ENDC}")
                json_vmaf = out_file.with_suffix(".json")
                vmaf_model = "vmaf_4k_v0.6.1" if "4K" in preset['name'] else "vmaf_v0.6.1"
                
                filter_str = f"{ref_chain}[ref];[0:v][ref]libvmaf=model=version={vmaf_model}:n_subsample=10:log_fmt=json:log_path={json_vmaf}"
                if ref_chain == "[1:v]": filter_str = f"[0:v][1:v]libvmaf=model=version={vmaf_model}:n_subsample=10:log_fmt=json:log_path={json_vmaf}"
                
                subprocess.run(["ffmpeg"] + common_input + ["-filter_complex", filter_str, "-f", "null", "-"],
                               stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
                
                score_vmaf = 0
                if json_vmaf.exists():
                    with open(json_vmaf, 'r') as f:
                        try: d = json.load(f); score_vmaf = d.get("pooled_metrics", {}).get("vmaf", {}).get("mean", 0)
                        except: pass
                    os.remove(json_vmaf)

                print(f"{Colors.BLUE}Calcolo SSIM...{Colors.ENDC}")
                filter_str_ssim = f"{ref_chain}[ref];[0:v][ref]ssim" if ref_chain != "[1:v]" else "[0:v][1:v]ssim"
                proc_ssim = subprocess.run(["ffmpeg"] + common_input + ["-filter_complex", filter_str_ssim, "-f", "null", "-"],
                                           stderr=subprocess.PIPE, text=True)
                score_ssim = parse_ssim_output(proc_ssim.stderr)

            video_size_gb = (out_file.stat().st_size / 45) * duration / (1024**3)
            audio_bitrate_str = preset.get('audio_bitrate', '320k')
            try: audio_kbps = int(audio_bitrate_str.replace('k', ''))
            except: audio_kbps = 320
            
            audio_size_gb = (audio_kbps * duration) / 8 / 1024 / 1024
            total_est_gb = video_size_gb + audio_size_gb
            
            results.append({
                "preset": preset,
                "name": preset['name'],
                "fps": fps_avg,
                "vmaf": score_vmaf,
                "ssim": score_ssim,
                "size_gb": total_est_gb
            })
            os.remove(out_file)

        if ref_file.exists(): os.remove(ref_file)

        print(f"\n{Colors.HEADER}=== RISULTATI BENCHMARK COMPLETO (v9.2.1) ==={Colors.ENDC}")
        print(f"{'PRESET':<32} | {'VMAF':<5} | {'VOTO':<11} | {'SSIM':<6} | {'EFF':<5} | {'SIZE'}")
        print("-" * 90)
        
        results.sort(key=lambda x: x['vmaf'], reverse=True)
        
        for i, r in enumerate(results):
            rating, _, col = get_quality_verdict(r['vmaf'], "VMAF")
            vmaf_str = f"{col}{r['vmaf']:.1f}{Colors.ENDC}"
            voto_str = f"{col}{rating:<11}{Colors.ENDC}"
            
            eff = r['vmaf'] / r['size_gb'] if r['size_gb'] > 0 else 0
            ssim_val = str(r['ssim'])[:6] if r['ssim'] != "N/A" else "N/A"

            print(f"[{i+1}] {r['name']:<32} | {vmaf_str:<5} | {voto_str} | {ssim_val:<6} | {eff:.2f}  | {r['size_gb']:.1f} GB")
        print("-" * 90)
        
        print("\nCosa vuoi fare?")
        print(" [1] Ripeti Test (Stesso file, altri preset)")
        print(" [2] Procedi all'Encode (Usa un preset testato)")
        print(" [q] Torna al Menu Principale")
        
        choice = input("> ").strip().lower()
        if choice == '1':
            continue
        elif choice == '2':
            if len(results) == 1:
                target_preset = results[0]['preset']
            else:
                sel_p = input("Quale preset usare? (Inserisci numero): ").strip()
                try:
                    idx = int(sel_p) - 1
                    target_preset = results[idx]['preset']
                except:
                    print("Selezione non valida. Ritorno al menu.")
                    return
            mode_encode(direct_file=input_path, direct_preset=target_preset)
            return
        else:
            return

# ============================================================
# MODALITÀ: QUALITY CHECK
# ============================================================
def mode_quality_check():
    print(f"\n{Colors.HEADER}=== ANALISI QUALITÀ VIDEO ==={Colors.ENDC}")
    
    print("\n1. Trascina il file REFERENCE (Originale/Remux) (q=Indietro):")
    ref_input = input("> ").strip()
    if ref_input.lower() == 'q': return
    ref_path = clean_input_path(ref_input)
    if not os.path.exists(ref_path): print("File non valido."); return

    print("\n2. Trascina il file DISTORTED (Encodato) (q=Indietro):")
    dist_input = input("> ").strip()
    if dist_input.lower() == 'q': return
    dist_path = clean_input_path(dist_input)
    if not os.path.exists(dist_path): print("File non valido."); return

    force_no_crop = False
    print("\n[ Opzioni Allineamento ]")
    print("Se hai encodato senza tagliare le bande nere, disabilita l'Auto-Crop.")
    opt_crop = input("Forzare confronto 1:1 (Disabilita Auto-Crop)? [s/N]: ").strip().lower()
    if opt_crop == 's':
        force_no_crop = True
        print(f"{Colors.WARNING}→ Auto-Crop Disabilitato (Modalità 1:1).{Colors.ENDC}")

    crop_filter_chain = ""
    if not force_no_crop:
        ref_w, ref_h = get_resolution(ref_path)
        dist_w, dist_h = get_resolution(dist_path)
        if ref_w > 0 and dist_w > 0:
            if ref_h > dist_h or ref_w > dist_w:
                print(f"{Colors.CYAN}ℹ️ Rilevata differenza risoluzione.{Colors.ENDC}")
                crop_w, crop_h = dist_w, dist_h
                crop_x, crop_y = (ref_w - dist_w) // 2, (ref_h - dist_h) // 2
                crop_filter_chain = f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y}[ref_cropped];"
                print(f"{Colors.GREEN}→ Applico auto-crop al reference.{Colors.ENDC}")
    
    print("\n3. Scegli Metrica (q=Indietro):")
    print(" [1] VMAF")
    print(" [2] SSIM")
    metric_choice = input("> ").strip()
    if metric_choice.lower() == 'q': return

    output_report = Path(dist_path).parent / f"quality_log_{Path(dist_path).stem}.txt"
    json_report = Path(dist_path).parent / f"vmaf_report_{Path(dist_path).stem}.json"
    
    ref_label = "[0:v]"
    dist_label = "[1:v]"
    if crop_filter_chain: ref_label = "[ref_cropped]"

    cmd_base = ["ffmpeg", "-i", ref_path, "-i", dist_path]
    filter_complex = ""
    metric_name = ""

    if metric_choice == "1":
        metric_name = "VMAF"
        print("\nScegli Modello VMAF:")
        print(" [1] 4K HDR")
        print(" [2] 1080p SDR")
        m_choice = input("> ").strip()
        model = "vmaf_v0.6.1"
        if m_choice == "1": model = "vmaf_4k_v0.6.1"
        filter_complex = f"{crop_filter_chain}{dist_label}{ref_label}libvmaf=model=version={model}:n_subsample=10:log_fmt=json:log_path={json_report}"

    elif metric_choice == "2":
        metric_name = "SSIM"
        filter_complex = f"{crop_filter_chain}{dist_label}{ref_label}ssim=stats_file={output_report}"
    
    else: print("Scelta non valida."); return

    print(f"\n{Colors.BLUE}🚀 Avvio analisi {metric_name}...{Colors.ENDC}")
    cmd = cmd_base + ["-filter_complex", filter_complex, "-f", "null", "-"]

    try:
        process = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        stderr_output = process.stderr
        print(f"\n{Colors.GREEN}✅ Analisi Completata.{Colors.ENDC}")

        score = "N/A"
        if metric_choice == "1":
             if os.path.exists(json_report):
                with open(json_report, 'r') as jf:
                    data = json.load(jf)
                    if "pooled_metrics" in data:
                        score = data["pooled_metrics"].get("vmaf", {}).get("mean", "N/A")
        else:
             score = parse_ssim_output(stderr_output)

        print("-" * 40)
        print(f"{Colors.BOLD}RISULTATO {metric_name}:{Colors.ENDC}")
        print(f"Punteggio: {Colors.BOLD}{score}{Colors.ENDC}")
        rating, comment, color = get_quality_verdict(score, metric_name)
        print(f"Giudizio:  {color}{rating}{Colors.ENDC}")
        print(f"Note:      {comment}")
        print("-" * 40)

    except KeyboardInterrupt:
        print("\nInterrotto dall'utente.")
    except Exception as e:
        print(f"Errore: {e}")

# ============================================================
# MODALITÀ: ENCODING (Supports Direct Handoff)
# ============================================================
def mode_encode(direct_file=None, direct_preset=None):
    zscale_available = has_zscale()
    if zscale_available:
        print(f"{Colors.GREEN}✓ Filtro zscale rilevato{Colors.ENDC}")
    else:
        print(f"{Colors.WARNING}⚠️ Filtro zscale NON rilevato.{Colors.ENDC}")

    current_preset = None
    
    if direct_preset:
        current_preset = direct_preset
        print(f"\n{Colors.CYAN}★ Preset selezionato dal Benchmark: {current_preset['name']}{Colors.ENDC}")
    else:
        print("\nSeleziona preset (q=Indietro):")
        for pid, pdata in PRESETS.items():
            print(f" [{pid}] {pdata['name']}")
        
        c = input("> ").strip().lower()
        if c == 'q': return

        if c in PRESETS:
            current_preset = PRESETS[c]
        else:
            return

    files = []
    if direct_file:
        files.append(direct_file)
    else:
        print("\nTrascina file o cartella (q=Indietro):")
        raw_path = input("> ").strip()
        if raw_path.lower() == 'q': return
        
        input_path = Path(clean_input_path(raw_path))
        if input_path.is_file(): files.append(input_path)
        elif input_path.is_dir():
            for f in input_path.rglob("*"):
                if f.suffix.lower() in [".mkv", ".mp4", ".mov", ".avi"] and not f.name.startswith("._"):
                    files.append(f)
    
    if not files: print("Nessun file trovato."); return
    files.sort()
    
    jobs = []
    output_dir = Path.home() / "Movies"
    if not output_dir.exists(): output_dir.mkdir()

    for idx, f in enumerate(files):
        print(f"\n{Colors.WARNING}=== Configurazione File {idx+1}/{len(files)}: {f.name} ==={Colors.ENDC}")
        info = get_file_info(f)
        if not info: continue
        
        duration = float(info.get("format", {}).get("duration", 0))
        streams = info.get("streams", [])
        hdr_found = is_hdr(streams)
        
        # --- CROP ---
        crop_filter = detect_black_bars(f, duration)
        
        is_video_copy = "-c:v" in current_preset["video_opts"] and "copy" in current_preset["video_opts"]
        if is_video_copy:
            crop_filter = None
            print(f"{Colors.BLUE}ℹ️ Remux Mode: Auto-Crop disabilitato (Video Copy).{Colors.ENDC}")
        
        if crop_filter:
            print(f"{Colors.GREEN}  → Crop rilevato: {crop_filter}{Colors.ENDC}")
            confirm = input(f"  Confermi? [s/n] (Invio=Si, n=Manuale, q=Indietro): ").lower()
            if confirm == 'q': return
            if confirm == 'n':
                m = input("  Crop manuale (es. 3840:1608:0:276) o Invio per NO: ").strip()
                crop_filter = f"crop={m}" if m and not m.startswith("crop=") else (m if m else None)
        elif not is_video_copy:
            print(f"{Colors.WARNING}  ⚠️ Nessun crop auto.{Colors.ENDC}")
            m = input("  Crop manuale o Invio per originale (q=Indietro): ").strip()
            if m.lower() == 'q': return
            crop_filter = f"crop={m}" if m and not m.startswith("crop=") else (m if m else None)
            
        # --- AUDIO STRATEGY ---
        print("\nScegli Strategia Audio:")
        print(" [1] Passthrough (Copia 1:1) - Default")
        print(f" [2] Converti in {Colors.BOLD}EAC3{Colors.ENDC} (Smart Surround - 7.1 Support)")
        print(" [3] Converti in AAC Stereo (Risparmio)")
        a_choice = input("> ").strip()
        audio_mode = "copy"
        if a_choice == "2": audio_mode = "eac3"
        elif a_choice == "3": audio_mode = "aac"

        sel_audio = select_tracks(streams, "audio")
        if sel_audio is None: return

        sel_subs = select_tracks(streams, "subtitle")
        if sel_subs is None: return

        # FILENAME SANITIZATION
        safe_preset_name = current_preset['name'].replace("/", "-").replace(":", "-")
        outfile = output_dir / f"{f.stem}_enc_{safe_preset_name}.mkv"
        
        jobs.append({
            "input": f, "output": outfile, "duration": duration,
            "hdr": hdr_found, "crop": crop_filter,
            "sel_audio": sel_audio, "sel_subs": sel_subs,
            "audio_mode": audio_mode
        })

    # --- RIEPILOGO PRE-START ---
    print(f"\n{Colors.HEADER}=== PIANO DI CODIFICA ==={Colors.ENDC}")
    for j in jobs:
        print(f"File: {j['input'].name}")
        print(f"Video: {current_preset['name']}")
        
        print("Audio:")
        for t in j['sel_audio']:
            action = "COPIA"
            if j['audio_mode'] == "eac3":
                if t['codec'] in ['ac3', 'eac3']:
                    action = "SMART COPY (Già AC3/EAC3)"
                elif t['channels'] <= 2:
                    action = "SMART COPY (Stereo/Mono - No Bloat)"
                else:
                    action = "CONVERTI (EAC3 640k)"
            elif j['audio_mode'] == "aac":
                action = "CONVERTI (AAC 2.0)"
            elif t['codec'] not in current_preset['passthrough']:
                action = "CONVERTI (Fallback AC3)"
            
            print(f"  - [{t['lang'].upper()}] {t['codec']} ({t['channels']}ch): {action}")
            
        print("Sottotitoli:")
        if not j['sel_subs']:
            print("  - Nessuno")
        else:
            for t in j['sel_subs']:
                print(f"  - [{t['lang'].upper()}] {t['codec']}: COPIA")
        print("---")

    if input("\nAvviare? [s/n/q]: ").lower() not in ['s', 'y']: return

    for i, job in enumerate(jobs):
        print(f"\n{Colors.BOLD}Elaborazione {i+1}/{len(jobs)}: {job['input'].name}{Colors.ENDC}")
        cmd = ["ffmpeg", "-y", "-i", str(job['input'])]
        vf_chain = []
        if job['crop']: vf_chain.append(job['crop'])
        
        if is_video_copy:
            pass
        else:
            is_1080_sdr = (current_preset['name'] == '1080p') or ("1080p" in current_preset['name'])
            if is_1080_sdr:
                if job['hdr']:
                    if zscale_available: vf_chain.append("scale=1920:-2,zscale=t=bt709:p=bt709:m=bt709:r=tv,format=p010le")
                    else: vf_chain.append("scale=1920:-2:flags=lanczos,format=p010le")
                else:
                    vf_chain.append("scale=1920:-2:flags=lanczos,format=p010le")
            elif current_preset.get('type') == "gpu":
                 vf_chain.append("format=p010le")

        cmd += ["-map", "0:v:0"]
        cmd += current_preset["video_opts"]
        
        if vf_chain and not is_video_copy:
            cmd += ["-vf", ",".join(vf_chain)]

        a_idx = 0
        for track in job['sel_audio']:
            cmd += ["-map", f"0:{track['index']}"]
            
            if job['audio_mode'] == "eac3":
                if track['codec'] in ['ac3', 'eac3']:
                    cmd += [f"-c:a:{a_idx}", "copy"]
                elif track['channels'] <= 2:
                    cmd += [f"-c:a:{a_idx}", "copy"]
                else:
                    cmd += [f"-c:a:{a_idx}", "eac3", f"-b:a:{a_idx}", "640k"]
            elif job['audio_mode'] == "aac":
                cmd += [f"-c:a:{a_idx}", "aac", f"-b:a:{a_idx}", "256k", "-ac", "2"]
            else:
                if track['codec'] in current_preset["passthrough"]:
                    cmd += [f"-c:a:{a_idx}", "copy"]
                else:
                    cmd += [f"-c:a:{a_idx}", "ac3", f"-b:a:{a_idx}", current_preset["audio_bitrate"]]
            a_idx += 1
            
        for track in job['sel_subs']: cmd += ["-map", f"0:{track['index']}"]
        if job['sel_subs']: cmd += ["-c:s", "copy"]
            
        cmd.append(str(job['output']))
        
        if run_ffmpeg_piped(cmd, job['duration']):
            in_size = job['input'].stat().st_size
            out_file = Path(str(job['output']))
            if out_file.exists():
                out_size = out_file.stat().st_size
                ratio = (out_size / in_size) * 100
                diff = in_size - out_size
                
                print(f"{Colors.CYAN}📊 STATISTICHE FILE:{Colors.ENDC}")
                print(f"  Originale:  {format_size(in_size)}")
                print(f"  Encodato:   {format_size(out_size)}")
                print(f"  Ratio:      {ratio:.1f}% (Hai risparmiato {format_size(diff)})")
            
            print(f"{Colors.GREEN}✔ File completato.{Colors.ENDC}")
        else:
            print(f"{Colors.FAIL}❌ Errore.{Colors.ENDC}")
            
        if i < len(jobs) - 1:
            print("Pausa tecnica 5s..."); time.sleep(5); gc.collect()

# ============================================================
# MAIN ENTRY POINT
# ============================================================
def main():
    print(f"{Colors.BOLD}=== MEDIAENC – Ultimate Suite v9.2.1 ==={Colors.ENDC}")
    check_deps()
    
    while True:
        print("\nCosa vuoi fare?")
        print(f" {Colors.GREEN}[1] ENCODE (CPU/GPU){Colors.ENDC}")
        print(f" {Colors.CYAN}[2] CHECK QUALITÀ (VMAF / SSIM){Colors.ENDC}")
        print(f" {Colors.WARNING}[3] TEST BENCHMARK (Confronta Preset){Colors.ENDC}")
        print(f" [q] Esci")
        
        choice = input("> ").strip().lower()
        
        if choice == "1":
            mode_encode()
        elif choice == "2":
            mode_quality_check()
        elif choice == "3":
            mode_test_bench()
        elif choice == "q":
            sys.exit(0)
        else:
            print("Scelta non valida.")

if __name__ == "__main__":
    main()
