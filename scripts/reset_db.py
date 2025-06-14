import os
import glob
from pathlib import Path

def reset_database():
    """Réinitialise complètement la base de données."""
    try:
        # 1. Supprimer la base de données
        db_path = Path("music.db")
        if db_path.exists():
            os.remove(db_path)
            print("Base de données supprimée")

        # 2. Supprimer les migrations existantes
        migrations_path = Path("alembic/versions")
        for migration in migrations_path.glob("*.py"):
            if migration.name not in ["env.py", "README"]:
                os.remove(migration)
        print("Migrations supprimées")

        # 3. Créer une nouvelle migration
        os.system("alembic revision --autogenerate -m 'initial'")
        print("Nouvelle migration créée")

        # 4. Appliquer la migration
        os.system("alembic upgrade head")
        print("Migration appliquée")

    except Exception as e:
        print(f"Erreur lors de la réinitialisation: {str(e)}")

if __name__ == "__main__":
    reset_database()
