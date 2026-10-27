from ecostream.v1 import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class WaterDestination(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DESTINATION_UNSPECIFIED: _ClassVar[WaterDestination]
    DESTINATION_SEWER: _ClassVar[WaterDestination]
    DESTINATION_IRRIGATION: _ClassVar[WaterDestination]
    DESTINATION_RECYCLE_PLANT: _ClassVar[WaterDestination]
DESTINATION_UNSPECIFIED: WaterDestination
DESTINATION_SEWER: WaterDestination
DESTINATION_IRRIGATION: WaterDestination
DESTINATION_RECYCLE_PLANT: WaterDestination

class ClientStreamMessage(_message.Message):
    __slots__ = ("room_id", "player_id", "client_tick", "action", "ping", "heartbeat")
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    PLAYER_ID_FIELD_NUMBER: _ClassVar[int]
    CLIENT_TICK_FIELD_NUMBER: _ClassVar[int]
    ACTION_FIELD_NUMBER: _ClassVar[int]
    PING_FIELD_NUMBER: _ClassVar[int]
    HEARTBEAT_FIELD_NUMBER: _ClassVar[int]
    room_id: str
    player_id: str
    client_tick: int
    action: PlayerAction
    ping: _common_pb2.PingMessage
    heartbeat: HeartbeatMessage
    def __init__(self, room_id: _Optional[str] = ..., player_id: _Optional[str] = ..., client_tick: _Optional[int] = ..., action: _Optional[_Union[PlayerAction, _Mapping]] = ..., ping: _Optional[_Union[_common_pb2.PingMessage, _Mapping]] = ..., heartbeat: _Optional[_Union[HeartbeatMessage, _Mapping]] = ...) -> None: ...

class HeartbeatMessage(_message.Message):
    __slots__ = ("timestamp_unix_ms",)
    TIMESTAMP_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    timestamp_unix_ms: int
    def __init__(self, timestamp_unix_ms: _Optional[int] = ...) -> None: ...

class PlayerAction(_message.Message):
    __slots__ = ("action_id", "move", "repair_pipe", "divert_valve", "operate_recycle", "interact")
    ACTION_ID_FIELD_NUMBER: _ClassVar[int]
    MOVE_FIELD_NUMBER: _ClassVar[int]
    REPAIR_PIPE_FIELD_NUMBER: _ClassVar[int]
    DIVERT_VALVE_FIELD_NUMBER: _ClassVar[int]
    OPERATE_RECYCLE_FIELD_NUMBER: _ClassVar[int]
    INTERACT_FIELD_NUMBER: _ClassVar[int]
    action_id: int
    move: MoveAction
    repair_pipe: RepairPipeAction
    divert_valve: DivertValveAction
    operate_recycle: OperateRecycleAction
    interact: InteractObjectAction
    def __init__(self, action_id: _Optional[int] = ..., move: _Optional[_Union[MoveAction, _Mapping]] = ..., repair_pipe: _Optional[_Union[RepairPipeAction, _Mapping]] = ..., divert_valve: _Optional[_Union[DivertValveAction, _Mapping]] = ..., operate_recycle: _Optional[_Union[OperateRecycleAction, _Mapping]] = ..., interact: _Optional[_Union[InteractObjectAction, _Mapping]] = ...) -> None: ...

class MoveAction(_message.Message):
    __slots__ = ("target_position", "velocity")
    TARGET_POSITION_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    target_position: _common_pb2.Vector2D
    velocity: _common_pb2.Vector2D
    def __init__(self, target_position: _Optional[_Union[_common_pb2.Vector2D, _Mapping]] = ..., velocity: _Optional[_Union[_common_pb2.Vector2D, _Mapping]] = ...) -> None: ...

class RepairPipeAction(_message.Message):
    __slots__ = ("pipe_id", "repair_progress_delta")
    PIPE_ID_FIELD_NUMBER: _ClassVar[int]
    REPAIR_PROGRESS_DELTA_FIELD_NUMBER: _ClassVar[int]
    pipe_id: int
    repair_progress_delta: float
    def __init__(self, pipe_id: _Optional[int] = ..., repair_progress_delta: _Optional[float] = ...) -> None: ...

class DivertValveAction(_message.Message):
    __slots__ = ("valve_id", "destination")
    VALVE_ID_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_FIELD_NUMBER: _ClassVar[int]
    valve_id: int
    destination: WaterDestination
    def __init__(self, valve_id: _Optional[int] = ..., destination: _Optional[_Union[WaterDestination, str]] = ...) -> None: ...

class OperateRecycleAction(_message.Message):
    __slots__ = ("plant_id", "operation")
    class RecycleOp(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        RECYCLE_OP_LOAD_FILTER: _ClassVar[OperateRecycleAction.RecycleOp]
        RECYCLE_OP_FLUSH_SLUDGE: _ClassVar[OperateRecycleAction.RecycleOp]
        RECYCLE_OP_BOOST_PUMP: _ClassVar[OperateRecycleAction.RecycleOp]
    RECYCLE_OP_LOAD_FILTER: OperateRecycleAction.RecycleOp
    RECYCLE_OP_FLUSH_SLUDGE: OperateRecycleAction.RecycleOp
    RECYCLE_OP_BOOST_PUMP: OperateRecycleAction.RecycleOp
    PLANT_ID_FIELD_NUMBER: _ClassVar[int]
    OPERATION_FIELD_NUMBER: _ClassVar[int]
    plant_id: int
    operation: OperateRecycleAction.RecycleOp
    def __init__(self, plant_id: _Optional[int] = ..., operation: _Optional[_Union[OperateRecycleAction.RecycleOp, str]] = ...) -> None: ...

class InteractObjectAction(_message.Message):
    __slots__ = ("object_id", "interaction_type")
    OBJECT_ID_FIELD_NUMBER: _ClassVar[int]
    INTERACTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    object_id: int
    interaction_type: str
    def __init__(self, object_id: _Optional[int] = ..., interaction_type: _Optional[str] = ...) -> None: ...

class ServerStreamMessage(_message.Message):
    __slots__ = ("server_tick", "server_timestamp_unix_ms", "world_state", "pong", "initial_snapshot", "match_end", "alert")
    SERVER_TICK_FIELD_NUMBER: _ClassVar[int]
    SERVER_TIMESTAMP_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    WORLD_STATE_FIELD_NUMBER: _ClassVar[int]
    PONG_FIELD_NUMBER: _ClassVar[int]
    INITIAL_SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    MATCH_END_FIELD_NUMBER: _ClassVar[int]
    ALERT_FIELD_NUMBER: _ClassVar[int]
    server_tick: int
    server_timestamp_unix_ms: int
    world_state: GameWorldState
    pong: _common_pb2.PongMessage
    initial_snapshot: GameWorldSnapshot
    match_end: MatchEndEvent
    alert: EventNotification
    def __init__(self, server_tick: _Optional[int] = ..., server_timestamp_unix_ms: _Optional[int] = ..., world_state: _Optional[_Union[GameWorldState, _Mapping]] = ..., pong: _Optional[_Union[_common_pb2.PongMessage, _Mapping]] = ..., initial_snapshot: _Optional[_Union[GameWorldSnapshot, _Mapping]] = ..., match_end: _Optional[_Union[MatchEndEvent, _Mapping]] = ..., alert: _Optional[_Union[EventNotification, _Mapping]] = ...) -> None: ...

class PlayerEntityState(_message.Message):
    __slots__ = ("player_id", "username", "role", "position", "velocity", "is_interacting", "current_score", "is_connected", "carrying_item")
    PLAYER_ID_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    VELOCITY_FIELD_NUMBER: _ClassVar[int]
    IS_INTERACTING_FIELD_NUMBER: _ClassVar[int]
    CURRENT_SCORE_FIELD_NUMBER: _ClassVar[int]
    IS_CONNECTED_FIELD_NUMBER: _ClassVar[int]
    CARRYING_ITEM_FIELD_NUMBER: _ClassVar[int]
    player_id: str
    username: str
    role: _common_pb2.PlayerRole
    position: _common_pb2.Vector2D
    velocity: _common_pb2.Vector2D
    is_interacting: bool
    current_score: int
    is_connected: bool
    carrying_item: str
    def __init__(self, player_id: _Optional[str] = ..., username: _Optional[str] = ..., role: _Optional[_Union[_common_pb2.PlayerRole, str]] = ..., position: _Optional[_Union[_common_pb2.Vector2D, _Mapping]] = ..., velocity: _Optional[_Union[_common_pb2.Vector2D, _Mapping]] = ..., is_interacting: _Optional[bool] = ..., current_score: _Optional[int] = ..., is_connected: _Optional[bool] = ..., carrying_item: _Optional[str] = ...) -> None: ...

class PipeEntityState(_message.Message):
    __slots__ = ("pipe_id", "position", "is_leaking", "leak_rate_liters_sec", "repair_progress_pct", "water_pressure_bar")
    PIPE_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    IS_LEAKING_FIELD_NUMBER: _ClassVar[int]
    LEAK_RATE_LITERS_SEC_FIELD_NUMBER: _ClassVar[int]
    REPAIR_PROGRESS_PCT_FIELD_NUMBER: _ClassVar[int]
    WATER_PRESSURE_BAR_FIELD_NUMBER: _ClassVar[int]
    pipe_id: int
    position: _common_pb2.Vector2D
    is_leaking: bool
    leak_rate_liters_sec: float
    repair_progress_pct: float
    water_pressure_bar: float
    def __init__(self, pipe_id: _Optional[int] = ..., position: _Optional[_Union[_common_pb2.Vector2D, _Mapping]] = ..., is_leaking: _Optional[bool] = ..., leak_rate_liters_sec: _Optional[float] = ..., repair_progress_pct: _Optional[float] = ..., water_pressure_bar: _Optional[float] = ...) -> None: ...

class ValveEntityState(_message.Message):
    __slots__ = ("valve_id", "position", "current_destination", "flow_rate_liters_sec")
    VALVE_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    CURRENT_DESTINATION_FIELD_NUMBER: _ClassVar[int]
    FLOW_RATE_LITERS_SEC_FIELD_NUMBER: _ClassVar[int]
    valve_id: int
    position: _common_pb2.Vector2D
    current_destination: WaterDestination
    flow_rate_liters_sec: float
    def __init__(self, valve_id: _Optional[int] = ..., position: _Optional[_Union[_common_pb2.Vector2D, _Mapping]] = ..., current_destination: _Optional[_Union[WaterDestination, str]] = ..., flow_rate_liters_sec: _Optional[float] = ...) -> None: ...

class TreatmentPlantEntityState(_message.Message):
    __slots__ = ("plant_id", "position", "filter_health_pct", "sludge_level_pct", "purification_rate_lps", "is_operating")
    PLANT_ID_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    FILTER_HEALTH_PCT_FIELD_NUMBER: _ClassVar[int]
    SLUDGE_LEVEL_PCT_FIELD_NUMBER: _ClassVar[int]
    PURIFICATION_RATE_LPS_FIELD_NUMBER: _ClassVar[int]
    IS_OPERATING_FIELD_NUMBER: _ClassVar[int]
    plant_id: int
    position: _common_pb2.Vector2D
    filter_health_pct: float
    sludge_level_pct: float
    purification_rate_lps: float
    is_operating: bool
    def __init__(self, plant_id: _Optional[int] = ..., position: _Optional[_Union[_common_pb2.Vector2D, _Mapping]] = ..., filter_health_pct: _Optional[float] = ..., sludge_level_pct: _Optional[float] = ..., purification_rate_lps: _Optional[float] = ..., is_operating: _Optional[bool] = ...) -> None: ...

class GameWorldState(_message.Message):
    __slots__ = ("tick", "water_metrics", "team_score", "remaining_seconds", "players", "pipes", "valves", "plants", "active_events")
    TICK_FIELD_NUMBER: _ClassVar[int]
    WATER_METRICS_FIELD_NUMBER: _ClassVar[int]
    TEAM_SCORE_FIELD_NUMBER: _ClassVar[int]
    REMAINING_SECONDS_FIELD_NUMBER: _ClassVar[int]
    PLAYERS_FIELD_NUMBER: _ClassVar[int]
    PIPES_FIELD_NUMBER: _ClassVar[int]
    VALVES_FIELD_NUMBER: _ClassVar[int]
    PLANTS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_EVENTS_FIELD_NUMBER: _ClassVar[int]
    tick: int
    water_metrics: _common_pb2.WaterMetrics
    team_score: int
    remaining_seconds: int
    players: _containers.RepeatedCompositeFieldContainer[PlayerEntityState]
    pipes: _containers.RepeatedCompositeFieldContainer[PipeEntityState]
    valves: _containers.RepeatedCompositeFieldContainer[ValveEntityState]
    plants: _containers.RepeatedCompositeFieldContainer[TreatmentPlantEntityState]
    active_events: _containers.RepeatedCompositeFieldContainer[ActiveEvent]
    def __init__(self, tick: _Optional[int] = ..., water_metrics: _Optional[_Union[_common_pb2.WaterMetrics, _Mapping]] = ..., team_score: _Optional[int] = ..., remaining_seconds: _Optional[int] = ..., players: _Optional[_Iterable[_Union[PlayerEntityState, _Mapping]]] = ..., pipes: _Optional[_Iterable[_Union[PipeEntityState, _Mapping]]] = ..., valves: _Optional[_Iterable[_Union[ValveEntityState, _Mapping]]] = ..., plants: _Optional[_Iterable[_Union[TreatmentPlantEntityState, _Mapping]]] = ..., active_events: _Optional[_Iterable[_Union[ActiveEvent, _Mapping]]] = ...) -> None: ...

class GameWorldSnapshot(_message.Message):
    __slots__ = ("baseline_tick", "room_id", "reconnect_ticket", "current_state", "match_duration_seconds")
    BASELINE_TICK_FIELD_NUMBER: _ClassVar[int]
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    RECONNECT_TICKET_FIELD_NUMBER: _ClassVar[int]
    CURRENT_STATE_FIELD_NUMBER: _ClassVar[int]
    MATCH_DURATION_SECONDS_FIELD_NUMBER: _ClassVar[int]
    baseline_tick: int
    room_id: str
    reconnect_ticket: str
    current_state: GameWorldState
    match_duration_seconds: int
    def __init__(self, baseline_tick: _Optional[int] = ..., room_id: _Optional[str] = ..., reconnect_ticket: _Optional[str] = ..., current_state: _Optional[_Union[GameWorldState, _Mapping]] = ..., match_duration_seconds: _Optional[int] = ...) -> None: ...

class ActiveEvent(_message.Message):
    __slots__ = ("event_id", "event_type", "title", "description", "remaining_seconds", "severity_multiplier")
    class EventType(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        EVENT_TYPE_UNSPECIFIED: _ClassVar[ActiveEvent.EventType]
        EVENT_TYPE_HEATWAVE: _ClassVar[ActiveEvent.EventType]
        EVENT_TYPE_MAJOR_BURST: _ClassVar[ActiveEvent.EventType]
        EVENT_TYPE_CONTAMINATION: _ClassVar[ActiveEvent.EventType]
        EVENT_TYPE_RAIN_HARVEST: _ClassVar[ActiveEvent.EventType]
    EVENT_TYPE_UNSPECIFIED: ActiveEvent.EventType
    EVENT_TYPE_HEATWAVE: ActiveEvent.EventType
    EVENT_TYPE_MAJOR_BURST: ActiveEvent.EventType
    EVENT_TYPE_CONTAMINATION: ActiveEvent.EventType
    EVENT_TYPE_RAIN_HARVEST: ActiveEvent.EventType
    EVENT_ID_FIELD_NUMBER: _ClassVar[int]
    EVENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    TITLE_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    REMAINING_SECONDS_FIELD_NUMBER: _ClassVar[int]
    SEVERITY_MULTIPLIER_FIELD_NUMBER: _ClassVar[int]
    event_id: int
    event_type: ActiveEvent.EventType
    title: str
    description: str
    remaining_seconds: int
    severity_multiplier: float
    def __init__(self, event_id: _Optional[int] = ..., event_type: _Optional[_Union[ActiveEvent.EventType, str]] = ..., title: _Optional[str] = ..., description: _Optional[str] = ..., remaining_seconds: _Optional[int] = ..., severity_multiplier: _Optional[float] = ...) -> None: ...

class EventNotification(_message.Message):
    __slots__ = ("event", "is_started")
    EVENT_FIELD_NUMBER: _ClassVar[int]
    IS_STARTED_FIELD_NUMBER: _ClassVar[int]
    event: ActiveEvent
    is_started: bool
    def __init__(self, event: _Optional[_Union[ActiveEvent, _Mapping]] = ..., is_started: _Optional[bool] = ...) -> None: ...

class MatchEndEvent(_message.Message):
    __slots__ = ("is_victory", "reason", "final_score", "final_metrics", "player_scores")
    IS_VICTORY_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    FINAL_SCORE_FIELD_NUMBER: _ClassVar[int]
    FINAL_METRICS_FIELD_NUMBER: _ClassVar[int]
    PLAYER_SCORES_FIELD_NUMBER: _ClassVar[int]
    is_victory: bool
    reason: str
    final_score: int
    final_metrics: _common_pb2.WaterMetrics
    player_scores: _containers.RepeatedCompositeFieldContainer[PlayerScoreBreakdown]
    def __init__(self, is_victory: _Optional[bool] = ..., reason: _Optional[str] = ..., final_score: _Optional[int] = ..., final_metrics: _Optional[_Union[_common_pb2.WaterMetrics, _Mapping]] = ..., player_scores: _Optional[_Iterable[_Union[PlayerScoreBreakdown, _Mapping]]] = ...) -> None: ...

class PlayerScoreBreakdown(_message.Message):
    __slots__ = ("player_id", "username", "role", "repairs_done", "water_saved_liters", "water_recycled_liters", "individual_points")
    PLAYER_ID_FIELD_NUMBER: _ClassVar[int]
    USERNAME_FIELD_NUMBER: _ClassVar[int]
    ROLE_FIELD_NUMBER: _ClassVar[int]
    REPAIRS_DONE_FIELD_NUMBER: _ClassVar[int]
    WATER_SAVED_LITERS_FIELD_NUMBER: _ClassVar[int]
    WATER_RECYCLED_LITERS_FIELD_NUMBER: _ClassVar[int]
    INDIVIDUAL_POINTS_FIELD_NUMBER: _ClassVar[int]
    player_id: str
    username: str
    role: _common_pb2.PlayerRole
    repairs_done: int
    water_saved_liters: float
    water_recycled_liters: float
    individual_points: int
    def __init__(self, player_id: _Optional[str] = ..., username: _Optional[str] = ..., role: _Optional[_Union[_common_pb2.PlayerRole, str]] = ..., repairs_done: _Optional[int] = ..., water_saved_liters: _Optional[float] = ..., water_recycled_liters: _Optional[float] = ..., individual_points: _Optional[int] = ...) -> None: ...

class ReconnectRequest(_message.Message):
    __slots__ = ("room_id", "player_id", "reconnect_ticket", "last_received_tick")
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    PLAYER_ID_FIELD_NUMBER: _ClassVar[int]
    RECONNECT_TICKET_FIELD_NUMBER: _ClassVar[int]
    LAST_RECEIVED_TICK_FIELD_NUMBER: _ClassVar[int]
    room_id: str
    player_id: str
    reconnect_ticket: str
    last_received_tick: int
    def __init__(self, room_id: _Optional[str] = ..., player_id: _Optional[str] = ..., reconnect_ticket: _Optional[str] = ..., last_received_tick: _Optional[int] = ...) -> None: ...

class ReconnectResponse(_message.Message):
    __slots__ = ("success", "message", "snapshot")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message: str
    snapshot: GameWorldSnapshot
    def __init__(self, success: _Optional[bool] = ..., message: _Optional[str] = ..., snapshot: _Optional[_Union[GameWorldSnapshot, _Mapping]] = ...) -> None: ...

class ChatMessage(_message.Message):
    __slots__ = ("message_id", "room_id", "sender_id", "sender_username", "sender_role", "content", "sent_at_unix_ms", "is_system_message")
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    SENDER_ID_FIELD_NUMBER: _ClassVar[int]
    SENDER_USERNAME_FIELD_NUMBER: _ClassVar[int]
    SENDER_ROLE_FIELD_NUMBER: _ClassVar[int]
    CONTENT_FIELD_NUMBER: _ClassVar[int]
    SENT_AT_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    IS_SYSTEM_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message_id: str
    room_id: str
    sender_id: str
    sender_username: str
    sender_role: _common_pb2.PlayerRole
    content: str
    sent_at_unix_ms: int
    is_system_message: bool
    def __init__(self, message_id: _Optional[str] = ..., room_id: _Optional[str] = ..., sender_id: _Optional[str] = ..., sender_username: _Optional[str] = ..., sender_role: _Optional[_Union[_common_pb2.PlayerRole, str]] = ..., content: _Optional[str] = ..., sent_at_unix_ms: _Optional[int] = ..., is_system_message: _Optional[bool] = ...) -> None: ...

class ChatAcknowledge(_message.Message):
    __slots__ = ("success", "message_id", "timestamp_unix_ms")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_ID_FIELD_NUMBER: _ClassVar[int]
    TIMESTAMP_UNIX_MS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    message_id: str
    timestamp_unix_ms: int
    def __init__(self, success: _Optional[bool] = ..., message_id: _Optional[str] = ..., timestamp_unix_ms: _Optional[int] = ...) -> None: ...

class StreamChatRequest(_message.Message):
    __slots__ = ("room_id", "player_id", "token")
    ROOM_ID_FIELD_NUMBER: _ClassVar[int]
    PLAYER_ID_FIELD_NUMBER: _ClassVar[int]
    TOKEN_FIELD_NUMBER: _ClassVar[int]
    room_id: str
    player_id: str
    token: str
    def __init__(self, room_id: _Optional[str] = ..., player_id: _Optional[str] = ..., token: _Optional[str] = ...) -> None: ...
