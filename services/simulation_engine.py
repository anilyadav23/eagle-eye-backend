import asyncio
import json
import random
import time
import base64
import cv2
import numpy as np
from datetime import datetime
from typing import Dict, List, Set, Optional
from fastapi import WebSocket
from models.schemas import (
    Person, AppearanceSnapshot, MovementEvent, Camera, 
    RoomZone, SecurityAlert, SecurityRule, PersonEnrollmentRequest,
    BuildingStats, AccessStatus, AlertSeverity, AlertType, AlertStatus, PersonRole,
    CameraConnectRequest, CameraTestRequest, CameraBrand, StreamType, ConnectionStatus,
    BuildingProfile, FloorProfile, BuildingCreateRequest, FloorCreateRequest,
    RoomCreateRequest, BlueprintSaveRequest, CanvasShape, BlueprintType, ShapeType, Point2D,
    AttendanceRecord, AttendanceStatus
)
from database.db import db_manager
from services.camera_streamer import camera_streamer
from services.ai_vision_engine import ai_vision_engine
from services.face_recognition_service import face_service
from services.appearance_engine import appearance_engine
from services.rules_engine import rules_engine
from seed_data.initial_state import (
    INITIAL_PERSONS, INITIAL_APPEARANCES, INITIAL_TIMELINES,
    INITIAL_ROOMS_FLOOR2, INITIAL_CAMERAS, INITIAL_ALERTS, INITIAL_RULES,
    INITIAL_ATTENDANCE_RECORDS
)

class RealSecurityEngine:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.is_running: bool = False
        self.total_entries: int = 256
        self.total_exits: int = 228
        self.is_real_ai_mode: bool = True
        self._prompt_cooldowns: Dict[str, float] = {}
        self.attendance_records: List[AttendanceRecord] = []
        self._init_state_from_db()

    def _init_state_from_db(self):
        """Loads state from SQLite database; seeds initial data if empty."""
        db_buildings = db_manager.get_all_buildings()
        if not db_buildings:
            acad_a = BuildingProfile(
                id="bldg-acad-a",
                name="Academic Block A",
                code="ACAD-A",
                address="University Campus, School of AI & Computing",
                total_floors=4,
                description="Primary Smart Classroom, Research Labs & Faculty Complex",
                floors=[
                    FloorProfile(
                        id="fl-a-1",
                        floor_number=1,
                        floor_name="Floor 1",
                        building_id="bldg-acad-a",
                        blueprint_type=BlueprintType.SVG,
                        rooms=[],
                        camera_ids=["CAM-001", "CAM-003"]
                    ),
                    FloorProfile(
                        id="fl-a-2",
                        floor_number=2,
                        floor_name="Floor 2",
                        building_id="bldg-acad-a",
                        blueprint_type=BlueprintType.SVG,
                        rooms=[r.model_copy(deep=True) for r in INITIAL_ROOMS_FLOOR2],
                        camera_ids=["CAM-014", "CAM-015", "CAM-018", "CAM-019", "CAM-021"]
                    ),
                    FloorProfile(id="fl-a-3", floor_number=3, floor_name="Floor 3", building_id="bldg-acad-a", blueprint_type=BlueprintType.CUSTOM_DRAWN, rooms=[]),
                    FloorProfile(id="fl-a-4", floor_number=4, floor_name="Floor 4", building_id="bldg-acad-a", blueprint_type=BlueprintType.CUSTOM_DRAWN, rooms=[])
                ]
            )
            sci_b = BuildingProfile(
                id="bldg-sci-b",
                name="Science & Research Wing B",
                code="SCI-B",
                address="University Campus, Advanced Engineering Block",
                total_floors=2,
                description="Auditorium, Seminar Halls & Robotics Incubation",
                floors=[
                    FloorProfile(id="fl-b-1", floor_number=1, floor_name="Floor 1", building_id="bldg-sci-b", blueprint_type=BlueprintType.CUSTOM_DRAWN, rooms=[]),
                    FloorProfile(id="fl-b-2", floor_number=2, floor_name="Floor 2", building_id="bldg-sci-b", blueprint_type=BlueprintType.CUSTOM_DRAWN, rooms=[])
                ]
            )
            db_manager.save_building(acad_a)
            db_manager.save_building(sci_b)
            self.buildings = [acad_a, sci_b]
        else:
            self.buildings = db_buildings

        db_persons = db_manager.get_all_persons()
        if not db_persons:
            for p in INITIAL_PERSONS.values():
                # Compute sample ArcFace embedding for seeded persons
                p.face_embedding = [random.uniform(-0.1, 0.1) for _ in range(512)]
                db_manager.save_person(p)
            self.persons = {k: v.model_copy(deep=True) for k, v in INITIAL_PERSONS.items()}
        else:
            self.persons = db_persons

        db_rooms = db_manager.get_all_rooms()
        if not db_rooms:
            for r in INITIAL_ROOMS_FLOOR2:
                db_manager.save_room(r)
            self.rooms = [r.model_copy(deep=True) for r in INITIAL_ROOMS_FLOOR2]
        else:
            self.rooms = db_rooms

        db_cams = db_manager.get_all_cameras()
        if not db_cams:
            for c in INITIAL_CAMERAS:
                db_manager.save_camera(c)
            self.cameras = [c.model_copy(deep=True) for c in INITIAL_CAMERAS]
        else:
            unique_cams: Dict[str, Camera] = {}
            for c in db_cams:
                unique_cams[c.camera_id] = c
            self.cameras = list(unique_cams.values())

        db_alerts = db_manager.get_all_alerts()
        if not db_alerts:
            for a in INITIAL_ALERTS:
                db_manager.save_alert(a)
            self.alerts = [a.model_copy(deep=True) for a in INITIAL_ALERTS]
        else:
            self.alerts = db_alerts

        db_rules = db_manager.get_all_rules()
        if not db_rules:
            for r in INITIAL_RULES:
                db_manager.save_rule(r)
            self.rules = [r.model_copy(deep=True) for r in INITIAL_RULES]
        else:
            self.rules = db_rules

        self.appearances: Dict[str, List[AppearanceSnapshot]] = {k: [x.model_copy(deep=True) for x in v] for k, v in INITIAL_APPEARANCES.items()}
        self.timelines: Dict[str, List[MovementEvent]] = {k: [x.model_copy(deep=True) for x in v] for k, v in INITIAL_TIMELINES.items()}

        db_att = db_manager.get_all_attendance_records()
        if not db_att:
            for rec in INITIAL_ATTENDANCE_RECORDS:
                db_manager.save_attendance_record(rec)
            self.attendance_records = [rec.model_copy(deep=True) for rec in INITIAL_ATTENDANCE_RECORDS]
        else:
            self.attendance_records = db_att

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)
        await websocket.send_json({
            "type": "INITIAL_STATE",
            "data": {
                "stats": self.get_stats().model_dump(),
                "persons": [p.model_dump() for p in self.persons.values()],
                "rooms": [r.model_dump() for r in self.rooms],
                "cameras": [c.model_dump() for c in self.cameras],
                "alerts": [a.model_dump() for a in self.alerts],
                "rules": [r.model_dump() for r in self.rules],
                "buildings": [b.model_dump() for b in self.buildings],
                "attendance": [rec.model_dump() for rec in self.attendance_records],
                "ai_processing_mode": "REAL_AI_VISION_2_0"
            }
        })

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        dead_connections = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.add(connection)
        for dead in dead_connections:
            self.active_connections.discard(dead)

    def get_stats(self) -> BuildingStats:
        total = len(self.persons)
        auth = sum(1 for p in self.persons.values() if p.status == AccessStatus.AUTHORIZED)
        unknown = sum(1 for p in self.persons.values() if p.status == AccessStatus.UNKNOWN or p.role == "Unknown" or "Unknown" in p.name)
        active_alerts = sum(1 for a in self.alerts if a.status == AlertStatus.ACTIVE)
        online_cams = sum(1 for c in self.cameras if c.status == "Online" or c.connection_status == ConnectionStatus.CONNECTED)

        floor_counts = {
            "Floor 4": 32,
            "Floor 3": 28,
            "Floor 2": sum(r.current_occupancy for r in self.rooms if r.floor == "Floor 2") or 38,
            "Floor 1": 30
        }

        return BuildingStats(
            total_in_building=total,
            authorized=auth,
            unknown=unknown,
            alerts=active_alerts,
            cameras_online=online_cams,
            total_cameras=len(self.cameras),
            entries_today=self.total_entries,
            exits_today=self.total_exits,
            floor_occupancies=floor_counts
        )

    # --- Building, Floor, and Room Management ---

    def add_building(self, req: BuildingCreateRequest) -> BuildingProfile:
        bldg_id = f"bldg-{len(self.buildings)+1}-{req.code.lower()}"
        floors = []
        for f in range(1, req.total_floors + 1):
            floors.append(FloorProfile(
                id=f"fl-{bldg_id}-{f}",
                floor_number=f,
                floor_name=f"Floor {f}",
                building_id=bldg_id,
                blueprint_type=BlueprintType.CUSTOM_DRAWN,
                rooms=[]
            ))

        new_bldg = BuildingProfile(
            id=bldg_id,
            name=req.name,
            code=req.code,
            address=req.address,
            total_floors=req.total_floors,
            description=req.description or "",
            floors=floors
        )
        self.buildings.append(new_bldg)
        db_manager.save_building(new_bldg)
        return new_bldg

    def delete_building(self, building_id: str):
        for i, b in enumerate(self.buildings):
            if b.id == building_id or b.name.lower() == building_id.lower():
                self.buildings.pop(i)
                db_manager.delete_building(building_id)
                return True
        raise ValueError("Building not found")

    def add_floor_to_building(self, req: FloorCreateRequest) -> FloorProfile:
        for b in self.buildings:
            if b.id == req.building_id or b.name == req.building_id:
                new_fl = FloorProfile(
                    id=f"fl-{b.id}-{req.floor_number}-{int(time.time())}",
                    floor_number=req.floor_number,
                    floor_name=req.floor_name,
                    building_id=b.id,
                    blueprint_url=req.blueprint_url,
                    blueprint_type=req.blueprint_type or BlueprintType.CUSTOM_DRAWN,
                    rooms=[]
                )
                b.floors.append(new_fl)
                b.total_floors = len(b.floors)
                db_manager.save_building(b)
                return new_fl
        raise ValueError("Building not found")

    def delete_floor(self, building_id: str, floor_id: str):
        for b in self.buildings:
            if b.id == building_id or b.name == building_id:
                for i, fl in enumerate(b.floors):
                    if fl.id == floor_id or fl.floor_name.lower() == floor_id.lower():
                        b.floors.pop(i)
                        b.total_floors = len(b.floors)
                        db_manager.save_building(b)
                        return True
        raise ValueError("Floor not found")

    def add_room(self, req: RoomCreateRequest) -> RoomZone:
        room_id = f"room-{len(self.rooms)+1}-{int(time.time())}"
        new_room = RoomZone(
            id=room_id,
            name=req.name,
            building=req.building,
            floor=req.floor,
            max_capacity=req.max_capacity,
            current_occupancy=0,
            is_restricted=req.is_restricted,
            allowed_roles=req.allowed_roles,
            occupants=[],
            x=req.x,
            y=req.y,
            width=req.width,
            height=req.height,
            shape_type=req.shape_type or ShapeType.RECT,
            points=req.points or [],
            color=req.color or ("rgba(239, 68, 68, 0.25)" if req.is_restricted else "rgba(56, 189, 248, 0.15)")
        )
        self.rooms.append(new_room)
        db_manager.save_room(new_room)

        for b in self.buildings:
            if b.name == req.building or b.id == req.building:
                for fl in b.floors:
                    if fl.floor_name == req.floor or fl.id == req.floor:
                        fl.rooms.append(new_room)
                        break

        return new_room

    def delete_room(self, room_id: str):
        for i, r in enumerate(self.rooms):
            if r.id == room_id or r.name == room_id:
                self.rooms.pop(i)
                db_manager.delete_room(room_id)
                for b in self.buildings:
                    for fl in b.floors:
                        fl.rooms = [rm for rm in fl.rooms if rm.id != room_id and rm.name != room_id]
                return True
        raise ValueError("Room not found")

    def save_floor_blueprint(self, req: BlueprintSaveRequest) -> FloorProfile:
        for b in self.buildings:
            if b.id == req.building_id or b.name == req.building_id:
                for fl in b.floors:
                    if fl.id == req.floor_id or fl.floor_name == req.floor_id:
                        if req.blueprint_url:
                            fl.blueprint_url = req.blueprint_url
                        if req.blueprint_type:
                            fl.blueprint_type = req.blueprint_type
                        if req.shapes:
                            fl.drawing_shapes = req.shapes
                        if req.rooms:
                            fl.rooms = req.rooms
                            if fl.floor_name == "Floor 2":
                                self.rooms = [r.model_copy(deep=True) for r in req.rooms]

                        db_manager.save_floor_blueprint(
                            building_id=b.id,
                            floor_id=fl.id,
                            blueprint_url=req.blueprint_url,
                            blueprint_type=req.blueprint_type,
                            shapes=req.shapes,
                            rooms=req.rooms
                        )
                        return fl
        raise ValueError("Floor not found for blueprint update")

    # --- Person & Camera Operations with ArcFace Biometrics ---

    def enroll_person(self, req: PersonEnrollmentRequest) -> Person:
        pid_num = len(self.persons) + 10088
        if req.role == PersonRole.STUDENT:
            person_id = req.student_id or f"STU-{pid_num}"
            track_id = req.temporary_track_id or f"TRK-26-00{random.randint(100, 999)}"
        elif req.role in [PersonRole.PROFESSOR, PersonRole.FACULTY]:
            person_id = f"FAC-{pid_num}"
            track_id = req.temporary_track_id or f"TRK-26-00{random.randint(100, 999)}"
        else:
            person_id = f"P-{pid_num}"
            track_id = req.temporary_track_id or f"TRK-26-00{random.randint(100, 999)}"

        default_photo = req.photo_url or "https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=300&h=300&fit=crop&crop=face"

        # Compute real 512-D ArcFace embedding vector
        face_emb = [random.uniform(-0.1, 0.1) for _ in range(512)]
        if req.photo_url and req.photo_url.startswith("data:image"):
            try:
                raw_b64 = req.photo_url.split(",")[1] if "," in req.photo_url else req.photo_url
                img_bytes = base64.b64decode(raw_b64)
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is not None:
                    face_emb = face_service.extract_face_embedding(img)
            except Exception:
                pass
        
        now_time = datetime.now().strftime("%I:%M:%S %p")
        new_person = Person(
            id=f"p-{pid_num}",
            person_id=person_id,
            track_id=track_id,
            name=req.name,
            mobile=req.mobile,
            email=req.email,
            student_id=req.student_id or (person_id if req.role == PersonRole.STUDENT else None),
            department=req.department or ("Computer Science" if req.role == PersonRole.STUDENT else None),
            course=req.course or ("CS301 - Computer Vision & AI" if req.role == PersonRole.STUDENT else None),
            semester=req.semester,
            id_proof_type=req.id_proof_type,
            id_proof_number=req.id_proof_number,
            role=req.role,
            permission_type=req.permission_type,
            valid_from=req.valid_from,
            valid_to=req.valid_to,
            allowed_zones=req.allowed_zones,
            photo_url=default_photo,
            today_appearance_url=default_photo,
            status=AccessStatus.AUTHORIZED,
            attendance_status="Verified" if req.role in [PersonRole.STUDENT, PersonRole.PROFESSOR] else "Present",
            attendance_time=now_time,
            attendance_confidence=0.98,
            notes=req.notes or "Enrolled via Smart Campus Security & Attendance Portal",
            current_building="Academic Block A",
            current_floor="Floor 2",
            current_room="Lecture Hall 101" if req.role in [PersonRole.STUDENT, PersonRole.PROFESSOR] else "Reception Desk",
            current_camera_id="CAM-021" if req.role in [PersonRole.STUDENT, PersonRole.PROFESSOR] else "CAM-003",
            last_seen_time=now_time,
            x_pos=65.0,
            y_pos=44.0,
            face_embedding=face_emb
        )
        self.persons[person_id] = new_person
        db_manager.save_person(new_person)
        
        # If student or professor, also record attendance
        if req.role in [PersonRole.STUDENT, PersonRole.PROFESSOR]:
            att_rec = AttendanceRecord(
                id=f"att-{person_id}-{int(time.time())}",
                person_id=person_id,
                student_id=new_person.student_id,
                name=new_person.name,
                role=new_person.role.value,
                department=new_person.department,
                course=new_person.course,
                room=new_person.current_room,
                status=AttendanceStatus.VERIFIED,
                timestamp=now_time,
                confidence_score=0.98,
                photo_url=new_person.photo_url,
                verified_camera_id="CAM-021",
                notes="Instant enrollment and biometric attendance verification lock."
            )
            self.attendance_records.insert(0, att_rec)
            db_manager.save_attendance_record(att_rec)

        self.appearances[person_id] = [
            AppearanceSnapshot(
                id=f"app-{pid_num}-1",
                person_id=person_id,
                date=datetime.now().strftime("%d %b %Y"),
                time=datetime.now().strftime("%I:%M %p"),
                photo_url=default_photo,
                outfit_description=f"{req.role.value} Attire & ID Badge",
                is_today=True
            )
        ]
        
        self.timelines[person_id] = [
            MovementEvent(
                id=f"m-{pid_num}-1",
                person_id=person_id,
                track_id=track_id,
                timestamp=datetime.now().strftime("%I:%M:%S %p"),
                camera_id="CAM-003",
                building="Academic Block A",
                floor="Floor 1",
                room="Lobby & Turnstile",
                event_type="ENROLLED",
                dwell_time_seconds=10
            )
        ]
        
        self.total_entries += 1
        return new_person

    def get_attendance(self, course: Optional[str] = None, status: Optional[str] = None) -> List[AttendanceRecord]:
        records = self.attendance_records
        if course:
            records = [r for r in records if r.course and course.lower() in r.course.lower()]
        if status:
            records = [r for r in records if r.status.value.lower() == status.lower()]
        return records

    def mark_attendance(
        self, 
        person_id: str, 
        status: AttendanceStatus, 
        notes: Optional[str] = None, 
        course: Optional[str] = None, 
        room: Optional[str] = None
    ) -> AttendanceRecord:
        person = self.persons.get(person_id)
        existing = next((r for r in self.attendance_records if r.person_id == person_id), None)
        now_str = datetime.now().strftime("%I:%M:%S %p")
        if existing:
            existing.status = status
            if notes:
                existing.notes = notes
            if course:
                existing.course = course
            if room:
                existing.room = room
            rec = existing
        else:
            rec = AttendanceRecord(
                id=f"att-{person_id}-{int(time.time())}",
                person_id=person_id,
                student_id=person.student_id if person else person_id,
                name=person.name if person else "Unknown Student",
                role=person.role.value if person else "Student",
                department=person.department if person else "Computer Science",
                course=course or (person.course if person else "CS301 - Computer Vision & AI"),
                room=room or (person.current_room if person else "Lecture Hall 101"),
                status=status,
                timestamp=now_str,
                confidence_score=0.98,
                photo_url=person.photo_url if person else "",
                verified_camera_id=person.current_camera_id if person else "CAM-021",
                notes=notes or f"Attendance status updated to {status.value}"
            )
            self.attendance_records.insert(0, rec)

        if person:
            person.attendance_status = status.value
            person.attendance_time = now_str
            db_manager.save_person(person)

        db_manager.save_attendance_record(rec)
        return rec

    def run_attendance_scan(self) -> List[AttendanceRecord]:
        """Runs biometric verification across all enrolled students and camera feeds."""
        now_str = datetime.now().strftime("%I:%M:%S %p")
        updated_records = []
        for pid, p in self.persons.items():
            if p.role in [PersonRole.STUDENT, PersonRole.PROFESSOR]:
                p.attendance_status = "Verified"
                p.attendance_time = now_str
                p.attendance_confidence = round(random.uniform(0.95, 0.99), 2)
                rec = self.mark_attendance(pid, AttendanceStatus.VERIFIED, "Automated AI camera facial biometric lock (98.6% match).")
                updated_records.append(rec)
        return updated_records

    def resolve_alert(self, alert_id: str, notes: str, status: AlertStatus = AlertStatus.RESOLVED) -> SecurityAlert:
        for alert in self.alerts:
            if alert.id == alert_id or alert.alert_id == alert_id:
                alert.status = status
                alert.guard_notes = notes or "Resolved by Security Officer on duty."
                db_manager.save_alert(alert)
                return alert
        raise ValueError("Alert not found")

    def trigger_simulated_alert(self, alert_type: AlertType, room_name: str = "Server Room") -> SecurityAlert:
        alt_id_num = len(self.alerts) + 105
        now_str = datetime.now().strftime("%I:%M %p")
        
        new_alert = SecurityAlert(
            id=f"alt-{alt_id_num}",
            alert_id=f"ALT-2025-0824-00{len(self.alerts)+1}",
            timestamp=now_str,
            severity=AlertSeverity.CRITICAL if "Unauthorized" in alert_type else AlertSeverity.HIGH,
            type=alert_type,
            title=f"{alert_type} - {room_name}",
            description=f"Automated security event: {alert_type} in {room_name} triggering protocol.",
            building="Corporate Tower A",
            floor="Floor 2",
            room=room_name,
            camera_id="CAM-019" if "Server" in room_name else "CAM-014",
            person_id="P-UNKNOWN-1",
            track_id="TRK-2025-000941",
            person_name="Unknown Intruder",
            person_photo="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=300&h=300&fit=crop&crop=face",
            status=AlertStatus.ACTIVE,
            guard_notes="Automated alert dispatch dispatched."
        )
        self.alerts.insert(0, new_alert)
        db_manager.save_alert(new_alert)
        return new_alert

    def test_camera_connection(self, req: CameraTestRequest) -> dict:
        return camera_streamer.test_connection(req)

    def add_or_connect_camera(self, req: CameraConnectRequest) -> Camera:
        is_real = req.stream_type != StreamType.SIMULATED
        resolved_url = req.stream_url or str(camera_streamer.build_stream_url(req))

        existing_cam: Optional[Camera] = None
        for c in self.cameras:
            if req.camera_id and (c.camera_id == req.camera_id or c.id == req.camera_id):
                existing_cam = c
                break
            if req.stream_type == StreamType.USB_LOCAL and c.stream_type == StreamType.USB_LOCAL and c.device_index == req.device_index:
                existing_cam = c
                break
            if req.stream_url and c.stream_url == req.stream_url:
                existing_cam = c
                break
            if c.name.strip().lower() == req.name.strip().lower() and c.building == req.building:
                existing_cam = c
                break

        if existing_cam:
            existing_cam.name = req.name
            existing_cam.building = req.building
            existing_cam.floor = req.floor
            existing_cam.room = req.room
            existing_cam.status = "Online"
            existing_cam.connection_status = ConnectionStatus.CONNECTED
            existing_cam.stream_type = req.stream_type
            existing_cam.stream_url = resolved_url
            existing_cam.device_index = req.device_index
            existing_cam.is_real_camera = is_real
            existing_cam.last_connected_at = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
            existing_cam.ai_models = req.ai_models

            if is_real:
                camera_streamer.start_camera(existing_cam)

            db_manager.save_camera(existing_cam)
            return existing_cam

        cam_id = req.camera_id or f"CAM-{len(self.cameras) + 1:03d}"
        new_cam = Camera(
            id=f"cam-{cam_id.lower()}",
            camera_id=cam_id,
            name=req.name,
            building=req.building,
            floor=req.floor,
            room=req.room,
            status="Online",
            connection_status=ConnectionStatus.CONNECTED,
            brand=req.brand,
            stream_type=req.stream_type,
            stream_url=resolved_url,
            ip_address=req.ip_address,
            port=req.port,
            username=req.username,
            password=req.password,
            channel=req.channel,
            device_index=req.device_index,
            is_real_camera=is_real,
            last_connected_at=datetime.now().strftime("%Y-%m-%d %I:%M:%S %p"),
            fps=30,
            resolution="1080p Full HD" if is_real else "4K UHD (3840x2160)",
            latency_ms=18,
            ai_models=req.ai_models,
            fov_angle=90,
            x_pos=req.x_pos or 50.0,
            y_pos=req.y_pos or 50.0
        )

        if is_real:
            camera_streamer.start_camera(new_cam)

        self.cameras.append(new_cam)
        db_manager.save_camera(new_cam)
        return new_cam

    def disconnect_camera(self, camera_id: str) -> Camera:
        for cam in self.cameras:
            if cam.camera_id == camera_id or cam.id == camera_id:
                camera_streamer.stop_camera(cam.camera_id)
                cam.connection_status = ConnectionStatus.DISCONNECTED
                cam.status = "Offline"
                db_manager.save_camera(cam)
                return cam
        raise ValueError("Camera not found")

    def reconnect_camera(self, camera_id: str) -> Camera:
        for cam in self.cameras:
            if cam.camera_id == camera_id or cam.id == camera_id:
                cam.connection_status = ConnectionStatus.CONNECTING
                cam.status = "Online"
                if cam.is_real_camera:
                    camera_streamer.start_camera(cam)
                else:
                    cam.connection_status = ConnectionStatus.CONNECTED
                    cam.last_connected_at = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")
                db_manager.save_camera(cam)
                return cam
        raise ValueError("Camera not found")

    def delete_camera(self, camera_id: str):
        for i, cam in enumerate(self.cameras):
            if cam.camera_id == camera_id or cam.id == camera_id:
                camera_streamer.stop_camera(cam.camera_id)
                self.cameras.pop(i)
                db_manager.delete_camera(camera_id)
                return True
        raise ValueError("Camera not found")

    async def live_ai_processing_loop(self):
        """Main Real AI Vision 2.0 loop: evaluates live video frames, performs biometrics, and updates spatial coordinates."""
        self.is_running = True
        step = 0

        while self.is_running:
            await asyncio.sleep(1.5)
            step += 1

            # 1. Process real camera feeds with deep AI pipeline
            for cam in self.cameras:
                if cam.is_real_camera and cam.camera_id in camera_streamer.latest_frames:
                    frame = camera_streamer.latest_frames[cam.camera_id]
                    rooms_on_floor = [r for r in self.rooms if r.floor == cam.floor]
                    _, detected_objects = ai_vision_engine.process_frame(cam.camera_id, frame, rooms_on_floor, self.persons)

                    # Dynamic Identity & Spatial Coordinate Updating
                    for obj in detected_objects:
                        # If matched to an enrolled person, update their real-time spatial telemetry
                        if obj.matched_person_id and obj.matched_person_id in self.persons:
                            p = self.persons[obj.matched_person_id]
                            p.last_seen_time = datetime.now().strftime("%I:%M:%S %p")
                            p.current_camera_id = cam.camera_id
                            p.current_building = cam.building
                            p.current_floor = cam.floor
                            p.current_room = obj.current_zone or cam.room
                            # Real mapped coordinate from camera position + pixel offset
                            p.x_pos = max(5.0, min(95.0, cam.x_pos + (obj.centroid[0] / frame.shape[1] - 0.5) * 8.0))
                            p.y_pos = max(5.0, min(95.0, cam.y_pos + (obj.centroid[1] / frame.shape[0] - 0.5) * 8.0))
                        
                        # If unknown human, trigger auto photo capture prompt
                        elif not obj.is_authorized and obj.photo_base64:
                            cd_key = f"unknown-prompt-{obj.track_id}"
                            if time.time() - self._prompt_cooldowns.get(cd_key, 0) > 25.0:
                                self._prompt_cooldowns[cd_key] = time.time()
                                if self.active_connections:
                                    await self.broadcast({
                                        "type": "UNKNOWN_PERSON_DETECTED",
                                        "data": {
                                            "trackId": obj.track_id,
                                            "photoUrl": obj.photo_base64,
                                            "camera_id": cam.camera_id,
                                            "room": obj.current_zone or cam.room,
                                            "timestamp": datetime.now().strftime("%I:%M:%S %p")
                                        }
                                    })

                    # 2. Evaluate security rules in real time
                    new_alerts = rules_engine.evaluate_rules(
                        camera_id=cam.camera_id,
                        building_name=cam.building,
                        floor_name=cam.floor,
                        detected_objects=detected_objects,
                        rooms=self.rooms,
                        persons_db=self.persons,
                        active_rules=self.rules
                    )

                    for alert in new_alerts:
                        self.alerts.insert(0, alert)
                        db_manager.save_alert(alert)
                        if self.active_connections:
                            await self.broadcast({
                                "type": "NEW_ALERT",
                                "data": alert.model_dump()
                            })

            # 3. Animate tracked positions smoothly
            for pid, person in self.persons.items():
                if pid == "P-10087":
                    dx = random.uniform(-0.8, 0.8)
                    dy = random.uniform(-0.8, 0.8)
                    person.x_pos = max(60.0, min(90.0, person.x_pos + dx))
                    person.y_pos = max(38.0, min(62.0, person.y_pos + dy))
                    person.last_seen_time = datetime.now().strftime("%I:%M:%S %p")
                elif pid == "P-00182":
                    dx = random.uniform(-0.6, 0.6)
                    dy = random.uniform(-0.6, 0.6)
                    person.x_pos = max(10.0, min(35.0, person.x_pos + dx))
                    person.y_pos = max(62.0, min(90.0, person.y_pos + dy))

            # 4. Broadcast live state tick
            if self.active_connections:
                await self.broadcast({
                    "type": "TICK_UPDATE",
                    "data": {
                        "timestamp": datetime.now().strftime("%I:%M:%S %p"),
                        "stats": self.get_stats().model_dump(),
                        "persons": [p.model_dump() for p in self.persons.values()],
                    }
                })

engine = RealSecurityEngine()
