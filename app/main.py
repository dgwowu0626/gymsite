from datetime import date, datetime, timedelta
import hashlib
import os
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload
from starlette.middleware.sessions import SessionMiddleware

from app.database import Base, SessionLocal, engine, get_db
from app.models import Booking, Client, Subscription, Trainer, User, UserProfile, UserSubscription, WorkoutHistory
from app.schemas import (
    AdminUserUpdate,
    AssignSubscriptionRequest,
    BookingCreate,
    BookingOut,
    BookingStatusUpdate,
    ClientDashboardOut,
    ClientHistoryOut,
    ClientNoteUpdate,
    LoginRequest,
    PublicMembershipOut,
    RegisterRequest,
    StatsOut,
    SubscriptionCreate,
    TrainerCreate,
    TrainerDashboardOut,
    TrainerOut,
    TrainerWorkoutComplete,
    UserBookingCreate,
    UserOut,
    UserSubscriptionOut,
)
from app.seed import seed_defaults


BASE_DIR = Path(__file__).resolve().parent.parent
GYM_NAME = "North Fit"
SESSION_SECRET = "north-fit-demo-secret"

app = FastAPI(title="Gym Site CRM")
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET, same_site="lax")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    salt_hex, digest_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return digest.hex() == digest_hex


def ensure_database() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_defaults(db)
    finally:
        db.close()


@app.on_event("startup")
def on_startup() -> None:
    ensure_database()


def normalize_phone(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip()


def normalize_email(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().lower()


def get_memberships(db: Session) -> list[Subscription]:
    return db.query(Subscription).filter(Subscription.is_active.is_(True)).order_by(Subscription.id.asc()).all()


def get_trainers_data(db: Session) -> list[Trainer]:
    return db.query(Trainer).order_by(Trainer.id.asc()).all()


def current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.trainer))
        .filter(User.id == user_id, User.is_active.is_(True))
        .first()
    )


def require_user(user: User | None = Depends(current_user_optional)) -> User:
    if user is None:
        raise HTTPException(status_code=401, detail="Auth required")
    return user


def require_role(*roles: str):
    def dependency(user: User = Depends(require_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return user

    return dependency


def get_base_context(db: Session, user: User | None) -> dict:
    memberships = get_memberships(db)
    dashboard_link = "/cabinet"
    if user and user.role == "admin":
        dashboard_link = "/admin"
    return {
        "gym_name": GYM_NAME,
        "trainers": get_trainers_data(db),
        "memberships": memberships,
        "current_user": user,
        "dashboard_link": dashboard_link,
    }


def find_user_by_login(db: Session, login: str) -> User | None:
    login = login.strip()
    if "@" in login:
        return (
            db.query(User)
            .options(joinedload(User.profile), joinedload(User.trainer))
            .filter(func.lower(User.email) == login.lower())
            .first()
        )
    return (
        db.query(User)
        .options(joinedload(User.profile), joinedload(User.trainer))
        .filter(User.phone == login)
        .first()
    )


def ensure_client_for_user(db: Session, user: User, name: str) -> Client:
    client = db.query(Client).filter(Client.user_id == user.id).first()
    if client:
        client.name = name
        client.phone = user.phone
        client.email = user.email
        return client

    if user.phone:
        client = db.query(Client).filter(Client.phone == user.phone).first()
        if client:
            client.user_id = user.id
            client.name = name
            client.email = user.email
            return client
    if user.email:
        client = db.query(Client).filter(func.lower(Client.email) == user.email.lower()).first()
        if client:
            client.user_id = user.id
            client.name = name
            client.phone = user.phone
            return client

    client = Client(
        user_id=user.id,
        name=name,
        phone=user.phone,
        email=user.email,
    )
    db.add(client)
    db.flush()
    return client


def find_trainer_by_name(db: Session, trainer_name: str) -> Trainer | None:
    return db.query(Trainer).filter(Trainer.name == trainer_name.strip()).first()


def resolve_trainer(
    db: Session,
    trainer_id: int | None = None,
    trainer_name: str | None = None,
) -> Trainer | None:
    if trainer_id:
        trainer = db.query(Trainer).filter(Trainer.id == trainer_id).first()
        if trainer:
            return trainer
    if trainer_name:
        return find_trainer_by_name(db, trainer_name)
    return None


def get_user_display_name(user: User) -> str:
    return user.profile.name if user.profile else (user.email or user.phone or f"User {user.id}")


def get_booking_query(db: Session):
    return (
        db.query(Booking)
        .options(
            joinedload(Booking.client),
            joinedload(Booking.user),
            joinedload(Booking.trainer_profile),
            joinedload(Booking.user_subscription).joinedload(UserSubscription.subscription),
        )
        .outerjoin(Client)
        .outerjoin(User, Booking.user_id == User.id)
    )


def get_active_subscription_for_training(
    db: Session,
    user_id: int,
    training_type: str,
) -> UserSubscription | None:
    normalized_type = training_type.strip()
    query = (
        db.query(UserSubscription)
        .options(joinedload(UserSubscription.subscription))
        .join(Subscription, UserSubscription.subscription_id == Subscription.id)
        .filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "active",
            UserSubscription.end_date >= date.today(),
            or_(UserSubscription.remaining_sessions.is_(None), UserSubscription.remaining_sessions > 0),
        )
        .order_by(UserSubscription.end_date.asc(), UserSubscription.id.asc())
    )

    active_items = query.all()
    for item in active_items:
        title = item.subscription.title
        if title == "Месячный абонемент":
            return item
        if title == normalized_type:
            return item
    return None


def update_subscription_after_completion(db: Session, booking: Booking) -> None:
    if booking.user_subscription_id:
        subscription = (
            db.query(UserSubscription)
            .filter(UserSubscription.id == booking.user_subscription_id, UserSubscription.status == "active")
            .first()
        )
    elif booking.user_id:
        subscription = get_active_subscription_for_training(db, booking.user_id, booking.training_type)
    else:
        return

    if subscription is None:
        return

    if subscription and subscription.remaining_sessions is not None and subscription.remaining_sessions > 0:
        subscription.remaining_sessions -= 1
        if subscription.remaining_sessions == 0:
            subscription.status = "used"


def create_user_subscription_assignment(
    db: Session,
    user_id: int,
    subscription: Subscription,
    start_date: date | None = None,
) -> UserSubscription:
    starts_at = start_date or date.today()
    assignment = UserSubscription(
        user_id=user_id,
        subscription_id=subscription.id,
        start_date=starts_at,
        end_date=starts_at + timedelta(days=subscription.duration_days),
        remaining_sessions=subscription.total_sessions,
        status="active",
    )
    db.add(assignment)
    db.flush()
    return assignment


def serialize_clients(clients: list[Client]) -> list[Client]:
    for client in clients:
        client.bookings.sort(key=lambda item: (item.date, item.time, item.id), reverse=True)
    return clients


def build_stats(db: Session) -> StatsOut:
    today = date.today()
    total_bookings = db.query(func.count(Booking.id)).scalar() or 0
    new_bookings = db.query(func.count(Booking.id)).filter(Booking.status == "new").scalar() or 0
    pending_bookings = db.query(func.count(Booking.id)).filter(Booking.status == "pending").scalar() or 0
    today_bookings = db.query(func.count(Booking.id)).filter(Booking.date == today).scalar() or 0
    completed_bookings = db.query(func.count(Booking.id)).filter(Booking.status == "completed").scalar() or 0
    total_clients = db.query(func.count(Client.id)).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0
    active_subscriptions = (
        db.query(func.count(UserSubscription.id)).filter(UserSubscription.status == "active").scalar() or 0
    )
    return StatsOut(
        total_bookings=total_bookings,
        new_bookings=new_bookings,
        pending_bookings=pending_bookings,
        today_bookings=today_bookings,
        completed_bookings=completed_bookings,
        total_clients=total_clients,
        total_users=total_users,
        active_subscriptions=active_subscriptions,
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    return templates.TemplateResponse("index.html", {"request": request, **get_base_context(db, user)})


@app.get("/memberships", response_class=HTMLResponse)
def memberships_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    return templates.TemplateResponse("memberships.html", {"request": request, **get_base_context(db, user)})


@app.get("/trainers", response_class=HTMLResponse)
def trainers_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    return templates.TemplateResponse("trainers.html", {"request": request, **get_base_context(db, user)})


@app.get("/booking", response_class=HTMLResponse)
def booking_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    return templates.TemplateResponse("booking.html", {"request": request, **get_base_context(db, user)})


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    if user:
        return RedirectResponse("/admin" if user.role == "admin" else "/cabinet", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, **get_base_context(db, None)})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db), user: User | None = Depends(current_user_optional)):
    if user:
        return RedirectResponse("/admin" if user.role == "admin" else "/cabinet", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request, **get_base_context(db, None)})


@app.get("/cabinet", response_class=HTMLResponse)
def cabinet_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(current_user_optional),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.role == "admin":
        return RedirectResponse("/admin", status_code=303)
    return templates.TemplateResponse("account.html", {"request": request, **get_base_context(db, user)})


@app.get("/admin", response_class=HTMLResponse)
def admin_page(
    request: Request,
    db: Session = Depends(get_db),
    user: User | None = Depends(current_user_optional),
):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.role != "admin":
        return RedirectResponse("/cabinet", status_code=303)
    return templates.TemplateResponse("admin.html", {"request": request, **get_base_context(db, user)})


@app.get("/logout")
def logout_page(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=303)


@app.get("/api/trainers", response_model=list[TrainerOut])
def list_trainers(db: Session = Depends(get_db)):
    return get_trainers_data(db)


@app.get("/api/memberships", response_model=list[PublicMembershipOut])
def list_memberships(db: Session = Depends(get_db)):
    return get_memberships(db)


@app.post("/api/auth/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    phone = normalize_phone(payload.phone)
    email = normalize_email(payload.email)

    if phone and db.query(User).filter(User.phone == phone).first():
        raise HTTPException(status_code=400, detail="Телефон уже зарегистрирован")
    if email and db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(status_code=400, detail="Email уже зарегистрирован")

    user = User(phone=phone, email=email, password_hash=hash_password(payload.password), role="client")
    user.profile = UserProfile(name=payload.name.strip())
    db.add(user)
    db.flush()
    ensure_client_for_user(db, user, payload.name.strip())
    db.commit()
    db.refresh(user)
    request.session["user_id"] = user.id
    return user


@app.post("/api/auth/login", response_model=UserOut)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = find_user_by_login(db, payload.login)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Пользователь отключён")
    request.session["user_id"] = user.id
    return user


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request):
    request.session.clear()


@app.get("/api/auth/me", response_model=UserOut | None)
def auth_me(user: User | None = Depends(current_user_optional)):
    return user


@app.post("/api/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_public_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    user: User | None = Depends(current_user_optional),
):
    phone = normalize_phone(payload.phone)
    client = ensure_client_for_user(db, user, payload.name.strip()) if user and user.role == "client" else db.query(Client).filter(Client.phone == phone).first()

    if client is None:
        client = Client(name=payload.name.strip(), phone=phone)
        db.add(client)
        db.flush()
    else:
        client.name = payload.name.strip()

    trainer_profile = resolve_trainer(db, payload.trainer_id, payload.trainer)
    trainer_name = trainer_profile.name if trainer_profile else (payload.trainer.strip() if payload.trainer else "Без тренера")
    booking = Booking(
        client_id=client.id,
        user_id=user.id if user and user.role == "client" else client.user_id,
        trainer_id=trainer_profile.id if trainer_profile else None,
        trainer=trainer_name,
        training_type=payload.training_type.strip(),
        date=payload.date,
        time=payload.time.strip(),
        status="new",
        comment=payload.comment.strip(),
    )
    db.add(booking)
    db.commit()
    return (
        get_booking_query(db)
        .filter(Booking.id == booking.id)
        .first()
    )


@app.get("/api/bookings", response_model=list[BookingOut])
def list_bookings(
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    booking_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    query = get_booking_query(db)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Client.name.ilike(pattern),
                Client.phone.ilike(pattern),
                Client.email.ilike(pattern),
                User.email.ilike(pattern),
            )
        )
    if status_filter:
        query = query.filter(Booking.status == status_filter)
    if booking_date:
        query = query.filter(Booking.date == booking_date)
    return query.order_by(Booking.date.desc(), Booking.time.desc(), Booking.id.desc()).all()


@app.patch("/api/bookings/{booking_id}/status", response_model=BookingOut)
def update_booking_status(
    booking_id: int,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    booking = get_booking_query(db).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = payload.status
    if payload.status == "completed":
        if booking.history is None and booking.trainer_id is not None:
            booking.history = WorkoutHistory(
                booking_id=booking.id,
                trainer_id=booking.trainer_id,
                client_user_id=booking.user_id,
                notes=booking.trainer_comment,
            )
        update_subscription_after_completion(db, booking)
    db.commit()
    return get_booking_query(db).filter(Booking.id == booking_id).first()


@app.delete("/api/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    db.delete(booking)
    db.commit()


@app.get("/api/clients", response_model=list[ClientHistoryOut])
def list_clients(
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    query = db.query(Client).options(joinedload(Client.bookings))
    if search:
        pattern = f"%{search.strip()}%"
        query = query.filter(or_(Client.name.ilike(pattern), Client.phone.ilike(pattern), Client.email.ilike(pattern)))
    return serialize_clients(query.order_by(Client.created_at.desc()).all())


@app.patch("/api/clients/{client_id}/note", response_model=ClientHistoryOut)
def update_client_note(
    client_id: int,
    payload: ClientNoteUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "trainer")),
):
    client = db.query(Client).options(joinedload(Client.bookings)).filter(Client.id == client_id).first()
    if client is None:
        raise HTTPException(status_code=404, detail="Client not found")
    if user.role == "trainer":
        trainer = db.query(Trainer).filter(Trainer.user_id == user.id).first()
        if trainer is None or not any(item.trainer_id == trainer.id for item in client.bookings):
            raise HTTPException(status_code=403, detail="Нет доступа к клиенту")
    client.note = payload.note.strip()
    db.commit()
    db.refresh(client)
    return serialize_clients([client])[0]


@app.get("/api/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    return build_stats(db)


@app.get("/api/me/dashboard", response_model=ClientDashboardOut)
def client_dashboard(db: Session = Depends(get_db), user: User = Depends(require_role("client"))):
    active_subscriptions = (
        db.query(UserSubscription)
        .options(joinedload(UserSubscription.subscription))
        .filter(UserSubscription.user_id == user.id)
        .order_by(UserSubscription.end_date.asc())
        .all()
    )
    upcoming = (
        get_booking_query(db)
        .filter(Booking.user_id == user.id, Booking.status.in_(["pending", "confirmed", "new"]))
        .order_by(Booking.date.asc(), Booking.time.asc())
        .all()
    )
    history = (
        get_booking_query(db)
        .filter(Booking.user_id == user.id, Booking.status.in_(["completed", "cancelled"]))
        .order_by(Booking.date.desc(), Booking.time.desc())
        .all()
    )
    return ClientDashboardOut(
        user=user,
        available_memberships=get_memberships(db),
        active_subscriptions=active_subscriptions,
        upcoming_bookings=upcoming,
        history=history,
    )


@app.post("/api/me/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_user_booking(
    payload: UserBookingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("client")),
):
    trainer = db.query(Trainer).filter(Trainer.id == payload.trainer_id).first() if payload.trainer_id else None
    client = ensure_client_for_user(db, user, get_user_display_name(user))

    linked_subscription = None
    if payload.training_type.strip() != "Разовый визит":
        linked_subscription = get_active_subscription_for_training(db, user.id, payload.training_type)
        if linked_subscription is None:
            raise HTTPException(
                status_code=400,
                detail="Для этой записи нужен активный абонемент с доступными посещениями",
            )

    booking = Booking(
        client_id=client.id,
        user_id=user.id,
        trainer_id=trainer.id if trainer else None,
        user_subscription_id=linked_subscription.id if linked_subscription else None,
        trainer=trainer.name if trainer else "Без тренера",
        training_type=payload.training_type.strip(),
        date=payload.date,
        time=payload.time.strip(),
        status="pending",
        comment=payload.comment.strip(),
    )
    db.add(booking)
    db.commit()
    return get_booking_query(db).filter(Booking.id == booking.id).first()


@app.post("/api/me/subscriptions/{subscription_id}/purchase", response_model=UserSubscriptionOut, status_code=status.HTTP_201_CREATED)
def purchase_subscription(
    subscription_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("client")),
):
    subscription = (
        db.query(Subscription)
        .filter(Subscription.id == subscription_id, Subscription.is_active.is_(True))
        .first()
    )
    if subscription is None:
        raise HTTPException(status_code=404, detail="Абонемент не найден")

    assignment = create_user_subscription_assignment(db, user.id, subscription)
    db.commit()
    return (
        db.query(UserSubscription)
        .options(joinedload(UserSubscription.subscription), joinedload(UserSubscription.user).joinedload(User.profile))
        .filter(UserSubscription.id == assignment.id)
        .first()
    )


@app.patch("/api/me/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel_user_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("client")),
):
    booking = get_booking_query(db).filter(Booking.id == booking_id, Booking.user_id == user.id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    if booking.status not in ["pending", "confirmed", "new"]:
        raise HTTPException(status_code=400, detail="Эту запись уже нельзя отменить")
    booking.status = "cancelled"
    db.commit()
    return get_booking_query(db).filter(Booking.id == booking.id).first()


@app.get("/api/trainer/dashboard", response_model=TrainerDashboardOut)
def trainer_dashboard(
    target_date: date | None = Query(default=None),
    db: Session = Depends(get_db),
    user: User = Depends(require_role("trainer")),
):
    trainer = db.query(Trainer).filter(Trainer.user_id == user.id).first()
    if trainer is None:
        raise HTTPException(status_code=404, detail="Trainer profile not found")

    base_date = target_date or date.today()
    week_end = base_date + timedelta(days=7)
    day_schedule = (
        get_booking_query(db)
        .filter(Booking.trainer_id == trainer.id, Booking.date == base_date)
        .order_by(Booking.time.asc())
        .all()
    )
    week_schedule = (
        get_booking_query(db)
        .filter(Booking.trainer_id == trainer.id, Booking.date >= base_date, Booking.date < week_end)
        .order_by(Booking.date.asc(), Booking.time.asc())
        .all()
    )
    clients = (
        db.query(Client)
        .join(Booking, Booking.client_id == Client.id)
        .filter(Booking.trainer_id == trainer.id)
        .distinct()
        .order_by(Client.name.asc())
        .all()
    )
    history = (
        db.query(WorkoutHistory)
        .filter(WorkoutHistory.trainer_id == trainer.id)
        .order_by(WorkoutHistory.completed_at.desc())
        .all()
    )
    return TrainerDashboardOut(
        trainer=trainer,
        day_schedule=day_schedule,
        week_schedule=week_schedule,
        clients=clients,
        workout_history=history,
    )


@app.patch("/api/trainer/bookings/{booking_id}/complete", response_model=BookingOut)
def complete_trainer_booking(
    booking_id: int,
    payload: TrainerWorkoutComplete,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("trainer")),
):
    trainer = db.query(Trainer).filter(Trainer.user_id == user.id).first()
    if trainer is None:
        raise HTTPException(status_code=404, detail="Trainer profile not found")
    booking = get_booking_query(db).filter(Booking.id == booking_id, Booking.trainer_id == trainer.id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking.status = "completed"
    booking.trainer_comment = payload.comment.strip()
    if booking.history is None:
        booking.history = WorkoutHistory(
            booking_id=booking.id,
            trainer_id=trainer.id,
            client_user_id=booking.user_id,
            notes=payload.comment.strip(),
        )
    else:
        booking.history.notes = payload.comment.strip()
        booking.history.completed_at = datetime.utcnow()
    update_subscription_after_completion(db, booking)
    db.commit()
    return get_booking_query(db).filter(Booking.id == booking.id).first()


@app.get("/api/admin/users", response_model=list[UserOut])
def admin_users(db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    return db.query(User).options(joinedload(User.profile)).order_by(User.created_at.desc()).all()


@app.patch("/api/admin/users/{user_id}", response_model=UserOut)
def update_admin_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    user = db.query(User).options(joinedload(User.profile)).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = payload.role
    user.is_active = payload.is_active
    if user.profile is None:
        user.profile = UserProfile(name=payload.name.strip())
    else:
        user.profile.name = payload.name.strip()
    db.commit()
    db.refresh(user)
    return user


@app.get("/api/admin/trainers", response_model=list[TrainerOut])
def admin_trainers(db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    return get_trainers_data(db)


@app.post("/api/admin/trainers", response_model=TrainerOut, status_code=status.HTTP_201_CREATED)
def create_admin_trainer(
    payload: TrainerCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    if payload.user_id:
        linked_user = db.query(User).filter(User.id == payload.user_id).first()
        if linked_user is None:
            raise HTTPException(status_code=404, detail="User not found")
        linked_user.role = "trainer"
    trainer = Trainer(**payload.model_dump())
    db.add(trainer)
    db.commit()
    db.refresh(trainer)
    return trainer


@app.patch("/api/admin/trainers/{trainer_id}", response_model=TrainerOut)
def update_admin_trainer(
    trainer_id: int,
    payload: TrainerCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    trainer = db.query(Trainer).filter(Trainer.id == trainer_id).first()
    if trainer is None:
        raise HTTPException(status_code=404, detail="Trainer not found")
    for key, value in payload.model_dump().items():
        setattr(trainer, key, value)
    if payload.user_id:
        linked_user = db.query(User).filter(User.id == payload.user_id).first()
        if linked_user:
            linked_user.role = "trainer"
    db.commit()
    db.refresh(trainer)
    return trainer


@app.get("/api/admin/subscriptions", response_model=list[PublicMembershipOut])
def admin_subscriptions(db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    return db.query(Subscription).order_by(Subscription.id.asc()).all()


@app.post("/api/admin/subscriptions", response_model=PublicMembershipOut, status_code=status.HTTP_201_CREATED)
def create_subscription(
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    subscription = Subscription(**payload.model_dump())
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


@app.patch("/api/admin/subscriptions/{subscription_id}", response_model=PublicMembershipOut)
def update_subscription(
    subscription_id: int,
    payload: SubscriptionCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    subscription = db.query(Subscription).filter(Subscription.id == subscription_id).first()
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    for key, value in payload.model_dump().items():
        setattr(subscription, key, value)
    db.commit()
    db.refresh(subscription)
    return subscription


@app.get("/api/admin/user-subscriptions", response_model=list[UserSubscriptionOut])
def admin_user_subscriptions(db: Session = Depends(get_db), _: User = Depends(require_role("admin"))):
    return (
        db.query(UserSubscription)
        .options(joinedload(UserSubscription.subscription), joinedload(UserSubscription.user).joinedload(User.profile))
        .order_by(UserSubscription.created_at.desc())
        .all()
    )


@app.post("/api/admin/subscriptions/assign", response_model=UserSubscriptionOut, status_code=status.HTTP_201_CREATED)
def assign_subscription(
    payload: AssignSubscriptionRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    user = db.query(User).filter(User.id == payload.user_id, User.role == "client").first()
    if user is None:
        raise HTTPException(status_code=404, detail="Client user not found")
    subscription = db.query(Subscription).filter(Subscription.id == payload.subscription_id).first()
    if subscription is None:
        raise HTTPException(status_code=404, detail="Subscription not found")
    assignment = UserSubscription(
        user_id=user.id,
        subscription_id=subscription.id,
        start_date=payload.start_date,
        end_date=payload.start_date + timedelta(days=subscription.duration_days),
        remaining_sessions=payload.remaining_sessions if payload.remaining_sessions is not None else subscription.total_sessions,
        status="active",
    )
    db.add(assignment)
    db.commit()
    return (
        db.query(UserSubscription)
        .options(joinedload(UserSubscription.subscription), joinedload(UserSubscription.user).joinedload(User.profile))
        .filter(UserSubscription.id == assignment.id)
        .first()
    )
