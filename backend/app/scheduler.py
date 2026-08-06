from apscheduler.schedulers.background import BackgroundScheduler

from .database import SessionLocal
from .reminders import run_reminder_sweep

scheduler = BackgroundScheduler()


def _job() -> None:
    db = SessionLocal()
    try:
        run_reminder_sweep(db)
    finally:
        db.close()


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.add_job(_job, "interval", hours=12, id="reminder_sweep", replace_existing=True)
        scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
