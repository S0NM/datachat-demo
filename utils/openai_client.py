from openai import OpenAI
import os
import plantuml
import re
import json

class OpenAIClient:
    def __init__(self):
        self.token = os.getenv('OPENAI_API_KEY')
        self.client = OpenAI()

    def _create_texts(self, df):
        column_names = ', '.join(df.columns)
        column_name_texts = f"Data Frame has column names: \n {column_names}"    
        rows = df.head(3).apply(lambda x: ', '.join(x.astype(str)), axis=1)
        row_texts = "Some example rows according to Data Frame are: "

        for index, row in enumerate(rows):
            row_texts = f"{row_texts} \n Row {index+1}: {rows[index+1]}"
        return f"{column_name_texts} \n {row_texts}"

    # Cai dat: pip install plantuml
    def _create_plantuml_image(self, uml_code, filename):
        puml = plantuml.PlantUML(url='http://www.plantuml.com/plantuml/img/')

        # Tạo file ảnh từ mã UMLç
        with open("./cache/"+filename + ".puml", "w") as file:
            file.write(uml_code)

        # Tạo ảnh và lưu kết quả
        result = puml.processes_file("./cache/"+filename + ".puml")
        if result:
            print(
                f'''PlantUML Image created sucessfully, stored at "./cache/" {filename}.png''')
        else:
            print("Plant UML Imange created FAILED")

    # ============== PROCESSING chat message ========================
    def send_chat_completion(self, message):
        completion = self.client.chat.completions.create(
            model="gpt-3.5-turbo", messages=[{"role": "user", "content": message}])
        return completion.choices[0].message.content
    
    def get_metadata_description(self,dfs):
        dfs_description = ''
        for df in dfs:
            dfs_description = dfs_description + " [" + self._create_texts(df)+"]"
        message = f'Based on my description about all dataframe: {dfs_description}. Adding description for all fields by predicting the meaning of each. If any field is datetime, please predict and add date/time format into its description. Answer in JSON format only without any explaination. Seperate each dataframe in a JSON item'
        # print(f'DEFBUG:get_metadata_description:Message:{message}')
        response = self.send_chat_completion(message)
        # print(f'DEFBUG:get_metadata_description:Response:{response}')
        response_json = json.loads(response)
        data_items = list(response_json.items())
        descriptions = []
        for index in range(0,len(data_items)):
            descriptions.append(data_items[index][1])
        # print(f'DEFBUG:get_metadata_description:Description:{descriptions}')
        return descriptions

    def create_5_suggestive_questions(self,dfs):
        metadata = self.get_metadata_description(dfs)
        dfs_description = ''
        for df in dfs:
            dfs_description = dfs_description + " [" + self._create_texts(df) + "]"
        prompt = (f"""My input data is described as follows:
        ---- Metadata information ----
        {metadata}
        ---- Sample data ----
        {dfs_description}
        ----
        Please create and return to me a list of 5 simple questions for querying data based on the example data of the described fields. As you are unaware of the exact timeframe, refrain from questions related to time data. Your answer should be formatted as JSON, each element contains only one question""")
        response = self.send_chat_completion(prompt)
        return response

    def rewirte_answer(self, question, answer):
        response = self.send_chat_completion(f"{answer} is the answer of the question: {question}. Rewrite that answer in the most user-friendly sentence")
        return response

    #Return image path: 'cache/planuml_img.png
    def create_uml_from_dataframe(self,dataframes):
        prompt = f'''Create a ER Diagram by using plantuml code and my description. Don't need to embed sample data in the code. {
            [self._create_texts(df) for df in dataframes]}.Answer code only without any explaination'''        
        completion = self.send_chat_completion(prompt)
        
        #Create PlantUML
        try:
            my_content = completion
            pattern = re.compile(r"@startuml.*?@enduml", re.DOTALL)
            matches = pattern.findall(my_content)
            if len(matches) > 0:
                self._create_plantuml_image(
                    matches[0], 'plantuml_img')
                return 'cache/plantuml_img.png'                
        except Exception as e:
            print(
                f"EXCEPTION:OpenAIClient:create_uml_from_dataframe()::{e}")

