from nicegui import ui, app
from fastapi.middleware.cors import CORSMiddleware
from frontend._version_ import __version__ as version
from frontend.utils.logging import logger
from frontend.pages.root import root_page as root
import os
storage_secret = os.getenv('ENCRYPTION_KEY', '123456789abcdef')
app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
)
app.add_static_files('/static', './static')

ui.run(
    root,
    host='0.0.0.0',
    title=f'SoniqueBay v{version}',
    favicon='./static/favicon.ico',
    show=False,
    storage_secret=storage_secret,
    uvicorn_reload_excludes='*.log',
    uvicorn_reload_dirs='/app/frontend',
)
