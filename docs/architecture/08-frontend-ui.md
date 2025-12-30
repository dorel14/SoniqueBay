## 1. Principes de conception

- Minimaliste, lisible et performant.
- Compatible écran tactile et navigation souris/clavier.
- Animations légères pour ne pas saturer le CPU.

## 2. Structure de l’interface

- **Bibliothèque musicale** : Arborescence Artiste → Album → Chansons.
- **Cartes d’albums** : Vignettes avec couverture, titre et bouton pour afficher les pistes.
- **Playqueue** : Liste des morceaux en lecture, ajout/suppression possible.
- **Recherche** : Barre simple avec filtres par genre, BPM et tags.

## 3. Exemple de carte d’album

```python
from nicegui import ui

def show_tracks(album_id):
    # Affiche les pistes de l’album sélectionné
    pass

with ui.row():
    ui.image(album.cover)
    ui.label(album.title)
    ui.button("Voir pistes", on_click=lambda: show_tracks(album.id))
```

## 4. Fonctionnalités avancées
** Transitions fluides : ui.page_transition() pour la navigation.

** WebSocket : Mise à jour en temps réel de la playqueue et métadonnées.

** Thème sombre/claire : Support complet via ui.theme().

## 5. Exemple de carte d’album
Lazy loading des images pour éviter le blocage du frontend.

Pré-calculer les vecteurs de recommandation pour réduire la charge CPU.

Décomposer l’interface en composants réutilisables.



