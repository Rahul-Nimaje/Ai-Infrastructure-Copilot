"""Socket.IO real-time layer — docs/02-HLD.md Section 10 event/room names.
Plan simplification #1: mounted directly on this ASGI app instead of a
separate notification-gateway service; same event names so extraction later
doesn't touch client code."""
import socketio

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
socket_asgi_app = socketio.ASGIApp(sio, socketio_path="socket.io")


async def emit_to_org(event: str, data: dict, *, organization_id) -> None:
    await sio.emit(event, data, room=f"org:{organization_id}")


@sio.event
async def join(sid, data):
    """Client calls socket.emit('join', {organization_id}) right after
    connecting, matching the org/user/task room model in docs/02-HLD.md
    Section 10."""
    organization_id = data.get("organization_id")
    if organization_id:
        await sio.enter_room(sid, f"org:{organization_id}")
