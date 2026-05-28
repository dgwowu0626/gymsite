from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    phone = Column(String(32), unique=True, nullable=True, index=True)
    email = Column(String(160), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="client", index=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    trainer = relationship("Trainer", back_populates="user", uselist=False)
    client = relationship("Client", back_populates="user", uselist=False)
    subscriptions = relationship("UserSubscription", back_populates="user", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="user")


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    name = Column(String(120), nullable=False)
    note = Column(Text, nullable=False, default="")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="profile")


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True, index=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(32), nullable=True, unique=True, index=True)
    email = Column(String(160), nullable=True, unique=True, index=True)
    note = Column(Text, default="", nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="client")
    bookings = relationship("Booking", back_populates="client", cascade="all, delete-orphan")


class Trainer(Base):
    __tablename__ = "trainers"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, unique=True, index=True)
    name = Column(String(120), nullable=False)
    specialization = Column(String(200), nullable=False)
    experience = Column(String(120), nullable=False)
    bio = Column(Text, nullable=False, default="")

    user = relationship("User", back_populates="trainer")
    bookings = relationship("Booking", back_populates="trainer_profile")
    workout_history = relationship("WorkoutHistory", back_populates="trainer")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(120), nullable=False)
    description = Column(Text, nullable=False)
    price = Column(Numeric(10, 2), nullable=False, default=0)
    duration_days = Column(Integer, nullable=False, default=30)
    total_sessions = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user_subscriptions = relationship("UserSubscription", back_populates="subscription")


class UserSubscription(Base):
    __tablename__ = "user_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=False, index=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    remaining_sessions = Column(Integer, nullable=True)
    status = Column(String(32), nullable=False, default="active", index=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    user = relationship("User", back_populates="subscriptions")
    subscription = relationship("Subscription", back_populates="user_subscriptions")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=True, index=True)
    user_subscription_id = Column(Integer, ForeignKey("user_subscriptions.id"), nullable=True, index=True)
    trainer = Column(String(120), nullable=False)
    training_type = Column(String(120), nullable=False)
    date = Column(Date, nullable=False, index=True)
    time = Column(String(16), nullable=False)
    status = Column(String(32), default="new", nullable=False, index=True)
    comment = Column(Text, default="", nullable=False)
    trainer_comment = Column(Text, default="", nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

    client = relationship("Client", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
    trainer_profile = relationship("Trainer", back_populates="bookings")
    user_subscription = relationship("UserSubscription")
    history = relationship("WorkoutHistory", back_populates="booking", uselist=False, cascade="all, delete-orphan")


class WorkoutHistory(Base):
    __tablename__ = "workout_history"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False, unique=True, index=True)
    client_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    trainer_id = Column(Integer, ForeignKey("trainers.id"), nullable=True, index=True)
    notes = Column(Text, nullable=False, default="")
    completed_at = Column(DateTime, server_default=func.now(), nullable=False)

    booking = relationship("Booking", back_populates="history")
    trainer = relationship("Trainer", back_populates="workout_history")
