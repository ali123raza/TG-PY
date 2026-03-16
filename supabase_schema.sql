-- ============================================================
-- TG-PY License System Schema
-- Run this in Supabase SQL Editor (supabase.com → SQL Editor)
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Users ─────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tgpy_users (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username     VARCHAR(50)  UNIQUE NOT NULL,
    password_hash TEXT         NOT NULL,
    email        VARCHAR(200) DEFAULT '',
    full_name    VARCHAR(200) DEFAULT '',
    is_active    BOOLEAN      DEFAULT TRUE,
    created_at   TIMESTAMPTZ  DEFAULT NOW(),
    notes        TEXT         DEFAULT ''
);

-- ── Plans (reference) ─────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tgpy_plans (
    id           SERIAL PRIMARY KEY,
    name         VARCHAR(50) UNIQUE NOT NULL,  -- 'basic', 'pro', 'lifetime'
    duration_days INT DEFAULT 30,              -- 0 = lifetime
    max_devices  INT DEFAULT 1,
    description  TEXT DEFAULT ''
);

INSERT INTO tgpy_plans (name, duration_days, max_devices, description) VALUES
    ('trial',    7,  1, '7 day trial'),
    ('basic',   30,  1, '1 month basic plan'),
    ('pro',     30,  3, '1 month pro — 3 devices'),
    ('lifetime', 0,  2, 'Lifetime access — 2 devices')
ON CONFLICT (name) DO NOTHING;

-- ── Licenses ──────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tgpy_licenses (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES tgpy_users(id) ON DELETE CASCADE,
    plan_name    VARCHAR(50)  NOT NULL DEFAULT 'basic',
    max_devices  INT          NOT NULL DEFAULT 1,
    starts_at    TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    expires_at   TIMESTAMPTZ,         -- NULL = lifetime
    is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at   TIMESTAMPTZ  DEFAULT NOW(),
    notes        TEXT         DEFAULT ''
);

-- ── Devices (hardware binding) ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tgpy_devices (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    license_id   UUID NOT NULL REFERENCES tgpy_licenses(id) ON DELETE CASCADE,
    hardware_id  VARCHAR(64)  NOT NULL,  -- SHA256 of CPU+Disk+MAC
    hostname     VARCHAR(200) DEFAULT '',
    platform     VARCHAR(100) DEFAULT '',
    activated_at TIMESTAMPTZ  DEFAULT NOW(),
    last_seen    TIMESTAMPTZ  DEFAULT NOW(),
    is_active    BOOLEAN      DEFAULT TRUE,
    UNIQUE(license_id, hardware_id)
);

-- ── Indexes ───────────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_licenses_user      ON tgpy_licenses(user_id);
CREATE INDEX IF NOT EXISTS idx_devices_license    ON tgpy_devices(license_id);
CREATE INDEX IF NOT EXISTS idx_devices_hardware   ON tgpy_devices(hardware_id);

-- ── Helpful view: active licenses with user info ─────────────────────────────
CREATE OR REPLACE VIEW tgpy_active_licenses AS
SELECT
    l.id             AS license_id,
    u.username,
    u.email,
    u.full_name,
    l.plan_name,
    l.max_devices,
    l.starts_at,
    l.expires_at,
    l.is_active,
    CASE
        WHEN l.expires_at IS NULL   THEN 'lifetime'
        WHEN l.expires_at > NOW()   THEN 'active'
        ELSE                             'expired'
    END              AS status,
    CASE
        WHEN l.expires_at IS NULL   THEN NULL
        WHEN l.expires_at > NOW()   THEN EXTRACT(DAY FROM l.expires_at - NOW())::INT
        ELSE                             0
    END              AS days_remaining,
    (SELECT COUNT(*) FROM tgpy_devices d
     WHERE d.license_id = l.id AND d.is_active = TRUE) AS active_devices
FROM tgpy_licenses l
JOIN tgpy_users u ON u.id = l.user_id;

-- ── RLS (disable for now — admin connects directly with service key) ──────────
ALTER TABLE tgpy_users    DISABLE ROW LEVEL SECURITY;
ALTER TABLE tgpy_licenses DISABLE ROW LEVEL SECURITY;
ALTER TABLE tgpy_devices  DISABLE ROW LEVEL SECURITY;
ALTER TABLE tgpy_plans    DISABLE ROW LEVEL SECURITY;

-- ── Test: insert admin user (change password after!) ─────────────────────────
-- password = 'admin123' (bcrypt hash)
INSERT INTO tgpy_users (username, password_hash, email, full_name, is_active)
VALUES (
    'admin',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TiGc.xD7lQk5J3Kp1I3LJ5XP6Mle',
    'admin@tgpy.com',
    'Admin',
    TRUE
) ON CONFLICT (username) DO NOTHING;
