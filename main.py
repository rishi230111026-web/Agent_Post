import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient
from crewai import Agent, Task, Crew, Process, LLM
from crewai.tools import tool
from dotenv import load_dotenv

# 1. Load the secure keys
load_dotenv()

# 2. FastAPI Setup
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. Database Connection
mongo_uri = os.environ.get("MONGO_URI")
client = MongoClient(mongo_uri)
db = client["support_agent_db"]

# 4. Gemini LLM Setup 
gemini_key = os.environ.get("GEMINI_API_KEY")

llm_high_tier = LLM(
    model="gemini/gemini-2.5-flash", 
    api_key=gemini_key
)

# 5. Custom Tools
@tool("Fetch Customer Data")
def fetch_customer_data(name: str) -> str:
    """Fetches order details, address, and phone number for a given customer name."""
    user = db.customers.find_one({"name": {"$regex": name, "$options": "i"}})
    if user:
        return f"Name: {user['name']}, Item: {user['item_ordered']}, Qty: {user['quantity']}, Address: {user['address']}, Phone: {user['phone']}"
    return "Customer not found."

@tool("Place New Order")
def place_new_order(name: str, item_ordered: str, quantity: int, address: str, phone: str) -> str:
    """Places a new order in the database. Requires name, item_ordered, quantity, address, and phone."""
    new_order = {
        "name": name,
        "item_ordered": item_ordered,
        "quantity": int(quantity),
        "address": address,
        "phone": phone
    }
    db.customers.insert_one(new_order)
    return f"SUCCESS: Order placed for {name}. They ordered {quantity}x {item_ordered} to {address}."

@tool("Fetch Policy Data")
def fetch_policy_data(query: str) -> str:
    """Fetches standard company policies regarding delivery, cancellation, and urgent help."""
    policy = db.policies.find_one()
    if policy:
        return f"Delivery: {policy['delivery_time']} | Cancellation: {policy['cancellation_policy']} | Contact: {policy['urgent_help_contact']}"
    return "Policy data not found."

# 6. API Request Format
class ChatRequest(BaseModel):
    user_message: str

# 7. The Main Chat Endpoint
@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    user_query = request.user_message
    
    # --- CREWAI AGENTS (Updated for natural conversation) ---
    data_agent = Agent(
        role='Customer Data Specialist',
        goal='Handle database tasks ONLY when the user asks about an order.',
        backstory='You are a database expert. You do not assume the user wants to buy something. You only use your tools if the user explicitly asks to check an order or place a new one.',
        verbose=True,
        allow_delegation=False,
        tools=[fetch_customer_data, place_new_order],
        llm=llm_high_tier
    )

    policy_agent = Agent(
        role='Company Policy Specialist',
        goal='Provide policy details ONLY if the user asks a question about rules, delivery, or cancellation.',
        backstory='You know the company rulebook. If the user is just saying hello, you do nothing.',
        verbose=True,
        allow_delegation=False,
        tools=[fetch_policy_data],
        llm=llm_high_tier
    )

    response_agent = Agent(
        role='Conversational Support Lead',
        goal='Have a natural, friendly conversation with the user based on exactly what they said.',
        backstory='You are a friendly, talkative support agent. You listen first. If the user just says "hi", you just say "Hello! How can I help you today?". You NEVER ask for order details unless the user explicitly stated they want to buy something.',
        verbose=True,
        allow_delegation=False,
        llm=llm_high_tier
    )

    # --- TASKS ---
    task1 = Task(
        description=f"Analyze the user's query: '{user_query}'. Figure out their intent. If it's just a greeting, do not use tools. If they want to check an order, use fetch_customer_data. If they EXPLICITLY want to place an order, use place_new_order.",
        expected_output="Details of the user's intent, database results if applicable, or just a note that it was a general chat message.",
        agent=data_agent,
        async_execution=True
    )

    task2 = Task(
        description=f"Analyze the user's query: '{user_query}'. If they are asking about policies, fetch them. Otherwise, note that no policy is needed.",
        expected_output="Company policy details, or note that no policy was needed.",
        agent=policy_agent,
        async_execution=True
    )

    task3 = Task(
        description="Format a natural, conversational response. Address exactly what the user said. Do not mention missing order details unless they specifically asked to place an order.",
        expected_output="A clean, conversational text response to send back to the user.",
        agent=response_agent,
        context=[task1, task2]
    )

    # --- CREW EXECUTION ---
    support_crew = Crew(
        agents=[data_agent, policy_agent, response_agent],
        tasks=[task1, task2, task3],
        process=Process.sequential
    )

    result = support_crew.kickoff()
    
    return {"response": result.raw}