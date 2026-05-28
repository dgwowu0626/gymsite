from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, model_validator


UserRole = Literal["client", "trainer", "admin"]
BookingStatus = Literal["new", "pending", "confirmed", "cancelled", "completed"]


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    password: str = Field(min_length=6, max_length=120)

    @model_validator(mode="after")
    def validate_login_fields(self):
        if not self.phone and not self.email:
            raise ValueError("Укажите телефон или email")
        return self


class LoginRequest(BaseModel):
    login: str = Field(min_length=3, max_length=160)
    password: str = Field(min_length=6, max_length=120)


class UserProfileSummary(BaseModel):
    user_id: int
    name: str
    note: str

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: int
    phone: str | None
    email: str | None
    role: UserRole
    is_active: bool
    created_at: datetime
    profile: UserProfileSummary | None

    class Config:
        from_attributes = True


class AssignedUserSummary(BaseModel):
    id: int
    phone: str | None
    email: str | None
    profile: UserProfileSummary | None

    class Config:
        from_attributes = True


class TrainerOut(BaseModel):
    id: int
    user_id: int | None
    name: str
    specialization: str
    experience: str
    bio: str

    class Config:
        from_attributes = True


class PublicMembershipOut(BaseModel):
    id: int
    title: str
    description: str
    price: Decimal
    duration_days: int
    total_sessions: int | None

    class Config:
        from_attributes = True


class BookingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=32)
    date: date
    time: str = Field(min_length=1, max_length=16)
    training_type: str = Field(min_length=2, max_length=120)
    trainer: str | None = Field(default=None, max_length=120)
    trainer_id: int | None = None
    comment: str = Field(default="", max_length=1000)


class UserBookingCreate(BaseModel):
    trainer_id: int | None = None
    date: date
    time: str = Field(min_length=1, max_length=16)
    training_type: str = Field(min_length=2, max_length=120)
    comment: str = Field(default="", max_length=1000)


class BookingStatusUpdate(BaseModel):
    status: BookingStatus


class ClientNoteUpdate(BaseModel):
    note: str = Field(default="", max_length=2000)


class TrainerWorkoutComplete(BaseModel):
    comment: str = Field(default="", max_length=2000)


class AdminUserUpdate(BaseModel):
    role: UserRole
    is_active: bool = True
    name: str = Field(min_length=2, max_length=120)


class TrainerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    specialization: str = Field(min_length=2, max_length=200)
    experience: str = Field(min_length=2, max_length=120)
    bio: str = Field(default="", max_length=2000)
    user_id: int | None = None


class SubscriptionCreate(BaseModel):
    title: str = Field(min_length=2, max_length=120)
    description: str = Field(min_length=2, max_length=2000)
    price: Decimal = Field(ge=0)
    duration_days: int = Field(ge=1, le=3650)
    total_sessions: int | None = Field(default=None, ge=1, le=1000)
    is_active: bool = True


class AssignSubscriptionRequest(BaseModel):
    user_id: int
    subscription_id: int
    start_date: date
    remaining_sessions: int | None = Field(default=None, ge=0, le=1000)


class ClientOut(BaseModel):
    id: int
    user_id: int | None
    name: str
    phone: str | None
    email: str | None
    note: str
    created_at: datetime

    class Config:
        from_attributes = True


class BookingClientSummary(BaseModel):
    id: int
    name: str
    phone: str | None
    email: str | None

    class Config:
        from_attributes = True


class BookingUserSummary(BaseModel):
    id: int
    phone: str | None
    email: str | None

    class Config:
        from_attributes = True


class BookingOut(BaseModel):
    id: int
    client_id: int | None
    user_id: int | None
    trainer_id: int | None
    user_subscription_id: int | None
    trainer: str
    training_type: str
    date: date
    time: str
    status: BookingStatus
    comment: str
    trainer_comment: str
    created_at: datetime
    client: BookingClientSummary | None
    user: BookingUserSummary | None

    class Config:
        from_attributes = True


class ClientBookingOut(BaseModel):
    id: int
    trainer: str
    training_type: str
    date: date
    time: str
    status: BookingStatus
    comment: str
    trainer_comment: str
    created_at: datetime

    class Config:
        from_attributes = True


class ClientHistoryOut(ClientOut):
    bookings: list[ClientBookingOut]


class UserSubscriptionOut(BaseModel):
    id: int
    user_id: int
    start_date: date
    end_date: date
    remaining_sessions: int | None
    status: str
    user: AssignedUserSummary | None
    subscription: PublicMembershipOut

    class Config:
        from_attributes = True


class WorkoutHistoryOut(BaseModel):
    id: int
    booking_id: int
    trainer_id: int
    notes: str
    completed_at: datetime

    class Config:
        from_attributes = True


class ClientDashboardOut(BaseModel):
    user: UserOut
    available_memberships: list[PublicMembershipOut]
    active_subscriptions: list[UserSubscriptionOut]
    upcoming_bookings: list[BookingOut]
    history: list[BookingOut]


class TrainerDashboardOut(BaseModel):
    trainer: TrainerOut
    day_schedule: list[BookingOut]
    week_schedule: list[BookingOut]
    clients: list[ClientOut]
    workout_history: list[WorkoutHistoryOut]


class StatsOut(BaseModel):
    total_bookings: int
    new_bookings: int
    pending_bookings: int
    today_bookings: int
    completed_bookings: int
    total_clients: int
    total_users: int
    active_subscriptions: int
