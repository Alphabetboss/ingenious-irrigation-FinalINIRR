from flask_socketio import SocketIO, emit

class AvatarController:
    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self.state = "idle"

    def trigger_animation(self, animation_name: str):
        self.state = animation_name
        self.socketio.emit("avatar_animation", {"animation": animation_name})
        print(f"[Avatar] Triggered: {animation_name}")

    def walk_to_zone(self, zone_id: str):
        self.trigger_animation(f"walk_to_{zone_id}")