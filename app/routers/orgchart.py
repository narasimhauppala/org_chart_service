from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import List, Optional

from app.models.orgchart import OrgChart, Employee
from app.schemas.orgchart import OrgChartRead, OrgChartCreate, EmployeeRead, EmployeeCreate, EmployeeUpdate, DirectReports
from app.database import SessionLocal

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(
    prefix="/orgcharts",
    tags=["orgcharts"],
)

# --- Helper Functions ---

def get_org_or_404(org_id: int, db: Session) -> OrgChart:
    org = db.query(OrgChart).filter(OrgChart.id == org_id).first()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OrgChart with id {org_id} not found")
    return org

def get_employee_or_404(employee_id: int, db: Session, org_id: Optional[int] = None) -> Employee:
    query = db.query(Employee).filter(Employee.id == employee_id)
    if org_id is not None:
        query = query.filter(Employee.org_id == org_id)
    employee = query.first()
    if not employee:
        detail = f"Employee with id {employee_id} not found"
        if org_id is not None:
            detail += f" in OrgChart {org_id}"
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    return employee

def detect_cycle(employee_id: int, potential_manager_id: Optional[int], db: Session) -> bool:
    """Detects if assigning potential_manager_id to employee_id creates a cycle."""
    if potential_manager_id is None:
        return False # Cannot create a cycle by assigning no manager

    visited = {employee_id} # Start with the employee itself
    current_manager_id = potential_manager_id

    while current_manager_id is not None:
        if current_manager_id in visited:
            return True # Cycle detected

        # Check if the current manager exists to prevent errors during traversal
        manager = db.query(Employee.manager_id).filter(Employee.id == current_manager_id).scalar()
        if manager is None and current_manager_id != potential_manager_id:
             # This case implies a broken chain, but might also happen if the initial potential_manager_id is invalid.
             # We rely on other validation to catch invalid potential_manager_id. We assume valid IDs here.
             # If the potential_manager exists, the chain up must be valid or end at None.
             # If potential_manager doesn't exist, other validation should catch it. Let's assume valid for cycle check.
             pass # Or raise an internal error? For cycle detection, assume valid chain exists up to this point.

        visited.add(current_manager_id)

        # Move up the hierarchy
        current_manager_id = db.query(Employee.manager_id).filter(Employee.id == current_manager_id).scalar()

    return False # No cycle detected

def validate_manager(org_id: int, employee_id: Optional[int], manager_id: Optional[int], db: Session):
    """Validates manager existence, org membership, and cycle creation."""
    if manager_id is None:
        return # No manager to validate

    # Check if manager exists
    manager = db.query(Employee).filter(Employee.id == manager_id).first()
    if not manager:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Manager with id {manager_id} not found")

    # Check if manager is in the same org
    if manager.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Manager with id {manager_id} does not belong to OrgChart {org_id}")

    # Check for cycles (only if we are updating an existing employee or adding a new one)
    if employee_id is not None:
        if detect_cycle(employee_id, manager_id, db):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Assigning this manager would create a reporting cycle")
    # Note: Cycle detection for new employees needs careful handling - maybe pass a temporary ID?
    # For now, we assume creating an employee won't immediately create a cycle if the manager is valid.
    # The check during manager assignment is the primary safeguard.

def reparent_direct_reports(employee: Employee, db: Session):
    """Reparents direct reports of a deleted employee to the employee's manager."""
    new_manager_id = employee.manager_id
    direct_reports = db.query(Employee).filter(Employee.manager_id == employee.id).all()
    for report in direct_reports:
        # Basic cycle check before reparenting (prevent direct report becoming its own manager's manager)
        if report.id == new_manager_id:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot delete employee {employee.id} as it would make employee {report.id} their own manager indirectly.")
        # More complex cycle check might be needed depending on desired strictness
        if detect_cycle(report.id, new_manager_id, db):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Reparenting employee {report.id} to {new_manager_id} would create a cycle.")
        report.manager_id = new_manager_id
    db.flush() # Ensure changes are flushed before deleting the employee


# --- OrgChart Endpoints ---

@router.post("/", response_model=OrgChartRead, status_code=status.HTTP_201_CREATED)
def create_org_chart(org: OrgChartCreate, db: Session = Depends(get_db)):
    db_org = OrgChart(name=org.name)
    db.add(db_org)
    db.commit()
    db.refresh(db_org)
    # Manually load employees relationship to ensure it's in the response model format
    db_org.employees = []
    return db_org

@router.get("/", response_model=List[OrgChartRead])
def list_org_charts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    orgs = db.query(OrgChart).options(joinedload(OrgChart.employees)).offset(skip).limit(limit).all()
    return orgs

@router.get("/{org_id}", response_model=OrgChartRead)
def get_org_chart(org_id: int, db: Session = Depends(get_db)):
    # Use joinedload to efficiently fetch employees along with the org chart
    db_org = db.query(OrgChart).options(joinedload(OrgChart.employees)).filter(OrgChart.id == org_id).first()
    if db_org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"OrgChart with id {org_id} not found")
    return db_org


# --- Employee Endpoints ---

@router.post("/{org_id}/employees/", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def add_employee_to_org(
    org_id: int,
    employee: EmployeeCreate,
    db: Session = Depends(get_db)
):
    db_org = get_org_or_404(org_id, db)

    # Validate manager (exists, same org, no cycle *potential* - simplified check here)
    # Cycle check for new employee is tricky without an ID. We rely on PUT validation.
    if employee.manager_id:
        validate_manager(org_id=org_id, employee_id=None, manager_id=employee.manager_id, db=db)
        # Basic check: manager cannot be the employee being created (no ID yet, check name/title? Unreliable)
        # Relying on PUT validation if manager is updated later.

    db_employee = Employee(**employee.dict(), org_id=db_org.id)
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)
    return db_employee

@router.get("/{org_id}/employees/", response_model=List[EmployeeRead])
def list_employees_in_org(org_id: int, skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    # Ensure org exists first
    get_org_or_404(org_id, db)
    employees = db.query(Employee).filter(Employee.org_id == org_id).offset(skip).limit(limit).all()
    return employees

@router.get("/{org_id}/employees/{employee_id}", response_model=EmployeeRead)
def get_employee_in_org(org_id: int, employee_id: int, db: Session = Depends(get_db)):
    get_org_or_404(org_id, db) # Validate org exists
    db_employee = get_employee_or_404(employee_id, db, org_id)
    return db_employee

@router.put("/{org_id}/employees/{employee_id}", response_model=EmployeeRead)
def update_employee_in_org(
    org_id: int,
    employee_id: int,
    employee_update: EmployeeUpdate,
    db: Session = Depends(get_db)
):
    get_org_or_404(org_id, db)
    db_employee = get_employee_or_404(employee_id, db, org_id)

    update_data = employee_update.dict(exclude_unset=True)

    # Validate manager if it's being changed
    new_manager_id = update_data.get('manager_id')
    if 'manager_id' in update_data: # Checks if manager_id was provided in the request, even if None
        if new_manager_id == employee_id:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee cannot manage themselves")
        validate_manager(org_id=org_id, employee_id=employee_id, manager_id=new_manager_id, db=db)
        db_employee.manager_id = new_manager_id # Update manager_id separately

    # Update other fields
    if 'name' in update_data:
        db_employee.name = update_data['name']
    if 'title' in update_data:
        db_employee.title = update_data['title']

    db.commit()
    db.refresh(db_employee)
    return db_employee

@router.delete("/{org_id}/employees/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee_from_org(org_id: int, employee_id: int, db: Session = Depends(get_db)):
    get_org_or_404(org_id, db)
    db_employee = get_employee_or_404(employee_id, db, org_id)

    # Re-parent direct reports before deleting
    reparent_direct_reports(db_employee, db)

    db.delete(db_employee)
    db.commit()
    return None # Return None for 204 response


# --- Business Logic Endpoints ---

@router.post("/{org_id}/employees/{employee_id}/promote_ceo", response_model=EmployeeRead)
def promote_employee_to_ceo(org_id: int, employee_id: int, db: Session = Depends(get_db)):
    get_org_or_404(org_id, db)
    db_employee = get_employee_or_404(employee_id, db, org_id)

    # Check if employee is already the CEO (or has no manager)
    if db_employee.manager_id is None:
        # Optionally return current state or a specific message
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee is already a CEO (has no manager)")
        return db_employee # Return current state if already CEO

    # Check if making this employee CEO would orphan others (optional, depends on rules)
    # Basic promotion: set manager_id to None and update title
    db_employee.manager_id = None
    db_employee.title = "CEO"
    db.commit()
    db.refresh(db_employee)
    return db_employee


# --- Hierarchy API Endpoint ---

@router.get("/{org_id}/employees/{employee_id}/direct_reports", response_model=DirectReports)
def get_employee_direct_reports(org_id: int, employee_id: int, db: Session = Depends(get_db)):
    get_org_or_404(org_id, db)
    # Ensure the target employee exists in the specified org
    get_employee_or_404(employee_id, db, org_id)

    # Fetch direct reports
    direct_reports = db.query(Employee).filter(Employee.manager_id == employee_id).all()

    # Convert SQLAlchemy models to Pydantic models
    direct_reports_pydantic = [EmployeeRead.from_orm(report) for report in direct_reports]

    return DirectReports(direct_reports=direct_reports_pydantic)

# Placeholder for Manager Chain API (if chosen)
# @router.get("/{org_id}/employees/{employee_id}/manager_chain", response_model=List[EmployeeRead])
# def get_employee_manager_chain(org_id: int, employee_id: int, db: Session = Depends(get_db)):
#     # Implementation would involve traversing up the manager links
#     pass
