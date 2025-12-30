# Spécification Technique — Système d’Agents IA SoniqueBay

## Objectif du document

Ce document définit **de manière exhaustive et non ambiguë** la spécification technique du système
d’agents IA de SoniqueBay.

Il est destiné :
- à un développeur backend
- ou à un agent IA codeur

afin de générer **l’intégralité du code** nécessaire :
- orchestrateur
- runtime
- agents pydantic_ai
- outils
- seed de base en base de données
- contrat WebSocket

sans aller-retour ni clarification supplémentaire.

---

## Contraintes Fondamentales

- Utilisation exclusive de **pydantic_ai**
- Communication **100% WebSocket**
- Backend FastAPI
- Modèles d’agents persistés en base PostgreSQL
- Pas de YAML
- Pas de NiceGUI dans ce périmètre
- Ollama utilisé via `OpenAIChatModel + OllamaProvider`
- Le système doit être extensible sans redéploiement

---

## Modèle de Données Agent (Base de Données)

### Table `ai_agents`

Chaque agent IA est persisté dans la base de données selon le modèle suivant :

- `id` : identifiant
- `name` : nom unique de l’agent
- `model` : modèle Ollama utilisé
- `enabled` : activation de l’agent
- `base_agent` : nom de l’agent parent (optionnel)

### Champs RTCROS (obligatoires)

- `role` : rôle fonctionnel de l’agent
- `task` : tâche principale
- `constraints` : limitations explicites
- `rules` : règles impératives
- `output_schema` : format de sortie attendu
- `state_strategy` : stratégie d’état d’exécution

### Métadonnées

- `tools` : liste des outils autorisés
- `tags` : catégorisation libre
- `version` : version fonctionnelle

### Paramètres LLM runtime

- `temperature`
- `top_p`
- `num_ctx`

---

## Concept RTCROS

RTCROS est le **contrat cognitif minimal** de chaque agent.

Chaque agent DOIT être instanciable uniquement à partir de ces champs.

| Champ | Rôle |
|------|-----|
| role | Identité de l’agent |
| task | Objectif principal |
| constraints | Ce que l’agent ne doit pas faire |
| rules | Comportements obligatoires |
| output_schema | Format strict de sortie |
| state_strategy | Gestion des états |

---

## États d’Exécution Normalisés

Tous les agents doivent respecter ces états :

- `thinking` : raisonnement interne
- `clarifying` : demande de précision utilisateur
- `acting` : appel d’outil
- `streaming` : réponse progressive
- `done` : réponse finale
- `refused` : refus contrôlé

---

## Agents de Base Obligatoires (Seed)

Ces agents DOIVENT être créés automatiquement au démarrage de l’application
s’ils n’existent pas déjà en base.

### Agent : orchestrator

- `name` : orchestrator
- `role` : routeur d’intentions
- `task` : identifier l’agent le plus pertinent
- `constraints` : ne jamais répondre à l’utilisateur final
- `rules` : toujours retourner un JSON valide
- `output_schema` : JSON { agent: string, confidence: float }
- `state_strategy` : routing
- `tools` : []

---

### Agent : smalltalk

- `name` : smalltalk
- `role` : discussion générale
- `task` : dialoguer naturellement avec l’utilisateur
- `constraints` : aucune action métier
- `rules` : réponse fluide et naturelle
- `output_schema` : texte libre
- `state_strategy` : streaming
- `tools` : []

Cet agent sert de **référence fonctionnelle** et de **test UI**.

---

### Agent : search

- `name` : search
- `role` : interprète de requêtes musicales
- `task` : transformer une demande utilisateur en requête structurée
- `constraints` : ne pas accéder directement à la base
- `rules` : sortie strictement structurée
- `output_schema` : SearchQuery (Pydantic)
- `state_strategy` : acting
- `tools` : ["search_music"]

---

## Seed System

### Objectif

Garantir que les agents de base existent toujours.

### Règles

- Exécuté au démarrage
- Idempotent
- Ne jamais écraser un agent existant
- Centralisé dans un module dédié

### Logique

- Charger la liste des agents requis
- Vérifier leur existence par `name`
- Créer uniquement les absents

---

## Orchestrator — Responsabilités

L’orchestrator est une **classe runtime**, distincte de l’agent `orchestrator`.

Il est responsable de :

- réception des messages utilisateur
- gestion du contexte conversationnel
- appel de l’agent orchestrator (intention)
- routage vers les agents candidats
- scoring et sélection
- gestion de la clarification
- gestion du refus contrôlé
- streaming ou réponse finale

---

## Intent Router

Le router est volontairement **minimaliste**.

Il doit uniquement :

- proposer N agents candidats
- fournir un score brut par agent

Il NE DOIT PAS :
- décider seul
- gérer la confiance finale
- exécuter d’agent

---

## Scoring & Confidence

- Le score brut est normalisé
- Une `confidence` finale est calculée
- En dessous d’un seuil configurable :
  - passage en `refused`

Exemple de refus contrôlé :

- agent = null
- confidence < seuil
- message explicite

---

## Clarification

Si un agent ne dispose pas d’informations suffisantes :

- état = `clarifying`
- une seule question claire est émise
- l’exécution est suspendue
- la réponse utilisateur relance l’agent

Exemple :
« Souhaitez-vous une playlist calme ou énergique ? »

---

## Tools

### Principes

- Déclarés via décorateur
- Appelables uniquement par les agents autorisés
- Peuvent encapsuler :
  - services backend
  - endpoints internes
  - requêtes PostgreSQL full-text

---

## Recherche Sémantique & Full-Text

Le système doit permettre à un agent de distinguer :

- « cherche un album de Michael Jackson »
- « cherche des morceaux funk de Prince »

Responsabilité :
- interprétation → agent
- exécution → tool de recherche

---

## WebSocket — Contrat Backend → Client

### Message Unifié

Tous les messages WebSocket respectent ce format :

- `type`
- `agent`
- `state`
- `payload`

---

### Streaming

- Les tokens Ollama sont **bufferisés**
- Les messages sont envoyés par chunks cohérents
- Jamais caractère par caractère

---

## Formats de Réponse par Agent

| Agent | Format |
|-----|------|
| smalltalk | streaming texte |
| orchestrator | JSON |
| search | JSON structuré |
| playlist | JSON + actions |

---

## Contexte Conversationnel

- Un contexte par utilisateur
- Persisté (DB ou Redis)
- Injecté à chaque appel agent
- Nettoyage configurable

---

## Livrables Attendus

Le développeur ou agent IA doit produire :

- orchestrator runtime
- intent router
- scoring engine
- loader d’agents depuis la DB
- seed agents
- outils
- schémas Pydantic
- client Ollama propre

---

## Objectif Qualité

- Aucun agent hardcodé
- Agents modifiables en base
- Ajout d’agent sans redéploiement
- Testable sans UI
- Extensible et observable

---

## Fin de la Spécification
