import gspread
from google.oauth2.service_account import Credentials
from pandasai.llm import OpenAI
import os
from pandasai import SmartDatalake
import pandas as pd
import streamlit as st
from pandasai.helpers.openai_info import get_openai_callback
import matplotlib
from pandasai.responses.response_parser import ResponseParser
from openai import OpenAI as OpenAI2
import plantuml
import re
import json

# Set backend before import pyplot (Do not show a new windows after plotting)
matplotlib.use("Agg", force=True)
env_openai_key = "OPENAI_API_KEY"
env_google_key = "GS_ACCOUNT_JSON"

# === INIT CONFIGURATION =====
if env_openai_key not in  os.environ:
    os.environ["OPENAI_API_KEY"] = st.secrets['OPENAI_API_KEY']
llm = OpenAI()
client = OpenAI2()
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
    st.session_state['is_first_loading'] = False
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
    st.session_state['is_first_loading'] = False
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


def create_texts(df):
    column_names = ', '.join(df.columns)
    column_name_texts = f"Data Frame has column names: \n {column_names}"
    print(column_name_texts)
    rows = df.head(3).apply(lambda x: ', '.join(x.astype(str)), axis=1)
    print(f'ROWS: {rows[1]}')

    row_texts = "Some example rows according to Data Frame are: "    
    
    for index, row in enumerate(rows):
        row_texts = f"{row_texts} \n Row {index+1}: {rows[index+1]}"
    return f"{column_name_texts} \n {row_texts}"


# Cai dat: pip install plantuml
def create_plantuml_image(uml_code, filename):
    print(f'create_plantuml_image:UML_CODE: {uml_code}')
    puml = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')

    # Tạo file ảnh từ mã UMLç
    with open(filename + ".puml", "w") as file:
        file.write(uml_code)

    # Tạo ảnh và lưu kết quả
    result = puml.processes_file(filename + ".puml")
    if result:
        print(f"Ảnh đã được tạo thành công và lưu tại {filename}.png")
    else:
        print("Không thể tạo ảnh.")


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
                st.image(message["content"])
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
        if (len(dataframes) > 0) & (not is_first_loading):
            # with st.chat_message("assistant"):
                # Create UML
            if not st.session_state['has_erd']:
                content1 = f'''**Skill 1** : UNDERSTANDING data and UNRAVELING the mysteries of table relationships!
                        \n Total number of sheet(s): **{len(dataframes)}**'''
                content2 = '''**Skill 2**: DRAWING the relationship amongs sheets (UML format)...'''
                append_messages(role='assistant',content=content1, type="string")
                append_messages(role='assistant',content=content2, type="string")
                
                prompt = f'''Create a ER Diagram by using plantuml code and my description. Don't need to embed sample data in the code. {[create_texts(df) for df in dataframes]}.Answer code only without any explaination'''
                
                completion = client.chat.completions.create(
                    model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
                try:
                    my_content = completion.choices[0].message.content
                    pattern = re.compile(r"@startuml.*?@enduml", re.DOTALL)
                    matches = pattern.findall(my_content)
                    if len(matches) >0:
                        create_plantuml_image(matches[0], 'plantuml_img')
                        append_messages(role="assistant",
                                        content='plantuml_img.png', type="image")
                        st.session_state['has_erd'] = True
                except Exception as e:
                    st.write(f"**😢 Ops! Error!** Exception Tracing:{e}")
                # with st.chat_message("assistant"):
                #     st.code('Tổng số tiền giao dịch trong tháng là bao nhiêu')
                #     st.code('Ai là người có số giao dịch nhiều nhất')
                #     st.code('Vẽ biểu đồ pie chart so sánh số lượng giao dịch của từng người dùng')

    # Show history messages based on message type
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
                                           "response_parser": MyStResponseParser
                                       })
                agent.chat(prompt)

    # Create some suggestion button
   

if __name__ == "__main__":    
    main_sidebar()
    if st.session_state['data_loaded']:
        main_page()

