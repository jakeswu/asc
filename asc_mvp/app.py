import streamlit as st
import pandas as pd

st.title("WA ASC Intelligence")

df = pd.read_csv("asc_mvp/data/ascs.csv")

st.dataframe(df)
