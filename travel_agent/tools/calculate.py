from langchain.tools import tool

@tool
def calculate_budget(expression: str) -> str:
    """Calculate travel budget. Input should be a mathematical expression like '100+200' or '500*0.15'."""
    try:
        allowed_chars = set('0123456789+-*/(). ')
        if not all(c in allowed_chars for c in expression):
            return "Invalid expression. Use only numbers and operators (+, -, *, /, parentheses)."
        
        result = eval(expression)
        return f"Calculated result: {result}"
    except Exception as e:
        return f"Calculation error: {str(e)}"


