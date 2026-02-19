# Product Context

## La Mission
Créer un système musical autonome capable de scanner, indexer, jouer et recommander de la musique sur du matériel modeste (Raspberry Pi 4), sans dépendre du cloud pour ses fonctions vitales.

## Expérience Utilisateur (UX)
- **Fluidité** : L'interface ne doit jamais bloquer. Les traitements longs (scan, analyse) sont déportés en arrière-plan et notifiés via SSE (Server-Sent Events).
- **Accessibilité** : Interface minimaliste, compatible tactile ("Touch-friendly") et responsive.
- **Temps Réel** : La file de lecture et l'état du lecteur sont synchronisés instantanément via WebSocket.
- **Visualisation** : Navigation par arbre (TreeView) et cartes d'albums avec chargement différé (Lazy Loading).

## Problèmes Résolus
- Gestion centralisée d'une bibliothèque musicale locale volumineuse.
- Suppression des latences d'interface sur matériel limité grâce à l'architecture asynchrone.
- Découverte musicale intelligente (recommandations) hors ligne (ou hybride).

## Évolutions Futures (Roadmap)
- Recherche hybride (SQL + Vectorielle).
- Intégrations externes (Last.fm, ListenBrainz, Napster, Soulseek).
- Lecture "Gapless" et transitions améliorées entre les pistes.