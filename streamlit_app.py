import gspread
from google.oauth2.service_account import Credentials
from pandasai.llm import OpenAI
import os
from pandasai import SmartDatalake
import pandas as pd
import streamlit as st
import matplotlib
import seaborn as sns
import matplotlib.pyplot as plt
from pandasai.responses.response_parser import ResponseParser
import json
from PIL import Image
from utils.openai_client import OpenAIClient

# Set backend before import pyplot (Do not show a new windows after plotting)
matplotlib.use("Agg", force=True)
#Set "seaborn" theme
sns.set_theme(style="whitegrid", palette="pastel",
              context="paper", font_scale=1.5)
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
if 'dataframes' not in st.session_state: #If data loaded
    st.session_state['dataframes'] = None
if 'is_first_loading' not in st.session_state:
    st.session_state['is_first_loading'] = True
if "messages" not in st.session_state:
    st.session_state['messages'] = []
if 'has_erd'not in st.session_state:
    st.session_state['has_erd'] = False
if 'last_prompt' in st.session_state:
    st.session_state['last_prompt'] = ""    


def reset_state_after_loading_data():
    print('Call:reset_state_after_loading_data()')
    st.session_state['messages'] = []
    st.session_state['is_first_loading'] = True
    st.session_state['has_erd'] = False


# === LOCAL FUNCTIONS =====
class MyStResponseParser(ResponseParser):
    def __init__(self, context) -> None:
        super().__init__(context)

    def parse(self, result):
        # print(f"Response Parser: Other Format: {result}")        
        content_type = result['type']
        content = result['value']
        print(f"DEBUG:ResponseParser:ContentType:{content_type}, content:{content}")

        #Rewrite the answer of pandasai before answering for user
        if (content_type == 'plot') or (content_type == 'image'):
            original_image = Image.open(content)
            append_messages(role="assistant",content=original_image, type=content_type)
            return
        elif (content_type == 'number') or (content_type == 'str'):
            content = client.rewirte_answer(st.session_state['last_prompt'],content)
        append_messages(role="assistant",content=content, type=content_type)           
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


# === Working with Messages =====
def show_welcome_messages():
    dataframes = st.session_state['dataframes']
    if not st.session_state['has_erd']:
        content1 = f'''**Skill 1** : UNDERSTANDING data and UNRAVELING the mysteries of table relationships!
                        \n Total number of sheet(s): **{len(dataframes)}**'''
        content2 = '''**Skill 2**: DRAWING the relationship amongs sheets (UML format)...'''
        append_messages('assistant', content1, "string")
        append_messages('assistant', content2, "string")

        # Create UML
        img_path = client.create_uml_from_dataframe(dataframes=dataframes)
        append_messages('assistant', img_path, "image")
        st.session_state['has_erd'] = True
    return

def append_messages(role="user", content=any, type="string"):
    message = {"role": role, "content": content, "type": type}
    st.session_state['messages'].append(message)
    show_message(message)

def show_message(message):
    with st.chat_message(message['role']):
        if message['type'] == "dataframe":
            st.dataframe(message['content'])
        elif message['type'] == 'plot':
            st.image(message["content"])
        elif message['type'] == 'image':
            # img = Image.open(message["content"]) #load from folder
            st.image(message["content"])
        elif message['type'] == 'markdown':
            st.markdown(message["content"])
        else:
            st.write(message["content"])

def show_all_messages():    
    messages = st.session_state['messages']
    for message in messages:
        show_message(message)
    return len(messages)

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
                    st.session_state['dataframes'] = dataframes                    
                    st.info("**👌 Load Successful! Ready to chat**")
                except Exception as e:
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
                # Create UML
                img_path = client.create_uml_from_dataframe(dataframes=dataframes)
                append_messages('assistant', img_path, "image")
                st.session_state['has_erd'] = True
            st.session_state['is_first_loading'] = False    
    

    # Get input from user. Sampe: "How many transaction users of company ANNAM"
    prompt = st.chat_input(" 🗣️ Chat with Data",)
    if prompt is not None:
        st.session_state['last_prompt'] = prompt
        if dataframes is not None:                        
            append_messages(role="user",content=prompt,type="string")
            try:                                
                agent = SmartDatalake(dataframes,
                                        config={
                                            "llm": llm,
                                            "conversational": False,
                                            "response_parser": MyStResponseParser,
                                        })
                agent.chat(prompt)                 
            except Exception as e:
                print(f'CallPansasException:Exception:{e}')


if __name__ == "__main__":    
    main_sidebar()
    if st.session_state['dataframes']:
        main_page()
    else:
        st.title('How Gabby Work')
        st.image('gabby.jpeg')
    

