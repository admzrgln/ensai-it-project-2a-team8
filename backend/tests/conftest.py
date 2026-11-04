"""Configuration commune à tous les tests (chargée automatiquement par pytest AVANT les fichiers de tests).

Certains modules créent des objets dès leur import (ex. MovieService() -> OmdbClient() qui lit
OMDB_API_KEY, JWTBearer -> JwtService() qui lit JWT_SECRET). Sans ces variables, l'import plante
avec un KeyError avant même que les tests commencent.

On met donc de FAUSSES valeurs, seulement si la variable n'existe pas déjà (setdefault) :
les vraies valeurs de votre .env ne sont jamais écrasées. Les tests remplacent de toute façon
la base de données et l'API OMDb par des mocks.
"""
import os

os.environ.setdefault("JWT_SECRET", "test-secret-for-pytest-only-32-bytes!!")
os.environ.setdefault("OMDB_API_KEY", "fake-omdb-key-for-tests")
