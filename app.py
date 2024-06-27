import google.generativeai as genai
import pandas as pd
import json
import typing_extensions
import streamlit as st
import os
import re
# from dotenv import load_dotenv

# load_dotenv()
# api_key1 = os.getenv('GOOGLE_API_KEY')
# os.environ['GOOGLE_API_KEY'] = api_key1
# genai.configure(api_key=api_key1)

api_key1 = st.secrets["google_api_key"]
os.environ['GOOGLE_API_KEY'] = api_key1
genai.configure(api_key=api_key1)

model_pandas = genai.GenerativeModel(
    'gemini-1.5-flash-latest',
    system_instruction="You are an expert python developer who works with pandas. You make sure to generate simple pandas 'command' for the user queries in JSON format. No need to add 'print' function. Analyse the datatypes of the columns before generating the command. If unfeasible, return 'None'."
)
model_response = genai.GenerativeModel(
    'gemini-1.5-flash-latest',
    system_instruction="Your task is to comprehend. You must analyse the user query and response data to generate a response data in natural language."
)
model_sql = genai.GenerativeModel(
    'gemini-1.5-flash-latest',
    system_instruction="You are an expert in SQL. Generate a simple SQL query for the given user query based on the dataframe structure provided."
)

class Command(typing_extensions.TypedDict):
    command: str

st.set_page_config("Talk2CSV 📈")
st.title('Talk2CSV 📈')
st.write('Talk with your CSV data and get sql query using Gemini!')

st.sidebar.header("Configuration")
api_key_input = st.sidebar.text_input("Enter your Gemini API Key (if available)", type="password")
temperature = st.sidebar.slider("Select Temperature", 0.0, 1.0, 0.8)
model_selection = st.sidebar.selectbox(
    "Select Model",
    ("gemini-1.5", "gemini-1.5-pro", "gemini-1.0-pro", "gemini-1.5-flash")
)
st.markdown("App built by Subhayu Dutta")

option = st.sidebar.radio(
    "Choose an option",
    ("Chat With CSV", "Get SQL Query")
)



uploaded_file = st.file_uploader("Upload your dataset here:")
if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.write("Dataset:")
    st.dataframe(df,height=200)
    head = str(df.head().to_dict())
    desc = str(df.describe().to_dict())
    cols = str(df.columns.to_list())
    dtype = str(df.dtypes.to_dict())

    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant", "content": "How can I help you?"}]

    for msg in st.session_state.messages:
        role = msg["role"]
        avatar = "user.png" if role == "user" else "bot.png"
        st.chat_message(role, avatar=avatar).write(msg["content"])

    if user_query := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": user_query})
        st.chat_message("user", avatar="user.png").write(user_query)

        final_query = f"The dataframe name is 'df'. df has the columns {cols} and their datatypes are {dtype}. df is in the following format: {desc}. The head of df is: {head}. You cannot use df.info() or any command that cannot be printed. Write a pandas command for this query on the dataframe df: {user_query}"
        sql_query_prompt = f"The dataframe name is 'df'. df has the columns {cols} and their datatypes are {dtype}. Generate a simple SQL query for this user query: {user_query}"

        if option == "Chat With CSV":
            with st.spinner('Analyzing the data...'):
                response = model_pandas.generate_content(
                    final_query,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=Command,
                        temperature=0.3
                    )
                )
                command = json.loads(response.text)['command']

            try:
                exec(f"data = {command}")
                natural_response = f"The user query is {final_query}. The output of the command is {str(data)}. If the data is 'None', you can say 'Please ask a query to get started'. Do not mention the command used. Generate a response in natural language for the output."
                bot_response = model_response.generate_content(
                    natural_response,
                    generation_config=genai.GenerationConfig(temperature=0.7)
                )
                st.chat_message("assistant", avatar="bot.png").write(bot_response.text)
                st.session_state.messages.append({"role": "assistant", "content": bot_response.text})

            except Exception as e:
                st.session_state.messages.append({"role": "assistant", "content": "Error"})

        elif option == "Get SQL Query":
            with st.spinner('Generating SQL query...'):
                sql_response = model_sql.generate_content(
                    sql_query_prompt,
                    generation_config=genai.GenerationConfig(
                        response_mime_type="application/json",
                        response_schema=Command,
                        temperature=0.3
                    )
                )
                ans = sql_response.text
                match = re.search(r'\"query\": \"(.*?)\"', ans)

                if match:
                    sql_query = match.group(1)
                else:
                    sql_query = "No SQL query found"
                st.chat_message("assistant", avatar="bot.png").write(f"SQL Query: {sql_query}")
                st.session_state.messages.append({"role": "assistant", "content": f"SQL Query: {sql_query}"})
