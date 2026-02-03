# GDC Ops Main

Single-tenant modular monolith for running GDC operations.

## Quickstart

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Seed CRM Pipeline Stages

```bash
python manage.py seed_pipeline
```

## Login & Dashboard
- Public landing page: `/`
- Login: `/login/`
- Dashboard (requires login): `/dashboard/`

## Workflow Discipline
See `docs/workflow.md` for the daily rules that keep metrics accurate.
