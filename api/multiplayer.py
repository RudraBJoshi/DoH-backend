"""
Real-time multiplayer rooms for UESL Game Maker.
Uses Flask-SocketIO for WebSocket connections.
"""
import uuid
from flask_socketio import emit, join_room, leave_room, rooms as get_rooms
from __init__ import socketio

# In-memory room store: room_id -> room dict
_rooms = {}

def _room_for_sid(sid):
    """Find which game room a socket SID is currently in."""
    for rid, room in _rooms.items():
        if sid in room['sids']:
            return rid, room
    return None, None


@socketio.on('connect')
def on_connect():
    pass  # no-op, just accept connection


@socketio.on('disconnect')
def on_disconnect():
    from flask import request
    sid = request.sid
    room_id, room = _room_for_sid(sid)
    if room_id:
        room['sids'].discard(sid)
        leave_room(room_id)
        emit('partner_left', {}, room=room_id)
        # Clean up empty rooms
        if not room['sids']:
            _rooms.pop(room_id, None)


@socketio.on('create_room')
def on_create_room(data):
    """
    Host creates a multiplayer room and gets back a room_id.
    data: { uid, name, game_data (JSON string), game_name }
    """
    from flask import request
    room_id = data.get('room_id') or str(uuid.uuid4())[:8].upper()
    _rooms[room_id] = {
        'host_uid':  data.get('uid', ''),
        'host_name': data.get('name', 'Player 1'),
        'game_data': data.get('game_data', '{}'),
        'game_name': data.get('game_name', 'Untitled Game'),
        'sids':      {request.sid},
        'players':   {}
    }
    join_room(room_id)
    emit('room_created', {'room_id': room_id})


@socketio.on('join_room_event')
def on_join_room(data):
    """
    Guest joins an existing room.
    data: { room_id, uid, name }
    """
    from flask import request
    room_id = data.get('room_id', '').upper()
    if room_id not in _rooms:
        emit('join_error', {'msg': 'Room not found or expired.'})
        return
    room = _rooms[room_id]
    if len(room['sids']) >= 2:
        emit('join_error', {'msg': 'Room is full (max 2 players).'})
        return
    room['sids'].add(request.sid)
    join_room(room_id)
    # Send host's game data to the guest
    emit('game_data', {
        'game_data': room['game_data'],
        'game_name': room['game_name'],
        'host_name': room['host_name'],
        'room_id':   room_id,
    })
    # Tell the host their partner arrived
    emit('partner_joined', {
        'uid':  data.get('uid', ''),
        'name': data.get('name', 'Player 2'),
    }, room=room_id, include_self=False)


@socketio.on('player_update')
def on_player_update(data):
    """
    Relay a player's position to their partner.
    data: { room_id, x, y, emoji, name }
    """
    room_id = data.get('room_id', '').upper()
    emit('partner_update', {
        'x':     data.get('x', 0),
        'y':     data.get('y', 0),
        'emoji': data.get('emoji', '🟦'),
        'name':  data.get('name', 'P2'),
    }, room=room_id, include_self=False)


@socketio.on('game_event')
def on_game_event(data):
    """
    Relay a co-op game event (star collected, level done) to the partner.
    data: { room_id, type, ...payload }
    """
    room_id = data.get('room_id', '').upper()
    emit('partner_game_event', data, room=room_id, include_self=False)
