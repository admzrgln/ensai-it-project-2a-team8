# Ensai Cinéma Club
 
A backend application that runs the day-to-day business of a cinema: **planning screenings, selling tickets, and following the money**.
 
It was built as the ENSAI 2A IT project (Team 8). The scenario: the *Ensai Cinéma Club* takes over the Cinéville theater in Bruz in 2027 and needs software to replace spreadsheets and paper tickets.
 
---
 
## What it does
 
| Who | Needs | What the app provides |
|---|---|---|
| **Administrator** | Build the weekly programme | Add movies (manually or imported from **OMDb** by title / IMDb id), manage rooms, schedule screenings with automatic checks (no overlap in a room, no past date, seats ≤ room capacity) |
| **Administrator** | Set prices | Manage tariffs (full price, student, …) and yearly price revisions |
| **Customer** | Book a seat | Create an account, browse movies and screenings, get a price quote, book and cancel tickets, see "my bookings" |
| **Administrator** | Follow the accounts | Accounting report for any period: revenue, tickets sold, average ticket price, occupancy rate, broken down per movie |
 
Everything is exposed as a **REST API** (FastAPI) with interactive documentation (Swagger UI). Data lives in **PostgreSQL**. Access is secured with **JWT** tokens and two roles: `customer` and `admin`.
 
---
 
## Quick start
 
### 1. Prerequisites
 
- **Python 3.14** (required by `pyproject.toml`)
- **PDM**, the package manager used by the project
```bash
pip install --user pdm
pdm --version
```
- A **PostgreSQL** database you can connect to
- An **OMDb API key** (free)
 
### 2. Install
 
```bash
git clone https://github.com/admzrgln/ensai-it-project-2a-team8.git
cd ensai-it-project-2a-team8
pdm install
```
 
### 3. Configure
 
Create a file named `.env` at the root of the repository :
 
```dotenv
# PostgreSQL
POSTGRES_HOST=
POSTGRES_PORT=
POSTGRES_DATABASE=
POSTGRES_USER=
POSTGRES_PASSWORD=
POSTGRES_SCHEMA=

JWT_SECRET=

OMDB_API_KEY=
```
 
### 4. Create the database
 
Run the two SQL scripts on your database, in this order:
 
```bash
psql -h localhost -U postgres -d cinema -f database/schema.sql   # tables
psql -h localhost -U postgres -d cinema -f database/seed.sql     # demo movies, rooms, screenings
```
 
(You can also paste them into the SQL editor of CloudBeaver / pgAdmin.)
 
### 5. Run
 
```bash
pdm start
```
 
## Project structure (short)
 
```
.
├── backend/          # application code and tests
├── database/         # schema.sql and seed.sql
├── doc/              # manual API test log
├── utils/            # logging helpers, singleton
├── __main__.py       # entry point (pdm start)
└── pyproject.toml    # dependencies and PDM scripts
```
 

 