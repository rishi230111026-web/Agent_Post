import os
from pymongo import MongoClient
from dotenv import load_dotenv

# 1. Load the keys from your secure .env file
load_dotenv()

# 2. Connect to your Cloud MongoDB
mongo_uri = os.environ.get("MONGO_URI")
if not mongo_uri:
    raise ValueError("Error: Could not find MONGO_URI in your .env file!")

client = MongoClient(mongo_uri)
db = client["support_agent_db"]

# 3. Define the Customer Data
customers = [
    {
        "name": "Nishant",
        "item_ordered": "MacBook Air M3",
        "quantity": 1,
        "address": "New Delhi, Delhi",
        "phone": "9876543210"
    },
    {
        "name": "Hariom",
        "item_ordered": "CMF by Nothing Phone 2 Pro",
        "quantity": 1,
        "address": "Kanpur, Uttar Pradesh",
        "phone": "9123456789"
    }
]

# 4. Define the Policy Data
policies = {
    "delivery_time": "Standard delivery takes 3-5 business days depending on the location.",
    "cancellation_policy": "Orders can be cancelled within 24 hours of placement without any penalty.",
    "urgent_help_contact": "For urgent inquiries, please contact support@portbug.com or call 1800-123-456."
}

# 5. Clear old data and insert the new data
db.customers.delete_many({})
db.policies.delete_many({})

db.customers.insert_many(customers)
db.policies.insert_one(policies)

print("Success! Database has been seeded with Nishant, Hariom, and the policies.")