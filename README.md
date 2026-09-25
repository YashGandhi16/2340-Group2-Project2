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

### Creating accounts

Anyone can register at http://127.0.0.1:8000/accounts/signup/ (username, email, password). New accounts start as **Job Seekers**; an administrator can change the role from the dashboard.

### Recruiters: post jobs

Recruiters land on http://127.0.0.1:8000/jobs/recruiter/ after login. From there they can post a job (company, position, location, job description, applicant criteria, closing date), edit their own postings, and see applicant counts. Postings appear on the job search page (http://127.0.0.1:8000/jobs/) until their closing date passes.

### Messaging

Recruiters can message candidates inside the platform at http://127.0.0.1:8000/messages/, so neither side has to share a personal email. Click **Message** next to a candidate in *Search candidates* or on an application review page. Only recruiters can start a conversation; the candidate can reply in the same thread. Unread counts show on the home page and recruiter dashboard.

### Administrator: manage users and roles

1. Create an admin (if needed): `python manage.py createsuperuser`
2. Log in at http://127.0.0.1:8000/accounts/login/
3. You are sent to the admin dashboard at http://127.0.0.1:8000/dashboard/

The dashboard (superusers only) lists every account with its role, shows counts per role, and lets you filter/search, change any user's role (Job Seeker / Recruiter / Administrator), and activate or deactivate accounts.

Admins can also moderate every job posting at http://127.0.0.1:8000/dashboard/jobs/: filter by open/closed/hidden, **edit** any posting, **hide** one with a reason (removed from search, no new applications, existing applications kept, recruiter sees the reason), **restore** it, or **delete** it permanently (with a confirmation, since it also deletes its applications).

The Administrator role and Django's superuser flag are kept in sync: promoting a user to Administrator makes them a superuser, and demoting them removes it. After login, each user is redirected by role: admins → dashboard, recruiters → recruiter dashboard, job seekers → job list.

## Project layout

- `config/` — Django project settings and root URLs
- `accounts/` — auth, roles (`Role` / `Profile`), role decorators, signup, login redirect
- `admin/` — superuser dashboard for user/role management (app label `admin_dashboard`, served at `/dashboard/`)
- `jobs/` — job postings, search, applications, recruiter dashboard
- `profiles/` — profile app (empty starter)
- `messaging/` — recruiter ↔ candidate conversations and inbox
- `templates/` — shared HTML templates
