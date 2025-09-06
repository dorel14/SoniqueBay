from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session as SQLAlchemySession
from sqlalchemy.exc import IntegrityError
from typing import List
from backend.utils.database import get_db
from backend.api.schemas.settings_schema import SettingCreate, Setting
from backend.api.models.settings_model import Setting as SettingModel
from backend.utils.crypto import encrypt_value, decrypt_value
from backend.utils.path_variables import PathVariables
import json

router = APIRouter(prefix="/api/settings", tags=["settings"])

# Routes spécifiques en premier
@router.get("/path-variables", description="Récupère les variables disponibles pour les chemins")
async def get_path_variables():
    """Retourne toutes les variables disponibles avec leurs descriptions."""
    variables = PathVariables.get_available_variables()
    example = PathVariables.get_example_path()
    return {
        "variables": variables,
        "example": example
    }

@router.post("/validate-path-template")
async def validate_template(template: str = None):
    """Valide un template de chemin."""
    # Try to get template from request body if not in query
    if template is None:
        # This might happen if the client sends it in the body
        pass
    is_valid = PathVariables.validate_path_template(template)
    return {
        "is_valid": is_valid,
        "template": template
    }

# Routes CRUD génériques ensuite
@router.post("/", response_model=Setting)
async def create_setting(setting: SettingCreate, db: SQLAlchemySession = Depends(get_db)):
    try:
        encrypted_value = encrypt_value(setting.value) if setting.is_encrypted else setting.value
        db_setting = SettingModel(
            key=setting.key,
            value=encrypted_value,
            description=setting.description,
            is_encrypted=setting.is_encrypted
        )
        db.add(db_setting)
        db.commit()
        db.refresh(db_setting)

        # Créer une copie pour la réponse avec la valeur décryptée si nécessaire
        response_setting = SettingModel(
            key=db_setting.key,
            value=decrypt_value(db_setting.value) if db_setting.is_encrypted and db_setting.value else db_setting.value,
            description=db_setting.description,
            is_encrypted=db_setting.is_encrypted,
            date_added=db_setting.date_added,
            date_modified=db_setting.date_modified
        )
        response_setting.id = db_setting.id
        return response_setting
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Un paramètre avec cette clé existe déjà")

@router.get("/", response_model=List[Setting])
async def read_settings(db: SQLAlchemySession = Depends(get_db)):
    settings = db.query(SettingModel).all()
    # Décrypter les valeurs si nécessaire
    for setting in settings:
        if setting.is_encrypted and setting.value:
            setting.value = decrypt_value(setting.value)
    return settings

# Modifier la route pour récupérer un setting par clé
@router.get("/{key}", response_model=Setting)
async def read_setting(key: str, db: SQLAlchemySession = Depends(get_db)):
    """Récupère un paramètre par sa clé."""
    db_setting = db.query(SettingModel).filter(SettingModel.key == key).first()
    
    if not db_setting:
        # Vérifier si c'est une clé par défaut
        if key in ["music_path_template", "artist_image_files", "album_cover_files"]:
            # Créer le setting avec la valeur par défaut
            default_values = {
                "music_path_template": PathVariables.get_example_path(),
                "artist_image_files": json.dumps(["folder.jpg", "fanart.jpg"]),
                "album_cover_files": json.dumps(["cover.jpg", "folder.jpg"])
            }

            db_setting = SettingModel(
                key=key,
                value=default_values[key],
                description=f"System setting: {key}",
                is_encrypted=False
            )
            db.add(db_setting)
            db.commit()
            db.refresh(db_setting)
        else:
            raise HTTPException(status_code=404, detail="Paramètre non trouvé")

    # Décrypter si nécessaire - créer une copie pour éviter de modifier l'objet en base
    if db_setting.is_encrypted and db_setting.value:
        # Créer une copie de l'objet pour la réponse
        response_setting = SettingModel(
            key=db_setting.key,
            value=decrypt_value(db_setting.value),
            description=db_setting.description,
            is_encrypted=db_setting.is_encrypted,
            date_added=db_setting.date_added,
            date_modified=db_setting.date_modified
        )
        response_setting.id = db_setting.id
        return response_setting

    return db_setting

@router.put("/{key}", response_model=Setting)
async def update_setting(key: str, setting: SettingCreate, db: SQLAlchemySession = Depends(get_db)):
    db_setting = db.query(SettingModel).filter(SettingModel.key == key).first()
    if not db_setting:
        raise HTTPException(status_code=404, detail="Paramètre non trouvé")

    encrypted_value = encrypt_value(setting.value) if setting.is_encrypted else setting.value
    db_setting.value = encrypted_value
    db_setting.description = setting.description
    db_setting.is_encrypted = setting.is_encrypted

    db.commit()
    db.refresh(db_setting)
    # Décrypter la valeur pour la réponse si elle est cryptée
    if db_setting.is_encrypted and db_setting.value:
        db_setting.value = decrypt_value(db_setting.value)
    return db_setting
