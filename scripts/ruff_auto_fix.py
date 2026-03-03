#!/usr/bin/env python3
"""
Script de correction automatique des erreurs Ruff pour SoniqueBay
Corrige les erreurs les plus courantes sans impacter l'architecture existante
"""

import subprocess
from pathlib import Path


def run_ruff_fix():
    """Exécute la correction automatique Ruff"""
    print("🔧 Correction automatique des erreurs Ruff...")
    
    # Corrections automatiques sûres
    commands = [
        # Suppression des imports inutilisés
        ["ruff", "check", "--select", "F401", "--fix", "."],
        
        # Suppression des variables non utilisées (dangereux, mais sûr pour les tests)
        ["ruff", "check", "--select", "F841", "--fix", "tests/"],
        
        # Correction des f-strings inutiles
        ["ruff", "check", "--select", "F541", "--fix", "."],
        
        # Correction des comparaisons booléennes
        ["ruff", "check", "--select", "E712", "--fix", "."],
        
        # Correction de l'ordre des imports
        ["ruff", "check", "--select", "E402", "--fix", "."],
    ]
    
    results = []
    for cmd in commands:
        print(f"Exécution: {' '.join(cmd)}")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=Path.cwd())
            results.append({
                'command': cmd,
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            })
            
            if result.stdout:
                print(f"✅ Sortie: {result.stdout[:200]}...")
            if result.stderr:
                print(f"⚠️ Erreurs: {result.stderr[:200]}...")
                
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution: {e}")
            results.append({
                'command': cmd,
                'success': False,
                'error': str(e)
            })
    
    return results

def check_remaining_errors():
    """Vérifie les erreurs restantes après correction"""
    print("\n🔍 Vérification des erreurs restantes...")
    
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format", "text", "."], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            print("✅ Aucune erreur Ruff détectée !")
            return True
        else:
            print(f"❌ {len(result.stdout.splitlines())} erreurs restantes:")
            print(result.stdout)
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False

def main():
    """Fonction principale"""
    print("🚀 Démarrage de la correction automatique Ruff pour SoniqueBay")
    print("=" * 60)
    
    # Correction automatique
    results = run_ruff_fix()
    
    print("\n📊 Résumé des corrections:")
    for i, result in enumerate(results, 1):
        status = "✅ SUCCÈS" if result['success'] else "❌ ÉCHEC"
        print(f"{i}. {' '.join(result['command'])}: {status}")
    
    # Vérification finale
    print("\n" + "=" * 60)
    final_status = check_remaining_errors()
    
    if final_status:
        print("\n🎉 Toutes les erreurs Ruff ont été corrigées !")
        print("Le code respecte maintenant les standards de qualité SoniqueBay.")
    else:
        print("\n⚠️ Certaines erreurs nécessitent une correction manuelle.")
        print("Exécutez 'ruff check .' pour voir les détails.")

if __name__ == "__main__":
    main()