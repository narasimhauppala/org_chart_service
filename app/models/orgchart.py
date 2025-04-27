from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class OrgChart(Base):
    __tablename__ = 'org_charts'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)

    employees = relationship("Employee", back_populates="org", cascade="all, delete-orphan") # Added cascade delete

class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True, index=True)
    org_id = Column(Integer, ForeignKey('org_charts.id'), nullable=False, index=True) # Made nullable=False, added index
    name = Column(String, nullable=False)
    title = Column(String, nullable=False)
    manager_id = Column(Integer, ForeignKey('employees.id'), nullable=True, index=True) # Added index

    org = relationship("OrgChart", back_populates="employees")
    # Define the manager relationship with remote_side to handle self-referential FK
    manager = relationship("Employee", remote_side=[id], back_populates="direct_reports")
    direct_reports = relationship("Employee", back_populates="manager") # Added direct_reports relationship
