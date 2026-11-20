-- ==============================================================================
-- Eagle Eye - Smart Class Attendance & Activity Intelligence
-- Complete PostgreSQL / Supabase Database Schema
-- ==============================================================================

-- 1. Buildings Table
CREATE TABLE IF NOT EXISTS buildings (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT NOT NULL,
    address TEXT,
    total_floors INTEGER DEFAULT 1,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Floors Table
CREATE TABLE IF NOT EXISTS floors (
    id TEXT PRIMARY KEY,
    building_id TEXT NOT NULL REFERENCES buildings(id) ON DELETE CASCADE,
    floor_number INTEGER NOT NULL,
    floor_name TEXT NOT NULL,
    blueprint_url TEXT,
    blueprint_type TEXT DEFAULT 'Custom Drawn',
    drawing_shapes_json TEXT DEFAULT '[]',
    camera_ids_json TEXT DEFAULT '[]'
);

-- 3. Room Zones Table
CREATE TABLE IF NOT EXISTS rooms (
    id TEXT PRIMARY KEY,
    building TEXT NOT NULL,
    floor TEXT NOT NULL,
    name TEXT NOT NULL,
    max_capacity INTEGER DEFAULT 10,
    current_occupancy INTEGER DEFAULT 0,
    is_restricted INTEGER DEFAULT 0,
    allowed_roles_json TEXT DEFAULT '[]',
    occupants_json TEXT DEFAULT '[]',
    x REAL NOT NULL,
    y REAL NOT NULL,
    width REAL NOT NULL,
    height REAL NOT NULL,
    shape_type TEXT DEFAULT 'RECT',
    points_json TEXT DEFAULT '[]',
    color TEXT
);

-- 4. Persons (Students, Faculty, Staff, Visitors)
CREATE TABLE IF NOT EXISTS persons (
    id TEXT PRIMARY KEY,
    person_id TEXT UNIQUE NOT NULL,
    track_id TEXT,
    name TEXT NOT NULL,
    mobile TEXT,
    email TEXT,
    student_id TEXT,
    department TEXT,
    course TEXT,
    semester TEXT,
    id_proof_type TEXT,
    id_proof_number TEXT,
    role TEXT DEFAULT 'Student',
    permission_type TEXT DEFAULT 'Academic Clearance',
    valid_from TEXT,
    valid_to TEXT,
    allowed_zones_json TEXT DEFAULT '[]',
    photo_url TEXT,
    today_appearance_url TEXT,
    status TEXT DEFAULT 'Authorized',
    attendance_status TEXT DEFAULT 'Present',
    attendance_time TEXT,
    attendance_confidence REAL DEFAULT 0.95,
    notes TEXT,
    current_building TEXT,
    current_floor TEXT,
    current_room TEXT,
    current_camera_id TEXT,
    last_seen_time TEXT,
    x_pos REAL DEFAULT 50.0,
    y_pos REAL DEFAULT 50.0,
    face_embedding_json TEXT DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 5. Attendance Records Table
CREATE TABLE IF NOT EXISTS attendance_records (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    student_id TEXT,
    name TEXT NOT NULL,
    role TEXT DEFAULT 'Student',
    department TEXT,
    course TEXT,
    room TEXT,
    status TEXT DEFAULT 'Present',
    timestamp TEXT NOT NULL,
    confidence_score REAL DEFAULT 0.95,
    photo_url TEXT,
    verified_camera_id TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_attendance_person ON attendance_records(person_id);
CREATE INDEX IF NOT EXISTS idx_attendance_course ON attendance_records(course);
CREATE INDEX IF NOT EXISTS idx_attendance_timestamp ON attendance_records(timestamp);

-- 6. Appearance Snapshots (Wardrobe & Verification Vault)
CREATE TABLE IF NOT EXISTS appearance_snapshots (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT NOT NULL,
    photo_url TEXT NOT NULL,
    outfit_description TEXT,
    is_today INTEGER DEFAULT 0
);

-- 7. Movement Events (Spatial Timeline)
CREATE TABLE IF NOT EXISTS movement_events (
    id TEXT PRIMARY KEY,
    person_id TEXT NOT NULL,
    track_id TEXT,
    timestamp TEXT NOT NULL,
    camera_id TEXT,
    building TEXT,
    floor TEXT,
    room TEXT,
    event_type TEXT DEFAULT 'ENTER',
    dwell_time_seconds INTEGER DEFAULT 0
);

-- 8. Cameras Table
CREATE TABLE IF NOT EXISTS cameras (
    id TEXT PRIMARY KEY,
    camera_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    building TEXT,
    floor TEXT,
    room TEXT,
    status TEXT DEFAULT 'Online',
    connection_status TEXT DEFAULT 'Connected',
    brand TEXT DEFAULT 'Generic RTSP',
    stream_type TEXT DEFAULT 'RTSP',
    stream_url TEXT,
    ip_address TEXT,
    port INTEGER DEFAULT 554,
    username TEXT,
    password TEXT,
    channel INTEGER DEFAULT 1,
    device_index INTEGER DEFAULT 0,
    is_real_camera INTEGER DEFAULT 0,
    last_connected_at TEXT,
    fps INTEGER DEFAULT 30,
    resolution TEXT DEFAULT '1080p Full HD',
    latency_ms INTEGER DEFAULT 18,
    ai_models_json TEXT DEFAULT '[]',
    fov_angle INTEGER DEFAULT 90,
    x_pos REAL DEFAULT 50.0,
    y_pos REAL DEFAULT 50.0
);

-- 9. Security Alerts & Threat Mitigations
CREATE TABLE IF NOT EXISTS security_alerts (
    id TEXT PRIMARY KEY,
    alert_id TEXT UNIQUE NOT NULL,
    timestamp TEXT NOT NULL,
    severity TEXT NOT NULL,
    type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    building TEXT,
    floor TEXT,
    room TEXT,
    camera_id TEXT,
    person_id TEXT,
    track_id TEXT,
    person_name TEXT,
    person_photo TEXT,
    status TEXT DEFAULT 'Active',
    guard_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. Security Rules Table
CREATE TABLE IF NOT EXISTS security_rules (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    description TEXT,
    is_enabled INTEGER DEFAULT 1,
    zone_id TEXT,
    threshold_seconds INTEGER DEFAULT 0,
    severity TEXT DEFAULT 'High'
);

-- 11. Users Table (Authentication & RBAC)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Guard',
    full_name TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 12. Audit Logs Table (Tamper-Proof Compliance)
CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    details_json TEXT,
    user_id TEXT,
    ip_address TEXT
);

-- ==============================================================================
-- Initial Seed: Default Administrator Account
-- Username: admin
-- Password: Password123!
-- ==============================================================================
INSERT INTO users (id, username, email, password_hash, role, full_name, is_active)
VALUES (
    'usr-admin-01',
    'admin',
    'admin@campus.edu',
    '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
    'SuperAdmin',
    'Chief Academic Security Officer',
    1
) ON CONFLICT (username) DO NOTHING;
