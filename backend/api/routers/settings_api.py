from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List
from backend.database import get_db
from backend.api.schemas.settings_schema import SettingCreate, Setting
from backend.api.models.settings_model import Setting as SettingModel
from backend.utils.crypto import encrypt_value, decrypt_value

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.post("/", response_model=Setting)
async def create_setting(setting: SettingCreate, db: SQLAlchemySession = Depends(get_db)):
    db_setting = SettingModel(
        key=setting.key,
        value=encrypt_value(setting.value) if setting.is_encrypted else setting.value,
        description=setting.description,
        is_encrypted=setting.is_encrypted
    )
    db.add(db_setting)
    db.commit()
    db.refresh(db_setting)
    return db_setting

@router.get("/", response_model=List[Setting])
async def read_settings(db: SQLAlchemySession = Depends(get_db)):
    settings = db.query(SettingModel).all()
    # Décrypter les valeurs si nécessaire
    for setting in settings:
        if setting.is_encrypted and setting.value:
            setting.value = decrypt_value(setting.value)
    return settings

@router.get("/{key}", response_model=Setting)
async def read_setting(key: str, db: SQLAlchemySession = Depends(get_db)):
    setting = db.query(SettingModel).filter(SettingModel.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Paramètre non trouvé")
    if setting.is_encrypted and setting.value:
        setting.value = decrypt_value(setting.value)
    return setting

@router.put("/{key}", response_model=Setting)
async def update_setting(key: str, setting: SettingCreate, db: SQLAlchemySession = Depends(get_db)):
    db_setting = db.query(SettingModel).filter(SettingModel.key == key).first()
    if not db_setting:
        raise HTTPException(status_code=404, detail="Paramètre non trouvé")

    db_setting.value = encrypt_value(setting.value) if setting.is_encrypted else setting.value
    db_setting.description = setting.description
    db_setting.is_encrypted = setting.is_encrypted

    db.commit()
    db.refresh(db_setting)
    return db_setting
