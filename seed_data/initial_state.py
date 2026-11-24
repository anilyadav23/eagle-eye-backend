from typing import Dict, List
from models.schemas import (
    Person, AppearanceSnapshot, MovementEvent, Camera, 
    RoomZone, SecurityAlert, SecurityRule, PersonRole, 
    AccessStatus, AlertSeverity, AlertType, AlertStatus,
    AttendanceRecord, AttendanceStatus
)

INITIAL_PERSONS: Dict[str, Person] = {
    "HODECC": Person(
        id="hod1",
        person_id="HODECC",
        track_id="TRK-HOD-001",
        name="ECEHOD",
        mobile="",
        email="hodecc@campus.edu",
        department="Electronics & Communication Engineering",
        course="ECE - Core & AI Systems",
        semester="HOD Desk",
        id_proof_type="Faculty Card",
        id_proof_number="ECE-HOD-01",
        role=PersonRole.PROFESSOR,
        permission_type="Faculty Master Clearance",
        valid_from="2020-01-01 00:00",
        valid_to="2030-12-31 23:59",
        allowed_zones=["Lecture Hall 101", "AI Vision & Robotics Lab", "Computer Science Lab 2", "Faculty & Dean Lounge", "Central Corridor"],
        photo_url="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=300&h=300&fit=crop&crop=face",
        today_appearance_url="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=300&h=300&fit=crop&crop=face",
        status=AccessStatus.AUTHORIZED,
        attendance_status=AttendanceStatus.VERIFIED,
        attendance_time="09:00:00 AM",
        attendance_confidence=1.0,
        notes="HOD Department Head Account",
        current_building="Academic Block A",
        current_floor="Floor 2",
        current_room="Faculty & Dean Lounge",
        current_camera_id="CAM-015",
        last_seen_time="09:00:00 AM",
        x_pos=60.0,
        y_pos=75.0
    )
}

INITIAL_ATTENDANCE_RECORDS: List[AttendanceRecord] = []

INITIAL_APPEARANCES: Dict[str, List[AppearanceSnapshot]] = {
    "HODECC": [
        AppearanceSnapshot(
            id="app-hod-01",
            person_id="HODECC",
            date="2026-11-24",
            time="09:00 AM",
            photo_url="https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?w=300&h=300&fit=crop&crop=face",
            outfit_description="Dark formal blazer with white collared shirt",
            is_today=True
        )
    ]
}

INITIAL_TIMELINES: Dict[str, List[MovementEvent]] = {
    "HODECC": [
        MovementEvent(
            id="mov-hod-01",
            person_id="HODECC",
            track_id="TRK-HOD-001",
            timestamp="09:00:00 AM",
            camera_id="CAM-015",
            building="Academic Block A",
            floor="Floor 2",
            room="Faculty & Dean Lounge",
            event_type="ENTER",
            dwell_time_seconds=120
        )
    ]
}

INITIAL_ROOMS_FLOOR2: List[RoomZone] = [
    RoomZone(
        id="room-lecture-101",
        name="Lecture Hall 101",
        building="Academic Block A",
        floor="Floor 2",
        max_capacity=60,
        current_occupancy=0,
        is_restricted=False,
        allowed_roles=["Student", "Professor", "Faculty", "Staff", "Visitor"],
        occupants=[],
        x=57.0,
        y=5.0,
        width=38.0,
        height=62.0
    ),
    RoomZone(
        id="room-ai-lab",
        name="AI Vision & Robotics Lab",
        building="Academic Block A",
        floor="Floor 2",
        max_capacity=25,
        current_occupancy=0,
        is_restricted=True,
        allowed_roles=["Professor", "Faculty", "Staff", "Security"],
        occupants=[],
        x=5.0,
        y=5.0,
        width=38.0,
        height=45.0
    ),
    RoomZone(
        id="room-cs-lab2",
        name="Computer Science Lab 2",
        building="Academic Block A",
        floor="Floor 2",
        max_capacity=35,
        current_occupancy=0,
        is_restricted=False,
        allowed_roles=["Student", "Professor", "Faculty", "Staff"],
        occupants=[],
        x=5.0,
        y=54.0,
        width=38.0,
        height=42.0
    ),
    RoomZone(
        id="room-faculty-lounge",
        name="Faculty & Dean Lounge",
        building="Academic Block A",
        floor="Floor 2",
        max_capacity=15,
        current_occupancy=1,
        is_restricted=True,
        allowed_roles=["Professor", "Faculty", "Staff"],
        occupants=["HODECC"],
        x=57.0,
        y=70.0,
        width=20.0,
        height=25.0
    ),
    RoomZone(
        id="room-corridor",
        name="Central Corridor",
        building="Academic Block A",
        floor="Floor 2",
        max_capacity=80,
        current_occupancy=0,
        is_restricted=False,
        allowed_roles=["Student", "Professor", "Faculty", "Staff", "Visitor", "Security"],
        occupants=[],
        x=44.0,
        y=5.0,
        width=12.0,
        height=90.0
    ),
    RoomZone(
        id="room-lift",
        name="Elevator Lobby",
        building="Academic Block A",
        floor="Floor 2",
        max_capacity=25,
        current_occupancy=0,
        is_restricted=False,
        allowed_roles=["Student", "Professor", "Faculty", "Staff", "Visitor", "Security"],
        occupants=[],
        x=78.0,
        y=70.0,
        width=17.0,
        height=25.0
    )
]

INITIAL_CAMERAS: List[Camera] = []

INITIAL_ALERTS: List[SecurityAlert] = []

INITIAL_RULES: List[SecurityRule] = [
    SecurityRule(
        id="rule-1",
        name="Restricted Research Lab Geofence",
        type=AlertType.RESTRICTED_ZONE,
        description="Alarm when non-authorized student or visitor breaches AI Vision & Robotics Lab",
        is_enabled=True,
        threshold_seconds=0,
        severity=AlertSeverity.CRITICAL
    ),
    SecurityRule(
        id="rule-2",
        name="Classroom Tailgating & Proxy Attendance Check",
        type=AlertType.TAILGATING,
        description="Trigger warning when two persons cross classroom entry barrier within 1.5 seconds",
        is_enabled=True,
        threshold_seconds=0,
        severity=AlertSeverity.HIGH
    ),
    SecurityRule(
        id="rule-3",
        name="Corridor Loitering During Lecture Hours",
        type=AlertType.LOITERING,
        description="Detect stationary lingering in academic corridors exceeding 5 minutes",
        is_enabled=True,
        threshold_seconds=300,
        severity=AlertSeverity.MEDIUM
    ),
    SecurityRule(
        id="rule-4",
        name="Visitor Badge Expiration Enforcement",
        type=AlertType.EXPIRED_PERMISSION,
        description="Flag visitor presence on campus after authorized pass valid_to timestamp",
        is_enabled=True,
        threshold_seconds=0,
        severity=AlertSeverity.HIGH
    )
]
