import mysql.connector
import requests
import re
import pandas as pd
import importlib.util
import matplotlib.pyplot as plt
import asyncio
import io

from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

API_KEY = "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"
MODEL = "llama3-70b-8192"
TOKEN = "7841680979:AAFKcJroMYH2WTkaXdgbXrPeHUaUOGyBrbI"

user_states = {}



conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin123",
        port=3306,
        database="chatbot",
        auth_plugin="mysql_native_password"
    )
cur = conn.cursor()


def get_schema_description():
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="admin123",
        port=3306,
        database="chatbot",
        auth_plugin="mysql_native_password"
    )
    cur = conn.cursor()
    cur.execute("""
        SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, COLUMN_DEFAULT, COLUMN_KEY 
        FROM information_schema.COLUMNS 
        WHERE TABLE_SCHEMA = 'chatbot'
        ORDER BY TABLE_NAME, ORDINAL_POSITION;
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()

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
    return schema_description

SYSTEM_PROMPT = f"""
You are a helpful AI assistant with access to the following database schema:

{get_schema_description()}

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
   - Generate **Python code** using **Pandas & Matplotlib** to visualize the data by using the MySQL connection.  
   - Format the graph code inside a function like:
        def plot_graph():
            ...code...

     and save it to a file with proper indentation and nothing extra.
"""

def table_fetching(sql_query):
    # conn = mysql.connector.connect(
    #     host="localhost",
    #     user="root",
    #     password="admin123",
    #     port=3306,
    #     database="chatbot",
    #     auth_plugin="mysql_native_password"
    # )
    # cur = conn.cursor()
    cur.execute(sql_query)
    rows = cur.fetchall()
    columns = [col[0] for col in cur.description]
    df = pd.DataFrame(rows, columns=columns)
    cur.close()
    conn.close()
    return df

def chat_with_groq(user_id, prompt):
    history = user_states.get(user_id, [{"role": "system", "content": SYSTEM_PROMPT}])
    history.append({"role": "user", "content": prompt})

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    data = {
        "model": MODEL,
        "messages": history
    }

    response = requests.post("https://api.groq.com/openai/v1/chat/completions", json=data, headers=headers)
    if response.status_code == 200:
        bot_response = response.json()["choices"][0]["message"]["content"]
        history.append({"role": "system", "content": bot_response})
        user_states[user_id] = history
        return bot_response
    return f"Error: {response.status_code}, {response.text}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! Ask me anything about your MySQL database.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_input = update.message.text.strip()

    if user_input.lower() == "confirm query":
        response = user_states[user_id][-1]["content"]
        query  =re.search(r"```(?:sql)?\s*(.*?)\s*```", response, re.DOTALL)
        
        if query:
            sql_query = query.group(1).strip()            
        else:
            print("No SQL query found.")
            
        df = table_fetching(sql_query)

        await update.message.reply_text("Query executed. Here's a preview:")
        await update.message.reply_text(df.head(10).to_string(index=False))

        await update.message.reply_text("Would you like a graph representation? (yes/no)")
        user_states[user_id].append({"role": "meta", "content": "awaiting_graph_decision"})
        return

    if user_states.get(user_id, []) and user_states[user_id][-1]["content"] == "awaiting_graph_decision":
        if user_input.lower() == "yes":
            await update.message.reply_text("What type of graph? (bar, line, pie)")
            user_states[user_id].append({"role": "meta", "content": "awaiting_graph_type"})
        else:
            await update.message.reply_text("Okay! No graph will be generated.")
        return

    if user_states.get(user_id, []) and user_states[user_id][-1]["content"] == "awaiting_graph_type":
        graph_type = user_input.lower()  
        user_input = f"type of graph is {graph_type}"
        print('user_input --------------',user_input)
        graph_code = chat_with_groq(user_id, user_input)
        print('graph_code --------------',graph_code)
        graph_code_cleaned = re.sub(r"```python\n|```$", "", graph_code).strip()

        with open("graph.py", "w") as f:
            f.write(graph_code_cleaned)

        
        spec = importlib.util.spec_from_file_location("graph", "graph.py")
        graph_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(graph_module)

        # Capture plot output to memory
        fig = plt.figure()
        graph_module.plot_graph()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plt.close(fig)

        await update.message.reply_photo(photo=InputFile(buf, filename="graph.png"))
        return

    # Default behavior
    response = chat_with_groq(user_id, user_input)
    await update.message.reply_text(response)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Telegram SQL chatbot running...")
    app.run_polling()

if __name__ == "__main__":
    main()
