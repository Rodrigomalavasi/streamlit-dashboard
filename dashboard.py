"""
Module: dashboard.

This module is responsible to renders a dashboard.
"""

import streamlit as st
import requests
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide")


URL = "https://labdados.com/produtos"
REGIONS = ["Brasil", "Centro-Oeste", "Nordeste", "Norte", "Sudeste", "Sul"]


def fetch_data(params: dict) -> pd.DataFrame:
    """
    Fetch data from the given URL with specified parameters.

    Args:
        params (dict): A dictionary of query parameters to include in the request.

    Returns:
        pd.DataFrame: A DataFrame containing the fetched data, or an empty DataFrame
                    if an error occurs during the request.
    """
    try:
        response = requests.get(URL, params=params)
        response.raise_for_status()  # Raise an error for bad responses (4xx or 5xx)
        return pd.DataFrame.from_dict(response.json())
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()  # Return an empty DataFrame in case of an error


def format_number(value: int | float, prefix="") -> str:
    """
    This function formats a numeric value into a string with appropriate units
    and an optional prefix. Values less than 1,000 are displayed as-is with two
    decimal places, while values from 1,000 to 999,999 are shown in thousands,
    and values of one million or more are displayed in millions.

    Args:
        value (int | float): The numeric value to be formatted.
        prefix (str): An optional prefix to be added before the formatted number.

    Returns:
        str: The formatted number as a string, including the prefix and appropriate unit.
    """
    for unit in ["", "mil"]:
        if value < 1000:
            return f"{prefix} {value:.2f} {unit}"
        value /= 1000

    return f"{prefix} {value:.2f} million"


st.sidebar.title("Filters", anchor=False)
region: str = st.sidebar.selectbox("Regions", REGIONS)

if region == "Brasil":
    region = ""

every_year: bool = st.sidebar.checkbox("Data for the entire period", value=True)

if every_year:
    year = 0
else:
    year: int = st.sidebar.slider("Ano", 2020, 2023)

query_string = {"regiao": region.lower(), "ano": year if not every_year else 0}

datas = fetch_data(query_string)
datas["Data da Compra"] = pd.to_datetime(datas["Data da Compra"], format="%d/%m/%Y")

seller_filter: str = st.sidebar.multiselect(
    "Sellers", datas["Vendedor"].unique(), placeholder="Sellers"
)
if seller_filter:
    datas = datas[datas["Vendedor"].isin(seller_filter)]

monthly_income = (
    datas.set_index("Data da Compra")
    .groupby(pd.Grouper(freq="M"))["Preço"]
    .sum()
    .reset_index()
)
monthly_income["Ano"] = monthly_income["Data da Compra"].dt.year
monthly_income["Mes"] = monthly_income["Data da Compra"].dt.month_name()

income_by_category = (
    datas.groupby("Categoria do Produto")[["Preço"]]
    .sum()
    .sort_values("Preço", ascending=False)
)

st.title("SALES DASHBOARD :shopping_trolley:", anchor=False)

## Tables
### Income tables
income_of_the_states = datas.groupby("Local da compra")[["Preço"]].sum()
income_of_the_states = (
    datas.drop_duplicates(subset="Local da compra")[["Local da compra", "lat", "lon"]]
    .merge(income_of_the_states, left_on="Local da compra", right_index=True)
    .sort_values("Preço", ascending=False)
)

### Sales quantity tables
vendas_estados = pd.DataFrame(datas.groupby("Local da compra")["Preço"].count())
vendas_estados = (
    datas.drop_duplicates(subset="Local da compra")[["Local da compra", "lat", "lon"]]
    .merge(vendas_estados, left_on="Local da compra", right_index=True)
    .sort_values("Preço", ascending=False)
)

vendas_mensal = pd.DataFrame(
    datas.set_index("Data da Compra").groupby(pd.Grouper(freq="M"))["Preço"].count()
).reset_index()
vendas_mensal["Ano"] = vendas_mensal["Data da Compra"].dt.year
vendas_mensal["Mes"] = vendas_mensal["Data da Compra"].dt.month_name()

vendas_categorias = pd.DataFrame(
    datas.groupby("Categoria do Produto")["Preço"].count().sort_values(ascending=False)
)

### Seller table
vendedores = pd.DataFrame(datas.groupby("Vendedor")["Preço"].agg(["sum", "count"]))

## Graphs
fig_map_income = px.scatter_geo(
    income_of_the_states,
    lat="lat",
    lon="lon",
    scope="south america",
    size="Preço",
    template="seaborn",
    hover_name="Local da compra",
    hover_data={"lat": False, "lon": False},
    title="Income by state",
)

fig_monthly_income = px.line(
    monthly_income,
    x="Mes",
    y="Preço",
    markers=True,
    range_y=(0, monthly_income.max()),
    color="Ano",
    line_dash="Ano",
    title="Monthly income",
)

fig_monthly_income.update_layout(yaxis_title="Receita")

fig_income_of_the_states = px.bar(
    income_of_the_states.head(),
    x="Local da compra",
    y="Preço",
    text_auto=True,
    title="Top states (Income)",
)

fig_income_of_the_states.update_layout(yaxis_title="Income")

fig_income_by_categories = px.bar(
    income_by_category, text_auto=True, title="Income by categories"
)

fig_income_by_categories.update_layout(yaxis_title="Income")

fig_mapa_vendas = px.scatter_geo(
    vendas_estados,
    lat="lat",
    lon="lon",
    scope="south america",
    template="seaborn",
    size="Preço",
    hover_name="Local da compra",
    hover_data={"lat": False, "lon": False},
    title="Sales by state",
)

fig_vendas_mensal = px.line(
    vendas_mensal,
    x="Mes",
    y="Preço",
    markers=True,
    range_y=(0, vendas_mensal.max()),
    color="Ano",
    line_dash="Ano",
    title="Monthly sales amount",
)

fig_vendas_mensal.update_layout(yaxis_title="Sales quantity")

fig_vendas_estados = px.bar(
    vendas_estados.head(),
    x="Local da compra",
    y="Preço",
    text_auto=True,
    title="Top 5 states",
)

fig_vendas_estados.update_layout(yaxis_title="Sales quantity")

fig_vendas_categorias = px.bar(
    vendas_categorias, text_auto=True, title="Sales by categories"
)
fig_vendas_categorias.update_layout(showlegend=False, yaxis_title="Sales quantity")

## Streamlit visualization
tab1, tab2, tab3 = st.tabs(["Income", "Sales quantity", "Sellers"])
with tab1:
    coluna1, coluna2 = st.columns(2)
    with coluna1:
        st.metric("Income", format_number(datas["Preço"].sum(), "R$"))
        st.plotly_chart(fig_map_income, use_container_width=True)
        st.plotly_chart(fig_income_of_the_states, use_container_width=True)
    with coluna2:
        st.metric("Sales quantity", format_number(datas.shape[0]))
        st.plotly_chart(fig_monthly_income, use_container_width=True)
        st.plotly_chart(fig_income_by_categories, use_container_width=True)

with tab2:
    coluna1, coluna2 = st.columns(2)
    with coluna1:
        st.metric("Income", format_number(datas["Preço"].sum(), "R$"))
        st.plotly_chart(fig_mapa_vendas, use_container_width=True)
        st.plotly_chart(fig_vendas_estados, use_container_width=True)
    with coluna2:
        st.metric("Sales quantity", format_number(datas.shape[0]))
        st.plotly_chart(fig_vendas_mensal, use_container_width=True)
        st.plotly_chart(fig_vendas_categorias, use_container_width=True)

with tab3:
    qtd_vendedores = st.number_input("Number of sellers", 2, 10, 5)
    coluna1, coluna2 = st.columns(2)
    with coluna1:
        st.metric("Income", format_number(datas["Preço"].sum(), "R$"))
        fig_receita_vendedores = px.bar(
            vendedores[["sum"]]
            .sort_values("sum", ascending=False)
            .head(qtd_vendedores),
            x="sum",
            y=vendedores[["sum"]]
            .sort_values("sum", ascending=False)
            .head(qtd_vendedores)
            .index,
            text_auto=True,
            title=f"Top {qtd_vendedores} sellers (income)",
        )
        st.plotly_chart(fig_receita_vendedores)
    with coluna2:
        st.metric("Sales quantity", format_number(datas.shape[0]))
        fig_vendas_vendedores = px.bar(
            vendedores[["count"]]
            .sort_values("count", ascending=False)
            .head(qtd_vendedores),
            x="count",
            y=vendedores[["count"]]
            .sort_values("count", ascending=False)
            .head(qtd_vendedores)
            .index,
            text_auto=True,
            title=f"Top {qtd_vendedores} sellers (sales quantity)",
        )
        st.plotly_chart(fig_vendas_vendedores)
