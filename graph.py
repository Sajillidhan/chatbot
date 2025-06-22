def plot_graph():
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="admin123",
            port=3306,
            database="chatbot",
            auth_plugin="mysql_native_password"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT AGE, SUM(REVENUE) AS TotalRevenue FROM employee_details GROUP BY AGE")
        data = cursor.fetchall()
        conn.close()
        import pandas as pd
        import matplotlib.pyplot as plt

        df = pd.DataFrame(data, columns=['Age', 'TotalRevenue'])

        plt.pie(df['TotalRevenue'], labels=df['Age'], autopct='%1.1f%%', startangle=90)
        plt.title('Age Wise Total Revenue')
        plt.show()
    
    if __name__ == "__main__":
      plot_graph()