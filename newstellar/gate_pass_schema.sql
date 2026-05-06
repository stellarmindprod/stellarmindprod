-- Table for Gate Pass Requests
CREATE TABLE IF NOT EXISTS gate_passes (
    id SERIAL PRIMARY KEY,
    roll_no TEXT NOT NULL,
    hostel_name TEXT NOT NULL,
    reason TEXT NOT NULL,
    out_date DATE NOT NULL,
    out_time TIME NOT NULL,
    in_date DATE,
    in_time TIME,
    status TEXT DEFAULT 'pending', -- pending, approved, rejected
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    approved_by TEXT, -- warden email
    approved_at TIMESTAMP WITH TIME ZONE
);
