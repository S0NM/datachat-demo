# Data Copilot: Implementing my first idea

## Demo
* Data Copilot Demo: https://elinson-chatapp.streamlit.app/
<img width="600" alt="image" src="mydemo.gif">

## Objectives 
Data Copilot: My goal is to create an assistant that helps me quickly access to product data. **Why?** There are two reasons:
* 1) I need rapid, anytime **access to 360-degree information** of feature performance & operation (I am the Product Manger)
* 2) I have worked directly with ChatGPT and encountered several limitations:
	* ChatGPT does not allow me to handle Google Sheets directly
	* Uploading and processing data with ChatGPT is a costly (tokens), time-consuming process, and sometimes the risk of having to share data is inevitable --> **I need a cheaper, more secure solution**


## What's in this project?
During my research, I discovered PandasAI (a fantastic library, which I recommend to anyone with similar goals) and to help you quickly get started, I created a demo project on Streamlit. You can freely download and explore it.
* **How to Combine PandasAI + ChatGPT + Streamlit**
	* Streamlit: allows you to build chat interfaces very quickly
	* Basic techniques with PandasAI
		* PandasAI only sends metadata instead of the full data set -> no worries about data leak risks
		* How to handle the response and display it on Streamlit
* **How to use ChatGPT and PlanUML to draw ER Diagrams** (I use it to check if ChatGPT really understands the relationships between data tables, as a misunderstanding could lead to incorrect processing)
* **How to work with Google Sheets**

<img width="600" alt="image" src="https://github.com/S0NM/datachat-demo/assets/31585927/45f769b8-d64f-479c-bb6e-69c78b6d17ff">


## Self-Deployment Note
You have to create two environment variables to store the OPENAI_API_KEY and the Credentials information when connecting to Google Sheets before running
```
export OPENAI_API_KEY="sk-iOZXf..................gqObIX5cd8Z"
export GS_ACCOUNT_JSON='{"type":"service_account","project_id":"...........,"universe_domain":"googleapis.com"}'
```

## Next
* Update after I have more time and further develop my idea
<img width="400" alt="image" src="https://github.com/S0NM/datachat-demo/assets/31585927/fc70141c-21e0-46fb-b114-a6e090d67f93">

