import datetime
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, Float, LargeBinary, cast, Text
from sqlalchemy.orm import relationship

from src.config import settings
from src.db import Base



class DiskScan(Base):
    __tablename__ = 'disk_scan'
    __table_args__ = {'schema': settings.DB_SCHEMA}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    disk_type_id = Column(Integer, ForeignKey(f'{settings.DB_SCHEMA}.disk_type.id', ondelete='CASCADE'), nullable=False)
    is_training = Column(Boolean, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))

    disk_type = relationship("DiskType", back_populates="disk_scans")
    blades = relationship("Blade", back_populates="disk_scan", cascade="all, delete", passive_deletes=True)




class DiskType(Base):
    __tablename__ = 'disk_type'
    __table_args__ = {'schema': settings.DB_SCHEMA}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, default=lambda: f"{datetime.datetime.now()} New disk type")  # Используем lambda для динамического значения
    diameter = Column(Integer, nullable=False, default=0)
    blade_distance = Column(Integer, nullable=False, default=0)
    blade_force = Column(Integer, nullable=False, default=0)  # Значение по умолчанию
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))

    disk_scans = relationship("DiskScan", back_populates="disk_type", cascade="all, delete", passive_deletes=True)
    models = relationship("DiskTypeModel", back_populates="disk_type", cascade="all, delete", passive_deletes=True)





class Blade(Base):
    __tablename__ = 'blade'
    __table_args__ = {'schema': settings.DB_SCHEMA}

    id = Column(Integer, primary_key=True, autoincrement=True)
    disk_scan_id = Column(Integer, ForeignKey(f'{settings.DB_SCHEMA}.disk_scan.id', ondelete='CASCADE'), nullable=False)
    num = Column(Integer, nullable=False)
    # scan = Column(String, nullable=False)
    scan = Column(LargeBinary, nullable=False)
    prediction = Column(Boolean, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))

    disk_scan = relationship("DiskScan", back_populates="blades")


class DiskTypeModel(Base):
    __tablename__ = 'disk_type_model'
    __table_args__ = {'schema': settings.DB_SCHEMA}

    id = Column(Integer, primary_key=True, autoincrement=True)
    disk_type_id = Column(Integer, ForeignKey(f'{settings.DB_SCHEMA}.disk_type.id', ondelete='CASCADE'), nullable=False)
    model = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.UTC))

    disk_type = relationship("DiskType", back_populates="models")


class DeviceConfig(Base):
    __tablename__ = 'device_config'
    __table_args__ = {'schema': settings.DB_SCHEMA}

    id = Column(Integer, primary_key=True, autoincrement=True)

    operating_port = Column(String, default="")
    SerialBaudRate = Column(Integer, default=115200)

    base_diameter = Column(Float, default=500.24)
    base_motor_speed = Column(Float, default=800)
    base_motor_accel = Column(Float, default=1600)
    base_motor_MaxSpeed = Column(Float, default=8000)

    head_motor_speed = Column(Float, default=800)
    head_motor_accel = Column(Float, default=1600)
    head_motor_MaxSpeed = Column(Float, default=8000)
    head_motor_returning_speed = Column(Float, default=2000)
    head_motor_returning_accel = Column(Float, default=3200)

    head_working_pos = Column(Float, default=300.0)

    tenzo_update_rate = Column(Integer, default=10)

    searching_time = Column(Integer, default = 10000, nullable=True)
    circle_in_steps = Column(Integer, default = 14400, nullable=True)
    recording_time = Column(Integer, default = 4000, nullable=True)
    force_to_find = Column(Integer, default = 50,nullable=True)

