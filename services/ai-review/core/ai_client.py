"""
AI Client for Groq API - FIXED VERSION
Produces varied, accurate code review scores based on actual code quality
"""

import json
from typing import Dict, List, Optional
import structlog
from groq import AsyncGroq

from core.config import settings

logger = structlog.get_logger(__name__)


class GroqAIClient:
    """Client for interacting with Groq API"""
    
    def __init__(self):
        """Initialize Groq client"""
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in environment")
        
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        self.max_tokens = settings.GROQ_MAX_TOKENS
        # ✅ FIX: Increase temperature for more varied responses
        self.temperature = 0.7  # Was 0.1, now 0.7 for variety
        
        logger.info(
            "Groq AI Client initialized",
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature
        )
    
    async def analyze_code(self, files_data: List[Dict], context: Dict) -> Dict:
        """
        Analyze code files using Groq AI
        
        Args:
            files_data: List of file data with content
            context: Additional context (language, description, etc.)
        
        Returns:
            Dictionary with review results
        """
        try:
            logger.info(
                "Starting code analysis",
                files_count=len(files_data),
                language=context.get("language"),
                model=self.model
            )
            
            # Build prompt
            prompt = self._build_review_prompt(files_data, context)
            
            # Call Groq API
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                response_format={"type": "json_object"}
            )
            
            # Parse response
            result = self._parse_ai_response(response)
            
            logger.info(
                "Code analysis completed",
                overall_score=result.get("overall_score"),
                suggestions_count=len(result.get("suggestions", [])),
                tokens_used=result.get("tokens_used")
            )
            
            return result
            
        except Exception as e:
            logger.error("Code analysis failed", error=str(e))
            raise
    
    def _get_system_prompt(self) -> str:
        """Get system prompt for AI - FIX: Detailed scoring criteria"""
        return """You are a strict, expert code reviewer with high standards. Analyze code thoroughly and provide honest, varied scores.

SCORING GUIDELINES (be strict and specific):
- 90-100: Exceptional code - production-ready, well-tested, follows all best practices
- 80-89: Very good code - minor improvements possible
- 70-79: Good code - some issues need addressing
- 60-69: Acceptable code - several issues, refactoring recommended
- 50-59: Poor code - significant problems, major refactoring needed
- Below 50: Critical issues - security holes, bugs, or fundamental flaws

IMPORTANT: Give LOW scores for:
- Missing error handling
- No input validation
- Security vulnerabilities
- Poor code structure
- No documentation
- Hard-coded values
- Code duplication
- Performance issues

Return JSON with:
{
  "overall_score": <0-100, be honest and vary based on ACTUAL code quality>,
  "summary": "<2-3 sentence honest assessment>",
  "suggestions": [
    {
      "file_path": "<filename>",
      "line_number": <line or null>,
      "suggestion_type": "bug|performance|style|security|best_practice",
      "severity": "low|medium|high|critical",
      "title": "<brief title>",
      "description": "<detailed explanation>",
      "suggested_fix": "<specific code fix>",
      "confidence_score": <0-100>
    }
  ]
}

Be critical, thorough, and provide specific line-by-line feedback. VARY your scores based on actual code quality."""
    
    def _build_review_prompt(self, files_data: List[Dict], context: Dict) -> str:
        """Build review prompt from files and context"""
        prompt_parts = []
        
        # Add context
        prompt_parts.append("=== CODE REVIEW REQUEST ===\n")
        
        if context.get("language"):
            prompt_parts.append(f"Language: {context['language']}")
        
        if context.get("description"):
            prompt_parts.append(f"Description: {context['description']}")
        
        prompt_parts.append(f"\nFiles to review: {len(files_data)}\n")
        prompt_parts.append("--- CODE FILES ---\n")
        
        # Add files with line numbers
        for file_data in files_data:
            filename = file_data["filename"]
            content = file_data["content"]
            
            # Add line numbers for better feedback
            lines = content.split('\n')
            numbered_content = '\n'.join([f"{i+1:4d} | {line}" for i, line in enumerate(lines)])
            
            prompt_parts.append(f"\n### File: {filename}")
            prompt_parts.append(f"Lines: {len(lines)}, Size: {len(content)} bytes\n")
            prompt_parts.append("```")
            prompt_parts.append(numbered_content)
            prompt_parts.append("```\n")
        
        prompt_parts.append("\n=== REVIEW INSTRUCTIONS ===")
        prompt_parts.append("1. Analyze EACH file thoroughly")
        prompt_parts.append("2. Check for bugs, security issues, performance problems")
        prompt_parts.append("3. Evaluate code structure, readability, maintainability")
        prompt_parts.append("4. Give an HONEST score - don't be generous, be accurate")
        prompt_parts.append("5. Provide specific, actionable suggestions with line numbers")
        prompt_parts.append("6. Return ONLY valid JSON\n")
        
        return "\n".join(prompt_parts)
    
    def _parse_ai_response(self, response) -> Dict:
        """Parse Groq API response"""
        try:
            # Extract content
            content = response.choices[0].message.content
            
            # Parse JSON
            result = json.loads(content)
            
            # Add metadata
            result["tokens_used"] = response.usage.total_tokens
            result["model_used"] = self.model
            
            # Validate required fields
            if "overall_score" not in result:
                result["overall_score"] = 65  # Neutral default
            
            if "summary" not in result:
                result["summary"] = "Code analysis completed"
            
            if "suggestions" not in result:
                result["suggestions"] = []
            
            # Ensure overall_score is in range
            result["overall_score"] = max(0, min(100, result["overall_score"]))
            
            # Validate and clean suggestions
            result["suggestions"] = self._validate_suggestions(result["suggestions"])
            
            # ✅ FIX: Log the actual score for debugging
            logger.info(
                "AI returned score",
                score=result["overall_score"],
                suggestions=len(result["suggestions"])
            )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error("Failed to parse AI response as JSON", error=str(e))
            # Return fallback response
            return {
                "overall_score": 65,
                "summary": "Analysis completed but response format was invalid",
                "suggestions": [],
                "tokens_used": getattr(response.usage, 'total_tokens', 0),
                "model_used": self.model
            }
        except Exception as e:
            logger.error("Error parsing AI response", error=str(e))
            raise
    
    def _validate_suggestions(self, suggestions: List[Dict]) -> List[Dict]:
        """Validate and clean suggestion data"""
        validated = []
        
        for suggestion in suggestions:
            # Skip invalid suggestions
            if not isinstance(suggestion, dict):
                continue
            
            # Ensure required fields
            validated_suggestion = {
                "file_path": suggestion.get("file_path", "unknown"),
                "line_number": suggestion.get("line_number"),
                "suggestion_type": self._validate_type(suggestion.get("suggestion_type")),
                "severity": self._validate_severity(suggestion.get("severity")),
                "title": suggestion.get("title", "Code improvement suggested"),
                "description": suggestion.get("description", "No description provided"),
                "suggested_fix": suggestion.get("suggested_fix"),
                "confidence_score": max(0, min(100, suggestion.get("confidence_score", 75)))
            }
            
            validated.append(validated_suggestion)
        
        return validated
    
    def _validate_type(self, suggestion_type: Optional[str]) -> str:
        """Validate suggestion type"""
        valid_types = ["bug", "performance", "style", "security", "best_practice", "other"]
        
        if suggestion_type and suggestion_type.lower() in valid_types:
            return suggestion_type.lower()
        
        return "other"
    
    def _validate_severity(self, severity: Optional[str]) -> str:
        """Validate severity level"""
        valid_severities = ["low", "medium", "high", "critical"]
        
        if severity and severity.lower() in valid_severities:
            return severity.lower()
        
        return "medium"


# Singleton instance
_ai_client_instance: Optional[GroqAIClient] = None


def get_ai_client() -> GroqAIClient:
    """Get singleton AI client instance"""
    global _ai_client_instance
    
    if _ai_client_instance is None:
        _ai_client_instance = GroqAIClient()
    
    return _ai_client_instance


async def test_groq_connection() -> bool:
    """Test connection to Groq API"""
    try:
        logger.info("Testing Groq API connection")
        
        client = get_ai_client()
        
        # Simple test request
        response = await client.client.chat.completions.create(
            model=client.model,
            messages=[
                {"role": "user", "content": "Say 'test' in JSON format: {\"result\": \"test\"}"}
            ],
            max_tokens=50,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        if response.choices[0].message.content:
            logger.info("Groq API connection test successful")
            return True
        else:
            raise Exception("Empty response from Groq API")
            
    except Exception as e:
        logger.error("Groq API connection test failed", error=str(e))
        raise Exception(f"Groq API connection failed: {str(e)}")


async def init_groq_client():
    """Initialize Groq client"""
    logger.info("Initializing Groq client")
    client = get_ai_client()
    logger.info("Groq client initialized successfully")
    return client