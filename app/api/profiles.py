from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.deps import get_db
from app.api.deps import get_current_user
from app.db.models import CustomerProfileDB, UserDB
from app.schemas.customer import CheckoutProfileOut

router = APIRouter(prefix="/me", tags=["me"])


@router.get("/checkout-profile", response_model=CheckoutProfileOut | None)
def get_checkout_profile(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    profile = db.execute(
        select(CustomerProfileDB).where(CustomerProfileDB.user_id == current_user.id)
    ).scalar_one_or_none()

    if not profile:
        return None

    return CheckoutProfileOut(
        first_name=profile.first_name,
        last_name=profile.last_name,
        phone=profile.phone,
        address_line1=profile.address_line1,
        address_line2=profile.address_line2,
        city=profile.city,
        postal_code=profile.postal_code,
        country=profile.country,
    )
