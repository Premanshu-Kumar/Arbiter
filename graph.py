"""
LangGraph Workflow - Multi-agent orchestration for data analysis

Phase 5: Adds cross-validation node, self-healing retry loop, and
comprehensive validation routing.
Phase 7: Adds performance recording integration.
"""
from typing import TypedDict, Any, Optional, Literal
from langgraph.graph import StateGraph, END
import pandas as pd
from state import AnalystState
from agents.jev_planner import JevPlanner
from agents.sql_agent import SQLAgent
from agents.python_agent import PythonAgent
from agents.viz_agent import VizAgent
from agents.report_agent import ReportAgent
from agents.jev_validator import JevValidator
from agents.cross_validator import CrossValidator
from agents.self_healer import SelfHealer
from decision.validation_policies import ValidationPolicyEngine
from sandbox.executor import SafeExecutor
from eval.performance_dashboard import ModelPerformanceDashboard, PerformanceTimer
import config
import time


class AnalystWorkflow:
    """LangGraph workflow for multi-agent data analysis"""
    
    def __init__(self):
        self.planner = JevPlanner()
        self.sql_agent = SQLAgent()
        self.python_agent = PythonAgent()
        self.viz_agent = VizAgent()
        self.report_agent = ReportAgent()
        self.validator = JevValidator()
        self.cross_validator = CrossValidator()
        self.self_healer = SelfHealer()
        self.policy = ValidationPolicyEngine()
        self.executor = SafeExecutor()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AnalystState)
        
        # Add nodes
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("sql_agent", self._sql_agent_node)
        workflow.add_node("python_agent", self._python_agent_node)
        workflow.add_node("self_heal", self._self_heal_node)
        workflow.add_node("validator", self._validator_node)
        workflow.add_node("cross_check", self._cross_check_node)
        workflow.add_node("visualization", self._visualization_node)
        workflow.add_node("report", self._report_node)
        
        # Set entry point
        workflow.set_entry_point("planner")
        
        # Planner → agent routing
        workflow.add_conditional_edges(
            "planner",
            self._route_to_agent,
            {
                "sql": "sql_agent",
                "python": "python_agent",
                "both": "sql_agent",  # Start with SQL for both
                "error": END
            }
        )
        
        # After SQL agent
        workflow.add_conditional_edges(
            "sql_agent",
            self._route_after_execution,
            {
                "validator": "validator",
                "self_heal": "self_heal",
                "python": "python_agent",  # Fallback to Python
                "error": END
            }
        )
        
        # After Python agent
        workflow.add_conditional_edges(
            "python_agent",
            self._route_after_execution,
            {
                "validator": "validator",
                "self_heal": "self_heal",
                "error": END
            }
        )
        
        # After self-healing
        workflow.add_conditional_edges(
            "self_heal",
            self._route_after_heal,
            {
                "sql_agent": "sql_agent",
                "python_agent": "python_agent",
                "validator": "validator",
                "error": END
            }
        )
        
        # After validation
        workflow.add_conditional_edges(
            "validator",
            self._route_after_validation,
            {
                "cross_check": "cross_check",
                "visualization": "visualization",
                "retry": "planner",
                "self_heal": "self_heal",
                "error": END
            }
        )
        
        # After cross-check
        workflow.add_conditional_edges(
            "cross_check",
            self._route_after_cross_check,
            {
                "visualization": "visualization",
                "retry": "planner",
                "error": END
            }
        )
        
        workflow.add_edge("visualization", "report")
        workflow.add_edge("report", END)
        
        return workflow.compile()
    
    # ==================================================================
    #  Nodes
    # ==================================================================
    
    def _planner_node(self, state: AnalystState) -> AnalystState:
        """Jev Planner node - creates analysis plan"""
        print("🧠 Jev Planner: Creating analysis plan...")
        
        try:
            data_profile = {
                "row_count": state.get("row_count", 0),
                "column_count": state.get("column_count", 0),
                "data_types": state.get("data_types", {}),
                "missing_values": state.get("missing_values", {})
            }
            
            plan = self.planner.plan_analysis(
                question=state["question"],
                schema=state["schema"],
                data_profile=data_profile
            )
            
            state["decision"] = plan["decision"]
            state["confidence"] = plan["confidence"]
            state["selected_agent"] = plan["method"]
            
            print(f"   Plan: {plan['method']} with confidence {plan['confidence']:.2f}")
            print(f"   Visualization: {plan['visualization']}")
            
        except Exception as e:
            print(f"   Error in planner: {str(e)}")
            state["error"] = str(e)
            state["selected_agent"] = "error"
        
        return state
    
    def _sql_agent_node(self, state: AnalystState) -> AnalystState:
        """SQL Agent node - generates and executes SQL"""
        print("🤖 SQL Agent: Generating and executing SQL...")
        
        try:
            if state.get("df") is None:
                raise Exception("No DataFrame available in state")
            
            self.executor.setup_duckdb(state["df"], "data")
            
            plan = {
                "method": "SQL",
                "requires_aggregation": state["decision"].get("requires_aggregation", False),
                "requires_time_series": state["decision"].get("requires_time_series", False),
                "requires_filtering": state["decision"].get("requires_filtering", False),
                "requires_sorting": state["decision"].get("requires_sorting", False),
                "visualization": state["decision"].get("visualization", "table")
            }
            
            # Try Ollama, fall back to mock
            try:
                sql_result = self.sql_agent.generate_sql(
                    question=state["question"],
                    schema=state["schema"],
                    plan=plan
                )
                if sql_result.get("success") is False:
                    print("   Ollama unavailable, using mock SQL generation")
                    sql_result = self.sql_agent.generate_sql_mock(
                        question=state["question"],
                        schema=state["schema"],
                        plan=plan
                    )
            except Exception as e:
                print(f"   SQL generation error: {str(e)}, using mock")
                sql_result = self.sql_agent.generate_sql_mock(
                    question=state["question"],
                    schema=state["schema"],
                    plan=plan
                )
            
            if sql_result.get("success") is False:
                state["error"] = sql_result.get("error", "SQL generation failed")
                state["failed_agent"] = "SQL"
                return state
            
            if not sql_result.get("code"):
                state["error"] = "SQL generation returned empty code"
                state["failed_agent"] = "SQL"
                return state
            
            state["code"] = sql_result["code"]
            state["code_type"] = "sql"
            
            execution_result = self.executor.execute_sql(sql_result["code"])
            
            if execution_result.get("success") is True:
                state["result"] = execution_result["result"]
                state["error"] = None
                if isinstance(state["result"], pd.DataFrame):
                    print(f"   SQL executed successfully: {len(state['result'])} rows")
                else:
                    print("   SQL executed successfully")
            else:
                state["error"] = execution_result["error"]
                state["failed_agent"] = "SQL"
                print(f"   SQL execution failed: {execution_result['error']}")
            
        except Exception as e:
            import traceback
            print(f"   Error in SQL agent: {str(e)}")
            print(f"   Traceback: {traceback.format_exc()}")
            state["error"] = str(e)
            state["failed_agent"] = "SQL"
        
        return state
    
    def _python_agent_node(self, state: AnalystState) -> AnalystState:
        """Python Agent node - generates and executes Python"""
        print("🤖 Python Agent: Generating and executing Python...")
        
        try:
            plan = {
                "method": "Python",
                "requires_aggregation": state["decision"].get("requires_aggregation", False),
                "requires_time_series": state["decision"].get("requires_time_series", False),
                "requires_filtering": state["decision"].get("requires_filtering", False),
                "requires_sorting": state["decision"].get("requires_sorting", False),
                "visualization": state["decision"].get("visualization", "table")
            }
            
            try:
                python_result = self.python_agent.generate_python(
                    question=state["question"],
                    schema=state["schema"],
                    plan=plan
                )
                if not python_result["success"]:
                    print("   Ollama unavailable, using mock Python generation")
                    python_result = self.python_agent.generate_python_mock(
                        question=state["question"],
                        schema=state["schema"],
                        plan=plan
                    )
            except Exception as e:
                print(f"   Python generation error: {str(e)}, using mock")
                python_result = self.python_agent.generate_python_mock(
                    question=state["question"],
                    schema=state["schema"],
                    plan=plan
                )
            
            if python_result.get("success") is False:
                state["error"] = python_result.get("error", "Python generation failed")
                state["failed_agent"] = "Python"
                return state
            
            state["code"] = python_result["code"]
            state["code_type"] = "python"
            
            if state.get("df") is None:
                raise Exception("No DataFrame available in state")
            
            if not python_result.get("code"):
                state["error"] = python_result.get("error", "Code generation failed")
                state["failed_agent"] = "Python"
                return state
            
            execution_result = self.executor.execute_python(
                python_result["code"],
                state["df"]
            )
            
            if execution_result.get("success") is True:
                state["result"] = execution_result["result"]
                state["error"] = None
                print("   Python executed successfully")
            else:
                state["error"] = execution_result["error"]
                state["failed_agent"] = "Python"
                print(f"   Python execution failed: {execution_result['error']}")
            
        except Exception as e:
            import traceback
            print(f"   Error in Python agent: {str(e)}")
            print(f"   Traceback: {traceback.format_exc()}")
            state["error"] = str(e)
            state["failed_agent"] = "Python"
        
        return state
    
    def _self_heal_node(self, state: AnalystState) -> AnalystState:
        """Self-healing node - attempts to fix broken code"""
        print("🔧 Self-Healer: Attempting to fix code...")
        
        heal_attempts = state.get("heal_attempts", 0)
        
        try:
            fix_result = self.self_healer.heal(
                code=state.get("code", ""),
                code_type=state.get("code_type", ""),
                error=state.get("error", ""),
                question=state["question"],
                schema=state["schema"],
                plan=state["decision"],
                attempt=heal_attempts,
                suggestions=state.get("suggested_fixes", []),
            )
            
            state["heal_attempts"] = heal_attempts + 1
            
            if fix_result.get("success"):
                state["code"] = fix_result["code"]
                state["error"] = None  # Clear the error so execution is reattempted
                print(f"   Fix applied ({fix_result['fix_type']}): {fix_result['reasoning']}")
            else:
                print(f"   Fix failed: {fix_result['reasoning']}")
                # Increment retry count since fix failed
                state["retry_count"] = state.get("retry_count", 0) + 1
        except Exception as e:
            print(f"   Error in self-healer: {str(e)}")
            state["retry_count"] = state.get("retry_count", 0) + 1
        
        return state
    
    def _validator_node(self, state: AnalystState) -> AnalystState:
        """Jev Validator node - validates results with comprehensive checks"""
        print("🔍 Jev Validator: Validating results...")
        
        try:
            validation = self.validator.validate_result(
                result=state.get("result"),
                error=state.get("error"),
                question=state["question"],
                plan=state["decision"],
                retry_count=state.get("retry_count", 0),
                code=state.get("code", ""),
                code_type=state.get("code_type", ""),
                failed_agent=state.get("failed_agent"),
            )
            
            state["valid"] = validation["valid"]
            state["validation_reason"] = validation["reasoning"]
            state["validation_issues"] = validation.get("issues", [])
            state["validation_warnings"] = validation.get("warnings", [])
            state["quality_score"] = validation.get("quality_score", 1.0)
            state["validation_checks"] = validation.get("checks", {})
            state["suggested_fixes"] = validation.get("suggestions", [])
            state["last_error_category"] = validation.get("error_category")
            
            if validation.get("should_retry"):
                state["retry_count"] = state.get("retry_count", 0) + 1
                print(f"   Validation failed → {validation['decision']} "
                      f"(attempt {state['retry_count']})")
                if validation.get("issues"):
                    for issue in validation["issues"]:
                        print(f"   ⚠️  {issue}")
            else:
                print(f"   Validation: {validation['decision']} "
                      f"(quality: {validation.get('quality_score', 1.0):.2f})")
                if validation.get("warnings"):
                    for w in validation["warnings"][:3]:
                        print(f"   ℹ️  {w}")
            
        except Exception as e:
            print(f"   Error in validator: {str(e)}")
            state["valid"] = True  # Default to valid on error
            state["validation_reason"] = f"Validator error: {str(e)}"
            state["validation_issues"] = []
            state["validation_warnings"] = []
            state["quality_score"] = 0.5
            state["validation_checks"] = {}
        
        return state
    
    def _cross_check_node(self, state: AnalystState) -> AnalystState:
        """Cross-validation node - runs SQL↔Python comparison"""
        print("🔀 Cross-Validator: Running SQL/Pandas cross-check...")
        
        try:
            cross_result = self.cross_validator.cross_check(
                question=state["question"],
                schema=state["schema"],
                plan=state["decision"],
                df=state["df"],
                primary_result=state.get("result"),
                primary_method=state.get("code_type", "sql").upper(),
                tolerance=self.policy.thresholds.cross_check_tolerance,
            )
            
            state["cross_check_performed"] = True
            state["cross_check_match"] = cross_result.get("match")
            state["cross_check_confidence"] = cross_result.get("confidence", 0.0)
            state["cross_check_discrepancies"] = cross_result.get("discrepancies", [])
            
            if cross_result.get("match") is True:
                print("   ✅ Cross-check passed — results match")
            elif cross_result.get("match") is False:
                print("   ⚠️  Cross-check found discrepancies:")
                for d in cross_result.get("discrepancies", [])[:3]:
                    print(f"      - {d}")
            else:
                print("   ℹ️  Cross-check inconclusive")
            
        except Exception as e:
            print(f"   Error in cross-check: {str(e)}")
            state["cross_check_performed"] = True
            state["cross_check_match"] = None
            state["cross_check_confidence"] = 0.0
            state["cross_check_discrepancies"] = [f"Cross-check error: {str(e)}"]
        
        return state
    
    def _visualization_node(self, state: AnalystState) -> AnalystState:
        """Visualization node - generates charts"""
        print("📊 Visualization Agent: Generating charts...")
        
        try:
            if state.get("result") is None or not isinstance(state["result"], pd.DataFrame):
                print("   No valid result for visualization")
                state["charts"] = []
                return state
            
            chart_type = state["decision"].get("visualization", "bar_chart")
            
            viz_result = self.viz_agent.generate_chart(
                data=state["result"],
                chart_type=chart_type,
                plan=state["decision"],
                question=state["question"]
            )
            
            if viz_result.get("success") is True:
                state["charts"] = [chart_type]
                print(f"   Chart generated: {chart_type}")
            else:
                state["charts"] = []
                print(f"   Chart generation failed: {viz_result.get('error', 'Unknown')}")
            
        except Exception as e:
            print(f"   Error in visualization: {str(e)}")
            state["charts"] = []
        
        return state
    
    def _report_node(self, state: AnalystState) -> AnalystState:
        """Report node - generates final report"""
        print("📝 Report Agent: Generating report...")
        
        try:
            execution_details = {
                "code_type": state.get("code_type"),
                "retry_count": state.get("retry_count", 0),
                "validated": state.get("valid", False),
                "quality_score": state.get("quality_score", 1.0),
                "validation_issues": state.get("validation_issues", []),
                "validation_warnings": state.get("validation_warnings", []),
                "cross_check_performed": state.get("cross_check_performed", False),
                "cross_check_match": state.get("cross_check_match"),
                "heal_attempts": state.get("heal_attempts", 0),
            }
            
            report_result = self.report_agent.generate_report(
                question=state["question"],
                plan=state["decision"],
                result=state.get("result"),
                error=state.get("error"),
                execution_details=execution_details
            )
            
            if report_result.get("success") is True:
                state["report"] = report_result["report"]
                state["insights"] = report_result["key_insights"]
                print("   Report generated successfully")
            else:
                state["report"] = f"Report generation failed: {report_result.get('error', 'Unknown')}"
                state["insights"] = []
                print("   Report generation failed")
            
        except Exception as e:
            print(f"   Error in report generation: {str(e)}")
            state["report"] = f"Report generation error: {str(e)}"
            state["insights"] = []
        
        return state
    
    # ==================================================================
    #  Routing functions
    # ==================================================================
    
    def _route_to_agent(self, state: AnalystState) -> Literal["sql", "python", "both", "error"]:
        """Route to appropriate agent based on plan"""
        method = state.get("selected_agent", "").lower()
        
        if method == "sql":
            return "sql"
        elif method == "python":
            return "python"
        elif method == "both":
            return "both"
        else:
            return "error"
    
    def _route_after_execution(self, state: AnalystState) -> Literal["validator", "self_heal", "python", "error"]:
        """Route after agent execution — sends errors to self-healer first"""
        if state.get("error") is not None:
            error = state["error"]
            retry_count = state.get("retry_count", 0)
            heal_attempts = state.get("heal_attempts", 0)
            failed_agent = state.get("failed_agent")
            
            # Classify the error
            category = self.policy.classify_error(error)
            state["last_error_category"] = category
            
            # Fatal errors go straight to END
            if category == "fatal":
                return "error"
            
            # If we haven't exhausted heal attempts, try self-healing
            max_heal = self.policy.retry_policy.max_fix_attempts
            if heal_attempts < max_heal:
                return "self_heal"
            
            # If SQL failed, try Python as fallback
            if failed_agent == "SQL" and retry_count == 0:
                return "python"
            
            return "error"
        
        return "validator"
    
    def _route_after_heal(self, state: AnalystState) -> Literal["sql_agent", "python_agent", "validator", "error"]:
        """Route after self-healing — re-execute with the fixed code"""
        if state.get("error") is not None:
            # Heal failed — check if we should still retry
            if state.get("retry_count", 0) < config.MAX_RETRIES:
                # Try the other method
                if state.get("failed_agent") == "SQL":
                    return "python_agent"
                return "sql_agent"
            return "error"
        
        # Heal succeeded — re-execute the fixed code
        code_type = state.get("code_type", "")
        if code_type == "sql":
            return "sql_agent"
        elif code_type == "python":
            return "python_agent"
        
        return "validator"
    
    def _route_after_validation(
        self, state: AnalystState
    ) -> Literal["cross_check", "visualization", "retry", "self_heal", "error"]:
        """Route after validation — includes cross-check and self-heal options"""
        if state.get("valid", False):
            # Check if cross-check is warranted
            if self.policy.should_cross_check(
                state.get("decision", {}),
                state.get("confidence", 0.5),
            ) and not state.get("cross_check_performed", False):
                return "cross_check"
            return "visualization"
        
        retry_count = state.get("retry_count", 0)
        
        # Decide between self-heal and full retry
        action = state.get("last_error_category", "")
        if action in ("syntax", "data") and state.get("heal_attempts", 0) < self.policy.retry_policy.max_fix_attempts:
            return "self_heal"
        
        if retry_count < config.MAX_RETRIES:
            return "retry"
        
        return "error"
    
    def _route_after_cross_check(
        self, state: AnalystState
    ) -> Literal["visualization", "retry", "error"]:
        """Route after cross-check"""
        match = state.get("cross_check_match")
        
        if match is True or match is None:
            # Match or inconclusive — proceed
            return "visualization"
        
        # Mismatch — retry if we haven't exhausted retries
        if state.get("retry_count", 0) < config.MAX_RETRIES:
            state["retry_count"] = state.get("retry_count", 0) + 1
            return "retry"
        
        # Exhausted retries — proceed with what we have
        return "visualization"
    
    # ==================================================================
    #  Public API
    # ==================================================================
    
    def run(
        self,
        question: str,
        df: pd.DataFrame,
        schema: str,
        data_profile: dict,
        record_metrics: bool = True,
    ) -> AnalystState:
        """Run the complete workflow"""
        initial_state: AnalystState = {
            "question": question,
            "file_path": "",
            "schema": schema,
            "row_count": data_profile.get("row_count", 0),
            "column_count": data_profile.get("column_count", 0),
            "missing_values": data_profile.get("missing_values", {}),
            "data_types": data_profile.get("data_types", {}),
            "decision": {},
            "confidence": 0.0,
            "selected_agent": "",
            "code": "",
            "code_type": "",
            "result": None,
            "error": None,
            # Phase 5 validation state
            "valid": False,
            "validation_reason": "",
            "validation_issues": [],
            "validation_warnings": [],
            "quality_score": 1.0,
            "validation_checks": {},
            # Phase 5 cross-check state
            "cross_check_performed": False,
            "cross_check_match": None,
            "cross_check_confidence": 0.0,
            "cross_check_discrepancies": [],
            # Phase 5 self-healing state
            "retry_count": 0,
            "failed_agent": None,
            "heal_attempts": 0,
            "last_error_category": None,
            "suggested_fixes": [],
            # Output
            "charts": [],
            "insights": [],
            "report": "",
            "df": df,
            # Phase 7 state
            "datasets": {},
            "joined_schema": None,
            "eda_report": None,
            "dataset_version_id": None,
            "latency_ms": 0.0,
        }
        
        print("🚀 Starting Multi-Agent Analysis Workflow")
        print("=" * 50)
        
        with PerformanceTimer() as timer:
            final_state = self.graph.invoke(initial_state)
        
        final_state["latency_ms"] = timer.elapsed_ms
        
        print("=" * 50)
        print(f"✅ Workflow Complete ({timer.elapsed_ms:.0f}ms)")
        
        # Phase 7: Record performance metrics
        if record_metrics:
            try:
                dashboard = ModelPerformanceDashboard()
                dashboard.record(final_state, timer.elapsed_ms)
            except Exception as e:
                print(f"   Warning: Could not record metrics: {e}")
        
        return final_state
    
    def close(self):
        """Clean up resources"""
        self.executor.close()
        self.cross_validator.close()


def create_analyst_workflow() -> AnalystWorkflow:
    """Factory function to create the analyst workflow"""
    return AnalystWorkflow()