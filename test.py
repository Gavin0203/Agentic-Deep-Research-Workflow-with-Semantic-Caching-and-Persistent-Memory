from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env file

def search_tool(query: str) -> str:
    """Search the web for information."""
    return f"Search results for '{query}': [Sample search result]"

def send_email_tool(email: str, subject: str, body: str) -> str:
    """Send an email."""
    return f"Email sent to {email} with subject '{subject}' and body '{body}'"

agent = create_agent(
    model="gpt-5.5",
    tools=[search_tool, send_email_tool],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                # Require approval for sensitive operations
                "send_email_tool": {"allowed_decisions": ["approve", "edit"]},
                # Auto-approve safe operations
                "search_tool": False,
            }
        ),
    ],
    # Persist the state across interrupts
    checkpointer=InMemorySaver(),
)

# Human-in-the-loop requires a thread ID for persistence
config = {"configurable": {"thread_id": "some_id"}}

# Agent will pause and wait for approval before executing sensitive tools
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Send an email to the team@test.com with subject 'Project Update' and body 'The project is on track.'"}]},
    config=config
)
print(result)
#result = agent.invoke(Command(resume={"decisions": [{"type": "approve"}]}), config=config)  # Approve the action