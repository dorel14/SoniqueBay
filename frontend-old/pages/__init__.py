# -*- coding: UTF-8 -*-
from .homepage import render as home
#from .library import render as library
from .recommendations import render as recommendations
from .downloads import render as downloads
from .search import render as search
from .settings.api_docs import render as api_docs
from .library.artists import render as artists
from .library.albums import render as albums
from .library.artist_details import render as artist_details

ROUTES = {
    'home': home,
    #'library': library,
    'artists': artists,
    'artist_details': artist_details,
    'albums': albums,
    'recommendations': recommendations,
    'downloads': downloads,
    'search': search,
    'api_docs': api_docs,
}