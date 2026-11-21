from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_membership, require_role
from app.api.schemas.offer import (
    OfferCreate,
    OfferOut,
    OfferUpdate,
    RedemptionOut,
    RedemptionUpdate,
)
from app.core.security import get_current_user
from app.db.session import get_db
from app.domain.jukebox import JukeboxMember, Role
from app.domain.user import User
from app.services import audit_service, offer_service

router = APIRouter(tags=["offers"])


@router.get("/jukeboxes/{jukebox_id}/offers", response_model=list[OfferOut])
async def list_offers(
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> list[OfferOut]:
    return await offer_service.list_offers(db, member)


@router.post(
    "/jukeboxes/{jukebox_id}/offers", response_model=OfferOut, status_code=status.HTTP_201_CREATED
)
async def create_offer(
    payload: OfferCreate,
    request: Request,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> OfferOut:
    offer = await offer_service.create_offer(db, member, payload)
    await audit_service.log_action(
        db,
        action="offer.create",
        user_id=member.user_id,
        resource_type="offer",
        resource_id=offer.id,
        detail={"jukebox_id": member.jukebox_id},
        request=request,
    )
    await db.commit()
    return offer


@router.patch("/jukeboxes/{jukebox_id}/offers/{offer_id}", response_model=OfferOut)
async def update_offer(
    offer_id: int,
    payload: OfferUpdate,
    request: Request,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> OfferOut:
    offer = await offer_service.update_offer(db, member, offer_id, payload)
    await audit_service.log_action(
        db,
        action="offer.update",
        user_id=member.user_id,
        resource_type="offer",
        resource_id=offer.id,
        request=request,
    )
    await db.commit()
    return offer


@router.post("/jukeboxes/{jukebox_id}/offers/{offer_id}/claim", response_model=OfferOut)
async def claim_offer(
    offer_id: int,
    request: Request,
    member: JukeboxMember = Depends(get_membership),
    db: AsyncSession = Depends(get_db),
) -> OfferOut:
    offer = await offer_service.claim_offer(db, member, offer_id)
    await audit_service.log_action(
        db,
        action="offer.claim",
        user_id=member.user_id,
        resource_type="offer",
        resource_id=offer.id,
        detail={"jukebox_id": member.jukebox_id},
        request=request,
    )
    await db.commit()
    return offer


@router.get("/jukeboxes/{jukebox_id}/redemptions", response_model=list[RedemptionOut])
async def list_redemptions(
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> list[RedemptionOut]:
    return await offer_service.list_redemptions(db, member)


@router.patch(
    "/jukeboxes/{jukebox_id}/redemptions/{redemption_id}", response_model=RedemptionOut
)
async def update_redemption(
    redemption_id: int,
    payload: RedemptionUpdate,
    request: Request,
    member: JukeboxMember = Depends(require_role(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> RedemptionOut:
    redemption = await offer_service.update_redemption(db, member, redemption_id, payload)
    await audit_service.log_action(
        db,
        action="redemption.update",
        user_id=member.user_id,
        resource_type="offer_redemption",
        resource_id=redemption.id,
        detail={"status": redemption.status},
        request=request,
    )
    await db.commit()
    return redemption


@router.get("/users/me/redemptions", response_model=list[RedemptionOut])
async def my_redemptions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RedemptionOut]:
    return await offer_service.my_redemptions(db, current_user.id)
