import mysql.connector
import requests
import re
import pandas as pd
import importlib


# Set your Groq API key
API_KEY = "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"
MODEL = "gemma2-9b-it"  # Change if needed


connection_credentails = {
    """
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin123",
        port=3306,
        database="chatbot",
        auth_plugin="mysql_native_password"
    )

"""
}

file_saving_structure = {
    """
    def plot_graph():
        { ....code ....}
    
    if __name__ == "__main__":
    plot_graph()
    """
}


def table_fetching(sql_query):
    # Connect to MySQL
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin123",
        port=3306,
        database="chatbot",
        auth_plugin="mysql_native_password"
    )
    cur = conn.cursor()
    
    # Fetch table structure
    cur.execute(sql_query)
    rows = cur.fetchall()
    columns = [col[0] for col in cur.description]
    df = pd.DataFrame(rows,columns=columns)
    cur.close()
    conn.close()
    return df


    

# Connect to MySQL
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="admin123",
    port=3306,
    database="chatbot",
    auth_plugin="mysql_native_password"
)
cur = conn.cursor()

# Fetch table structure
cur.execute("""
SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY 
FROM information_schema.COLUMNS 
WHERE TABLE_SCHEMA = 'chatbot'
ORDER BY TABLE_NAME, ORDINAL_POSITION;
""")
rows = cur.fetchall()

cur.close()
conn.close()

# ✅ Convert rows into a structured format
schema_description = ""
current_table = None

for row in rows:
    table_name, column_name, data_type, column_type, is_nullable, column_default, column_key = row
    
    if table_name != current_table:
        schema_description += f"\n📌 **Table: {table_name}**\n"
        schema_description += "| Column Name | Data Type | Nullable | Default | Key |\n"
        schema_description += "|------------|----------|----------|---------|-----|\n"
        current_table = table_name
    
    schema_description += f"| {column_name} | {data_type} | {is_nullable} | {column_default} | {column_key.decode() if isinstance(column_key, (bytes, bytearray)) else column_key} |\n"

# ✅ Define the system prompt with the formatted table schema
SYSTEM_PROMPT = f"""

You are a helpful AI assistant with access to the following database schema:

{schema_description}

You assist with SQL queries and graph generation related to this schema.

1️⃣ **Query Generation:**  
   - Collect all necessary information from the user before generating a query.  
   - If the keyword **"total"** is mentioned, apply **SUM()** in the query where relevant.  
   - Once the query is generated, provide a **brief description** explaining its purpose.  
   - Ask the user if the description is correct.  
   - Ask the user for confirmation:  
     ✅ Type **"confirm query"** to proceed.  
     ❌ Or add additional requirements.  
   - If the user inputs **"confirm query"**, return **only the SQL query** without any other text.  

2️⃣ **Graph Generation (After Query Confirmation):**  
   - After the query is confirmed, ask the user if they want a **graph representation** of the query results.  
   - If yes, ask what type of graph (e.g., bar chart, line graph, pie chart).  
   - Generate **Python code** using **Pandas & Matplotlib** to visualize the data by using the MySQL connection as {connection_credentails}.And put that python code inside a function by this structure {file_saving_structure}.Maintain proper indendation for the python code and dont add anything other than python code in that file.

"""


# ✅ Store conversation history
conversation_history = [{"role": "system", "content": SYSTEM_PROMPT}]

def chat_with_groq(prompt):
    global conversation_history  # Maintain previous messages

    # Append user message to history
    conversation_history.append({"role": "user", "content": prompt})
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": conversation_history  # Send full history
    }
    
    response = requests.post(url, json=data, headers=headers)
    
    if response.status_code == 200:
        bot_response = response.json()["choices"][0]["message"]["content"]
        conversation_history.append({"role": "system", "content": bot_response})
        return bot_response
    else:
        return f"Error: {response.status_code}, {response.text}"

if __name__ == "__main__":
    print("SQL Chatbot (Type 'exit' to quit)")
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break

        response = chat_with_groq(user_input)
        print(f"Bot: {response}")

        if user_input.lower() == "confirm query":
            sql_query = re.sub(r"```sql|```", "", response).strip()
            print(sql_query)  # ✅ Return only SQL query
            table_result = table_fetching(sql_query)
            print(table_result)
            graph_input = input("Would you like a graph representation? (yes/no): ").strip().lower()
            
            if graph_input == "yes":
                graph_query = "What type of graph? (bar, line, pie): "
                graph_type = input(graph_query).strip().lower()
                response = chat_with_groq(graph_query+graph_type)
                response = re.sub(r"```python\n|```$", "", response).strip()
                with open("graph.py", "w") as f:
                    f.write(response)
        
                importlib.reload(graph)
                import graph
                graph.plot_graph()
                                
                #print(response)
                break
