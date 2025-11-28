from typing import Dict

class PathVariables:
    # Définition des variables disponibles avec leurs descriptions
    VARIABLES = {
        # Variables d'artiste
        "{artist}": "Nom de l'artiste principal",
        "{artist_id}": "ID de l'artiste dans la base de données",
        "{musicbrainz_artist_id}": "ID MusicBrainz de l'artiste",
        
        # Variables d'album
        "{album}": "Titre de l'album",
        "{album_artist}": "Artiste de l'album",
        "{year}": "Année de sortie",
        "{album_id}": "ID de l'album dans la base de données",
        "{musicbrainz_album_id}": "ID MusicBrainz de l'album",
        "{album_genre}": "Genre principal de l'album",
        
        # Variables de piste
        "{title}": "Titre de la piste",
        "{track_number}": "Numéro de piste",
        "{disc_number}": "Numéro de disque",
        "{genre}": "Genre de la piste",
        "{musicbrainz_track_id}": "ID MusicBrainz de la piste",
        "{bpm}": "Tempo en BPM",
        
        # Variables spéciales
        "{disc_track}": "Combinaison disque-piste (ex: 1-01)",
        "{first_letter}": "Première lettre de l'artiste",
        "{decade}": "Décennie (ex: 1980)"
    }

    # Mapping des variables vers les champs de la base de données
    DB_MAPPING = {
        "{artist}": "track_artist.name",
        "{artist_id}": "track_artist_id",
        "{album}": "album.title",
        "{album_artist}": "album.album_artist.name",
        "{year}": "year",
        "{title}": "title",
        "{track_number}": "track_number",
        "{disc_number}": "disc_number",
        "{genre}": "genre",
        # etc...
    }

    @classmethod
    def get_available_variables(cls) -> Dict[str, str]:
        """Retourne la liste des variables disponibles avec leurs descriptions."""
        return cls.VARIABLES

    @classmethod
    def get_example_path(cls) -> str:
        """Retourne un exemple de chemin utilisant les variables."""
        return "{album_artist}/{album}/{disc_track} - {artist} - {title}"

    @classmethod
    def validate_path_template(cls, template: str) -> bool:
        """Vérifie si le template utilise des variables valides."""
        import re
        variables = re.findall(r'\{([^}]+)\}', template)
        return all(f"{{{var}}}" in cls.VARIABLES for var in variables)
