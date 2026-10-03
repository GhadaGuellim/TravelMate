# TravelMate - Backend

API Django REST + MongoDB.

## Prérequis

- Python 3.12 ou plus
- Git
- MongoDB Community Server (service actif sur `mongodb://localhost:27017`)

Installation sous Windows (PowerShell) :

    winget install Git.Git
    winget install MongoDB.Server

Vérifier que MongoDB tourne :

    Get-Service MongoDB

Le statut doit être `Running`.

## Installation du projet

    git clone https://github.com/GhadaGuellim/TravelMate.git
    cd TravelMate
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt

Si l'activation du venv est bloquée par PowerShell :

    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

## Lancer le serveur

    python manage.py runserver

Ne pas lancer `python manage.py migrate` : le projet utilise MongoDB, pas la base SQL de Django.

## Documentation de l'API

http://127.0.0.1:8000/api/docs/

## Routes

- POST /api/auth/register/
- POST /api/auth/login/
- GET /api/auth/me/

Les routes protégées demandent l'en-tête `Authorization: Bearer <access_token>`.

## Travailler en équipe

- Une branche par personne : `git checkout -b feature/nom-du-module`
- Ne jamais travailler directement sur `main`
- Récupérer les changements : `git pull origin main`