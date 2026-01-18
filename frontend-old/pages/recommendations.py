from nicegui import ui

def render(container):
    with container:
        ui.label('✨ Suggestions musicales').classes('text-2xl text-primary mb-4')
        ui.label('Fonctionnalité IA à venir...').classes('text-muted')