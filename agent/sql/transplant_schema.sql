-- Transplant Candidacy Screening — Database Schema
--
-- Three tables for the organ transplant candidacy screening feature:
--   1. transplant_icd10_criteria  — Reference data from CMS ICD-10-CM FY2026
--   2. transplant_organ_criteria  — Reference data from OPTN/UNOS policy
--   3. transplant_screenings      — Per-patient screening records (CRUD)
--
-- Follows OpenEMR conventions:
--   - InnoDB engine
--   - snake_case naming
--   - bigint for patient ID references
--   - DATETIME with CURRENT_TIMESTAMP defaults
--   - Idempotent (IF NOT EXISTS)

-- ── Table 1: ICD-10-CM transplant-relevant diagnostic codes ─────────────────

CREATE TABLE IF NOT EXISTS `transplant_icd10_criteria` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `icd10_code` VARCHAR(10) NOT NULL,
  `short_description` VARCHAR(100),
  `long_description` TEXT,
  `is_billable` TINYINT(1) DEFAULT 1,
  `organ_system` ENUM('kidney', 'heart', 'lung', 'liver', 'general') NOT NULL,
  `criteria_type` ENUM(
    'qualifying_diagnosis',
    'transplant_status',
    'complication',
    'contraindication',
    'screening'
  ) NOT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `idx_icd10_code` (`icd10_code`),
  KEY `idx_organ_system` (`organ_system`),
  KEY `idx_criteria_type` (`criteria_type`)
) ENGINE=InnoDB;


-- ── Table 2: OPTN organ-specific eligibility criteria ───────────────────────

CREATE TABLE IF NOT EXISTS `transplant_organ_criteria` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `organ_type` ENUM('kidney', 'heart', 'lung', 'liver') NOT NULL,
  `criteria_json` JSON NOT NULL COMMENT 'Full criteria object from optn_transplant_criteria.json',
  `source` VARCHAR(255) DEFAULT 'OPTN Policy',
  `version` VARCHAR(20),
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY `idx_organ_type` (`organ_type`)
) ENGINE=InnoDB;


-- ── Table 3: Per-patient transplant screening records ───────────────────────

CREATE TABLE IF NOT EXISTS `transplant_screenings` (
  `id` INT AUTO_INCREMENT PRIMARY KEY,
  `pid` BIGINT NOT NULL COMMENT 'Patient ID from patient_data table',
  `organ_type` ENUM('kidney', 'heart', 'lung', 'liver') NOT NULL,
  `screening_status` ENUM('initiated', 'in_progress', 'complete', 'cancelled') DEFAULT 'initiated',
  `qualifying_diagnosis_code` VARCHAR(10) COMMENT 'ICD-10 code from transplant_icd10_criteria',
  `qualifying_diagnosis_met` TINYINT(1) DEFAULT NULL,
  `lab_criteria_met` TINYINT(1) DEFAULT NULL,
  `lab_criteria_notes` TEXT,
  `bmi_eligible` TINYINT(1) DEFAULT NULL,
  `bmi_value` DECIMAL(5,2) DEFAULT NULL,
  `substance_screening_status` ENUM(
    'not_started', 'scheduled', 'completed_pass', 'completed_fail', 'waived'
  ) DEFAULT 'not_started',
  `substance_screening_date` DATE DEFAULT NULL,
  `psychiatric_eval_status` ENUM(
    'not_started', 'scheduled', 'completed_pass', 'completed_fail', 'waived'
  ) DEFAULT 'not_started',
  `psychiatric_eval_date` DATE DEFAULT NULL,
  `cardiac_clearance_status` ENUM(
    'not_started', 'scheduled', 'completed_pass', 'completed_fail', 'not_applicable'
  ) DEFAULT 'not_started',
  `hla_typing_status` ENUM(
    'not_started', 'submitted', 'results_received'
  ) DEFAULT 'not_started',
  `blood_type` VARCHAR(5) DEFAULT NULL,
  `insurance_verified` TINYINT(1) DEFAULT NULL,
  `insurance_notes` TEXT,
  `contraindications_found` TINYINT(1) DEFAULT NULL,
  `contraindication_details` TEXT,
  `overall_eligibility` ENUM(
    'eligible', 'ineligible', 'pending_review', 'incomplete'
  ) DEFAULT 'incomplete',
  `priority_score` DECIMAL(8,2) DEFAULT NULL,
  `notes` TEXT,
  `referred_by` VARCHAR(255),
  `reviewed_by` VARCHAR(255),
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  KEY `idx_pid` (`pid`),
  KEY `idx_organ_type` (`organ_type`),
  KEY `idx_status` (`screening_status`),
  KEY `idx_eligibility` (`overall_eligibility`),
  CONSTRAINT `fk_screening_patient` FOREIGN KEY (`pid`)
    REFERENCES `patient_data` (`pid`) ON DELETE CASCADE
) ENGINE=InnoDB;
