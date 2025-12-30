# Spécification Technique — Système d’Agents IA SoniqueBay

## Objectif du document

Ce document décrit de manière complète, cohérente et exploitable la conception du système d’agents IA de SoniqueBay.  
Il sert de **référence unique** pour permettre à un développeur ou à un agent IA codeur de générer l’ensemble du code nécessaire **sans aller-retour fonctionnel**.

Le périmètre couvre :
- orchestrateur
- runtime d’agents
- modèles de données
- seed en base de données
- routage, scoring, clarification
- outils (tools)
- contrat WebSocket
- intégration Ollama via pydantic_ai

---

## Contraintes Fondamentales

- Backend FastAPI
- Communication **100 % WebSocket**
- Utilisation exclusive de **pydantic_ai**
- LLM via **Ollama** (`OpenAIChatModel` + `OllamaProvider`)
- Agents persistés en base PostgreSQL
- Pas de YAML
- Pas de NiceGUI dans ce périmètre
- Architecture extensible sans redéploiement

---

## Modèle de Données — Agent

### Table `ai_agents`

Chaque agent IA est défini et persisté selon le modèle suivant :

- `id` : identifiant unique
- `name` : nom unique de l’agent
- `model` : nom du modèle Ollama
- `enabled` : activation de l’agent
- `base_agent` : agent parent (optionnel)

### Champs RTCROS (obligatoires)

- `role` : identité fonctionnelle de l’agent
- `task` : objectif principal
- `constraints` : limitations explicites
- `rules` : règles impératives
- `output_schema` : format strict de sortie
- `state_strategy` : stratégie de gestion d’état

### Métadonnées

- `tools` : liste des outils autorisés
- `tags` : catégorisation libre
- `version` : version fonctionnelle

### Paramètres LLM Runtime

- `temperature`
- `top_p`
- `num_ctx`

---

## Concept RTCROS

RTCROS constitue le **contrat cognitif minimal** d’un agent.

Chaque agent doit être instanciable **uniquement** à partir de ces champs.

| Champ | Description |
|-----|------------|
| Role | Qui est l’agent |
| Task | Ce qu’il doit accomplir |
| Constraints | Ce qu’il ne doit jamais faire |
| Rules | Règles impératives |
| Output Schema | Format de sortie strict |
| State Strategy | Gestion des états |

---

## États d’Exécution Normalisés

Tous les agents doivent respecter les états suivants :

- `thinking` : raisonnement interne
- `clarifying` : demande de précision utilisateur
- `acting` : appel d’outil
- `streaming` : réponse progressive
- `done` : réponse finale
- `refused` : refus contrôlé

---

## Agents de Base Obligatoires (Seed)

Ces agents doivent être créés automatiquement au démarrage de l’application s’ils n’existent pas.

### Agent : orchestrator

- `name` : orchestrator
- `role` : routeur d’intentions
- `task` : identifier l’agent le plus pertinent
- `constraints` : ne jamais répondre directement à l’utilisateur
- `rules` : toujours retourner un JSON valide
- `output_schema` : `{ agent: string, confidence: float }`
- `state_strategy` : routing
- `tools` : []

---

### Agent : smalltalk

- `name` : smalltalk
- `role` : discussion générale
- `task` : dialoguer naturellement avec l’utilisateur
- `constraints` : aucune action métier
- `rules` : conversation fluide et naturelle
- `output_schema` : texte libre
- `state_strategy` : streaming
- `tools` : []

Cet agent sert de **référence fonctionnelle** et de **test UI**.

---

### Agent : search

- `name` : search
- `role` : interprète de requêtes musicales
- `task` : transformer une demande utilisateur en requête structurée
- `constraints` : pas d’accès direct à la base
- `rules` : sortie strictement structurée
- `output_schema` : modèle Pydantic `SearchQuery`
- `state_strategy` : acting
- `tools` : ["search_music"]

---

## Seed System

### Objectif

Garantir la présence des agents de base.

### Règles

- Exécuté au démarrage
- Idempotent
- Ne jamais écraser un agent existant
- Centralisé dans un module dédié

### Logique

1. Charger la liste des agents requis
2. Vérifier leur existence par `name`
3. Créer uniquement les agents absents

---

## Orchestrator (Runtime)

L’orchestrator est une **classe runtime**, distincte de l’agent `orchestrator`.

### Responsabilités

- Réception des messages utilisateur
- Gestion du contexte conversationnel
- Appel de l’agent orchestrator (intention)
- Proposition d’agents candidats
- Scoring et sélection
- Gestion de la clarification
- Refus contrôlé
- Streaming ou réponse finale

---

## Intent Router

Le router est volontairement minimal.

### Rôle

- Proposer N agents candidats
- Retourner un score brut par agent

### Limites

- Pas de décision finale
- Pas de confiance
- Pas d’exécution d’agent

---

## Scoring & Confidence

- Le score brut est normalisé
- Une `confidence` finale est calculée
- En dessous d’un seuil configurable → `refused`

### Refus contrôlé

- `agent = null`
- `confidence < seuil`
- Message explicite retourné au client

---

## Clarification

Si un agent manque d’informations :

- état = `clarifying`
- une seule question claire
- suspension de l’exécution
- reprise après réponse utilisateur

---

## Tools

### Principes

- Déclarés via décorateur
- Associés explicitement aux agents
- Peuvent encapsuler :
  - services backend
  - endpoints internes
  - recherche PostgreSQL full-text

---

## Recherche Sémantique & Full-Text

Les agents doivent distinguer les intentions :

- « chercher un album de Michael Jackson »
- « chercher des morceaux funk de Prince »

### Répartition

- Compréhension : agent
- Exécution : tool de recherche

---

## WebSocket — Contrat Backend → Client

### Format Unifié

Chaque message WebSocket contient :

- `type`
- `agent`
- `state`
- `payload`

---

### Streaming

- Les tokens Ollama sont **bufferisés**
- Envoi par chunks cohérents
- Jamais caractère par caractère

---

## Formats de Réponse par Agent

| Agent | Format |
|-----|------|
| smalltalk | texte streamé |
| orchestrator | JSON |
| search | JSON structuré |
| playlist | JSON + actions |

---

## Contexte Conversationnel

- Un contexte par utilisateur
- Persisté (DB ou Redis)
- Injecté à chaque appel agent
- Politique de nettoyage configurable

---

## Livrables Attendus

Le système doit produire :

- orchestrator runtime
- intent router
- moteur de scoring
- loader DB → agents
- seed d’agents
- décorateur tools
- schémas Pydantic
- client Ollama propre

---

## Objectifs Qualité

- Aucun agent hardcodé
- Agents modifiables en base
- Ajout sans redéploiement
- Testable sans UI
- Architecture extensible et observable

---

## Fin de la Spécification
