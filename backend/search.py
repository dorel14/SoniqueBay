# -*- coding: utf-8 -*-
from whoosh.index import create_in
from whoosh.fields import Schema, TEXT, ID
from whoosh.qparser import OperatorsPlugin, scoring, sorting
import os

def create_search_index(directory):
    schema = Schema(title=TEXT(stored=True),
                    artist=TEXT(stored=True),
                    album=TEXT(stored=True),
                    path=ID(stored=True),
                    genre=TEXT(stored=True),
                    year=TEXT(stored=True),
                    decade=TEXT(stored=True),
                    disc_number=TEXT(stored=True),
                    track_number=TEXT(stored=True),
                    acoustid_fingerprint=TEXT(stored=True),
                    duration=TEXT(stored=True),
                    musicbrain_id=TEXT(stored=True),
                    musicbrain_albumid=TEXT(stored=True),
                    musicbrain_artistid=TEXT(stored=True),
                    musicbrain_albumartistid=TEXT(stored=True),
                    musicbrain_genre=TEXT(stored=True),
                    cover=TEXT(stored=True))
    # Create the index directory if it doesn't exist
    if not os.path.exists(directory):
        os.makedirs(directory)
    # Create the index
    index = create_in(directory, schema)
    return index
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