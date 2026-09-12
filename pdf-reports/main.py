import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from report_queries import (
    get_report_data,
    init_reports_table,
    insert_report,
    get_report_by_id,
    get_latest_report_today,
)
from render import build_html, render_pdf
from pydantic import BaseModel


class GenerateOptions(BaseModel):
    force: bool = False

app = FastAPI()

DB_PATH = Path(__file__).parent / "report.db"
REPORTS_DIR = Path(__file__).parent / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

init_reports_table()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports", summary="Generate a new PDF report (idempotent per day unless forced)")
def create_report(options: GenerateOptions = GenerateOptions(), response_status: int = 201):
    from fastapi.responses import JSONResponse

    today_date = datetime.now(timezone.utc).date().isoformat()

    if not options.force:
        existing = get_latest_report_today(today_date)
        if existing:
            return JSONResponse(
                status_code=200,
                content={
                    "id": existing["id"],
                    "file": f"/reports/{existing['id']}/file",
                    "note": "A report was already generated today; returning the existing one. Pass {\"force\": true} for a fresh one.",
                },
            )

    data = get_report_data()
    html = build_html(data)

    created_at = datetime.now(timezone.utc).isoformat()

    # Insert first (with a placeholder path) so we get an id to name the file after,
    # then update the row with the real path once the file exists.
    report_id = insert_report(path="", created_at=created_at)
    file_path = REPORTS_DIR / f"{report_id}.pdf"
    render_pdf(html, str(file_path))

    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE reports SET path = ? WHERE id = ?", (str(file_path), report_id))
    conn.commit()
    conn.close()

    return JSONResponse(
        status_code=201,
        content={"id": report_id, "file": f"/reports/{report_id}/file"},
    )


@app.get("/reports/{report_id}", summary="Get report metadata")
def get_report(report_id: int):
    report = get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return {
        "id": report["id"],
        "path": report["path"],
        "created_at": report["created_at"],
        "file": f"/reports/{report_id}/file",
    }


@app.get("/reports/{report_id}/file", summary="Download the PDF file")
def get_report_file(report_id: int):
    report = get_report_by_id(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    file_path = Path(report["path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Report file missing from disk")
    return FileResponse(file_path, media_type="application/pdf", filename=f"report-{report_id}.pdf")