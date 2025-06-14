import subprocess
from pathlib import Path

def get_git_tag():
    try:
        print("Récupération du tag Git...")
        result = subprocess.run('git describe --tags', 
                            capture_output=True, 
                            text=True,
                            shell=True)
        print(f"Résultat de git describe : {result.stdout}")
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"Erreur lors de la récupération du tag : {e}")
    return "0.1.0"

def update_version_file():
    print("Début de la mise à jour de version...")
    version = get_git_tag()

    version_file = Path(__file__).parent.parent / "_version_.py"
    print(f"Chemin du fichier version : {version_file}")

    content = f'''"""Version information."""

__version__ = "{version}"
'''

    try:
        version_file.write_text(content, encoding='utf-8')
        print(f"Version mise à jour : {version}")
        return True
    except Exception as e:
        print(f"Erreur lors de la mise à jour du fichier version : {e}")
        return False

if __name__ == "__main__":
    success = update_version_file()
    exit(0 if success else 1)