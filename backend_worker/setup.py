from setuptools import setup, find_packages

setup(
    name="backend_worker",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "cachetools",
        "httpx",
        "mutagen",
        "librosa",
        "numpy",
        "scipy",
        "scikit-learn",
        "faiss-cpu",
        "pydantic",
        "sqlalchemy",
        "alembic",
        "fastapi",
        "uvicorn",
        "celery",
        "redis",
        "pytest",
        "pytest-asyncio",
        "pytest-mock",
    ],
)