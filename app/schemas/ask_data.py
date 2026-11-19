from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class AskDataRequest(BaseModel):
    query: str


class AskDataResponse(BaseModel):
    query: str
    answer: str
    generated_sql: Optional[str] = None
    source_memos: List[str] = []
    data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None
