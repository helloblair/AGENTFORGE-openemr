<?php

/**
 * Transplant Screening Service
 *
 * Provides CRUD operations for the transplant_screenings table,
 * which tracks per-patient organ transplant candidacy screening records.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Veris Agent <veris@openemr.org>
 * @copyright Copyright (c) 2026 Veris Agent
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

namespace OpenEMR\Services;

use OpenEMR\Common\Database\QueryUtils;
use OpenEMR\Common\Uuid\UuidRegistry;
use OpenEMR\Validators\ProcessingResult;

class TransplantScreeningService extends BaseService
{
    public const TABLE_NAME = "transplant_screenings";

    /**
     * Fields allowed for insert/update operations.
     */
    private const WHITELISTED_FIELDS = [
        'organ_type',
        'screening_status',
        'qualifying_diagnosis_code',
        'qualifying_diagnosis_met',
        'lab_criteria_met',
        'lab_criteria_notes',
        'bmi_eligible',
        'bmi_value',
        'substance_screening_status',
        'substance_screening_date',
        'psychiatric_eval_status',
        'psychiatric_eval_date',
        'cardiac_clearance_status',
        'hla_typing_status',
        'blood_type',
        'insurance_verified',
        'insurance_notes',
        'contraindications_found',
        'contraindication_details',
        'overall_eligibility',
        'priority_score',
        'notes',
        'referred_by',
        'reviewed_by',
    ];

    public function __construct()
    {
        parent::__construct(self::TABLE_NAME);
    }

    /**
     * Create a new transplant screening record for a patient.
     *
     * @param int $pid Patient ID from patient_data table.
     * @param array $data Screening data fields.
     * @return ProcessingResult
     */
    public function insert(int $pid, array $data): ProcessingResult
    {
        $processingResult = new ProcessingResult();

        // Validate required field
        if (empty($data['organ_type'])) {
            $processingResult->setValidationMessages([
                'organ_type' => ['organ_type is required']
            ]);
            return $processingResult;
        }

        $validOrgans = ['kidney', 'heart', 'lung', 'liver'];
        if (!in_array($data['organ_type'], $validOrgans, true)) {
            $processingResult->setValidationMessages([
                'organ_type' => ['organ_type must be one of: ' . implode(', ', $validOrgans)]
            ]);
            return $processingResult;
        }

        // Verify patient exists
        $patientCheck = QueryUtils::fetchRecords(
            "SELECT pid FROM patient_data WHERE pid = ?",
            [$pid]
        );
        if (empty($patientCheck)) {
            $processingResult->setValidationMessages([
                'pid' => ['Patient not found with pid: ' . $pid]
            ]);
            return $processingResult;
        }

        // Filter data to whitelisted fields
        $filteredData = array_intersect_key($data, array_flip(self::WHITELISTED_FIELDS));
        $filteredData['pid'] = $pid;

        $query = $this->buildInsertColumns($filteredData);
        $sql = "INSERT INTO " . self::TABLE_NAME . " SET " . $query['set'];

        $insertId = sqlInsert($sql, $query['bind']);

        if ($insertId) {
            $processingResult->addData([
                'id' => $insertId,
                'pid' => $pid,
                'organ_type' => $data['organ_type'],
            ]);
        } else {
            $processingResult->addInternalError("Error creating transplant screening record");
        }

        return $processingResult;
    }

    /**
     * Get all transplant screenings for a patient.
     *
     * @param int $pid Patient ID.
     * @return ProcessingResult
     */
    public function getByPatient(int $pid): ProcessingResult
    {
        $processingResult = new ProcessingResult();

        $sql = "SELECT * FROM " . self::TABLE_NAME
             . " WHERE pid = ? ORDER BY created_at DESC";

        $records = QueryUtils::fetchRecords($sql, [$pid]);
        foreach ($records as $record) {
            $processingResult->addData($record);
        }

        return $processingResult;
    }

    /**
     * Get a single transplant screening by ID.
     *
     * @param int $id Screening record ID.
     * @param int|null $pid Optional patient ID for validation.
     * @return ProcessingResult
     */
    public function getOne(int $id, ?int $pid = null): ProcessingResult
    {
        $processingResult = new ProcessingResult();

        $sql = "SELECT * FROM " . self::TABLE_NAME . " WHERE id = ?";
        $binds = [$id];

        if ($pid !== null) {
            $sql .= " AND pid = ?";
            $binds[] = $pid;
        }

        $records = QueryUtils::fetchRecords($sql, $binds);
        foreach ($records as $record) {
            $processingResult->addData($record);
        }

        return $processingResult;
    }

    /**
     * Update a transplant screening record.
     *
     * @param int $id Screening record ID.
     * @param array $data Updated fields.
     * @param int|null $pid Optional patient ID for validation.
     * @return ProcessingResult
     */
    public function update(int $id, array $data, ?int $pid = null): ProcessingResult
    {
        $processingResult = new ProcessingResult();

        if (empty($data)) {
            $processingResult->setValidationMessages([
                'data' => ['No update data provided']
            ]);
            return $processingResult;
        }

        // Verify record exists
        $existing = $this->getOne($id, $pid);
        if (!$existing->hasData()) {
            $processingResult->setValidationMessages([
                'id' => ['Screening record not found']
            ]);
            return $processingResult;
        }

        // Filter data to whitelisted fields
        $filteredData = array_intersect_key($data, array_flip(self::WHITELISTED_FIELDS));

        if (empty($filteredData)) {
            $processingResult->setValidationMessages([
                'data' => ['No valid update fields provided']
            ]);
            return $processingResult;
        }

        $query = $this->buildUpdateColumns($filteredData);
        $sql = "UPDATE " . self::TABLE_NAME . " SET " . $query['set'] . " WHERE id = ?";
        $query['bind'][] = $id;

        if ($pid !== null) {
            $sql .= " AND pid = ?";
            $query['bind'][] = $pid;
        }

        $result = sqlStatement($sql, $query['bind']);

        if ($result !== false) {
            $processingResult = $this->getOne($id, $pid);
        } else {
            $processingResult->addInternalError("Error updating transplant screening record");
        }

        return $processingResult;
    }

    /**
     * Delete a transplant screening record.
     *
     * @param int $id Screening record ID.
     * @param int|null $pid Optional patient ID for validation.
     * @return ProcessingResult
     */
    public function delete(int $id, ?int $pid = null): ProcessingResult
    {
        $processingResult = new ProcessingResult();

        // Verify record exists
        $existing = $this->getOne($id, $pid);
        if (!$existing->hasData()) {
            $processingResult->setValidationMessages([
                'id' => ['Screening record not found']
            ]);
            return $processingResult;
        }

        $sql = "DELETE FROM " . self::TABLE_NAME . " WHERE id = ?";
        $binds = [$id];

        if ($pid !== null) {
            $sql .= " AND pid = ?";
            $binds[] = $pid;
        }

        $result = sqlStatement($sql, $binds);

        if ($result !== false) {
            $processingResult->addData(['id' => $id, 'deleted' => true]);
        } else {
            $processingResult->addInternalError("Error deleting transplant screening record");
        }

        return $processingResult;
    }
}
