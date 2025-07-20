from fastapi import HTTPException
from sqlalchemy.orm import Session as SQLAlchemySession
from typing import List
from api.schemas.settings_schema import SettingCreate, Setting
from api.models.settings_model import Setting as SettingModel
from utils.crypto import encrypt_value, decrypt_value
from utils.path_variables import PathVariables
import json
from utils.session import transactional

class SettingsServiceLogic:
    async def get_path_variables(self):
        """Retourne toutes les variables disponibles avec leurs descriptions."""
        variables = PathVariables.get_available_variables()
        example = PathVariables.get_example_path()
        return {
            "variables": variables,
            "example": example
        }

    async def validate_path_template(self, template: str):
        """Valide un template de chemin."""
        is_valid = PathVariables.validate_path_template(template)
        return {
            "is_valid": is_valid,
            "template": template
        }

    @transactional
    async def create_setting(self, session: SQLAlchemySession, setting: SettingCreate) -> Setting:
        db_setting = SettingModel(
            key=setting.key,
            value=encrypt_value(setting.value) if setting.is_encrypted else setting.value,
            description=setting.description,
            is_encrypted=setting.is_encrypted
        )
        session.add(db_setting)
        session.flush()
        session.refresh(db_setting)
        return db_setting

    @transactional
    async def read_settings(self, session: SQLAlchemySession) -> List[Setting]:
        settings = session.query(SettingModel).all()
        for setting in settings:
            if setting.is_encrypted and setting.value:
                setting.value = decrypt_value(setting.value)
        return settings

    @transactional
    async def read_setting(self, session: SQLAlchemySession, key: str) -> Setting:
        """Récupère un paramètre par sa clé."""
        db_setting = session.query(SettingModel).filter(SettingModel.key == key).first()
        
        if not db_setting:
            if key in ["music_path_template", "artist_image_files", "album_cover_files"]:
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
                session.add(db_setting)
                session.flush()
                session.refresh(db_setting)
            else:
                raise HTTPException(status_code=404, detail="Paramètre non trouvé")

        if db_setting.is_encrypted and db_setting.value:
            db_setting.value = decrypt_value(db_setting.value)
        
        return db_setting

    @transactional
    async def update_setting(self, session: SQLAlchemySession, key: str, setting: SettingCreate) -> Setting:
        db_setting = session.query(SettingModel).filter(SettingModel.key == key).first()
        if not db_setting:
            raise HTTPException(status_code=404, detail="Paramètre non trouvé")

        db_setting.value = encrypt_value(setting.value) if setting.is_encrypted else setting.value
        db_setting.description = setting.description
        db_setting.is_encrypted = setting.is_encrypted

        session.flush()
        session.refresh(db_setting)
        return db_setting