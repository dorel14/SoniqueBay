# -*- coding: utf-8 -*-
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, DATETIME, KEYWORD
from whoosh.qparser import OperatorsPlugin
from whoosh import scoring, sorting
import os

def get_or_create_index(index_dir: str):
    """Récupère l'index existant ou en crée un nouveau."""
    # Créer le répertoire s'il n'existe pas
    os.makedirs(index_dir, exist_ok=True)

    # Définition du schéma
    schema = Schema(
        path=ID(stored=True, unique=True),
        title=TEXT(stored=True),
        artist=TEXT(stored=True),
        album=TEXT(stored=True),
        genre=KEYWORD(stored=True, commas=True),
        year=ID(stored=True),
        added=DATETIME(stored=True)
    )

    # Vérifier si l'index existe
    if exists_in(index_dir):
        return open_dir(index_dir)
    
    # Créer un nouvel index si nécessaire
    return create_in(index_dir, schema)

def add_to_index(index, track):
    writer = index.writer()

    #Caculate decade
    if track['year'] is not None and track['year'].isdigit():
        # Convert year to integer and calculate decade  
        decade = str(int(track['year']) // 10 * 10)
    else:
        decade = None

    writer.add_document(
        title=track['title'],
        artist=track['artist'],
        album=track['album'],
        path=track['path'],
        genre=track['genre'],
        year=track['year'],
        decade=decade,
        disc_number=track['disc_number'],
        track_number=track['track_number'],
        acoustid_fingerprint=track['acoustid_fingerprint'],
        duration=str(track['duration']),
        musicbrain_id=track['musicbrain_id'],
        musicbrain_albumid=track['musicbrain_albumid'],
        musicbrain_artistid=track['musicbrain_artistid'],
        musicbrain_albumartistid=track['musicbrain_albumartistid'],
        musicbrain_genre=track['musicbrain_genre'],
        cover=str(track['cover'])
    )
    writer.commit()
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