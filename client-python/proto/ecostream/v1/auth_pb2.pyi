from ecostream.v1 import common_pb2 as _common_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class UserProfile(_message.Message):
    __slots__ = ("user_id", "username", "email", "default_role", "games_played", "games_won", "total_eco_score", "created_at")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ROLE_FIELD_NUMBER: _ClassVar[int]
    GAMES_PLAYED_FIELD_NUMBER: _ClassVar[int]
    GAMES_WON_FIELD_NUMBER: _ClassVar[int]
    TOTAL_ECO_SCORE_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    username: str
    email: str
    default_role: _common_pb2.PlayerRole
    games_played: int
    games_won: int
    total_eco_score: float
    created_at: str
    def __init__(self, user_id: _Optional[str] = ..., username: _Optional[str] = ..., email: _Optional[str] = ..., default_role: _Optional[_Union[_common_pb2.PlayerRole, str]] = ..., games_played: _Optional[int] = ..., games_won: _Optional[int] = ..., total_eco_score: _Optional[float] = ..., created_at: _Optional[str] = ...) -> None: ...

class RegisterRequest(_message.Message):
    __slots__ = ("username", "email", "password", "default_role")
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    EMAIL_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ROLE_FIELD_NUMBER: _ClassVar[int]
    username: str
    email: str
    password: str
    default_role: _common_pb2.PlayerRole
    def __init__(self, username: _Optional[str] = ..., email: _Optional[str] = ..., password: _Optional[str] = ..., default_role: _Optional[_Union[_common_pb2.PlayerRole, str]] = ...) -> None: ...

class RegisterResponse(_message.Message):
    __slots__ = ("success", "message", "token", "user", "expires_at_unix")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_UNIX_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    token: str
    user: UserProfile
    expires_at_unix: int
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ..., token: _Optional[str] = ..., user: _Optional[_Union[UserProfile, _Mapping]] = ..., expires_at_unix: _Optional[int] = ...) -> None: ...

class LoginRequest(_message.Message):
    __slots__ = ("username_or_email", "password")
    USERNAME_OR_EMAIL_FIELD_NUMBER: _ClassVar[int]
    PASSWORD_FIELD_NUMBER: _ClassVar[int]
    username_or_email: str
    password: str
    def __init__(self, username_or_email: _Optional[str] = ..., password: _Optional[str] = ...) -> None: ...

class LoginResponse(_message.Message):
    __slots__ = ("success", "message", "token", "user", "expires_at_unix")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_UNIX_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    token: str
    user: UserProfile
    expires_at_unix: int
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ..., token: _Optional[str] = ..., user: _Optional[_Union[UserProfile, _Mapping]] = ..., expires_at_unix: _Optional[int] = ...) -> None: ...

class VerifyTokenRequest(_message.Message):
    __slots__ = ("token",)
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    token: str
    def __init__(self, token: _Optional[str] = ...) -> None: ...

class VerifyTokenResponse(_message.Message):
    __slots__ = ("valid", "user_id", "username", "role", "message")
    VALID_FIELD_NUMBER: _ClassVar[int]
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    valid: bool
    user_id: str
    username: str
    role: _common_pb2.PlayerRole
    message: str
    def __init__(self, valid: _Optional[bool] = ..., user_id: _Optional[str] = ..., username: _Optional[str] = ..., role: _Optional[_Union[_common_pb2.PlayerRole, str]] = ..., message: _Optional[str] = ...) -> None: ...

class GetProfileRequest(_message.Message):
    __slots__ = ("user_id",)
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    def __init__(self, user_id: _Optional[str] = ...) -> None: ...

class GetProfileResponse(_message.Message):
    __slots__ = ("success", "user", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    USER_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    user: UserProfile
    error: str
    def __init__(self, success: _Optional[bool] = ..., user: _Optional[_Union[UserProfile, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...
