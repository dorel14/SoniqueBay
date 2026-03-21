# Template : Rapport de Tests

## 📋 Informations Générales

- **Date** : [DATE]
- **Testeur** : [NOM]
- **Phase** : [NUMÉRO] ([NOM PHASE])
- **Environnement** : [LOCAL/DOCKER]

---

## 📊 Résumé

- **Tests exécutés** : [NOMBRE]
- **Tests réussis** : [NOMBRE]
- **Tests échoués** : [NOMBRE]
- **Taux de réussite** : [POURCENTAGE]%

---

## 🧪 Tests Unitaires TaskIQ

- **Tests exécutés** : [NOMBRE]
- **Tests réussis** : [NOMBRE]
- **Tests échoués** : [NOMBRE]
- **Détails** : [LIEN VERS FICHIER]

### Tests Échoués (si applicable)
| # | Test | Erreur | Cause Probable |
|---|------|--------|----------------|
| 1 | [TEST] | [ERREUR] | [CAUSE] |
| 2 | [TEST] | [ERREUR] | [CAUSE] |

---

## 🔄 Tests Unitaires Celery (Non-Régression)

- **Tests exécutés** : [NOMBRE]
- **Tests réussis** : [NOMBRE]
- **Tests échoués** : [NOMBRE]
- **Régression** : [OUI/NON]
- **Détails** : [LIEN VERS FICHIER]

### Tests Échoués (si applicable)
| # | Test | Erreur | Cause Probable |
|---|------|--------|----------------|
| 1 | [TEST] | [ERREUR] | [CAUSE] |
| 2 | [TEST] | [ERREUR] | [CAUSE] |

---

## 🔗 Tests d'Intégration Workers (Non-Régression)

- **Tests exécutés** : [NOMBRE]
- **Tests réussis** : [NOMBRE]
- **Tests échoués** : [NOMBRE]
- **Régression** : [OUI/NON]
- **Détails** : [LIEN VERS FICHIER]

### Tests Échoués (si applicable)
| # | Test | Erreur | Cause Probable |
|---|------|--------|----------------|
| 1 | [TEST] | [ERREUR] | [CAUSE] |
| 2 | [TEST] | [ERREUR] | [CAUSE] |

---

## 🐳 Démarrage Docker

- **Construction images** : [RÉUSSI/ÉCHOUÉ]
- **Démarrage services** : [RÉUSSI/ÉCHOUÉ]
- **Logs TaskIQ** : [OK/ERREUR]
- **Logs Celery** : [OK/ERREUR]
- **Santé services** : [OK/ERREUR]

### Détails des Erreurs (si applicable)
| Service | Erreur | Cause Probable |
|---------|--------|----------------|
| taskiq-worker | [ERREUR] | [CAUSE] |
| celery-worker | [ERREUR] | [CAUSE] |

---

## 🚨 Anomalies Détectées

| # | Test | Erreur | Statut | Solution |
|---|------|--------|--------|----------|
| 1 | [TEST] | [ERREUR] | [OUVERT/CORRIGÉ] | [SOLUTION] |
| 2 | [TEST] | [ERREUR] | [OUVERT/CORRIGÉ] | [SOLUTION] |

---

## 📈 Métriques de Performance (si applicable)

- **Temps d'exécution moyen** : [SECONDES]
- **Mémoire utilisée** : [MO]
- **Latence p50** : [MS]
- **Latence p95** : [MS]

---

## ✅ Conclusion

- **Phase validée** : [OUI/NON]
- **Prêt pour phase suivante** : [OUI/NON]
- **Recommandations** : [LISTE]

---

## 📝 Signatures

- **Testeur** : [NOM] — [DATE]
- **Lead Développeur** : [NOM] — [DATE]

---

## 📎 Pièces Jointes

- [ ] Fichier de résultats tests unitaires
- [ ] Fichier de résultats tests d'intégration
- [ ] Logs Docker
- [ ] Captures d'écran (si applicable)

---

*Dernière mise à jour : 2026-03-20*
*Version : 1.0*
