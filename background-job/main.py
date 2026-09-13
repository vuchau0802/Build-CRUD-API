import os
import uuid
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import inngest
import inngest.fast_api
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

inngest_client = inngest.Inngest(app_id="background-job-api", is_production=False)

# In-memory store — forgets everything on restart, same lesson as A1.
reports: dict[str, dict] = {}


@app.get("/health")
def health():
    return {"status": "ok"}


class ReportRequest(BaseModel):
    topic: str = ""


@app.post("/reports", status_code=202, summary="Accept a report request instantly, work happens in the background")
def create_report(req: ReportRequest):
    if not req.topic or not req.topic.strip():
        raise HTTPException(status_code=400, detail="topic is required and cannot be empty")

    report_id = str(uuid.uuid4())
    reports[report_id] = {"id": report_id, "topic": req.topic, "status": "pending"}

    inngest_client.send_sync(
        inngest.Event(name="report/requested", data={"id": report_id, "topic": req.topic})
    )

    return {"id": report_id, "status": "pending"}


@app.get("/reports/{report_id}", summary="Poll for report status/result")
def get_report(report_id: str):
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report {report_id} not found")
    return report


@app.get("/reports", summary="List all reports")
def list_reports():
    return list(reports.values())


# --- Inngest background function ---

def call_llm_about_topic(topic: str) -> str:
    """The real slow work: ask an LLM to write a short paragraph about the topic."""
    from openai import OpenAI

    client = OpenAI(
        base_url=os.environ["OPENAI_BASE_URL"],
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    res = client.chat.completions.create(
        model=os.environ.get("OPENAI_MODEL", "openrouter/free"),
        temperature=0.7,
        messages=[
            {"role": "system", "content": "Write a short, factual paragraph (3-4 sentences) about the given topic."},
            {"role": "user", "content": topic},
        ],
    )
    return res.choices[0].message.content


@inngest_client.create_function(
    fn_id="make-report",
    trigger=inngest.TriggerEvent(event="report/requested"),
    retries=2,
)
def make_report(ctx: inngest.Context) -> None:
    report_id = ctx.event.data["id"]
    topic = ctx.event.data["topic"]

    def build_report():
        if topic == "fail":
            raise Exception("The report oven is broken!")
        text = call_llm_about_topic(topic)
        reports[report_id] = {"id": report_id, "topic": topic, "status": "done", "result": text}
        return text

    ctx.step.run("build-report", build_report)


@inngest_client.create_function(
    fn_id="heartbeat",
    trigger=inngest.TriggerCron(cron="* * * * *"),
)
def heartbeat(ctx: inngest.Context) -> None:
    def log_summary():
        pending = sum(1 for r in reports.values() if r["status"] == "pending")
        done = sum(1 for r in reports.values() if r["status"] == "done")
        failed = sum(1 for r in reports.values() if r["status"] == "failed")
        print(f"[heartbeat] pending={pending} done={done} failed={failed} total={len(reports)}")

    ctx.step.run("log-summary", log_summary)


inngest.fast_api.serve(app, inngest_client, [make_report, heartbeat])