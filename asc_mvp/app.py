import pandas as pd
import streamlit as st

df = pd.read_csv("data/ascs.csv")

st.dataframe(df)