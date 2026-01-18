from nicegui import ui


@ui.refreshable
def playqueue_component(app_state):
    if not app_state.playqueue:
        ui.label("No songs in queue").classes('text-slate-600 italic text-xs p-4')
        return

    for i, song in enumerate(app_state.playqueue):
        with ui.row().classes('w-full items-center gap-3 p-2 hover:bg-white/5 rounded-lg group'):
            ui.label(f"{i+1}").classes('text-[10px] text-slate-600 w-4')
            ui.image(song['cover']).classes('w-8 h-8 rounded-md')
            with ui.column().classes('gap-0 flex-grow'):
                ui.label(song['title']).classes('text-[11px] font-bold text-white truncate')
                ui.label(song['artist']).classes('text-[9px] text-slate-500 uppercase')
                ui.button(icon='close', on_click=lambda i=i: (app_state.queue.pop(i), playqueue_component.refresh())) \
                .props('flat dense size=sm color=red-4').classes('opacity-0 group-hover:opacity-100')
