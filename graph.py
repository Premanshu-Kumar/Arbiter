"""
LangGraph Workflow - Multi-agent orchestration for data analysis
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
from sandbox.executor import SafeExecutor
import config


class AnalystWorkflow:
    """LangGraph workflow for multi-agent data analysis"""
    
    def __init__(self):
        self.planner = JevPlanner()
        self.sql_agent = SQLAgent()
        self.python_agent = PythonAgent()
        self.viz_agent = VizAgent()
        self.report_agent = ReportAgent()
        self.validator = JevValidator()
        self.executor = SafeExecutor()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AnalystState)
        
        # Add nodes
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("sql_agent", self._sql_agent_node)
        workflow.add_node("python_agent", self._python_agent_node)
        workflow.add_node("validator", self._validator_node)
        workflow.add_node("visualization", self._visualization_node)
        workflow.add_node("report", self._report_node)
        
        # Set entry point
        workflow.set_entry_point("planner")
        
        # Add conditional edges
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
        
        workflow.add_conditional_edges(
            "sql_agent",
            self._route_after_execution,
            {
                "validator": "validator",
                "python": "python_agent",  # Fallback to Python
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "python_agent",
            self._route_after_execution,
            {
                "validator": "validator",
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "validator",
            self._route_after_validation,
            {
                "visualization": "visualization",
                "retry": "planner",  # Retry with different approach
                "error": END
            }
        )
        
        workflow.add_edge("visualization", "report")
        workflow.add_edge("report", END)
        
        return workflow.compile()
    
    def _planner_node(self, state: AnalystState) -> AnalystState:
        """Jev Planner node - creates analysis plan"""
        print("🧠 Jev Planner: Creating analysis plan...")
        
        try:
            # Create data profile for planning
            data_profile = {
                "row_count": state.get("row_count", 0),
                "column_count": state.get("column_count", 0),
                "data_types": state.get("data_types", {}),
                "missing_values": state.get("missing_values", {})
            }
            
            # Generate analysis plan
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
            # Setup executor with data
            if state.get("df") is None:
                raise Exception("No DataFrame available in state")
            
            self.executor.setup_duckdb(state["df"], "data")
            
            # Generate SQL
            plan = {
                "method": "SQL",
                "requires_aggregation": state["decision"].get("requires_aggregation", False),
                "requires_time_series": state["decision"].get("requires_time_series", False),
                "requires_filtering": state["decision"].get("requires_filtering", False),
                "requires_sorting": state["decision"].get("requires_sorting", False),
                "visualization": state["decision"].get("visualization", "table")
            }
            
            # Try to generate SQL with Ollama, fall back to mock
            try:
                sql_result = self.sql_agent.generate_sql(
                    question=state["question"],
                    schema=state["schema"],
                    plan=plan
                )
                # If Ollama fails, use mock
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
            
            if sql_result.get("code") is None or sql_result.get("code") == "":
                state["error"] = "SQL generation returned empty code"
                state["failed_agent"] = "SQL"
                return state
            
            state["code"] = sql_result["code"]
            state["code_type"] = "sql"
            
            # Execute SQL
            execution_result = self.executor.execute_sql(sql_result["code"])
            
            if execution_result.get("success") is True:
                state["result"] = execution_result["result"]
                state["error"] = None
                if isinstance(state["result"], pd.DataFrame):
                    if not state["result"].empty:
                        print(f"   SQL executed successfully: {len(state['result'])} rows")
                    else:
                        print(f"   SQL executed successfully: 0 rows")
                else:
                    print(f"   SQL executed successfully")
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
            # Generate Python
            plan = {
                "method": "Python",
                "requires_aggregation": state["decision"].get("requires_aggregation", False),
                "requires_time_series": state["decision"].get("requires_time_series", False),
                "requires_filtering": state["decision"].get("requires_filtering", False),
                "requires_sorting": state["decision"].get("requires_sorting", False),
                "visualization": state["decision"].get("visualization", "table")
            }
            
            # Try to generate Python with Ollama, fall back to mock
            try:
                python_result = self.python_agent.generate_python(
                    question=state["question"],
                    schema=state["schema"],
                    plan=plan
                )
                # If Ollama fails, use mock
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
            
            # Execute Python
            if state.get("df") is None:
                raise Exception("No DataFrame available in state")
            
            # Check if code generation failed
            if python_result.get("code") is None or python_result.get("code") == "":
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
                print(f"   Python executed successfully")
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
    
    def _validator_node(self, state: AnalystState) -> AnalystState:
        """Jev Validator node - validates results"""
        print("🔍 Jev Validator: Validating results...")
        
        try:
            validation = self.validator.validate_result(
                result=state.get("result"),
                error=state.get("error"),
                question=state["question"],
                plan=state["decision"],
                retry_count=state.get("retry_count", 0)
            )
            
            state["valid"] = validation["valid"]
            state["validation_reason"] = validation["reasoning"]
            
            if validation.get("should_retry") is True:
                state["retry_count"] = state.get("retry_count", 0) + 1
                print(f"   Validation failed, retrying (attempt {state['retry_count']})")
            else:
                print(f"   Validation passed: {validation['reasoning']}")
            
        except Exception as e:
            print(f"   Error in validator: {str(e)}")
            state["valid"] = True  # Default to valid on error
            state["validation_reason"] = f"Validator error: {str(e)}"
        
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
                "validated": state.get("valid", False)
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
                print(f"   Report generated successfully")
            else:
                state["report"] = f"Report generation failed: {report_result.get('error', 'Unknown')}"
                state["insights"] = []
                print(f"   Report generation failed")
            
        except Exception as e:
            print(f"   Error in report generation: {str(e)}")
            state["report"] = f"Report generation error: {str(e)}"
            state["insights"] = []
        
        return state
    
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
    
    def _route_after_execution(self, state: AnalystState) -> Literal["validator", "python", "error"]:
        """Route after agent execution"""
        if state.get("error") is not None:
            # If SQL failed, try Python as fallback
            if state.get("failed_agent") == "SQL" and state.get("retry_count", 0) == 0:
                return "python"
            return "error"
        return "validator"
    
    def _route_after_validation(self, state: AnalystState) -> Literal["visualization", "retry", "error"]:
        """Route after validation"""
        if state.get("valid", False):
            return "visualization"
        elif state.get("retry_count", 0) < config.MAX_RETRIES:
            return "retry"
        else:
            return "error"
    
    def run(self, question: str, df: pd.DataFrame, schema: str, data_profile: dict) -> AnalystState:
        """Run the complete workflow"""
        # Initialize state
        initial_state: AnalystState = {
            "question": question,
            "file_path": "",
            "schema": schema,
            "row_count": data_profile.get("row_count", 0),
            "column_count": data_profile.get("column_count", 0),
            "missing_values": data_profile.get("missing_values", {}),
            "decision": {},
            "confidence": 0.0,
            "selected_agent": "",
            "code": "",
            "code_type": "",
            "result": None,
            "error": None,
            "valid": False,
            "validation_reason": "",
            "retry_count": 0,
            "failed_agent": None,
            "charts": [],
            "insights": [],
            "report": "",
            "df": df  # Include DataFrame for execution
        }
        
        print("🚀 Starting Multi-Agent Analysis Workflow")
        print("="*50)
        
        # Run the graph
        final_state = self.graph.invoke(initial_state)
        
        print("="*50)
        print("✅ Workflow Complete")
        
        return final_state
    
    def close(self):
        """Clean up resources"""
        self.executor.close()


def create_analyst_workflow() -> AnalystWorkflow:
    """Factory function to create the analyst workflow"""
    return AnalystWorkflow()