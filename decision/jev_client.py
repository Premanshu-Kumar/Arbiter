"""
Jev Client - Interface for Jev decision engine
"""
import requests
import json
from typing import Dict, Any, Optional
import config


class JevClient:
    """Client for interacting with Jev decision engine"""
    
    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or config.JEV_API_KEY
        self.model = model or config.JEV_MODEL
        self.base_url = "https://api.jev.ai/v1"  # Placeholder - adjust based on actual Jev API
        
        if not self.api_key:
            print("Warning: JEV_API_KEY not configured. Using fallback logic.")
    
    def check_connection(self) -> bool:
        """Check if Jev service is accessible"""
        if not self.api_key:
            return False
        
        try:
            # Placeholder health check - adjust based on actual Jev API
            response = requests.get(
                f"{self.base_url}/health",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def make_decision(
        self,
        context: Dict[str, Any],
        decision_type: str
    ) -> Dict[str, Any]:
        """
        Make a decision using Jev
        
        Args:
            context: Context information for the decision
            decision_type: Type of decision (routing, validation, retry, etc.)
        
        Returns:
            Decision result with confidence score
        """
        if not self.api_key:
            # Fallback to rule-based decision making
            return self._fallback_decision(context, decision_type)
        
        try:
            payload = {
                "model": self.model,
                "decision_type": decision_type,
                "context": context
            }
            
            response = requests.post(
                f"{self.base_url}/decide",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "decision": result.get("decision"),
                    "confidence": result.get("confidence", 0.5),
                    "reasoning": result.get("reasoning", "")
                }
            else:
                print(f"Jev API error: {response.status_code}, using fallback")
                return self._fallback_decision(context, decision_type)
                
        except Exception as e:
            print(f"Error calling Jev: {str(e)}, using fallback")
            return self._fallback_decision(context, decision_type)
    
    def _fallback_decision(self, context: Dict[str, Any], decision_type: str) -> Dict[str, Any]:
        """Fallback rule-based decision making when Jev is unavailable"""
        
        if decision_type == "routing":
            # Default to SQL for aggregation, Python for complex operations
            question = context.get("question", "").lower()
            
            if any(word in question for word in ["average", "sum", "count", "group", "total"]):
                return {
                    "decision": {"method": "SQL"},
                    "confidence": 0.7,
                    "reasoning": "Rule-based: Aggregation keywords suggest SQL"
                }
            else:
                return {
                    "decision": {"method": "Python"},
                    "confidence": 0.6,
                    "reasoning": "Rule-based: Default to Python for general queries"
                }
        
        elif decision_type == "validation":
            # Accept results unless there are obvious errors
            error = context.get("error")
            if error:
                return {
                    "decision": "RETRY",
                    "confidence": 0.8,
                    "reasoning": f"Error detected: {error}"
                }
            else:
                return {
                    "decision": "ACCEPT",
                    "confidence": 0.7,
                    "reasoning": "No errors detected"
                }
        
        elif decision_type == "retry":
            retry_count = context.get("retry_count", 0)
            if retry_count >= config.MAX_RETRIES:
                return {
                    "decision": "REJECT",
                    "confidence": 0.9,
                    "reasoning": "Max retries exceeded"
                }
            else:
                return {
                    "decision": "RETRY",
                    "confidence": 0.8,
                    "reasoning": f"Retry attempt {retry_count + 1}"
                }
        
        else:
            return {
                "decision": {},
                "confidence": 0.5,
                "reasoning": "Unknown decision type, using default"
            }
    
    def plan_analysis(self, question: str, schema: str) -> Dict[str, Any]:
        """Plan the analysis approach for a given question"""
        context = {
            "question": question,
            "schema": schema
        }
        
        return self.make_decision(context, "routing")
