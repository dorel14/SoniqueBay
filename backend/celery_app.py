# -*- coding: utf-8 -*-
from celery import Celery

# Création de l'application Celery
celery = Celery(
    "soniquebay",
    broker="filesystem://",
    backend='db+sqlite:///results.sqlite'
)

celery.conf.update(
    broker_transport_options={
        "data_folder_in": "./celery_in",
        "data_folder_out": "./celery_out",
        "data_folder_processed": "./celery_processed",
    },
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Europe/Paris",
    enable_utc=True,
)