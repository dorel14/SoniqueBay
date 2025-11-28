#!/usr/bin/env python3
"""
Test rapide de la correction de validate_release_year
"""

from backend.api.schemas.albums_schema import AlbumBase

# Test des cas réels des logs d'erreur
test_cases = [
    ('2014-08-05', '2014'),  # Du log original
    ('2024-02-09', '2024'),  # Du log original  
    ('2014', '2014'),
    ('15/08/2014', '2014'),
    ('14', '2014'),
    ('95', '1995'),
    (2014, '2014'),
    (None, None),
    ('abc', None),
]

validator = AlbumBase.validate_release_year

print("🧪 Test de la correction validate_release_year:")
print("=" * 50)

all_passed = True
for input_val, expected in test_cases:
    try:
        result = validator(input_val)
        status = '✅' if result == expected else '❌'
        if result != expected:
            all_passed = False
        print(f'{status} {repr(input_val)} → {repr(result)} (attendu: {repr(expected)})')
    except Exception as e:
        print(f'❌ {repr(input_val)} → ERREUR: {e}')
        all_passed = False

print("=" * 50)
if all_passed:
    print("✅ Tous les tests passent !")
else:
    print("❌ Certains tests échouent.")
    
print("\n🎯 Tests critiques (logs d'erreur originaux):")
critical_cases = [('2014-08-05', '2014'), ('2024-02-09', '2024')]
for input_val, expected in critical_cases:
    result = validator(input_val)
    status = '✅' if result == expected else '❌'
    print(f'{status} {input_val} → {result}')