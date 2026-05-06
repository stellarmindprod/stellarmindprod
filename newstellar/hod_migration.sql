-- Migration to add HOD fields to teachers table
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS is_hod BOOLEAN DEFAULT FALSE;
ALTER TABLE teachers ADD COLUMN IF NOT EXISTS hod_department TEXT;
ALTER TABLE courses ADD COLUMN IF NOT EXISTS department TEXT;
