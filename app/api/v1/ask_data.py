from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_readonly_db
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.ask_data import AskDataRequest, AskDataResponse
from app.services.chat.text_to_sql import GuardedTextToSQL

router = APIRouter(prefix="/ask-data", tags=["Ask Your Data"])


@router.post("", response_model=AskDataResponse)
def ask_data(
    req: AskDataRequest,
    current_user: User = Depends(get_current_user),
    readonly_db: Session = Depends(get_readonly_db)
):
    """
    Guarded text-to-SQL business intelligence interface.
    """
    result = GuardedTextToSQL.execute_query(
        db=readonly_db,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_query=req.query
    )
    return result
