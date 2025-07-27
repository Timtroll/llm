# backend/models.py

from pydantic import BaseModel


class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"

# Модель для валидации запросов
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str
    password: str
    role: str = "user"  # Изменено с roles на role


class UpdateUserRequest(BaseModel):
    username: str
    password: str | None = None
    role: str | None = None


class DeleteUserRequest(BaseModel):
    username: str


