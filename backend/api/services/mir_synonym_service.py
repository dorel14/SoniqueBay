# -*- coding: utf-8 -*-
"""
Service API MIRSynonym pour la gestion des synonyms MIR avec recherche hybride.

Ce service fournit les opérations CRUD pour les synonyms dynamiques
avec recherche hybride SQL (FTS) + vectorielle (pgvector).

Dépendances:
    - backend.api.utils.logging: logger
    - backend.api.services.redis_cache_service: cache Redis
    - backend.api.models.mir_synonym_model: modèle SQLAlchemy

Auteur: SoniqueBay Team
Version: 1.0.0
"""

import hashlib
import json
from typing import Any, Optional

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.mir_synonym_model import MIRSynonym
from backend.api.services.redis_cache_service import redis_cache_service
from backend.api.utils.logging import logger


class MIRSynonymService:
    """
    Service pour gérer les synonyms MIR avec recherche hybride SQL + vectorielle.

    Ce service permet de:
    - Récupérer les synonyms pour un tag spécifique
    - Rechercher des synonyms via FTS PostgreSQL et recherche vectorielle
    - Créer ou mettre à jour des synonyms
    - Désactiver des synonyms

    Recherche Hybride:
        La recherche combine:
        - PostgreSQL Full-Text Search (FTS) sur search_terms (pondération: 0.3)
        - Recherche vectorielle via pgvector sur embedding (pondération: 0.7)

    Exemple:
        >>> service = MIRSynonymService()
        >>> synonyms = await service.get_synonyms('genre', 'rock')
        >>> results = await service.search_synonyms('énergique', tag_type='mood')
    """

    # Pondération pour la fusion des résultats
    FTS_WEIGHT = 0.3
    VECTOR_WEIGHT = 0.7

    # TTL pour le cache Redis (24 heures)
    CACHE_TTL = 86400

    def __init__(self, db: AsyncSession) -> None:
        """
        Initialise le service MIRSynonym.

        Args:
            db: Session de base de données async
        """
        self.db = db
        logger.info("[MIR_SYNONYM] Service MIRSynonym initialisé")

    async def get_synonyms(
        self, tag_type: str, tag_value: str
    ) -> Optional[dict[str, Any]]:
        """
        Récupère les synonyms pour un tag spécifique.

        Args:
            tag_type: Type de tag ('genre' ou 'mood')
            tag_value: Valeur du tag (nom du genre ou mood)

        Returns:
            Dictionnaire contenant les synonyms ou None si non trouvé
        """
        try:
            logger.debug(
                f"[MIR_SYNONYM] Récupération synonyms pour {tag_type}:{tag_value}"
            )

            # Vérifier le cache Redis d'abord
            cache_key = self._get_cache_key("synonym", tag_type, tag_value)
            cached_result = await self._get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"[MIR_SYNONYM] Cache hit pour {cache_key}")
                return cached_result

            # Requête SQLAlchemy
            query = select(MIRSynonym).where(
                MIRSynonym.tag_type == tag_type,
                MIRSynonym.tag_value == tag_value,
                MIRSynonym.is_active == True,
            )

            result = await self.db.execute(query)
            synonym_record = result.scalar_one_or_none()

            if synonym_record:
                synonym_dict = self._synonym_to_dict(synonym_record)

                # Mettre en cache
                await self._cache_result(cache_key, synonym_dict)

                return synonym_dict

            logger.debug(
                f"[MIR_SYNONYM] Aucun synonym trouvé pour {tag_type}:{tag_value}"
            )
            return None

        except Exception as e:
            logger.error(
                f"[MIR_SYNONYM] Erreur récupération synonyms {tag_type}:{tag_value}: {e}"
            )
            return None

    async def search_synonyms(
        self,
        query: str,
        tag_type: Optional[str] = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Recherche hybride FTS + vectorielle pour les synonyms.

        Cette méthode combine:
        1. Recherche Full-Text Search (FTS) sur synonyms.search_terms
        2. Recherche vectorielle sur embedding via pgvector
        3. Fusion des résultats avec pondération

        Args:
            query: Terme de recherche
            tag_type: Filtrer par type ('genre' ou 'mood') - Optionnel
            limit: Nombre maximum de résultats

        Returns:
            Liste de synonyms avec scores de pertinence
        """
        try:
            logger.info(
                f"[MIR_SYNONYM] Recherche hybride: '{query}' (type={tag_type}, limit={limit})"
            )

            # Vérifier le cache Redis
            cache_key = self._get_cache_key(
                "search", query, tag_type, str(limit)
            )
            cached_result = await self._get_cached_result(cache_key)
            if cached_result:
                logger.debug(f"[MIR_SYNONYM] Cache hit pour {cache_key}")
                return cached_result

            # Si pas de query, Lister tous les synonyms actifs
            if not query or not query.strip():
                results = await self._list_synonyms(tag_type, limit)
                await self._cache_result(cache_key, results)
                return results

            # Générer l'embedding pour la recherche vectorielle
            embedding = await self._generate_embedding(query)
            if embedding is None:
                # Fallback sur FTS uniquement
                logger.warning(
                    "[MIR_SYNONYM] Échec génération embedding, utilisation FTS uniquement"
                )
                results = await self._fts_search(query, tag_type, limit)
                await self._cache_result(cache_key, results)
                return results

            # Exécuter les deux recherches en parallèle
            fts_results, vector_results = await self._execute_hybrid_search(
                query, embedding, tag_type, limit
            )

            # Fusionner les résultats avec pondération
            merged_results = self._merge_results(
                fts_results, vector_results, limit
            )

            await self._cache_result(cache_key, merged_results)

            logger.info(
                f"[MIR_SYNONYM] {len(merged_results)} résultats pour '{query}'"
            )

            return merged_results

        except Exception as e:
            logger.error(f"[MIR_SYNONYM] Erreur recherche hybride: {e}")
            return []

    async def create_synonyms(
        self,
        tag_type: str,
        tag_value: str,
        synonyms: dict[str, Any],
        embedding: Optional[list[float]] = None,
        confidence: float = 1.0,
    ) -> dict[str, Any]:
        """
        Crée ou met à jour les synonyms pour un tag.

        Args:
            tag_type: Type de tag ('genre' ou 'mood')
            tag_value: Valeur du tag
            synonyms: Structure JSONB contenant les synonyms
            embedding: Vecteur sémantique (optionnel, généré si absent)
            confidence: Score de confiance (0.0 à 1.0)

        Returns:
            Dictionnaire représentant le synonym créé/mis à jour
        """
        try:
            logger.info(
                f"[MIR_SYNONYM] Création/mise à jour {tag_type}:{tag_value}"
            )

            # Vérifier si le synonym existe déjà
            existing = await self.get_synonyms(tag_type, tag_value)

            # Générer l'embedding si non fourni
            if embedding is None:
                search_text = self._build_search_text(synonyms)
                embedding = await self._generate_embedding(search_text)

            if existing:
                # Mise à jour de l'existant
                query = (
                    update(MIRSynonym)
                    .where(
                        MIRSynonym.tag_type == tag_type,
                        MIRSynonym.tag_value == tag_value,
                    )
                    .values(
                        synonyms=synonyms,
                        embedding=embedding,
                        confidence=confidence,
                        is_active=True,
                    )
                )
                await self.db.execute(query)
                logger.info(f"[MIR_SYNONYM] Synonym mis à jour: {tag_type}:{tag_value}")
            else:
                # Création d'un nouveau record
                synonym_record = MIRSynonym(
                    tag_type=tag_type,
                    tag_value=tag_value,
                    synonyms=synonyms,
                    embedding=embedding,
                    confidence=confidence,
                    source="api",
                    is_active=True,
                )
                self.db.add(synonym_record)
                logger.info(f"[MIR_SYNONYM] Synonym créé: {tag_type}:{tag_value}")

            await self.db.commit()

            # Invalider le cache
            await self._invalidate_cache()

            # Retourner le synonym créé/mis à jour
            return await self.get_synonyms(tag_type, tag_value) or {
                "tag_type": tag_type,
                "tag_value": tag_value,
                "synonyms": synonyms,
                "confidence": confidence,
            }

        except Exception as e:
            logger.error(
                f"[MIR_SYNONYM] Erreur création synonyms {tag_type}:{tag_value}: {e}"
            )
            await self.db.rollback()
            raise

    async def deactivate_synonyms(
        self, tag_type: str, tag_value: str
    ) -> bool:
        """
        Désactive les synonyms pour un tag (soft delete).

        Args:
            tag_type: Type de tag ('genre' ou 'mood')
            tag_value: Valeur du tag

        Returns:
            True si désactivé avec succès
        """
        try:
            logger.info(f"[MIR_SYNONYM] Désactivation {tag_type}:{tag_value}")

            query = (
                update(MIRSynonym)
                .where(
                    MIRSynonym.tag_type == tag_type,
                    MIRSynonym.tag_value == tag_value,
                )
                .values(is_active=False)
            )

            result = await self.db.execute(query)
            await self.db.commit()

            if result.rowcount > 0:
                logger.info(f"[MIR_SYNONYM] Synonym désactivé: {tag_type}:{tag_value}")
                await self._invalidate_cache()
                return True

            logger.warning(
                f"[MIR_SYNONYM] Aucun synonym trouvé pour désactivation: {tag_type}:{tag_value}"
            )
            return False

        except Exception as e:
            logger.error(
                f"[MIR_SYNONYM] Erreur désactivation {tag_type}:{tag_value}: {e}"
            )
            await self.db.rollback()
            return False

    # =========================================================================
    # Méthodes privées
    # =========================================================================

    def _get_cache_key(self, prefix: str, *args: str) -> str:
        """
        Génère une clé de cache Redis.

        Args:
            prefix: Préfixe pour identifier le type de cache
            *args: Arguments à inclure dans le hash

        Returns:
            Clé de cache Redis
        """
        # Créer un hash des arguments
        args_str = ":".join(str(arg) for arg in args)
        args_hash = hashlib.md5(args_str.encode()).hexdigest()[:12]
        return f"mir_synonym:{prefix}:{args_hash}"

    async def _get_cached_result(self, cache_key: str) -> Optional[Any]:
        """
        Récupère un résultat depuis le cache Redis.

        Args:
            cache_key: Clé de cache

        Returns:
            Résultat mis en cache ou None
        """
        try:
            cached = redis_cache_service.redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
            return None
        except Exception as e:
            logger.debug(f"[MIR_SYNONYM] Cache miss: {e}")
            return None

    async def _cache_result(self, cache_key: str, result: Any) -> None:
        """
        Met en cache un résultat Redis.

        Args:
            cache_key: Clé de cache
            Résultat à mettre en cache
        """
        try:
            if redis_cache_service.redis_client:
                redis_cache_service.redis_client.setex(
                    cache_key, self.CACHE_TTL, json.dumps(result)
                )
                logger.debug(f"[MIR_SYNONYM] Résultat mis en cache: {cache_key}")
        except Exception as e:
            logger.warning(f"[MIR_SYNONYM] Erreur mise en cache: {e}")

    async def _invalidate_cache(self) -> None:
        """
        Invalide le cache de recherche synonyms.
        """
        try:
            if redis_cache_service.redis_client:
                pattern = "mir_synonym:*"
                keys = redis_cache_service.redis_client.keys(pattern)
                if keys:
                    redis_cache_service.redis_client.delete(*keys)
                    logger.debug(f"[MIR_SYNONYM] Cache invalidé: {len(keys)} clés")
        except Exception as e:
            logger.warning(f"[MIR_SYNONYM] Erreur invalidation cache: {e}")

    def _synonym_to_dict(self, synonym: MIRSynonym) -> dict[str, Any]:
        """
        Convertit un modèle MIRSynonym en dictionnaire.

        Args:
            synonym: Instance du modèle

        Returns:
            Dictionnaire représentant le synonym
        """
        return {
            "id": synonym.id,
            "tag_type": synonym.tag_type,
            "tag_value": synonym.tag_value,
            "synonyms": synonym.synonyms,
            "search_terms": synonym.search_terms,
            "related_tags": synonym.related_tags,
            "usage_contexts": synonym.usage_contexts,
            "translations": synonym.translations,
            "embedding_dim": len(synonym.embedding) if synonym.embedding else 0,
            "source": synonym.source,
            "confidence": synonym.confidence,
            "is_active": synonym.is_active,
        }

    def _build_search_text(self, synonyms: dict[str, Any]) -> str:
        """
        Construit un texte de recherche à partir des synonyms.

        Args:
            synonyms: Structure JSONB des synonyms

        Returns:
            Texte concaténé pour la vectorisation
        """
        parts = []

        # Ajouter tag_value s'il y a des search_terms
        search_terms = synonyms.get("search_terms", [])
        if search_terms:
            parts.extend(search_terms[:10])  # Limiter à 10 termes

        # Ajouter related_tags
        related_tags = synonyms.get("related_tags", [])
        if related_tags:
            parts.extend(related_tags[:10])

        return " ".join(parts)

    async def _generate_embedding(
        self, text: str
    ) -> Optional[list[float]]:
        """
        Génère un embedding via le backend_worker.

        Cette méthode appelle l'API du backend_worker pour générer
        l'embedding sémantique en utilisant le modèle nomic-embed-text.

        Args:
            text: Texte à vectoriser

        Returns:
            Vecteur d'embedding ou None si échec
        """
        try:
            import httpx
            import os

            # URL du backend_worker (port 8003 par défaut)
            worker_url = os.getenv(
                'BACKEND_WORKER_URL',
                'http://backend_worker:8003'
            )

            # Appeler l'API d'embedding du worker
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{worker_url}/api/vectorization/embed",
                    json={"text": text}
                )

                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding")
                    model = data.get("model", "unknown")
                    dimensions = data.get("dimensions", 0)

                    logger.debug(
                        f"[MIR_SYNONYM] Embedding généré via worker "
                        f"({dimensions} dim, modèle: {model})"
                    )
                    return embedding
                else:
                    logger.error(
                        f"[MIR_SYNONYM] Erreur worker API: {response.status_code} - "
                        f"{response.text}"
                    )
                    return None

        except httpx.TimeoutException:
            logger.error("[MIR_SYNONYM] Timeout lors de l'appel au worker")
            return None
        except Exception as e:
            logger.error(f"[MIR_SYNONYM] Erreur génération embedding: {e}")
            return None

    async def _fts_search(
        self, query: str, tag_type: Optional[str], limit: int
    ) -> list[dict[str, Any]]:
        """
        Effectue une recherche Full-Text Search PostgreSQL.

        Args:
            query: Terme de recherche
            tag_type: Filtrer par type (optionnel)
            limit: Nombre maximum de résultats

        Returns:
            Liste des résultats FTS
        """
        try:
            # Construire la requête FTS
            where_clauses = ["is_active = True"]
            params = {"query": query, "limit": limit}

            if tag_type:
                where_clauses.append("tag_type = :tag_type")
                params["tag_type"] = tag_type

            where_sql = " AND ".join(where_clauses)

            # Requête FTS avec ts_rank
            sql = f"""
                SELECT id, tag_type, tag_value, synonyms,
                       ts_rank(search_terms, websearch_to_tsquery('french', :query)) as fts_rank
                FROM (
                    SELECT id, tag_type, tag_value, synonyms,
                           (synonyms->>'search_terms')::text[] as search_terms
                    FROM mir_synonyms
                    WHERE {where_sql}
                ) sub
                WHERE search_terms && ARRAY[:query]::text[]
                ORDER BY fts_rank DESC
                LIMIT :limit
            """

            result = await self.db.execute(text(sql), params)
            rows = result.fetchall()

            return [
                {
                    "tag_type": row.tag_type,
                    "tag_value": row.tag_value,
                    "synonyms": row.synonyms,
                    "fts_score": float(row.fts_rank) if row.fts_rank else 0.0,
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"[MIR_SYNONYM] Erreur FTS search: {e}")
            return []

    async def _vector_search(
        self, embedding: list[float], tag_type: Optional[str], limit: int
    ) -> list[dict[str, Any]]:
        """
        Effectue une recherche vectorielle via pgvector.

        Args:
            embedding: Vecteur de recherche
            tag_type: Filtrer par type (optionnel)
            limit: Nombre maximum de résultats

        Returns:
            Liste des résultats vectoriels
        """
        try:
            # Requête pgvector avec similarité cosinus
            where_clauses = ["is_active = True", "embedding IS NOT NULL"]
            params: dict[str, Any] = {"embedding": embedding, "limit": limit}

            if tag_type:
                where_clauses.append("tag_type = :tag_type")
                params["tag_type"] = tag_type

            where_sql = " AND ".join(where_clauses)

            # Calcul de similarité cosinus via pgvector
            sql = f"""
                SELECT id, tag_type, tag_value, synonyms,
                       1 - (embedding <=> :embedding) as similarity
                FROM mir_synonyms
                WHERE {where_sql}
                ORDER BY embedding <=> :embedding
                LIMIT :limit
            """

            result = await self.db.execute(text(sql), params)
            rows = result.fetchall()

            return [
                {
                    "tag_type": row.tag_type,
                    "tag_value": row.tag_value,
                    "synonyms": row.synonyms,
                    "vector_score": float(row.similarity),
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"[MIR_SYNONYM] Erreur vector search: {e}")
            return []

    async def _execute_hybrid_search(
        self,
        query: str,
        embedding: list[float],
        tag_type: Optional[str],
        limit: int,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """
        Exécute les recherches FTS et vectorielle en parallèle.

        Args:
            query: Terme de recherche
            embedding: Vecteur de recherche
            tag_type: Filtrer par type (optionnel)
            limit: Nombre maximum de résultats

        Returns:
            Tuple (résultats FTS, résultats vectoriels)
        """
        import asyncio

        fts_task = self._fts_search(query, tag_type, limit * 2)
        vector_task = self._vector_search(embedding, tag_type, limit * 2)

        fts_results, vector_results = await asyncio.gather(
            fts_task, vector_task, return_exceptions=True
        )

        if isinstance(fts_results, Exception):
            logger.error(f"[MIR_SYNONYM] Erreur FTS: {fts_results}")
            fts_results = []

        if isinstance(vector_results, Exception):
            logger.error(f"[MIR_SYNONYM] Erreur vector: {vector_results}")
            vector_results = []

        return fts_results, vector_results

    def _merge_results(
        self,
        fts_results: list[dict[str, Any]],
        vector_results: list[dict[str, Any]],
        limit: int,
    ) -> list[dict[str, Any]]:
        """
        Fusionne les résultats FTS et vectoriels avec pondération.

        Args:
            fts_results: Résultats de la recherche FTS
            vector_results: Résultats de la recherche vectorielle
            limit: Nombre maximum de résultats finaux

        Returns:
            Liste fusionnée triée par score pondéré
        """
        # Indexer par clé unique
        merged: dict[str, dict[str, Any]] = {}

        # Ajouter les résultats FTS
        for item in fts_results:
            key = f"{item['tag_type']}:{item['tag_value']}"
            merged[key] = {
                **item,
                "fts_score": item.get("fts_score", 0.0),
                "vector_score": 0.0,
                "hybrid_score": item.get("fts_score", 0.0) * self.FTS_WEIGHT,
            }

        # Ajouter/fusionner les résultats vectoriels
        for item in vector_results:
            key = f"{item['tag_type']}:{item['tag_value']}"
            if key in merged:
                # Fusion: ajouter le score vectoriel
                merged[key]["vector_score"] = item.get("vector_score", 0.0)
                merged[key]["hybrid_score"] = (
                    merged[key]["fts_score"] * self.FTS_WEIGHT
                    + item.get("vector_score", 0.0) * self.VECTOR_WEIGHT
                )
            else:
                merged[key] = {
                    **item,
                    "fts_score": 0.0,
                    "vector_score": item.get("vector_score", 0.0),
                    "hybrid_score": item.get("vector_score", 0.0) * self.VECTOR_WEIGHT,
                }

        # Trier par score hybride et limiter
        sorted_results = sorted(
            merged.values(),
            key=lambda x: x.get("hybrid_score", 0.0),
            reverse=True,
        )

        return sorted_results[:limit]

    async def _list_synonyms(
        self, tag_type: Optional[str], limit: int
    ) -> list[dict[str, Any]]:
        """
        Liste tous les synonyms actifs.

        Args:
            tag_type: Filtrer par type (optionnel)
            limit: Nombre maximum de résultats

        Returns:
            Liste des synonyms
        """
        try:
            query = select(MIRSynonym).where(MIRSynonym.is_active == True)

            if tag_type:
                query = query.where(MIRSynonym.tag_type == tag_type)

            query = query.limit(limit)

            result = await self.db.execute(query)
            records = result.scalars().all()

            return [self._synonym_to_dict(record) for record in records]

        except Exception as e:
            logger.error(f"[MIR_SYNONYM] Erreur list synonyms: {e}")
            return []
