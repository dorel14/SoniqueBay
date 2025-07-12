# -*- coding: UTF-8 -*-
from .homepage import render as home
from .library import render as library
from .recommendations import render as recommendations
from .downloads import render as downloads
from .api_docs import render as api_docs

ROUTES = {
    'home': home,
    'library': library,
    'recommendations': recommendations,
    'downloads': downloads,
    'api_docs': api_docs,
}