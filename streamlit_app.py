import gspread
from google.oauth2.service_account import Credentials
from pandasai.llm import OpenAI
import os
from pandasai import SmartDatalake
import pandas as pd
import streamlit as st
import matplotlib
from pandasai.responses.response_parser import ResponseParser
import re
import json
from PIL import Image
from utils.openai_client import OpenAIClient

# Set backend before import pyplot (Do not show a new windows after plotting)
matplotlib.use("Agg", force=True)
env_openai_key = "OPENAI_API_KEY"
env_google_key = "GS_ACCOUNT_JSON"

# === INIT CONFIGURATION =====
if env_openai_key not in  os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets['OPENAI_API_KEY']
llm = OpenAI()
client = OpenAIClient()
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
if 'data_loaded' not in st.session_state: #If data loaded
    st.session_state['data_loaded'] = False
if 'is_first_loading' not in st.session_state:
    st.session_state['is_first_loading'] = True
if "messages" not in st.session_state:
    st.session_state['messages'] = []
if 'df' not in st.session_state:
    st.session_state['df'] = None
if 'has_erd'not in st.session_state:
    st.session_state['has_erd'] = False
df = st.session_state['df']

def reset_state_after_loading_data():
    print('Call:reset_state_after_loading_data()')
    st.session_state['messages'] = []
    st.session_state['is_first_loading'] = True
    st.session_state['has_erd'] = False


# === LOCAL FUNCTIONS =====
# Xử lý các loại format của response trả về
class MyStResponseParser(ResponseParser):
    def __init__(self, context) -> None:
        super().__init__(context)

    def parse(self, result):
        # print(f"Response Parser: Other Format: {result}")

        #Save into session state
        append_messages(role="assistant",content=result['value'], type=result['type'])        
        if result['type'] == "dataframe":
            # Fix: loi bi trung lap cot "count"
            df = result['value']
            duplicate_columns = df.columns[df.columns.duplicated(keep=False)]
            if not duplicate_columns.empty:
                df.columns = ['item'] + df.columns[1:].tolist()
            st.dataframe(result['value'])
        elif result['type'] == 'plot':
            st.image(result["value"])
        else:
            st.write(result['value'])
        return

#Load multiple sheets into a list of dataframe
def load_datalake_from_googleshset(url):
    # Save into a Google Sheet
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
        df.columns = df.iloc[0]  # Đặt hàng đầu tiên làm header
        df = df.iloc[1:]  # Loại bỏ hàng header khỏi dữ liệu
        dataframes.append(df)

    return dataframes


def append_messages(role="user", content=any, type="string"):
    st.session_state['messages'].append(
        {"role": role, "content": content, "type": type})

def get_all_messages():
    return st.session_state['messages']

def render_messages(messages):
    for message in messages:
        with st.chat_message(message['role']):
            if message['type'] == "dataframe":
                st.dataframe(message['content'])
            elif message['type'] == 'plot':
                st.image(message["content"])
            elif message['type'] == 'image':
                img = Image.open(message["content"]) #load from folder
                st.image(img)
            elif message['type'] == 'markdown':
                st.markdown(message["content"])
            else:
                st.write(message["content"])

# === MAIN PAGE =====
def main_sidebar():
    with st.sidebar:
        #Sidebar components
        st.title(" Hello, I'm GabbyGPT !")
        st.image('chat_with_data.png')
        st.info("**Yo Guys! Start here ↓**", icon="👋🏾")
        url = st.text_input("👇 Paste your 'Google Sheet Link' below...!",
                            value=GS_URL, key="load_data_clicked")
        #check url
        if url != "":
            #Click loading button
            if st.button("Load Data"):
                reset_state_after_loading_data()                
                try: 
                    dataframes = load_datalake_from_googleshset(url)                
                    st.session_state['data_loaded'] = True
                    st.session_state['df'] = dataframes
                    st.info("**👌 Load Successful! Ready to chat**")
                except Exception as e:
                    st.session_state['data_loaded'] = False
                    st.warning(
                        "**😢 Ops! Error! I have NO DATA** \n\n I'm waiting... 👆")
        else:
            st.session_state['data_loaded'] = False
            st.warning("👆 Please input URL ")


def show_first_messages():
    dataframes = st.session_state['df']
    if not st.session_state['has_erd']:
        content1 = f'''**Skill 1** : UNDERSTANDING data and UNRAVELING the mysteries of table relationships!
                        \n Total number of sheet(s): **{len(dataframes)}**'''
        content2 = '''**Skill 2**: DRAWING the relationship amongs sheets (UML format)...'''
        
        with st.chat_message('assistant'):
           st.write(content1)           
           append_messages('assistant', content1,"string")
        yield 
        
        with st.chat_message('assistant'):
           st.write(content2)
           img_path = client.create_uml_from_dataframe(dataframes=dataframes)
           st.image(img_path)
           append_messages('assistant', content2, "string")
           append_messages('assistant', img_path, "image")
        yield 
        
        # Finding insights
        with st.chat_message('assistant'):
           content3 = '''**Skill 3**: I'm FINDING Insights from your data... '''
           st.write(content3)
           question = "Perform insights analysis based on your input data "
           agent = SmartDatalake(dataframes,
                              config={
                                  "llm": llm,
                                  "conversational": False
                              })
           answer = agent.chat(question)
           content4 = "OK! Let's your turn. Ask me anything."
           formated_answer = client.rewirte_answer(question, answer)
           st.write(f'{formated_answer} \n\n {content4}')
           append_messages('assistant', f'''{content3} \n\n {formated_answer} \n\n {content4}''', "string")
        st.session_state['has_erd'] = True
        yield 
        

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
    dataframes = st.session_state['df']
    is_first_loading = st.session_state['is_first_loading']

    # Show first message (after loading data successfully)
    if st.session_state['data_loaded']:
        if (len(dataframes) > 0) & (is_first_loading):
            for message in show_first_messages():
                pass
            st.session_state['is_first_loading'] = False
    
    # Show history messages based on message type
    if (not is_first_loading):
        messages = get_all_messages()
        render_messages(messages=messages)

    # Get input from user. Sampe: "How many transaction users of company ANNAM"
    prompt = st.chat_input(" 🗣️ Chat with Data",)
    if prompt is not None:
        if dataframes is not None:
            # Show message
            with st.chat_message('user'):
                st.write(prompt)
            append_messages(role="user",content=prompt,type="string")
            with st.chat_message("assistant"):
                agent = SmartDatalake(dataframes,
                                       config={
                                           "llm": llm,
                                           "conversational": False,
                                           "response_parser": MyStResponseParser,
                                       })
                agent.chat(prompt)

    # Create some suggestion button
   

if __name__ == "__main__":    
    main_sidebar()
    if st.session_state['data_loaded']:
        main_page()
    else:
        st.title('How Gabby Work')
        st.image('gabby.jpeg')
    

