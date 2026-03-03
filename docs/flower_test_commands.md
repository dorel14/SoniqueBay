# Commandes de Test et Validation - Correction Permissions Flower

## 🧪 Commandes de Test Local (Windows PowerShell)

```powershell
# =============================================================================
# VALIDATION COMPLÈTE DES CORRECTIONS FLOWER
# =============================================================================

Write-Host "🔍 === VALIDATION DES CORRECTIONS FLOWER ===" -ForegroundColor Cyan
Write-Host "Test du script flower_entrypoint_fixed.sh amélioré" -ForegroundColor Yellow
Write-Host ""

# 1. Vérification de la syntaxe du script
Write-Host "1️⃣ Vérification de la syntaxe du script Flower..." -ForegroundColor Green
sh -n scripts/flower_entrypoint_fixed.sh
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Syntaxe du script Flower correcte" -ForegroundColor Green
} else {
    Write-Host "❌ Erreur de syntaxe dans le script Flower" -ForegroundColor Red
    exit 1
}

# 2. Test des corrections de permissions
Write-Host "`n2️⃣ Test des corrections de permissions..." -ForegroundColor Yellow
Write-Host "Exécution du script de test amélioré..." -ForegroundColor Gray
sh scripts/test_flower_permissions_fix.sh

# 3. Affichage du contenu du script corrigé
Write-Host "`n3️⃣ Extrait des améliorations du script..." -ForegroundColor Yellow
Write-Host "Fonction log() avec fallback robuste :" -ForegroundColor Cyan
Get-Content scripts/flower_entrypoint_fixed.sh | Select-Object -First 15

Write-Host "`nFonction setup_data_permissions() améliorée :" -ForegroundColor Cyan
Get-Content scripts/flower_entrypoint_fixed.sh | Select-Object -Lines 50..70

# 4. Vérification des nouveaux fichiers
Write-Host "`n4️⃣ Vérification des fichiers créés..." -ForegroundColor Yellow
if (Test-Path "docs/flower_permissions_fix.md") {
    Write-Host "✅ Documentation mise à jour : docs/flower_permissions_fix.md" -ForegroundColor Green
} else {
    Write-Host "❌ Documentation manquante" -ForegroundColor Red
}

if (Test-Path "scripts/test_flower_permissions_fix.sh") {
    Write-Host "✅ Script de test mis à jour : scripts/test_flower_permissions_fix.sh" -ForegroundColor Green
} else {
    Write-Host "❌ Script de test manquant" -ForegroundColor Red
}

Write-Host "`n🎉 === VALIDATION TERMINÉE ===" -ForegroundColor Cyan
```

## 🚀 Commandes de Déploiement (Raspberry Pi)

```powershell
# =============================================================================
# DÉPLOIEMENT SUR RASPBERRY PI
# =============================================================================

Write-Host "🚀 === DÉPLOIEMENT DES CORRECTIONS FLOWER ===" -ForegroundColor Cyan

# 1. Copier les scripts corrigés vers le Raspberry Pi
Write-Host "1️⃣ Copie des scripts corrigés vers le Raspberry Pi..." -ForegroundColor Yellow
Write-Host "Sur le Raspberry Pi ou via SSH :" -ForegroundColor Gray
Write-Host "scp scripts/flower_entrypoint_fixed.sh user@raspberry-pi:/path/to/soniquebay/scripts/" -ForegroundColor Cyan

# 2. Redémarrer le conteneur Flower
Write-Host "`n2️⃣ Redémarrage du conteneur Flower..." -ForegroundColor Yellow
docker-compose restart soniquebay-flower

# 3. Surveillance des logs
Write-Host "`n3️⃣ Surveillance des logs du conteneur Flower..." -ForegroundColor Yellow
Write-Host "Attendre 30 secondes puis vérifier les logs :" -ForegroundColor Gray
Write-Host "docker logs soniquebay-flower --tail 30" -ForegroundColor Cyan

# 4. Vérification de l'accessibilité
Write-Host "`n4️⃣ Vérification de l'accessibilité Flower..." -ForegroundColor Yellow
Write-Host "Ouvrir http://localhost:5555/flower dans un navigateur" -ForegroundColor Cyan
Write-Host " ou http://IP-RASPBERRY-PI:5555/flower depuis un autre ordinateur" -ForegroundColor Gray
```

## 🔍 Validation du Résultat Attendu

```powershell
# =============================================================================
# VÉRIFICATION DU RÉSULTAT
# =============================================================================

Write-Host "🔍 === VÉRIFICATION DU RÉSULTAT ===" -ForegroundColor Cyan

# Vérifier les logs récents
Write-Host "Logs récents du conteneur Flower :" -ForegroundColor Yellow
docker logs soniquebay-flower --tail 20

# Vérifier le statut du conteneur
Write-Host "`nStatut du conteneur Flower :" -ForegroundColor Yellow
docker ps --filter name=soniquebay-flower

# Test de connectivité
Write-Host "`nTest de connectivité Flower :" -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "http://localhost:5555/flower" -TimeoutSec 10 -UseBasicParsing
    Write-Host "✅ Flower est accessible sur http://localhost:5555/flower" -ForegroundColor Green
} catch {
    Write-Host "⚠️ Flower n'est pas encore accessible (normal pendant le démarrage)" -ForegroundColor Yellow
}
```

## 🛠️ Dépannage

### Si les erreurs persistent :

```powershell
# Vérifier les permissions du volume flower-data
Write-Host "🔧 Vérification des permissions du volume..." -ForegroundColor Yellow
docker exec soniquebay-flower ls -la /data

# Vérifier les logs détaillés
Write-Host "`nLogs détaillés du démarrage..." -ForegroundColor Yellow
docker logs soniquebay-flower --details

# Redémarrage complet si nécessaire
Write-Host "`nRedémarrage complet du service Flower..." -ForegroundColor Yellow
docker-compose down soniquebay-flower
docker-compose up -d soniquebay-flower
```

### Signes de succès :

- ✅ Aucune erreur `tee: Permission denied`
- ✅ Aucune erreur `_gdbm.error: Permission denied`
- ✅ Flower accessible sur http://localhost:5555/flower
- ✅ Interface Flower fonctionnelle avec monitoring des tâches

### En cas de fallback (mode sans persistance) :

- ⚠️ Messages d'avertissement sur les permissions
- ✅ Flower démarre quand même en mode non-persistant
- ⚠️ Les données ne seront pas conservées entre redémarrages
- ✅ Monitoring fonctionnel mais temporaire