# app/schemas.py
from pydantic import BaseModel
from typing import Optional

class TaskRead(BaseModel):
    id: int
    filename: str
    status: str
    progress: float
    output_file: Optional[str]

    class Config:
        from_attributes = True  # 更新配置

