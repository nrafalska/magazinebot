import json
import os

def write_result_log(job_id, pdf_path, preview_path, duration):
    result = {
        "job_id": job_id,
        "pdf": pdf_path,
        "preview": preview_path,
        "seconds": round(duration, 2)
    }

    out_file = os.path.join(
        os.getenv("AIZINE_JOBS"),
        job_id,
        "result.json"
    )

    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print("[AIZINE] Log saved:", out_file)
