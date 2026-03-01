<?php

/**
 * Transplant Screening REST Controller
 *
 * Handles REST API requests for per-patient transplant screening CRUD operations.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Veris Agent <veris@openemr.org>
 * @copyright Copyright (c) 2026 Veris Agent
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

namespace OpenEMR\RestControllers;

use OpenEMR\Common\Http\HttpRestRequest;
use OpenEMR\Common\Database\QueryUtils;
use OpenEMR\Services\TransplantScreeningService;

class TransplantScreeningRestController
{
    private TransplantScreeningService $service;

    public function __construct()
    {
        $this->service = new TransplantScreeningService();
    }

    /**
     * Resolve a patient UUID string to a numeric pid.
     *
     * @param string $puuid Patient UUID string.
     * @return int|null The patient pid, or null if not found.
     */
    private function resolvePid(string $puuid): ?int
    {
        $sql = "SELECT pid FROM patient_data WHERE uuid = ?";
        $uuidBinary = \OpenEMR\Common\Uuid\UuidRegistry::uuidToBytes($puuid);
        $records = QueryUtils::fetchRecords($sql, [$uuidBinary]);
        return !empty($records) ? (int) $records[0]['pid'] : null;
    }

    /**
     * POST /api/patient/:puuid/transplant_screening
     *
     * Create a new transplant screening for a patient.
     *
     * @param string $puuid Patient UUID.
     * @param array $data Request body (organ_type required).
     * @param HttpRestRequest $request
     * @return array
     */
    public function post(string $puuid, array $data, HttpRestRequest $request): array
    {
        $pid = $this->resolvePid($puuid);
        if ($pid === null) {
            $result = new \OpenEMR\Validators\ProcessingResult();
            $result->setValidationMessages(['puuid' => ['Patient not found']]);
            return RestControllerHelper::handleProcessingResult($result, 404);
        }

        $processingResult = $this->service->insert($pid, $data);
        return RestControllerHelper::handleProcessingResult($processingResult, 201);
    }

    /**
     * GET /api/patient/:puuid/transplant_screening
     *
     * Get all transplant screenings for a patient.
     *
     * @param string $puuid Patient UUID.
     * @param HttpRestRequest $request
     * @return array
     */
    public function getAll(string $puuid, HttpRestRequest $request): array
    {
        $pid = $this->resolvePid($puuid);
        if ($pid === null) {
            $result = new \OpenEMR\Validators\ProcessingResult();
            $result->setValidationMessages(['puuid' => ['Patient not found']]);
            return RestControllerHelper::handleProcessingResult($result, 404);
        }

        $processingResult = $this->service->getByPatient($pid);
        return RestControllerHelper::handleProcessingResult($processingResult, 200, true);
    }

    /**
     * GET /api/patient/:puuid/transplant_screening/:sid
     *
     * Get a specific transplant screening.
     *
     * @param string $puuid Patient UUID.
     * @param int $sid Screening record ID.
     * @param HttpRestRequest $request
     * @return array
     */
    public function getOne(string $puuid, int $sid, HttpRestRequest $request): array
    {
        $pid = $this->resolvePid($puuid);
        if ($pid === null) {
            $result = new \OpenEMR\Validators\ProcessingResult();
            $result->setValidationMessages(['puuid' => ['Patient not found']]);
            return RestControllerHelper::handleProcessingResult($result, 404);
        }

        $processingResult = $this->service->getOne($sid, $pid);

        if (!$processingResult->hasErrors() && count($processingResult->getData()) == 0) {
            return RestControllerHelper::handleProcessingResult($processingResult, 404);
        }

        return RestControllerHelper::handleProcessingResult($processingResult, 200);
    }

    /**
     * PUT /api/patient/:puuid/transplant_screening/:sid
     *
     * Update a transplant screening record.
     *
     * @param string $puuid Patient UUID.
     * @param int $sid Screening record ID.
     * @param array $data Updated fields.
     * @param HttpRestRequest $request
     * @return array
     */
    public function put(string $puuid, int $sid, array $data, HttpRestRequest $request): array
    {
        $pid = $this->resolvePid($puuid);
        if ($pid === null) {
            $result = new \OpenEMR\Validators\ProcessingResult();
            $result->setValidationMessages(['puuid' => ['Patient not found']]);
            return RestControllerHelper::handleProcessingResult($result, 404);
        }

        $processingResult = $this->service->update($sid, $data, $pid);
        return RestControllerHelper::handleProcessingResult($processingResult, 200);
    }

    /**
     * DELETE /api/patient/:puuid/transplant_screening/:sid
     *
     * Delete a transplant screening record.
     *
     * @param string $puuid Patient UUID.
     * @param int $sid Screening record ID.
     * @param HttpRestRequest $request
     * @return array
     */
    public function delete(string $puuid, int $sid, HttpRestRequest $request): array
    {
        $pid = $this->resolvePid($puuid);
        if ($pid === null) {
            $result = new \OpenEMR\Validators\ProcessingResult();
            $result->setValidationMessages(['puuid' => ['Patient not found']]);
            return RestControllerHelper::handleProcessingResult($result, 404);
        }

        $processingResult = $this->service->delete($sid, $pid);
        return RestControllerHelper::handleProcessingResult($processingResult, 200);
    }
}
