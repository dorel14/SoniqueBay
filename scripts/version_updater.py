import re
import subprocess
from pathlib import Path

def get_git_tag():
    try:
        # Utilisation de shell=True pour Windows
        result = subprocess.run('git describe --tags', 
                            capture_output=True, 
                            text=True,
                            shell=True)
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception as e:
        print(f"Erreur lors de la récupération du tag : {e}")
    return "0.1.0"  # Version par défaut

def update_version_file():
    version = get_git_tag()
    
    # Utilisation de Path pour gérer les chemins Windows correctement
    version_file = Path(__file__).parent.parent / "_version_.py"
    
    # Contenu du fichier
    content = f'''"""Version information."""

__version__ = "{version}"
'''
    
    try:
        # Écriture du fichier avec encoding explicite
        version_file.write_text(content, encoding='utf-8')
        print(f"Version mise à jour : {version}")
        
        # Ajout automatique au git
        subprocess.run('git add _version_.py', shell=True, check=True)
    except Exception as e:
        print(f"Erreur lors de la mise à jour du fichier version : {e}")

if __name__ == "__main__":
    update_version_file()