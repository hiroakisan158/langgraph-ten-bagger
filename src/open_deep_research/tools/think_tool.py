from datetime import datetime
from langchain_core.tools import tool


def get_today_str() -> str:
    """Get current date in a human-readable format."""
    return datetime.now().strftime("%a %b %-d, %Y")


@tool(description="Strategic reflection tool for research planning and evaluation - MUST USE before and after each research step")
def think_tool(reflection: str) -> str:
    """Tool for strategic reflection on research progress and decision-making.
    
    🔥 CRITICAL: This tool MUST be used at key decision points in research workflow:
    1. BEFORE starting research: Plan strategy and approach
    2. AFTER each tool execution: Evaluate results and plan next steps
    3. BEFORE concluding: Assess if information is sufficient for complete answer

    When to use (MANDATORY):
    - Before any research: What is my strategic approach and priority areas?
    - After receiving search results: What key information did I find? What gaps remain?
    - Before deciding next steps: Do I have enough to answer comprehensively?
    - When assessing research gaps: What specific information am I still missing?
    - Before concluding research: Can I provide a complete answer now?

    Reflection should address:
    1. Strategic planning - What is my approach and priority for this research step?
    2. Analysis of current findings - What concrete information have I gathered?
    3. Gap assessment - What crucial information is still missing?
    4. Quality evaluation - Do I have sufficient evidence/examples for a good answer?
    5. Strategic decision - Should I continue searching or provide my answer?

    Args:
        reflection: Your detailed reflection on research strategy, progress, findings, gaps, and next steps

    Returns:
        Confirmation that reflection was recorded for decision-making
    """
    # ログを出力
    print(f"\n🧠 THINK_TOOL CALLED:")
    print(f"📝 Reflection: {reflection}")
    print(f"⏰ Timestamp: {get_today_str()}")
    print("=" * 50)
    
    return f"Reflection recorded: {reflection}"
