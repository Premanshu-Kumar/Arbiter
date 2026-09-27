"""
Jev Planner Agent - Uses Jev decision engine to plan analysis strategy
"""
from typing import Dict, Any
from decision.jev_client import JevClient
import config


class JevPlanner:
    """Plans analysis strategy using Jev decision engine"""
    
    def __init__(self):
        self.jev_client = JevClient()
    
    def plan_analysis(
        self,
        question: str,
        schema: str,
        data_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Plan the analysis approach for a given question
        
        Args:
            question: User's natural language question
            schema: Data schema information
            data_profile: Detailed data profile with statistics
        
        Returns:
            Analysis plan with method, visualization, and confidence
        """
        context = {
            "question": question,
            "schema": schema,
            "row_count": data_profile.get("row_count", 0),
            "column_count": data_profile.get("column_count", 0),
            "data_types": data_profile.get("data_types", {}),
            "missing_values": data_profile.get("missing_values", {})
        }
        
        # Use Jev to make routing decision
        decision_result = self.jev_client.make_decision(context, "routing")
        
        # Enhance the decision with analysis-specific details
        analysis_plan = self._enhance_plan(decision_result, question, data_profile)
        
        return analysis_plan
    
    def _enhance_plan(
        self,
        decision_result: Dict[str, Any],
        question: str,
        data_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Enhance the basic decision with analysis-specific details"""
        plan = {
            "decision": decision_result.get("decision", {}),
            "confidence": decision_result.get("confidence", 0.5),
            "reasoning": decision_result.get("reasoning", ""),
            "question": question
        }
        
        # Determine analysis method
        method = plan["decision"].get("method", "BOTH")
        plan["method"] = method
        
        # Determine if time series analysis is needed
        question_lower = question.lower()
        plan["requires_time_series"] = any(keyword in question_lower for keyword in [
            "trend", "over time", "month", "year", "date", "time", "daily", "weekly",
            "monthly", "quarterly", "annually", "historical", "change"
        ])
        
        # Determine if aggregation is needed
        plan["requires_aggregation"] = any(keyword in question_lower for keyword in [
            "sum", "average", "mean", "count", "total", "aggregate", "group by",
            "per", "each", "by", "top", "bottom", "highest", "lowest"
        ])
        
        # Determine if filtering is needed
        plan["requires_filtering"] = any(keyword in question_lower for keyword in [
            "where", "when", "only", "specific", "during", "between", "after", "before",
            "greater than", "less than", "equal to", "contains"
        ])
        
        # Determine if sorting is needed
        plan["requires_sorting"] = any(keyword in question_lower for keyword in [
            "top", "bottom", "highest", "lowest", "first", "last", "most", "least",
            "order by", "sort", "rank", "largest", "smallest"
        ])
        
        # Determine visualization type
        plan["visualization"] = self._determine_visualization(question, method)
        
        # Set validation requirement
        plan["validation"] = True
        
        return plan
    
    def _determine_visualization(self, question: str, method: str) -> str:
        """Determine appropriate visualization type based on question"""
        question_lower = question.lower()
        
        # Time series trends
        if any(keyword in question_lower for keyword in [
            "trend", "over time", "change", "growth", "decline", "pattern"
        ]):
            return "line_chart"
        
        # Comparisons between categories
        if any(keyword in question_lower for keyword in [
            "compare", "vs", "versus", "difference", "between", "top", "bottom"
        ]):
            return "bar_chart"
        
        # Distributions
        if any(keyword in question_lower for keyword in [
            "distribution", "spread", "range", "histogram", "frequency"
        ]):
            return "histogram"
        
        # Relationships/correlations
        if any(keyword in question_lower for keyword in [
            "relationship", "correlation", "between", "vs", "scatter"
        ]):
            return "scatter_plot"
        
        # Part-to-whole
        if any(keyword in question_lower for keyword in [
            "proportion", "percentage", "share", "composition", "breakdown"
        ]):
            return "pie_chart"
        
        # Default based on method
        if method == "SQL":
            return "bar_chart"
        else:
            return "table"
    
    def suggest_grouping(self, question: str, schema: str) -> list:
        """Suggest appropriate grouping columns based on question and schema"""
        question_lower = question.lower()
        
        # Extract potential grouping keywords
        grouping_keywords = {
            "category": ["category", "type", "kind", "class", "group"],
            "time": ["month", "year", "date", "time", "day", "week", "quarter"],
            "location": ["region", "city", "country", "state", "area"],
            "product": ["product", "item", "sku", "name"]
        }
        
        suggested_groups = []
        
        for group_type, keywords in grouping_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                suggested_groups.append(group_type)
        
        return suggested_groups
    
    def estimate_complexity(self, plan: Dict[str, Any]) -> str:
        """Estimate the complexity of the analysis plan"""
        complexity_score = 0
        
        if plan["requires_time_series"]:
            complexity_score += 2
        if plan["requires_aggregation"]:
            complexity_score += 1
        if plan["requires_filtering"]:
            complexity_score += 1
        if plan["requires_sorting"]:
            complexity_score += 1
        
        if plan["method"] == "BOTH":
            complexity_score += 2
        
        if complexity_score <= 2:
            return "simple"
        elif complexity_score <= 4:
            return "moderate"
        else:
            return "complex"
