import gspread
from pandasai.llm import OpenAI
import os
from pandasai import SmartDataframe
from pandasai.connectors import PandasConnector
import pandas as pd
import streamlit as st
from pandasai.helpers.openai_info import get_openai_callback
import matplotlib
from pandasai.responses.response_parser import ResponseParser
from openai import OpenAI as OpenAI2
import plantuml

# Set backend before import pyplot (Do not show a new windows after plotting)
matplotlib.use("Agg", force=True)

# === INIT CONFIGURATION =====
os.environ["OPENAI_API_KEY"] = st.secrets['OPENAI_API_KEY']
llm = OpenAI()
client = OpenAI2()
GS_ACCOUNT_PATH = 'google_sheet_account.json'
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
        # Debug
        # print(f"Response Parser: Other Format: {result}")

        #Save into session state
        st.session_state.messages.append({'role': "assistant", "type": result['type'], "content": result['value']})
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

# Load data in Google Sheet into DataFrame
def load_df_from_googleshset(url):
    # Save into a Google Sheet
    gs_account = gspread.service_account(filename=GS_ACCOUNT_PATH)
    gs_sheet = gs_account.open_by_url(url)

    # Get the first sheet
    # in case you want to select sheeet by name: workbook.worksheet('Sheet1')
    first_sheet = gs_sheet.get_worksheet(0)
    data = first_sheet.get_all_values()

    # Convert into DataFrame
    df = pd.DataFrame(data)
    df.columns = df.iloc[0]  # Đặt hàng đầu tiên làm header
    df = df.iloc[1:]  # Loại bỏ hàng header khỏi dữ liệu
    return df

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
    print(f'UML_CODE: {uml_code}')
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
                    df = load_df_from_googleshset(url)                
                    st.session_state['data_loaded'] = True
                    st.session_state['df'] = df                    
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
    df = st.session_state['df']    
    is_first_loading = st.session_state['is_first_loading']
    
    # Show first message (after loading data successfully)
    if st.session_state['data_loaded']:            
        if (len(df)> 0) & (not is_first_loading):
            with st.chat_message("assistant"):                
                # Create UML          
                if not st.session_state['has_erd']:
                    st.write(
                        f"I've got your DATA! The number of Record is: **{len(df)}** records")
                    st.write("The relationship between your data tables is shown in the figure below: ")
                    prompt = f"Create a ER Diagram by using plantuml code and my description. Don't need to embed sample data in the code. {create_texts(df)}.Answer code only without any explaination"
                    completion = client.chat.completions.create(
                        model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}])
                    my_content = completion.choices[0].message.content
                    create_plantuml_image(my_content, 'plantuml_img')
                    st.image('plantuml_img.png')
                    st.session_state['has_erd'] = True
    
    # Show history messages based on message type
    messages = st.session_state['messages']    
    for index,message in enumerate(messages):        
        with st.chat_message(message['role']):
            if message['type'] == "dataframe":
                st.dataframe(message['content'])
            elif message['type'] == 'plot':
                st.image(message["content"])
            else:
                # print(f'call me {index} and message: {message}')
                st.write(message["content"])
    
    # Get input from user. Sampe: "How many transaction users of company ANNAM"
    prompt = st.chat_input(" 🗣️ Chat with Data",)
    if prompt is not None:
        if df is not None:
            # Show message
            with st.chat_message('user'):
                st.write(prompt)
            st.session_state.messages.append({"role": "user", "content": prompt,"type": "string"})
            with st.chat_message("assistant"):                                                  
                agent = SmartDataframe(df,
                                    config={
                                        "llm": llm,
                                        "conversational": False,
                                        "response_parser": MyStResponseParser
                                    })                 
                agent.chat(prompt)                                          

if __name__ == "__main__":    
    main_sidebar()
    if st.session_state['data_loaded']:
        main_page()
