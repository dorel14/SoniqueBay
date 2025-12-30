
---

## 4. Contrat de sortie Orchestrator → Client

Chaque message streamé via WebSocket suit un format structuré :

- **Types de messages** :
  - `text` : dialogue normal
  - `tool_call` : action à exécuter
  - `clarification` : question pour obtenir informations manquantes
  - `refusal` : agent refuse d’exécuter la demande
- **États** :
  - `thinking` : agent traite le message
  - `clarifying` : attente d’informations supplémentaires
  - `acting` : exécution d’un tool
  - `done` : réponse finale ou refus contrôlé
- **Structure JSON typique** :
  - `type`: `text` | `tool_call` | `clarification` | `refusal`
  - `state`: `thinking` | `clarifying` | `acting` | `done`
  - `content`: texte ou JSON (selon type)
  - `tool`: identifiant de l’action (si tool_call)
  - `tool_args`: arguments (si tool_call)
  - `clarification`: détails (si clarifying)
  - `confidence`: float 0..1 (optionnel)

Ce contrat permet à l’UI ou à un client automatisé de gérer correctement toutes les réponses.

---

## 5. Contexte conversationnel

- **Scope** : par utilisateur
- **Persistant** : possibilité de sauvegarder en base pour reprise
- **Contenu** :
  - `messages` : liste des échanges (user et agent)
  - `waiting_for` : champs ou informations manquantes
  - `collected` : informations déjà fournies
  - `last_agent` : dernier agent actif
  - `last_intent` : dernière intention identifiée
- **Usage** :
  - Maintien du dialogue multi-tours
  - Gestion automatique des clarifications
  - Relance de l’agent après collecte
  - Suivi de la confiance / confidence score

---

## 6. Agents IA

### 6.1 Principes

- Un agent a une responsabilité unique
- Ne déclenche jamais une action
- Retourne uniquement des messages conformes au contrat
- Peut demander des clarifications si données manquantes
- Dispose d’un **Agent Capability Model** :
  - Liste des tâches qu’il peut exécuter
  - Liste des types d’inputs requis
  - Limites et refus contrôlés
- Retourne un **confidence score** estimant la fiabilité de sa réponse

### 6.2 Agents de base

- **OrchestratorAgent** : identifie l’intention, propose N agents candidats avec score brut
- **SearchAgent** : recherche artistes, albums, morceaux
- **PlaylistAgent** : génère des playlists, déclenche clarification si critères insuffisants
- **ActionAgent** : décrit et déclenche les actions backend via tools
- **SmalltalkAgent** : gère le dialogue informel et déduit le mood utilisateur

### 6.3 Sous-agents spécialisés

- Création à partir d’un agent parent
- Héritent du prompt parent
- Spécialisent uniquement certaines tâches ou critères
- Maintiennent un Agent Capability Model adapté
- Clarification spécifique pour les cas spécialisés

---

## 7. Système de clarification

- L’agent retourne un message `clarifying` si certaines informations sont manquantes
- L’orchestrateur suspend l’exécution et attend la réponse
- Les réponses sont intégrées dans `collected` du contexte
- L’agent est relancé automatiquement avec les nouvelles informations
- Remplace les formulaires et menus UI

---

## 8. Tools & Actions

- Les actions sont déclarées via un **décorateur @tool**
- Enregistrées dans le **ToolRegistry**
- Utilisées par les agents via `tool_call`
- Les agents **ne peuvent pas exécuter directement** les actions
- Chaque tool a :
  - un nom unique
  - une description
  - une liste d’agents autorisés
  - un handler (endpoint ou fonction backend)

---

## 9. IntentRouter

- Limité à proposer N agents candidats
- Retourne un score brut pour chaque candidat
- N’interfère pas dans la décision finale
- Orchestrateur utilise le score et le contexte pour choisir l’agent à exécuter
- Sert de base pour scoring et apprentissage futur

---

## 10. Scoring et apprentissage

- Permet de prioriser les agents les plus efficaces
- Paramètres pris en compte :
  - réussite des tâches
  - nombre de clarifications nécessaires
  - feedback implicite ou explicite
  - confidence score
- Ne nécessite pas de ML lourd pour la première version

---

## 11. Streaming WebSocket

- Messages envoyés au fil de l’eau
- Chaque chunk peut être :
  - texte de dialogue
  - instruction tool
  - clarification
  - refus contrôlé
- Permet UX fluide et perception de réactivité

---

## 12. Persistance

- Agents et sous-agents
- Prompts système
- Actions disponibles
- Scores de routage et confidence
- Historique minimal de conversations

YAML utilisé uniquement pour migration initiale.

---

## 13. Création dynamique d’agents

- Par dialogue ou interface backend
- Création de sous-agents spécialisés
- Héritage du parent + spécialisation des capacités
- Mise à jour automatique du contexte et des capacités
- Ré-enregistrement dans la BDD

---

## 14. États spéciaux

- `refusal` : l’agent refuse la demande pour cause :
  - impossible
  - action non permise
  - information manquante critique
- Doit être géré par orchestrateur et client

---

## 15. Évolutions futures

- Auto-tuning des paramètres modèles
- Routage adaptatif
- Mémoire long terme
- Agents auto-générés
- Feedback utilisateur
- Gestion avancée du confidence score

---

## 16. Résumé

- Dialogue naturel remplaçant les boutons UI
- Clarification systématique pour données manquantes
- Agents spécialisés et capables d’auto-organisation
- Outils/actions déclenchés via orchestrateur
- Scoring et confidence pour apprentissage futur
- Streaming WebSocket structuré pour l’UI
- Base solide pour évolution et extension

---
