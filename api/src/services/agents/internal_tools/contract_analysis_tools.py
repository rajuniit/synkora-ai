"""
Contract Analysis Tools for Synkora Agents.

Provides contract analysis capabilities including document parsing,
risk assessment, loophole detection, and report generation.
"""

import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


async def internal_analyze_contract(
    file_path: str, analysis_type: str = "comprehensive", config: dict[str, Any] | None = None
) -> dict[str, Any]:
    """
    Analyze a contract document for legal issues, risks, and concerns.

    This tool performs comprehensive contract analysis to identify:
    - Legal loopholes and vulnerabilities
    - Unfavorable terms and clauses
    - Missing protections and safeguards
    - Risk areas and liabilities
    - Ambiguous or unclear language
    - Compliance and regulatory issues

    Args:
        file_path: Path to the contract file (PDF, DOCX, or TXT)
        analysis_type: Type of analysis to perform:
            - "comprehensive": Full analysis with all sections (default)
            - "risk_assessment": Focus on risks and liabilities
            - "compliance": Focus on legal compliance
            - "financial": Focus on payment and financial terms
            - "quick": Quick overview analysis
        config: Optional configuration dictionary

    Returns:
        Dictionary containing:
        - success: Whether analysis was successful
        - file_name: Name of analyzed file
        - file_type: Type of file
        - analysis_type: Type of analysis performed
        - contract_type: Detected contract type
        - executive_summary: Brief summary of findings
        - risk_score: Overall risk score (0-100)
        - findings: Detailed findings organized by severity
        - recommendations: List of recommended actions
        - metadata: Analysis metadata
        - error: Error message (if any)
    """
    try:
        from src.services.agents.internal_tools.file_tools import internal_read_file

        logger.info(f"Starting contract analysis for: {file_path} (type: {analysis_type})")

        # Validate file path
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        file_name = path.name
        file_extension = path.suffix.lower()

        # Read file content using the unified read function
        contract_text = ""

        if file_extension not in [".txt", ".pdf", ".docx", ".doc"]:
            return {
                "success": False,
                "error": f"Unsupported file type: {file_extension}",
                "supported_types": [".txt", ".pdf", ".docx"],
            }

        result = await internal_read_file(file_path)
        if "error" in result:
            return result

        if result.get("file_type") == "text":
            contract_text = result.get("content", "")
        elif result.get("file_type") == "media":
            # For PDF/DOCX, we'll extract text
            # Note: This is a placeholder - in production, you'd use libraries like
            # PyPDF2, pdfplumber for PDF or python-docx for DOCX
            return {
                "error": f"Cannot analyze {file_extension} files yet. Please convert to TXT format or use the LLM's vision capabilities for PDF analysis.",
                "suggestion": "Upload a text version of the contract or ask me to read it using vision tools.",
            }

        if not contract_text or len(contract_text.strip()) < 100:
            return {"success": False, "error": "Contract text is too short or empty. Please provide a valid contract."}

        # Detect contract type based on keywords
        contract_type = _detect_contract_type(contract_text)

        # Prepare analysis structure
        analysis_sections = {
            "comprehensive": [
                "parties_and_definitions",
                "obligations_and_responsibilities",
                "payment_terms",
                "liability_and_indemnification",
                "termination_clauses",
                "dispute_resolution",
                "compliance_and_regulatory",
                "intellectual_property",
                "confidentiality",
                "general_provisions",
            ],
            "risk_assessment": [
                "liability_and_indemnification",
                "termination_clauses",
                "payment_terms",
                "obligations_and_responsibilities",
            ],
            "compliance": ["compliance_and_regulatory", "data_protection", "liability_and_indemnification"],
            "financial": ["payment_terms", "pricing_structure", "penalties_and_fees", "termination_costs"],
            "quick": ["key_obligations", "major_risks", "critical_dates"],
        }

        sections_to_analyze = analysis_sections.get(analysis_type, analysis_sections["comprehensive"])

        # Extract key contract elements
        contract_elements = _extract_contract_elements(contract_text)

        # Perform initial analysis
        findings = {
            "critical": [],  # High risk - immediate attention required
            "moderate": [],  # Medium risk - should be addressed
            "minor": [],  # Low risk - for awareness
            "positive": [],  # Favorable terms
        }

        # Analyze for common issues
        issues = _analyze_common_issues(contract_text, contract_elements)
        findings["critical"].extend(issues["critical"])
        findings["moderate"].extend(issues["moderate"])
        findings["minor"].extend(issues["minor"])

        # Calculate risk score (0-100, higher is riskier)
        risk_score = _calculate_risk_score(findings)

        # Generate executive summary
        executive_summary = _generate_executive_summary(contract_type, risk_score, findings, analysis_type)

        # Generate recommendations
        recommendations = _generate_recommendations(findings, risk_score)

        # Prepare metadata
        metadata = {
            "analyzed_at": datetime.now(UTC).isoformat(),
            "word_count": len(contract_text.split()),
            "sections_analyzed": sections_to_analyze,
            "contract_elements": contract_elements,
        }

        return {
            "success": True,
            "file_name": file_name,
            "file_type": file_extension,
            "analysis_type": analysis_type,
            "contract_type": contract_type,
            "executive_summary": executive_summary,
            "risk_score": risk_score,
            "findings": findings,
            "recommendations": recommendations,
            "metadata": metadata,
            "raw_text_length": len(contract_text),
            "note": "This is an automated analysis. Always consult with a qualified attorney for legal advice.",
        }

    except Exception as e:
        logger.error(f"Error analyzing contract {file_path}: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to analyze contract: {str(e)}"}


async def internal_generate_contract_report(
    analysis_data: dict[str, Any],
    report_format: str = "markdown",
    include_raw_findings: bool = True,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Generate a formatted contract analysis report.

    Creates a professional, well-structured report from contract analysis data
    that can be saved, downloaded, or shared.

    Args:
        analysis_data: Analysis data from internal_analyze_contract
        report_format: Format for the report:
            - "markdown": Markdown format (default)
            - "html": HTML format
            - "json": Structured JSON
            - "text": Plain text
        include_raw_findings: Whether to include all detailed findings
        config: Optional configuration dictionary

    Returns:
        Dictionary containing:
        - success: Whether report generation was successful
        - report_content: The formatted report content
        - report_format: Format of the report
        - file_name: Suggested filename for the report
        - metadata: Report metadata
        - error: Error message (if any)
    """
    try:
        if not analysis_data or "error" in analysis_data:
            return {"success": False, "error": "Invalid analysis data provided"}

        logger.info(f"Generating contract report in {report_format} format")

        # Generate report based on format
        if report_format == "markdown":
            report_content = _generate_markdown_report(analysis_data, include_raw_findings)
            file_extension = "md"
        elif report_format == "html":
            report_content = _generate_html_report(analysis_data, include_raw_findings)
            file_extension = "html"
        elif report_format == "json":
            import json

            report_content = json.dumps(analysis_data, indent=2)
            file_extension = "json"
        elif report_format == "text":
            report_content = _generate_text_report(analysis_data, include_raw_findings)
            file_extension = "txt"
        else:
            return {"success": False, "error": f"Unsupported report format: {report_format}"}

        # Generate filename
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        file_name = analysis_data.get("file_name", "contract")
        base_name = Path(file_name).stem
        suggested_filename = f"contract_analysis_{base_name}_{timestamp}.{file_extension}"

        # Prepare metadata
        metadata = {
            "generated_at": datetime.now(UTC).isoformat(),
            "original_file": analysis_data.get("file_name"),
            "analysis_type": analysis_data.get("analysis_type"),
            "risk_score": analysis_data.get("risk_score"),
            "report_format": report_format,
        }

        return {
            "success": True,
            "report_content": report_content,
            "report_format": report_format,
            "file_name": suggested_filename,
            "metadata": metadata,
            "content_length": len(report_content),
        }

    except Exception as e:
        logger.error(f"Error generating contract report: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to generate report: {str(e)}"}


# Helper functions


def _detect_contract_type(text: str) -> str:
    """Detect the type of contract based on keywords."""
    text_lower = text.lower()

    contract_keywords = {
        "employment": ["employment", "employee", "employer", "salary", "position", "duties"],
        "service": ["services", "service provider", "deliverables", "scope of work"],
        "nda": ["non-disclosure", "confidential information", "proprietary", "trade secrets"],
        "sales": ["purchase", "buyer", "seller", "goods", "price", "delivery"],
        "lease": ["lease", "lessor", "lessee", "rent", "premises", "tenant"],
        "partnership": ["partner", "partnership", "profit sharing", "capital contribution"],
        "license": ["license", "licensor", "licensee", "intellectual property", "royalty"],
        "consulting": ["consultant", "consulting", "professional services", "hourly rate"],
    }

    scores = {}
    for contract_type, keywords in contract_keywords.items():
        score = sum(1 for keyword in keywords if keyword in text_lower)
        scores[contract_type] = score

    if scores:
        detected_type = max(scores, key=scores.get)
        if scores[detected_type] > 0:
            return detected_type.title() + " Agreement"

    return "General Contract"


def _extract_contract_elements(text: str) -> dict[str, Any]:
    """Extract key elements from contract text."""
    elements = {
        "has_parties": False,
        "has_effective_date": False,
        "has_termination_clause": False,
        "has_governing_law": False,
        "has_dispute_resolution": False,
        "has_liability_cap": False,
        "has_indemnification": False,
        "has_confidentiality": False,
    }

    text_lower = text.lower()

    # Check for key elements
    if any(term in text_lower for term in ["party", "parties", "between"]):
        elements["has_parties"] = True

    if any(term in text_lower for term in ["effective date", "commencement date", "start date"]):
        elements["has_effective_date"] = True

    if any(term in text_lower for term in ["termination", "terminate", "cancellation"]):
        elements["has_termination_clause"] = True

    if any(term in text_lower for term in ["governing law", "jurisdiction", "shall be governed"]):
        elements["has_governing_law"] = True

    if any(term in text_lower for term in ["arbitration", "mediation", "dispute resolution"]):
        elements["has_dispute_resolution"] = True

    if any(term in text_lower for term in ["liability cap", "limitation of liability", "maximum liability"]):
        elements["has_liability_cap"] = True

    if any(term in text_lower for term in ["indemnify", "indemnification", "hold harmless"]):
        elements["has_indemnification"] = True

    if any(term in text_lower for term in ["confidential", "proprietary", "non-disclosure"]):
        elements["has_confidentiality"] = True

    return elements


def _analyze_common_issues(text: str, elements: dict[str, Any]) -> dict[str, list]:
    """Analyze contract for common issues and red flags."""
    issues = {"critical": [], "moderate": [], "minor": []}

    text_lower = text.lower()

    # Critical issues
    if not elements["has_termination_clause"]:
        issues["critical"].append(
            {
                "issue": "Missing Termination Clause",
                "description": "No clear termination provisions found. This makes it difficult to exit the agreement.",
                "recommendation": "Add explicit termination clause with notice periods and conditions.",
            }
        )

    if not elements["has_governing_law"]:
        issues["critical"].append(
            {
                "issue": "No Governing Law Specified",
                "description": "Contract doesn't specify which jurisdiction's laws apply.",
                "recommendation": "Specify governing law and jurisdiction for legal certainty.",
            }
        )

    # Check for one-sided liability
    if "liable" in text_lower and "not liable" in text_lower:
        if text_lower.count("not liable") > text_lower.count("shall be liable"):
            issues["critical"].append(
                {
                    "issue": "One-Sided Liability Limitations",
                    "description": "Contract appears to heavily limit one party's liability while not protecting the other.",
                    "recommendation": "Negotiate for balanced liability provisions.",
                }
            )

    # Moderate issues
    if not elements["has_dispute_resolution"]:
        issues["moderate"].append(
            {
                "issue": "No Dispute Resolution Mechanism",
                "description": "No arbitration or mediation clause found.",
                "recommendation": "Consider adding arbitration or mediation clause to avoid costly litigation.",
            }
        )

    if not elements["has_liability_cap"]:
        issues["moderate"].append(
            {
                "issue": "Unlimited Liability Exposure",
                "description": "No limitation on liability amount found.",
                "recommendation": "Consider negotiating a liability cap to limit financial exposure.",
            }
        )

    # Check for automatic renewal
    if any(term in text_lower for term in ["automatic renewal", "auto-renew", "automatically renew"]):
        issues["moderate"].append(
            {
                "issue": "Automatic Renewal Clause",
                "description": "Contract may automatically renew without explicit consent.",
                "recommendation": "Review renewal terms and ensure adequate notice period for non-renewal.",
            }
        )

    # Minor issues
    if not elements["has_confidentiality"]:
        issues["minor"].append(
            {
                "issue": "No Confidentiality Clause",
                "description": "No explicit confidentiality provisions found.",
                "recommendation": "Consider adding confidentiality clause if sensitive information is involved.",
            }
        )

    # Check for ambiguous terms
    ambiguous_terms = ["reasonable", "best efforts", "as soon as possible", "timely manner"]
    found_ambiguous = [term for term in ambiguous_terms if term in text_lower]
    if found_ambiguous:
        issues["minor"].append(
            {
                "issue": "Ambiguous Language Detected",
                "description": f"Contract contains potentially ambiguous terms: {', '.join(found_ambiguous)}",
                "recommendation": "Define specific timelines, standards, or metrics for these terms.",
            }
        )

    return issues


def _calculate_risk_score(findings: dict[str, list]) -> int:
    """Calculate overall risk score based on findings."""
    # Weight different severity levels
    critical_weight = 30
    moderate_weight = 15
    minor_weight = 5

    critical_count = len(findings.get("critical", []))
    moderate_count = len(findings.get("moderate", []))
    minor_count = len(findings.get("minor", []))

    # Calculate raw score
    raw_score = critical_count * critical_weight + moderate_count * moderate_weight + minor_count * minor_weight

    # Cap at 100
    risk_score = min(100, raw_score)

    return risk_score


def _generate_executive_summary(
    contract_type: str, risk_score: int, findings: dict[str, list], analysis_type: str
) -> str:
    """Generate executive summary of the analysis."""
    critical_count = len(findings.get("critical", []))
    moderate_count = len(findings.get("moderate", []))
    minor_count = len(findings.get("minor", []))

    # Determine risk level
    if risk_score >= 70:
        risk_level = "HIGH RISK"
        risk_description = "This contract contains significant issues that require immediate attention."
    elif risk_score >= 40:
        risk_level = "MODERATE RISK"
        risk_description = "This contract has several concerns that should be addressed before signing."
    else:
        risk_level = "LOW RISK"
        risk_description = "This contract appears relatively standard with minor issues."

    summary = f"""
**Contract Type:** {contract_type}
**Analysis Type:** {analysis_type.replace("_", " ").title()}
**Overall Risk Level:** {risk_level} (Score: {risk_score}/100)

{risk_description}

**Issues Identified:**
- 🚨 Critical Issues: {critical_count}
- ⚠️ Moderate Concerns: {moderate_count}
- ℹ️ Minor Points: {minor_count}

**Key Recommendation:** {_get_key_recommendation(risk_score, critical_count)}
    """.strip()

    return summary


def _get_key_recommendation(risk_score: int, critical_count: int) -> str:
    """Get key recommendation based on risk assessment."""
    if critical_count > 0:
        return (
            "Do not sign this contract without addressing the critical issues. Consult with legal counsel immediately."
        )
    elif risk_score >= 40:
        return "Review the moderate concerns carefully and negotiate changes where possible before signing."
    else:
        return "Contract appears acceptable, but review the minor points for completeness."


def _generate_recommendations(findings: dict[str, list], risk_score: int) -> list[str]:
    """Generate list of actionable recommendations."""
    recommendations = []

    # Add priority recommendations based on critical issues
    critical_issues = findings.get("critical", [])
    for issue in critical_issues[:3]:  # Top 3 critical issues
        recommendations.append(f"URGENT: {issue['recommendation']}")

    # Add general recommendations
    if risk_score >= 70:
        recommendations.extend(
            [
                "Engage a qualified attorney to review this contract before signing",
                "Prepare a list of required amendments and negotiate with the other party",
                "Consider walking away if critical issues cannot be resolved",
            ]
        )
    elif risk_score >= 40:
        recommendations.extend(
            [
                "Consult with legal counsel to address moderate concerns",
                "Negotiate key terms that pose significant risk",
                "Ensure all ambiguous terms are clarified before signing",
            ]
        )
    else:
        recommendations.extend(
            [
                "Review minor points for completeness",
                "Clarify any ambiguous terms if possible",
                "Keep a signed copy for your records",
            ]
        )

    # Add specific recommendations from moderate issues
    moderate_issues = findings.get("moderate", [])
    for issue in moderate_issues[:2]:  # Top 2 moderate issues
        recommendations.append(issue["recommendation"])

    return recommendations


def _generate_markdown_report(analysis_data: dict[str, Any], include_raw_findings: bool) -> str:
    """Generate a markdown formatted report."""
    findings = analysis_data.get("findings", {})

    report = f"""# Contract Analysis Report

Generated: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")}

---

## Executive Summary

{analysis_data.get("executive_summary", "No summary available")}

---

## Analysis Details

- **File Name:** {analysis_data.get("file_name", "N/A")}
- **Contract Type:** {analysis_data.get("contract_type", "Unknown")}
- **Analysis Type:** {analysis_data.get("analysis_type", "comprehensive").replace("_", " ").title()}
- **Risk Score:** {analysis_data.get("risk_score", 0)}/100
- **Word Count:** {analysis_data.get("metadata", {}).get("word_count", "N/A")}

---

## Findings

"""

    # Critical issues
    critical = findings.get("critical", [])
    if critical:
        report += "\n### 🚨 Critical Issues (High Risk)\n\n"
        report += (
            "These issues require immediate attention and may significantly impact your rights or obligations.\n\n"
        )
        for i, issue in enumerate(critical, 1):
            report += f"#### {i}. {issue['issue']}\n\n"
            report += f"**Concern:** {issue['description']}\n\n"
            report += f"**Recommendation:** {issue['recommendation']}\n\n"
            report += "---\n\n"

    # Moderate concerns
    moderate = findings.get("moderate", [])
    if moderate:
        report += "\n### ⚠️ Moderate Concerns (Medium Risk)\n\n"
        report += "These issues should be addressed to reduce risk and improve contract terms.\n\n"
        for i, issue in enumerate(moderate, 1):
            report += f"#### {i}. {issue['issue']}\n\n"
            report += f"**Concern:** {issue['description']}\n\n"
            report += f"**Recommendation:** {issue['recommendation']}\n\n"
            report += "---\n\n"

    # Minor points
    minor = findings.get("minor", [])
    if minor:
        report += "\n### ℹ️ Minor Points (Low Risk)\n\n"
        report += "These are minor points for your awareness.\n\n"
        for i, issue in enumerate(minor, 1):
            report += f"#### {i}. {issue['issue']}\n\n"
            report += f"**Note:** {issue['description']}\n\n"
            report += f"**Suggestion:** {issue['recommendation']}\n\n"
            report += "---\n\n"

    # Recommendations
    report += "\n## Recommendations\n\n"
    recommendations = analysis_data.get("recommendations", [])
    if recommendations:
        for i, rec in enumerate(recommendations, 1):
            report += f"{i}. {rec}\n"
    else:
        report += "No specific recommendations at this time.\n"

    # Contract elements check
    elements = analysis_data.get("metadata", {}).get("contract_elements", {})
    if elements:
        report += "\n---\n\n## Contract Elements Checklist\n\n"
        report += "| Element | Present |\n"
        report += "|---------|--------|\n"
        for element, present in elements.items():
            element_name = element.replace("has_", "").replace("_", " ").title()
            status = "✅ Yes" if present else "❌ No"
            report += f"| {element_name} | {status} |\n"

    # Disclaimer
    report += "\n---\n\n## Important Disclaimer\n\n"
    report += f"⚠️ **{analysis_data.get('note', 'This is an automated analysis.')}**\n\n"
    report += "This analysis is provided for informational purposes only and does not constitute legal advice. "
    report += "Always consult with a qualified attorney before entering into any legal agreement.\n"

    return report


def _generate_html_report(analysis_data: dict[str, Any], include_raw_findings: bool) -> str:
    """Generate an HTML formatted report."""
    # Convert markdown to HTML with basic styling
    md_report = _generate_markdown_report(analysis_data, include_raw_findings)

    # Get values outside of f-string to avoid backslash issues
    risk_color = _get_risk_color(analysis_data.get("risk_score", 0))
    generated_time = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    executive_summary = analysis_data.get("executive_summary", "No summary available").replace("\n", "<br>")
    risk_score = analysis_data.get("risk_score", 0)
    note = analysis_data.get("note", "This is an automated analysis.")

    # Simple markdown to HTML conversion
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Contract Analysis Report</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}
        .container {{
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
        }}
        h3 {{
            color: #555;
        }}
        .critical {{
            background: #fee;
            border-left: 4px solid #e74c3c;
            padding: 15px;
            margin: 15px 0;
        }}
        .moderate {{
            background: #fef9e7;
            border-left: 4px solid #f39c12;
            padding: 15px;
            margin: 15px 0;
        }}
        .minor {{
            background: #eef;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 15px 0;
        }}
        .risk-score {{
            font-size: 24px;
            font-weight: bold;
            color: {risk_color};
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #3498db;
            color: white;
        }}
        .disclaimer {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            margin-top: 30px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Contract Analysis Report</h1>
        <p><strong>Generated:</strong> {generated_time}</p>

        <h2>Executive Summary</h2>
        <p>{executive_summary}</p>

        <p class="risk-score">Risk Score: {risk_score}/100</p>

        <!-- Rest of the report would be generated here -->
        <pre>{md_report}</pre>

        <div class="disclaimer">
            <strong>⚠️ Important Disclaimer</strong><br>
            {note}
        </div>
    </div>
</body>
</html>"""

    return html


def _generate_text_report(analysis_data: dict[str, Any], include_raw_findings: bool) -> str:
    """Generate a plain text formatted report."""
    # Convert markdown to plain text
    md_report = _generate_markdown_report(analysis_data, include_raw_findings)

    # Remove markdown formatting
    text_report = md_report.replace("#", "").replace("**", "").replace("*", "")
    text_report = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text_report)  # Remove links
    text_report = re.sub(r"---+", "=" * 80, text_report)  # Replace horizontal rules

    return text_report


def _get_risk_color(risk_score: int) -> str:
    """Get color code based on risk score."""
    if risk_score >= 70:
        return "#e74c3c"  # Red
    elif risk_score >= 40:
        return "#f39c12"  # Orange
    else:
        return "#27ae60"  # Green
