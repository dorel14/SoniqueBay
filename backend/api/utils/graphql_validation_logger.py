"""
Utility pour logger les erreurs de validation GraphQL (Strawberry) et conversions Pydantic.
"""
import traceback
import json
from typing import Dict, Any, List, Optional
from strawberry.types import Info
from pydantic import ValidationError
from .logging import logger


def log_graphql_validation_error(
    mutation_name: str,
    operation: str,
    graphql_data: Dict[str, Any],
    validation_error: ValidationError,
    info: Optional[Info] = None
):
    """
    Log détaillé d'une erreur de validation GraphQL entre Strawberry et Pydantic.
    
    Args:
        mutation_name: Nom de la mutation GraphQL
        operation: Type d'opération (create, update, batch, etc.)
        graphql_data: Données reçues de GraphQL
        validation_error: L'exception Pydantic
        info: Contexte GraphQL Strawberry
    """
    try:
        # Extraire les détails de validation
        error_details = []
        for error in validation_error.errors():
            field_path = " -> ".join(str(x) for x in error['loc']) if error['loc'] else "root"
            error_details.append({
                "field": field_path,
                "type": error['type'],
                "message": error['msg'],
                "input": str(error.get('input', 'N/A'))[:200]
            })
        
        # Informations sur le contexte GraphQL
        context_info = {}
        if info and hasattr(info, 'context'):
            context_info = {
                "user": getattr(info.context, 'user', 'Unknown'),
                "request_id": getattr(info.context, 'request_id', 'Unknown')
            }
        
        # Préparer le log détaillé
        log_data = {
            "error_type": "GRAPHQL_VALIDATION_ERROR",
            "mutation_name": mutation_name,
            "operation": operation,
            "total_validation_errors": len(error_details),
            "validation_errors": error_details,
            "graphql_data_sample": _sanitize_graphql_data_for_logging(graphql_data),
            "context_info": context_info,
            "full_error": str(validation_error),
            "traceback": traceback.format_exc()
        }
        
        logger.error(f"ERREUR VALIDATION GRAPHQL {mutation_name}: {json.dumps(log_data, indent=2, default=str)}")
        
        # Log spécifique pour les erreurs de conversion
        _log_specific_graphql_issues(error_details, mutation_name)
        
    except Exception as e:
        logger.error(f"Erreur lors du log de validation GraphQL: {e}")


def _sanitize_graphql_data_for_logging(data: Any, max_size: int = 1000) -> Dict[str, Any]:
    """Nettoie les données GraphQL pour les logs."""
    try:
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                if any(sensitive in key.lower() for sensitive in ['password', 'token', 'secret', 'key']):
                    sanitized[key] = "[REDACTED]"
                elif hasattr(value, '__dict__'):  # Objet Strawberry
                    sanitized[key] = f"<StrawberryObject: {type(value).__name__}>"
                elif isinstance(value, (str, int, float, bool, list, dict)):
                    str_value = str(value)
                    if len(str_value) > max_size:
                        sanitized[key] = str_value[:max_size] + "...[TRUNCATED]"
                    else:
                        sanitized[key] = value
                else:
                    sanitized[key] = f"<{type(value).__name__}>"
            return sanitized
        else:
            return {"raw_data": str(data)[:max_size] + "...[TRUNCATED]" if len(str(data)) > max_size else str(data)}
    except Exception:
        return {"error": "Impossible de traiter les données GraphQL pour le logging"}


def _log_specific_graphql_issues(error_details: List[Dict], mutation_name: str):
    """Log des problèmes spécifiques de validation GraphQL."""
    issues = []
    
    for error in error_details:
        field = error['field']
        error_type = error['type']
        message = error['message']
        
        if error_type == 'missing':
            issues.append(f"Champ Strawberry->Pydantic manquant: {field}")
        elif error_type == 'type_error':
            issues.append(f"Erreur conversion Strawberry->Pydantic pour {field}: {message}")
        elif error_type == 'value_error':
            issues.append(f"Valeur invalide pour {field}: {message}")
        elif error_type in ['less_than_equal', 'greater_than_equal', 'less_than', 'greater_than']:
            issues.append(f"Contrainte de valeur violée pour {field}: {message}")
        elif error_type == 'list_type':
            issues.append(f"Erreur conversion liste pour {field}: {message}")
        else:
            issues.append(f"Validation {error_type} échouée pour {field}: {message}")
    
    if issues:
        logger.warning(f"PROBLÈMES VALIDATION GRAPHQL {mutation_name}:")
        for i, issue in enumerate(issues, 1):
            logger.warning(f"  {i}. {issue}")


def log_graphql_mutation_entry(mutation_name: str, data_count: int = 0):
    """Log l'entrée d'une mutation pour tracer les opérations."""
    logger.info(f"GRAPHQL MUTATION ENTRY: {mutation_name} - {data_count} éléments")


def log_graphql_mutation_success(mutation_name: str, result_count: int, operation_duration: float = 0):
    """Log le succès d'une mutation."""
    logger.info(f"GRAPHQL MUTATION SUCCESS: {mutation_name} - {result_count} résultats - {operation_duration:.3f}s")


def log_graphql_mutation_error(mutation_name: str, error: Exception):
    """Log l'erreur d'une mutation."""
    logger.error(f"GRAPHQL MUTATION ERROR: {mutation_name} - {type(error).__name__}: {str(error)}")