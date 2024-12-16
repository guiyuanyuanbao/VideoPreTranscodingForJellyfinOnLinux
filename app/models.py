# app/models.py
from typing import Optional
from sqlmodel import SQLModel, Field

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str
    status: str  # 'pending', 'processing', 'completed', 'failed'
    progress: float = 0.0
    output_file: Optional[str] = None

