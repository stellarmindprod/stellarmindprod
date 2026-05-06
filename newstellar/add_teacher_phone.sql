-- Add teacher_phone column to teachers table
ALTER TABLE "teachers" ADD COLUMN IF NOT EXISTS "teacher_phone" TEXT;
