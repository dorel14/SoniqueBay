# Spécification d’implémentation – Système d’agents IA SoniqueBay

## 1. Objectif du document

Ce document décrit de manière complète et opérationnelle l’architecture du système
d’agents IA de SoniqueBay.

Il sert de **référence canonique** pour implémenter :
- la gestion des agents IA persistés en base de données
- l’orchestrateur central
- le routage, la clarification et le refus contrôlé
- l’intégration avec `pydantic_ai` et Ollama
- un dialogue temps réel 100 % WebSocket

Ce document est destiné à être utilisé par :
- un développeur humain
- ou un agent IA développeur chargé d’implémenter la solution backend

La couche UI (NiceGUI) est volontairement exclue.

---

## 2. Modèle de données Agent (source de vérité)

Les agents IA sont persistés dans la table `ai_agents`.

Le modèle de données constitue la **source unique de vérité** :
- aucun agent n’est défini en dur dans le code
- aucun YAML n’est requis au runtime
- tout agent est instancié dynamiquement depuis la base

---

## 3. Concept RTCROS appliqué aux agents

Chaque agent est défini par une structure RTCROS persistée en base de données.

RTCROS est utilisé pour construire dynamiquement le `system_prompt` de chaque agent.

### 3.1 Role

Décrit l’identité fonctionnelle de l’agent.

Exemples :
- assistant conversationnel général
- moteur de recherche musicale
- générateur de playlists
- routeur d’intentions

Le rôle ne décrit pas une action, mais une **position**.

---

### 3.2 Task

Décrit précisément la mission principale de l’agent.

Exemples :
- discuter avec l’utilisateur
- identifier une intention
- rechercher des entités musicales
- construire une playlist cohérente

La task est **unique et centrale**.

---

### 3.3 Constraints

Contraintes strictes que l’agent ne doit jamais violer.

Exemples :
- ne jamais halluciner des données absentes de la base
- ne pas effectuer d’action sans tool
- rester concis et explicite

Les contraintes priment toujours sur la task.

---

### 3.4 Rules

Règles comportementales et logiques.

Exemples :
- poser une question si une information est manquante
- refuser si la demande sort du périmètre
- privilégier la clarification au hasard

Les rules guident le raisonnement interne.

---

### 3.5 Output Schema

Description **conceptuelle** du format de sortie attendu.

Ce champ ne contient pas de code mais une description exploitable par le LLM.

Exemples :
- texte naturel
- JSON structuré
- mixte (texte + actions possibles)

Ce champ est utilisé pour :
- structurer la réponse
- guider le streaming
- faciliter l’affichage côté client

---

### 3.6 State Strategy

Décrit la stratégie de gestion des états internes de l’agent.

Ce champ définit :
- quand clarifier
- quand agir
- quand refuser
- quand conclure

---

## 4. États conversationnels standardisés

Tous les agents doivent produire des réponses associées à un état explicite.

### États autorisés

- `thinking` : raisonnement interne (non affiché au client)
- `clarifying` : question posée à l’utilisateur
- `acting` : appel de tool ou action backend
- `done` : réponse finale
- `refused` : refus contrôlé et expliqué

Ces états sont utilisés par :
- l’orchestrateur
- le client WebSocket
- le scoring et l’apprentissage futur

---

## 5. Création des agents au démarrage de l’application

### 5.1 Principe général

Au démarrage de l’application backend :

1. Vérifier les agents existants en base
2. Créer automatiquement les agents critiques manquants
3. Garantir un système fonctionnel minimal sans configuration manuelle

Cette étape est appelée **bootstrap des agents**.

---

### 5.2 Agents créés par défaut

#### Orchestrator Agent

- Nom : `orchestrator`
- Rôle : routage d’intentions
- Task : identifier l’agent le plus pertinent
- Output : JSON (agent, confidence)
- Tools : aucun

Cet agent ne répond jamais directement à l’utilisateur.

---

#### Smalltalk Agent

- Nom : `smalltalk_agent`
- Rôle : discussion générale
- Task : dialoguer naturellement avec l’utilisateur
- Tools : aucun
- Output : texte
- Utilisé pour :
  - tests UI
  - validation du pipeline complet
  - fallback conversationnel

---

## 6. AgentLoader

### 6.1 Responsabilités

Le `AgentLoader` est responsable de :

- charger les agents `enabled=True`
- résoudre l’héritage via `base_agent`
- fusionner les champs RTCROS
- instancier les objets `pydantic_ai.Agent`
- appliquer les paramètres runtime (temperature, top_p, num_ctx)

---

### 6.2 Héritage et spécialisation

Si `base_agent` est défini :

- le parent est chargé en premier
- les champs non définis sont hérités
- les champs définis surchargent le parent

Cela permet :
- agents spécialisés
- auto-création future
- tuning progressif

---

## 7. Orchestrator

### 7.1 Rôle de l’orchestrateur

L’orchestrateur est le **point d’entrée unique** du système IA.

Il :
- reçoit les messages utilisateur
- maintient le contexte conversationnel
- appelle l’agent orchestrator
- propose plusieurs agents candidats
- applique un scoring
- déclenche clarification ou refus si nécessaire
- stream la réponse finale

---

### 7.2 Ce que l’orchestrateur ne fait pas

- aucune logique métier musicale
- aucune requête SQL directe
- aucune logique UI
- aucune génération de contenu final

Il coordonne, il ne décide pas seul.

---

## 8. IntentRouter (routage volontairement limité)

### 8.1 Philosophie

Le router doit rester simple et déterministe.

Il ne doit pas :
- contenir de logique métier
- éliminer prématurément des agents
- produire une décision finale

---

### 8.2 Responsabilités

Le router doit :

- proposer N agents candidats
- retourner un score brut par agent
- permettre un refus contrôlé
- rester extensible pour du scoring avancé

---

## 9. Scoring et confidence

Chaque agent est associé à :

- un score brut de pertinence
- un confidence score

L’orchestrateur peut alors :

- accepter la réponse
- demander une clarification
- refuser la demande

---

## 10. Clarification

Un agent doit entrer en état `clarifying` si :

- des informations essentielles manquent
- la demande est ambiguë
- la confiance est insuffisante

Dans ce cas :
- une question claire est posée
- aucun autre agent n’est appelé
- le contexte est mis à jour

---

## 11. Refus contrôlé

Si aucun agent n’est pertinent :

- état = `refused`
- message explicatif obligatoire
- suggestion de reformulation si possible

Un refus ne doit jamais être silencieux.

---

## 12. Tools (actions backend)

### 12.1 Principe

Les tools sont déclarés via un décorateur Python.

Un tool peut :
- appeler un service backend
- appeler un endpoint interne
- effectuer une action métier

---

### 12.2 Sécurité

- un agent ne peut appeler que les tools listés dans son champ `tools`
- aucune action backend sans tool explicite

---

## 13. Streaming WebSocket – Contrat Orchestrator → Client

### 13.1 Transport

- WebSocket uniquement
- une connexion par utilisateur
- contexte conversationnel par session

---

### 13.2 Types de messages streamés

Chaque message envoyé au client est un JSON contenant :

- `type` : dialogue | action | state | error
- `state` : thinking | clarifying | acting | done | refused
- `content` : texte ou JSON structuré
- `confidence` : optionnel

---

## 14. Contexte conversationnel

Le contexte conserve :

- historique user / agent
- dernier intent
- agent actif
- métriques futures (optionnelles)

Le contexte est :
- en mémoire dans un premier temps
- persistant ultérieurement si nécessaire

---

## 15. Évolutions prévues (hors scope immédiat)

- apprentissage des scores
- auto-tuning des paramètres LLM
- auto-création d’agents spécialisés
- A/B routing
- feedback utilisateur
- persistance longue durée des conversations

---

## 16. Résumé conceptuel

- Les agents sont des entités métiers persistées
- RTCROS est le socle de tout comportement
- L’orchestrateur coordonne sans centraliser l’intelligence
- Les agents peuvent clarifier ou refuser
- Le client reçoit des états explicites
- Le système est conçu pour évoluer sans refactor majeur

---

Fin du document.
