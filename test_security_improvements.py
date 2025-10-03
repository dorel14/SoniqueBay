#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de test pour vérifier les améliorations de sécurité de secure_open_file
"""

import asyncio
import tempfile
import os
from pathlib import Path
from backend_worker.services.music_scan import secure_open_file
from backend_worker.services.scanner import validate_file_path


async def test_security_improvements():
    """Teste les améliorations de sécurité implémentées."""

    print("🧪 Test des améliorations de sécurité pour secure_open_file")
    print("=" * 60)

    # Créer un répertoire temporaire pour les tests
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        allowed_base_paths = [temp_path]

        # Test 1: Créer un fichier de test valide
        test_file = temp_path / "test_valid.txt"
        test_content = b"Contenu de test valide"
        test_file.write_bytes(test_content)

        print("\n✅ TEST 1: Fichier valide")
        result = await secure_open_file(test_file, 'rb', allowed_base_paths)
        if result == test_content:
            print("   ✓ Lecture du fichier valide réussie")
        else:
            print("   ✗ Échec de lecture du fichier valide")

        # Test 2: Chemin relatif (devrait échouer)
        print("\n❌ TEST 2: Chemin relatif")
        relative_path = Path("test.txt")
        result = await secure_open_file(relative_path, 'rb', allowed_base_paths)
        if result is None:
            print("   ✓ Chemin relatif correctement rejeté")
        else:
            print("   ✗ Chemin relatif accepté (vulnérabilité!)")

        # Test 3: Mode d'ouverture non autorisé (devrait échouer)
        print("\n❌ TEST 3: Mode d'ouverture non autorisé")
        result = await secure_open_file(test_file, 'w', allowed_base_paths)
        if result is None:
            print("   ✓ Mode d'écriture correctement rejeté")
        else:
            print("   ✗ Mode d'écriture accepté (vulnérabilité!)")

        # Test 4: Chemin en dehors du répertoire autorisé (devrait échouer)
        print("\n❌ TEST 4: Chemin en dehors du répertoire autorisé")
        external_file = Path("/etc/passwd")
        if external_file.exists():
            result = await secure_open_file(external_file, 'rb', allowed_base_paths)
            if result is None:
                print("   ✓ Accès au fichier externe correctement rejeté")
            else:
                print("   ✗ Accès au fichier externe accepté (vulnérabilité!)")
        else:
            print("   ⚠ Fichier externe non disponible pour le test")

        # Test 5: Caractères interdits dans le nom de fichier
        print("\n❌ TEST 5: Caractères interdits dans le nom de fichier")
        # Créer un fichier avec des caractères interdits en utilisant l'API os directement
        import os
        forbidden_filename = "test*file.txt"  # * est interdit dans les noms de fichiers Windows
        forbidden_file_path = temp_path / forbidden_filename
        try:
            with open(forbidden_file_path, 'wb') as f:
                f.write(b"test")
            result = await secure_open_file(forbidden_file_path, 'rb', allowed_base_paths)
            if result is None:
                print("   ✓ Caractères interdits correctement rejetés")
            else:
                print("   ✗ Caractères interdits acceptés (vulnérabilité!)")
        except OSError:
            # Si on ne peut pas créer le fichier avec des caractères interdits,
            # tester directement avec un chemin qui contient ces caractères
            fake_path = temp_path / "test?file.txt"  # ? est aussi interdit
            result = await secure_open_file(fake_path, 'rb', allowed_base_paths)
            if result is None:
                print("   ✓ Caractères interdits correctement rejetés")
            else:
                print("   ✗ Caractères interdits acceptés (vulnérabilité!)")

        # Test 6: Nom de fichier trop long
        print("\n❌ TEST 6: Nom de fichier trop long")
        long_name = "a" * 300 + ".txt"
        long_file = temp_path / long_name
        long_file.write_bytes(b"test")
        result = await secure_open_file(long_file, 'rb', allowed_base_paths)
        if result is None:
            print("   ✓ Nom de fichier trop long correctement rejeté")
        else:
            print("   ✗ Nom de fichier trop long accepté (vulnérabilité!)")

        # Test 7: Pattern de traversée de répertoire
        print("\n❌ TEST 7: Pattern de traversée de répertoire")
        # Créer un fichier avec un pattern de traversée dans le nom
        traversal_file = temp_path / "test_.._traversal.txt"
        traversal_file.write_bytes(b"test")
        result = await secure_open_file(traversal_file, 'rb', allowed_base_paths)
        if result is None:
            print("   ✓ Pattern de traversée correctement rejeté")
        else:
            print("   ✗ Pattern de traversée accepté (vulnérabilité!)")

        # Test 8: Test de validate_file_path
        print("\n🧪 TEST 8: Fonction validate_file_path")
        valid_result = await validate_file_path(str(test_file), temp_path)
        if valid_result and valid_result == test_file.resolve():
            print("   ✓ validate_file_path fonctionne correctement pour les chemins valides")
        else:
            print("   ✗ validate_file_path échoue pour les chemins valides")

        invalid_result = await validate_file_path("/etc/passwd", temp_path)
        if invalid_result is None:
            print("   ✓ validate_file_path rejette correctement les chemins invalides")
        else:
            print("   ✗ validate_file_path accepte les chemins invalides (vulnérabilité!)")

    print("\n" + "=" * 60)
    print("🎯 Tests de sécurité terminés!")
    print("\n📋 Résumé des améliorations implémentées:")
    print("   ✅ Validation du type du chemin comme Path")
    print("   ✅ Vérification que le chemin est absolu")
    print("   ✅ Restriction des modes d'ouverture autorisés")
    print("   ✅ Validation que le chemin est dans le répertoire de travail")
    print("   ✅ Vérification des caractères interdits dans le nom de fichier")
    print("   ✅ Validation de la longueur du nom de fichier")
    print("   ✅ Vérification des permissions du fichier")
    print("   ✅ Logging détaillé de toutes les étapes de validation")


if __name__ == "__main__":
    asyncio.run(test_security_improvements())