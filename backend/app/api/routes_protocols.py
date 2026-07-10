from fastapi import APIRouter

from app.schemas.protocols import ProtocolListResponse
from app.services.protocol_service import list_protocols

router = APIRouter(tags=["protocols"])


@router.get("/protocols", response_model=ProtocolListResponse)
def protocols() -> ProtocolListResponse:
    return list_protocols()
