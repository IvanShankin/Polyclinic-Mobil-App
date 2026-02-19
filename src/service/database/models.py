import enum

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship

from src.service.database.core.database import Base


class StorageStatus(enum.Enum):
    DOCTOR = "doctor"
    PATIENT = "patient"
    ADMIN = "admin"
    DELETED = "deleted"


class AppointmentStatus(enum.Enum):
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class User(Base):
    __tablename__ = "User"

    id = Column(Integer, primary_key=True, autoincrement=True)
    login = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(
        Enum(
            StorageStatus,
            values_callable=lambda x: [e.value for e in x],
            name="role"
        ),
        nullable=False
    )

    # Связи с Doctor и Patient
    doctor = relationship("Doctor", back_populates="user", uselist=False)
    patient = relationship("Patient", back_populates="user", uselist=False)


class Doctor(Base):
    __tablename__ = "Doctor"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), unique=True, nullable=False)
    fio = Column(String, nullable=False)
    specialization = Column(String, nullable=False)

    # Связи
    user = relationship("User", back_populates="doctor")
    appointments = relationship("Appointment", back_populates="doctor")


class Patient(Base):
    __tablename__ = "Patient"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("User.id", ondelete="CASCADE", onupdate="CASCADE"), unique=True, nullable=False)
    fio = Column(String, nullable=False)
    phone = Column(String, nullable=False)

    # Связи
    user = relationship("User", back_populates="patient")
    appointments = relationship("Appointment", back_populates="patient")


class Appointment(Base):
    __tablename__ = "Appointment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    doctor_id = Column(Integer, ForeignKey("Doctor.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    patient_id = Column(Integer, ForeignKey("Patient.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    datetime = Column(DateTime, nullable=False)
    complaint = Column(String, nullable=True)
    condition = Column(String, nullable=True)
    conclusion = Column(String, nullable=True)
    status = Column(
        Enum(
            AppointmentStatus,
            values_callable=lambda x: [e.value for e in x],
            name="appointment_status",
        ),
        nullable=False,
        default=AppointmentStatus.SCHEDULED,
    )

    # Связи
    doctor = relationship("Doctor", back_populates="appointments")
    patient = relationship("Patient", back_populates="appointments")
