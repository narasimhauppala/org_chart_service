# Org Chart Service

This project implements a RESTful API service for managing organizational charts using FastAPI, PostgreSQL, SQLAlchemy, and Alembic. It includes features for managing organizations and employees, handling hierarchies, validating data, and includes containerization with Docker.

## Features

*   **Organizations:** CRUD operations for managing organization charts.
*   **Employees:** CRUD operations for managing employees within organizations.
*   **Hierarchy Management:**
    *   Assign managers to employees.
    *   Validation to prevent reporting cycles.
    *   Automatic re-parenting of direct reports when an employee is deleted.
    *   Endpoint to promote an employee to CEO (remove their manager).
    *   API endpoint to retrieve direct reports for an employee.
*   **Database Migrations:** Alembic for managing database schema changes.
*   **Data Seeding:** Script to populate the database with large amounts of test data (10,000 orgs).
*   **Containerization:** Docker and Docker Compose for easy setup and deployment.
*   **Environment Configuration:** Uses `.env` files for managing settings.

## Tech Stack

*   **Backend:** Python, FastAPI
*   **Database:** PostgreSQL
*   **ORM:** SQLAlchemy
*   **Migrations:** Alembic
*   **Data Validation:** Pydantic
*   **Containerization:** Docker, Docker Compose
*   **Testing Data:** Faker

## Project Structure

```
org_chart_service/
├── app/
│   ├── __init__.py
│   ├── database.py       # SQLAlchemy setup (engine, session, Base)
│   ├── main.py           # FastAPI application entrypoint
│   ├── models/
│   │   └── orgchart.py   # SQLAlchemy models (OrgChart, Employee)
│   ├── routers/
│   │   └── orgchart.py   # FastAPI router for org chart endpoints
│   └── schemas/
│       └── orgchart.py   # Pydantic schemas for request/response validation
├── migrations/           # Alembic migration scripts
│   ├── versions/         # Individual migration files
│   ├── env.py            # Alembic environment configuration
│   └── script.py.mako    # Alembic migration template
├── scripts/
│   └── seed_data.py      # Script to populate DB with test data
├── .env.dev              # Development environment variables
├── .env.example          # Example environment file
├── .env.prod             # Placeholder for production environment variables
├── .gitignore            # Git ignore file
├── alembic.ini           # Alembic configuration file
├── docker-compose.yml    # Docker Compose setup for services (API, DB)
├── Dockerfile            # Dockerfile for the FastAPI application
├── entrypoint.sh         # Entrypoint script for API container (runs migrations)
├── README.md             # This file
└── requirements.txt      # Python package dependencies
```

## Quick Start (using Docker)

1.  **Prerequisites:**
    *   Docker: [Install Docker](https://docs.docker.com/get-docker/)
    *   Docker Compose: (Usually included with Docker Desktop)

2.  **Clone the repository (if applicable):**
    ```bash
    git clone <repository_url>
    cd org_chart_service
    ```

3.  **Environment Setup:**
    *   Copy the example environment file:
        ```bash
        # On Linux/macOS
        cp .env.example .env.dev
        # On Windows (Command Prompt)
        copy .env.example .env.dev
        # On Windows (PowerShell)
        Copy-Item .env.example .env.dev
        ```
    *   The default `.env.dev` uses the settings defined in `docker-compose.yml` and should work out-of-the-box.

4.  **Build and Run Services:**
    ```bash
    docker-compose up --build -d
    ```
    *   `--build`: Forces Docker to rebuild the API image if `Dockerfile` or related files changed.
    *   `-d`: Runs the containers in detached mode (in the background).

5.  **Access API:**
    *   The API will be available at `http://localhost:8000`.
    *   Interactive API documentation (Swagger UI) at `http://localhost:8000/docs`.
    *   Alternative API documentation (ReDoc) at `http://localhost:8000/redoc`.

## Time Expectation & Log

*   **Target:** ≤ 2 hours for core functionality, plus ½ hour for documentation & polish (total ≤ 2.5 h).
*   **Time Log (Approximate):**
    *   Project Setup & Initial Scaffolding: [20m]
    *   Database Setup (Models, Connection, Alembic): [25m]
    *   API Logic (CRUD, Validation, Business Rules): [25m]
    *   Hierarchy API Implementation: [15m]
    *   Seeding Script: [10m]
    *   Containerization (Dockerfile, Docker Compose, Entrypoint): [10m]
    *   Environment Config & Gitignore: [10m]
    *   Documentation (README): [15m]
    *   Testing & Debugging: [10m]
    *   Performance Demo Prep: [10m]
    *   **Total:** [150m]

## Database Initialization & Migrations

*   Database tables are automatically created/updated when the `api` container starts.
*   The `entrypoint.sh` script waits for the PostgreSQL database (`db` service) to be ready and then executes `alembic upgrade head` to apply any pending migrations defined in the `migrations/versions` directory.
*   The initial migration creates the `org_charts` and `employees` tables.

## Running the Seed Script

To populate the database with ~10,000 organizations and their employees (as defined in `scripts/seed_data.py`), run the following command **after** starting the services with `docker-compose up`:

```bash
docker-compose exec api python scripts/seed_data.py
```

This executes the `seed_data.py` script inside the running `api` container.

## API Details

### Hierarchy View

This implementation includes the **Direct Reports** hierarchy view.

*   `GET /orgcharts/{org_id}/employees/{employee_id}/direct_reports`: Returns a list of employees who report directly to the specified `employee_id` within the given `org_id`.

### Employee Deletion

*   When an employee is deleted via `DELETE /orgcharts/{org_id}/employees/{employee_id}`, their direct reports are automatically re-assigned to the manager of the deleted employee.
*   If the deleted employee was a CEO (had no manager), their direct reports will also become manager-less (CEOs of their own potential sub-trees).
*   The deletion checks for potential cycle creation during re-parenting.

### CEO Promotion

*   `POST /orgcharts/{org_id}/employees/{employee_id}/promote_ceo`: Sets the specified employee's `manager_id` to `null`, effectively making them a root employee (CEO) within their hierarchy.

## Database Indices

The following database indices are created by the initial migration to improve query performance:

*   `org_charts`: `id` (Primary Key index)
*   `employees`: `id` (Primary Key index)
*   `employees`: `org_id` (Foreign Key index, speeds up filtering employees by org)
*   `employees`: `manager_id` (Foreign Key index, speeds up finding direct reports and traversing hierarchy)

## Performance Evidence (Placeholder)

*(Results from timing tests after seeding should be added here)*

*   **Test Environment:** (e.g., Docker Desktop on Windows 11, M1 Mac, etc.)
*   **Seeding Time:** (e.g., Approx. X minutes/seconds)
*   **`GET /orgcharts/{org_id}/employees` (Large Org):** (e.g., Average Y ms)
*   **`GET /orgcharts/{org_id}/employees/{id}/direct_reports`:** (e.g., Average Z ms)

*(Target: Response time < 2 seconds)*

## Secrets Management

*   **Development:** Uses `.env.dev` (loaded via `python-dotenv`) for the `DATABASE_URL`. See `.env.example`.
*   **Production:** **DO NOT** commit `.env.prod` with real credentials. Use a secure method:
    *   Docker Secrets
    *   Cloud provider secrets managers (AWS Secrets Manager, Google Secret Manager, Azure Key Vault)
    *   HashiCorp Vault
    *   Environment variables injected securely by CI/CD or orchestration tools.

## Enhancements & Open Issues

*   **More Robust Cycle Detection:** The current cycle detection works but could be enhanced, especially around edge cases during creation or complex reparenting scenarios.
*   **Improved Seeding Hierarchy:** The seed script creates a basic hierarchy; it could be enhanced to create deeper and more varied structures.
*   **Manager Chain API:** Implement the `GET /orgcharts/{org_id}/employees/{employee_id}/manager_chain` endpoint as an alternative hierarchy view.
*   **Authentication/Authorization:** Add user authentication and authorization to protect endpoints.
*   **Testing:** Implement unit and integration tests (e.g., using `pytest` and `httpx`).
*   **Async Database:** Convert database operations to use async drivers (`asyncpg`) and sessions for potentially higher concurrency.
*   **Error Handling:** Add more specific error handling and logging.
*   **Performance Tuning:** Further optimize database queries, potentially adding more specific indices based on access patterns.
*   **Known Bugs (Fixed):**
    *   `promote_ceo` endpoint only updated `manager_id`, not `title`. Fixed by adding `db_employee.title = "CEO"`.
    *   `entrypoint.sh` failed due to missing `pg_isready` (or `nc` fallback). Fixed by installing `postgresql-client` in the `Dockerfile`.
*   **Platform Considerations:**
    *   Alembic commands might require specific environment setup (virtualenv activation) to be found in the system PATH.
    *   File permissions (`chmod`) behave differently on Windows vs. Linux/macOS.

## AI Assistance

ChatGPT was used to assist with:

*   Generating the initial project structure and boilerplate code.
*   Creating the data seeding script.
*   Generating this README file.

### Potential Fixes/Considerations from Initial Design

*   **Alembic Initialization:** The `alembic init` command failed initially due to environment path issues. We manually created the Alembic configuration (`alembic.ini`, `migrations/env.py`, `migrations/script.py.mako`, `migrations/versions/`). If `alembic` is correctly installed and accessible in your environment (e.g., activated virtual environment), `alembic init migrations`, `alembic revision --autogenerate`, and `alembic upgrade head` should work as expected, potentially simplifying the migration setup.
*   **Seed Script Hierarchy:** The current seed script creates a relatively shallow (max 2 levels below CEO) and simple hierarchy. For more complex testing, this script could be modified to generate deeper or more varied organizational structures.
*   **Cycle Detection on Create:** The current cycle detection in `POST /{org_id}/employees/` is basic because the new employee doesn't have an ID yet. A more robust check might involve temporary IDs or alternative logic if strictly needed before the first `PUT` update.
*   **Direct Reports API:** The `/direct_reports` endpoint was chosen for the hierarchy view. Implementing the `/manager_chain` endpoint would require adding logic to traverse upwards from an employee to the CEO.
*   **Permissions:** The `chmod +x entrypoint.sh` command failed on Windows. While Docker often handles this for Linux containers, ensuring Git tracks execute permissions (`git update-index --chmod=+x entrypoint.sh`) is good practice for cross-platform compatibility if the repository is shared.
