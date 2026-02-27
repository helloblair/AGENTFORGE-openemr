"""Tests for the drug safety validator post-processor."""

import pytest

from src.verification.drug_safety import (
    CLINICAL_DATA_DISCLAIMER,
    CLINICAL_DATA_TOOLS,
    CROSS_REACTIVITY,
    MEDICATION_TOOLS,
    _parse_allergies_from_text,
    _parse_medications_from_text,
    check_drug_safety,
    find_conflicts,
    format_warning,
    should_add_clinical_disclaimer,
)


# ── Allergy parsing ──────────────────────────────────────────────────────────


class TestParseAllergies:
    def test_single_allergy(self):
        text = (
            "Found 1 documented allergy(ies):\n\n"
            "- Penicillin\n"
            "  Category: medication  |  Criticality: high\n"
            "  Reactions: Anaphylaxis\n"
        )
        result = _parse_allergies_from_text(text)
        assert result == ["Penicillin"]

    def test_multiple_allergies(self):
        text = (
            "Found 2 documented allergy(ies):\n\n"
            "- Penicillin\n"
            "  Category: medication  |  Criticality: high\n"
            "  Reactions: Anaphylaxis\n\n"
            "- Sulfa\n"
            "  Category: medication  |  Criticality: low\n"
        )
        result = _parse_allergies_from_text(text)
        assert result == ["Penicillin", "Sulfa"]

    def test_no_allergies(self):
        text = "No allergies documented for this patient."
        result = _parse_allergies_from_text(text)
        assert result == []

    def test_unknown_substance_excluded(self):
        text = (
            "Found 1 documented allergy(ies):\n\n"
            "- Unknown substance\n"
            "  Category: medication  |  Criticality: unknown\n"
        )
        result = _parse_allergies_from_text(text)
        assert result == []


# ── Medication parsing ────────────────────────────────────────────────────────


class TestParseMedications:
    def test_single_medication(self):
        text = (
            "Found 1 active medication(s):\n\n"
            "- Amoxicillin\n"
            "  Dosage: 500 mg | Frequency: 3 per 1 day(s) | Route: oral\n"
            "  Prescriber: Dr. Smith\n"
            "  Start date: 2024-01-15\n"
            "  Status: active\n"
        )
        result = _parse_medications_from_text(text)
        assert result == ["Amoxicillin"]

    def test_multiple_medications(self):
        text = (
            "Found 2 active medication(s):\n\n"
            "- Lisinopril\n"
            "  Dosage: 10 mg\n"
            "  Status: active\n\n"
            "- Amoxicillin\n"
            "  Dosage: 500 mg\n"
            "  Status: active\n"
        )
        result = _parse_medications_from_text(text)
        assert result == ["Lisinopril", "Amoxicillin"]

    def test_no_medications(self):
        text = "No active medications documented for this patient."
        result = _parse_medications_from_text(text)
        assert result == []


# ── Conflict detection ────────────────────────────────────────────────────────


class TestFindConflicts:
    def test_direct_match(self):
        """Allergy to aspirin, patient is on aspirin."""
        conflicts = find_conflicts(["Aspirin"], ["Aspirin"])
        assert len(conflicts) == 1
        assert "Direct match" in conflicts[0]["reason"]

    def test_penicillin_amoxicillin_cross_reactivity(self):
        """KEY TEST: Penicillin allergy should flag amoxicillin."""
        conflicts = find_conflicts(["Penicillin"], ["Amoxicillin"])
        assert len(conflicts) == 1
        assert conflicts[0]["allergy"] == "Penicillin"
        assert conflicts[0]["medication"] == "Amoxicillin"
        assert "Cross-reactivity" in conflicts[0]["reason"]
        assert "penicillin" in conflicts[0]["reason"]

    def test_no_conflict(self):
        """Penicillin allergy, patient on lisinopril — no conflict."""
        conflicts = find_conflicts(["Penicillin"], ["Lisinopril"])
        assert len(conflicts) == 0

    def test_sulfa_cross_reactivity(self):
        """Sulfa allergy should flag bactrim."""
        conflicts = find_conflicts(["Sulfa"], ["Bactrim"])
        assert len(conflicts) == 1
        assert "Cross-reactivity" in conflicts[0]["reason"]

    def test_multiple_conflicts(self):
        """Multiple allergies, multiple conflicting meds."""
        conflicts = find_conflicts(
            ["Penicillin", "NSAID"],
            ["Amoxicillin", "Ibuprofen", "Lisinopril"],
        )
        assert len(conflicts) == 2
        meds = {c["medication"] for c in conflicts}
        assert "Amoxicillin" in meds
        assert "Ibuprofen" in meds

    def test_no_duplicates(self):
        """Same allergy-med pair should not produce duplicate conflicts."""
        conflicts = find_conflicts(
            ["Penicillin", "Penicillin"],
            ["Amoxicillin"],
        )
        assert len(conflicts) == 1

    def test_case_insensitive(self):
        """Matching should be case-insensitive."""
        conflicts = find_conflicts(["penicillin"], ["AMOXICILLIN"])
        assert len(conflicts) == 1

    def test_codeine_cross_reactivity(self):
        """Codeine allergy should flag hydrocodone."""
        conflicts = find_conflicts(["Codeine"], ["Hydrocodone"])
        assert len(conflicts) == 1
        assert "Cross-reactivity" in conflicts[0]["reason"]


# ── Warning formatter ────────────────────────────────────────────────────────


class TestFormatWarning:
    def test_single_conflict(self):
        conflicts = [{
            "allergy": "Penicillin",
            "medication": "Amoxicillin",
            "reason": "Cross-reactivity: penicillin drug class",
        }]
        warning = format_warning(conflicts)
        assert "WARNING" in warning
        assert "ALLERGY-MEDICATION CONFLICT" in warning
        assert "Amoxicillin" in warning
        assert "penicillin" in warning.lower()

    def test_multiple_conflicts(self):
        conflicts = [
            {"allergy": "Penicillin", "medication": "Amoxicillin", "reason": "cross"},
            {"allergy": "NSAID", "medication": "Ibuprofen", "reason": "cross"},
        ]
        warning = format_warning(conflicts)
        assert warning.count("- **") == 2


# ── check_drug_safety integration ────────────────────────────────────────────


class FakeMessage:
    """Minimal message mock for testing."""

    def __init__(self, content: str, tool_calls=None, msg_type="ai"):
        self.content = content
        self.tool_calls = tool_calls or []
        self.type = msg_type


class TestCheckDrugSafety:
    def test_no_medication_tools(self):
        """No medication tools → no warning, no fetch needed."""
        messages = [FakeMessage("Hello")]
        warning, needs_fetch = check_drug_safety(messages, ["patient_lookup"])
        assert warning is None
        assert needs_fetch is False

    def test_medication_tool_with_allergy_data(self):
        """Medication tool used + allergy data present + conflict → warning."""
        allergy_msg = FakeMessage(
            "Found 1 documented allergy(ies):\n\n"
            "- Penicillin\n"
            "  Category: medication  |  Criticality: high\n"
        )
        med_msg = FakeMessage(
            "Found 1 active medication(s):\n\n"
            "- Amoxicillin\n"
            "  Dosage: 500 mg\n"
            "  Status: active\n"
        )
        messages = [allergy_msg, med_msg]
        warning, needs_fetch = check_drug_safety(
            messages, ["medication_list", "allergy_check"]
        )
        assert warning is not None
        assert "WARNING" in warning
        assert "Amoxicillin" in warning
        assert needs_fetch is False

    def test_medication_tool_no_allergy_data(self):
        """Medication tool used + no allergy data → needs_allergy_fetch."""
        med_msg = FakeMessage(
            "Found 1 active medication(s):\n\n"
            "- Lisinopril\n"
            "  Dosage: 10 mg\n"
            "  Status: active\n"
        )
        messages = [med_msg]
        warning, needs_fetch = check_drug_safety(
            messages, ["medication_list"]
        )
        assert warning is None
        assert needs_fetch is True

    def test_no_conflict(self):
        """Medication tool + allergy data but no conflict → no warning."""
        allergy_msg = FakeMessage(
            "Found 1 documented allergy(ies):\n\n"
            "- Shellfish\n"
            "  Category: food  |  Criticality: low\n"
        )
        med_msg = FakeMessage(
            "Found 1 active medication(s):\n\n"
            "- Lisinopril\n"
            "  Dosage: 10 mg\n"
            "  Status: active\n"
        )
        messages = [allergy_msg, med_msg]
        warning, needs_fetch = check_drug_safety(
            messages, ["medication_list", "allergy_check"]
        )
        assert warning is None
        assert needs_fetch is False


# ── Clinical disclaimer logic ────────────────────────────────────────────────


class TestClinicalDisclaimer:
    def test_clinical_tools_trigger_disclaimer(self):
        for tool in CLINICAL_DATA_TOOLS:
            assert should_add_clinical_disclaimer([tool]) is True

    def test_non_clinical_tools_no_disclaimer(self):
        assert should_add_clinical_disclaimer(["patient_lookup"]) is False
        assert should_add_clinical_disclaimer(["provider_lookup"]) is False

    def test_disclaimer_text(self):
        assert "not medical advice" in CLINICAL_DATA_DISCLAIMER
        assert "healthcare provider" in CLINICAL_DATA_DISCLAIMER
