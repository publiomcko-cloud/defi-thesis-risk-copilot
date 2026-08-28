from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import require_authenticated_user
from app.auth.schemas import UserContext
from app.customer_requests.schemas import (
    CustomerRequestCreateRequest,
    CustomerRequestResponse,
    CustomerRequestsResponse,
)
from app.customer_requests.service import (
    close_customer_request,
    create_customer_request,
    get_customer_request,
    list_customer_requests,
)
from app.db.session import get_db


router = APIRouter(prefix="/customer-requests", tags=["customer-requests"])


@router.post("", response_model=CustomerRequestResponse, status_code=201)
def create_request(
    request: CustomerRequestCreateRequest,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> CustomerRequestResponse:
    return create_customer_request(db, actor, request)


@router.get("", response_model=CustomerRequestsResponse)
def read_requests(
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> CustomerRequestsResponse:
    return CustomerRequestsResponse(items=list_customer_requests(db, actor))


@router.get("/{request_id}", response_model=CustomerRequestResponse)
def read_request(
    request_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> CustomerRequestResponse:
    return get_customer_request(db, actor, request_id)


@router.post("/{request_id}/close", response_model=CustomerRequestResponse)
def close_request(
    request_id: str,
    db: Session = Depends(get_db),
    actor: UserContext = Depends(require_authenticated_user),
) -> CustomerRequestResponse:
    return close_customer_request(db, actor, request_id)
