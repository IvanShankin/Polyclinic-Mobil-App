import hashlib
import hmac
import os
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from src.service.database.core.database import get_db
from src.service.database.models import (
    User,
    StorageStatus,
    Doctor,
    Patient,
    Appointment,
    AppointmentStatus,
)
from src.service.exeptions import ServiceError


@dataclass
class AuthPayload:
    user_id: int
    role: StorageStatus
    login: str


@dataclass
class DoctorView:
    id: int
    fio: str
    specialization: str


@dataclass
class AppointmentView:
    id: int
    doctor_fio: str
    patient_fio: str
    dt: datetime
    status: AppointmentStatus
    complaint: str
    condition: str
    conclusion: str



def hash_password(password: str) -> str:
    salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"pbkdf2_sha256${salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    if stored.startswith("pbkdf2_sha256$"):
        _, salt_hex, hash_hex = stored.split("$", 2)
        salt = bytes.fromhex(salt_hex)
        test_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(test_hash.hex(), hash_hex)

    # поддержка старых данных с паролем в открытом виде
    return hmac.compare_digest(password, stored)


async def register_patient(login: str, password: str, fio: str, phone: str) -> AuthPayload:
    if not login or not password or not fio or not phone:
        raise ServiceError("Переданы не все данные")

    async with get_db() as db:
        user = User(login=login.strip(), password=hash_password(password), role=StorageStatus.PATIENT)
        db.add(user)
        try:
            await db.flush()
            db.add(Patient(user_id=user.id, fio=fio.strip(), phone=phone.strip()))
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ServiceError("Логин уже занят")

        return AuthPayload(user_id=user.id, role=user.role, login=user.login)


async def login_user(login: str, password: str) -> AuthPayload:
    async with get_db() as db:
        result = await db.execute(select(User).where(User.login == login.strip()))
        user = result.scalar_one_or_none()

        if user is None or user.role == StorageStatus.DELETED:
            raise ServiceError("Пользователь не найден")

        if not verify_password(password, user.password):
            raise ServiceError("Неверный пароль")

        return AuthPayload(user_id=user.id, role=user.role, login=user.login)


async def get_doctors() -> list[DoctorView]:
    async with get_db() as db:
        result = await db.execute(select(Doctor).order_by(Doctor.fio.asc()))
        doctors = result.scalars().all()
        return [DoctorView(id=d.id, fio=d.fio, specialization=d.specialization) for d in doctors]


async def create_doctor(login: str, password: str, fio: str, specialization: str) -> None:
    async with get_db() as db:
        user = User(login=login.strip(), password=hash_password(password), role=StorageStatus.DOCTOR)
        db.add(user)

        try:
            await db.flush()
            db.add(Doctor(user_id=user.id, fio=fio.strip(), specialization=specialization.strip()))
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ServiceError("Логин уже занят")


async def update_doctor(
    doctor_id: int,
    fio: str,
    specialization: str,
    login: str | None = None,
    password: str | None = None,
) -> None:
    async with get_db() as db:
        result = await db.execute(select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id))
        doctor = result.scalar_one_or_none()
        if doctor is None:
            raise ServiceError("Врач не найден")

        doctor.fio = fio.strip()
        doctor.specialization = specialization.strip()

        if login is not None and login.strip():
            doctor.user.login = login.strip()

        if password is not None and password.strip():
            doctor.user.password = hash_password(password.strip())

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            raise ServiceError("Логин уже занят")


async def delete_doctor(doctor_id: int) -> None:
    async with get_db() as db:
        result = await db.execute(select(Doctor).options(selectinload(Doctor.user)).where(Doctor.id == doctor_id))
        doctor = result.scalar_one_or_none()
        if doctor is None:
            raise ServiceError("Врач не найден")

        user_id = doctor.user_id
        await db.execute(delete(Doctor).where(Doctor.id == doctor_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def create_appointment(patient_user_id: int, doctor_id: int, dt: datetime) -> None:
    async with get_db() as db:
        patient_result = await db.execute(select(Patient).where(Patient.user_id == patient_user_id))
        patient = patient_result.scalar_one_or_none()
        if patient is None:
            raise ServiceError("Пациент не найден")

        doctor_result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
        doctor = doctor_result.scalar_one_or_none()
        if doctor is None:
            raise ServiceError("Врач не найден")

        occupied = await db.execute(
            select(Appointment).where(
                Appointment.doctor_id == doctor_id,
                Appointment.datetime == dt,
            )
        )
        if occupied.scalar_one_or_none() is not None:
            raise ServiceError("Выбранное время занято")

        db.add(
            Appointment(
                doctor_id=doctor_id,
                patient_id=patient.id,
                datetime=dt,
                complaint="",
                condition="",
                conclusion="",
                status=AppointmentStatus.SCHEDULED,
            )
        )
        await db.commit()


async def get_patient_appointments(patient_user_id: int) -> list[AppointmentView]:
    async with get_db() as db:
        patient_result = await db.execute(select(Patient).where(Patient.user_id == patient_user_id))
        patient = patient_result.scalar_one_or_none()
        if patient is None:
            raise ServiceError("Пациент не найден")

        result = await db.execute(
            select(Appointment)
            .options(selectinload(Appointment.doctor), selectinload(Appointment.patient))
            .where(Appointment.patient_id == patient.id)
            .order_by(Appointment.datetime.asc())
        )
        appointments = result.scalars().all()

        return [
            AppointmentView(
                id=a.id,
                doctor_fio=a.doctor.fio,
                patient_fio=a.patient.fio,
                dt=a.datetime,
                status=a.status,
                complaint=a.complaint or "",
                condition=a.condition or "",
                conclusion=a.conclusion or "",
            )
            for a in appointments
        ]


async def get_doctor_appointments(doctor_user_id: int) -> list[AppointmentView]:
    async with get_db() as db:
        doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == doctor_user_id))
        doctor = doctor_result.scalar_one_or_none()
        if doctor is None:
            raise ServiceError("Врач не найден")

        result = await db.execute(
            select(Appointment)
            .options(selectinload(Appointment.patient), selectinload(Appointment.doctor))
            .where(Appointment.doctor_id == doctor.id)
            .order_by(Appointment.datetime.asc())
        )
        appointments = result.scalars().all()

        return [
            AppointmentView(
                id=a.id,
                doctor_fio=a.doctor.fio,
                patient_fio=a.patient.fio,
                dt=a.datetime,
                status=a.status,
                complaint=a.complaint or "",
                condition=a.condition or "",
                conclusion=a.conclusion or "",
            )
            for a in appointments
        ]




async def get_appointments_by_doctor_id(doctor_id: int) -> list[AppointmentView]:
    async with get_db() as db:
        doctor_result = await db.execute(select(Doctor).where(Doctor.id == doctor_id))
        doctor = doctor_result.scalar_one_or_none()
        if doctor is None:
            raise ServiceError("Врач не найден")

        result = await db.execute(
            select(Appointment)
            .options(selectinload(Appointment.patient), selectinload(Appointment.doctor))
            .where(Appointment.doctor_id == doctor.id)
            .order_by(Appointment.datetime.asc())
        )
        appointments = result.scalars().all()

        return [
            AppointmentView(
                id=a.id,
                doctor_fio=a.doctor.fio,
                patient_fio=a.patient.fio,
                dt=a.datetime,
                status=a.status,
                complaint=a.complaint or "",
                condition=a.condition or "",
                conclusion=a.conclusion or "",
            )
            for a in appointments
        ]

async def update_appointment_by_doctor(
    doctor_user_id: int,
    appointment_id: int,
    complaint: str,
    condition: str,
    conclusion: str,
    status: AppointmentStatus,
) -> None:
    async with get_db() as db:
        doctor_result = await db.execute(select(Doctor).where(Doctor.user_id == doctor_user_id))
        doctor = doctor_result.scalar_one_or_none()
        if doctor is None:
            raise ServiceError("Врач не найден")

        appointment_result = await db.execute(
            select(Appointment).where(
                Appointment.id == appointment_id,
                Appointment.doctor_id == doctor.id,
            )
        )
        appointment = appointment_result.scalar_one_or_none()
        if appointment is None:
            raise ServiceError("Прием не найден")

        appointment.complaint = complaint.strip()
        appointment.condition = condition.strip()
        appointment.conclusion = conclusion.strip()
        appointment.status = status
        await db.commit()


def parse_datetime(raw: str) -> datetime:
    try:
        return datetime.strptime(raw.strip(), "%Y-%m-%d %H:%M")
    except ValueError:
        raise ServiceError("Формат даты: ГГГГ-ММ-ДД ЧЧ:ММ")
