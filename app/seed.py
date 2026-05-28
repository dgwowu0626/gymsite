from datetime import date, timedelta
from decimal import Decimal
import hashlib
import os

from sqlalchemy.orm import Session

from app.models import Subscription, Trainer, User, UserProfile


TRAINERS = [
    {
        "name": "Алексей Воронцов",
        "specialization": "Силовые тренировки и набор мышечной массы",
        "experience": "6 лет опыта",
        "bio": "Работает с базовыми силовыми циклами и техничным прогрессом без перегруза.",
        "login_phone": "+79990000001",
    },
    {
        "name": "Марина Белова",
        "specialization": "Функциональный тренинг и снижение веса",
        "experience": "5 лет опыта",
        "bio": "Собирает регулярные планы для снижения веса и устойчивого режима.",
        "login_phone": "+79990000002",
    },
    {
        "name": "Игорь Соколов",
        "specialization": "Персональные программы и реабилитационный фитнес",
        "experience": "8 лет опыта",
        "bio": "Ведёт восстановительные и персональные занятия с акцентом на безопасность.",
        "login_phone": "+79990000003",
    },
]

SUBSCRIPTIONS = [
    {
        "title": "Разовый визит",
        "description": "Подходит для знакомства с залом или разовой тренировки.",
        "price": Decimal("700"),
        "duration_days": 1,
        "total_sessions": 1,
    },
    {
        "title": "Месячный абонемент",
        "description": "Свободное посещение зала каждый день в часы работы.",
        "price": Decimal("3900"),
        "duration_days": 30,
        "total_sessions": 30,
    },
    {
        "title": "Персональные тренировки",
        "description": "Индивидуальная программа с тренером под вашу цель.",
        "price": Decimal("1800"),
        "duration_days": 30,
        "total_sessions": 8,
    },
    {
        "title": "Групповые занятия",
        "description": "Функциональные и круговые тренировки в мини-группах.",
        "price": Decimal("2500"),
        "duration_days": 30,
        "total_sessions": 12,
    },
]


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return f"{salt.hex()}:{digest.hex()}"


def seed_defaults(db: Session) -> None:
    if db.query(User).count() == 0:
        admin = User(
            phone="+79990000000",
            email="admin@northfit.local",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        admin.profile = UserProfile(name="Администратор North Fit")
        db.add(admin)
        db.flush()

        for index, item in enumerate(TRAINERS, start=1):
            user = User(
                phone=item["login_phone"],
                email=f"trainer{index}@northfit.local",
                password_hash=hash_password("trainer123"),
                role="trainer",
            )
            user.profile = UserProfile(name=item["name"])
            db.add(user)
            db.flush()
            db.add(
                Trainer(
                    user_id=user.id,
                    name=item["name"],
                    specialization=item["specialization"],
                    experience=item["experience"],
                    bio=item["bio"],
                )
            )

    existing_subscriptions = {item.title: item for item in db.query(Subscription).all()}
    for item in SUBSCRIPTIONS:
        subscription = existing_subscriptions.get(item["title"])
        if subscription is None:
            db.add(Subscription(**item))
            continue
        subscription.description = item["description"]
        subscription.price = item["price"]
        subscription.duration_days = item["duration_days"]
        subscription.total_sessions = item["total_sessions"]
        subscription.is_active = True

    db.commit()
