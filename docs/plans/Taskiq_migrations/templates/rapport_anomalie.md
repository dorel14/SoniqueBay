# Template : Rapport d'Anomalie

## 📋 Informations Générales

- **Numéro d'anomalie** : [NUMÉRO]
- **Date de détection** : [DATE]
- **Date de résolution** : [DATE]
- **Phase** : [NUMÉRO] ([NOM PHASE])
- **Testeur** : [NOM]
- **Développeur** : [NOM]

---

## 🔍 Description de l'Anomalie

### Test Échoué
- **Nom du test** : [NOM DU TEST]
- **Fichier** : [CHEMIN FICHIER]
- **Ligne** : [NUMÉRO LIGNE]

### Message d'Erreur
```
[MESSAGE D'ERREUR COMPLET]
```

### Contexte
- **Environnement** : [LOCAL/DOCKER]
- **Configuration** : [DESCRIPTION]
- **Données de test** : [DESCRIPTION]

---

## 🔬 Analyse

### Cause Probable
[DESCRIPTION DÉTAILLÉE DE LA CAUSE]

### Impact
- **Type** : [BLOQUANT/MAJEUR/MINEUR]
- **Fréquence** : [SYSTÉMATIQUE/INTERMITTENT]
- **Portée** : [DESCRIPTION DE L'IMPACT]

### Reproduction
1. [ÉTAPE 1]
2. [ÉTAPE 2]
3. [ÉTAPE 3]

---

## 🛠️ Solution

### Correction Appliquée
[DESCRIPTION DÉTAILLÉE DE LA CORRECTION]

### Fichiers Modifiés
| Fichier | Modification |
|---------|--------------|
| [FICHIER 1] | [DESCRIPTION] |
| [FICHIER 2] | [DESCRIPTION] |

### Tests Ajoutés
| Test | Description |
|------|-------------|
| [TEST 1] | [DESCRIPTION] |
| [TEST 2] | [DESCRIPTION] |

---

## ✅ Validation

### Tests Re-exécutés
- [ ] Test unitaire : [RÉUSSI/ÉCHOUÉ]
- [ ] Test d'intégration : [RÉUSSI/ÉCHOUÉ]
- [ ] Test de non-régression : [RÉUSSI/ÉCHOUÉ]

### Résultat
- **Correction validée** : [OUI/NON]
- **Régression introduite** : [OUI/NON]
- **Performance impactée** : [OUI/NON]

---

## 📊 Métriques

### Avant Correction
- **Temps d'exécution** : [SECONDES]
- **Mémoire utilisée** : [MO]
- **Taux de réussite** : [POURCENTAGE]%

### Après Correction
- **Temps d'exécution** : [SECONDES]
- **Mémoire utilisée** : [MO]
- **Taux de réussite** : [POURCENTAGE]%

---

## 📝 Statut

- **Statut** : [OUVERT/CORRIGÉ/FERMÉ]
- **Validé par** : [NOM]
- **Date de validation** : [DATE]

---

## 📎 Pièces Jointes

- [ ] Logs d'erreur
- [ ] Captures d'écran
- [ ] Code modifié
- [ ] Tests ajoutés

---

## 🔄 Suivi

### Actions de Suivi
- [ ] [ACTION 1]
- [ ] [ACTION 2]
- [ ] [ACTION 3]

### Prochaine Revue
- **Date** : [DATE]
- **Responsable** : [NOM]

---

*Dernière mise à jour : 2026-03-20*
*Version : 1.0*
