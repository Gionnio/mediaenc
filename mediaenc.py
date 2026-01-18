#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MEDIAENC - Ultimate Encoding Suite
Version: 9.2.4
Description: Professional CLI video encoder optimized for macOS Apple Silicon.
             Features: Queue Merge, Batch Summary, Safe Benchmark, Smart Audio.
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
# PRESETS
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
    if os.name != 'nt': path = path.replace("\\", "")
    return path

def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024: return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} PB"

def clear_screen(): print("\033c", end="")

def check_deps():
    for cmd in ["ffmpeg", "ffprobe"]:
        if not shutil.which(cmd):
            print(f"{Colors.FAIL}❌ Errore: Manca {cmd}.{Colors.ENDC}")
            sys.exit(1)

def has_zscale():
    try:
        res = subprocess.run(["ffmpeg", "-filters"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return "zscale" in res.stdout
    except: return False

def get_file_info(path):
    cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", "-show_entries", "format=duration", str(path)]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        return json.loads(res.stdout)
    except: return None

def get_total_duration(info):
    try:
        d = float(info.get("format", {}).get("duration", 0))
        if d > 0: return d
    except: pass
    for s in info.get("streams", []):
        if s.get("codec_type") == "video":
            try:
                d = float(s.get("duration", 0))
                if d > 0: return d
            except: pass
            try:
                d = float(s.get("tags", {}).get("DURATION", "0").split(":")[2])
                if d > 0: return d
            except: pass
    return 0.0

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
            if transfer in ("smpte2084", "arib-std-b67") or primaries == "bt2020": return True
            return False
    return False

# ============================================================
# QUEUE SERIALIZATION
# ============================================================
class JobEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Path): return str(obj)
        return super().default(obj)

def save_queue(jobs):
    print(f"\n{Colors.CYAN}--- ESPORTA CODA ---{Colors.ENDC}")
    default_name = "mediaenc_coda.json"
    desktop_path = Path.home() / "Desktop"
    fname = input(f"Nome file (Invio per '{default_name}'): ").strip()
    if not fname: fname = default_name
    if not fname.endswith(".json"): fname += ".json"
    full_path = desktop_path / fname
    try:
        with open(full_path, 'w') as f: json.dump(jobs, f, indent=4, cls=JobEncoder)
        print(f"{Colors.GREEN}✔ Coda salvata in: {full_path}{Colors.ENDC}")
    except Exception as e: print(f"{Colors.FAIL}Errore salvataggio: {e}{Colors.ENDC}")

def parse_json_queue(path_str):
    """ Helper to parse JSON and return jobs list """
    path = Path(clean_input_path(path_str))
    if not path.exists():
        print(f"{Colors.FAIL}File non trovato.{Colors.ENDC}")
        return None
    try:
        with open(path, 'r') as f: jobs_data = json.load(f)
        for job in jobs_data:
            job['input'] = Path(job['input'])
            job['output'] = Path(job['output'])
        return jobs_data
    except Exception as e:
        print(f"{Colors.FAIL}Errore caricamento: {e}{Colors.ENDC}")
        return None

# ============================================================
# CROP & TRACKS
# ============================================================
def detect_black_bars(input_path: Path, duration: float):
    timestamps = [duration * 0.20, duration * 0.50, duration * 0.75]
    detected_crops = []
    full_path = str(input_path)
    print(f"{Colors.BLUE} ⏳ Analisi crop...{Colors.ENDC}")
    orig_w, orig_h = 0, 0
    info = get_file_info(input_path)
    if info:
        for s in info.get("streams", []):
            if s.get("codec_type") == "video":
                orig_w, orig_h = int(s.get("width", 0)), int(s.get("height", 0)); break
    if orig_w == 0: return None

    for ts in timestamps:
        cmd = ["ffmpeg", "-hide_banner", "-y", "-ss", str(ts), "-i", full_path, "-frames:v", "40", r"-vf", r"select=gte(n\,20),cropdetect=0.1:2:0", "-f", "null", "-"]
        try:
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True)
            _, stderr = p.communicate()
            if stderr:
                for line in stderr.splitlines():
                    if "crop=" in line:
                        try:
                            c = line.strip().split("crop=")[-1].split(":")[0:4]
                            if len(c) >= 4:
                                W, H, X, Y = map(int, c)
                                if W == orig_w and X == 0 and abs(orig_h - H) > 10: detected_crops.append((W, H, X, Y))
                        except: pass
        except: pass

    if not detected_crops: return None
    try:
        heights = [c[1] for c in detected_crops]
        final_h = statistics.mode(heights)
        ys = [c[3] for c in detected_crops if c[1] == final_h]
        return f"crop={orig_w}:{final_h}:0:{statistics.mode(ys)}"
    except:
        last = detected_crops[-1]
        return f"crop={last[0]}:{last[1]}:{last[2]}:{last[3]}"

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
        channels = s.get("channels", 2)
        info = f"[{idx+1}] {lang.upper()} ({codec})"
        if track_type == "audio": info += f" {channels}ch"
        if title != "-": info += f" - {title}"
        print(info)
        map_indices[idx+1] = {"index": real_index, "lang": lang, "codec": codec, "channels": channels}

    default_msg = "Default ITA" if track_type == "audio" else "nessuno"
    prompt = f"Scegli tracce (es. 1,3 o Invio per {default_msg}, q=Indietro): "
    choice = input(f"{Colors.BOLD}{prompt}{Colors.ENDC}").strip()
    if choice.lower() == 'q': return None

    selected = []
    defaults = [k for k, v in map_indices.items() if v['lang'] == 'ita'] if track_type == "audio" else []
    if not defaults and track_type == "audio": defaults = [1]

    if not choice:
        for k in defaults: selected.append(map_indices[k])
    else:
        try:
            for p in choice.replace(",", " ").split():
                if int(p) in map_indices: selected.append(map_indices[int(p)])
        except:
            for k in defaults: selected.append(map_indices[k])
    return selected

# ============================================================
# FFMPEG RUNNER
# ============================================================
def format_time(seconds):
    m, s = divmod(seconds, 60); h, m = divmod(m, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d}"

def run_ffmpeg_piped(cmd, total_duration):
    full_cmd = cmd + ["-progress", "pipe:1", "-nostats", "-v", "error"]
    process = subprocess.Popen(full_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    start_time = time.time()
    out_time_us = 0
    fps = 0.0
    captured_errors = []
    
    try:
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None: break
            if line:
                key, _, value = line.strip().partition("=")
                key, value = key.strip(), value.strip()
                if key == "out_time_us":
                    try: out_time_us = int(value)
                    except: pass
                elif key == "fps":
                    try: fps = float(value)
                    except: pass
                elif key == "progress" and value in ["continue", "end"]:
                    current_sec = out_time_us / 1_000_000
                    pct = 0
                    if total_duration > 0:
                        pct = min(100, (current_sec / total_duration) * 100)
                    
                    elapsed = format_time(time.time() - start_time)
                    eta = "--:--:--"
                    if pct > 0:
                        total_est = (time.time() - start_time) / (pct/100)
                        eta = format_time(total_est - (time.time() - start_time))
                    
                    bar = "#" * int(pct/5) + "." * (20 - int(pct/5))
                    sys.stdout.write(f"\r[{bar}] {pct:5.1f}% | Time: {elapsed} | ETA: {eta} | FPS: {fps:3.0f}")
                    sys.stdout.flush()
    finally:
        if process.stdout: process.stdout.close()
        stderr_output = process.stderr.read()
        if stderr_output: captured_errors.append(stderr_output)
        process.wait()
    
    print() # Force new line to ensure stats are visible
    if process.returncode != 0:
        print(f"\n{Colors.FAIL}❌ FFmpeg Error Log:{Colors.ENDC}")
        for err in captured_errors: print(err)
        return False
    return True

# ============================================================
# METRICS & BENCHMARK
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
        if s >= 95: return "ECCELLENTE", "Indistinguibile", Colors.GREEN
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

def mode_test_bench():
    print(f"\n{Colors.HEADER}=== TEST BENCHMARK (Sample 45s - Video Only) ==={Colors.ENDC}")
    print("\nTrascina il file VIDEO (q=Indietro):")
    raw_path = input("> ").strip()
    if raw_path.lower() == 'q': return
    input_path = Path(clean_input_path(raw_path))
    if not input_path.exists(): print("File non valido."); return

    info = get_file_info(input_path)
    if not info: return
    duration = get_total_duration(info)
    start_time = duration / 2
    
    while True:
        print(f"\nSeleziona i Preset da confrontare (es. 1,3,4):")
        for pid, pdata in PRESETS.items(): print(f" [{pid}] {pdata['name']}")
        sel = input("> ").strip()
        if sel.lower() == 'q': return
        selected_presets = []
        for s in sel.replace(",", " ").split():
            if s in PRESETS: selected_presets.append(PRESETS[s])
        if not selected_presets: print("Nessun preset valido."); continue

        print(f"\n{Colors.BLUE}Generazione Reference (45s)...{Colors.ENDC}")
        ref_file = input_path.parent / f"bench_ref_{input_path.stem[:10]}.mkv"
        subprocess.run(["ffmpeg", "-y", "-flags2", "+ignorecrop", "-ss", str(start_time), "-i", str(input_path), "-t", "45", "-map", "0:v:0", "-c:v", "copy", "-an", "-sn", str(ref_file)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        if not ref_file.exists():
            print(f"{Colors.FAIL}Errore ref.{Colors.ENDC}"); return

        results = []
        for preset in selected_presets:
            print(f"\n{Colors.CYAN}--- Testing: {preset['name']} ---{Colors.ENDC}")
            out_file = input_path.parent / f"bench_res_{preset['name'].replace(' ', '_')}.mkv"
            cmd = ["ffmpeg", "-y", "-flags2", "+ignorecrop", "-i", str(ref_file)]
            vf = []
            is_copy = "-c:v" in preset["video_opts"] and "copy" in preset["video_opts"]
            
            if not is_copy:
                force_10bit = "p010le" in preset.get("video_opts", [])
                if "1080p" in preset['name']: vf.append("scale=1920:-2:flags=lanczos,format=p010le" if force_10bit else "scale=1920:-2:flags=lanczos")
                elif preset.get('type') == "gpu": vf.append("format=p010le")
            
            cmd += ["-map", "0:v:0"]
            cmd += preset["video_opts"]
            if vf: cmd += ["-vf", ",".join(vf)]
            cmd.append(str(out_file))
            
            t0 = time.time()
            if run_ffmpeg_piped(cmd, 45):
                t_elapsed = time.time() - t0
                fps_avg = (45 * 24) / t_elapsed
                
                if is_copy: vmaf, ssim = 100.0, 1.0
                else:
                    print(f"   {Colors.BLUE}⚙️ Calcolo metriche (VMAF/SSIM) - Attendere...{Colors.ENDC}")
                    ref_chain = "[1:v]"
                    if force_10bit: ref_chain += "format=yuv420p10le,"
                    if "1080p" in preset['name']: ref_chain += "scale=1920:-2:flags=lanczos,"
                    ref_chain = ref_chain.rstrip(",")
                    json_vmaf = out_file.with_suffix(".json")
                    
                    subprocess.run(["ffmpeg", "-flags2", "+ignorecrop", "-i", str(out_file), "-flags2", "+ignorecrop", "-i", str(ref_file), "-filter_complex", f"{ref_chain}[ref];[0:v][ref]libvmaf=model=version=vmaf_v0.6.1:n_subsample=10:log_fmt=json:log_path={json_vmaf}", "-f", "null", "-"], stderr=subprocess.DEVNULL)
                    vmaf = 0
                    if json_vmaf.exists():
                        try:
                            with open(json_vmaf, 'r') as f: vmaf = json.load(f).get("pooled_metrics", {}).get("vmaf", {}).get("mean", 0)
                        except: pass
                        os.remove(json_vmaf)
                    
                    p_ssim = subprocess.run(["ffmpeg", "-flags2", "+ignorecrop", "-i", str(out_file), "-flags2", "+ignorecrop", "-i", str(ref_file), "-filter_complex", f"{ref_chain}[ref];[0:v][ref]ssim", "-f", "null", "-"], stderr=subprocess.PIPE, text=True)
                    ssim = parse_ssim_output(p_ssim.stderr)

                size_gb = (out_file.stat().st_size / 45) * duration / (1024**3)
                audio_bitrate_str = preset.get('audio_bitrate', '320k')
                try: audio_kbps = int(audio_bitrate_str.replace('k', ''))
                except: audio_kbps = 320
                size_gb += (audio_kbps * duration) / 8 / 1024 / 1024
                
                results.append({"preset": preset, "name": preset['name'], "fps": fps_avg, "vmaf": vmaf, "ssim": ssim, "size_gb": size_gb})
                os.remove(out_file)

        if ref_file.exists(): os.remove(ref_file)

        print(f"\n{Colors.HEADER}=== RISULTATI BENCHMARK ==={Colors.ENDC}")
        results.sort(key=lambda x: x['vmaf'], reverse=True)
        for i, r in enumerate(results):
            rating, _, col = get_quality_verdict(r['vmaf'], "VMAF")
            print(f"[{i+1}] {r['name']:<32} | {col}{r['vmaf']:.1f}{Colors.ENDC} | {col}{rating}{Colors.ENDC} | {r['size_gb']:.1f} GB")
        
        print("\n[1] Ripeti | [2] Encode con Preset Vincente | [q] Esci")
        c = input("> ").strip()
        if c == '2':
             sel_p = input("Numero preset: "); idx = int(sel_p)-1
             wizard_result = wizard_new_jobs(direct_file=input_path, direct_preset=results[idx]['preset'])
             if wizard_result: mode_queue_manager(wizard_result)
             return
        if c == 'q': return

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
    if opt_crop == 's': force_no_crop = True

    crop_filter_chain = ""
    if not force_no_crop:
        ref_w, ref_h = get_resolution(ref_path)
        dist_w, dist_h = get_resolution(dist_path)
        if ref_w > 0 and dist_w > 0 and (ref_h > dist_h or ref_w > dist_w):
            print(f"{Colors.GREEN}→ Applico auto-crop al reference.{Colors.ENDC}")
            crop_w, crop_h = dist_w, dist_h
            crop_x, crop_y = (ref_w - dist_w) // 2, (ref_h - dist_h) // 2
            crop_filter_chain = f"[0:v]crop={crop_w}:{crop_h}:{crop_x}:{crop_y}[ref_cropped];"
    
    print("\n3. Scegli Metrica (q=Indietro): [1] VMAF [2] SSIM")
    metric_choice = input("> ").strip()
    if metric_choice.lower() == 'q': return

    output_report = Path(dist_path).parent / f"quality_log_{Path(dist_path).stem}.txt"
    json_report = Path(dist_path).parent / f"vmaf_report_{Path(dist_path).stem}.json"
    ref_label = "[0:v]"; dist_label = "[1:v]"
    if crop_filter_chain: ref_label = "[ref_cropped]"

    cmd = ["ffmpeg", "-i", ref_path, "-i", dist_path]
    
    if metric_choice == "1":
        model = "vmaf_v0.6.1"
        if input("Modello [1] 4K HDR [2] 1080p SDR: ").strip() == "1": model = "vmaf_4k_v0.6.1"
        cmd += ["-filter_complex", f"{crop_filter_chain}{dist_label}{ref_label}libvmaf=model=version={model}:n_subsample=10:log_fmt=json:log_path={json_report}", "-f", "null", "-"]
    elif metric_choice == "2":
        cmd += ["-filter_complex", f"{crop_filter_chain}{dist_label}{ref_label}ssim=stats_file={output_report}", "-f", "null", "-"]
    else: return

    print(f"\n{Colors.BLUE}🚀 Avvio analisi...{Colors.ENDC}")
    p = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    
    score = "N/A"
    if metric_choice == "1" and os.path.exists(json_report):
        with open(json_report, 'r') as jf: score = json.load(jf).get("pooled_metrics", {}).get("vmaf", {}).get("mean", "N/A")
    elif metric_choice == "2":
        score = parse_ssim_output(p.stderr)

    print(f"\n{Colors.BOLD}RISULTATO: {score}{Colors.ENDC}")

# ============================================================
# JOB CREATION WIZARD
# ============================================================
def wizard_new_jobs(direct_file=None, direct_preset=None):
    zscale_available = has_zscale()
    new_jobs = []
    
    if direct_preset:
        current_preset = direct_preset
        print(f"\n{Colors.CYAN}★ Preset selezionato: {current_preset['name']}{Colors.ENDC}")
    else:
        print("\nSeleziona preset (q=Indietro):")
        for pid, pdata in PRESETS.items(): print(f" [{pid}] {pdata['name']}")
        c = input("> ").strip().lower()
        if c == 'q': return []
        if c in PRESETS: current_preset = PRESETS[c]
        else: return []

    files = []
    if direct_file:
        files.append(direct_file)
    else:
        print("\nTrascina file o cartella (q=Indietro):")
        raw_path = input("> ").strip()
        if raw_path.lower() == 'q': return []
        input_path = Path(clean_input_path(raw_path))
        if input_path.is_file(): files.append(input_path)
        elif input_path.is_dir():
            for f in input_path.rglob("*"):
                if f.suffix.lower() in [".mkv", ".mp4", ".mov", ".avi"] and not f.name.startswith("._"):
                    files.append(f)
    
    if not files: print("Nessun file trovato."); return []
    files.sort()
    
    output_dir = Path.home() / "Movies"
    if not output_dir.exists(): output_dir.mkdir()

    for idx, f in enumerate(files):
        print(f"\n{Colors.WARNING}=== Configurazione {idx+1}/{len(files)}: {f.name} ==={Colors.ENDC}")
        info = get_file_info(f)
        if not info: continue
        
        duration = get_total_duration(info)
        streams = info.get("streams", [])
        hdr_found = is_hdr(streams)
        
        crop_filter = detect_black_bars(f, duration)
        is_video_copy = "-c:v" in current_preset["video_opts"] and "copy" in current_preset["video_opts"]
        
        if is_video_copy:
            crop_filter = None
            print(f"{Colors.BLUE}ℹ️ Remux Mode: Auto-Crop disabilitato.{Colors.ENDC}")
        else:
            if crop_filter:
                print(f"{Colors.GREEN}  → Crop rilevato: {crop_filter}{Colors.ENDC}")
                if input(f"  Confermi? [s/n] (Invio=Si): ").lower() == 'n':
                    m = input("  Crop manuale o Invio per NO: ").strip()
                    crop_filter = f"crop={m}" if m and not m.startswith("crop=") else (m if m else None)
            else:
                m = input("  Crop manuale o Invio per originale: ").strip()
                crop_filter = f"crop={m}" if m and not m.startswith("crop=") else (m if m else None)
            
        print("\nScegli Strategia Audio:")
        print(" [1] Passthrough (Copia 1:1)")
        print(f" [2] Smart Surround (EAC3 se necessario)")
        print(" [3] Stereo Saver (AAC 2.0)")
        a_choice = input("> ").strip()
        audio_mode = "copy"
        if a_choice == "2": audio_mode = "eac3"
        elif a_choice == "3": audio_mode = "aac"

        sel_audio = select_tracks(streams, "audio")
        if sel_audio is None: return []
        sel_subs = select_tracks(streams, "subtitle")
        if sel_subs is None: return []

        safe_preset_name = current_preset['name'].replace("/", "-").replace(":", "-")
        outfile = output_dir / f"{f.stem}_enc_{safe_preset_name}.mkv"
        
        new_jobs.append({
            "input": f, "output": outfile, "duration": duration,
            "hdr": hdr_found, "crop": crop_filter,
            "sel_audio": sel_audio, "sel_subs": sel_subs,
            "audio_mode": audio_mode,
            "preset": current_preset
        })
        
    return new_jobs

# ============================================================
# QUEUE MANAGER & EXECUTION
# ============================================================
def run_job_execution(jobs):
    zscale_available = has_zscale()
    total_in = 0
    total_out = 0
    
    for i, job in enumerate(jobs):
        print(f"\n{Colors.BOLD}Elaborazione {i+1}/{len(jobs)}: {job['input'].name}{Colors.ENDC}")
        current_preset = job['preset']
        is_video_copy = "-c:v" in current_preset["video_opts"] and "copy" in current_preset["video_opts"]
        
        cmd = ["ffmpeg", "-y", "-i", str(job['input'])]
        
        vf_chain = []
        if job['crop'] and not is_video_copy: vf_chain.append(job['crop'])
        
        if not is_video_copy:
            is_1080_sdr = "1080p" in current_preset['name']
            if is_1080_sdr:
                if job['hdr']:
                    if zscale_available: vf_chain.append("scale=1920:-2,zscale=t=bt709:p=bt709:m=bt709:r=tv,format=p010le")
                    else: vf_chain.append("scale=1920:-2:flags=lanczos,format=p010le")
                else: vf_chain.append("scale=1920:-2:flags=lanczos,format=p010le")
            elif current_preset.get('type') == "gpu":
                 vf_chain.append("format=p010le")

        cmd += ["-map", "0:v:0"]
        cmd += current_preset["video_opts"]
        if vf_chain: cmd += ["-vf", ",".join(vf_chain)]

        a_idx = 0
        for track in job['sel_audio']:
            cmd += ["-map", f"0:{track['index']}"]
            if job['audio_mode'] == "eac3":
                if track['codec'] in ['ac3', 'eac3']: cmd += [f"-c:a:{a_idx}", "copy"]
                elif track['channels'] <= 2: cmd += [f"-c:a:{a_idx}", "copy"]
                else: cmd += [f"-c:a:{a_idx}", "eac3", f"-b:a:{a_idx}", "640k"]
            elif job['audio_mode'] == "aac":
                cmd += [f"-c:a:{a_idx}", "aac", f"-b:a:{a_idx}", "256k", "-ac", "2"]
            else:
                if track['codec'] in current_preset["passthrough"]: cmd += [f"-c:a:{a_idx}", "copy"]
                else: cmd += [f"-c:a:{a_idx}", "ac3", f"-b:a:{a_idx}", current_preset["audio_bitrate"]]
            a_idx += 1
            
        for track in job['sel_subs']: cmd += ["-map", f"0:{track['index']}"]
        if job['sel_subs']: cmd += ["-c:s", "copy"]
            
        cmd.append(str(job['output']))
        
        if run_ffmpeg_piped(cmd, job['duration']):
            in_size = job['input'].stat().st_size
            total_in += in_size
            if Path(str(job['output'])).exists():
                out_size = Path(str(job['output'])).stat().st_size
                total_out += out_size
                ratio = (out_size / in_size) * 100
                diff = in_size - out_size
                
                print(f"{Colors.GREEN}✔ Completato.{Colors.ENDC}")
                print(f"  {Colors.CYAN}Orig: {format_size(in_size)} -> Enc: {format_size(out_size)} (Ratio: {ratio:.1f}%){Colors.ENDC}")
        
        if i < len(jobs) - 1:
            print("Pausa tecnica 5s..."); time.sleep(5); gc.collect()

    # Total Batch Summary
    if len(jobs) > 1 and total_in > 0:
        print(f"\n{Colors.HEADER}=== RIEPILOGO TOTALE BATCH ==={Colors.ENDC}")
        print(f"File processati:  {len(jobs)}")
        print(f"Spazio Originale: {format_size(total_in)}")
        print(f"Spazio Finale:    {format_size(total_out)}")
        saved = total_in - total_out
        pct = (saved / total_in) * 100
        print(f"Risparmio Totale: {format_size(saved)} ({pct:.1f}%)")

def mode_queue_manager(jobs=[]):
    if not jobs: print("La coda è vuota."); return

    while True:
        print(f"\n{Colors.HEADER}=== RIEPILOGO CODA ({len(jobs)} File) ==={Colors.ENDC}")
        for i, j in enumerate(jobs):
            print(f"{i+1}. {j['input'].name} -> {j['preset']['name']}")
            print(f"   Audio: {len(j['sel_audio'])} tracce | Mode: {j['audio_mode']}")
        print("-" * 40)
        print(f"{Colors.GREEN}[s] START (Avvia Lavori){Colors.ENDC}")
        print(f"{Colors.CYAN}[a] ADD FILES (Aggiungi file da zero){Colors.ENDC}")
        print(f"{Colors.BLUE}[m] MERGE QUEUE (Unisci altra coda JSON){Colors.ENDC}")
        print(f"{Colors.WARNING}[e] EXPORT (Salva coda su file){Colors.ENDC}")
        print("[q] ESCI (Torna al menu)")
        
        choice = input("> ").strip().lower()
        
        if choice == 's': run_job_execution(jobs); return
        elif choice == 'a':
            add_jobs = wizard_new_jobs()
            if add_jobs:
                jobs.extend(add_jobs)
                print(f"{Colors.GREEN}✔ Aggiunti {len(add_jobs)} nuovi lavori.{Colors.ENDC}")
        elif choice == 'm':
            print("Trascina il file JSON da unire:")
            jpath = input("> ").strip()
            new_jobs = parse_json_queue(jpath)
            if new_jobs:
                jobs.extend(new_jobs)
                print(f"{Colors.GREEN}✔ Unite {len(new_jobs)} voci alla coda.{Colors.ENDC}")
        elif choice == 'e': save_queue(jobs)
        elif choice == 'q': return
        else: print("Scelta non valida.")

def main():
    print(f"{Colors.BOLD}=== MEDIAENC – Ultimate Suite v9.2.4 (Batch Summary) ==={Colors.ENDC}")
    check_deps()
    while True:
        print("\nCosa vuoi fare?")
        print(f" {Colors.GREEN}[1] NUOVA CODA (Encode){Colors.ENDC}")
        print(f" {Colors.CYAN}[2] CHECK QUALITÀ (VMAF / SSIM){Colors.ENDC}")
        print(f" {Colors.WARNING}[3] TEST BENCHMARK (Confronta Preset){Colors.ENDC}")
        print(f" {Colors.BLUE}[4] IMPORTA CODA (Resume / Batch){Colors.ENDC}")
        print(f" [q] Esci")
        choice = input("> ").strip().lower()
        if choice == "1":
            jobs = wizard_new_jobs()
            if jobs: mode_queue_manager(jobs)
        elif choice == "2": mode_quality_check()
        elif choice == "3": mode_test_bench()
        elif choice == "4":
            jobs = load_queue()
            if jobs: mode_queue_manager(jobs)
        elif choice == "q": sys.exit(0)
        else: print("Scelta non valida.")

if __name__ == "__main__":
    main()
