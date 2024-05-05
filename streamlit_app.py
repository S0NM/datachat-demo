import gspread
from google.oauth2.service_account import Credentials
from typing import Union
from pandasai.llm import OpenAI
import os
from pandasai import SmartDatalake
import pandas as pd
import streamlit as st
import seaborn as sns
from pandasai.responses.response_parser import ResponseParser
import json
from PIL import Image
from utils.openai_client import OpenAIClient

# Set backend before import pyplot (Do not show a new windows after plotting)
# matplotlib.uses("Agg", force=True)
# Set "seaborn" theme
sns.set_theme(style="whitegrid", palette="pastel", context="paper", font_scale=1.5)
env_openai_key = "OPENAI_API_KEY"
env_google_key = "GS_ACCOUNT_JSON"

# === INIT CONFIGURATION =====
if env_openai_key not in os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets['OPENAI_API_KEY']
pandas_client = OpenAI()
pandas_client.model="gpt-4"
openai_client = OpenAIClient()
if env_google_key not in os.environ:
    GS_ACCOUNT_JSON = st.secrets[env_google_key]
else:
    GS_ACCOUNT_JSON = os.environ[env_google_key]
GS_ACCOUNT_PATH = 'google_sheet_account.json'
GG_SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
GS_URL = 'https://docs.google.com/spreadsheets/d/11AqzXaJbt5yHgoP0x4lt1M-sTDlvYee9C1syTASHyhM/edit?usp=sharing'

# Set Page config
st.set_page_config(
    layout="wide",
    initial_sidebar_state="expanded"
)

# === INIT STATE ===
if 'dataframes' not in st.session_state:  # If data loaded
    st.session_state['dataframes'] = None
if 'dataframes_description' not in st.session_state:
    st.session_state['dataframes_description'] = None
if 'is_first_loading' not in st.session_state:
    st.session_state['is_first_loading'] = True
if "last_prompt" not in st.session_state:
    st.session_state['last_prompt'] = None
if "messages" not in st.session_state:
    st.session_state['messages'] = []
if "question_selected" not in st.session_state:
    st.session_state['question_selected'] = None
if 'has_erd' not in st.session_state:
    st.session_state['has_erd'] = False


def reset_state_after_loading_data():
    print('Call:reset_state_after_loading_data()')
    st.session_state['messages'] = []
    st.session_state['is_first_loading'] = True
    st.session_state['has_erd'] = False
    st.session_state['last_prompt'] = None


# === LOCAL FUNCTIONS =====
class MyStResponseParser(ResponseParser):
    def __init__(self, context) -> None:
        super().__init__(context)

    def parse(self, result):
        # print(f"Response Parser: Other Format: {result}")        
        content_type = result['type']
        content = result['value']
        print(f"DEBUG:ResponseParser:ContentType:{content_type}, content:{content}")

        # Rewrite the answer of pandasai before answering for user
        if (content_type == 'plot') or (content_type == 'image'):
            original_image = Image.open(content)
            append_messages(role="assistant", content=original_image, type=content_type)
            return
        elif (content_type == 'number') or (content_type == 'str'):
            last_prompt = st.session_state['last_prompt']
            print(f'DEBUG:MyStResponseParser:{last_prompt}')
            content = openai_client.rewirte_answer(last_prompt, content)
        append_messages(role="assistant", content=content, type=content_type)
        return


def load_datalake_from_googlesheet(url:str):
    """
    Load data from Google Sheet and return it as list of dataframe

    :param url:Google sheet url
    :return: list of dataframe
    """

    # Load google sheet account configuration
    if os.path.exists('google_sheet_account.json'):
        print("Load GG Credential from files")
        gs_account = gspread.service_account(filename=GS_ACCOUNT_PATH)
    else:
        print("Load GG Credential from JSON")
        creds = Credentials.from_service_account_info(json.loads(GS_ACCOUNT_JSON), scopes=GG_SCOPES)
        gs_account = gspread.auth.authorize(creds)
    gs_sheet = gs_account.open_by_url(url)

    # A list of dataframe
    dataframes = []
    for sheet in gs_sheet.worksheets():
        data = sheet.get_all_values()
        # Convert into DataFrame
        df = pd.DataFrame(data)
        df.columns = df.iloc[0]  # Assign first row as header
        df = df.iloc[1:]  # Remove first row from dataframe
        dataframes.append(df)
    return dataframes


# === Working with Messages =====
def show_welcome_messages():
    dataframes = st.session_state['dataframes']
    if not st.session_state['has_erd']:
        st.session_state['has_erd'] = True

        content1 = f'''**Skill 1** : UNDERSTANDING data and UNRAVELING the mysteries of table relationships!
                        \n Total number of sheet(s): **{len(dataframes)}**'''
        content2 = '''**Skill 2**: DRAWING the relationship amongs sheets (UML format)...'''
        append_messages('assistant', content1, "string")
        append_messages('assistant', content2, "string")

        # Create UML
        img_path = openai_client.create_uml_from_dataframe(dataframes=dataframes)
        append_messages('assistant', img_path, "image")

        # Using ChatGPT to predict field description
        fields_description = openai_client.get_metadata_description(dataframes)
        st.session_state['dataframes_description'] = fields_description
        append_messages('assistant', fields_description, "string")
    return


def append_messages(role="user", content: Union[pd.DataFrame, Image, str] = "No Content", type="string"):
    message = {"role": role, "content": content, "type": type}
    st.session_state['messages'].append(message)
    show_message(message)

def show_message(message):
    """
    Render message content according to content type
    :param message: message to render
    """
    message_type_to_function = {
        "dataframe": st.dataframe,
        "plot": st.image,
        "image": st.image,
        "markdown": st.markdown,
        "questions": st.button
    }
    print(f"Debug:ShowMessage:Msg_Type:{message['type']}:Msg_value:{message['content']}")
    with st.chat_message(message['role']):
        func = message_type_to_function.get(message['type'], st.write)
        if message['type'] == "questions":
            questions = message['content']
            for key, value in questions.items():
                if st.button(label=value):
                    print(f"DEBUG:Selected Question: {value}")
                    st.session_state['question_selected'] = value
        else:
            func(message['content'])


def show_all_messages():
    messages = st.session_state['messages']
    for message in messages:
        show_message(message)
    return len(messages)

def send_prompt(prompt):
    dataframes = st.session_state['dataframes']
    append_messages(role="user", content=prompt, type="string")
    with st.spinner("Running..."):
        try:
            agent = SmartDatalake(dataframes, config={
                "llm": pandas_client,
                "conversational": True,
                "response_parser": MyStResponseParser,
                "save_logs": True
            }, )
            st.session_state['last_prompt'] = prompt
            agent.chat(prompt)
        except Exception as e:
            print(f'DEBUG:CallPansasException:Exception:{e}')


# === MAIN PAGE =====
def main_sidebar():
    with st.sidebar:
        # Sidebar components
        st.title(" Playground \n with \n **PandasAI & ChatGPT !**")
        st.image('pandasai.png')
        st.info("**Yo Guys! Start here ↓**", icon="👋🏾")
        url = st.text_input("👇 Paste your 'Google Sheet Link' below...! or use my link instead", value=GS_URL, key="load_data_clicked")

        if url != "":
            # Event: "Loading Button" Clicked
            if st.button("Let's Start Here"):
                reset_state_after_loading_data()
                try:
                    dataframes = load_datalake_from_googlesheet(url)
                    st.session_state['dataframes'] = dataframes
                    st.info("**👌 Load Successful! Ready to chat**")
                except Exception:
                    st.session_state['dataframes'] = None
                    st.warning(
                        "**😢 Ops! Error! I have NO DATA** \n\n I'm waiting... 👆")
        else:
            st.warning("👆 Please input URL ")


def main_page():
    header = st.container()
    header.title("🍻 :rainbow[Let's chat... !]")
    header.write("""<div class='fixed-header'/>""", unsafe_allow_html=True)

    # Custom CSS for the sticky header
    st.markdown(
        """
    <style>
        div[data-testid="stVerticalBlock"] div:has(div.fixed-header) {
            position: sticky;
            top: 2.875rem;
            background-color: white;
            z-index: 999;
        }
        .fixed-header {
            border-bottom: 1px solid black;
        }
    </style>   
        """,
        unsafe_allow_html=True
    )
    dataframes = st.session_state['dataframes']
    is_first_loading = st.session_state['is_first_loading']

    show_all_messages()
    # Show first message (after loading data successfully)
    if dataframes is not None:
        if is_first_loading:
            if not st.session_state['has_erd']:
                content1 = f'''**Skill 1** : UNDERSTANDING data and UNRAVELING the mysteries of table relationships!
                                \n Total number of sheet(s): **{len(dataframes)}**'''
                content2 = '''**Skill 2**: DRAWING the relationship amongs sheets (UML format)...'''
                append_messages('assistant', content1, "string")
                append_messages('assistant', content2, "string")
                with st.spinner("Running...."):
                    # Create UML
                    img_path = openai_client.create_uml_from_dataframe(dataframes=dataframes)
                    append_messages('assistant', img_path, "image")
                    st.session_state['has_erd'] = True

                # Generate some suggestion questions
                content3 = '''**Skill 3**: Based on your input Data. I will create some suggested questions:'''
                append_messages('assistant', content3, "string")
                with st.spinner("Running...."):
                    json_string = openai_client.create_5_suggestive_questions(dataframes)
                    print(json_string)
                    questions = json.loads(json_string)
                    append_messages('assistant', questions, "questions")

            st.session_state['is_first_loading'] = False
            # Get input from user. Sampe: "How many transaction users of company ANNAM"
    if st.session_state['question_selected'] is not None:
        prompt = st.session_state['question_selected']
        send_prompt(prompt)
        st.session_state['question_selected'] = None
    prompt = st.chat_input(" 🗣️ Chat with Data", )
    if prompt is not None:
        if dataframes is not None:
            send_prompt(prompt)


if __name__ == "__main__":
    main_sidebar()
    if st.session_state['dataframes']:
        main_page()
    else:
        st.title("What's in this project")
        st.markdown("""During my learning, I discovered PandasAI (a fantastic library, which I recommend to anyone with similar goals) and to help you quickly get started, I created a demo project on Streamlit. 
        You can freely download and explore it.Some interesting points you can find in this project:
* **How to Combine PandasAI + ChatGPT + Streamlit**
	* Streamlit: allows you to build chat interfaces very quickly
	* Basic techniques with PandasAI
		* PandasAI only sends metadata instead of the full data set -> no worries about data leak risks
		* How to handle the response and display it on Streamlit
* **How to use ChatGPT and PlanUML to draw ER Diagrams** (I use it to check if ChatGPT really understands the relationships between data tables, as a misunderstanding could lead to incorrect processing)
* **How to work with Google Sheets**""")
        st.image('mydemo.gif')

