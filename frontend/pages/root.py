from nicegui import ui


from frontend.pages.main import main
from frontend.pages.other import other
from frontend.pages.api_docs import api_docs
from frontend.pages.components.layout.header import header_component
from frontend.pages.components.layout.left_drawer import left_drawer_component
from frontend.pages.components.layout.footer import footer_component
from frontend.pages.components.layout.right_drawer import right_drawer_component
from frontend.pages.components.layout.head import head_component
from frontend.pages.artist_details import artist_details_page
from frontend.pages.components.layout.audioplayer import audioplayer_component

def root_page():
    head_component()
    header_component()
    left_drawer_component()
    right_drawer_component()  
    audioplayer_component()
    footer_component()
    ui.sub_pages({'/': main,
                '/api_docs':api_docs,
                '/artist_details/{artist_id}': artist_details_page,
                '/other': other},
                ).classes('w-full h-full')


