from typing import Dict, Any



# Sample GraphQL queries for testing
QUERY_GET_ARTIST = """
query GetArtist($id: Int!) {
  artist(id: $id) {
    id
    name
    musicbrainzArtistid
  }
}
"""

QUERY_LIST_ARTISTS = """
query ListArtists {
  artists {
    id
    name
    musicbrainzArtistid
  }
}
"""

QUERY_GET_ALBUM = """
query GetAlbum($id: Int!) {
  album(id: $id) {
    id
    title
    albumArtistId
    releaseYear
    musicbrainzAlbumid
  }
}
"""

QUERY_LIST_ALBUMS = """
query ListAlbums {
  albums {
    id
    title
    albumArtistId
  }
}
"""

QUERY_GET_TRACK = """
query GetTrack($id: Int!) {
  track(id: $id) {
    id
    title
    path
    trackArtistId
    albumId
    genre
    bpm
    key
    scale
  }
}
"""

QUERY_LIST_TRACKS = """
query ListTracks {
  tracks {
    id
    title
    path
    trackArtistId
  }
}
"""

# Sample mutation strings
MUTATION_CREATE_ARTIST = """
mutation CreateArtist($data: ArtistCreateInput!) {
  createArtist(data: $data) {
    id
    name
    musicbrainzArtistid
  }
}
"""

MUTATION_CREATE_ARTISTS = """
mutation CreateArtists($data: [ArtistCreateInput!]!) {
  createArtists(data: $data) {
    id
    name
  }
}
"""

MUTATION_CREATE_ALBUM = """
mutation CreateAlbum($data: AlbumCreateInput!) {
  createAlbum(data: $data) {
    id
    title
    albumArtistId
  }
}
"""

MUTATION_CREATE_TRACK = """
mutation CreateTrack($data: TrackCreateInput!) {
  createTrack(data: $data) {
    id
    title
    path
    trackArtistId
    albumId
  }
}
"""

MUTATION_UPDATE_ARTIST = """
mutation UpdateArtistById($data: ArtistUpdateInput!) {
  updateArtistById(data: $data) {
    id
    name
  }
}
"""

# Sample variables for mutations
SAMPLE_ARTIST_INPUT: Dict[str, Any] = {
    "data": {
        "name": "Test Artist",
        "musicbrainzArtistid": "test-mb-artist-id"
    }
}

SAMPLE_ALBUM_INPUT: Dict[str, Any] = {
    "data": {
        "title": "Test Album",
        "albumArtistId": 1,  # Assume artist ID 1 exists
        "musicbrainzAlbumid": "test-mb-album-id",
        "releaseYear": "2023"
    }
}

SAMPLE_TRACK_INPUT: Dict[str, Any] = {
    "data": {
        "title": "Test Track",
        "path": "/path/to/test.mp3",
        "trackArtistId": 1,
        "albumId": 1,
        "genre": "Rock",
        "bpm": 120.0,
        "key": "C",
        "scale": "major"
    }
}

SAMPLE_UPDATE_ARTIST_INPUT: Dict[str, Any] = {
    "data": {
        "id": 1,
        "name": "Updated Test Artist"
    }
}