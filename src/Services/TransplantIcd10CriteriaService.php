<?php

/**
 * Transplant ICD-10 Criteria Service
 *
 * Provides CRUD operations for the transplant_icd10_criteria reference table,
 * which stores ICD-10-CM codes relevant to organ transplant candidacy screening.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Veris Agent <veris@openemr.org>
 * @copyright Copyright (c) 2026 Veris Agent
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

namespace OpenEMR\Services;

use OpenEMR\Common\Database\QueryUtils;
use OpenEMR\Validators\ProcessingResult;

class TransplantIcd10CriteriaService extends BaseService
{
    public const TABLE_NAME = "transplant_icd10_criteria";

    /**
     * Supported search/filter fields.
     */
    private const SUPPORTED_SEARCH_FIELDS = [
        'organ_system',
        'criteria_type',
        'icd10_code',
        'is_billable',
    ];

    public function __construct()
    {
        parent::__construct(self::TABLE_NAME);
    }

    /**
     * Get all transplant ICD-10 criteria, with optional filtering.
     *
     * @param array $search Associative array of search filters.
     *   Supported keys: organ_system, criteria_type, icd10_code, is_billable
     * @return ProcessingResult
     */
    public function getAll(array $search = []): ProcessingResult
    {
        $processingResult = new ProcessingResult();

        $sql = "SELECT id, icd10_code, short_description, long_description, "
             . "is_billable, organ_system, criteria_type, created_at, updated_at "
             . "FROM " . self::TABLE_NAME;

        $whereFragments = [];
        $binds = [];

        foreach ($search as $key => $value) {
            if (!in_array($key, self::SUPPORTED_SEARCH_FIELDS, true)) {
                continue;
            }
            if ($value === null || $value === '') {
                continue;
            }
            $whereFragments[] = "`{$key}` = ?";
            $binds[] = $value;
        }

        if (!empty($whereFragments)) {
            $sql .= " WHERE " . implode(" AND ", $whereFragments);
        }

        $sql .= " ORDER BY icd10_code ASC";

        $records = QueryUtils::fetchRecords($sql, $binds);
        foreach ($records as $record) {
            $processingResult->addData($record);
        }

        return $processingResult;
    }

    /**
     * Look up a specific ICD-10 code's transplant relevance.
     *
     * @param string $code The ICD-10-CM code (e.g. "N18.6")
     * @return ProcessingResult
     */
    public function getByCode(string $code): ProcessingResult
    {
        $processingResult = new ProcessingResult();

        $sql = "SELECT id, icd10_code, short_description, long_description, "
             . "is_billable, organ_system, criteria_type, created_at, updated_at "
             . "FROM " . self::TABLE_NAME
             . " WHERE icd10_code = ?";

        $records = QueryUtils::fetchRecords($sql, [$code]);
        foreach ($records as $record) {
            $processingResult->addData($record);
        }

        return $processingResult;
    }
}
