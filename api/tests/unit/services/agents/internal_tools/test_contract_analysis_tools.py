"""
Tests for contract_analysis_tools.py - Contract Analysis Tools

Tests the contract analysis capabilities including type detection,
element extraction, risk assessment, and report generation.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestDetectContractType:
    """Tests for _detect_contract_type function."""

    def test_detects_employment_agreement(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _detect_contract_type

        text = "This employment agreement between employer and employee establishes salary and duties."
        result = _detect_contract_type(text)
        assert "Employment" in result

    def test_detects_service_agreement(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _detect_contract_type

        text = "This service agreement defines deliverables and scope of work for the service provider."
        result = _detect_contract_type(text)
        assert "Service" in result

    def test_detects_nda(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _detect_contract_type

        text = "This non-disclosure agreement protects confidential information and trade secrets."
        result = _detect_contract_type(text)
        assert "Nda" in result

    def test_detects_sales_agreement(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _detect_contract_type

        text = "The buyer agrees to purchase goods from the seller at the specified price with delivery terms."
        result = _detect_contract_type(text)
        assert "Sales" in result

    def test_detects_lease_agreement(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _detect_contract_type

        text = "This lease agreement between lessor and lessee establishes rent and premises terms."
        result = _detect_contract_type(text)
        assert "Lease" in result

    def test_detects_partnership_agreement(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _detect_contract_type

        text = "This partnership agreement governs profit sharing and capital contribution between partners."
        result = _detect_contract_type(text)
        assert "Partnership" in result

    def test_detects_license_agreement(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _detect_contract_type

        text = "This license agreement grants licensor intellectual property rights with royalty payments."
        result = _detect_contract_type(text)
        assert "License" in result

    def test_detects_consulting_agreement(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _detect_contract_type

        text = "The consultant will provide professional services at an hourly rate for consulting work."
        result = _detect_contract_type(text)
        assert "Consulting" in result

    def test_returns_general_contract_for_unknown(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _detect_contract_type

        text = "This is a generic document with no specific legal terms or keywords."
        result = _detect_contract_type(text)
        assert result == "General Contract"


class TestExtractContractElements:
    """Tests for _extract_contract_elements function."""

    def test_detects_parties(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _extract_contract_elements

        text = "This agreement is between the parties hereto."
        result = _extract_contract_elements(text)
        assert result["has_parties"] is True

    def test_detects_effective_date(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _extract_contract_elements

        text = "The effective date of this agreement is January 1, 2024."
        result = _extract_contract_elements(text)
        assert result["has_effective_date"] is True

    def test_detects_termination_clause(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _extract_contract_elements

        text = "Either party may terminate this agreement with 30 days notice."
        result = _extract_contract_elements(text)
        assert result["has_termination_clause"] is True

    def test_detects_governing_law(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _extract_contract_elements

        text = "This agreement shall be governed by the laws of the State of California."
        result = _extract_contract_elements(text)
        assert result["has_governing_law"] is True

    def test_detects_dispute_resolution(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _extract_contract_elements

        text = "Any disputes shall be resolved through arbitration or mediation."
        result = _extract_contract_elements(text)
        assert result["has_dispute_resolution"] is True

    def test_detects_liability_cap(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _extract_contract_elements

        text = "The maximum liability under this agreement shall not exceed $100,000."
        result = _extract_contract_elements(text)
        assert result["has_liability_cap"] is True

    def test_detects_indemnification(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _extract_contract_elements

        text = "Each party shall indemnify and hold harmless the other party."
        result = _extract_contract_elements(text)
        assert result["has_indemnification"] is True

    def test_detects_confidentiality(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _extract_contract_elements

        text = "All proprietary and confidential information shall be protected."
        result = _extract_contract_elements(text)
        assert result["has_confidentiality"] is True

    def test_detects_missing_elements(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _extract_contract_elements

        text = "This is a very simple document with no standard clauses."
        result = _extract_contract_elements(text)
        assert all(value is False for value in result.values())


class TestAnalyzeCommonIssues:
    """Tests for _analyze_common_issues function."""

    def test_identifies_missing_termination_clause(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _analyze_common_issues

        text = "This is a contract without termination provisions."
        elements = {
            "has_termination_clause": False,
            "has_governing_law": True,
            "has_dispute_resolution": True,
            "has_liability_cap": True,
            "has_confidentiality": True,
        }

        result = _analyze_common_issues(text, elements)

        assert len(result["critical"]) > 0
        assert any("Termination" in issue["issue"] for issue in result["critical"])

    def test_identifies_missing_governing_law(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _analyze_common_issues

        text = "This contract has termination but no jurisdiction specified."
        elements = {
            "has_termination_clause": True,
            "has_governing_law": False,
            "has_dispute_resolution": True,
            "has_liability_cap": True,
            "has_confidentiality": True,
        }

        result = _analyze_common_issues(text, elements)

        assert any("Governing Law" in issue["issue"] for issue in result["critical"])

    def test_identifies_missing_dispute_resolution(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _analyze_common_issues

        text = "This contract has no arbitration or mediation clause."
        elements = {
            "has_termination_clause": True,
            "has_governing_law": True,
            "has_dispute_resolution": False,
            "has_liability_cap": True,
            "has_confidentiality": True,
        }

        result = _analyze_common_issues(text, elements)

        assert any("Dispute Resolution" in issue["issue"] for issue in result["moderate"])

    def test_identifies_missing_liability_cap(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _analyze_common_issues

        text = "This contract has unlimited liability exposure."
        elements = {
            "has_termination_clause": True,
            "has_governing_law": True,
            "has_dispute_resolution": True,
            "has_liability_cap": False,
            "has_confidentiality": True,
        }

        result = _analyze_common_issues(text, elements)

        assert any("Liability" in issue["issue"] for issue in result["moderate"])

    def test_identifies_automatic_renewal(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _analyze_common_issues

        text = "This agreement will automatically renew unless cancelled."
        elements = {
            "has_termination_clause": True,
            "has_governing_law": True,
            "has_dispute_resolution": True,
            "has_liability_cap": True,
            "has_confidentiality": True,
        }

        result = _analyze_common_issues(text, elements)

        assert any("Automatic Renewal" in issue["issue"] for issue in result["moderate"])

    def test_identifies_missing_confidentiality(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _analyze_common_issues

        text = "This contract has no confidentiality clause."
        elements = {
            "has_termination_clause": True,
            "has_governing_law": True,
            "has_dispute_resolution": True,
            "has_liability_cap": True,
            "has_confidentiality": False,
        }

        result = _analyze_common_issues(text, elements)

        assert any("Confidentiality" in issue["issue"] for issue in result["minor"])

    def test_identifies_ambiguous_language(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _analyze_common_issues

        text = "The parties will use best efforts to complete as soon as possible in a timely manner."
        elements = {
            "has_termination_clause": True,
            "has_governing_law": True,
            "has_dispute_resolution": True,
            "has_liability_cap": True,
            "has_confidentiality": True,
        }

        result = _analyze_common_issues(text, elements)

        assert any("Ambiguous" in issue["issue"] for issue in result["minor"])


class TestCalculateRiskScore:
    """Tests for _calculate_risk_score function."""

    def test_high_risk_with_critical_issues(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _calculate_risk_score

        findings = {
            "critical": [{"issue": "Issue 1"}, {"issue": "Issue 2"}],  # 2 * 30 = 60
            "moderate": [{"issue": "Issue 3"}],  # 1 * 15 = 15
            "minor": [],
        }

        result = _calculate_risk_score(findings)
        assert result == 75  # 60 + 15

    def test_moderate_risk(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _calculate_risk_score

        findings = {
            "critical": [],
            "moderate": [{"issue": "Issue 1"}, {"issue": "Issue 2"}],  # 2 * 15 = 30
            "minor": [{"issue": "Issue 3"}],  # 1 * 5 = 5
        }

        result = _calculate_risk_score(findings)
        assert result == 35

    def test_low_risk_with_minor_issues(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _calculate_risk_score

        findings = {
            "critical": [],
            "moderate": [],
            "minor": [{"issue": "Issue 1"}, {"issue": "Issue 2"}],  # 2 * 5 = 10
        }

        result = _calculate_risk_score(findings)
        assert result == 10

    def test_zero_risk_with_no_issues(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _calculate_risk_score

        findings = {"critical": [], "moderate": [], "minor": []}

        result = _calculate_risk_score(findings)
        assert result == 0

    def test_caps_at_100(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _calculate_risk_score

        findings = {
            "critical": [{"issue": f"Issue {i}"} for i in range(5)],  # 5 * 30 = 150
            "moderate": [],
            "minor": [],
        }

        result = _calculate_risk_score(findings)
        assert result == 100


class TestGenerateExecutiveSummary:
    """Tests for _generate_executive_summary function."""

    def test_high_risk_summary(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _generate_executive_summary

        findings = {"critical": [{"issue": "Issue 1"}], "moderate": [], "minor": []}

        result = _generate_executive_summary("Service Agreement", 75, findings, "comprehensive")

        assert "HIGH RISK" in result
        assert "Service Agreement" in result
        assert "75/100" in result

    def test_moderate_risk_summary(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _generate_executive_summary

        findings = {"critical": [], "moderate": [{"issue": "Issue 1"}], "minor": []}

        result = _generate_executive_summary("Employment Agreement", 50, findings, "risk_assessment")

        assert "MODERATE RISK" in result

    def test_low_risk_summary(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _generate_executive_summary

        findings = {"critical": [], "moderate": [], "minor": [{"issue": "Issue 1"}]}

        result = _generate_executive_summary("NDA Agreement", 10, findings, "quick")

        assert "LOW RISK" in result


class TestGetKeyRecommendation:
    """Tests for _get_key_recommendation function."""

    def test_critical_issues_recommendation(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _get_key_recommendation

        result = _get_key_recommendation(risk_score=80, critical_count=2)

        assert "Do not sign" in result
        assert "legal counsel" in result.lower()

    def test_moderate_risk_recommendation(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _get_key_recommendation

        result = _get_key_recommendation(risk_score=50, critical_count=0)

        assert "Review" in result or "negotiate" in result.lower()

    def test_low_risk_recommendation(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _get_key_recommendation

        result = _get_key_recommendation(risk_score=20, critical_count=0)

        assert "acceptable" in result.lower() or "minor" in result.lower()


class TestGenerateRecommendations:
    """Tests for _generate_recommendations function."""

    def test_includes_urgent_recommendations_for_critical_issues(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _generate_recommendations

        findings = {
            "critical": [{"issue": "Missing clause", "recommendation": "Add termination clause"}],
            "moderate": [],
            "minor": [],
        }

        result = _generate_recommendations(findings, risk_score=75)

        assert any("URGENT" in rec for rec in result)

    def test_high_risk_includes_attorney_recommendation(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _generate_recommendations

        findings = {"critical": [], "moderate": [], "minor": []}

        result = _generate_recommendations(findings, risk_score=80)

        assert any("attorney" in rec.lower() for rec in result)

    def test_moderate_risk_includes_negotiation_recommendation(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _generate_recommendations

        findings = {"critical": [], "moderate": [], "minor": []}

        result = _generate_recommendations(findings, risk_score=50)

        assert any("negotiate" in rec.lower() or "counsel" in rec.lower() for rec in result)


class TestGetRiskColor:
    """Tests for _get_risk_color function."""

    def test_high_risk_returns_red(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _get_risk_color

        result = _get_risk_color(75)
        assert result == "#e74c3c"  # Red

    def test_moderate_risk_returns_orange(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _get_risk_color

        result = _get_risk_color(50)
        assert result == "#f39c12"  # Orange

    def test_low_risk_returns_green(self):
        from src.services.agents.internal_tools.contract_analysis_tools import _get_risk_color

        result = _get_risk_color(20)
        assert result == "#27ae60"  # Green


class TestInternalAnalyzeContract:
    """Tests for internal_analyze_contract function."""

    @pytest.mark.asyncio
    async def test_returns_error_for_nonexistent_file(self):
        from src.services.agents.internal_tools.contract_analysis_tools import internal_analyze_contract

        result = await internal_analyze_contract(file_path="/nonexistent/file.txt")

        assert "error" in result
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_returns_error_for_unsupported_file_type(self):
        import os
        import tempfile

        from src.services.agents.internal_tools.contract_analysis_tools import internal_analyze_contract

        # Create a temp file with unsupported extension
        with tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False) as f:
            f.write("Some content")
            temp_path = f.name

        try:
            result = await internal_analyze_contract(file_path=temp_path)
            assert "error" in result
            assert "Unsupported file type" in result["error"]
        finally:
            os.unlink(temp_path)

    @pytest.mark.asyncio
    async def test_analyzes_text_contract_successfully(self):
        import os
        import tempfile

        from src.services.agents.internal_tools.contract_analysis_tools import internal_analyze_contract

        # Create a contract text file
        contract_text = (
            """
        SERVICE AGREEMENT

        This Service Agreement is entered into between Company A (the "Service Provider")
        and Company B (the "Client"), effective as of January 1, 2024.

        SCOPE OF SERVICES:
        The Service Provider shall deliver the services as outlined in Exhibit A.

        PAYMENT TERMS:
        Client agrees to pay $10,000 per month for services rendered.

        TERMINATION:
        Either party may terminate this agreement with 30 days written notice.

        CONFIDENTIALITY:
        All proprietary information shall remain confidential.

        GOVERNING LAW:
        This agreement shall be governed by the laws of California.

        DISPUTE RESOLUTION:
        Any disputes shall be resolved through binding arbitration.

        LIMITATION OF LIABILITY:
        Maximum liability shall not exceed the total fees paid.

        IN WITNESS WHEREOF, the parties have executed this agreement.
        """
            * 3
        )  # Make it longer than 100 chars

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(contract_text)
            temp_path = f.name

        try:
            # Mock internal_read_file since it requires workspace config
            # The import happens inside the function, so we patch the source module
            with patch(
                "src.services.agents.internal_tools.file_tools.internal_read_file",
                new_callable=AsyncMock,
                return_value={"file_type": "text", "content": contract_text},
            ):
                result = await internal_analyze_contract(file_path=temp_path)

                assert result["success"] is True
                assert "contract_type" in result
                assert "risk_score" in result
                assert "findings" in result
                assert "recommendations" in result
                assert "executive_summary" in result
        finally:
            os.unlink(temp_path)


class TestInternalGenerateContractReport:
    """Tests for internal_generate_contract_report function."""

    @pytest.mark.asyncio
    async def test_returns_error_for_invalid_data(self):
        from src.services.agents.internal_tools.contract_analysis_tools import internal_generate_contract_report

        result = await internal_generate_contract_report(analysis_data=None)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_returns_error_for_error_data(self):
        from src.services.agents.internal_tools.contract_analysis_tools import internal_generate_contract_report

        result = await internal_generate_contract_report(analysis_data={"error": "Some error"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_generates_markdown_report(self):
        from src.services.agents.internal_tools.contract_analysis_tools import internal_generate_contract_report

        analysis_data = {
            "success": True,
            "file_name": "contract.txt",
            "contract_type": "Service Agreement",
            "analysis_type": "comprehensive",
            "risk_score": 45,
            "executive_summary": "This is a test summary.",
            "findings": {
                "critical": [],
                "moderate": [{"issue": "Test", "description": "Test desc", "recommendation": "Fix it"}],
                "minor": [],
            },
            "recommendations": ["Review the contract"],
            "metadata": {"word_count": 500, "contract_elements": {}},
            "note": "This is automated analysis.",
        }

        result = await internal_generate_contract_report(analysis_data=analysis_data, report_format="markdown")

        assert result["success"] is True
        assert result["report_format"] == "markdown"
        assert "# Contract Analysis Report" in result["report_content"]
        assert ".md" in result["file_name"]

    @pytest.mark.asyncio
    async def test_generates_html_report(self):
        from src.services.agents.internal_tools.contract_analysis_tools import internal_generate_contract_report

        analysis_data = {
            "success": True,
            "file_name": "contract.txt",
            "contract_type": "NDA Agreement",
            "analysis_type": "quick",
            "risk_score": 25,
            "executive_summary": "Low risk contract.",
            "findings": {"critical": [], "moderate": [], "minor": []},
            "recommendations": [],
            "metadata": {"word_count": 200, "contract_elements": {}},
            "note": "Automated analysis.",
        }

        result = await internal_generate_contract_report(analysis_data=analysis_data, report_format="html")

        assert result["success"] is True
        assert result["report_format"] == "html"
        assert "<!DOCTYPE html>" in result["report_content"]
        assert ".html" in result["file_name"]

    @pytest.mark.asyncio
    async def test_generates_json_report(self):
        from src.services.agents.internal_tools.contract_analysis_tools import internal_generate_contract_report

        analysis_data = {
            "success": True,
            "file_name": "contract.txt",
            "contract_type": "Employment Agreement",
            "analysis_type": "risk_assessment",
            "risk_score": 60,
            "executive_summary": "Moderate risk.",
            "findings": {"critical": [], "moderate": [], "minor": []},
            "recommendations": [],
            "metadata": {},
            "note": "Test note.",
        }

        result = await internal_generate_contract_report(analysis_data=analysis_data, report_format="json")

        assert result["success"] is True
        assert result["report_format"] == "json"
        assert ".json" in result["file_name"]

    @pytest.mark.asyncio
    async def test_generates_text_report(self):
        from src.services.agents.internal_tools.contract_analysis_tools import internal_generate_contract_report

        analysis_data = {
            "success": True,
            "file_name": "contract.txt",
            "contract_type": "Lease Agreement",
            "analysis_type": "comprehensive",
            "risk_score": 30,
            "executive_summary": "Good contract.",
            "findings": {"critical": [], "moderate": [], "minor": []},
            "recommendations": [],
            "metadata": {"word_count": 1000, "contract_elements": {}},
            "note": "Automated.",
        }

        result = await internal_generate_contract_report(analysis_data=analysis_data, report_format="text")

        assert result["success"] is True
        assert result["report_format"] == "text"
        assert ".txt" in result["file_name"]

    @pytest.mark.asyncio
    async def test_returns_error_for_unsupported_format(self):
        from src.services.agents.internal_tools.contract_analysis_tools import internal_generate_contract_report

        analysis_data = {"success": True, "file_name": "test.txt"}

        result = await internal_generate_contract_report(analysis_data=analysis_data, report_format="pdf")

        assert "error" in result
        assert "Unsupported report format" in result["error"]
