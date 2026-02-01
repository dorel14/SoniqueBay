from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from typing import List
from backend.api.utils.database import get_async_session
from backend.api.schemas.settings_schema import SettingCreate, Setting

router = APIRouter(prefix="/settings", tags=["settings"])

# Routes spécifiques en premier
@router.get("/path-variables", description="Récupère les variables disponibles pour les chemins")
async def get_path_variables():
    from backend.api.services.settings_service import SettingsService
    service = SettingsService()
    return service.get_path_variables()

@router.post("/validate-path-template")
async def validate_template(template: str = None):
    from backend.api.services.settings_service import SettingsService
    service = SettingsService()
    return service.validate_template(template)

# Routes CRUD génériques ensuite
@router.post("/", response_model=Setting)
async def create_setting(setting: SettingCreate, db: AsyncSession = Depends(get_async_session)):
    try:
        from backend.api.services.settings_service import SettingsService
        return await SettingsService().create_setting(setting, db)
    except IntegrityError:
        raise HTTPException(status_code=400, detail="Clé existe déjà")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Settings error: {str(e)}")

@router.get("/", response_model=List[Setting])
async def read_settings(db: AsyncSession = Depends(get_async_session)):
    from backend.api.services.settings_service import SettingsService
    service = SettingsService()
    return await service.read_settings(db)

# Modifier la route pour récupérer un setting par clé
@router.get("/{key}", response_model=Setting)
async def read_setting(key: str, db: AsyncSession = Depends(get_async_session)):
    from backend.api.services.settings_service import SettingsService
    service = SettingsService()
    result = await service.read_setting(key, db)
    if not result:
        raise HTTPException(status_code=404, detail="Paramètre non trouvé")
    return result

@router.put("/{key}", response_model=Setting)
async def update_setting(key: str, setting: SettingCreate, db: AsyncSession = Depends(get_async_session)):
    from backend.api.services.settings_service import SettingsService
    service = SettingsService()
    updated = await service.update_setting(key, setting, db)
    if not updated:
        raise HTTPException(status_code=404, detail="Paramètre non trouvé")
    return updated
