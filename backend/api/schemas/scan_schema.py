from typing import Optional

from pydantic import BaseModel, ConfigDict


class ScanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")  # Prevent extra fields

    directory: Optional[str] = None
    cleanup_deleted: bool = False