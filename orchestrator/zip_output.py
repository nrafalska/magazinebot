import os
import zipfile

def create_zip(job_id):
    out_dir = os.getenv("AIZINE_OUT")
    job_dir = os.path.join(os.getenv("AIZINE_JOBS"), job_id)

    zip_path = os.path.join(out_dir, f"magazine_{job_id}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(job_dir):
            for file in files:
                full = os.path.join(root, file)
                rel = os.path.relpath(full, job_dir)
                z.write(full, rel)

    return zip_path
