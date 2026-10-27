from ecostream.v1 import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RoomStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ROOM_STATUS_UNSPECIFIED: _ClassVar[RoomStatus]
    ROOM_STATUS_WAITING: _ClassVar[RoomStatus]
    ROOM_STATUS_STARTING: _ClassVar[RoomStatus]
    ROOM_STATUS_IN_PROGRESS: _ClassVar[RoomStatus]
    ROOM_STATUS_FINISHED: _ClassVar[RoomStatus]
ROOM_STATUS_UNSPECIFIED: RoomStatus
ROOM_STATUS_WAITING: RoomStatus
ROOM_STATUS_STARTING: RoomStatus
ROOM_STATUS_IN_PROGRESS: RoomStatus
ROOM_STATUS_FINISHED: RoomStatus

class PlayerSlot(_message.Message):
    __slots__ = ("user_id", "username", "selected_role", "is_host", "is_ready", "is_bot")
    USER_ID_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    SELECTED_ROLE_FIELD_NUMBER: _ClassVar[int]
    IS_HOST_FIELD_NUMBER: _ClassVar[int]
    IS_READY_FIELD_NUMBER: _ClassVar[int]
    IS_BOT_FIELD_NUMBER: _ClassVar[int]
    user_id: str
    username: str
    selected_role: _common_pb2.PlayerRole
    is_host: bool
    is_ready: bool
    is_bot: bool
    def __init__(self, user_id: _Optional[str] = ..., username: _Optional[str] = ..., selected_role: _Optional[_Union[_common_pb2.PlayerRole, str]] = ..., is_host: _Optional[bool] = ..., is_ready: _Optional[bool] = ..., is_bot: _Optional[bool] = ...) -> None: ...

class RoomInfo(_message.Message):
    __slots__ = ("room_id", "room_code", "room_name", "status", "max_players", "players", "simulation_endpoint", "created_at_unix", "difficulty_level")
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    ROOM_CODE_FIELD_NUMBER: _ClassVar[int]
    ROOM_NAME_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    MAX_PLAYERS_FIELD_NUMBER: _ClassVar[int]
    PLAYERS_FIELD_NUMBER: _ClassVar[int]
    SIMULATION_ENDPOINT_FIELD_NUMBER: _ClassVar[int]
    CREATED_AT_UNIX_FIELD_NUMBER: _ClassVar[int]
    DIFFICULTY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    room_id: str
    room_code: str
    room_name: str
    status: RoomStatus
    max_players: int
    players: _containers.RepeatedCompositeFieldContainer[PlayerSlot]
    simulation_endpoint: str
    created_at_unix: int
    difficulty_level: int
    def __init__(self, room_id: _Optional[str] = ..., room_code: _Optional[str] = ..., room_name: _Optional[str] = ..., status: _Optional[_Union[RoomStatus, str]] = ..., max_players: _Optional[int] = ..., players: _Optional[_Iterable[_Union[PlayerSlot, _Mapping]]] = ..., simulation_endpoint: _Optional[str] = ..., created_at_unix: _Optional[int] = ..., difficulty_level: _Optional[int] = ...) -> None: ...

class CreateRoomRequest(_message.Message):
    __slots__ = ("token", "room_name", "selected_role", "max_players", "difficulty_level")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    ROOM_NAME_FIELD_NUMBER: _ClassVar[int]
    SELECTED_ROLE_FIELD_NUMBER: _ClassVar[int]
    MAX_PLAYERS_FIELD_NUMBER: _ClassVar[int]
    DIFFICULTY_LEVEL_FIELD_NUMBER: _ClassVar[int]
    token: str
    room_name: str
    selected_role: _common_pb2.PlayerRole
    max_players: int
    difficulty_level: int
    def __init__(self, token: _Optional[str] = ..., room_name: _Optional[str] = ..., selected_role: _Optional[_Union[_common_pb2.PlayerRole, str]] = ..., max_players: _Optional[int] = ..., difficulty_level: _Optional[int] = ...) -> None: ...

class CreateRoomResponse(_message.Message):
    __slots__ = ("success", "message", "room", "room_ticket")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ROOM_FIELD_NUMBER: _ClassVar[int]
    ROOM_TICKET_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    room: RoomInfo
    room_ticket: str
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ..., room: _Optional[_Union[RoomInfo, _Mapping]] = ..., room_ticket: _Optional[str] = ...) -> None: ...

class JoinRoomRequest(_message.Message):
    __slots__ = ("token", "room_code", "selected_role")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    ROOM_CODE_FIELD_NUMBER: _ClassVar[int]
    SELECTED_ROLE_FIELD_NUMBER: _ClassVar[int]
    token: str
    room_code: str
    selected_role: _common_pb2.PlayerRole
    def __init__(self, token: _Optional[str] = ..., room_code: _Optional[str] = ..., selected_role: _Optional[_Union[_common_pb2.PlayerRole, str]] = ...) -> None: ...

class JoinRoomResponse(_message.Message):
    __slots__ = ("success", "message", "room", "room_ticket")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ROOM_FIELD_NUMBER: _ClassVar[int]
    ROOM_TICKET_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    room: RoomInfo
    room_ticket: str
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ..., room: _Optional[_Union[RoomInfo, _Mapping]] = ..., room_ticket: _Optional[str] = ...) -> None: ...

class QuickMatchRequest(_message.Message):
    __slots__ = ("token", "preferred_role")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    PREFERRED_ROLE_FIELD_NUMBER: _ClassVar[int]
    token: str
    preferred_role: _common_pb2.PlayerRole
    def __init__(self, token: _Optional[str] = ..., preferred_role: _Optional[_Union[_common_pb2.PlayerRole, str]] = ...) -> None: ...

class QuickMatchResponse(_message.Message):
    __slots__ = ("success", "message", "room", "room_ticket")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ROOM_FIELD_NUMBER: _ClassVar[int]
    ROOM_TICKET_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    room: RoomInfo
    room_ticket: str
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ..., room: _Optional[_Union[RoomInfo, _Mapping]] = ..., room_ticket: _Optional[str] = ...) -> None: ...

class LeaveRoomRequest(_message.Message):
    __slots__ = ("token", "room_id")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    token: str
    room_id: str
    def __init__(self, token: _Optional[str] = ..., room_id: _Optional[str] = ...) -> None: ...

class LeaveRoomResponse(_message.Message):
    __slots__ = ("success", "message")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ...) -> None: ...

class GetRoomStatusRequest(_message.Message):
    __slots__ = ("token", "room_id")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    token: str
    room_id: str
    def __init__(self, token: _Optional[str] = ..., room_id: _Optional[str] = ...) -> None: ...

class GetRoomStatusResponse(_message.Message):
    __slots__ = ("success", "message", "room")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ROOM_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    room: RoomInfo
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ..., room: _Optional[_Union[RoomInfo, _Mapping]] = ...) -> None: ...

class StartMatchRequest(_message.Message):
    __slots__ = ("token", "room_id", "fill_with_bots")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    FILL_WITH_BOTS_FIELD_NUMBER: _ClassVar[int]
    token: str
    room_id: str
    fill_with_bots: bool
    def __init__(self, token: _Optional[str] = ..., room_id: _Optional[str] = ..., fill_with_bots: _Optional[bool] = ...) -> None: ...

class StartMatchResponse(_message.Message):
    __slots__ = ("success", "message", "room", "room_ticket")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    ROOM_FIELD_NUMBER: _ClassVar[int]
    ROOM_TICKET_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    room: RoomInfo
    room_ticket: str
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ..., room: _Optional[_Union[RoomInfo, _Mapping]] = ..., room_ticket: _Optional[str] = ...) -> None: ...

class ListAvailableRoomsRequest(_message.Message):
    __slots__ = ("token", "page_size")
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    PAGE_SIZE_FIELD_NUMBER: _ClassVar[int]
    token: str
    page_size: int
    def __init__(self, token: _Optional[str] = ..., page_size: _Optional[int] = ...) -> None: ...

class ListAvailableRoomsResponse(_message.Message):
    __slots__ = ("success", "rooms")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ROOMS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    rooms: _containers.RepeatedCompositeFieldContainer[RoomInfo]
    def __init__(self, success: _Optional[bool] = ..., rooms: _Optional[_Iterable[_Union[RoomInfo, _Mapping]]] = ...) -> None: ...
