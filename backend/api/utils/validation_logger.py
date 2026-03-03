"""
Utility pour logger les erreurs de validation Pydantic et générer des diagnostics détaillés.
"""
import traceback
import json
from typing import Dict, Any, List
from fastapi import Request
from pydantic import ValidationError
from .logging import logger


def log_validation_error(
    endpoint: str,
    method: str,
    request_data: Dict[str, Any],
    validation_error: ValidationError,
    request: Request = None
):
    """
    Log détaillé d'une erreur de validation Pydantic.
    
    Args:
        endpoint: URL de l'endpoint appelé
        method: Méthode HTTP (GET, POST, PUT, etc.)
        request_data: Données de la requête qui ont causé l'erreur
        validation_error: L'exception Pydantic
        request: Objet Request FastAPI pour plus de contexte
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
                "input": str(error.get('input', 'N/A'))[:200]  # Limiter la taille pour les logs
            })
        
        # Informations sur la requête
        request_info = {}
        if request:
            request_info = {
                "headers": dict(request.headers),
                "query_params": dict(request.query_params),
                "client_ip": request.client.host if request.client else None,
                "user_agent": request.headers.get('user-agent', 'Unknown')
            }
        
        # Préparer le log détaillé
        log_data = {
            "error_type": "VALIDATION_ERROR_422",
            "endpoint": endpoint,
            "method": method,
            "total_validation_errors": len(error_details),
            "validation_errors": error_details,
            "request_data_sample": _sanitize_data_for_logging(request_data),
            "request_info": request_info,
            "full_error": str(validation_error),
            "traceback": traceback.format_exc()
        }
        
        logger.error(f"ERREUR 422 VALIDATION: {json.dumps(log_data, indent=2, default=str)}")
        
        # Log spécifique par type d'erreur
        _log_specific_validation_issues(error_details, endpoint)
        
    except Exception as e:
        logger.error(f"Erreur lors du log de validation: {e}")


def _sanitize_data_for_logging(data: Any, max_size: int = 1000) -> Dict[str, Any]:
    """Nettoie les données sensibles et limite la taille pour les logs."""
    try:
        if isinstance(data, dict):
            sanitized = {}
            for key, value in data.items():
                # Ne pas logger de données sensibles
                if any(sensitive in key.lower() for sensitive in ['password', 'token', 'secret', 'key']):
                    sanitized[key] = "[REDACTED]"
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
        return {"error": "Impossible de traiter les données pour le logging"}


def _log_specific_validation_issues(error_details: List[Dict], endpoint: str):
    """Log des problèmes spécifiques de validation pour diagnostiquer rapidement."""
    issues = []
    
    for error in error_details:
        field = error['field']
        error_type = error['type']
        message = error['message']
        
        if error_type == 'missing':
            issues.append(f"Champ obligatoire manquant: {field}")
        elif error_type == 'type_error':
            issues.append(f"Type incorrect pour {field}: {message}")
        elif error_type == 'value_error':
            issues.append(f"Valeur invalide pour {field}: {message}")
        elif error_type in ['less_than_equal', 'greater_than_equal', 'less_than', 'greater_than']:
            issues.append(f"Contrainte de valeur violée pour {field}: {message}")
        elif error_type == 'list_type':
            issues.append(f"Erreur de type liste pour {field}: {message}")
        else:
            issues.append(f"Validation {error_type} échouée pour {field}: {message}")
    
    if issues:
        logger.warning(f"PROBLÈMES DE VALIDATION DÉTECTÉS sur {endpoint}:")
        for i, issue in enumerate(issues, 1):
            logger.warning(f"  {i}. {issue}")


def log_schema_validation_debug(schema_name: str, data: Any, validation_result: bool = True):
    """Log pour déboguer les problèmes de validation de schéma."""
    logger.debug(f"VALIDATION SCHÉMA {schema_name}:")
    logger.debug(f"  Données d'entrée: {_sanitize_data_for_logging(data)}")
    logger.debug(f"  Résultat validation: {validation_result}")
    
    if not validation_result:
        try:
            if hasattr(data, 'model_dump'):
                logger.debug(f"  Champs présents: {list(data.model_dump().keys())}")
        except Exception as e:
            logger.debug(f"  Erreur inspection données: {e}")


def create_validation_summary(validation_errors: List[ValidationError]) -> Dict[str, Any]:
    """Crée un résumé des erreurs de validation pour le debugging."""
    summary = {
        "total_errors": len(validation_errors),
        "error_types": {},
        "field_errors": {},
        "common_patterns": []
    }
    
    for error in validation_errors:
        for err in error.errors():
            error_type = err['type']
            field = " -> ".join(str(x) for x in err['loc']) if err['loc'] else "root"
            
            # Compter les types d'erreurs
            summary["error_types"][error_type] = summary["error_types"].get(error_type, 0) + 1
            
            # Grouper par champ
            if field not in summary["field_errors"]:
                summary["field_errors"][field] = []
            summary["field_errors"][field].append({
                "type": error_type,
                "message": err['msg']
            })
    
    # Identifier les patterns communs
    if summary["error_types"]:
        most_common_type = max(summary["error_types"], key=summary["error_types"].get)
        summary["common_patterns"].append(f"Type d'erreur le plus fréquent: {most_common_type} ({summary['error_types'][most_common_type]} fois)")
    
    return summary