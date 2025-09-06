from fastapi import APIRouter, HTTPException, Depends, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import or_, func
from sqlalchemy.orm import Session as SQLAlchemySession, joinedload
from typing import List, Optional
from backend.utils.database import get_db
from backend.utils.paginated_routes import paginated_route
from backend.api.schemas.artists_schema import ArtistCreate, Artist, ArtistWithRelations

from backend.api.models.artists_model import Artist as ArtistModel
from backend.api.schemas.covers_schema import Cover
from backend.utils.paginations import paginate_query
from backend.utils.logging import logger


router = APIRouter(prefix="/api/artists", tags=["artists"])

# Déplacer la route search AVANT les routes avec paramètres
@router.get("/search", response_model=List[Artist])
async def search_artists(
    name: Optional[str] = Query(None),
    musicbrainz_artistid: Optional[str] = Query(None),
    genre: Optional[str] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    """Recherche des artistes par nom, genre ou ID MusicBrainz."""
    query = db.query(ArtistModel)

    if name:
        query = query.filter(func.lower(ArtistModel.name).like(f"%{name.lower()}%"))
    if musicbrainz_artistid:
        query = query.filter(ArtistModel.musicbrainz_artistid == musicbrainz_artistid)
    if genre:
        query = query.filter(func.lower(ArtistModel.genre).like(f"%{genre.lower()}%"))

    return query.all()

@router.post("/batch", response_model=List[Artist])
def create_artists_batch(artists: List[ArtistCreate], db: SQLAlchemySession = Depends(get_db)):
    """Crée ou récupère plusieurs artistes en une seule fois (batch)."""
    try:
        artist_names = {a.name for a in artists if a.name}
        mbids = {a.musicbrainz_artistid for a in artists if a.musicbrainz_artistid}

        # 1. Récupérer les artistes existants en une seule requête
        existing_artists_query = db.query(ArtistModel).filter(
            or_(
                ArtistModel.name.in_(artist_names),
                ArtistModel.musicbrainz_artistid.in_(mbids)
            )
        )
        existing_artists = existing_artists_query.all()

        # Créer des dictionnaires pour un accès rapide
        existing_by_name = {a.name.lower(): a for a in existing_artists}
        existing_by_mbid = {a.musicbrainz_artistid: a for a in existing_artists if a.musicbrainz_artistid}

        # 2. Identifier les nouveaux artistes à créer
        new_artists_to_create = []
        final_artist_map = {} # Pour garder la trace de tous les artistes (nouveaux et existants)

        for artist_data in artists:
            artist_key = artist_data.musicbrainz_artistid or artist_data.name.lower()
            if artist_key in final_artist_map:
                continue

            existing = None
            if artist_data.musicbrainz_artistid:
                existing = existing_by_mbid.get(artist_data.musicbrainz_artistid)
            if not existing and artist_data.name:
                existing = existing_by_name.get(artist_data.name.lower())

            if existing:
                final_artist_map[artist_key] = existing
            else:
                # Éviter les doublons dans la liste de création
                if artist_key not in [a.musicbrainz_artistid or a.name.lower() for a in new_artists_to_create]:
                    new_artists_to_create.append(artist_data)

        # 3. Créer les nouveaux artistes en une seule fois
        if new_artists_to_create:
            new_db_artists = [
                ArtistModel(**artist.model_dump(exclude_unset=True), date_added=func.now(), date_modified=func.now())
                for artist in new_artists_to_create
            ]
            db.add_all(new_db_artists)
            db.commit()
            for db_artist in new_db_artists:
                key = db_artist.musicbrainz_artistid or db_artist.name.lower()
                final_artist_map[key] = db_artist
        
        # 4. Retourner la liste complète des artistes traités
        return list(final_artist_map.values())

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Erreur d'intégrité lors de la création en batch d'artistes: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflit de données lors de la création en batch.")
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur inattendue lors de la création en batch d'artistes: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@router.post("/", response_model=Artist)
def create_artist(artist: ArtistCreate, db: SQLAlchemySession = Depends(get_db)):
    """Crée un nouvel artiste."""
    try:
        # Vérifier si l'artiste existe déjà
        if artist.musicbrainz_artistid:
            existing = db.query(ArtistModel).filter(
                ArtistModel.musicbrainz_artistid == artist.musicbrainz_artistid
            ).first()
            if existing:
                return existing

        existing_artist = db.query(ArtistModel).filter(
            func.lower(ArtistModel.name) == func.lower(artist.name)
        ).first()

        if existing_artist:
            return existing_artist

        db_artist = ArtistModel(
            **artist.model_dump(exclude_unset=True),
            date_added=func.now(),
            date_modified=func.now()
        )
        db.add(db_artist)
        db.commit()
        db.refresh(db_artist)
        return db_artist
    except IntegrityError as e:
        db.rollback()
        # Double vérification en cas de race condition
        if "UNIQUE constraint failed: artists.musicbrainz_artistid" in str(e):
            existing = db.query(ArtistModel).filter(
                ArtistModel.musicbrainz_artistid == artist.musicbrainz_artistid
            ).first()
            if existing:
                return existing
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un artiste avec cet identifiant existe déjà"
        )

""" @router.get("/", response_model=PaginatedResponse[Artist])
async def read_artists(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    artists = db.query(ArtistModel).order_by('name').offset(skip).limit(limit)
    return paginate_query(artists, skip, limit) """

@paginated_route(
    router=router,
    path="",
    schema=Artist,
    db_model=ArtistModel,
    tags=["Artists"],
    summary="Liste paginée des artistes"
)
def ignored():  # ⚠️ fonction requise pour la syntaxe du décorateur, mais ignorée
    pass

@router.get("/{artist_id}", response_model=ArtistWithRelations)
async def read_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    try:
        # Modifier la requête pour inclure explicitement les covers
        artist = db.query(ArtistModel)\
                .options(joinedload(ArtistModel.covers))\
                .filter(ArtistModel.id == artist_id)\
                .first()

        if not artist:
            raise HTTPException(status_code=404, detail="Artiste non trouvé")

        # Debug log pour vérifier les covers
        logger.debug(f"Covers trouvées pour l'artiste {artist_id}: {artist.covers}")

        # Traiter les covers
        artist_covers = []
        if hasattr(artist, 'covers') and artist.covers:
            for cover in artist.covers:
                try:
                    cover_data = {
                        "id": cover.id,
                        "entity_type": "artist",
                        "entity_id": artist.id,
                        "url": cover.url,
                        "cover_data": cover.cover_data,
                        "created_at": cover.date_added,
                        "updated_at": cover.date_modified
                    }
                    artist_covers.append(Cover(**cover_data))
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de la cover {cover.id}: {str(e)}")
                    continue

        # Créer la réponse avec toutes les données de l'artiste
        response_data = {
            "id": artist.id,
            "name": artist.name,
            "musicbrainz_artistid": artist.musicbrainz_artistid,
            "date_added": artist.date_added,
            "date_modified": artist.date_modified,
            "covers": artist_covers
        }
        
        # Debug log pour vérifier la réponse
        logger.debug(f"Réponse pour l'artiste {artist_id}: {response_data}")
        
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la récupération de l'artiste {artist_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la récupération de l'artiste: {str(e)}"
        )

@router.put("/{artist_id}", response_model=Artist)
def update_artist(artist_id: int, artist: ArtistCreate, db: SQLAlchemySession = Depends(get_db)):
    db_artist = db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
    if db_artist is None:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    
    for key, value in artist.model_dump(exclude_unset=True).items():
        setattr(db_artist, key, value)
    db_artist.date_modified = func.now()  # Mise à jour compatible cross-DB
    
    db.commit()
    db.refresh(db_artist)
    return db_artist

@router.delete("/{artist_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_artist(artist_id: int, db: SQLAlchemySession = Depends(get_db)):
    artist = db.query(ArtistModel).filter(ArtistModel.id == artist_id).first()
    if artist is None:
        raise HTTPException(status_code=404, detail="Artiste non trouvé")
    
    db.delete(artist)
    db.commit()
    return {"ok": True}
