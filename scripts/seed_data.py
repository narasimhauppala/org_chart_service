import os
import sys
import random
import time
from faker import Faker
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

# Add project root to sys.path to allow importing app modules
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.database import SessionLocal, engine, Base
from app.models.orgchart import OrgChart, Employee

# Configuration
NUM_ORG_CHARTS = 10000
MIN_EMPLOYEES_PER_ORG = 5
MAX_EMPLOYEES_PER_ORG = 15
MAX_HIERARCHY_DEPTH = 2 # CEO (0) -> Manager (1) -> Report (2)

fake = Faker()

def create_hierarchy(db: Session, org_id: int, num_employees: int):
    """Creates a simple hierarchy for a given org."""
    employees = []
    ceo = None

    # Create CEO first
    ceo_data = {
        "name": fake.name(),
        "title": "CEO",
        "org_id": org_id,
        "manager_id": None
    }
    db_ceo = Employee(**ceo_data)
    db.add(db_ceo)
    try:
        db.flush() # Flush to get CEO ID
        employees.append(db_ceo)
        ceo = db_ceo
    except IntegrityError:
        db.rollback() # Should not happen if org_id is valid
        print(f"Error creating CEO for org {org_id}")
        return [] # Skip this org if CEO fails

    # Create remaining employees
    possible_managers = [ceo]
    current_employees = 1

    while current_employees < num_employees:
        manager = random.choice(possible_managers)

        # Check if the current manager exists to prevent errors during traversal
        # Note: This check might not be strictly necessary in seed script if we trust our logic,
        # but kept for consistency demonstration
        # manager_exists = db.query(Employee).filter(Employee.id == current_manager_id).first()
        # if not manager_exists:
            # print(f"Debug: Manager ID {current_manager_id} not found during depth check.")
            # pass # Or handle appropriately

        # Simple depth check (based on manager's title for this basic setup)
        can_have_reports = True
        if manager.title == "CEO":
            depth = 1
            title = random.choice(["VP", "Director", "Manager"])
        elif manager.title in ["VP", "Director", "Manager"]:
            depth = 2
            title = random.choice(["Specialist", "Analyst", "Associate", "Engineer"])
        else: # Employees at max depth cannot manage others in this simple model
            depth = MAX_HIERARCHY_DEPTH + 1
            can_have_reports = False
            # If all possible managers are at max depth, we stop early or assign to higher level?
            # For simplicity, we might end up with fewer than num_employees if we run out of valid managers.
            if all(emp.title not in ["CEO", "VP", "Director", "Manager"] for emp in possible_managers):
                 print(f"Warning: Could not create all {num_employees} for org {org_id} due to depth limit.")
                 break # Stop if no valid managers left
            continue # Try another manager if this one can't have reports

        if depth > MAX_HIERARCHY_DEPTH:
             # If we accidentally select someone too deep, find a different manager
             if all(emp == manager for emp in possible_managers): # Avoid infinite loop if only one manager left and is too deep
                 print(f"Warning: Only manager left (ID: {manager.id}) is too deep. Stopping for org {org_id}.")
                 break
             continue

        employee_data = {
            "name": fake.name(),
            "title": title,
            "org_id": org_id,
            "manager_id": manager.id
        }
        db_employee = Employee(**employee_data)
        db.add(db_employee)
        try:
            db.flush() # Flush to get ID, needed if this employee becomes a manager
            employees.append(db_employee)
            if can_have_reports:
                 possible_managers.append(db_employee) # Add new employee as potential manager if not at max depth
            current_employees += 1
        except IntegrityError as e:
            db.rollback()
            print(f"Error creating employee under manager {manager.id} for org {org_id}: {e}")
            # Continue trying to add employees, maybe try a different manager
            # Potentially remove the failing manager from `possible_managers` if it's causing issues?
            continue

    return employees

def seed_data(db: Session):
    """Seeds the database with org charts and employees."""
    start_time = time.time()
    print(f"Starting seed process for {NUM_ORG_CHARTS} org charts...")

    total_employees_created = 0
    for i in range(NUM_ORG_CHARTS):
        org_name = fake.company() + f" Org-{i+1}"
        db_org = OrgChart(name=org_name)
        db.add(db_org)
        try:
            db.flush() # Flush to get the org ID
        except IntegrityError:
            db.rollback()
            print(f"Error creating OrgChart {i+1}. Skipping.")
            continue

        num_employees = random.randint(MIN_EMPLOYEES_PER_ORG, MAX_EMPLOYEES_PER_ORG)
        created_emps = create_hierarchy(db, db_org.id, num_employees)
        total_employees_created += len(created_emps)

        # Commit per organization to manage transaction size
        try:
            db.commit()
            if (i + 1) % 100 == 0:
                print(f"Seeded {i + 1}/{NUM_ORG_CHARTS} org charts...")
        except IntegrityError as e:
            db.rollback()
            print(f"Error committing data for OrgChart {db_org.id}. Skipping commit for this org. Error: {e}")
        except Exception as e:
            db.rollback()
            print(f"An unexpected error occurred for OrgChart {db_org.id}. Error: {e}")

    end_time = time.time()
    duration = end_time - start_time
    print("\n--- Seeding Complete ---")
    print(f"Created {NUM_ORG_CHARTS} org charts.")
    print(f"Created {total_employees_created} employees.")
    print(f"Seeding took {duration:.2f} seconds.")

if __name__ == "__main__":
    print("Initializing database connection...")
    db = SessionLocal()

    # Optional: Drop and recreate tables for a clean seed
    # print("Dropping existing tables (if any)...")
    # Base.metadata.drop_all(bind=engine)
    # print("Creating tables...")
    # Base.metadata.create_all(bind=engine)

    try:
        seed_data(db)
    finally:
        print("Closing database connection.")
        db.close()
