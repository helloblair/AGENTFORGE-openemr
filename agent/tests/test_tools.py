"""Tests for OpenEMR API tool wrappers.

Run from the agent/ directory:
    pytest tests/test_tools.py -v

Or with coverage:
    pytest tests/test_tools.py -v --tb=short
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# Ensure the agent package root is on the path.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


# ── Shared helpers ────────────────────────────────────────────────────────────

def _mock_response(json_body, status_code: int = 200) -> MagicMock:
    """Return a mock httpx Response-like object."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_body
    resp.raise_for_status = MagicMock()
    return resp


def _mock_http_client(*responses) -> AsyncMock:
    """Async httpx client whose .get() returns responses in order (or loops if one)."""
    client = AsyncMock()
    if len(responses) == 1:
        client.get = AsyncMock(return_value=responses[0])
    else:
        client.get = AsyncMock(side_effect=list(responses))
    return client


def _auth_ctx(http_client: AsyncMock) -> MagicMock:
    """OpenEMRAuth instance whose get_client() context manager yields http_client."""
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=http_client)
    ctx.__aexit__ = AsyncMock(return_value=None)
    auth = MagicMock()
    auth.get_client.return_value = ctx
    return auth


# ── patient_lookup ────────────────────────────────────────────────────────────

_PATIENT_ROW = {
    "uuid": "abc-123",
    "fname": "Jane",
    "lname": "Doe",
    "DOB": "1990-05-10",
    "sex": "Female",
    "phone_home": "555-0100",
    "phone_cell": "",
    "street": "1 Main St",
    "city": "Springfield",
    "state": "IL",
    "postal_code": "62701",
}


class TestPatientLookup:
    @pytest.mark.asyncio
    async def test_requires_at_least_one_arg(self):
        from src.tools.patient_lookup import patient_lookup

        result = await patient_lookup.ainvoke({})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_single_patient_returned(self):
        from src.tools.patient_lookup import patient_lookup

        http = _mock_http_client(_mock_response({"data": [_PATIENT_ROW]}))
        with patch("src.tools.patient_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await patient_lookup.ainvoke({"first_name": "Jane", "last_name": "Doe"})

        assert "Jane Doe" in result
        assert "abc-123" in result
        assert "1990-05-10" in result
        assert "555-0100" in result

    @pytest.mark.asyncio
    async def test_empty_results_message(self):
        from src.tools.patient_lookup import patient_lookup

        http = _mock_http_client(_mock_response({"data": []}))
        with patch("src.tools.patient_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await patient_lookup.ainvoke({"last_name": "NoOne"})

        assert "No patients found" in result

    @pytest.mark.asyncio
    async def test_bare_list_response(self):
        """API may return a bare list instead of wrapping in 'data'."""
        from src.tools.patient_lookup import patient_lookup

        http = _mock_http_client(_mock_response([_PATIENT_ROW]))
        with patch("src.tools.patient_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await patient_lookup.ainvoke({"last_name": "Doe"})

        assert "Jane Doe" in result

    @pytest.mark.asyncio
    async def test_multiple_patients_shows_count(self):
        from src.tools.patient_lookup import patient_lookup

        rows = [
            {**_PATIENT_ROW, "uuid": f"u{i}", "fname": "John", "lname": "Smith"}
            for i in range(3)
        ]
        http = _mock_http_client(_mock_response({"data": rows}))
        with patch("src.tools.patient_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await patient_lookup.ainvoke({"last_name": "Smith"})

        assert "3" in result

    @pytest.mark.asyncio
    async def test_timeout_returns_friendly_error(self):
        from src.tools.patient_lookup import patient_lookup

        http = AsyncMock()
        http.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        with patch("src.tools.patient_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await patient_lookup.ainvoke({"last_name": "Smith"})

        assert "Unable to reach" in result

    @pytest.mark.asyncio
    async def test_http_error_returns_friendly_error(self):
        from src.tools.patient_lookup import patient_lookup

        bad_resp = _mock_response({}, status_code=500)
        bad_resp.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=bad_resp)
        )
        http = _mock_http_client(bad_resp)
        with patch("src.tools.patient_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await patient_lookup.ainvoke({"last_name": "Smith"})

        assert "Unable to reach" in result

    def test_format_patient_full_address(self):
        from src.tools.patient_lookup import _format_patient

        result = _format_patient(_PATIENT_ROW)
        assert result["name"] == "Jane Doe"
        assert "1 Main St" in result["address"]
        assert "Springfield" in result["address"]
        assert result["phone"] == "555-0100"

    def test_format_patient_prefers_cell_when_no_home(self):
        from src.tools.patient_lookup import _format_patient

        row = {**_PATIENT_ROW, "phone_home": "", "phone_cell": "555-9999"}
        result = _format_patient(row)
        assert result["phone"] == "555-9999"

    def test_format_patient_empty_address_when_no_address_fields(self):
        from src.tools.patient_lookup import _format_patient

        row = {**_PATIENT_ROW, "street": "", "city": "", "state": "", "postal_code": ""}
        result = _format_patient(row)
        assert result["address"] == ""


# ── allergy_check ─────────────────────────────────────────────────────────────

_ALLERGY_BUNDLE = {
    "entry": [
        {
            "resource": {
                "code": {
                    "text": "Penicillin",
                    "coding": [
                        {"system": "http://snomed.info/sct", "code": "372687004", "display": "Penicillin"}
                    ],
                },
                "category": ["medication"],
                "criticality": "high",
                "reaction": [
                    {
                        "manifestation": [{"coding": [{"display": "Hives"}]}],
                        "description": "Generalized urticaria",
                    }
                ],
            }
        }
    ]
}


class TestAllergyCheck:
    @pytest.mark.asyncio
    async def test_requires_patient_uuid(self):
        from src.tools.allergy_check import allergy_check

        result = await allergy_check.ainvoke({"patient_uuid": ""})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_whitespace_uuid_rejected(self):
        from src.tools.allergy_check import allergy_check

        result = await allergy_check.ainvoke({"patient_uuid": "   "})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_returns_allergies(self):
        from src.tools.allergy_check import allergy_check

        http = _mock_http_client(_mock_response(_ALLERGY_BUNDLE))
        with patch("src.tools.allergy_check.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await allergy_check.ainvoke({"patient_uuid": "abc-123"})

        assert "Penicillin" in result
        assert "high" in result
        assert "Hives" in result

    @pytest.mark.asyncio
    async def test_empty_bundle_returns_no_allergies(self):
        from src.tools.allergy_check import allergy_check

        http = _mock_http_client(_mock_response({"resourceType": "Bundle"}))
        with patch("src.tools.allergy_check.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await allergy_check.ainvoke({"patient_uuid": "abc-123"})

        assert "No allergies" in result

    def test_parse_allergy_uses_code_text(self):
        from src.tools.allergy_check import _parse_allergy

        resource = {
            "code": {"text": "Sulfa drugs", "coding": []},
            "category": ["medication"],
            "criticality": "low",
            "reaction": [],
        }
        result = _parse_allergy(resource)
        assert result["substance"] == "Sulfa drugs"
        assert result["criticality"] == "low"
        assert result["reactions"] is None

    def test_parse_allergy_falls_back_to_html_narrative(self):
        from src.tools.allergy_check import _parse_allergy

        resource = {
            "code": {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/data-absent-reason",
                        "code": "unknown",
                    }
                ]
            },
            "text": {"div": "<div><p>Tree pollen</p></div>"},
            "category": ["environment"],
            "criticality": "unable-to-assess",
            "reaction": [],
        }
        result = _parse_allergy(resource)
        assert result["substance"] == "Tree pollen"

    def test_parse_allergy_collects_multiple_reactions(self):
        from src.tools.allergy_check import _parse_allergy

        resource = {
            "code": {"text": "Aspirin"},
            "category": ["medication"],
            "criticality": "low",
            "reaction": [
                {
                    "manifestation": [
                        {"coding": [{"display": "Rash"}]},
                        {"coding": [{"display": "Itching"}]},
                    ]
                }
            ],
        }
        result = _parse_allergy(resource)
        assert "Rash" in result["reactions"]
        assert "Itching" in result["reactions"]

    def test_strip_html_removes_tags(self):
        from src.tools.allergy_check import _strip_html

        assert _strip_html("<div><b>Hello</b> World</div>") == "Hello World"
        assert _strip_html("Plain text") == "Plain text"
        assert _strip_html("") == ""


# ── drug_interaction_check ────────────────────────────────────────────────────

class TestDrugInteractionCheck:
    @pytest.mark.asyncio
    async def test_requires_two_drugs(self):
        from src.tools.drug_interaction_check import drug_interaction_check

        result = await drug_interaction_check.ainvoke({"drug_names": ["aspirin"]})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_empty_list_rejected(self):
        from src.tools.drug_interaction_check import drug_interaction_check

        result = await drug_interaction_check.ainvoke({"drug_names": []})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_both_drugs_unresolved(self):
        """When RxNorm returns no IDs, each drug is reported as unresolved."""
        from src.tools.drug_interaction_check import drug_interaction_check

        # RxNorm resolves neither drug.
        rxnorm_empty = _mock_response({"idGroup": {}})
        http = _mock_http_client(rxnorm_empty, rxnorm_empty)

        mock_client_cls = MagicMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=http)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=None)

        with patch("src.tools.drug_interaction_check.httpx.AsyncClient", mock_client_cls):
            result = await drug_interaction_check.ainvoke(
                {"drug_names": ["fakedrugaaa", "fakedrugbbb"]}
            )

        assert "fakedrugaaa" in result or "fakedrugbbb" in result

    def test_format_results_no_interactions(self):
        from src.tools.drug_interaction_check import _format_results

        result = _format_results([], [])
        assert "No known interactions" in result

    def test_format_results_with_unresolved_drug(self):
        from src.tools.drug_interaction_check import _format_results

        result = _format_results([], ["fakedrugxyz"])
        assert "fakedrugxyz" in result
        assert "verify spelling" in result

    def test_format_results_with_interaction(self):
        from src.tools.drug_interaction_check import _format_results

        interactions = [
            {
                "drug_pair": "Aspirin + Warfarin",
                "severity": "see description",
                "description": "Co-administration increases bleeding risk.",
            }
        ]
        result = _format_results(interactions, [])
        assert "Aspirin + Warfarin" in result
        assert "bleeding risk" in result

    def test_clean_label_text_strips_section_numbers(self):
        from src.tools.drug_interaction_check import _clean_label_text

        assert _clean_label_text("7 DRUG INTERACTIONS aspirin may interact") == "aspirin may interact"
        assert _clean_label_text("7.1 Some important text") == "Some important text"
        assert _clean_label_text("Normal sentence.") == "Normal sentence."


# ── medication_list ───────────────────────────────────────────────────────────

_MED_BUNDLE = {
    "entry": [
        {
            "resource": {
                "resourceType": "MedicationRequest",
                "medicationCodeableConcept": {
                    "text": "Metformin 500 mg",
                    "coding": [{"display": "metFORMIN"}],
                },
                "dosageInstruction": [
                    {
                        "doseAndRate": [{"doseQuantity": {"value": 500, "unit": "mg"}}],
                        "timing": {"repeat": {"frequency": 2, "period": 1, "periodUnit": "d"}},
                        "route": {"text": "Oral"},
                    }
                ],
                "requester": {"display": "Dr. Patel"},
                "authoredOn": "2024-01-15",
                "status": "active",
            }
        }
    ]
}


class TestMedicationList:
    @pytest.mark.asyncio
    async def test_requires_patient_uuid(self):
        from src.tools.medication_list import medication_list

        result = await medication_list.ainvoke({"patient_uuid": ""})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_returns_medications(self):
        from src.tools.medication_list import medication_list

        http = _mock_http_client(_mock_response(_MED_BUNDLE))
        with patch("src.tools.medication_list.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await medication_list.ainvoke({"patient_uuid": "abc-123"})

        assert "Metformin 500 mg" in result
        assert "Dr. Patel" in result
        assert "Oral" in result
        assert "2024-01-15" in result
        assert "active" in result

    @pytest.mark.asyncio
    async def test_empty_bundle_returns_no_meds(self):
        from src.tools.medication_list import medication_list

        http = _mock_http_client(_mock_response({"resourceType": "Bundle"}))
        with patch("src.tools.medication_list.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await medication_list.ainvoke({"patient_uuid": "abc-123"})

        assert "No active medications" in result

    def test_parse_medication_extracts_dosage_and_frequency(self):
        from src.tools.medication_list import _parse_medication

        resource = _MED_BUNDLE["entry"][0]["resource"]
        result = _parse_medication(resource)
        assert result["drug_name"] == "Metformin 500 mg"
        assert result["dosage"] == "500 mg"
        assert result["frequency"] == "2 per 1 day(s)"
        assert result["route"] == "Oral"
        assert result["prescriber"] == "Dr. Patel"
        assert result["status"] == "active"

    def test_parse_medication_falls_back_to_coding_display(self):
        from src.tools.medication_list import _parse_medication

        resource = {
            "medicationCodeableConcept": {
                "coding": [{"display": "lisinopril 10 MG Oral Tablet"}]
            },
            "dosageInstruction": [],
            "status": "active",
        }
        result = _parse_medication(resource)
        assert result["drug_name"] == "lisinopril 10 MG Oral Tablet"

    def test_parse_medication_unknown_when_no_concept(self):
        from src.tools.medication_list import _parse_medication

        result = _parse_medication({"status": "active"})
        assert result["drug_name"] == "Unknown medication"
        assert result["dosage"] is None
        assert result["frequency"] is None

    def test_parse_medication_uses_text_dosage_instruction(self):
        from src.tools.medication_list import _parse_medication

        resource = {
            "medicationCodeableConcept": {"text": "Amoxicillin"},
            "dosageInstruction": [{"text": "Take one capsule twice daily"}],
            "status": "active",
        }
        result = _parse_medication(resource)
        assert result["frequency"] == "Take one capsule twice daily"


# ── problem_list ──────────────────────────────────────────────────────────────

_CONDITION_BUNDLE = {
    "entry": [
        {
            "resource": {
                "resourceType": "Condition",
                "code": {
                    "text": "Type 2 diabetes mellitus",
                    "coding": [
                        {
                            "system": "http://hl7.org/fhir/sid/icd-10-cm",
                            "code": "E11",
                            "display": "Type 2 diabetes mellitus",
                        }
                    ],
                },
                "clinicalStatus": {"coding": [{"code": "active"}]},
                "category": [{"coding": [{"code": "problem-list-item"}]}],
                "onsetDateTime": "2019-03-01",
            }
        }
    ]
}


class TestProblemList:
    @pytest.mark.asyncio
    async def test_requires_patient_uuid(self):
        from src.tools.problem_list import problem_list

        result = await problem_list.ainvoke({"patient_uuid": ""})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_returns_conditions(self):
        from src.tools.problem_list import problem_list

        http = _mock_http_client(_mock_response(_CONDITION_BUNDLE))
        with patch("src.tools.problem_list.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await problem_list.ainvoke({"patient_uuid": "abc-123"})

        assert "Type 2 diabetes" in result
        assert "E11" in result
        assert "active" in result

    @pytest.mark.asyncio
    async def test_empty_bundle_returns_no_conditions(self):
        from src.tools.problem_list import problem_list

        http = _mock_http_client(_mock_response({"resourceType": "Bundle"}))
        with patch("src.tools.problem_list.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await problem_list.ainvoke({"patient_uuid": "abc-123"})

        assert "No active conditions" in result

    def test_parse_condition_extracts_icd10(self):
        from src.tools.problem_list import _parse_condition

        resource = _CONDITION_BUNDLE["entry"][0]["resource"]
        result = _parse_condition(resource)
        assert result["name"] == "Type 2 diabetes mellitus"
        assert result["icd10_code"] == "E11"
        assert result["clinical_status"] == "active"
        assert result["onset_date"] == "2019-03-01"
        assert result["category"] == "problem-list-item"

    def test_parse_condition_uses_onset_period_start(self):
        from src.tools.problem_list import _parse_condition

        resource = {
            "code": {"text": "Hypertension"},
            "onsetPeriod": {"start": "2015-06-01"},
            "clinicalStatus": {"text": "active"},
        }
        result = _parse_condition(resource)
        assert result["onset_date"] == "2015-06-01"

    def test_parse_condition_unknown_fallbacks(self):
        from src.tools.problem_list import _parse_condition

        result = _parse_condition({})
        assert result["name"] == "Unknown condition"
        assert result["icd10_code"] is None
        assert result["onset_date"] is None


# ── insurance_coverage ────────────────────────────────────────────────────────

_COVERAGE_BUNDLE = {
    "entry": [
        {
            "resource": {
                "resourceType": "Coverage",
                "class": [
                    {
                        "type": {"coding": [{"code": "plan"}]},
                        "name": "Gold PPO",
                        "value": "GPPO",
                    }
                ],
                "type": {"text": "Medical"},
                "payor": [{"display": "Blue Cross Blue Shield"}],
                "subscriberId": "BCBS123456",
                "period": {"start": "2023-01-01", "end": "2099-12-31"},
                "status": "active",
                "relationship": {"coding": [{"code": "self", "display": "Self"}]},
            }
        }
    ]
}


class TestInsuranceCoverage:
    @pytest.mark.asyncio
    async def test_requires_patient_uuid(self):
        from src.tools.insurance_coverage import insurance_coverage

        result = await insurance_coverage.ainvoke({"patient_uuid": ""})
        assert "Error" in result

    @pytest.mark.asyncio
    async def test_returns_coverage(self):
        from src.tools.insurance_coverage import insurance_coverage

        http = _mock_http_client(_mock_response(_COVERAGE_BUNDLE))
        with patch("src.tools.insurance_coverage.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await insurance_coverage.ainvoke({"patient_uuid": "abc-123"})

        assert "Gold PPO" in result
        assert "Blue Cross Blue Shield" in result
        assert "BCBS123456" in result
        assert "Self" in result

    @pytest.mark.asyncio
    async def test_empty_bundle_returns_no_coverage(self):
        from src.tools.insurance_coverage import insurance_coverage

        http = _mock_http_client(_mock_response({"resourceType": "Bundle"}))
        with patch("src.tools.insurance_coverage.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await insurance_coverage.ainvoke({"patient_uuid": "abc-123"})

        assert "No insurance coverage" in result

    @pytest.mark.asyncio
    async def test_expired_coverage_is_flagged(self):
        from src.tools.insurance_coverage import insurance_coverage

        bundle = {
            "entry": [
                {
                    "resource": {
                        "resourceType": "Coverage",
                        "class": [{"type": {"coding": [{"code": "plan"}]}, "name": "Old Plan"}],
                        "payor": [{"display": "Former Insurer"}],
                        "period": {"start": "2010-01-01", "end": "2015-12-31"},
                        "status": "cancelled",
                    }
                }
            ]
        }
        http = _mock_http_client(_mock_response(bundle))
        with patch("src.tools.insurance_coverage.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await insurance_coverage.ainvoke({"patient_uuid": "abc-123"})

        assert "EXPIRED" in result or "expired" in result.lower()

    def test_parse_coverage_extracts_all_fields(self):
        from src.tools.insurance_coverage import _parse_coverage

        resource = _COVERAGE_BUNDLE["entry"][0]["resource"]
        result = _parse_coverage(resource)
        assert result["plan_name"] == "Gold PPO"
        assert result["insurer"] == "Blue Cross Blue Shield"
        assert result["policy_number"] == "BCBS123456"
        assert result["coverage_type"] == "Medical"
        assert result["status"] == "active"
        assert result["relationship"] == "Self"
        assert result["effective_start"] == "2023-01-01"

    def test_is_expired_past_date(self):
        from src.tools.insurance_coverage import _is_expired

        assert _is_expired({"effective_end": "2020-01-01"}) is True

    def test_is_not_expired_future_date(self):
        from src.tools.insurance_coverage import _is_expired

        assert _is_expired({"effective_end": "2099-12-31"}) is False

    def test_is_not_expired_no_end_date(self):
        from src.tools.insurance_coverage import _is_expired

        assert _is_expired({"effective_end": None}) is False
        assert _is_expired({}) is False


# ── provider_lookup ───────────────────────────────────────────────────────────

_PRACTITIONER_BUNDLE = {
    "entry": [
        {
            "resource": {
                "resourceType": "Practitioner",
                "id": "pract-001",
                "name": [{"prefix": ["Dr."], "given": ["Alice"], "family": "Chen"}],
                "telecom": [
                    {"system": "phone", "value": "555-2000"},
                    {"system": "email", "value": "achen@clinic.org"},
                ],
                "identifier": [
                    {"system": "http://hl7.org/fhir/sid/us-npi", "value": "1234567890"}
                ],
            }
        },
        {
            "resource": {
                "resourceType": "Practitioner",
                "id": "pract-002",
                "name": [{"given": ["Bob"], "family": "Smith"}],
                "telecom": [],
            }
        },
    ]
}

_ROLE_BUNDLE = {
    "entry": [
        {
            "resource": {
                "practitioner": {"reference": "Practitioner/pract-001"},
                "specialty": [{"text": "Cardiology"}],
            }
        }
    ]
}


class TestProviderLookup:
    def _http_with_roles(self):
        """Client that returns the practitioner bundle, then the role bundle."""
        return _mock_http_client(
            _mock_response(_PRACTITIONER_BUNDLE),
            _mock_response(_ROLE_BUNDLE),
        )

    @pytest.mark.asyncio
    async def test_directory_listing_returns_all_providers(self):
        from src.tools.provider_lookup import provider_lookup

        http = self._http_with_roles()
        with patch("src.tools.provider_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await provider_lookup.ainvoke({})

        assert "Chen" in result
        assert "Bob Smith" in result

    @pytest.mark.asyncio
    async def test_filter_by_name_case_insensitive(self):
        from src.tools.provider_lookup import provider_lookup

        http = self._http_with_roles()
        with patch("src.tools.provider_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await provider_lookup.ainvoke({"name": "chen"})

        assert "Chen" in result
        assert "Bob Smith" not in result

    @pytest.mark.asyncio
    async def test_filter_by_specialty(self):
        from src.tools.provider_lookup import provider_lookup

        http = self._http_with_roles()
        with patch("src.tools.provider_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await provider_lookup.ainvoke({"specialty": "Cardiology"})

        assert "Alice" in result or "Chen" in result
        assert "Bob Smith" not in result

    @pytest.mark.asyncio
    async def test_name_no_match_returns_message(self):
        from src.tools.provider_lookup import provider_lookup

        http = self._http_with_roles()
        with patch("src.tools.provider_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await provider_lookup.ainvoke({"name": "Zzzznotaname"})

        assert "No providers found" in result

    @pytest.mark.asyncio
    async def test_specialty_no_match_returns_message(self):
        from src.tools.provider_lookup import provider_lookup

        http = self._http_with_roles()
        with patch("src.tools.provider_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await provider_lookup.ainvoke({"specialty": "Neurosurgery"})

        assert "No providers found" in result

    @pytest.mark.asyncio
    async def test_empty_practitioner_bundle(self):
        from src.tools.provider_lookup import provider_lookup

        http = _mock_http_client(_mock_response({"resourceType": "Bundle"}))
        with patch("src.tools.provider_lookup.OpenEMRAuth", return_value=_auth_ctx(http)):
            result = await provider_lookup.ainvoke({})

        assert "No providers" in result

    def test_format_fhir_practitioner_extracts_fields(self):
        from src.tools.provider_lookup import _format_fhir_practitioner

        resource = _PRACTITIONER_BUNDLE["entry"][0]["resource"]
        result = _format_fhir_practitioner(resource)
        assert "Alice" in result["name"]
        assert "Chen" in result["name"]
        assert result["phone"] == "555-2000"
        assert result["email"] == "achen@clinic.org"
        assert result["npi"] == "1234567890"
        assert result["uuid"] == "pract-001"

    def test_format_fhir_practitioner_includes_prefix(self):
        from src.tools.provider_lookup import _format_fhir_practitioner

        resource = _PRACTITIONER_BUNDLE["entry"][0]["resource"]
        result = _format_fhir_practitioner(resource)
        assert "Dr." in result["name"]

    def test_enrich_specialties_merges_by_uuid(self):
        from src.tools.provider_lookup import _enrich_specialties, _format_fhir_practitioner

        practitioners = [
            _format_fhir_practitioner(e["resource"])
            for e in _PRACTITIONER_BUNDLE["entry"]
        ]
        result = _enrich_specialties(practitioners, _ROLE_BUNDLE["entry"])

        pract_001 = next(p for p in result if p["uuid"] == "pract-001")
        pract_002 = next(p for p in result if p["uuid"] == "pract-002")
        assert pract_001["specialty"] == "Cardiology"
        assert pract_002["specialty"] == ""  # no role entry for pract-002

    def test_matches_specialty_case_insensitive(self):
        from src.tools.provider_lookup import _matches_specialty

        pract = {"specialty": "Family Medicine"}
        assert _matches_specialty(pract, "family") is True
        assert _matches_specialty(pract, "MEDICINE") is True
        assert _matches_specialty(pract, "Cardiology") is False

    def test_matches_specialty_empty_specialty(self):
        from src.tools.provider_lookup import _matches_specialty

        assert _matches_specialty({"specialty": ""}, "Cardiology") is False
        assert _matches_specialty({}, "Cardiology") is False
