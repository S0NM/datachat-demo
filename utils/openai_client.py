from openai import OpenAI
import os
import plantuml
import re

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

    def rewirte_answer(self, question, answer):
        response = self.send_chat_completion(f"{answer} is the answer of the question: {question}. Rewrite that answer in the most user-friendly sentence. Answer in the same language with the question")
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

