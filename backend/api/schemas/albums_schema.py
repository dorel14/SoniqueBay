from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
from typing import Optional, List
from .base_schema import TimestampedSchema
from .covers_schema import Cover
from backend.api.utils.logging import logger

class AlbumBase(BaseModel):
    title: str = Field(..., description="Titre de l'album")
    album_artist_id: int = Field(..., description="ID de l'artiste")
    release_year: Optional[str] = Field(None, description="Année de sortie")
    musicbrainz_albumid: Optional[str] = Field(None, description="ID MusicBrainz de l'album")
    
    # Champ optionnel pour résoudre album_artist_name -> album_artist_id
    album_artist_name: Optional[str] = Field(None, description="Nom de l'artiste (pour résolution automatique)", deprecated=True)

    @field_validator('release_year')
    @classmethod
    def validate_release_year(cls, v):
        """Convertit automatiquement int vers str et extrait l'année des dates."""
        if v is None:
            return v
        try:
            if isinstance(v, int):
                return str(v)
            elif isinstance(v, str):
                # Nettoyer les espaces
                v = v.strip()
                
                # Cas 1: Juste une année (priorité absolue)
                if v.isdigit():
                    if len(v) == 4:  # Année complète
                        return v
                    elif len(v) == 2:  # Année courte
                        year_int = int(v)
                        if year_int <= 30:
                            return f"20{v}"
                        else:
                            return f"19{v}"
                
                # Cas 2: Date au format YYYY-MM-DD ou YYYY/MM/DD
                # Détecter si commence par 4 chiffres (année)
                if len(v) >= 4 and v[:4].isdigit():
                    separator = None
                    if '-' in v:
                        separator = '-'
                    elif '/' in v:
                        separator = '/'
                    
                    if separator:
                        parts = v.split(separator)
                        if len(parts) >= 1 and len(parts[0]) == 4 and parts[0].isdigit():
                            return parts[0]
                
                # Cas 3: Date au format dd/mm/yyyy ou dd/mm/yy
                # Détecter si commence par 1-2 chiffres puis slash
                if '/' in v and len(v.split('/')) == 3:
                    parts = v.split('/')
                    # dd/mm/yyyy : le 3ème élément (index 2) est l'année
                    if len(parts[2]) == 4 and parts[2].isdigit():
                        return parts[2]
                    elif len(parts[2]) == 2 and parts[2].isdigit():
                        # dd/mm/yy : convertir yy en yyyy
                        year_int = int(parts[2])
                        if year_int <= 30:
                            return f"20{parts[2]}"
                        else:
                            return f"19{parts[2]}"
                
                # Cas 4: Autres formats avec tirets (non YYYY-MM-DD)
                # Essayer d'extraire l'année si elle commence par 2 chiffres
                if '-' in v and not v[:4].isdigit():
                    parts = v.split('-')
                    if len(parts[0]) == 2 and parts[0].isdigit():
                        year_int = int(parts[0])
                        if year_int <= 30:
                            return f"20{parts[0]}"
                        else:
                            return f"19{parts[0]}"
                
                # Si aucune logique n'a fonctionné
                logger.warning(f"Format de release_year non reconnu: {v}")
                return None
                    
            else:
                # Pour les autres types, essayer de convertir
                return str(v)
        except (ValueError, TypeError) as e:
            logger.warning(f"Erreur conversion release_year: {v} ({type(v).__name__}) - {e}")
            return None

    @model_validator(mode='before')
    @classmethod
    def validate_artist_reference(cls, data):
        """
        Valide que album_artist_id est fourni ou album_artist_name avec musique.
        """
        if isinstance(data, dict):
            # Vérifier si on a les champs nécessaires
            has_artist_id = "album_artist_id" in data and data["album_artist_id"] is not None
            has_artist_name = "album_artist_name" in data and data["album_artist_name"]
            
            if has_artist_id:
                # Album_artist_id fourni - tout va bien
                if has_artist_name:
                    logger.debug(f"album_artist_id fourni ({data['album_artist_id']}), album_artist_name ignoré")
                return data
            elif has_artist_name:
                # Album_artist_name fourni mais pas d'ID
                artist_name = data["album_artist_name"]
                error_msg = (
                    f"ERREUR: album_artist_name '{artist_name}' fourni sans album_artist_id. "
                    f"Vous devez d'abord rechercher ou créer l'artiste pour obtenir son ID. "
                    f"Utilisez l'endpoint /api/artists/search?name={artist_name} pour trouver l'ID, "
                    f"ou créez l'artiste via /api/artists."
                )
                logger.error(error_msg)
                raise ValueError(error_msg)
            else:
                # Ni album_artist_id ni album_artist_name
                raise ValueError(
                    "ERREUR: album_artist_id ou album_artist_name est requis. "
                    "Vous devez fournir l'ID de l'artiste (recommandé) ou son nom."
                )
        
        return data

class AlbumCreate(AlbumBase):
    pass

class AlbumUpdate(AlbumBase):
    title: Optional[str] = None
    album_artist_id: Optional[int] = None
    release_year: Optional[str] = None
    musicbrainz_albumid: Optional[str] = None

class Album(AlbumBase, TimestampedSchema):
    id: int
    covers: List[Cover] = []

    model_config = ConfigDict(from_attributes=True)

class AlbumWithRelations(Album):
    cover_url: Optional[str] = Field(None, description="URL de la couverture")