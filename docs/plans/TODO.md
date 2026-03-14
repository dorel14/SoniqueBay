# TODO — Stabilisation GraphQL avant migration TaskIQ

- [x] Corriger l’exécution GraphQL des tests via `schema.execute` (async)
- [ ] Corriger `backend/api/graphql/queries/mutations/album_mutations.py` (alignement service + types + contexte)
- [ ] Exécuter `tests/integration/graphql/test_mutations.py::TestAlbumMutations -q`
- [ ] Corriger les anomalies restantes sur mutations album/track
- [ ] Exécuter `tests/integration/graphql/test_queries.py tests/integration/graphql/test_mutations.py -q`
- [ ] Lancer phase de tests **Thorough** (Windows, sans curl)
- [ ] Préparer PR de la branche actuelle puis création nouvelle branche dédiée migration TaskIQ
