from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class PlayerRole(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ROLE_UNSPECIFIED: _ClassVar[PlayerRole]
    ROLE_PLUMBER: _ClassVar[PlayerRole]
    ROLE_HYDRAULIC_ENGINEER: _ClassVar[PlayerRole]
    ROLE_CHEMICAL_OPERATOR: _ClassVar[PlayerRole]
    ROLE_GENERALIST: _ClassVar[PlayerRole]
ROLE_UNSPECIFIED: PlayerRole
ROLE_PLUMBER: PlayerRole
ROLE_HYDRAULIC_ENGINEER: PlayerRole
ROLE_CHEMICAL_OPERATOR: PlayerRole
ROLE_GENERALIST: PlayerRole

class Vector2D(_message.Message):
    __slots__ = ("x", "y")
    X_FIELD_NUMBER: _ClassVar[int]
    Y_FIELD_NUMBER: _ClassVar[int]
    x: float
    y: float
    def __init__(self, x: _Optional[float] = ..., y: _Optional[float] = ...) -> None: ...

class WaterMetrics(_message.Message):
    __slots__ = ("reservoir_level_pct", "water_purity_pct", "total_liters_saved", "total_liters_reused", "total_liters_recycled")
    RESERVOIR_LEVEL_PCT_FIELD_NUMBER: _ClassVar[int]
    WATER_PURITY_PCT_FIELD_NUMBER: _ClassVar[int]
    TOTAL_LITERS_SAVED_FIELD_NUMBER: _ClassVar[int]
    TOTAL_LITERS_REUSED_FIELD_NUMBER: _ClassVar[int]
    TOTAL_LITERS_RECYCLED_FIELD_NUMBER: _ClassVar[int]
    reservoir_level_pct: float
    water_purity_pct: float
    total_liters_saved: float
    total_liters_reused: float
    total_liters_recycled: float
    def __init__(self, reservoir_level_pct: _Optional[float] = ..., water_purity_pct: _Optional[float] = ..., total_liters_saved: _Optional[float] = ..., total_liters_reused: _Optional[float] = ..., total_liters_recycled: _Optional[float] = ...) -> None: ...

class PingMessage(_message.Message):
    __slots__ = ("client_timestamp_ms", "sequence_id")
    CLIENT_TIMESTAMP_MS_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_ID_FIELD_NUMBER: _ClassVar[int]
    client_timestamp_ms: int
    sequence_id: int
    def __init__(self, client_timestamp_ms: _Optional[int] = ..., sequence_id: _Optional[int] = ...) -> None: ...

class PongMessage(_message.Message):
    __slots__ = ("echo_client_timestamp_ms", "server_tick", "server_timestamp_ms")
    ECHO_CLIENT_TIMESTAMP_MS_FIELD_NUMBER: _ClassVar[int]
    SERVER_TICK_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIMESTAMP_MS_FIELD_NUMBER: _ClassVar[int]
    echo_client_timestamp_ms: int
    server_tick: int
    server_timestamp_ms: int
    def __init__(self, echo_client_timestamp_ms: _Optional[int] = ..., server_tick: _Optional[int] = ..., server_timestamp_ms: _Optional[int] = ...) -> None: ...
