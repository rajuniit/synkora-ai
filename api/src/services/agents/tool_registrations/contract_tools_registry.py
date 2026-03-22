"""
Contract Analysis Tools Registry

Registers all contract analysis tools with the ADK tool registry.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def register_contract_tools(registry):
    """
    Register all contract analysis tools with the ADK tool registry.

    Args:
        registry: ADKToolRegistry instance
    """
    from src.services.agents.internal_tools.contract_analysis_tools import (
        internal_analyze_contract,
        internal_generate_contract_report,
    )

    # Contract Analysis Tool - wrapper that injects runtime_context
    async def internal_analyze_contract_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_analyze_contract(
            file_path=kwargs.get("file_path"), analysis_type=kwargs.get("analysis_type", "comprehensive"), config=config
        )

    # Contract Report Generation Tool - wrapper that injects runtime_context
    async def internal_generate_contract_report_wrapper(config: dict[str, Any] | None = None, **kwargs):
        return await internal_generate_contract_report(
            analysis_data=kwargs.get("analysis_data"),
            report_format=kwargs.get("report_format", "markdown"),
            include_raw_findings=kwargs.get("include_raw_findings", True),
            config=config,
        )

    registry.register_tool(
        name="internal_analyze_contract",
        description="""Analyze a contract document for legal issues, risks, and concerns.

This tool performs comprehensive contract analysis to identify:
- Legal loopholes and vulnerabilities
- Unfavorable terms and clauses
- Missing protections and safeguards
- Risk areas and liabilities
- Ambiguous or unclear language
- Compliance and regulatory issues

The tool returns a detailed analysis with risk scoring, findings categorized by severity
(critical/moderate/minor), and actionable recommendations.

IMPORTANT: This tool requires the contract to be available as a readable file.
If the user uploads a contract, ensure you have the file path before calling this tool.
For attachments in chat, the file will be automatically downloaded and the path provided.""",
        parameters={
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the contract file (TXT, PDF, or DOCX). This should be the local file path where the contract has been saved or downloaded.",
                },
                "analysis_type": {
                    "type": "string",
                    "enum": ["comprehensive", "risk_assessment", "compliance", "financial", "quick"],
                    "description": """Type of analysis to perform:
- comprehensive: Full analysis with all sections (default) - best for general review
- risk_assessment: Focus on risks and liabilities - use when client is concerned about exposure
- compliance: Focus on legal compliance - use for regulatory review
- financial: Focus on payment and financial terms - use for cost analysis
- quick: Quick overview analysis - use for initial screening""",
                },
            },
            "required": ["file_path"],
        },
        function=internal_analyze_contract_wrapper,
    )

    registry.register_tool(
        name="internal_generate_contract_report",
        description="""Generate a formatted contract analysis report from analysis data.

This tool creates a professional, well-structured report that can be:
- Displayed in the chat for immediate review
- Saved to a file for download
- Shared with stakeholders

The report includes:
- Executive summary with risk assessment
- Detailed findings organized by severity
- Actionable recommendations
- Contract elements checklist
- Professional disclaimers

Supported formats:
- markdown: Best for chat display and general use
- html: For web viewing and sharing
- json: For programmatic access
- text: Plain text for simple viewing

USAGE: Call this tool AFTER analyzing a contract with internal_analyze_contract.
Pass the analysis_data returned from that tool to generate a formatted report.""",
        parameters={
            "type": "object",
            "properties": {
                "analysis_data": {
                    "type": "object",
                    "description": "The analysis data returned from internal_analyze_contract tool. This should be the complete analysis result object.",
                },
                "report_format": {
                    "type": "string",
                    "enum": ["markdown", "html", "json", "text"],
                    "description": "Format for the report. Use 'markdown' for chat display (default), 'html' for web viewing, 'json' for data export, or 'text' for plain text.",
                },
                "include_raw_findings": {
                    "type": "boolean",
                    "description": "Whether to include all detailed findings in the report. Set to false for a more concise summary. Defaults to true.",
                },
            },
            "required": ["analysis_data"],
        },
        function=internal_generate_contract_report_wrapper,
    )

    logger.info("Registered 2 contract analysis tools")
