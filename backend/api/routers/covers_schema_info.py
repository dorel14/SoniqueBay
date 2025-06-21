from fastapi import APIRouter
from ..schemas.covers_schema import CoverCreate, CoverType

router = APIRouter(prefix="/api", tags=["covers"])

@router.get("/covers/schema")
async def get_cover_schema():
    """Retourne le schéma JSON attendu pour CoverCreate."""
    return CoverCreate.schema()

@router.get("/covers/types")
async def get_cover_types():
    """Retourne les types de couverture disponibles."""
    return [cover_type.value for cover_type in CoverType]