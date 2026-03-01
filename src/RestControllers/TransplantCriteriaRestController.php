<?php

/**
 * Transplant Criteria REST Controller
 *
 * Handles REST API requests for transplant ICD-10 criteria reference data.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Veris Agent <veris@openemr.org>
 * @copyright Copyright (c) 2026 Veris Agent
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

namespace OpenEMR\RestControllers;

use OpenEMR\Common\Http\HttpRestRequest;
use OpenEMR\Services\TransplantIcd10CriteriaService;

class TransplantCriteriaRestController
{
    private TransplantIcd10CriteriaService $service;

    public function __construct()
    {
        $this->service = new TransplantIcd10CriteriaService();
    }

    /**
     * GET /api/transplant/criteria
     *
     * Returns transplant ICD-10 criteria, filterable by organ_system and criteria_type.
     *
     * @param HttpRestRequest $request
     * @param array $search Query parameters for filtering.
     * @return array
     */
    public function getAll(HttpRestRequest $request, array $search = []): array
    {
        $processingResult = $this->service->getAll($search);
        return RestControllerHelper::handleProcessingResult($processingResult, 200, true);
    }

    /**
     * GET /api/transplant/criteria/:code
     *
     * Look up a specific ICD-10 code's transplant relevance.
     *
     * @param string $code The ICD-10-CM code (e.g. "N18.6").
     * @param HttpRestRequest $request
     * @return array
     */
    public function getByCode(string $code, HttpRestRequest $request): array
    {
        $processingResult = $this->service->getByCode($code);

        if (!$processingResult->hasErrors() && count($processingResult->getData()) == 0) {
            return RestControllerHelper::handleProcessingResult($processingResult, 404);
        }

        return RestControllerHelper::handleProcessingResult($processingResult, 200);
    }
}
