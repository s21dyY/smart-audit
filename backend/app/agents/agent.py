from google.adk.agents import Agent
from google.adk.tools import agent_tool
from google.genai import types
from google.adk.models.google_llm import Gemini
import json

with open("knowledge.json", "r") as f:
    knowledge_data = json.load(f)

knowledge_str = json.dumps(knowledge_data, indent=2)

# retry config to prevent limit errors
retry_config = types.HttpRetryOptions(
    attempts=5, 
    initial_delay=10, 
    max_delay=60
)

# "Worker Agent
# 1. The Classifier (Deterministic Output)
matching_agent = Agent(
    name="MatchingAgent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction=f"""You are a DETERMINISTIC Financial Audit Tool. 

    KNOWLEDGE BASE (MANDATORY): {knowledge_str}

    STRICT OPERATING RULES:
    1. SEARCH provided KNOWLEDGE BASE for the exact user request.
    2. JSON ONLY: Your output must be ONLY a JSON object. No conversation.
    
    JSON SCHEMA:
    {{
        "financial_audit": {{
            "primary_metric": "string",
            "value": float (amount in us dollars or unit in the question),
            "status": "Peer Match | Above Target | Below Target",
            "context": "Direct quote from KNOWLEDGE BASE verifying the fact",
            "confidence": float (0.0 to 1.0) 
        }}
    }}
    
    If the data is truly missing from the KNOWLEDGE BASE, set value to 0.0 and status to "Missing"."""
)

# 2. The Context Provider,  not using for now for quota savings
memory_agent = Agent(
    name="MemoryAgent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""You are the System Context Monitor.

   TASK: Maintain the 'World Model' for this session.
   
   RULE: Even if this is the FIRST message, do NOT just say 'No context'. 
   Instead, summarize the current user intent.
   
   Example (First Message): 'User is starting an audit of MGM Resorts FY2022 regional performance.'
   Example (Second Message): 'Comparing MGM's 90% Vegas concentration with PepsiCo's CapEx.'"""
)

# 3. The Generator
conversation_agent = Agent(
    name="ConversationAgent",
    model=Gemini(model="gemini-2.5-flash-lite", retry_options=retry_config),
    instruction="""You are a Senior Portfolio Manager. 
    
    INPUT: You will receive a 'financial_audit' JSON object. 
    
    CRITICAL RULE: 
    - If the input is empty, missing, or says 'Data Missing', do NOT crash. 
    - Instead, explain to the user that specific 10-K data for this company/year 
    is not in the current audit scope and offer to analyze a different metric.
    
    TASK: Convert available audit data into a professional narrative. 
    - Use 'financial_audit' keys: primary_metric, value, status, and context.
    - If status is 'Peer Match', validate the finding with the provided context."""
)

# Root Orchestrator
root_agent = Agent(
    name="FinanceOrchestrator",
    model=Gemini(model="gemini-2.5-flash", retry_options=retry_config),
    instruction=f"""You are the Lead Financial Systems Orchestrator. 

            PROTOCOL: Execute a precise two-stage pipeline to audit data and maintain state.

            STRICT EXECUTION FLOW:
            1. STATE RESOLUTION (Call MemoryAgent): 
            - Mandatory: Call MemoryAgent first.
            - Purpose: Retrieve the 'memory_summary' to resolve pronouns (e.g., 'them', 'it', 'the previous company').
            
            2. DATA RETRIEVAL & SYNTHESIS (Call MatchingAgent OR ConversationAgent):
            - SEARCH: Check the provided KNOWLEDGE BASE internally first.
            - IF DATA FOUND INTERNALLY: Skip MatchingAgent. Pass your internal JSON and the 'memory_summary' directly to ConversationAgent.
            - IF DATA MISSING/COMPLEX: Call MatchingAgent, then pass its 'financial_audit' output and 'memory_summary' to ConversationAgent.

            DELIVERY: 
            - Return the ConversationAgent's response VERBATIM.
            - Do NOT provide your own commentary or step-by-step updates.

            CONSTRAINTS:
            - QUOTA PRIORITY: Limit to 2 tool-calling turns per message.
            - SILENT MODE: No intro/outro text. Just the final analyst output.""",
    tools=[
        agent_tool.AgentTool(agent=memory_agent),  # Disabled for quota savings
        agent_tool.AgentTool(agent=matching_agent),  # Disabled for quota savings
        agent_tool.AgentTool(agent=conversation_agent)
    ]
)