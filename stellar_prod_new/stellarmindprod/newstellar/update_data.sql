-- 1. OVERWRITE ALL PASSWORDS ACROSS ALL TABLES
UPDATE b1 
SET student_password = 'pbkdf2:sha256:1000000$HyiUAoDQFbCk0tQo$ea95c84029fa572e84c5e2fc007d26165ea880c905c693c1570c212b2cac5b57', 
    parent_password = 'pbkdf2:sha256:1000000$HyiUAoDQFbCk0tQo$ea95c84029fa572e84c5e2fc007d26165ea880c905c693c1570c212b2cac5b57';

UPDATE b2 
SET student_password = 'pbkdf2:sha256:1000000$HyiUAoDQFbCk0tQo$ea95c84029fa572e84c5e2fc007d26165ea880c905c693c1570c212b2cac5b57', 
    parent_password = 'pbkdf2:sha256:1000000$HyiUAoDQFbCk0tQo$ea95c84029fa572e84c5e2fc007d26165ea880c905c693c1570c212b2cac5b57';

UPDATE b3 
SET student_password = 'pbkdf2:sha256:1000000$HyiUAoDQFbCk0tQo$ea95c84029fa572e84c5e2fc007d26165ea880c905c693c1570c212b2cac5b57', 
    parent_password = 'pbkdf2:sha256:1000000$HyiUAoDQFbCk0tQo$ea95c84029fa572e84c5e2fc007d26165ea880c905c693c1570c212b2cac5b57';

UPDATE b4 
SET student_password = 'pbkdf2:sha256:1000000$HyiUAoDQFbCk0tQo$ea95c84029fa572e84c5e2fc007d26165ea880c905c693c1570c212b2cac5b57', 
    parent_password = 'pbkdf2:sha256:1000000$HyiUAoDQFbCk0tQo$ea95c84029fa572e84c5e2fc007d26165ea880c905c693c1570c212b2cac5b57';

UPDATE teachers 
SET teacher_password = 'pbkdf2:sha256:1000000$HyiUAoDQFbCk0tQo$ea95c84029fa572e84c5e2fc007d26165ea880c905c693c1570c212b2cac5b57';

UPDATE admin 
SET password = 'pbkdf2:sha256:1000000$HyiUAoDQFbCk0tQo$ea95c84029fa572e84c5e2fc007d26165ea880c905c693c1570c212b2cac5b57';


-- 2. WIPE EXISTING DUMMY MARKS/ATTENDANCE TO PREVENT ERRORS
DELETE FROM attendance1 WHERE subject_code IN ('CS13111', 'CS13112');
DELETE FROM marks1 WHERE subject_code IN ('CS13111', 'CS13112');

-- 3. INSERT DUMMY ATTENDANCE FOR ALL STUDENTS IN B1
-- Day 1 Attendance: Present
INSERT INTO attendance1 (roll_no, subject_code, subject_name, date, status, total_classes)
SELECT roll_no, 'CS13111', 'Data Structure and Algorithm', '2025-09-01', 1, 1 FROM b1;

-- Day 2 Attendance: Absent
INSERT INTO attendance1 (roll_no, subject_code, subject_name, date, status, total_classes)
SELECT roll_no, 'CS13111', 'Data Structure and Algorithm', '2025-09-02', 0, 1 FROM b1;

-- Day 1 Attendance for another subject
INSERT INTO attendance1 (roll_no, subject_code, subject_name, date, status, total_classes)
SELECT roll_no, 'CS13112', 'COMPUTER NETWORKS', '2025-09-01', 1, 1 FROM b1;

-- Day 2 Attendance for another subject
INSERT INTO attendance1 (roll_no, subject_code, subject_name, date, status, total_classes)
SELECT roll_no, 'CS13112', 'COMPUTER NETWORKS', '2025-09-02', 1, 1 FROM b1;


-- 4. INSERT DUMMY MARKS FOR ALL STUDENTS IN B1
INSERT INTO marks1 (roll_no, subject_code, credits, mid1, mid2, endsem, internal_marks, final_grade)
SELECT roll_no, 'CS13111', 4, 14, 13, 40, 18, 'A+' FROM b1;

INSERT INTO marks1 (roll_no, subject_code, credits, mid1, mid2, endsem, internal_marks, final_grade)
SELECT roll_no, 'CS13112', 3, 10, 12, 35, 15, 'B+' FROM b1;
