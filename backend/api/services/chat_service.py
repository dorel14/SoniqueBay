"""
Service de chat IA pour SoniqueBay.
Gère les interactions avec l'assistant IA musical.
Auteur : Kilo Code
"""
import uuid
import asyncio
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.schemas.chat_schema import ChatMessage, ChatResponse, ChatHistory
from backend.api.utils.logging import logger


class ChatService:
    """Service pour gérer les interactions de chat IA."""

    @staticmethod
    async def process_message(message: ChatMessage, db: Session) -> ChatResponse:
        """
        Traite un message utilisateur et génère une réponse IA.

        Args:
            message: Message de l'utilisateur
            db: Session de base de données

        Returns:
            Réponse de l'IA
        """
        try:
            # Générer ou récupérer session_id
            session_id = message.session_id or str(uuid.uuid4())

            # Sauvegarder le message utilisateur
            await ChatService._save_message(db, session_id, "user", message.message)

            # Générer réponse IA (simulation pour l'instant)
            ai_response = await ChatService._generate_ai_response(message.message, db)

            # Sauvegarder la réponse IA
            await ChatService._save_message(db, session_id, "assistant", ai_response)

            response = ChatResponse(
                response=ai_response,
                session_id=session_id
            )

            logger.info(f"Chat response generated for session {session_id}")
            return response

        except Exception as e:
            logger.error(f"Erreur traitement message chat: {e}")
            # Retourner une réponse d'erreur
            return ChatResponse(
                response="Désolé, une erreur s'est produite. Veuillez réessayer.",
                session_id=message.session_id or str(uuid.uuid4())
            )

    @staticmethod
    async def _generate_ai_response(user_message: str, db: Session) -> str:
        """
        Génère une réponse IA basée sur le message utilisateur.
        Pour l'instant, simulation simple. À remplacer par un vrai modèle IA.
        """
        # Simulation de traitement asynchrone
        await asyncio.sleep(0.5)

        # Logique simple de réponse basée sur des mots-clés
        message_lower = user_message.lower()

        if "recommande" in message_lower or "suggère" in message_lower:
            # Rechercher des pistes dans la DB pour recommandations
            return await ChatService._get_music_recommendations(db)

        elif "cherche" in message_lower or "trouve" in message_lower:
            return "Je peux vous aider à chercher dans votre bibliothèque musicale. Que cherchez-vous ?"

        elif "joue" in message_lower or "écoute" in message_lower:
            return "Pour écouter de la musique, utilisez le player intégré de SoniqueBay."

        elif "artiste" in message_lower:
            return await ChatService._get_artist_info(db)

        else:
            return f"Je suis l'assistant musical de SoniqueBay. Je peux vous aider à découvrir de la musique, chercher des artistes, ou obtenir des recommandations. Votre message : '{user_message}'"

    @staticmethod
    async def _get_music_recommendations(db: Session) -> str:
        """Génère des recommandations musicales depuis la DB."""
        try:
            from sqlalchemy import text
            query = text("""
                SELECT t.title, a.name as artist, al.title as album
                FROM tracks t
                LEFT JOIN artists a ON t.track_artist_id = a.id
                LEFT JOIN albums al ON t.album_id = al.id
                ORDER BY RANDOM()
                LIMIT 3
            """)

            results = db.execute(query).fetchall()

            if results:
                recommendations = []
                for row in results:
                    recommendations.append(f"• {row.title} - {row.artist}")

                return "Voici quelques suggestions de votre bibliothèque :\n" + "\n".join(recommendations)
            else:
                return "Votre bibliothèque semble vide. Essayez de scanner vos fichiers audio d'abord."

        except Exception as e:
            logger.error(f"Erreur génération recommandations: {e}")
            return "Désolé, je n'arrive pas à accéder à votre bibliothèque pour le moment."

    @staticmethod
    async def _get_artist_info(db: Session) -> str:
        """Fournit des informations sur les artistes."""
        try:
            from sqlalchemy import text
            query = text("""
                SELECT a.name, COUNT(t.id) as track_count
                FROM artists a
                LEFT JOIN tracks t ON a.id = t.track_artist_id
                GROUP BY a.id, a.name
                ORDER BY track_count DESC
                LIMIT 5
            """)

            results = db.execute(query).fetchall()

            if results:
                artists = []
                for row in results:
                    artists.append(f"• {row.name} ({row.track_count} titres)")

                return "Vos artistes principaux :\n" + "\n".join(artists)
            else:
                return "Aucun artiste trouvé dans votre bibliothèque."

        except Exception as e:
            logger.error(f"Erreur récupération info artistes: {e}")
            return "Désolé, je n'arrive pas à accéder aux informations des artistes."

    @staticmethod
    async def _save_message(db: Session, session_id: str, role: str, content: str) -> None:
        """
        Sauvegarde un message dans l'historique (table à créer plus tard).
        Pour l'instant, juste log pour développement.
        """
        try:
            # TODO: Créer table chat_messages et implémenter sauvegarde
            logger.debug(f"Saving message - Session: {session_id}, Role: {role}, Content: {content[:50]}...")

            # Placeholder pour insertion en DB
            # insert_query = text("""
            #     INSERT INTO chat_messages (session_id, role, content, created_at)
            #     VALUES (:session_id, :role, :content, :created_at)
            # """)
            # db.execute(insert_query, {
            #     "session_id": session_id,
            #     "role": role,
            #     "content": content,
            #     "created_at": datetime.utcnow()
            # })
            # db.commit()

        except Exception as e:
            logger.error(f"Erreur sauvegarde message: {e}")

    @staticmethod
    async def get_chat_history(session_id: str, db: Session) -> Optional[ChatHistory]:
        """
        Récupère l'historique d'une session de chat.
        TODO: Implémenter quand table chat_messages créée.
        """
        try:
            # TODO: Implémenter récupération depuis DB
            logger.debug(f"Getting chat history for session: {session_id}")
            return None  # Placeholder

        except Exception as e:
            logger.error(f"Erreur récupération historique: {e}")
            return None

    @staticmethod
    async def stream_response(message: ChatMessage, db: Session):
        """
        Génère une réponse en streaming pour WebSocket.
        Yields des chunks de la réponse IA.
        """
        try:
            session_id = message.session_id or str(uuid.uuid4())

            # Sauvegarder message utilisateur
            await ChatService._save_message(db, session_id, "user", message.message)

            # Générer réponse en chunks
            response_chunks = await ChatService._generate_streaming_response(message.message, db)

            full_response = ""
            for chunk in response_chunks:
                full_response += chunk
                yield {
                    "type": "chat_chunk",
                    "session_id": session_id,
                    "chunk": chunk,
                    "finished": False
                }

            # Signal de fin
            yield {
                "type": "chat_chunk",
                "session_id": session_id,
                "chunk": "",
                "finished": True
            }

            # Sauvegarder réponse complète
            await ChatService._save_message(db, session_id, "assistant", full_response)

        except Exception as e:
            logger.error(f"Erreur streaming réponse: {e}")
            yield {
                "type": "error",
                "message": "Erreur lors de la génération de la réponse"
            }

    @staticmethod
    async def _generate_streaming_response(user_message: str, db: Session) -> List[str]:
        """
        Génère une réponse IA en chunks pour streaming.
        Simulation pour développement.
        """
        # Simulation de génération progressive
        base_response = await ChatService._generate_ai_response(user_message, db)

        # Diviser en chunks
        chunks = []
        words = base_response.split()
        current_chunk = ""

        for word in words:
            current_chunk += word + " "
            if len(current_chunk) > 20:  # Chunk d'environ 20 caractères
                chunks.append(current_chunk)
                current_chunk = ""
                await asyncio.sleep(0.1)  # Simulation de latence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    # ==========================================================================
    # === Phase 12: Intégration MIR =============================================
    # ==========================================================================

    @staticmethod
    async def generate_track_context(
        db: AsyncSession,
        track_id: int,
        track_title: str,
        artist_name: str,
        album_name: Optional[str] = None,
    ) -> str:
        """
        Génère le contexte de track avec données MIR pour les prompts LLM.

        Args:
            db: Session de base de données asynchrone
            track_id: ID de la piste
            track_title: Titre de la piste
            artist_name: Nom de l'artiste
            album_name: Nom de l'album (optionnel)

        Returns:
            Contexte formaté pour les LLM
        """
        try:
            # Import du service LLM MIR
            from backend.api.services.mir_llm_service import MIRLLMService

            mir_service = MIRLLMService(db)

            # Générer la description complète
            description = await mir_service.generate_track_description_for_llm(
                track_id=track_id,
                track_title=track_title,
                artist_name=artist_name,
                album_name=album_name,
            )

            logger.debug(f"[CHAT] Contexte MIR généré pour track_id={track_id}")
            return description

        except Exception as e:
            logger.error(f"[CHAT] Erreur génération contexte MIR: {e}")
            # Fallback simple
            return f"Piste: '{track_title}' par {artist_name}"

    @staticmethod
    async def get_mir_recommendations(
        db: AsyncSession,
        mood: Optional[str] = None,
        energy_min: Optional[float] = None,
        genre: Optional[str] = None,
        limit: int = 5,
    ) -> str:
        """
        Génère des recommandations basées sur les données MIR.

        Args:
            db: Session de base de données asynchrone
            mood: Mood souhaité (happy, aggressive, relaxed, party)
            energy_min: Score d'énergie minimum [0-1]
            genre: Genre souhaité
            limit: Nombre de recommandations

        Returns:
            Description des recommandations
        """
        try:
            from sqlalchemy import select, and_, func
            from backend.api.models.tracks_model import Track
            from backend.api.models.track_mir_normalized_model import TrackMIRNormalized

            # Construire la requête
            conditions = []

            if mood:
                mood_field = getattr(TrackMIRNormalized, f"mood_{mood}", None)
                if mood_field:
                    conditions.append(mood_field >= 0.5)

            if energy_min is not None:
                # Chercher dans TrackMIRScores pour energy_score
                from backend.api.models.track_mir_scores_model import TrackMIRScores
                conditions.append(TrackMIRScores.energy_score >= energy_min)

            if genre:
                conditions.append(TrackMIRNormalized.genre_main.ilike(genre))

            # Requête de base
            query = (
                select(Track, TrackMIRNormalized)
                .join(TrackMIRNormalized, Track.id == TrackMIRNormalized.track_id)
            )

            if conditions:
                query = query.where(and_(*conditions))

            query = query.limit(limit)

            result = await db.execute(query)
            tracks = result.all()

            if tracks:
                recommendations = []
                for track, mir in tracks[:limit]:
                    rec = f"• {track.title} - {track.get('artist_name', 'Inconnu')}"
                    if mir.genre_main:
                        rec += f" [{mir.genre_main}]"
                    if mir.bpm:
                        rec += f" ({int(mir.bpm)} BPM)"
                    recommendations.append(rec)

                return "Voici mes recommandations MIR :\n" + "\n".join(recommendations)
            else:
                return "Aucune piste ne correspond à vos critères de recherche MIR."

        except Exception as e:
            logger.error(f"[CHAT] Erreur recommandations MIR: {e}")
            return "Désolé, je n'ai pas pu générer de recommandations basées sur MIR."

    @staticmethod
    async def describe_track_with_mir(
        db: AsyncSession,
        track_id: int,
        track_title: str,
        artist_name: str,
    ) -> str:
        """
        Décrit une piste en utilisant les données MIR.

        Args:
            db: Session de base de données asynchrone
            track_id: ID de la piste
            track_title: Titre de la piste
            artist_name: Nom de l'artiste

        Returns:
            Description formatée
        """
        try:
            from backend.api.services.mir_llm_service import MIRLLMService

            mir_service = MIRLLMService(db)
            mir_data = await mir_service.get_mir_data(track_id)

            if not mir_data:
                return f"Piste: '{track_title}' par {artist_name}"

            # Générer le résumé
            summary = mir_service.generate_track_summary(track_id, mir_data)

            # Générer les suggestions de recherche
            suggestions = mir_service.generate_search_query_suggestions(mir_data)

            # Construire la réponse
            parts = [f"Analyse de '{track_title}' par {artist_name}:", "", summary]

            if suggestions:
                parts.extend(["", "Suggestions de recherche:"])
                for s in suggestions[:5]:
                    parts.append(f"• {s}")

            return "\n".join(parts)

        except Exception as e:
            logger.error(f"[CHAT] Erreur description MIR: {e}")
            return f"Piste: '{track_title}' par {artist_name}"