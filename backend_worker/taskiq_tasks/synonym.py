"""TaskIQ tasks for MIR synonym generation."""

from backend_worker.taskiq_app import broker
from backend_worker.services.mir_synonym_service import MIRSynonymService
from backend_worker.utils.logging import logger
import asyncio


@broker.task(name="synonym.generate_synonyms_for_tag")
async def generate_synonyms_for_tag_task(tag_type: str, tag_value: str, force: bool = False) -> dict:
    """
    Generate synonyms for a specific tag.
    
    Args:
        tag_type: Type of tag ('genre' or 'mood')
        tag_value: Value of the tag
        force: Force regeneration even if recent
        
    Returns:
        Dict with generation results
    """
    logger.info(f"[TASKIQ] Starting synonym generation for {tag_type}:{tag_value} (force={force})")
    async with MIRSynonymService() as service:
        result = await service.generate_synonyms(tag_type, tag_value, force=force)
    logger.info(f"[TASKIQ] Synonym generation completed for {tag_type}:{tag_value}: {result}")
    return result


@broker.task(name="synonym.generate_all_synonyms")
async def generate_all_synonyms_task(tag_type: str) -> dict:
    """
    Generate synonyms for all tags of a given type.
    
    Args:
        tag_type: Type of tag to process ('genre' or 'mood')
        
    Returns:
        Dict with generation results
    """
    logger.info(f"[TASKIQ] Starting batch synonym generation for {tag_type}")
    async with MIRSynonymService() as service:
        result = await service.generate_all_synonyms(tag_type)
    logger.info(f"[TASKIQ] Batch synonym generation completed for {tag_type}: {result}")
    return result