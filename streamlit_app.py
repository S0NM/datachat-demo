# Follow steps on the video: https://www.youtube.com/watch?v=hEPoto5xp3k&ab_channel=CodingIsFun
#pip install streamlit-option-menu
#You can find more icons from here: https://icons.getbootstrap.com/

import streamlit as st
from streamlit_option_menu import option_menu
import altair as alt

# Add custom CSS to hide the GitHub icon
hide_github_icon = """
#GithubIcon {
  visibility: hidden;
}
"""
st.markdown(hide_github_icon, unsafe_allow_html=True)

# load a sample dataset as a pandas DataFrame
from vega_datasets import data
cars = data.cars()

# 1.Vertical Menu
options = ["Basic Components", "Altair Charts", "Camera Input"]
with st.sidebar:
    selected = option_menu(
        menu_title="Main Menu",
        options=options,
        icons= ["house","book","envelope"],
        menu_icon="cast"
    )

st.title(f"you have selected {selected}")

if selected == options[0]:
    #Cliked button demo
    clicked1 = st.button("Click me, First!")
    st.write("Button Status:", clicked1)
    clicked2 = st.button("Click me, Second!")
    st.write("Button Status:", clicked2)

    #metric
    st.metric(label="Active Users", value="24.4123", delta="-8%",)
    st.json({'title': 'Building Blocks Deluxe Set', 'short_description': 'Unleash your creativity with this deluxe set of building blocks for endless fun.', 'price': 34.99, 'category': 'Toys', 'features': [
        'Includes 500+ colorful building blocks', 'Promotes STEM learning and creativity', 'Compatible with other major brick brands', 'Comes with a durable storage container', 'Ideal for children ages 3 and up']})
elif selected == options[1]:    
    chart = alt.Chart(cars).mark_point().encode(
            x='Horsepower',
            y='Miles_per_Gallon',
            color='Origin',
        ).interactive()
    tab1, tab2 = st.tabs(["Streamlit theme (default)", "Altair native theme"])

    with tab1:
        # Use the Streamlit theme.
        # This is the default. So you can also omit the theme argument.
        st.altair_chart(chart, theme="streamlit", use_container_width=True)
    with tab2:
        # Use the native Altair theme.
        st.altair_chart(chart, theme=None, use_container_width=True)
elif selected == options[2]:
    photo = st.camera_input("Take a picture")
    if photo:
        st.image(photo)



