"""
Report Agent - Generates AI-powered analytical reports
"""
from typing import Dict, Any
from agents.ollama_client import OllamaClient
import config
import os
from datetime import datetime
import pandas as pd


class ReportAgent:
    """Generates comprehensive analytical reports"""
    
    def __init__(self):
        self.ollama_client = OllamaClient()
    
    def generate_report(
        self,
        question: str,
        plan: Dict[str, Any],
        result: Any,
        error: str = None,
        execution_details: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive report
        
        Args:
            question: Original user question
            plan: Analysis plan used
            result: Analysis results
            error: Error message if execution failed
            execution_details: Details about code execution
        
        Returns:
            Generated report with metadata
        """
        try:
            # Generate different sections of the report
            executive_summary = self._generate_executive_summary(question, plan, result, error)
            key_insights = self._generate_key_insights(question, plan, result, error)
            methodology = self._generate_methodology(plan, execution_details)
            validation_status = self._generate_validation_status(error, execution_details)
            
            # Combine into full report
            full_report = self._combine_report_sections(
                executive_summary,
                key_insights,
                methodology,
                validation_status,
                question,
                plan
            )
            
            return {
                "success": True,
                "report": full_report,
                "executive_summary": executive_summary,
                "key_insights": key_insights,
                "methodology": methodology,
                "validation_status": validation_status,
                "reasoning": "Report generated successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "reasoning": f"Report generation failed: {str(e)}"
            }
    
    def _generate_executive_summary(
        self,
        question: str,
        plan: Dict[str, Any],
        result: Any,
        error: str
    ) -> str:
        """Generate executive summary of the analysis"""
        if error:
            return f"Analysis failed to complete. The system encountered an error while attempting to answer: '{question}'. Error: {error}"
        
        prompt = f"""Generate a concise executive summary (2-3 sentences) for this data analysis:
Question: {question}
Analysis Method: {plan.get('method', 'Unknown')}
Confidence: {plan.get('confidence', 0.5)}

Provide a brief summary of what was analyzed and the key takeaway.
"""
        
        try:
            summary = self.ollama_client.generate(
                prompt=prompt,
                model=config.REASONING_MODEL,
                max_tokens=200
            )
            return summary
        except Exception as e:
            return f"Analysis completed using {plan.get('method', 'unknown')} method to answer: {question}"
    
    def _generate_key_insights(
        self,
        question: str,
        plan: Dict[str, Any],
        result: Any,
        error: str
    ) -> list:
        """Generate key insights from the analysis"""
        if error:
            return ["Analysis failed due to execution error", "No insights could be generated"]
        
        # For DataFrame results, extract insights directly
        if isinstance(result, pd.DataFrame):
            insights = []
            
            # Check if it's a grouped/aggregated result
            if len(result.columns) >= 2:
                # Try to find the highest value
                numeric_cols = result.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    agg_col = numeric_cols[0]
                    cat_cols = [col for col in result.columns if col not in numeric_cols]
                    
                    if len(cat_cols) > 0:
                        cat_col = cat_cols[0]
                        max_idx = result[agg_col].idxmax()
                        max_cat = result.loc[max_idx, cat_col]
                        max_val = result.loc[max_idx, agg_col]
                        
                        insights.append(f"Highest value: {max_cat} with {max_val:.2f}")
                        
                        # Add total rows insight
                        insights.append(f"Total categories analyzed: {len(result)}")
                        
                        # Add range insight
                        min_val = result[agg_col].min()
                        insights.append(f"Value range: {min_val:.2f} to {max_val:.2f}")
                        
                        return insights
        
        # Fallback to LLM-based insights
        prompt = f"""Generate 3-5 key insights from this data analysis:
Question: {question}
Analysis Method: {plan.get('method', 'Unknown')}
Visualization Type: {plan.get('visualization', 'Unknown')}

Provide insights as a numbered list, focusing on actionable findings.
"""
        
        try:
            insights_text = self.ollama_client.generate(
                prompt=prompt,
                model=config.REASONING_MODEL,
                max_tokens=400
            )
            
            # Parse into list
            insights = []
            for line in insights_text.split('\n'):
                line = line.strip()
                if line is not None and line != "" and (line[0].isdigit() or line.startswith('-')):
                    insights.append(line)
            
            return insights if insights else ["Analysis completed successfully"]
            
        except Exception as e:
            return ["Analysis completed using " + plan.get('method', 'unknown') + " method"]
    
    def _generate_methodology(
        self,
        plan: Dict[str, Any],
        execution_details: Dict[str, Any] = None
    ) -> str:
        """Generate methodology section"""
        methodology_parts = [
            f"Analysis Method: {plan.get('method', 'Unknown')}",
            f"Confidence Score: {plan.get('confidence', 0.5):.2f}",
            f"Visualization: {plan.get('visualization', 'None')}",
        ]
        
        if plan.get('requires_aggregation'):
            methodology_parts.append("Data Aggregation: Applied")
        if plan.get('requires_filtering'):
            methodology_parts.append("Data Filtering: Applied")
        if plan.get('requires_time_series'):
            methodology_parts.append("Time Series Analysis: Applied")
        if plan.get('requires_sorting'):
            methodology_parts.append("Data Sorting: Applied")
        
        if execution_details:
            if execution_details.get('code_type'):
                methodology_parts.append(f"Code Type: {execution_details['code_type']}")
            if execution_details.get('execution_time'):
                methodology_parts.append(f"Execution Time: {execution_details['execution_time']:.2f}s")
        
        return "\n".join(methodology_parts)
    
    def _generate_validation_status(
        self,
        error: str,
        execution_details: Dict[str, Any] = None
    ) -> str:
        """Generate validation status section"""
        if error:
            return f"Status: FAILED\nError: {error}\nValidation: Execution error detected"
        
        validation_parts = ["Status: SUCCESS"]
        
        if execution_details:
            if execution_details.get('retry_count', 0) > 0:
                validation_parts.append(f"Retries Required: {execution_details['retry_count']}")
            else:
                validation_parts.append("Retries Required: 0")
            
            if execution_details.get('validated'):
                validation_parts.append("Result Validation: PASSED")
            else:
                validation_parts.append("Result Validation: SKIPPED")
        
        return "\n".join(validation_parts)
    
    def _combine_report_sections(
        self,
        executive_summary: str,
        key_insights: list,
        methodology: str,
        validation_status: str,
        question: str,
        plan: Dict[str, Any]
    ) -> str:
        """Combine all sections into a full report"""
        report_lines = [
            "# Data Analysis Report",
            f"\n**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Question:** {question}",
            f"**Analysis Method:** {plan.get('method', 'Unknown')}",
            "",
            "## Executive Summary",
            executive_summary,
            "",
            "## Key Insights",
        ]
        
        for insight in key_insights:
            report_lines.append(f"- {insight}")
        
        report_lines.extend([
            "",
            "## Methodology",
            methodology,
            "",
            "## Validation Status",
            validation_status,
            "",
            "---",
            "*Generated by Multi-Agent Data Analyst*"
        ])
        
        return "\n".join(report_lines)
    
    def format_as_html(self, report: str) -> str:
        """Convert markdown report to HTML"""
        # Simple markdown to HTML conversion
        html = report
        
        # Headers
        html = html.replace('# ', '<h1>').replace('\n', '</h1>\n', 1)
        html = html.replace('## ', '<h2>').replace('\n', '</h2>\n', 1)
        html = html.replace('### ', '<h3>').replace('\n', '</h3>\n', 1)
        
        # Bold
        html = html.replace('**', '<strong>')
        html = html.replace('</strong>', '</strong>')
        
        # Lists
        lines = html.split('\n')
        in_list = False
        html_lines = []
        
        for line in lines:
            if line.strip().startswith('- '):
                if not in_list:
                    html_lines.append('<ul>')
                    in_list = True
                html_lines.append(f'<li>{line.strip()[2:]}</li>')
            else:
                if in_list:
                    html_lines.append('</ul>')
                    in_list = False
                html_lines.append(line)
        
        if in_list:
            html_lines.append('</ul>')
        
        html = '\n'.join(html_lines)
        
        # Paragraphs
        html = html.replace('\n\n', '</p>\n<p>')
        html = f'<p>{html}</p>'
        
        return html
    
    def save_report(
        self,
        report: str,
        format: str = "markdown",
        filename: str = None
    ) -> str:
        """Save report to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"report_{timestamp}.{format}"
        
        filepath = os.path.join(config.REPORTS_DIR, filename)
        
        try:
            if format == "markdown":
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(report)
            elif format == "html":
                html_content = self.format_as_html(report)
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(html_content)
            else:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(report)
            
            return filepath
            
        except Exception as e:
            print(f"Error saving report: {str(e)}")
            return ""
    
    def generate_explanation(
        self,
        question: str,
        result: Any,
        code: str,
        code_type: str
    ) -> str:
        """Generate a natural language explanation of the analysis"""
        prompt = f"""Explain this data analysis in simple terms:
Question: {question}
Code Type: {code_type}
Code: {code[:500]}...

Provide a clear explanation of what the analysis does and what the results mean.
"""
        
        try:
            explanation = self.ollama_client.generate(
                prompt=prompt,
                model=config.REASONING_MODEL,
                max_tokens=500
            )
            return explanation
        except Exception as e:
            return f"Analysis completed using {code_type} to answer the question."
