"""
Service de traitement d'images.
Gère le traitement, la transformation et l'optimisation des images musicales.
"""

import io
import base64
import hashlib
from typing import Dict, Any, Optional, Tuple
from PIL import Image, ImageOps, ImageFilter
import httpx
from backend_worker.utils.logging import logger
from backend_worker.services.image_service import read_image_file, process_cover_image, process_artist_image
from backend_worker.services.coverart_service import get_coverart_image
from backend_worker.services.lastfm_service import get_lastfm_artist_image


class ImageProcessingService:
    """
    Service de traitement et optimisation des images.
    
    Fonctionnalités :
    - Redimensionnement intelligent
    - Compression optimisée
    - Conversion de formats
    - Application de filtres
    - Extraction de métadonnées
    - Recherche multi-sources
    """
    
    def __init__(self):
        self.max_sizes = {
            "thumbnail": (150, 150),
            "small": (300, 300),
            "medium": (500, 500),
            "large": (800, 800),
            "original": None  # Garder la taille originale
        }
        
        self.quality_settings = {
            "thumbnail": 85,
            "small": 80,
            "medium": 85,
            "large": 90,
            "original": 95
        }
        
        # Configuration des formats supportés
        self.supported_formats = ["JPEG", "PNG", "WEBP"]
        self.preferred_format = "JPEG"
        
        logger.info("[IMAGE_PROCESSING] Service initialisé")
    
    async def process_image(
        self, 
        image_path: Optional[str] = None,
        image_data: Optional[str] = None,
        target_size: str = "medium",
        quality: Optional[int] = None,
        apply_filters: bool = False
    ) -> Dict[str, Any]:
        """
        Traite une image selon les paramètres spécifiés.
        
        Args:
            image_path: Chemin du fichier image
            image_data: Données image en base64
            target_size: Taille cible (thumbnail, small, medium, large, original)
            quality: Qualité JPEG (0-100)
            apply_filters: Appliquer des filtres d'amélioration
            
        Returns:
            Dictionnaire avec les données traitées et métadonnées
        """
        try:
            # Initialisation des variables
            original_image = None
            processed_data = None
            mime_type = "image/jpeg"
            
            # Chargement de l'image
            if image_data and image_data.startswith('data:image/'):
                # Image en base64
                original_image = await self._load_image_from_base64(image_data)
                mime_type = image_data.split(';')[0].replace('data:', '')
            elif image_path:
                # Image depuis un fichier
                image_bytes = await read_image_file(image_path)
                if image_bytes:
                    original_image = Image.open(io.BytesIO(image_bytes))
                else:
                    return {"error": "Impossible de charger l'image depuis le fichier"}
            else:
                return {"error": "Aucune source d'image fournie"}
            
            if not original_image:
                return {"error": "Impossible de charger l'image"}
            
            # Traitement de l'image
            processed_image = await self._process_image(
                original_image, 
                target_size, 
                quality, 
                apply_filters
            )
            
            # Conversion en base64
            processed_data, mime_type = await self._image_to_base64(
                processed_image,
                target_size,
                quality
            )
            
            # Calcul des métadonnées
            metadata = await self._extract_metadata(original_image, processed_image)
            
            return {
                "status": "success",
                "data": processed_data,
                "mime_type": mime_type,
                "metadata": metadata,
                "processing_info": {
                    "original_size": original_image.size,
                    "processed_size": processed_image.size,
                    "target_size": target_size,
                    "quality": quality or self.quality_settings.get(target_size, 85)
                }
            }
            
        except Exception as e:
            logger.error(f"[IMAGE_PROCESSING] Erreur traitement image: {str(e)}")
            return {"error": str(e)}
    
    async def find_and_process_image(
        self,
        image_type: str,
        entity_id: Optional[int] = None,
        entity_path: Optional[str] = None,
        mb_release_id: Optional[str] = None,
        artist_name: Optional[str] = None,
        album_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Trouve et traite une image depuis plusieurs sources.
        
        Args:
            image_type: Type d'image (album_cover, artist_image, etc.)
            entity_id: ID de l'entité
            entity_path: Chemin local
            mb_release_id: ID MusicBrainz
            artist_name: Nom de l'artiste
            album_title: Titre de l'album
            
        Returns:
            Résultat du traitement
        """
        try:
            logger.info(f"[IMAGE_PROCESSING] Recherche image {image_type} pour entité {entity_id}")
            
            # 1. Recherche locale en premier
            if entity_path:
                if image_type == "album_cover":
                    processed_result = await process_cover_image(entity_path)
                elif image_type == "artist_image":
                    processed_result = await process_artist_image(entity_path)
                else:
                    # Traitement générique
                    image_data = await self._load_local_image(entity_path)
                    if image_data:
                        processed_result = await self.process_image(image_data=image_data)
                    else:
                        processed_result = (None, None)
                
                if processed_result and processed_result[0]:
                    return {
                        "status": "success",
                        "source": "local",
                        "data": processed_result[0],
                        "mime_type": processed_result[1]
                    }
            
            # 2. Recherche sur Cover Art Archive
            if image_type == "album_cover" and mb_release_id:
                async with httpx.AsyncClient() as client:
                    cover_data = await get_coverart_image(client, mb_release_id)
                    if cover_data:
                        processed_result = await self.process_image(
                            image_data=cover_data[0],
                            target_size="medium"
                        )
                        if processed_result.get("status") == "success":
                            return {
                                "status": "success",
                                "source": "coverart",
                                "data": processed_result["data"],
                                "mime_type": processed_result["mime_type"]
                            }
            
            # 3. Recherche Last.fm
            if artist_name and (image_type == "artist_image" or image_type == "album_cover"):
                async with httpx.AsyncClient() as client:
                    # Note: get_lastfm_artist_image existe, mais il n'y a pas de fonction pour album_image
                    # Pour l'instant, on fait seulement les images d'artiste
                    if image_type == "artist_image":
                        lastfm_data = await get_lastfm_artist_image(client, artist_name)
                        
                        if lastfm_data:
                            processed_result = await self.process_image(
                                image_data=lastfm_data[0],  # lastfm_data retourne un tuple (data, mime_type)
                                target_size="medium"
                            )
                            if processed_result.get("status") == "success":
                                return {
                                    "status": "success",
                                    "source": "lastfm",
                                    "data": processed_result["data"],
                                    "mime_type": processed_result["mime_type"]
                                }
            
            return {
                "status": "not_found",
                "message": "Aucune image trouvée dans les sources disponibles"
            }
            
        except Exception as e:
            logger.error(f"[IMAGE_PROCESSING] Erreur recherche image: {str(e)}")
            return {"error": str(e)}
    
    async def optimize_for_storage(
        self,
        image_data: str,
        target_format: str = "JPEG",
        quality: int = 85,
        max_size: Tuple[int, int] = (800, 800)
    ) -> Dict[str, Any]:
        """
        Optimise une image pour le stockage.
        
        Args:
            image_data: Données image en base64
            target_format: Format cible (JPEG, PNG, WEBP)
            quality: Qualité de compression
            max_size: Taille maximale (largeur, hauteur)
            
        Returns:
            Image optimisée et métadonnées
        """
        try:
            original_image = await self._load_image_from_base64(image_data)
            if not original_image:
                return {"error": "Impossible de charger l'image"}
            
            # Redimensionnement si nécessaire
            if max_size:
                original_image.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Conversion de format si nécessaire
            if target_format.upper() != original_image.format:
                if target_format.upper() == "JPEG":
                    # Convertir en RGB pour JPEG
                    if original_image.mode in ("RGBA", "P"):
                        background = Image.new("RGB", original_image.size, (255, 255, 255))
                        if original_image.mode == "P":
                            original_image = original_image.convert("RGBA")
                        background.paste(original_image, mask=original_image.split()[-1] if original_image.mode == "RGBA" else None)
                        original_image = background
                elif target_format.upper() == "WEBP":
                    original_image = original_image.convert("RGB")
            
            # Sauvegarde optimisée
            output_buffer = io.BytesIO()
            save_kwargs = {
                "format": target_format.upper(),
                "optimize": True
            }
            
            if target_format.upper() == "JPEG":
                save_kwargs["quality"] = quality
                save_kwargs["progressive"] = True
            
            original_image.save(output_buffer, **save_kwargs)
            
            # Conversion en base64
            optimized_data = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
            optimized_mime_type = f"image/{target_format.lower()}"
            
            return {
                "status": "success",
                "data": f"data:{optimized_mime_type};base64,{optimized_data}",
                "mime_type": optimized_mime_type,
                "original_size": len(image_data),
                "optimized_size": len(optimized_data),
                "compression_ratio": len(optimized_data) / len(image_data),
                "format": target_format.upper()
            }
            
        except Exception as e:
            logger.error(f"[IMAGE_PROCESSING] Erreur optimisation: {str(e)}")
            return {"error": str(e)}
    
    async def _load_image_from_base64(self, image_data: str) -> Optional[Image.Image]:
        """Charge une image depuis une chaîne base64."""
        try:
            if image_data.startswith('data:image/'):
                # Retirer le préfixe data:image/...;base64,
                header, data = image_data.split(',', 1)
                image_bytes = base64.b64decode(data)
            else:
                image_bytes = base64.b64decode(image_data)
            
            return Image.open(io.BytesIO(image_bytes))
            
        except Exception as e:
            logger.error(f"[IMAGE_PROCESSING] Erreur chargement base64: {e}")
            return None
    
    async def _load_local_image(self, file_path: str) -> Optional[str]:
        """Charge une image locale et la convertit en base64."""
        try:
            image_bytes = await read_image_file(file_path)
            if image_bytes:
                return f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode('utf-8')}"
            return None
            
        except Exception as e:
            logger.error(f"[IMAGE_PROCESSING] Erreur chargement local: {e}")
            return None
    
    async def _process_image(
        self, 
        image: Image.Image, 
        target_size: str, 
        quality: Optional[int], 
        apply_filters: bool
    ) -> Image.Image:
        """Traite l'image selon les paramètres."""
        try:
            processed_image = image.copy()
            
            # Redimensionnement
            if target_size != "original" and target_size in self.max_sizes:
                size = self.max_sizes[target_size]
                if size:
                    processed_image.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Application de filtres si demandée
            if apply_filters:
                # Amélioration automatique du contraste
                processed_image = ImageOps.autocontrast(processed_image)
                # Réduction légère du bruit
                processed_image = processed_image.filter(ImageFilter.SMOOTH_MORE)
            
            return processed_image
            
        except Exception as e:
            logger.error(f"[IMAGE_PROCESSING] Erreur traitement: {e}")
            return image
    
    async def _image_to_base64(self, image: Image.Image, target_size: str, quality: Optional[int] = None) -> Tuple[str, str]:
        """Convertit une image PIL en base64."""
        try:
            output_buffer = io.BytesIO()
            
            # Détermination du format et de la qualité
            image_format = self.preferred_format
            save_quality = quality or self.quality_settings.get(target_size, 85)
            
            save_kwargs = {
                "format": image_format,
                "optimize": True
            }
            
            if image_format == "JPEG":
                save_kwargs["quality"] = save_quality
                save_kwargs["progressive"] = True
            
            image.save(output_buffer, **save_kwargs)
            
            # Conversion en base64
            image_data = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
            mime_type = f"image/{image_format.lower()}"
            
            return f"data:{mime_type};base64,{image_data}", mime_type
            
        except Exception as e:
            logger.error(f"[IMAGE_PROCESSING] Erreur conversion base64: {e}")
            return None, None
    
    async def _extract_metadata(
        self, 
        original_image: Image.Image, 
        processed_image: Image.Image
    ) -> Dict[str, Any]:
        """Extrait les métadonnées d'une image."""
        try:
            metadata = {
                "original_dimensions": original_image.size,
                "processed_dimensions": processed_image.size,
                "original_mode": original_image.mode,
                "processed_mode": processed_image.mode,
                "original_format": original_image.format,
                "file_size_ratio": (
                    processed_image.size[0] * processed_image.size[1] * len(processed_image.getbands()) /
                    (original_image.size[0] * original_image.size[1] * len(original_image.getbands()))
                    if original_image.size[0] * original_image.size[1] > 0 else 1.0
                )
            }
            
            # Informations EXF si disponibles
            if hasattr(original_image, '_getexif') and original_image._getexif():
                exif_data = original_image._getexif()
                metadata["exif_available"] = True
                metadata["exif_keys"] = list(exif_data.keys())
            else:
                metadata["exif_available"] = False
            
            return metadata
            
        except Exception as e:
            logger.warning(f"[IMAGE_PROCESSING] Erreur extraction métadonnées: {e}")
            return {"error": str(e)}


# Instance globale du service
image_processing_service = ImageProcessingService()


# ============================================================================
# FONCTIONS UTILITAIRES
# ============================================================================

async def initialize_image_processing():
    """Initialise le service de traitement d'images."""
    return image_processing_service


def calculate_image_hash(image_data: str) -> str:
    """
    Calcule un hash SHA256 d'une image.
    
    Args:
        image_data: Données image en base64
        
    Returns:
        Hash hexadécimal
    """
    try:
        # Retirer le préfixe si présent
        if image_data.startswith('data:image/'):
            header, data = image_data.split(',', 1)
            image_bytes = base64.b64decode(data)
        else:
            image_bytes = base64.b64decode(image_data)
        
        return hashlib.sha256(image_bytes).hexdigest()
        
    except Exception as e:
        logger.error(f"[IMAGE_PROCESSING] Erreur calcul hash: {e}")
        return ""