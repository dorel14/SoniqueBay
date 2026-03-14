# 📋 TODO - Traque runtime callable SQLAlchemy `utcnow` + correction ciblée

## ✅ Statut Global
- [x] **Plan créé et approuvé** (instrumentation runtime + correctif unique)
- [x] **1. docs/plans/TODO.md** ← Ce fichier (mis à jour)
- [ ] **2. backend/api/utils/database.py** (instrumentation temporaire du callable `onupdate`)
- [ ] **3. Exécution tests GraphQL ciblés avec `-W error::DeprecationWarning`**
- [ ] **4. Correction finale unique du callable datetime**
- [ ] **5. Re-validation tests ciblés**
- [ ] **6. Rapport final + Conventional Commit**

## Détails Techniques

### Fichiers à corriger (cette intervention)
| Fichier | Problème | Correction |
|---------|----------|------------|
| `backend/api/utils/database.py` | `TimestampMixin.date_modified.onupdate=datetime.datetime.utcnow` déclenche un warning converti en erreur | Instrumenter puis remplacer par un callable timezone-aware (`datetime.datetime.now(datetime.UTC)`) |

### Ordre d'exécution
```
1. Mettre à jour ce TODO.md ✅
2. Instrumenter temporairement le callable onupdate dans database.py
3. Lancer les 4 tests d’intégration GraphQL ciblés avec -W error::DeprecationWarning
4. Confirmer le callable exact et appliquer la correction unique définitive
5. Relancer les 4 tests ciblés
6. ✅ Clôture + message de commit Conventional Commit
```

**Notes :**
- Focus strict sur le point unique qui alimente `date_modified` via SQLAlchemy.
- Pas de refactor global des autres usages `datetime.utcnow` hors scope.
- Respect des règles repo (modification incrémentale, tests ciblés, logs via utilitaire projet).

---
*Généré par BlackboxAI - 2026*
