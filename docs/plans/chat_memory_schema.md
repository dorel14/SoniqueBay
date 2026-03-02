# Schéma de Mémoire Conversationnelle pour IA

## Vue d'ensemble

Architecture en deux niveaux pour stocker l'historique des chats avec support de la mémoire à long terme pour les agents IA.

```
┌─────────────────────────────────────────────────────────┐
│                    CONVERSATION                         │
│              (Entête avec résumé)                       │
├─────────────────────────────────────────────────────────┤
│  • id, user_id, title                                   │
│  • summary: Résumé généré par l'IA                     │
│  • summary_embedding: Embedding vectoriel du résumé     │
│  • summary_version: Version du résumé                   │
│  • message_count: Nombre de messages                    │
│  • last_message_at: Dernier message                     │
│  • conversation_type: Catégorie                         │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   CHAT_MESSAGES                         │
│                 (Détail des messages)                   │
├─────────────────────────────────────────────────────────┤
│  • id, conversation_id, user_id                         │
│  • role: user/assistant/system/tool                     │
│  • content: Contenu textuel                             │
│  • content_embedding: Embedding du message                │
│  • metadata: tokens, model, latency...                  │
│  • sequence_number: Ordre dans la conversation          │
│  • parent_id: Pour threads/réponses imbriquées          │
└─────────────────────────────────────────────────────────┘
```

## Tables

### 1. conversations

Entête de conversation avec résumé pour recherche sémantique rapide.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Clé primaire |
| `user_id` | int | Propriétaire |
| `session_id` | UUID | Session regroupant plusieurs conversations |
| `external_id` | string | Compatibilité ancien système |
| `title` | string | Titre généré ou manuel |
| **summary** | text | **Résumé de la conversation** |
| **summary_embedding** | vector | **Embedding du résumé** |
| **summary_version** | int | **Version du résumé** |
| **summary_generated_at** | timestamp | **Date de génération** |
| `conversation_type` | enum | general, music_search, recommendation... |
| `system_context` | text | Contexte système |
| `message_count` | int | Compteur de messages |
| `last_message_at` | timestamp | Dernier message |
| `is_active` | bool | Conversation active |
| `is_archived` | bool | Archivée |

### 2. chat_messages

Messages individuels avec embeddings pour recherche dans le contexte.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Clé primaire |
| `conversation_id` | UUID | Référence conversation |
| `user_id` | int | Auteur (null pour IA) |
| `role` | enum | user, assistant, system, tool |
| `content` | text | Contenu |
| **content_embedding** | vector | **Embedding du contenu** |
| `metadata` | JSONB | tokens, model, latency... |
| `tool_calls` | JSONB | Function calling |
| `tool_call_id` | string | ID d'appel d'outil |
| `sequence_number` | int | Ordre dans conversation |
| `parent_id` | UUID | Message parent (threads) |
| `message_timestamp` | timestamp | Date du message |

### 3. chat_sessions

Regroupement logique de conversations.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Clé primaire |
| `user_id` | int | Propriétaire |
| `title` | string | Titre de la session |
| `description` | text | Description |
| `session_type` | enum | general, music_exploration... |
| `conversation_count` | int | Nombre de conversations |

### 4. conversation_summaries

Versioning des résumés pour tracking.

| Colonne | Type | Description |
|---------|------|-------------|
| `id` | UUID | Clé primaire |
| `conversation_id` | UUID | Référence |
| `version` | int | Numéro de version |
| `summary_text` | text | Contenu |
| `summary_embedding` | vector | Embedding |
| `generated_by` | enum | ai, user, system |
| `start_message_sequence` | int | Début couvert |
| `end_message_sequence` | int | Fin couverte |

## Cas d'usage pour la mémoire IA

### 1. Récupération de contexte

```python
# Récupérer les derniers messages + résumé
context = await memory_service.get_conversation_context(
    conversation_id=conv_id,
    max_messages=20,
    include_summary=True
)
# Retourne: titre, résumé, messages récents, métadonnées
```

### 2. Recherche sémantique dans l'historique

```python
# Trouver des conversations similaires à la requête actuelle
results = await memory_service.search_conversations_by_summary(
    user_id=user_id,
    query="recommandations de jazz",
    limit=5
)
# Retourne: conversations avec score de similarité
```

### 3. Enrichissement du contexte IA

```python
# Récupérer les souvenirs pertinents avant d'appeler l'IA
memories = await memory_service.get_relevant_memories(
    user_id=user_id,
    current_query="Tu me conseilles quoi ce soir ?",
    max_memories=5
)
# Combine: recherche sémantique + conversations récentes
```

### 4. Génération de résumé

```python
# Générer un résumé après N messages
summary = await memory_service.generate_conversation_summary(
    conversation_id=conv_id,
    summary_text="L'utilisateur aime le jazz et le rock des années 70...",
    generated_by="ai",
    model_used="gpt-4",
    tokens_used=150
)
# Met à jour: conversation.summary + crée un versioned summary
```

## Flux de mémoire pour les agents IA

```
1. Requête utilisateur
         ↓
2. Recherche sémantique dans les résumés
   └── "Quelles conversations parlent de jazz ?"
         ↓
3. Récupération du contexte enrichi
   ├── Résumés pertinents (mémoire long terme)
   ├── Messages récents (mémoire court terme)
   └── Métadonnées (préférences utilisateur)
         ↓
4. Appel à l'IA avec contexte complet
         ↓
5. Stockage de la réponse + embedding
         ↓
6. Mise à jour du résumé si nécessaire
```

## Indexes pour performances

```sql
-- Recherche rapide par utilisateur + activité
idx_conversations_user_active (user_id, is_active, last_message_at)

-- Recherche par type
idx_conversations_type_user (conversation_type, user_id)

-- Pagination messages
idx_chat_messages_conv_timestamp (conversation_id, message_timestamp)

-- Ordre des messages
idx_chat_messages_conv_sequence (conversation_id, sequence_number)
```

## RLS (Row Level Security)

```sql
-- Users can only see their own conversations
CREATE POLICY "Users view own conversations"
ON conversations FOR SELECT
USING (auth.uid() = user_id);

-- Users can only see messages from their conversations
CREATE POLICY "Users view own messages"
ON chat_messages FOR SELECT
USING (
    conversation_id IN (
        SELECT id FROM conversations WHERE user_id = auth.uid()
    )
);
```

## Migration depuis l'ancien système

L'ancienne table `conversations` stockait les messages en JSON :

```json
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

**Migration** :
1. Créer nouvelles tables
2. Migrer: JSON → lignes chat_messages
3. Générer résumés avec IA
4. Créer embeddings
5. Mettre à jour `external_id` pour référence

## Prochaines étapes

1. ✅ Modèles SQLAlchemy créés
2. ✅ Migration Alembic créée
3. ✅ Service ChatMemoryService créé
4. ⏳ Intégrer avec orchestrateur IA
5. ⏳ Worker Celery pour génération d'embeddings
6. ⏳ API endpoints pour gestion des conversations
7. ⏳ Frontend: interface de chat avec mémoire
