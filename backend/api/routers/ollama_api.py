from fastapi import APIRouter, HTTPException
from backend.api.services.ollama_service import OllamaService
router = APIRouter(prefix="/playqueue", tags=["playqueue"])



@router.get("/models")
async def get_models():
    try:
        service = OllamaService()
        return await service.get_model_list()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")
