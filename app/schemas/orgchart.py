from pydantic import BaseModel, Field
from typing import List, Optional

# --- Employee Schemas ---

class EmployeeBase(BaseModel):
    name: str
    title: str
    manager_id: Optional[int] = None

class EmployeeCreate(EmployeeBase):
    pass

class EmployeeUpdate(EmployeeBase):
    # Allow partial updates
    name: Optional[str] = None
    title: Optional[str] = None
    manager_id: Optional[int] = None # Explicitly allow setting manager to None (or changing it)

class EmployeeRead(EmployeeBase):
    id: int
    org_id: int
    # Add relationships for richer responses
    # manager: Optional['EmployeeRead'] = None # Avoid deep recursion for now
    # direct_reports: List['EmployeeRead'] = [] # Avoid deep recursion for now

    class Config:
        orm_mode = True # Enable ORM mode for compatibility with SQLAlchemy models


# --- OrgChart Schemas ---

class OrgChartBase(BaseModel):
    name: str

class OrgChartCreate(OrgChartBase):
    pass

class OrgChartRead(OrgChartBase):
    id: int
    employees: List[EmployeeRead] = [] # Include employees in the OrgChart response

    class Config:
        orm_mode = True

# Schema for the hierarchy endpoint (Direct Reports)
class DirectReports(BaseModel):
    direct_reports: List[EmployeeRead]
