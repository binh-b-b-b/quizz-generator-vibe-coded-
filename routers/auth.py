from fastapi import APIRouter, Depends
from models.schemas import RegisterRequest, LoginRequest, TokenResponse, UserOut
from services.auth import create_user, authenticate_user, create_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut)
def register(body: RegisterRequest):
    """Create a new user account."""
    user = create_user(body.username, body.password)
    return UserOut(id=user["id"], username=user["username"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """Verify credentials and return a JWT token."""
    user = authenticate_user(body.username, body.password)
    token = create_token(user)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    """Return the currently logged-in user."""
    return UserOut(id=user["id"], username=user["username"])