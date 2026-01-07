"""
MagazineBot Orchestrator — run_job.py
Simplified MVP version:
1) build_plan.py
2) InDesign COM (PowerShell)
3) PDF-only ZIP
"""

import subprocess
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
JOBS_DIR = BASE_DIR / "jobs"
AIZINE_DIR = BASE_DIR / "aizine_integration"
SCRIPTS_DIR = BASE_DIR / "scripts"

BUILD_PLAN = AIZINE_DIR / "build_plan.py"
COMPOSE_JSX = SCRIPTS_DIR / "compose.jsx"

INDESIGN_COM_PROGID = "InDesign.Application"


def safe_print(text):
    try:
        print(text)
    except Exception:
        print("<<unprintable>>")


def log(msg):
    safe_print(f"[ORCH] {msg}")


# ================================================================
# 1) BUILD PLAN
# ================================================================
def run_build_plan(job_id: str) -> Path:
    log("Running build_plan.py...")

    cmd = [
        sys.executable,
        str(BUILD_PLAN),
        "-JobId", job_id,
        "-v",
    ]

    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    safe_print(proc.stdout)
    safe_print(proc.stderr)

    if proc.returncode != 0:
        raise RuntimeError("build_plan.py FAILED")

    log("build_plan OK")
    return JOBS_DIR / job_id / "meta" / "compose_plan.json"


# ================================================================
# 2) InDesign — PowerShell COM
# ================================================================
def run_indesign(plan_path: str):
    log("Launching InDesign COM...")

    plan_path = plan_path.replace("\\", "/")
    jsx_path = COMPOSE_JSX.as_posix()

    # Write plan path to a config file that JSX can read reliably
    # Environment variables don't always work with InDesign COM
    config_file = Path(os.environ["TEMP"]) / "magazinebot_config.txt"
    config_file.write_text(plan_path, encoding="utf-8")
    config_path = str(config_file).replace("\\", "/")

    ps_script = f'''
Write-Output "[PS] === InDesign COM Runner ==="
Write-Output "[PS] JSX path: {jsx_path}"
Write-Output "[PS] Plan path: {plan_path}"
Write-Output "[PS] Config file: {config_path}"

$env:AIZINE_PLAN = "{plan_path}"
$env:AIZINE_JSX  = "{jsx_path}"
$env:AIZINE_CONFIG = "{config_path}"

# Check if JSX file exists
if (-not (Test-Path $env:AIZINE_JSX)) {{
    Write-Output "[PS] ERROR: JSX file not found!"
    exit 1
}}

# Read JSX content
$code = Get-Content $env:AIZINE_JSX -Raw -Encoding UTF8
if (-not $code) {{
    Write-Output "[PS] ERROR: JSX file is empty!"
    exit 1
}}
Write-Output "[PS] JSX loaded, length: $($code.Length) chars"

# Create COM
Write-Output "[PS] Creating InDesign COM object..."
try {{
    $app = New-Object -ComObject {INDESIGN_COM_PROGID}
    Write-Output "[PS] COM object created: $($app.Name) $($app.Version)"
}} catch {{
    Write-Output "[PS] ERROR: Cannot create COM object"
    Write-Output $_
    exit 1
}}

# Close open docs
try {{
    if ($app.Documents.Count -gt 0) {{
        Write-Output "[PS] Closing $($app.Documents.Count) open documents..."
        $app.Documents.Close()
    }}
}} catch {{
    Write-Output "[PS] Warning: Could not close documents: $_"
}}

# Execute script
Write-Output "[PS] Executing JSX script..."
try {{
    $app.DoScript($code, 1246973031)
    Write-Output "[PS] JSX execution completed"
}} catch {{
    Write-Output "[PS] ERROR executing JSX"
    Write-Output "[PS] Exception: $_"
    Write-Output "[PS] Exception type: $($_.Exception.GetType().FullName)"
    try {{ $app.Quit() }} catch {{}}
    exit 1
}}

# Quit
try {{ $app.Documents.Close() }} catch {{}}
try {{ $app.Quit() }} catch {{}}

Write-Output "[PS] SUCCESS"
exit 0
'''

    tmp = Path(os.environ["TEMP"]) / "magazinebot_indesign.ps1"
    tmp.write_text(ps_script, encoding="utf-8")

    # Extract job_id from plan_path to find debug log
    job_dir = Path(plan_path).parent.parent

    try:
        result = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(tmp)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        safe_print(result.stdout)
        safe_print(result.stderr)

        # Read and display compose debug log if it exists
        debug_log = job_dir / "meta" / "compose_debug.log"
        if debug_log.exists():
            log("=== COMPOSE.JSX DEBUG LOG ===")
            try:
                safe_print(debug_log.read_text(encoding="utf-8"))
            except Exception as e:
                log(f"Could not read debug log: {e}")
            log("=== END DEBUG LOG ===")

        if result.returncode != 0:
            raise RuntimeError("InDesign failed")

    finally:
        try:
            tmp.unlink()
        except:
            pass

    log("InDesign OK")


# ================================================================
# 3) VERIFY OUTPUT (PDF only)
# ================================================================
def verify_output(job_id: str):
    out = JOBS_DIR / job_id / "output"

    pdf = out / "final.pdf"
    if not pdf.exists():
        raise FileNotFoundError(f"PDF not found: {pdf}")

    log("PDF OK")
    return pdf


# ================================================================
# 4) ZIP (PDF only)
# ================================================================
def make_zip(job_id: str) -> Path:
    out = JOBS_DIR / job_id / "output"
    zip_path = out / "magazine.zip"

    pdf = out / "final.pdf"

    import zipfile
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        if pdf.exists():
            z.write(pdf, arcname="final.pdf")

    log("ZIP OK")
    return zip_path


# ================================================================
# MAIN
# ================================================================
def main():
    if len(sys.argv) < 2:
        print("Usage: python run_job.py <job_id>")
        sys.exit(1)

    job_id = sys.argv[1]

    log("=" * 50)
    log(f"JOB START {job_id}")
    log("=" * 50)

    plan_path = run_build_plan(job_id)

    run_indesign(str(plan_path))

    pdf = verify_output(job_id)

    zip_path = make_zip(job_id)

    log("JOB COMPLETE")
    safe_print(f"PDF: {pdf}")
    safe_print(f"ZIP: {zip_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"FATAL ERROR: {e}")
        sys.exit(1)
