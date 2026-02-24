# TODO - Correction vulnérabilité Prompt Injection ChatML

## Objectif
Corriger la vulnérabilité de sécurité dans `backend/ai/models/kobold_model.py` où les marqueurs ChatML ne sont pas sanitizés, permettant une injection de prompt.

## Étapes

- [x] Analyser la méthode `_format_messages` et identifier les points de vulnérabilité
- [x] Créer la méthode helper `_sanitize_chatml_markers` pour échapper les marqueurs
- [x] Modifier `_format_messages` pour appliquer la sanitisation sur le contenu utilisateur
- [x] Ajouter des commentaires de sécurité
- [x] Tester la correction

## Détails de l'implémentation

### Méthode `_sanitize_chatml_markers`
- Échapper les marqueurs `<|im_start|>` et `</s>` en les remplaçant par des versions échappées
- Appliquer cette méthode sur tout contenu provenant de l'utilisateur (user-prompt, retry-prompt)

### Modification de `_format_messages`
- Appeler `_sanitize_chatml_markers` sur le contenu avant de l'intégrer au format ChatML
- Conserver le comportement existant pour les autres types de messages (system, assistant, tool)

## Fichier concerné
- `backend/ai/models/kobold_model.py`

## Validation
- Les marqueurs ChatML dans le contenu utilisateur doivent être échappés
- Le contenu légitime ne doit pas être affecté
