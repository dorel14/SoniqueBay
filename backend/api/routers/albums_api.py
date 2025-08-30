from fastapi import APIRouter, HTTPException, Depends, status, Query
from sqlalchemy.orm import Session as SQLAlchemySession
from backend.api.schemas.albums_schema import AlbumCreate, AlbumUpdate, Album, AlbumWithRelations
from backend.api.models.albums_model import Album as AlbumModel
from backend.api.models.tracks_model import Track as TrackModel
from backend.api.schemas.covers_schema import Cover
from backend.api.schemas.tracks_schema import Track
from sqlalchemy import func, or_
from datetime import datetime, timezone
from typing import List, Optional
from backend.utils.database import get_db
from sqlalchemy.exc import IntegrityError
from backend.utils.logging import logger
from sqlalchemy.orm import joinedload

router = APIRouter(prefix="/api/albums", tags=["albums"])

# Déplacer la route search AVANT les routes avec paramètres
@router.get("/search", response_model=List[Album])
async def search_albums(
    title: Optional[str] = Query(None),
    artist_id: Optional[int] = Query(None),
    musicbrainz_albumid: Optional[str] = Query(None),
    musicbrainz_albumartistid: Optional[str] = Query(None),
    db: SQLAlchemySession = Depends(get_db)
):
    """Recherche des albums avec critères MusicBrainz."""
    query = db.query(AlbumModel)

    if title:
        query = query.filter(func.lower(AlbumModel.title).like(f"%{title.lower()}%"))
    if artist_id:
        query = query.filter(AlbumModel.album_artist_id == artist_id)
    if musicbrainz_albumid:
        query = query.filter(AlbumModel.musicbrainz_albumid == musicbrainz_albumid)
    if musicbrainz_albumartistid:
        query = query.filter(AlbumModel.musicbrainz_albumartistid == musicbrainz_albumartistid)

    albums = query.all()
    return [Album.model_validate(album) for album in albums]

@router.post("/batch", response_model=List[AlbumWithRelations])
def create_albums_batch(albums: List[AlbumCreate], db: SQLAlchemySession = Depends(get_db)):
    """Crée ou récupère plusieurs albums en une seule fois (batch)."""
    try:
        # Clés pour identifier les albums : (titre, artist_id) ou mbid
        keys_to_find = set()
        mbids_to_find = set()
        for album_data in albums:
            if album_data.musicbrainz_albumid:
                mbids_to_find.add(album_data.musicbrainz_albumid)
            elif album_data.title and album_data.album_artist_id:
                keys_to_find.add((album_data.title.lower(), album_data.album_artist_id))

        # 1. Récupérer les albums existants en une seule requête
        existing_albums_query = db.query(AlbumModel)
        if mbids_to_find:
            existing_albums_query = existing_albums_query.filter(AlbumModel.musicbrainz_albumid.in_(mbids_to_find))
        
        # Construction d'une condition OR pour les paires (titre, artist_id)
        if keys_to_find:
            or_conditions = []
            for title, artist_id in keys_to_find:
                or_conditions.append(
                    (func.lower(AlbumModel.title) == title) & (AlbumModel.album_artist_id == artist_id)
                )
            existing_albums_query = existing_albums_query.filter(or_(*or_conditions))

        existing_albums = existing_albums_query.options(joinedload(AlbumModel.covers)).all()


        # Dictionnaires pour un accès rapide
        existing_by_mbid = {a.musicbrainz_albumid: a for a in existing_albums if a.musicbrainz_albumid}
        existing_by_key = {(a.title.lower(), a.album_artist_id): a for a in existing_albums}

        # 2. Identifier les nouveaux albums à créer
        new_albums_to_create = []
        final_album_map = {}

        for album_data in albums:
            key = album_data.musicbrainz_albumid or (album_data.title.lower(), album_data.album_artist_id)
            if key in final_album_map:
                continue

            existing = None
            if album_data.musicbrainz_albumid:
                existing = existing_by_mbid.get(album_data.musicbrainz_albumid)
            if not existing and album_data.title and album_data.album_artist_id:
                existing = existing_by_key.get((album_data.title.lower(), album_data.album_artist_id))

            if existing:
                final_album_map[key] = existing
            else:
                # Éviter les doublons dans la liste de création
                if key not in [a.musicbrainz_albumid or (a.title.lower(), a.album_artist_id) for a in new_albums_to_create]:
                    new_albums_to_create.append(album_data)

        # 3. Créer les nouveaux albums en une seule fois
        if new_albums_to_create:
            new_db_albums = [
                AlbumModel(**album.model_dump(exclude_unset=True), date_added=func.now(), date_modified=func.now())
                for album in new_albums_to_create
            ]
            db.add_all(new_db_albums)
            db.commit()
            for db_album in new_db_albums:
                db.refresh(db_album, ["covers"]) # Rafraîchir pour charger les relations
                key = db_album.musicbrainz_albumid or (db_album.title.lower(), db_album.album_artist_id)
                final_album_map[key] = db_album

        # Valider explicitement la sortie avec le schéma Pydantic
        result = []
        for album_in in albums:
            key = album_in.musicbrainz_albumid or (album_in.title.lower(), album_in.album_artist_id)
            album = final_album_map[key]
            covers = []
            if hasattr(album, "covers"):
                covers = [Cover.model_validate(c) for c in album.covers]
            album_data = {
                **album.__dict__,
                "covers": covers,
                "date_added": album.date_added or datetime.now(timezone.utc),
                "date_modified": album.date_modified or datetime.now(timezone.utc),
            }
            # On crée l'objet Pydantic puis on le "dump" en dict
            result.append(AlbumWithRelations.model_validate(album_data).model_dump())
        return result

    except IntegrityError as e:
        db.rollback()
        logger.error(f"Erreur d'intégrité lors de la création en batch d'albums: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conflit de données lors de la création en batch.")
    except Exception as e:
        db.rollback()
        logger.error(f"Erreur inattendue lors de la création en batch d'albums: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erreur interne du serveur.")

@router.post("/", response_model=Album, status_code=status.HTTP_201_CREATED)
def create_album(album: AlbumCreate, db: SQLAlchemySession = Depends(get_db)):
    try:
        # Vérifier si l'album existe déjà par musicbrainz_id
        if album.musicbrainz_albumid:
            existing_album = db.query(AlbumModel).filter(
                AlbumModel.musicbrainz_albumid == album.musicbrainz_albumid
            ).first()
            if existing_album:
                return Album.model_validate(existing_album)

        # Vérifier par titre et artiste
        existing_album = db.query(AlbumModel).filter(
            AlbumModel.title == album.title,
            AlbumModel.album_artist_id == album.album_artist_id
        ).first()
        if existing_album:
            return Album.model_validate(existing_album)

        # Créer le nouvel album
        db_album = AlbumModel(
            **album.model_dump(exclude={"date_added", "date_modified"}),
            date_added=func.now(),
            date_modified=func.now()
        )
        db.add(db_album)
        db.commit()
        db.refresh(db_album)
        return Album.model_validate(db_album)

    except IntegrityError as e:
        db.rollback()
        if "UNIQUE constraint failed: albums.musicbrainz_albumid" in str(e):
            # Double vérification en cas de race condition
            existing = db.query(AlbumModel).filter(
                AlbumModel.musicbrainz_albumid == album.musicbrainz_albumid
            ).first()
            if existing:
                return Album.model_validate(existing)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un album avec cet identifiant existe déjà"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[AlbumWithRelations])
def read_albums(skip: int = 0, limit: int = 100, db: SQLAlchemySession = Depends(get_db)):
    albums = db.query(AlbumModel).offset(skip).limit(limit).all()
    # Convertir les dates None en datetime.now()
    return [AlbumWithRelations.model_validate(
        {**album.__dict__,
         "covers": [],
         "cover_url": None,
         "date_added": album.date_added or datetime.now(timezone.utc),
         "date_modified": album.date_modified or datetime.now(timezone.utc)
        }
    ).model_dump() for album in albums]


@router.get("/{album_id}", response_model=AlbumWithRelations)
async def read_album(
    album_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    album = db.query(AlbumModel) \
        .options(joinedload(AlbumModel.covers)) \
        .filter(AlbumModel.id == album_id).first()
    if not album:
        raise HTTPException(status_code=404, detail="Album non trouvé")
    logger.debug(f"Covers trouvées pour l'album {album_id}: {album.covers}")

    try:
        album_covers = []
        if hasattr(album, 'covers') and album.covers:
            for cover in album.covers:
                try:
                    cover_data = {
                        "id": cover.id,
                        "entity_type": "album",
                        "entity_id": album.id,
                        "url": cover.url,
                        "cover_data": cover.cover_data,
                        "date_added": cover.date_added,
                        "date_modified": cover.date_modified,
                        "mime_type": cover.mime_type
                    }
                    album_covers.append(Cover(**cover_data))
                except Exception as e:
                    logger.error(f"Erreur lors du traitement de la cover {cover.id}: {str(e)}")
                    continue

        # Toujours définir album_data, même si pas de covers
        album_data = {
            **album.__dict__,
            "covers": album_covers,
            "cover_url": album_covers[0].url if album_covers else None,
            "date_added": album.date_added or datetime.now(timezone.utc),
            "date_modified": album.date_modified or datetime.now(timezone.utc),
        }

        # Retourne un dict pour FastAPI
        return AlbumWithRelations.model_validate(album_data).model_dump()

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des albums: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erreur lors de la récupération des albums"
        )

@router.get("/artists/{artist_id}", response_model=List[AlbumWithRelations])
def read_artist_albums(
    artist_id: int,
    db: SQLAlchemySession = Depends(get_db)
):
    """Récupère les albums d'un artiste spécifique."""
    try:
        albums = db.query(AlbumModel) \
            .options(joinedload(AlbumModel.covers)) \
            .filter(AlbumModel.album_artist_id == artist_id).all()
        logger.debug(f"Albums trouvés pour l'artiste {artist_id}: {len(albums)}")
        if not albums:
            raise HTTPException(status_code=404, detail="Aucun album trouvé pour cet artiste")

        album_list = []
        for album in albums:
            album_data = {
                **album.__dict__,
                "covers": [Cover.model_validate(c) for c in album.covers],
                "date_added": album.date_added or datetime.now(timezone.utc),
                "date_modified": album.date_modified or datetime.now(timezone.utc)
            }
            album_model = AlbumWithRelations.model_validate(album_data)
            album_list.append(album_model)

        return album_list

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des albums de l'artiste {artist_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des albums de l'artiste")

@router.put("/{album_id}", response_model=Album)
def update_album(album_id: int, album: AlbumUpdate, db: SQLAlchemySession = Depends(get_db)):
    db_album = db.query(AlbumModel).filter(AlbumModel.id == album_id).first()
    if db_album is None:
        raise HTTPException(status_code=404, detail="Album non trouvé")

    # Update only the fields that should be updatable, excluding timestamps
    update_data = album.model_dump(exclude_unset=True, exclude={"date_added", "date_modified"})
    for key, value in update_data.items():
        if hasattr(db_album, key):
            setattr(db_album, key, value)

    # Update the modification timestamp
    db_album.date_modified = func.now()

    db.commit()
    db.refresh(db_album)
    return Album.model_validate(db_album)

@router.get("/{album_id}/tracks", response_model=List[Track])
def read_album_tracks(album_id: int, db: SQLAlchemySession = Depends(get_db)):
    """Récupère les pistes d'un album."""
    try:
        tracks = db.query(TrackModel).filter(TrackModel.album_id == album_id).all()
        logger.debug(f"Pistes trouvées pour l'album {album_id}: {len(tracks)}")

        # Convertir en format de réponse
        result = []
        for track in tracks:
            track_dict = {
                "id": track.id,
                "title": track.title,
                "path": track.path,
                "track_artist_id": track.track_artist_id,
                "album_id": track.album_id,
                "duration": track.duration,
                "track_number": track.track_number,
                "disc_number": track.disc_number,
                "year": track.year,
                "genre": track.genre,
                "file_type": track.file_type,
                "bitrate": track.bitrate,
                "featured_artists": track.featured_artists,
                "bpm": track.bpm,
                "key": track.key,
                "scale": track.scale,
                "danceability": track.danceability,
                "mood_happy": track.mood_happy,
                "mood_aggressive": track.mood_aggressive,
                "mood_party": track.mood_party,
                "mood_relaxed": track.mood_relaxed,
                "instrumental": track.instrumental,
                "acoustic": track.acoustic,
                "tonal": track.tonal,
                "musicbrainz_id": track.musicbrainz_id,
                "musicbrainz_albumid": track.musicbrainz_albumid,
                "musicbrainz_artistid": track.musicbrainz_artistid,
                "musicbrainz_albumartistid": track.musicbrainz_albumartistid,
                "acoustid_fingerprint": track.acoustid_fingerprint,
                "date_added": track.date_added,
                "date_modified": track.date_modified,
                "genre_tags": [tag.name for tag in track.genre_tags] if track.genre_tags else [],
                "mood_tags": [tag.name for tag in track.mood_tags] if track.mood_tags else []
            }
            result.append(track_dict)

        return result

    except Exception as e:
        logger.error(f"Erreur lors de la récupération des pistes de l'album {album_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des pistes de l'album")

@router.delete("/{album_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_album(album_id: int, db: SQLAlchemySession = Depends(get_db)):
    album = db.query(AlbumModel).filter(AlbumModel.id == album_id).first()
    if album is None:
        raise HTTPException(status_code=404, detail="Album non trouvé")

    db.delete(album)
    db.commit()
    return
