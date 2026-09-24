# 2340-Group2-Project2

Django starter for Sprint 1. Python **3.12**.

## Setup

```bash
cd 2340-Group2-Project2
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Open http://127.0.0.1:8000/ — blank home page for now.

### Administrator: manage users and roles

1. Create an admin (if needed): `python manage.py createsuperuser`
2. Log in at http://127.0.0.1:8000/accounts/login/
3. Open http://127.0.0.1:8000/accounts/manage-users/

Superusers get the Administrator role automatically. You can change any user's role (Job Seeker / Recruiter / Administrator) and active status.

## Project layout

- `config/` — Django project settings and root URLs
- `accounts/` — auth, roles, manage-users page
- `jobs/` — job posting / search app (empty starter)
- `profiles/` — profile app (empty starter)
- `templates/` — shared HTML templates
