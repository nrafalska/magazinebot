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

    ps_script = f'''
Write-Output "[PS] === InDesign COM Runner ==="

$env:AIZINE_PLAN = "{plan_path}"
$env:AIZINE_JSX  = "{jsx_path}"

# Read JSX content
$code = Get-Content $env:AIZINE_JSX -Raw

# Create COM
try {{
    $app = New-Object -ComObject {INDESIGN_COM_PROGID}
}} catch {{
    Write-Output "[PS] ERROR: Cannot create COM object"
    exit 1
}}

# Close open docs
try {{
    if ($app.Documents.Count -gt 0) {{
        $app.Documents.Close()
    }}
}} catch {{}}

# Execute script
try {{
    $app.DoScript($code, 1246973031)
}} catch {{
    Write-Output "[PS] ERROR executing JSX"
    Write-Output $_
    $app.Quit()
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
