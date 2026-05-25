import logging
from app.graph.state import TriageState
from app.services.tools import tools

logger = logging.getLogger(__name__)

async def execute_tools(state: TriageState) -> dict:
    tool_calls = state.get("tool_calls", [])
    if not tool_calls:
        return {"tool_results": []}
    
    results = []
    for tool_call in tool_calls:
        tool_name = tool_call.function.name
        tool_args = tool_call.function.arguments
        
        # Find the tool
        tool = next((t for t in tools if t.name == tool_name), None)
        if tool:
            try:
                # Execute tool
                import json
                args = json.loads(tool_args)
                result = tool.invoke(args)
                results.append({"tool": tool_name, "result": result})
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                results.append({"tool": tool_name, "error": str(e)})
        else:
            logger.warning(f"Tool {tool_name} not found")
            
    return {"tool_results": results}
