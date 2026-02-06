# tests/benchmark/benchmark_api_graphql.py
"""
Benchmarks pour les requêtes API GraphQL.
"""
import pytest


class TestAPIGraphQLBenchmark:
    """Benchmarks pour les endpoints GraphQL."""

    @pytest.mark.benchmark(
        group="api_graphql",
        min_rounds=5,
        max_time=10.0,
        disable_gc=True,
        warmup=True
    )
    def test_graphql_tracks_list_benchmark(self, benchmark, benchmark_client, create_test_tracks):
        """Benchmark récupération liste des tracks via GraphQL."""

        # Créer des données de test
        create_test_tracks(count=50)

        query = """
        query GetTracks($skip: Int, $limit: Int) {
            tracks(skip: $skip, limit: $limit) {
                id
                title
                path
                genre
                bpm
                key
                scale
                covers {
                    id
                    url
                    mimeType
                }
            }
        }
        """

        variables = {"skip": 0, "limit": 50}

        def run_query():
            response = benchmark_client.post(
                "/api/graphql",
                json={"query": query, "variables": variables}
            )
            return response

        response = benchmark(run_query)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "tracks" in data["data"]
        assert len(data["data"]["tracks"]) >= 50

    @pytest.mark.benchmark(
        group="api_graphql",
        min_rounds=5,
        max_time=8.0,
        disable_gc=True,
        warmup=True
    )
    def test_graphql_single_track_benchmark(self, benchmark, benchmark_client, create_test_track):
        """Benchmark récupération track individuelle via GraphQL."""

        track = create_test_track()

        query = """
        query GetTrack($id: Int!) {
            track(id: $id) {
                id
                title
                path
                duration
                genre
                bpm
                key
                scale
                danceability
                instrumental
                acoustic
                covers {
                    id
                    url
                    mimeType
                }
            }
        }
        """

        variables = {"id": track.id}

        def run_query():
            response = benchmark_client.post(
                "/api/graphql",
                json={"query": query, "variables": variables}
            )
            return response

        response = benchmark(run_query)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "track" in data["data"]
        assert data["data"]["track"]["id"] == track.id

    @pytest.mark.benchmark(
        group="api_graphql",
        min_rounds=5,
        max_time=12.0,
        disable_gc=True,
        warmup=True
    )
    def test_graphql_tracks_with_complex_relations_benchmark(self, benchmark, benchmark_client, create_test_track_with_relations):
        """Benchmark récupération tracks avec relations complexes via GraphQL."""

        track, artist, album = create_test_track_with_relations()

        query = """
        query GetTracksWithRelations {
            tracks(limit: 10) {
                id
                title
                path
                genre
                bpm
                key
                scale
                covers {
                    id
                    entityType
                    entityId
                    url
                    mimeType
                    coverData
                }
            }
        }
        """

        def run_query():
            response = benchmark_client.post(
                "/api/graphql",
                json={"query": query}
            )
            return response

        response = benchmark(run_query)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "tracks" in data["data"]
        assert len(data["data"]["tracks"]) >= 1

    @pytest.mark.benchmark(
        group="api_graphql",
        min_rounds=3,
        max_time=25.0,
        disable_gc=True,
        warmup=True
    )
    def test_graphql_large_dataset_pagination_benchmark(self, benchmark, benchmark_client, create_test_tracks):
        """Benchmark pagination GraphQL avec grand jeu de données."""

        # Créer un grand nombre de tracks
        create_test_tracks(count=500)

        query = """
        query GetTracksPaginated($skip: Int, $limit: Int) {
            tracks(skip: $skip, limit: $limit) {
                id
                title
                genre
                bpm
                key
            }
        }
        """

        variables = {"skip": 100, "limit": 50}

        def run_query():
            response = benchmark_client.post(
                "/api/graphql",
                json={"query": query, "variables": variables}
            )
            return response

        response = benchmark(run_query)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "tracks" in data["data"]
        assert len(data["data"]["tracks"]) <= 50

    @pytest.mark.benchmark(
        group="api_graphql",
        min_rounds=5,
        max_time=15.0,
        disable_gc=True,
        warmup=True
    )
    def test_graphql_multiple_queries_benchmark(self, benchmark, benchmark_client, create_test_tracks):
        """Benchmark exécution de multiples requêtes GraphQL."""

        create_test_tracks(count=20)

        # Requête complexe avec plusieurs champs
        query = """
        query GetMultipleData {
            tracks(limit: 10) {
                id
                title
                path
                duration
                genre
                bpm
                key
                scale
                danceability
                moodHappy
                moodAggressive
                moodParty
                moodRelaxed
                instrumental
                acoustic
                tonal
                covers {
                    id
                    url
                    mimeType
                }
            }
            track(id: 1) {
                id
                title
                genre
                bpm
            }
        }
        """

        def run_query():
            response = benchmark_client.post(
                "/api/graphql",
                json={"query": query}
            )
            return response

        response = benchmark(run_query)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "tracks" in data["data"]
        assert "track" in data["data"]

    @pytest.mark.benchmark(
        group="api_graphql",
        min_rounds=5,
        max_time=10.0,
        disable_gc=True,
        warmup=True
    )
    def test_graphql_introspection_benchmark(self, benchmark, benchmark_client):
        """Benchmark requête d'introspection GraphQL."""

        query = """
        query IntrospectionQuery {
            __schema {
                types {
                    name
                    kind
                    fields {
                        name
                        type {
                            name
                            kind
                        }
                    }
                }
            }
        }
        """

        def run_query():
            response = benchmark_client.post(
                "/api/graphql",
                json={"query": query}
            )
            return response

        response = benchmark(run_query)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "__schema" in data["data"]

    @pytest.mark.benchmark(
        group="api_graphql",
        min_rounds=10,
        max_time=5.0,
        disable_gc=True,
        warmup=True
    )
    def test_graphql_simple_field_selection_benchmark(self, benchmark, benchmark_client, create_test_track):
        """Benchmark sélection de champs simples via GraphQL."""

        track = create_test_track()

        query = """
        query GetTrackSimple($id: Int!) {
            track(id: $id) {
                id
                title
                genre
            }
        }
        """

        variables = {"id": track.id}

        def run_query():
            response = benchmark_client.post(
                "/api/graphql",
                json={"query": query, "variables": variables}
            )
            return response

        response = benchmark(run_query)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert data["data"]["track"]["id"] == track.id
        assert "title" in data["data"]["track"]
        assert "genre" in data["data"]["track"]

    @pytest.mark.benchmark(
        group="api_graphql",
        min_rounds=3,
        max_time=20.0,
        disable_gc=True,
        warmup=True
    )
    def test_graphql_batch_queries_benchmark(self, benchmark, benchmark_client, create_test_tracks):
        """Benchmark traitement par lot de requêtes GraphQL."""

        tracks = create_test_tracks(count=50)

        # Simuler plusieurs requêtes séquentielles
        queries = []
        for i in range(10):
            query = f"""
            query GetTrack{i} {{
                track(id: {tracks[i].id}) {{
                    id
                    title
                    genre
                    bpm
                }}
            }}
            """
            queries.append(query)

        def run_batch_queries():
            results = []
            for query in queries:
                response = benchmark_client.post(
                    "/api/graphql",
                    json={"query": query}
                )
                results.append(response)
            return results

        responses = benchmark(run_batch_queries)

        assert len(responses) == 10
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "data" in data