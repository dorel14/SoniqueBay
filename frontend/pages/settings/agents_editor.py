from nicegui import ui
import httpx
import asyncio
import os
API_URL = os.getenv('API_URL', 'http://api:8001')


def render(container):
    with container:
        with ui.card().classes("w-full items-center p-4"):
            ui.label("Agent Editor").classes("text-xl")
            name = ui.input("Agent name").classes("w-full")
            model = ui.input("Model", value="phi3:mini").classes("w-full")
            prompt = ui.textarea("System prompt", value="").classes("w-full")
            def create_agent():
                data = {
                    "name": name.value,
                    "model": model.value,
                    "system_prompt": prompt.value,
                    "rules": [],
                    "tools": [],
                    "ui_blocks": [],
                    "response_schema": {}
                }
                async def call():
                    async with httpx.AsyncClient() as c:
                        r = await c.post(f"{API_URL}/api/agents/", json=data, timeout=10)
                        if r.status_code == 200:
                            ui.notify("Created", color="positive")
                        else:
                            ui.notify(f"Error {r.status_code}", color="negative")
                asyncio.create_task(call())
            ui.button("Create", on_click=create_agent).classes("mt-2 w-full bg-blue-600 text-white")

