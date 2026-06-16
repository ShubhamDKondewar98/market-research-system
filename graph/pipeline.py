from langgraph.graph import StateGraph, START, END
from graph.state import AgentState
from agents.technical_agent import technical_agent
from agents.news_agent import news_agent
from agents.sentiment_agent import sentiment_agent
from agents.risk_agent import risk_agent
from agents.validation_agent import validation_agent



# Initialize graph
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("technical_agent",technical_agent)
workflow.add_node("news_agent",news_agent)
workflow.add_node("sentiment_agent",sentiment_agent)
workflow.add_node("risk_agent",risk_agent)
workflow.add_node("validation_agent",validation_agent)

# Add edges — parallel execution
workflow.add_edge(START,"technical_agent")
workflow.add_edge(START,"news_agent")
workflow.add_edge(START,"sentiment_agent")
workflow.add_edge(START,"risk_agent") 

workflow.add_edge("technical_agent","validation_agent")
workflow.add_edge("news_agent","validation_agent")
workflow.add_edge("sentiment_agent","validation_agent")
workflow.add_edge("risk_agent","validation_agent") 

workflow.add_edge("validation_agent", END)


# Compile
graph = workflow.compile()

print(graph.get_graph().draw_ascii())


