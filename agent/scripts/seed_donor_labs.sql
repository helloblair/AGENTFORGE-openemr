-- Donor patient lab results
-- Run against your OpenEMR database to populate lab values for donor viability tool.
--
-- These inserts create procedure_order → procedure_report → procedure_result
-- records that the FHIR Observation endpoint can read.

-- Lab results for Priya Sharma (pid=19) — Living kidney donor, HEALTHY
SET @po_pid = 19;
SET @po_eid = 0;

INSERT INTO procedure_order (uuid, provider_id, patient_id, encounter_id, date_ordered, order_priority, order_status, procedure_order_type, activity) VALUES (UNHEX(REPLACE(UUID(), '-', '')), 0, @po_pid, @po_eid, '2026-03-20 08:00:00', 'normal', 'complete', 'laboratory_test', 1);
SET @order_id = LAST_INSERT_ID();

INSERT INTO procedure_order_code (procedure_order_id, procedure_order_seq, procedure_code, procedure_name, procedure_source) VALUES (@order_id, 1, 'DONOR_PANEL', 'Living Donor Evaluation Panel', '1');

INSERT INTO procedure_report (uuid, procedure_order_id, procedure_order_seq, date_collected, date_report, report_status, review_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @order_id, 1, '2026-03-20 08:00:00', '2026-03-20 08:00:00', 'final', 'reviewed');
SET @report_id = LAST_INSERT_ID();

INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '33914-3', 'eGFR', '2026-03-20 08:00:00', 'mL/min', '105', '>60', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '2160-0', 'Creatinine', '2026-03-20 08:00:00', 'mg/dL', '0.8', '0.6-1.2', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '718-7', 'Hemoglobin', '2026-03-20 08:00:00', 'g/dL', '13.8', '12.0-16.0', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '1751-7', 'Albumin', '2026-03-20 08:00:00', 'g/dL', '4.2', '3.4-5.4', '', 'final');


-- Lab results for Tomás Herrera (pid=20) — Living liver donor, HEALTHY
SET @po_pid = 20;
SET @po_eid = 0;

INSERT INTO procedure_order (uuid, provider_id, patient_id, encounter_id, date_ordered, order_priority, order_status, procedure_order_type, activity) VALUES (UNHEX(REPLACE(UUID(), '-', '')), 0, @po_pid, @po_eid, '2026-03-20 08:00:00', 'normal', 'complete', 'laboratory_test', 1);
SET @order_id = LAST_INSERT_ID();

INSERT INTO procedure_order_code (procedure_order_id, procedure_order_seq, procedure_code, procedure_name, procedure_source) VALUES (@order_id, 1, 'DONOR_PANEL', 'Living Donor Hepatic Panel', '1');

INSERT INTO procedure_report (uuid, procedure_order_id, procedure_order_seq, date_collected, date_report, report_status, review_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @order_id, 1, '2026-03-20 08:00:00', '2026-03-20 08:00:00', 'final', 'reviewed');
SET @report_id = LAST_INSERT_ID();

INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '1975-2', 'Bilirubin Total', '2026-03-20 08:00:00', 'mg/dL', '0.7', '0.1-1.2', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '6301-6', 'INR', '2026-03-20 08:00:00', '', '0.9', '0.8-1.2', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '1751-7', 'Albumin', '2026-03-20 08:00:00', 'g/dL', '4.5', '3.4-5.4', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '2160-0', 'Creatinine', '2026-03-20 08:00:00', 'mg/dL', '0.9', '0.6-1.2', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '718-7', 'Hemoglobin', '2026-03-20 08:00:00', 'g/dL', '15.2', '13.5-17.5', '', 'final');


-- Lab results for Gerald Franklin (pid=21) — Deceased donor, CVA, good organs
SET @po_pid = 21;
SET @po_eid = 0;

INSERT INTO procedure_order (uuid, provider_id, patient_id, encounter_id, date_ordered, order_priority, order_status, procedure_order_type, activity) VALUES (UNHEX(REPLACE(UUID(), '-', '')), 0, @po_pid, @po_eid, '2026-03-20 08:00:00', 'normal', 'complete', 'laboratory_test', 1);
SET @order_id = LAST_INSERT_ID();

INSERT INTO procedure_order_code (procedure_order_id, procedure_order_seq, procedure_code, procedure_name, procedure_source) VALUES (@order_id, 1, 'DONOR_PANEL', 'Deceased Donor Organ Assessment Panel', '1');

INSERT INTO procedure_report (uuid, procedure_order_id, procedure_order_seq, date_collected, date_report, report_status, review_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @order_id, 1, '2026-03-20 08:00:00', '2026-03-20 08:00:00', 'final', 'reviewed');
SET @report_id = LAST_INSERT_ID();

-- Kidney labs (good)
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '2160-0', 'Creatinine', '2026-03-20 08:00:00', 'mg/dL', '1.1', '0.6-1.2', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '33914-3', 'eGFR', '2026-03-20 08:00:00', 'mL/min', '78', '>60', '', 'final');
-- Liver labs (good)
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '1975-2', 'Bilirubin Total', '2026-03-20 08:00:00', 'mg/dL', '0.9', '0.1-1.2', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '6301-6', 'INR', '2026-03-20 08:00:00', '', '1.0', '0.8-1.2', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '1751-7', 'Albumin', '2026-03-20 08:00:00', 'g/dL', '3.9', '3.4-5.4', '', 'final');
-- Heart labs (good)
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '10230-1', 'Ejection Fraction', '2026-03-20 08:00:00', '%', '58', '55-70', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '30934-4', 'BNP', '2026-03-20 08:00:00', 'pg/mL', '45', '<100', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '718-7', 'Hemoglobin', '2026-03-20 08:00:00', 'g/dL', '14.1', '13.5-17.5', '', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '2951-2', 'Sodium', '2026-03-20 08:00:00', 'mEq/L', '140', '136-145', '', 'final');


-- Lab results for Evelyn Matsuda (pid=22) — Deceased donor, cardiac arrest, marginal organs
SET @po_pid = 22;
SET @po_eid = 0;

INSERT INTO procedure_order (uuid, provider_id, patient_id, encounter_id, date_ordered, order_priority, order_status, procedure_order_type, activity) VALUES (UNHEX(REPLACE(UUID(), '-', '')), 0, @po_pid, @po_eid, '2026-03-20 08:00:00', 'normal', 'complete', 'laboratory_test', 1);
SET @order_id = LAST_INSERT_ID();

INSERT INTO procedure_order_code (procedure_order_id, procedure_order_seq, procedure_code, procedure_name, procedure_source) VALUES (@order_id, 1, 'DONOR_PANEL', 'Deceased Donor Organ Assessment Panel', '1');

INSERT INTO procedure_report (uuid, procedure_order_id, procedure_order_seq, date_collected, date_report, report_status, review_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @order_id, 1, '2026-03-20 08:00:00', '2026-03-20 08:00:00', 'final', 'reviewed');
SET @report_id = LAST_INSERT_ID();

-- Kidney labs (marginal — elevated creatinine, diabetes history)
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '2160-0', 'Creatinine', '2026-03-20 08:00:00', 'mg/dL', '1.8', '0.6-1.2', 'high', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '33914-3', 'eGFR', '2026-03-20 08:00:00', 'mL/min', '42', '>60', 'low', 'final');
-- Liver labs (marginal)
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '1975-2', 'Bilirubin Total', '2026-03-20 08:00:00', 'mg/dL', '1.6', '0.1-1.2', 'high', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '6301-6', 'INR', '2026-03-20 08:00:00', '', '1.3', '0.8-1.2', 'high', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '1751-7', 'Albumin', '2026-03-20 08:00:00', 'g/dL', '3.1', '3.4-5.4', 'low', 'final');
-- Heart labs (marginal — reduced EF from arrest)
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '10230-1', 'Ejection Fraction', '2026-03-20 08:00:00', '%', '35', '55-70', 'low', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '30934-4', 'BNP', '2026-03-20 08:00:00', 'pg/mL', '620', '<100', 'high', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '718-7', 'Hemoglobin', '2026-03-20 08:00:00', 'g/dL', '11.2', '12.0-16.0', 'low', 'final');
INSERT INTO procedure_result (uuid, procedure_report_id, result_data_type, result_code, result_text, date, units, result, `range`, abnormal, result_status) VALUES (UNHEX(REPLACE(UUID(), '-', '')), @report_id, 'N', '2951-2', 'Sodium', '2026-03-20 08:00:00', 'mEq/L', '148', '136-145', 'high', 'final');
