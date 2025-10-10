from pydantic import BaseModel, ConfigDict
from typing import Optional

class ScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Prevent extra fields

    directory: Optional[str] = None
    cleanup_deleted: bool = False