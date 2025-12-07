
from backend.api.utils.path_variables import PathVariables
from backend.api.models.settings_model import Setting as SettingModel
from backend.api.schemas.settings_schema import SettingCreate
from backend.api.utils.crypto import encrypt_value, decrypt_value
from typing import Any, Dict, Optional

MUSIC_PATH_TEMPLATE = "music_path_template"
ARTIST_IMAGE_FILES = "artist_image_files"
ALBUM_COVER_FILES = "album_cover_files"

DEFAULT_SETTINGS = {
    MUSIC_PATH_TEMPLATE: PathVariables.get_example_path(),
    ARTIST_IMAGE_FILES: ["folder.jpg", "fanart.jpg"],
    ALBUM_COVER_FILES: ["cover.jpg", "folder.jpg"]
}


class SettingsService:
	async def initialize_default_settings(self, db=None):
		"""Initialise les paramètres par défaut dans la base si manquants."""
		from backend.api.models.settings_model import Setting as SettingModel
		from backend.api.schemas.settings_schema import SettingCreate
		# Vérifie chaque clé par défaut et crée si manquante
		for key, value in DEFAULT_SETTINGS.items():
			db_setting = None
			if db:
				db_setting = db.query(SettingModel).filter(SettingModel.key == key).first()
			# Conversion en string si nécessaire
			str_value = value if isinstance(value, str) else __import__('json').dumps(value)
			if not db_setting:
				setting = SettingCreate(
					key=key,
					value=str_value,
					description=f"System setting: {key}",
					is_encrypted=False
				)
				if db:
					db_setting = SettingModel(
						key=setting.key,
						value=setting.value,
						description=setting.description,
						is_encrypted=setting.is_encrypted
					)
					db.add(db_setting)
					db.commit()
					db.refresh(db_setting)
		# Optionnel : log
		import logging
		logging.getLogger().info("Paramètres par défaut initialisés si manquants.")
	"""
	Service pour la gestion des paramètres système et utilisateur.
	Toutes les méthodes utilisent le modèle SettingModel et gèrent le chiffrement/décryptage si nécessaire.
	"""

	def get_path_variables(self) -> Dict[str, Any]:
		"""Retourne les variables de chemin disponibles et un exemple."""
		return {
			"variables": PathVariables.get_available_variables(),
			"example": PathVariables.get_example_path()
		}

	def validate_template(self, template: str) -> Dict[str, Any]:
		"""Valide un template de chemin et retourne le résultat."""
		is_valid = PathVariables.validate_path_template(template)
		return {
			"is_valid": is_valid,
			"template": template
		}

	def create_setting(self, setting: SettingCreate, db) -> SettingModel:
		"""Crée un paramètre, chiffre la valeur si nécessaire."""
		value = encrypt_value(setting.value) if setting.is_encrypted else setting.value
		db_setting = SettingModel(
			key=setting.key,
			value=value,
			description=setting.description,
			is_encrypted=setting.is_encrypted
		)
		db.add(db_setting)
		db.commit()
		db.refresh(db_setting)
		# Retourne le modèle avec valeur déchiffrée si besoin
		if db_setting.is_encrypted and db_setting.value:
			db_setting.value = decrypt_value(db_setting.value)
		return db_setting

	def read_settings(self, db) -> list[SettingModel]:
	    """Retourne tous les paramètres, déchiffre les valeurs si besoin."""
	    import logging
	    logger = logging.getLogger(__name__)
	
	    settings = db.query(SettingModel).all()
	    logger.info(f"Nombre de paramètres trouvés: {len(settings)}")
	
	    for setting in settings:
	        logger.info(f"Traitement du paramètre: {setting.key}, is_encrypted={setting.is_encrypted}, has_value={bool(setting.value)}")
	        if setting.is_encrypted and setting.value:
	            try:
	                logger.info(f"Valeur chiffrée avant déchiffrement: {setting.value[:50]}...")
	                decrypted_value = decrypt_value(setting.value)
	                if decrypted_value:  # Vérifier si le déchiffrement a réussi
	                    setting.value = decrypted_value
	                    logger.info(f"Déchiffrement réussi pour {setting.key}")
	                else:
	                    logger.warning(f"Déchiffrement a retourné une valeur vide pour {setting.key}, conservation de la valeur chiffrée")
	                    # Ne pas écraser avec une valeur vide, garder la valeur chiffrée pour éviter la perte de données
	            except Exception as e:
	                logger.error(f"Échec du déchiffrement pour {setting.key}: {str(e)}")
	                logger.error(f"Valeur chiffrée problématique: {setting.value[:100]}...")
	                # En cas d'échec, désactiver le chiffrement pour ce paramètre et garder la valeur chiffrée
	                setting.is_encrypted = False
	                logger.warning(f"Désactivation du chiffrement pour {setting.key} en raison de l'échec du déchiffrement")
	    return settings

	def read_setting(self, key: str, db) -> Optional[SettingModel]:
		"""Retourne un paramètre par clé, crée la valeur par défaut si besoin."""
		db_setting = db.query(SettingModel).filter(SettingModel.key == key).first()
		if not db_setting:
			if key in DEFAULT_SETTINGS:
				# Conversion en string si nécessaire
				str_value = DEFAULT_SETTINGS[key] if isinstance(DEFAULT_SETTINGS[key], str) else __import__('json').dumps(DEFAULT_SETTINGS[key])
				db_setting = SettingModel(
					key=key,
					value=str_value,
					description=f"System setting: {key}",
					is_encrypted=False
				)
				db.add(db_setting)
				db.commit()
				db.refresh(db_setting)
			else:
				return None
		if db_setting.is_encrypted and db_setting.value:
			db_setting.value = decrypt_value(db_setting.value)
		# Désérialiser si c'est du JSON
		try:
			import json
			db_setting.value = json.loads(db_setting.value) if isinstance(db_setting.value, str) and db_setting.value.startswith('[') else db_setting.value
		except (json.JSONDecodeError, TypeError):
			pass
		return db_setting

	def update_setting(self, key: str, setting: SettingCreate, db) -> Optional[SettingModel]:
		"""Met à jour un paramètre existant, chiffre la valeur si besoin."""
		db_setting = db.query(SettingModel).filter(SettingModel.key == key).first()
		if not db_setting:
			return None
		value = setting.value
		if setting.is_encrypted:
			value = encrypt_value(value)
		else:
			# Sérialiser en JSON si ce n'est pas une string
			if not isinstance(value, str):
				value = __import__('json').dumps(value)
		db_setting.value = value
		db_setting.description = setting.description
		db_setting.is_encrypted = setting.is_encrypted
		db.commit()
		db.refresh(db_setting)
		if db_setting.is_encrypted and db_setting.value:
			db_setting.value = decrypt_value(db_setting.value)
		# Désérialiser si c'est du JSON
		try:
			import json
			db_setting.value = json.loads(db_setting.value) if isinstance(db_setting.value, str) and db_setting.value.startswith('[') else db_setting.value
		except (json.JSONDecodeError, TypeError):
			pass
		return db_setting
