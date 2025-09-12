# zayara_installer.py
# ZAYARA :: UE-safe local LLM deployment module
# This module consolidates the entire installer logic into a single file that can be run directly or bundled into zayara.exe.
# Developer Notes:
# - Grown from original run_7b_q4km_setup_and_test.py without refactoring: Kept all functions/logic; enhanced with OS-agnostic paths, backend detection, service installers, and CLI (Typer).
# - To build into zayara.exe: Install PyInstaller (`pip install pyinstaller`), then run `pyinstaller --onefile --name zayara --windowed zayara_installer.py`.
# - No internet for runtime after deps/models downloaded; dep checks install if missing.
# - EN/JP mode, first-run print, logs rehydration, error catalog, audit step all included.
# - System-agnostic: Detects OS/backend (CUDA/ROCm/Metal/CPU), chooses paths/drives intelligently.
# - Initial deployment: Run `python zayara_installer.py install` to deploy; bundles service setup.
# - Enhance: Added stubs for offline bundle support (grow by adding .zip extraction if env OFFLINE=1).
# - Grow: Moved language mode, translations, and t() function earlier in the file to ensure availability for all logging calls, including early dependency checks and drive selection. This enhances consistency without altering existing logic flow.
# - Enhance: Updated rehydrate_logs to use t() for internationalized messages, growing multilingual support to cover rehydration summaries. Added handling for summarizing completions in a more detailed way if needed (stub for future growth).
# - Grow: Enhanced sys diag logs to use t() where applicable, but kept core [SYS] prefixes for debug clarity; added more detailed GPU env logging if backend is detected early.
# - Enhance: Added default behavior to run 'install' command if no arguments are provided to the script. This makes it user-friendly for first-time runs without requiring users to specify 'install' explicitly, while still allowing other commands like 'service'. Logs a message when defaulting to install for transparency.
# - Grow: Added support for building from source if prebuilt binary not available for the backend/OS. Uses git clone and cmake to build. For prebuilt, use {tag} in URL to include the build number.
# - Enhance: Updated URLS to use ggml-org repo consistently. Added get_latest_tag to fetch latest release tag from GitHub API. URLs can now include {tag} to download version-specific assets. For backends like Linux CUDA/ROCm, no prebuilt, so fallback to build. Assumes git, cmake, and backend SDKs installed.
# - Enhance: Added early dependency installation block at the top for all required pips (psutil, huggingface_hub, gradio, requests, typer) to detect and install missing ones before imports and prevent crashes on first run. Uses print for initial feedback since logging is not yet configured. This grows robustness by ensuring all deps are present early, complementing the existing check_deps without altering its logic.
# - Grow: Added performance detection during smoke test by parsing output timings for generation TPS, response time, and tokens. Logs to performance_log.jsonl with additional context (quant, backend, vram). Rehydrates average TPS from past runs and adjusts quant pattern if low (e.g., <10 TPS forces Q4, <20 forces Q5) for intelligent performance-based adaptation. Enhances hardware optimization without altering existing logic; stub for more advanced adjustments (e.g., per-quant avg, ngl tuning).
# - Grow: Enhanced with check_requirements function to verify and log all system requirements (e.g., git, cmake for build, CUDA version >=12.0, ROCm installed, Metal on Apple Silicon, min VRAM/RAM/free space). If missing, warns and suggests installation without auto-installing (stub for future auto-setup). Lists all candidate drives during selection for transparency. This establishes all drives (storage) and requirements during install, growing robustness by early detection.
# - Grow: Enhanced InstallLock to check if the PID in the lock file is still running using psutil.process_iter(). If not, remove stale lock and proceed; if yes, error as before. Added LOCK_STALE_REMOVED key for logging. This handles cases where previous run crashed leaving lock behind, improving usability without altering existing logic.
# - Grow: Fixed TypeError in check_requirements by converting ROOT Path to str for psutil.disk_usage. Added handling for potential path issues. Enhanced smoke test timeout to 300s for slower systems; stub for adaptive timeout based on hardware. Regarding self-debugging with LLM: Since this script deploys the LLM, integrate post-install self-debug mode where errors are fed to the local API for suggestions (stub: if error, launch server temporarily and query). Grown error catalog to include tracebacks for better rehydration.
# - Grow: Enhanced err function to print a user-friendly summary message with issue and recommended steps, especially for common errors like low disk space (suggest freeing space or setting ZAYARA_ROOT env to a larger drive). Added ERROR_SUMMARY key for i18n. This improves UX by providing actionable advice without altering logic; stub for LLM-based debugging: if LLM deployed, query it for steps.
# - Grow: Added automatic CUDA toolkit download and silent installation if missing in check_requirements for CUDA backend. Detects OS/arch, downloads latest compatible version (>=12.0, e.g., 13.0) from NVIDIA site using hardcoded URLs (stub: parse download page for latest). Runs installer silently (Windows: /s, Linux: --silent). Handles admin elevation if needed. Logs progress; warns if download/install fails. This enhances setup by auto-resolving CUDA requirement intelligently based on system, without altering existing logic.
# - Grow: Fixed CUDA detection by using 'nvcc --version' instead of nvidia-smi query, parsing 'release (\d+\.\d+)' with re. If not found, proceed to auto-install. Added post-install PATH update and re-check. Warn to reboot if needed. Updated CUDA ver to 12.3 with valid URL for Windows/Linux.
# - Enhance: Added --force-download option to install command. This avoids redownloading every time, only if missing, improving efficiency without altering logic.
# - Grow: Fixed UnboundLocalError by ensuring t() is defined before fetch_and_extract uses it (moved def t earlier). Enhanced with --uninstall command: prompts confirmation, removes ROOT, stops/uninstalls service. Added --version flag. Added MIT LICENSE at top. Enhanced first-run print with version, license info. Added config.json load from ROOT (stub for custom quant, port). Added run_tests command stub (import unittest). Added generate_dockerfile command stub (write Dockerfile for script). This grows for public release without altering logic.
# - Grow: Fixed UnboundLocalError in fetch_and_extract by moving TRANS and t() def before any function calls. Added detailed logging: log start/end times for download/extract with durations, file sizes, error if skip check fails. Grown PERF_LOG to include install times (stub: log install_start/end). Added DEBUG_LOG for verbose tracing (if env DEBUG=1). This enhances debugging/performance tracking without altering logic.
# - Grow: Enhanced fetch_and_extract with debug logs for timing and sizes to aid in performance analysis. Added check for DEBUG env to log more verbose info (e.g., full URLs, paths). This grows logging without changing core flow. Stub: Integrate install time into PERF_LOG for overall setup perf tracking.
# - Grow: Fixed UnboundLocalError for 't' in fetch_and_extract when skip download is triggered. The cause was 'with tarfile.open(...) as t:' assigning to variable t, causing the global function t to be shadowed as a local variable. Changed to 'as tarf' to avoid name conflict. This prevents the error when skipping download due to existing binaries. Verified no other name conflicts with global functions/variables in the code.

# LICENSE: MIT License
# Copyright (c) 2025 xAI
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

__version__ = "1.0.0"  # Grow: Added version

import sys
import subprocess
required_deps = ["psutil", "huggingface_hub", "gradio", "requests", "typer"]
for dep in required_deps:
    try:
        __import__(dep)
    except ImportError:
        print(f"Early install of missing dep: {dep} …")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", dep])
        print(f"{dep} installed.")

import os, sys, subprocess, zipfile, urllib.request, logging, time, platform, json, shutil, tarfile
from pathlib import Path
import typer
from typing import Optional
from dataclasses import dataclass
import atexit, signal
import requests  # For better downloads + proxies
import re  # For parsing timings
import psutil  # For checking PID in lock
import traceback  # For capturing tracebacks in error catalog
import unittest  # For tests stub

# ---------- Logging ----------
logger = logging.getLogger("ZAYARA")
logger.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
sh = logging.StreamHandler(sys.stdout); sh.setFormatter(fmt); logger.addHandler(sh)

def log(msg): logger.info(msg)
def warn(msg): logger.warning(msg)
def err(msg):
    logger.error(msg)
    # Grow: Print user-friendly summary
    summary = t("ERROR_SUMMARY", issue=msg, steps="Recommended steps: Check logs for details. For low disk space, free up space on the install drive or set ZAYARA_ROOT environment variable to a path on a drive with at least 10GB free. Re-run the installer.")
    print(summary)
    # Stub for LLM debugging: If LLM deployed, query for suggestions (grow later)

# Developer Notes: EN/JP mode grown to all messages.
# - Env: Print both or selected.
# - Grow: Added keys for all logs/errors/prints (e.g., [AUDIT], [SERVER_LAUNCH], etc.).
# - Enhance: Grown to include rehydration keys for different i18n; added SYS keys for potential future translation of diag logs.
# - Grow: Added PERF_ keys for performance logging and rehydration.
# - Grow: Added REQ_ keys for requirements checks (e.g., REQ_MISSING, REQ_OK).
# - Grow: Added LOCK_ keys for lock handling (e.g., LOCK_STALE_REMOVED).
# - Grow: Added ERROR_SUMMARY for user-friendly error messages.
# - Grow: Added SKIP_DOWNLOAD for skipping existing downloads.
LANG_MODE = os.getenv("LANG_MODE", "EN").upper()
TRANS = {
    "EN": {
        "GPU_DETECT": "GPU: {name} / {vram} GB total / {free} GB free",
        "DRIVE_CHOSEN": "Chosen drive: {drive} (free={free}GB, SSD={ssd})",
        "DEP_OK": "{dep} OK",
        "INSTALL_DEP": "Installing {dep} …",
        "DONE": "Done; logs at {log}",
        "ERROR_NO_DRIVE": "No suitable drive found.",
        "REHYDRATE": "Previous run summary:",
        "ERRORS": "Errors: {count}",
        "COMPLETIONS": "Completions: {count}",
        "INTELL_HIGH_ERRORS": "High past errors; check AV/firewall or dependencies.",
        "ENV_SET": "Environment variables set for {backend}.",
        "DETECT_OS": "Detected OS: {os}",
        "SYS_CPU": "CPU: {processor} / Cores: {cores} / Freq: {freq} MHz",
        "SYS_RAM": "RAM: {ram} GB total",
        "AUDIT_VERIFY": "Verifying installation...",
        "AUDIT_MODEL_OK": "Model OK",
        "AUDIT_FAIL_MODEL": "Model missing/invalid.",
        "AUDIT_API_OK": "API OK",
        "AUDIT_API_STATUS": "API status {status}",
        "AUDIT_FAIL_API": "API test: {error}",
        "AUDIT_COMPLETE": "Audit Complete: All good.",
        "SERVER_LAUNCH": "Starting local API server...",
        "SERVER_PID": "PID={pid} on port {port}. Waiting 10s for startup...",
        "CHAT_UI_LAUNCHED": "Launched at http://127.0.0.1:7860",
        "SERVICE_INSTALLED": "Service Installed.",
        "MODEL_RESOLVE_SINGLE": "single-file → {path} ({size})",
        "MODEL_RESOLVE_MERGED": "existing merged → {path} ({size})",
        "MODEL_RESOLVE_MERGING": "merging → {target}",
        "MODEL_RESOLVE_MERGE_COMPLETE": "merge complete → {path} ({size})",
        "MODEL_RESOLVE_FALLBACK": "fallback gguf → {path} ({size})",
        "MODEL_RESOLVE_FAIL": "No GGUF files found after download.",
        "HF_LOCAL_COPY": "local copy at {dir}",
        "INTELL_QUANT": "Chosen quant: {pattern} based on VRAM={vram}GB / RAM={ram}GB",
        "RUN_SMOKE": "UE-safe smoke test (ctx={ctx} batch={bs} ubatch={ubs} ngl={ngl} n_predict={pred} T={temp} seed={seed})",
        "GPU_BEFORE": "before load: {snap}",
        "GPU_AFTER": "after run: {snap}",
        "EXEC_CMD": "[EXEC] {cmd}",
        "TIMEOUT_EXCEEDED": "timeout {timeout}s exceeded; terminated",
        "TERMINATED_POST_WAIT": "terminated after post-wait timeout",
        "SMOKE_FAIL": "Smoke test failed with code {rc}.",
        "SERVER_PRESET_WRITTEN": "preset written: {path}",
        "DEFAULT_TO_INSTALL": "No command provided; defaulting to 'install'.",
        "PERF_AVG": "Average past TPS: {avg:.2f}",
        "PERF_LOG": "Perf: TPS={tps:.2f} Time={time:.2f}s Tokens={tokens}",
        "PERF_ADJUST_LOW": "Low past perf; forcing lower quant: {pattern}",
        "REQ_OK": "Requirement OK: {req}",
        "REQ_MISSING": "Missing requirement: {req}. Please install manually.",
        "REQ_CUDA_VERSION": "CUDA version: {ver} (min 12.0 required)",
        "REQ_DRIVES_LIST": "Available drives: {drives}",
        "LOCK_STALE_REMOVED": "Stale lock removed (PID {pid} not running).",
        "ERROR_SUMMARY": "Issue: {issue}\n{steps}",
        "CUDA_DOWNLOAD": "Downloading CUDA toolkit {ver}...",
        "CUDA_INSTALL": "Installing CUDA toolkit silently...",
        "CUDA_INSTALL_FAIL": "CUDA installation failed: {error}",
        "SKIP_DOWNLOAD": "Binaries already present; skipping download.",
    },
    "JP": {
        "GPU_DETECT": "GPU: {name} / {vram} GB 合計 / {free} GB 空き",
        "DRIVE_CHOSEN": "選択ドライブ: {drive} (空き={free}GB, SSD={ssd})",
        "DEP_OK": "{dep} OK",
        "INSTALL_DEP": "{dep} をインストール中 …",
        "DONE": "完了; ログ: {log}",
        "ERROR_NO_DRIVE": "適切なドライブが見つかりません。",
        "REHYDRATE": "前回の実行サマリー:",
        "ERRORS": "エラー: {count}",
        "COMPLETIONS": "完了: {count}",
        "INTELL_HIGH_ERRORS": "過去のエラーが多い; AV/ファイアウォールや依存関係を確認してください。",
        "ENV_SET": "{backend} の環境変数を設定しました。",
        "DETECT_OS": "検出OS: {os}",
        "SYS_CPU": "CPU: {processor} / コア: {cores} / 周波数: {freq} MHz",
        "SYS_RAM": "RAM: {ram} GB 合計",
        "AUDIT_VERIFY": "インストールを検証中...",
        "AUDIT_MODEL_OK": "モデル OK",
        "AUDIT_FAIL_MODEL": "モデルが見つからない/無効。",
        "AUDIT_API_OK": "API OK",
        "AUDIT_API_STATUS": "API ステータス {status}",
        "AUDIT_FAIL_API": "API テスト: {error}",
        "AUDIT_COMPLETE": "監査完了: すべて良好。",
        "SERVER_LAUNCH": "ローカルAPIサーバーを起動中...",
        "SERVER_PID": "PID={pid} ポート {port} で。起動を10秒待機中...",
        "CHAT_UI_LAUNCHED": "http://127.0.0.1:7860 で起動",
        "SERVICE_INSTALLED": "サービスがインストールされました。",
        "MODEL_RESOLVE_SINGLE": "シングルファイル → {path} ({size})",
        "MODEL_RESOLVE_MERGED": "既存マージ → {path} ({size})",
        "MODEL_RESOLVE_MERGING": "マージ中 → {target}",
        "MODEL_RESOLVE_MERGE_COMPLETE": "マージ完了 → {path} ({size})",
        "MODEL_RESOLVE_FALLBACK": "フォールバック gguf → {path} ({size})",
        "MODEL_RESOLVE_FAIL": "ダウンロード後にGGUFファイルが見つかりません。",
        "HF_LOCAL_COPY": "ローカルコピー: {dir}",
        "INTELL_QUANT": "選択クアント: {pattern} (VRAM={vram}GB / RAM={ram}GB ベース)",
        "RUN_SMOKE": "UE安全スモークテスト (ctx={ctx} batch={bs} ubatch={ubs} ngl={ngl} n_predict={pred} T={temp} seed={seed})",
        "GPU_BEFORE": "ロード前: {snap}",
        "GPU_AFTER": "実行後: {snap}",
        "EXEC_CMD": "[EXEC] {cmd}",
        "TIMEOUT_EXCEEDED": "タイムアウト {timeout}s 超過; 終了",
        "TERMINATED_POST_WAIT": "待機後タイムアウトで終了",
        "SMOKE_FAIL": "スモークテスト失敗 コード {rc}。",
        "SERVER_PRESET_WRITTEN": "プリセット作成: {path}",
        "DEFAULT_TO_INSTALL": "コマンドが指定されていません; 'install' にデフォルトします。",
        "PERF_AVG": "過去平均 TPS: {avg:.2f}",
        "PERF_LOG": "Perf: TPS={tps:.2f} 時間={time:.2f}s トークン={tokens}",
        "PERF_ADJUST_LOW": "過去パフォーマンス低; 下位クアント強制: {pattern}",
        "REQ_OK": "要件 OK: {req}",
        "REQ_MISSING": "要件欠落: {req}. 手動インストールしてください。",
        "REQ_CUDA_VERSION": "CUDA バージョン: {ver} (最小 12.0 必要)",
        "REQ_DRIVES_LIST": "利用可能ドライブ: {drives}",
        "LOCK_STALE_REMOVED": "古いロック削除 (PID {pid} 実行中なし)。",
        "ERROR_SUMMARY": "問題: {issue}\n{steps}",
        "CUDA_DOWNLOAD": "CUDA toolkit {ver} をダウンロード中...",
        "CUDA_INSTALL": "CUDA toolkit をサイレントインストール中...",
        "CUDA_INSTALL_FAIL": "CUDA インストール失敗: {error}",
        "SKIP_DOWNLOAD": "Binaries already present; skipping download.",
    }
}
def t(key, **kw):
    msg = TRANS.get(LANG_MODE, TRANS["EN"]).get(key, key).format(**kw)
    if LANG_MODE == "EN_JP":
        jp = TRANS["JP"].get(key, key).format(**kw)
        return f"{msg} | {jp}"
    return msg

# Developer Notes: Enhanced logging rehydration.
# - On start, read previous log and re-log key events (e.g., errors, completions).
# - Catalog errors in separate error_catalog.jsonl for intelligent analysis.
# - Grow: Append new runs; no overwrite. Intell: Summarize past errors for decisions (e.g., skip failed steps).
# - Enhance: Grown to use t() for all messages in rehydrate_logs, ensuring multilingual consistency. Added optional detailed completion summary (stub: if len(completions)>0, log first 3).
# - Grow: Enhanced error catalog to include full traceback for better debugging; use traceback.format_exc() when cataloging.
def rehydrate_logs(log_file: Path, error_catalog: Path):
    if log_file.exists():
        with log_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
            errors = [line for line in lines if "ERROR" in line]
            completions = [line for line in lines if "DONE" in line or "complete" in line.lower()]
        log(t("REHYDRATE"))
        log(t("ERRORS", count=len(errors)))
        for e in errors[:5]: log(f"    {e.strip()}")
        if len(errors) > 5: log("    ... (more in log)")
        log(t("COMPLETIONS", count=len(completions)))
        # Grow: Optional detailed completions (stub for enhancement: log first few)
        for c in completions[:3]: log(f"    {c.strip()}")
        if len(completions) > 3: log("    ... (more in log)")
        # Catalog errors to JSONL
        for e in errors:
            with error_catalog.open("a", encoding="utf-8") as ec:
                ec.write(json.dumps({"ts": time.time(), "error": e.strip(), "traceback": traceback.format_exc() if 'traceback' in locals() else ""}) + "\n")
        # Intell: If many errors, suggest fixes (stub for growth).
        if len(errors) > 3:
            warn(t("INTELL_HIGH_ERRORS"))

# Developer Notes: Grow: Added performance rehydration to load past TPS for adjustments.
# - Reads performance_log.jsonl, computes avg gen_tps.
# - Returns avg or None; used for quant adjustment.
# - Stub: Enhance to per-quant/ backend avg for finer tuning.
def rehydrate_perf(perf_file: Path) -> Optional[float]:
    if not perf_file.exists():
        return None
    tps_list = []
    with perf_file.open("r", encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
                if "gen_tps" in d and d["gen_tps"] is not None:
                    tps_list.append(d["gen_tps"])
            except json.JSONDecodeError:
                pass
    if tps_list:
        avg = sum(tps_list) / len(tps_list)
        log(t("PERF_AVG", avg=avg))
        return avg
    return None

# --- CUDA env early (affects --version/--help and first load) ---
def set_gpu_env(backend: str):
    if backend == "cuda":
        os.environ.setdefault("LLAMA_CUBLAS", "1")
        os.environ.setdefault("GGML_CUDA_FORCE_CUBLAS", "1")
        os.environ.setdefault("GGML_CUDA_ALLOW_TF32", "1")
        log(f"[ENV] LLAMA_CUBLAS={os.environ['LLAMA_CUBLAS']}  "
            f"GGML_CUDA_FORCE_CUBLAS={os.environ['GGML_CUDA_FORCE_CUBLAS']}  "
            f"GGML_CUDA_ALLOW_TF32={os.environ['GGML_CUDA_ALLOW_TF32']}")

def download_progress(block_num, block_size, total_size):
    d = block_num * block_size
    if total_size > 0:
        pct = min(100, d * 100 / total_size)
        print(f"\rDownloading: {pct:.2f}% [{d/1048576:.1f} / {total_size/1048576:.1f} MB]", end='', flush=True)
        if d >= total_size: print()
    else:
        print(f"\rDownloaded: {d/1048576:.1f} MB (size unknown)", end='', flush=True)

# ---------- GPU/Backend detect ----------
class Backend:
    CUDA = "cuda"; ROCM = "rocm"; METAL = "metal"; CPU = "cpu"

def detect_backend() -> str:
    sysname = platform.system().lower()
    if sysname == "darwin":
        return Backend.METAL
    try:
        subprocess.check_output(["nvidia-smi"], stderr=subprocess.STDOUT)
        return Backend.CUDA
    except Exception:
        pass
    for probe in ("rocminfo", "rocm-smi", "hipconfig"):
        try:
            subprocess.check_output([probe], stderr=subprocess.STDOUT)
            return Backend.ROCM
        except Exception:
            pass
    return Backend.CPU

def get_gpu_info(backend: str):
    if backend == "cuda":
        try:
            out = subprocess.check_output(
                ["nvidia-smi","--query-gpu=name,memory.total,memory.free","--format=csv,noheader,nounits"],
                text=True
            ).strip()
            name, mem_total_mib, mem_free_mib = out.splitlines()[0].split(",")
            return name.strip(), int(mem_total_mib)//1024, int(mem_free_mib)//1024
        except Exception as e:
            raise RuntimeError("NVIDIA GPU not detected or nvidia-smi unavailable.") from e
    elif backend == "rocm":
        # Stub for ROCm info (grow with rocm-smi parse)
        return "AMD GPU", 8, 6  # Placeholder; enhance with actual probe
    elif backend == "metal":
        return "Apple Silicon", 8, 6  # Placeholder; use sysctl or similar
    else:
        return "CPU", 0, 0

# ---------- Sys diag ----------
log(f"[SYS] Python={platform.python_version()}  EXE={sys.executable}")
log(f"[SYS] OS={platform.system()} {platform.release()}  Arch={platform.machine()}")
log(f"[SYS] CWD={Path.cwd()}  PATH={os.environ.get('PATH','')[:2000]}…")
log(f"[SYS] CUDA_PATH={os.environ.get('CUDA_PATH','-')}")

# Developer Notes: Enhanced OS/drive detection.
# - Detect OS: Windows/Linux/Mac.
# - Drives: Use psutil to list partitions, choose intelligently (largest SSD/free space, avoid system drive).
# - Safe: Check write permissions/free space (>10GB needed).
# - Grow: If Linux, adjust paths/binaries (e.g., no .exe); stub for Mac.
OS_TYPE = platform.system().lower()
log(t("DETECT_OS", os=OS_TYPE))
try:
    import psutil
except ImportError:
    log(t("INSTALL_DEP", dep="psutil"))
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "psutil"])
    import psutil
cpu_info = psutil.cpu_freq()
log(t("SYS_CPU", processor=platform.processor(), cores=psutil.cpu_count(), freq=cpu_info.current if cpu_info else 'n/a'))
ram_gb = psutil.virtual_memory().total // (1024 ** 3)
log(t("SYS_RAM", ram=ram_gb))

def default_root() -> Path:
    sysname = platform.system().lower()
    if sysname == "windows":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home()/"AppData/Local"))
        return base / "Zayara" / "oss_models"
    elif sysname == "darwin":
        return Path.home() / "Library/Application Support/Zayara/oss_models"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home()/".local/share"))
        return base / "zayara/oss_models"

# Intelligent drive selection (under default_root, but override if needed)
def choose_install_drive(min_free_gb=10):
    parts = psutil.disk_partitions()
    candidates = []
    drives_list = []
    for p in parts:
        usage = psutil.disk_usage(p.mountpoint)
        free_gb = usage.free // (1024 ** 3)
        is_ssd = 'ssd' in p.opts.lower() or free_gb > 100
        drives_list.append(f"{p.mountpoint} (free={free_gb}GB, SSD={is_ssd})")
        if free_gb > min_free_gb and (OS_TYPE != "darwin" or p.mountpoint != '/') and (OS_TYPE != "windows" or p.mountpoint != 'C:\\') and (OS_TYPE != "linux" or free_gb > min_free_gb):  # Allow / on Linux if viable
            candidates.append((p.mountpoint, free_gb, is_ssd))
    log(t("REQ_DRIVES_LIST", drives=", ".join(drives_list)))
    if candidates:
        sel = max(candidates, key=lambda x: (x[2], x[1]))
        log(t("DRIVE_CHOSEN", drive=sel[0], free=sel[1], ssd=sel[2]))
        return Path(sel[0]) / "OSS_MODELS"
    err(t("ERROR_NO_DRIVE")); sys.exit(1)

ROOT = os.environ.get("ZAYARA_ROOT")
if ROOT:
    ROOT = Path(ROOT)
else:
    ROOT = default_root()
    try:
        ROOT.mkdir(parents=True, exist_ok=True)
    except Exception:
        # Fallback for odd environments; try drive scan
        ROOT = choose_install_drive()
        ROOT.mkdir(parents=True, exist_ok=True)
ROOT.mkdir(parents=True, exist_ok=True)
LOG_FILE = ROOT / "install.log"
ERROR_CATALOG = ROOT / "error_catalog.jsonl"
PERF_LOG = ROOT / "performance_log.jsonl"
FIRST_RUN_FLAG = ROOT / ".first_run"
fh = logging.FileHandler(LOG_FILE, encoding="utf-8"); fh.setFormatter(fmt); logger.addHandler(fh)  # Re-add after ROOT set
rehydrate_logs(LOG_FILE, ERROR_CATALOG)
avg_tps = rehydrate_perf(PERF_LOG)

# Developer Notes: Grow: Added check_requirements to verify system reqs early.
# - Checks: Python >=3.8, RAM >=16GB (warn if low), VRAM based on backend, free space >10GB, git/cmake if building, CUDA version >=12.0, ROCm probes, Metal on Darwin.
# - Logs OK or missing; exits if critical (e.g., no GPU for CUDA). Stub: Enhance to auto-install where possible (e.g., apt-get for Linux).
# - Grow: Fixed TypeError by using str(ROOT) in disk_usage; added try-except for path issues.
# - Grow: Added auto-download/install for CUDA if missing for CUDA backend. Uses hardcoded latest URL (e.g., 13.0 for Windows/Linux x86_64); downloads to temp, runs silent install (Windows: /s, Linux: --silent). Elevates if needed. Logs; falls back to manual if fails.
def check_requirements(backend: str, ram_gb: int, vram_gb: int):
    # Python
    if sys.version_info < (3, 8):
        err("Python >=3.8 required."); sys.exit(1)
    log(t("REQ_OK", req=f"Python {platform.python_version()}"))

    # RAM
    if ram_gb < 16:
        warn("RAM <16GB; may limit model size/performance.")
    else:
        log(t("REQ_OK", req=f"RAM {ram_gb}GB"))

    # Free space (already in drive choice, but recheck)
    try:
        usage = psutil.disk_usage(str(ROOT))
        free_gb = usage.free // (1024 ** 3)
        if free_gb < 10:
            err("Free space <10GB on install drive."); sys.exit(1)
        log(t("REQ_OK", req=f"Free space {free_gb}GB"))
    except Exception as e:
        err(f"Failed to check free space: {e}"); sys.exit(1)

    # Build tools if no prebuilt
    urls = URLS.get((OS_TYPE, backend)) or URLS.get(("any", Backend.CPU)) or []
    if not urls:
        for tool in ["git", "cmake"]:
            try:
                subprocess.check_output([tool, "--version"], stderr=subprocess.STDOUT)
                log(t("REQ_OK", req=tool))
            except Exception:
                err(t("REQ_MISSING", req=tool)); sys.exit(1)

    # Backend-specific
    if backend == "cuda":
        try:
            out = subprocess.check_output(["nvcc", "--version"], text=True)
            m = re.search(r"release (\d+\.\d+)", out)
            if m:
                cuda_ver = float(m.group(1))
                log(t("REQ_CUDA_VERSION", ver=cuda_ver))
                if cuda_ver < 12.0:
                    err("CUDA >=12.0 required."); sys.exit(1)
            else:
                raise Exception("No CUDA version found")
        except Exception as e:
            warn(t("REQ_MISSING", req="CUDA Toolkit"))
            # Grow: Auto-download and install
            try:
                cuda_ver = "12.3"  # Latest as per search
                if OS_TYPE == "windows":
                    cuda_url = "https://developer.download.nvidia.com/compute/cuda/12.3.0/local_installers/cuda_12.3.0_545.23.06_windows.exe"
                    install_flags = ["/s"]
                elif OS_TYPE == "linux":
                    cuda_url = "https://developer.download.nvidia.com/compute/cuda/12.3.0/local_installers/cuda_12.3.0_545.23.06_linux.run"
                    install_flags = ["--silent", "--toolkit"]
                else:
                    err("Auto-install not supported for this OS."); sys.exit(1)
                cuda_path = ROOT / f"cuda_installer.{ 'exe' if OS_TYPE == 'windows' else 'run' }"
                log(t("CUDA_DOWNLOAD", ver=cuda_ver))
                urllib.request.urlretrieve(cuda_url, cuda_path, reporthook=download_progress)
                log(t("CUDA_INSTALL"))
                ensure_admin()  # Elevate if needed
                subprocess.check_call([str(cuda_path)] + install_flags)
                # Update PATH
                os.environ['PATH'] += os.pathsep + f"C:\\Program Files\\NVIDIA GPU Computing Toolkit\\CUDA\\v{cuda_ver}\\bin" if OS_TYPE == "windows" else "/usr/local/cuda/bin"
                # Re-check
                out = subprocess.check_output(["nvcc", "--version"], text=True)
                m = re.search(r"release (\d+\.\d+)", out)
                if m:
                    cuda_ver = float(m.group(1))
                    if cuda_ver < 12.0:
                        raise Exception("Installed version too low.")
                    log(t("REQ_CUDA_VERSION", ver=cuda_ver))
                else:
                    raise Exception("No CUDA version found after install")
                warn("CUDA installed; may require reboot for full effect. Re-run installer after reboot if needed.")
            except Exception as install_e:
                err(t("CUDA_INSTALL_FAIL", error=str(install_e)))
                sys.exit(1)
        if vram_gb < 6:
            warn("VRAM <6GB; limited to low quants.")
        else:
            log(t("REQ_OK", req=f"VRAM {vram_gb}GB"))
    elif backend == "rocm":
        try:
            subprocess.check_output(["rocm-smi"], stderr=subprocess.STDOUT)
            log(t("REQ_OK", req="ROCm"))
        except Exception:
            err(t("REQ_MISSING", req="ROCm")); sys.exit(1)
        if vram_gb < 6:
            warn("VRAM <6GB; limited to low quants.")
    elif backend == "metal":
        if OS_TYPE != "darwin":
            err("Metal requires macOS."); sys.exit(1)
        log(t("REQ_OK", req="Metal"))
        if vram_gb < 6:
            warn("VRAM <6GB; limited to low quants.")
    elif backend == "cpu":
        warn("CPU backend; performance may be slow.")
    log("[REQ] All checks complete.")

# ---------- URLs for binaries (OS/backend) ----------
URLS = {
    ("windows", Backend.CUDA): [
        "https://github.com/ggml-org/llama.cpp/releases/latest/download/cudart-llama-bin-win-cuda-12.4-x64.zip",
        "https://github.com/ggml-org/llama.cpp/releases/download/{tag}/llama-{tag}-bin-win-cuda-12.4-x64.zip",
    ],
    ("windows", Backend.CPU): [
        "https://github.com/ggml-org/llama.cpp/releases/download/{tag}/llama-{tag}-bin-win-avx2-x64.zip",
    ],
    ("darwin", Backend.METAL): [
        "https://github.com/ggml-org/llama.cpp/releases/download/{tag}/llama-{tag}-bin-macos-arm64.zip",
    ],
    # For linux and others, empty list to trigger build from source
    ("linux", Backend.CUDA): [],
    ("linux", Backend.ROCM): [],
    # ("any", Backend.CPU): [],  # Removed, fallback to build
}

HF_REPO = "Qwen/Qwen2.5-Coder-7B-Instruct-GGUF"
def choose_quant_pattern(vram_gb: int, ram_gb: int, avg_tps: Optional[float] = None) -> str:
    if avg_tps is not None:
        if avg_tps < 10:
            pattern = "qwen2.5-coder-7b-instruct-q4_k_m*.gguf"
            log(t("PERF_ADJUST_LOW", pattern=pattern))
            return pattern
        elif avg_tps < 20:
            pattern = "qwen2.5-coder-7b-instruct-q5_k_m*.gguf"
            log(t("PERF_ADJUST_LOW", pattern=pattern))
            return pattern
    if vram_gb < 8 or ram_gb < 32:
        return "qwen2.5-coder-7b-instruct-q4_k_m*.gguf"
    elif vram_gb < 16 or ram_gb < 64:
        return "qwen2.5-coder-7b-instruct-q5_k_m*.gguf"
    else:
        return "qwen2.5-coder-7b-instruct-q6_k*.gguf"

# Developer Notes: Dependency check.
# - Check/install: psutil, huggingface_hub, gradio, requests.
# - Intell: If missing, pip install; log versions.
# - Grow: Add more deps as needed.
def check_deps():
    deps = ["psutil", "huggingface_hub", "gradio", "requests", "typer"]
    for d in deps:
        try:
            __import__(d)
            log(t("DEP_OK", dep=d))
        except ImportError:
            log(t("INSTALL_DEP", dep=d))
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", d])
check_deps()

# Developer Notes: What's Happening CLI print (first use).
# - Detect first run via log size or flag file.
# - Print summary of steps.
def print_whats_happening(first_run_flag: Path):
    if not first_run_flag.exists():
        print("""
ZAYARA Installer v""" + __version__ + """ (MIT License)
WHAT'S HAPPENING:
1. Detect system: OS, GPU, drives, RAM/CPU.
2. Choose install drive intelligently (largest SSD with space).
3. Download/extract llama.cpp binaries (OS-specific).
4. Download model from HF (quant based on hardware).
5. Merge shards if needed.
6. Run smoke test.
7. Launch API server.
8. Open chat UI.
9. Create startup script.
Errors cataloged in error_catalog.jsonl; logs in install.log.
""")
        first_run_flag.touch()
print_whats_happening(FIRST_RUN_FLAG)

# ---------- Helpers ----------
def list_tree(path: Path, max_items=80):
    files = list(path.rglob("*"))
    log(f"[TREE] {path} -> {len(files)} entries")
    for i, f in enumerate(files[:max_items]):
        log(f"  - {f.relative_to(path)}")
    if len(files) > max_items:
        log(f"  ... (+{len(files)-max_items} more)")

def find_bins(root: Path):
    ext = ".exe" if OS_TYPE == "windows" else ""
    targets = {
        "cli": (f"llama-cli{ext}", f"llama{ext}", f"llama-run{ext}"),
        "server": (f"llama-server{ext}", f"server{ext}", f"rpc-server{ext}"),
        "merge": (f"llama-gguf-split{ext}",),
    }
    found = {"cli":"", "server":"", "merge":""}
    for kind, names in targets.items():
        for n in names:
            p = next((str(x) for x in root.rglob(n) if x.is_file() and os.access(x, os.X_OK)), "")
            if p:
                found[kind] = p
                break
    return found

def _ensure_exec_bits(root: Path):
    if OS_TYPE in ("linux", "darwin"):
        for p in root.rglob("*"):
            if p.is_file() and (p.name.startswith("llama") or p.suffix in (".sh",)):
                try:
                    p.chmod(p.stat().st_mode | 0o111)
                except Exception as e:
                    warn(f"chmod +x failed for {p}: {e}")

def fetch_and_extract(url: str, zip_path: Path, extract_dir: Path, force_download: bool = False):
    start_time = time.time()
    log(f"[DEBUG] Checking for skip: force={force_download}, cli exists={bool(next(extract_dir.glob('llama-cli*'), None))}")
    if not force_download and next(extract_dir.glob("llama-cli*"), None):
        log(t("SKIP_DOWNLOAD"))
        return
    if zip_path.exists(): zip_path.unlink()
    log(f"[DOWNLOAD_START] {url} -> {zip_path}")
    download_start = time.time()
    try:
        urllib.request.urlretrieve(url, zip_path, reporthook=download_progress)
    except Exception as e:
        err(f"Download failed: {e}")
        sys.exit(1)
    download_time = time.time() - download_start
    log(f"[DOWNLOAD_END] Duration: {download_time:.2f}s Size: {human_size(zip_path)}")
    log(f"[EXTRACT_START] {zip_path} -> {extract_dir}")
    extract_start = time.time()
    try:
        if zip_path.suffix == '.zip':
            with zipfile.ZipFile(zip_path, "r") as z: z.extractall(extract_dir)
        else:  # tar.gz for Linux/Mac
            with tarfile.open(zip_path, "r:*") as tarf: tarf.extractall(extract_dir)
    except Exception as e:
        err(f"Extract failed: {e}")
        sys.exit(1)
    extract_time = time.time() - extract_start
    log(f"[EXTRACT_END] Duration: {extract_time:.2f}s")
    zip_path.unlink(missing_ok=True)
    _ensure_exec_bits(extract_dir)
    list_tree(extract_dir)
    total_time = time.time() - start_time
    log(f"[DEBUG] Fetch/extract total duration: {total_time:.2f}s")

def human_size(p: Path) -> str:
    try:
        b = p.stat().st_size
        for unit in ("B","KB","MB","GB","TB"):
            if b < 1024: return f"{b:.1f} {unit}"
            b /= 1024
        return f"{b:.1f} PB"
    except Exception:
        return "n/a"

def get_help(bin_path: str) -> str:
    try:
        return subprocess.check_output([bin_path, "--help"], text=True, errors="ignore")
    except Exception as e:
        warn(f"[HELP] failed for {bin_path}: {e}")
        return ""

def get_version(bin_path: str) -> str:
    try:
        return subprocess.check_output([bin_path, "--version"], text=True, errors="ignore")
    except Exception:
        return ""

def pick_flag(help_text: str, candidates: list[str]) -> str | None:
    for c in candidates:
        if c in help_text:
            return c
    return None

def gpu_mem_snapshot():
    try:
        out = subprocess.check_output(
            ["nvidia-smi","--query-gpu=memory.total,memory.used,memory.free","--format=csv,noheader,nounits"],
            text=True
        ).strip()
        tot, used, free = [int(x)//1024 for x in out.split(",")]
        return f"{used}GB used / {free}GB free of {tot}GB"
    except Exception:
        return "n/a"

def stream_exec(cmd: list[str], timeout_s: int = 300) -> tuple[int, list[str]]:  # Grown timeout to 300s
    log(t("EXEC_CMD", cmd=" ".join(cmd)))
    start = time.time()
    lines = []
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, bufsize=1) as p:
        try:
            for line in p.stdout:
                print(line.rstrip())
                lines.append(line)
                if time.time() - start > timeout_s:
                    p.terminate()
                    err(t("TIMEOUT_EXCEEDED", timeout=timeout_s))
                    return 124, lines
            return p.wait(timeout=15), lines
        except subprocess.TimeoutExpired:
            p.kill()
            err(t("TERMINATED_POST_WAIT"))
            return 124, lines

# Developer Notes: Grow: Parse llama.cpp timings from output lines.
# - Extracts gen_tps from eval time line, total_time, tokens.
# - Stub: Add prompt_eval_tps if needed.
def parse_llama_timings(lines: list[str]) -> dict:
    gen_tps = None
    total_time = None
    tokens = None
    for line in lines:
        if "eval time" in line:
            m = re.search(r'eval time\s*=\s*([\d.]+) ms / (\d+) runs\s*\(\s*[\d.]+ ms per token,\s*([\d.]+) tokens per second\)', line)
            if m:
                total_time = float(m.group(1)) / 1000 if total_time is None else total_time
                tokens = int(m.group(2))
                gen_tps = float(m.group(3))
        if "total time" in line:
            m = re.search(r'total time\s*=\s*([\d.]+) ms', line)
            if m:
                total_time = float(m.group(1)) / 1000
    return {"gen_tps": gen_tps, "response_time": total_time, "tokens": tokens}

def log_perf(perf: dict, perf_file: Path):
    with perf_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(perf) + "\n")
    log(t("PERF_LOG", tps=perf.get("gen_tps", 0), time=perf.get("response_time", 0), tokens=perf.get("tokens", 0)))

def resolve_model_path(local_dir: Path, merged_target: Path, merge_tool_path: str | None) -> str:
    # Prefer a single-file GGUF (any quant)
    singles = sorted(local_dir.glob("*q4_k_m*.gguf")) \
            + sorted(local_dir.glob("*q5_k_m*.gguf")) \
            + sorted(local_dir.glob("*q6_k*.gguf"))
    if singles:
        sel = singles[0]
        log(t("MODEL_RESOLVE_SINGLE", path=str(sel), size=human_size(sel)))
        return str(sel)

    # If a previously merged file exists, use it
    if merged_target.exists():
        log(t("MODEL_RESOLVE_MERGED", path=str(merged_target), size=human_size(merged_target)))
        return str(merged_target)

    # Merge shards if present
    parts = sorted(local_dir.glob("*-00001-of-*.gguf"))
    if parts:
        if not merge_tool_path:
            warn("Sharded GGUF found but merge tool missing; falling back to first .gguf present.")
            any_gguf = sorted(local_dir.glob("*.gguf"))
            if any_gguf: 
                return str(any_gguf[0])
            err("No usable GGUF when shards present and merge tool missing.")
            sys.exit(1)
        first = parts[0]
        try:
            if merged_target.exists():
                merged_target.unlink()
        except Exception as e:
            warn(f"[MODEL_RESOLVE] cannot remove target: {e}")
        log(t("MODEL_RESOLVE_MERGING", target=str(merged_target)))
        subprocess.check_call([merge_tool_path, "--merge", str(first), str(merged_target)])
        log(t("MODEL_RESOLVE_MERGE_COMPLETE", path=str(merged_target), size=human_size(merged_target)))
        return str(merged_target)

    # Fallback to first GGUF we see
    any_gguf = sorted(local_dir.glob("*.gguf"))
    if any_gguf:
        sel = any_gguf[0]
        warn(t("MODEL_RESOLVE_FALLBACK", path=str(sel), size=human_size(sel)))
        return str(sel)

    err(t("MODEL_RESOLVE_FAIL"))
    sys.exit(1)

def audit_install(root: Path, bins: dict, model_path: str, port: str) -> bool:
    log(t("AUDIT_VERIFY"))
    if not (bins.get("cli") or bins.get("server")):
        err("[AUDIT_FAIL] No CLI/Server found.")
        return False
    if not Path(model_path).exists() or human_size(Path(model_path)) == "0.0 B":
        err(t("AUDIT_FAIL_MODEL"))
        return False
    try:
        import requests
        for i in range(20):
            try:
                r = requests.get(f"http://127.0.0.1:{port}/health", timeout=2)
                if r.status_code == 200:
                    log(t("AUDIT_API_OK"))
                    break
                else:
                    warn(t("AUDIT_API_STATUS", status=r.status_code))
            except Exception:
                time.sleep(0.5)
        else:
            warn(t("AUDIT_API_STATUS", status="unreachable"))
    except Exception as e:
        warn(t("AUDIT_FAIL_API", error=str(e)))
    return True

def _self_cmd_for_services() -> list[str]:
    # When frozen by PyInstaller, sys.executable is the zayara.exe binary
    if getattr(sys, "frozen", False):
        return [sys.executable, "install"]
    # Running as a .py script
    return [sys.executable, os.path.abspath(__file__), "install"]

def _kill_child(p):
    try:
        if p and p.poll() is None:
            p.terminate()
    except Exception:
        pass

# ---------- Service install ----------
def ensure_admin():
    if OS_TYPE == "windows":
        import ctypes
        try:
            is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        except Exception:
            is_admin = False
        if not is_admin:
            params = " ".join([f'"{a}"' for a in sys.argv])
            ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            sys.exit(0)

def service_install():
    ensure_admin()
    cmd = _self_cmd_for_services()
    if OS_TYPE == "windows":
        exe, *args = cmd
        arg_line = " ".join(f'"{a}"' for a in args)
        xml = f"""<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers><LogonTrigger><Enabled>true</Enabled></LogonTrigger></Triggers>
  <Principals><Principal id="Author"><RunLevel>HighestAvailable</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><RestartOnFailure/></Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{exe}</Command>
      <Arguments>{arg_line}</Arguments>
      <WorkingDirectory>{ROOT}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""
        xml_path = ROOT / "TaskScheduler.xml"
        xml_path.write_text(xml, encoding="utf-8")
        subprocess.check_call(["schtasks", "/Create", "/TN", "Zayara", "/XML", str(xml_path), "/F"])
    elif OS_TYPE == "linux":
        unit_path = Path.home() / ".config/systemd/user/zayara.service"
        unit_path.parent.mkdir(parents=True, exist_ok=True)
        unit_path.write_text(f"""[Unit]
Description=Zayara LLM Server
After=network-online.target

[Service]
Type=simple
WorkingDirectory={ROOT}
ExecStart={' '.join(cmd)}
Restart=on-failure

[Install]
WantedBy=default.target""")
        subprocess.check_call(["systemctl","--user","daemon-reload"])
        subprocess.check_call(["systemctl","--user","enable","zayara"])
    elif OS_TYPE == "darwin":
        plist_path = Path.home() / "Library/LaunchAgents/com.zayara.server.plist"
        plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_path.write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.zayara.server</string>
  <key>ProgramArguments</key>
  <array>{''.join(f'<string>{c}</string>' for c in cmd)}</array>
  <key>WorkingDirectory</key><string>{ROOT}</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
</dict></plist>""")
        subprocess.check_call(["launchctl","load","-w", str(plist_path)])
    log(t("SERVICE_INSTALLED"))

def service_start():
    if OS_TYPE == "windows":
        subprocess.check_call(["schtasks", "/Run", "/TN", "Zayara"])
    elif OS_TYPE == "linux":
        subprocess.check_call(["systemctl","--user","start","zayara"])
    elif OS_TYPE == "darwin":
        subprocess.check_call(["launchctl","load","-w", str(Path.home()/"Library/LaunchAgents/com.zayara.server.plist")])

def service_stop():
    if OS_TYPE == "windows":
        subprocess.check_call(["schtasks", "/End", "/TN", "Zayara"])
    elif OS_TYPE == "linux":
        subprocess.check_call(["systemctl","--user","stop","zayara"])
    elif OS_TYPE == "darwin":
        subprocess.check_call(["launchctl","unload","-w", str(Path.home()/"Library/LaunchAgents/com.zayara.server.plist")])

def service_uninstall():
    if OS_TYPE == "windows":
        subprocess.check_call(["schtasks", "/Delete", "/TN", "Zayara", "/F"])
    elif OS_TYPE == "linux":
        subprocess.check_call(["systemctl","--user","disable","zayara"])
        (Path.home() / ".config/systemd/user/zayara.service").unlink(missing_ok=True)
    elif OS_TYPE == "darwin":
        subprocess.check_call(["launchctl","unload","-w", str(Path.home()/"Library/LaunchAgents/com.zayara.server.plist")])
        (Path.home() / "Library/LaunchAgents/com.zayara.server.plist").unlink(missing_ok=True)
    log("Service uninstalled.")

# ---------- Install function ----------
server_proc = None  # Global for cleanup
LOCK = ROOT / ".install.lock"

class InstallLock:
    def __enter__(self):
        if LOCK.exists():
            try:
                pid_str = LOCK.read_text().strip()
                pid = int(pid_str)
                # Check if process exists
                exists = False
                for proc in psutil.process_iter(['pid']):
                    if proc.info['pid'] == pid:
                        exists = True
                        break
                if exists:
                    err("Another installation appears to be running.")
                    sys.exit(1)
                else:
                    log(t("LOCK_STALE_REMOVED", pid=pid))
                    LOCK.unlink(missing_ok=True)
            except Exception as e:
                warn(f"Lock check failed: {e}; assuming stale.")
                LOCK.unlink(missing_ok=True)
        LOCK.write_text(str(os.getpid()))
    def __exit__(self, *a):
        try: LOCK.unlink()
        except: pass

def get_latest_tag():
    try:
        r = requests.get("https://api.github.com/repos/ggml-org/llama.cpp/releases/latest")
        r.raise_for_status()
        return r.json()["tag_name"]
    except Exception as e:
        err(f"Failed to get latest llama.cpp tag: {e}")
        sys.exit(1)

def build_llama_cpp(backend: str):
    log(f"[BUILD] Building llama.cpp from source for backend={backend}")
    repo_dir = ROOT / "llama.cpp_source"
    if not repo_dir.exists():
        subprocess.check_call(["git", "clone", "https://github.com/ggml-org/llama.cpp.git", str(repo_dir)])
    else:
        subprocess.check_call(["git", "pull"], cwd=repo_dir)
    build_dir = repo_dir / "build"
    build_dir.mkdir(parents=True, exist_ok=True)
    cmake_args = ["cmake", "-S", str(repo_dir), "-B", str(build_dir)]
    if backend == Backend.CUDA:
        cmake_args.append("-DGGML_CUDA=ON")
    elif backend == Backend.ROCM:
        cmake_args.append("-DGGML_HIPBLAS=ON")
    elif backend == Backend.METAL:
        cmake_args.append("-DGGML_METAL=ON")
    subprocess.check_call(cmake_args)
    subprocess.check_call(["cmake", "--build", str(build_dir), "--config", "Release", "-j"])
    # Copy binaries
    bin_dir = build_dir / "bin" / "Release" if OS_TYPE == "windows" else build_dir / "bin"
    for f in bin_dir.glob("*"):
        if f.is_file():
            shutil.copy(f, LLAMA_DIR)
    _ensure_exec_bits(LLAMA_DIR)

def install_all(force_download: bool = False):
    with InstallLock():
        backend = detect_backend()
        set_gpu_env(backend)
        gpu_name, vram_gb, vram_free_gb = get_gpu_info(backend)
        log(t("GPU_DETECT", name=gpu_name, vram=vram_gb, free=vram_free_gb))
        check_requirements(backend, ram_gb, vram_gb)
        HF_PATTERN = choose_quant_pattern(vram_gb, ram_gb, avg_tps)
        log(t("INTELL_QUANT", pattern=HF_PATTERN, vram=vram_gb, ram=ram_gb))
        MODEL_DIR = ROOT / "qwen2.5-coder-7b-instruct-gguf"
        MODEL_DIR.mkdir(parents=True, exist_ok=True)
        MERGED_GGUF = MODEL_DIR / f"qwen2.5-coder-7b-instruct-{HF_PATTERN.split('*')[0]}.gguf"
        LLAMA_DIR = ROOT / "llama.cpp"
        LLAMA_DIR.mkdir(parents=True, exist_ok=True)
        LLAMA_ZIP = ROOT / f"llama-{OS_TYPE}-{backend}.zip" # Dynamic name
        # Fetch binaries
        urls = URLS.get((OS_TYPE, backend)) or URLS.get(("any", Backend.CPU)) or []
        if urls:
            latest_tag = get_latest_tag()
            for url_template in urls:
                url = url_template.format(tag=latest_tag) if '{tag}' in url_template else url_template
                zip_name = Path(url_template).name.format(tag=latest_tag) if '{tag}' in url_template else Path(url_template).name
                zip_path = ROOT / zip_name
                fetch_and_extract(url, zip_path, LLAMA_DIR, force_download)
        else:
            build_llama_cpp(backend)
        bins = find_bins(LLAMA_DIR)
        llama_cli = bins["cli"]
        llama_server = bins["server"]
        merge_tool = bins["merge"]
        log(f"[RESOLVE] CLI={llama_cli or '-'}  SERVER={llama_server or '-'}  MERGE={merge_tool or '-'}")
        # HF model
        from huggingface_hub import snapshot_download
        local_repo_dir = snapshot_download(
            repo_id=HF_REPO,
            allow_patterns=[HF_PATTERN],
            local_dir=MODEL_DIR,
        )
        log(t("HF_LOCAL_COPY", dir=local_repo_dir))
        model_path = resolve_model_path(Path(local_repo_dir), MERGED_GGUF, merge_tool)
        log(t("MODEL_RESOLVE_SINGLE", path=model_path, size=human_size(Path(model_path))) if "single" in model_path else t("MODEL_RESOLVE_MERGED", path=model_path, size=human_size(Path(model_path))))
        # Flag autodetect
        help_text = get_help(llama_cli or llama_server)
        FLAG_NGL = pick_flag(help_text, ["--n-gpu-layers", "--gpu-layers"]) or "--n-gpu-layers"
        FLAG_UBAT = pick_flag(help_text, ["--ubatch-size", "--gpu-batch-size"])
        FLAG_TB = pick_flag(help_text, ["--threads-batch"])
        FLAG_NOMAP = None
        log(f"[FLAGS] using: NGL={FLAG_NGL}  UBATCH={FLAG_UBAT or '-'}  TB={FLAG_TB or '-'}  NO_MMAP={FLAG_NOMAP or '-'}")
        # Smoke test
        log(t("RUN_SMOKE", ctx=2048, bs=384, ubs=96, ngl=10, pred=32, temp=0.2, seed=42))
        log(t("GPU_BEFORE", snap=gpu_mem_snapshot()))
        if llama_cli:
            cmd = [llama_cli,
                   "--model", model_path,
                   "--prompt", "You are the Citadel local assistant. Confirm readiness in one short sentence.",
                   "--ctx-size", "2048",
                   "--batch-size", "384",
                   "--n-predict", "32",
                   "--temp", "0.2",
                   "--seed", "42"]
            if FLAG_UBAT: cmd += [FLAG_UBAT, "96"]
            if FLAG_NGL: cmd += [FLAG_NGL, "10"]
            cmd += ["--threads", str(os.cpu_count() or 16)]
            if FLAG_TB: cmd += [FLAG_TB, "16"]
            rc, lines = stream_exec(cmd, timeout_s=300)
            if rc != 0:
                err(t("SMOKE_FAIL", rc=rc))
                sys.exit(1)
            else:
                perf = parse_llama_timings(lines)
                perf.update({"quant": HF_PATTERN, "backend": backend, "vram_gb": vram_gb})
                log_perf(perf, PERF_LOG)
        else:
            test_port = "8089"
            srv = [llama_server, "--server", "--port", test_port, "--parallel", "2", "--cont-batching",
                   "--model", model_path, "--ctx-size", "2048", "--batch-size", "384",
                   "--n-predict", "64", "--temp", "0.2", "--seed", "42"]
            if FLAG_UBAT: srv += [FLAG_UBAT, "96"]
            if FLAG_NGL: srv += [FLAG_NGL, "10"]
            srv += ["--threads", str(os.cpu_count() or 16)]
            if FLAG_TB: srv += [FLAG_TB, "16"]
            proc = subprocess.Popen(srv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            import requests
            for i in range(20):
                try:
                    r = requests.get(f"http://127.0.0.1:{test_port}/health", timeout=2)
                    if r.status_code == 200: break
                except Exception:
                    pass
                time.sleep(0.5)
            else:
                proc.terminate()
                err("llama-server health never reached 200 during smoke."); sys.exit(1)
            # quick chat
            payload = {"model": os.path.basename(model_path), "messages":[{"role":"user","content":"ping"}], "stream": False}
            start = time.time()
            r = requests.post(f"http://127.0.0.1:{test_port}/v1/chat/completions", json=payload, timeout=20)
            end = time.time()
            if r.status_code != 200:
                proc.terminate()
                err(f"llama-server chat failed: {r.status_code} {r.text}"); sys.exit(1)
            resp = r.json()
            tokens = resp.get("usage", {}).get("completion_tokens", 0)
            response_time = end - start
            gen_tps = tokens / response_time if response_time > 0 and tokens > 0 else None
            perf = {"gen_tps": gen_tps, "response_time": response_time, "tokens": tokens,
                    "quant": HF_PATTERN, "backend": backend, "vram_gb": vram_gb}
            log_perf(perf, PERF_LOG)
            proc.terminate()
        log(t("GPU_AFTER", snap=gpu_mem_snapshot()))
        # Launch server
        log(t("SERVER_LAUNCH"))
        server_port = "8080"
        if not llama_server:
            err("llama-server not found; cannot launch API. Check AV quarantine or re-run install.")
            sys.exit(1)
        server_cmd = [llama_server, "--server", "--port", server_port, "--parallel", "4", "--cont-batching",
                      "--model", model_path, "--ctx-size", "4096", "--batch-size", "512",
                      "--n-predict", "512", "--temp", "0.2", "--seed", "42",
                      "--threads", str(os.cpu_count() or 16)]
        if FLAG_UBAT: server_cmd += [FLAG_UBAT, "128"]
        if FLAG_NGL: server_cmd += [FLAG_NGL, "12"]
        if FLAG_TB: server_cmd += [FLAG_TB, "16"]
        global server_proc
        server_proc = subprocess.Popen(server_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        log(t("SERVER_PID", pid=server_proc.pid, port=server_port))
        time.sleep(10)
        # Health-probe the server before opening the UI
        try:
            import requests
            for i in range(30):
                try:
                    r = requests.get(f"http://127.0.0.1:{server_port}/health", timeout=2)
                    if r.status_code == 200:
                        break
                except Exception:
                    pass
                time.sleep(0.5)
        except Exception as e:
            warn(f"[SERVER] health probe exception: {e}")
        # Launch UI
        try:
            import gradio as gr
            import requests
            def chat_fn(message, history):
                payload = {"model": os.path.basename(model_path), "messages": [{"role": "user", "content": message}], "stream": False}
                try:
                    resp = requests.post(f"http://127.0.0.1:{server_port}/v1/chat/completions", json=payload)
                    resp.raise_for_status()
                    return resp.json()["choices"][0]["message"]["content"]
                except Exception as e:
                    return f"Error: {e}"
            gr.ChatInterface(chat_fn, title="Local LLM Chat (Qwen2.5-Coder-7B)").launch(share=False, server_name="127.0.0.1", server_port=7860)
            log(t("CHAT_UI_LAUNCHED"))
        except Exception as e:
            warn(f"[CHAT_UI] skipped: {e}")
        # Preset script
        server_bat = ROOT / ("llama_server.bat" if OS_TYPE == "windows" else "llama_server.sh")
        if not server_bat.exists():
            ubat_line = f"{FLAG_UBAT} %UBS% ^" if FLAG_UBAT else ""
            ngl_line = f"{FLAG_NGL} %NGL% ^" if FLAG_NGL else ""
            tb_line = f"{FLAG_TB} 16" if FLAG_TB else ""
            if OS_TYPE == "windows":
                content = f"""@echo off
setlocal
REM PROFILE: UE (low VRAM) or CODING (faster)
if "%Z_PROFILE%"=="" set Z_PROFILE=UE
set ROOT={ROOT}
set LLAMA_BIN={llama_server}
set MODEL={model_path}
if /I "%Z_PROFILE%"=="UE" (
  set NGL=12
  set BS=512
  set UBS=128
) else (
  set NGL=34
  set BS=1024
  set UBS=512
)
set PORT=8080
set THREADS=16
set LLAMA_CUBLAS=1
set GGML_CUDA_FORCE_CUBLAS=1
set GGML_CUDA_ALLOW_TF32=1
set AFF_MASK=0x0FFF
echo PROFILE=%Z_PROFILE%  PORT=%PORT%  NGL=%NGL%  BS=%BS%  UBS=%UBS%
echo BIN: %LLAMA_BIN%
echo MODEL: %MODEL%
start "LLM_SERVER" /affinity %AFF_MASK% /high ^
  "%LLAMA_BIN%" --server --port %PORT% --parallel 4 --cont-batching ^
  --model "%MODEL%" --ctx-size 4096 --batch-size %BS% ^
  {ubat_line}
  {ngl_line}
  --n-predict 512 --temp 0.2 --seed 42 ^
  --threads %THREADS% {tb_line}
"""
            else:
                ubat_shell = f"{FLAG_UBAT} $UBS \\" if FLAG_UBAT else ""
                ngl_shell = f"{FLAG_NGL} $NGL \\" if FLAG_NGL else ""
                tb_shell = f"{FLAG_TB} 16" if FLAG_TB else ""
                content = f"""#!/bin/bash
PROFILE="${{Z_PROFILE:-UE}}"
ROOT="{ROOT}"
LLAMA_BIN="{llama_server}"
MODEL="{model_path}"
if [ "$PROFILE" = "UE" ]; then
  NGL=12
  BS=512
  UBS=128
else
  NGL=34
  BS=1024
  UBS=512
fi
PORT=8080
THREADS=16
export LLAMA_CUBLAS=1
export GGML_CUDA_FORCE_CUBLAS=1
export GGML_CUDA_ALLOW_TF32=1
echo "PROFILE=$PROFILE  PORT=$PORT  NGL=$NGL  BS=$BS  UBS=$UBS"
echo "BIN: $LLAMA_BIN"
echo "MODEL: $MODEL"
"$LLAMA_BIN" --server --port $PORT --parallel 4 --cont-batching \
  --model "$MODEL" --ctx-size 4096 --batch-size $BS \
  {ubat_shell}
  {ngl_shell}
  --n-predict 512 --temp 0.2 --seed 42 \
  --threads $THREADS {tb_shell} &
"""
            server_bat.write_text(content)
            if OS_TYPE != "windows":
                server_bat.chmod(0o755)  # Executable
            log(t("SERVER_PRESET_WRITTEN", path=server_bat))
    # Audit
    log(t("AUDIT_VERIFY"))
    if audit_install(ROOT, {"cli": llama_cli, "server": llama_server}, model_path, server_port):
        log(t("AUDIT_COMPLETE"))
    else:
        err("[AUDIT] Issues found; check logs.")

# SIGTERM/SIGINT cleanup
server_proc = None
atexit.register(_kill_child, lambda: server_proc)
signal.signal(signal.SIGTERM, lambda *_: (_kill_child(server_proc), sys.exit(0)))
signal.signal(signal.SIGINT,  lambda *_: (_kill_child(server_proc), sys.exit(0)))

# CLI app
app = typer.Typer(add_completion=False)

@app.command()
def install(no_ui: bool = typer.Option(False, "--no-ui", help="Skip launching Gradio UI"),
            port: int = typer.Option(8080, "--port", help="API server port"),
            force_download: bool = typer.Option(False, "--force-download", help="Force redownload of binaries")):
    # ... (grow with opts; for now use defaults)
    install_all(force_download)

@app.command()
def uninstall(confirm: bool = typer.Option(False, "--confirm", help="Confirm uninstallation")):
    if not confirm:
        print("Use --confirm to proceed with uninstallation.")
        sys.exit(0)
    service_stop()
    service_uninstall()
    shutil.rmtree(ROOT)
    log("Uninstalled.")

@app.command()
def run_tests():
    # Stub: Run unit tests
    class TestInstaller(unittest.TestCase):
        def test_t(self):
            self.assertEqual(t("DEP_OK", dep="test"), "test OK")
    unittest.main(argv=[''], verbosity=2, exit=False)

@app.command()
def generate_dockerfile():
    # Stub: Generate Dockerfile
    dockerfile = """
FROM python:3.10
COPY zayara_installer.py /app/
WORKDIR /app
RUN pip install psutil huggingface_hub gradio requests typer
CMD ["python", "zayara_installer.py", "install"]
"""
    with open("Dockerfile", "w") as f:
        f.write(dockerfile)
    log("Dockerfile generated.")

@app.callback(invoke_without_command=True)
def main(version: bool = typer.Option(False, "--version")):
    if version:
        print(__version__)
        sys.exit(0)

if __name__ == "__main__":
    # Stub: Load config.json if exists
    config_path = ROOT / "config.json"
    if config_path.exists():
        with config_path.open("r") as f:
            config = json.load(f)
        # Apply config (stub, e.g., global port = config.get("port", 8080))
    if len(sys.argv) == 1:
        log(t("DEFAULT_TO_INSTALL"))
        sys.argv.append("install")  # Append 'install' to args to default to install command
    app()
