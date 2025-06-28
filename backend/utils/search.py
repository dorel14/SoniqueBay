# -*- coding: utf-8 -*-
from utils.search_config import configure_whoosh_warnings
configure_whoosh_warnings()
from whoosh.index import create_in, open_dir, exists_in  # noqa: E402
from whoosh.fields import Schema, ID, TEXT, NUMERIC, STORED  # noqa: E402
from whoosh.qparser import OperatorsPlugin  # noqa: E402
from whoosh import scoring, sorting  # noqa: E402
from helpers.logging import logger  # noqa: E402

import os  # noqa: E402
import shutil  # noqa: E402


def get_schema():
    """Définit le schéma d'indexation."""
    return Schema(
        id=STORED,  # ID de la base de données
        path=ID(stored=True, unique=True),
        title=TEXT(stored=True),
        artist=TEXT(stored=True),
        album=TEXT(stored=True),
        genre=TEXT(stored=True),
        year=TEXT(stored=True),
        decade=TEXT(stored=True),  # Pour le filtrage par décennie
        duration=NUMERIC(stored=True),
        track_number=STORED,
        disc_number=STORED,
        # Ajout des champs MusicBrainz pour faciliter la recherche
        musicbrainz_id=STORED,
        musicbrainz_albumid=STORED,
        musicbrainz_artistid=STORED,
        musicbrainz_genre=TEXT(stored=True)
    )

def migrate_index(index_dir: str) -> bool:
    """Vérifie si l'index nécessite une migration et le recrée si nécessaire."""
    try:
        if exists_in(index_dir):
            index = open_dir(index_dir)
            current_schema = index.schema
            new_schema = get_schema()

            # Vérifier si les champs sont différents
            if set(current_schema.names()) != set(new_schema.names()):
                logger.warning("Schéma d'index obsolète détecté. Migration nécessaire...")

                # Sauvegarder l'ancien répertoire
                backup_dir = f"{index_dir}_backup"
                if os.path.exists(index_dir):
                    shutil.copytree(index_dir, backup_dir, dirs_exist_ok=True)

                # Supprimer et recréer l'index
                shutil.rmtree(index_dir)
                os.makedirs(index_dir, exist_ok=True)
                return True

        return False
    except Exception as e:
        logger.error(f"Erreur lors de la vérification/migration de l'index: {str(e)}")
        return False

def get_or_create_index(index_dir: str, indexname: str = "music_index"):
    """Récupère l'index existant ou en crée un nouveau."""
    os.makedirs(index_dir, exist_ok=True)

    # Vérifier si une migration est nécessaire
    if migrate_index(index_dir):
        logger.info("Création d'un nouvel index avec le schéma mis à jour")
        return create_in(index_dir, get_schema(), indexname=indexname)

    # Utiliser l'index existant ou en créer un nouveau
    if exists_in(index_dir, indexname=indexname):
        return open_dir(index_dir)

    return create_in(index_dir, get_schema(),indexname=indexname)

def add_to_index(index, track):
    """Ajoute une piste à l'index Whoosh."""
    writer = index.writer()
    try:
        # Calcul de la décennie
        decade = None
        if track.get('year') and str(track.get('year')).isdigit():
            decade = str(int(track['year']) // 10 * 10)

        writer.add_document(
            id=track.get('id'),
            path=track.get('path'),
            title=track.get('title'),
            artist=track.get('artist'),
            album=track.get('album'),
            genre=track.get('genre'),
            year=track.get('year'),
            decade=decade,
            duration=track.get('duration', 0),
            track_number=track.get('track_number'),
            disc_number=track.get('disc_number'),
            musicbrainz_id=track.get('musicbrainz_id'),
            musicbrainz_albumid=track.get('musicbrainz_albumid'),
            musicbrainz_artistid=track.get('musicbrainz_artistid'),
            musicbrainz_genre=track.get('musicbrainz_genre')
        )
        writer.commit()
    except Exception as e:
        writer.cancel()
        raise e

def search_index(index, query):
    from whoosh.qparser import QueryParser
    with index.searcher(weighting=scoring.TF_IDF()) as searcher:
        query_parser = QueryParser("content", index.schema)
        op = OperatorsPlugin(And="\\+",
                                Or="\\|",
                                AndNot="&!",
                                AndMaybe="&~",
                                Not="\\-")
        query_parser.replace_plugin(op)

        artistFacet = sorting.FieldFacet("artist", allow_overlap=True)
        genreFacet = sorting.FieldFacet("genre", allow_overlap=True)
        decadeFacet = sorting.FieldFacet("decade", allow_overlap=True)
        parsed_query = query_parser.parse(query)
        results = searcher.search(parsed_query)
        nbresults = len(results)
        finalresults = []
        for result in results:
            finalresults.append(dict(result))
        return nbresults, artistFacet, genreFacet, decadeFacet, finalresults
def delete_index(index):
    index.delete_by_term('path', '*')
    index.commit()