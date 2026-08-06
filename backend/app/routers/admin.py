from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..deps import get_current_user
from ..reminders import run_reminder_sweep

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/run-reminders")
def trigger_reminder_sweep(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Manually triggers the same reminder sweep the background scheduler
    runs every 12h -- lets the Pro-only reminder feature be demoed
    immediately instead of waiting for the interval to elapse."""
    sent = run_reminder_sweep(db)
    return {"reminders_sent": sent}
