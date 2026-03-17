import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Nassau Candy — Profitability Analyzer",
    layout="wide",
    page_icon="💰"
)

# ─────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────
FILE_NAME = "nassau_candy_distributor.csv"

PRODUCT_FACTORY_MAP = {
    "Wonka Bar - Nutty Crunch Surprise":  "Lot's O' Nuts",
    "Wonka Bar - Fudge Mallows":          "Lot's O' Nuts",
    "Wonka Bar -Scrumdiddlyumptious":     "Lot's O' Nuts",
    "Wonka Bar - Milk Chocolate":         "Wicked Choccy's",
    "Wonka Bar - Triple Dazzle Caramel":  "Wicked Choccy's",
    "Laffy Taffy":                        "Sugar Shack",
    "SweeTARTS":                          "Sugar Shack",
    "Nerds":                              "Sugar Shack",
    "Fun Dip":                            "Sugar Shack",
    "Fizzy Lifting Drinks":               "Sugar Shack",
    "Everlasting Gobstopper":             "Secret Factory",
    "Hair Toffee":                        "The Other Factory",
    "Lickable Wallpaper":                 "Secret Factory",
    "Wonka Gum":                          "Secret Factory",
    "Kazookles":                          "The Other Factory",
}

# ─────────────────────────────────────────────────────────
# DATA LOADING & CLEANING
# ─────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    df = pd.read_csv(FILE_NAME)

    # Fix dates
    df['Order Date'] = pd.to_datetime(df['Order Date'], dayfirst=True)
    df['Ship Date']  = pd.to_datetime(df['Ship Date'],  dayfirst=True)

    # Fix numeric
    for col in ['Sales', 'Cost', 'Gross Profit', 'Units']:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # Fix missing
    df['Units'].fillna(df['Units'].median(), inplace=True)
    df.dropna(subset=['Sales', 'Gross Profit', 'Cost'], inplace=True)

    # Remove invalid
    df = df[df['Sales'] > 0]
    df = df[df['Units'] > 0]
    df = df[df['Cost']  > 0]

    # Fix spacing
    for col in ['Product Name', 'Division', 'Region', 'Ship Mode']:
        df[col] = df[col].str.strip()
    df['Product Name'] = df['Product Name'].str.replace(
        'Wonka Bar -Scrumdiddlyumptious',
        'Wonka Bar - Scrumdiddlyumptious'
    )

    # Remove duplicates
    df.drop_duplicates(inplace=True)

    # Add factory
    df['Factory'] = df['Product Name'].map(PRODUCT_FACTORY_MAP)

    # ── KPI Features ──────────────────────────────────────
    df['Gross Margin %']         = (df['Gross Profit'] / df['Sales']) * 100
    df['Profit per Unit']        = df['Gross Profit'] / df['Units']
    df['Revenue Contribution %'] = (df['Sales'] / df['Sales'].sum()) * 100
    df['Profit Contribution %']  = (df['Gross Profit'] / df['Gross Profit'].sum()) * 100
    df['Cost per Unit']          = df['Cost'] / df['Units']
    df['Sales per Unit']         = df['Sales'] / df['Units']
    df['Order Month']            = df['Order Date'].dt.month
    df['Order Year']             = df['Order Date'].dt.year

    # ── Margin Risk Flag ──────────────────────────────────
    avg_margin = df['Gross Margin %'].mean()
    df['Margin Risk'] = df['Gross Margin %'].apply(
        lambda x: '🔴 High Risk'   if x < avg_margin * 0.5
        else ('🟡 Medium Risk'     if x < avg_margin
        else '🟢 Healthy')
    )

    return df

# ─────────────────────────────────────────────────────────
# MAIN APP
# ─────────────────────────────────────────────────────────
st.title("💰 Nassau Candy Distributor — Product Line Profitability Analyzer")
st.caption(f"📂 Source: `{FILE_NAME}`  |  10,194 orders  |  15 products  |  3 divisions")

# Load data
with st.spinner("Loading and cleaning data..."):
    df = load_data()

# ── SIDEBAR FILTERS ───────────────────────────────────────
st.sidebar.header("🔧 Filters")

# Division filter
divisions = ["All"] + sorted(df['Division'].dropna().unique().tolist())
sel_division = st.sidebar.selectbox("Division", divisions)

# Region filter
regions = ["All"] + sorted(df['Region'].dropna().unique().tolist())
sel_region = st.sidebar.selectbox("Region", regions)

# Margin threshold
margin_threshold = st.sidebar.slider(
    "Minimum Gross Margin %", 0, 100, 0)

# Date range
min_date = df['Order Date'].min().date()
max_date = df['Order Date'].max().date()
date_range = st.sidebar.date_input(
    "Order Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)

# Apply filters
filtered = df.copy()
if sel_division != "All":
    filtered = filtered[filtered['Division'] == sel_division]
if sel_region != "All":
    filtered = filtered[filtered['Region'] == sel_region]
filtered = filtered[filtered['Gross Margin %'] >= margin_threshold]
if len(date_range) == 2:
    filtered = filtered[
        (filtered['Order Date'].dt.date >= date_range[0]) &
        (filtered['Order Date'].dt.date <= date_range[1])
    ]

# ── TOP KPI BANNER ────────────────────────────────────────
k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("📦 Total Orders",      f"{len(filtered):,}")
k2.metric("💵 Total Sales",       f"${filtered['Sales'].sum():,.0f}")
k3.metric("💰 Total Profit",      f"${filtered['Gross Profit'].sum():,.0f}")
k4.metric("📊 Avg Gross Margin",  f"{filtered['Gross Margin %'].mean():.1f}%")
k5.metric("📦 Total Units",       f"{filtered['Units'].sum():,.0f}")

st.divider()

# ── TABS ──────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Product Profitability Overview",
    "🏭 Division Performance",
    "💰 Cost vs Margin Diagnostics",
    "📈 Profit Concentration Analysis"
])

# ══════════════════════════════════════════════════════════
# TAB 1 — PRODUCT PROFITABILITY OVERVIEW
# ══════════════════════════════════════════════════════════
with tab1:
    st.subheader("📊 Product Level Profitability")

    # Product summary table
    prod_summary = filtered.groupby('Product Name').agg(
        Total_Sales      =('Sales',         'sum'),
        Total_Profit     =('Gross Profit',  'sum'),
        Total_Units      =('Units',         'sum'),
        Avg_Margin       =('Gross Margin %','mean'),
        Avg_Profit_Unit  =('Profit per Unit','mean'),
        Orders           =('Row ID',        'count'),
    ).reset_index().round(2)
    prod_summary = prod_summary.sort_values('Avg_Margin', ascending=False)
    prod_summary['Division'] = prod_summary['Product Name'].map(
        filtered.groupby('Product Name')['Division'].first())
    prod_summary['Factory'] = prod_summary['Product Name'].map(PRODUCT_FACTORY_MAP)

    c1, c2 = st.columns(2)

    with c1:
        # Gross Margin % by Product
        fig1 = px.bar(
            prod_summary.sort_values('Avg_Margin'),
            x='Avg_Margin', y='Product Name',
            orientation='h',
            color='Avg_Margin',
            color_continuous_scale='RdYlGn',
            title="📊 Gross Margin % by Product",
            labels={'Avg_Margin': 'Gross Margin %', 'Product Name': ''}
        )
        fig1.add_vline(x=filtered['Gross Margin %'].mean(),
                       line_dash="dot", line_color="red",
                       annotation_text="Avg Margin")
        st.plotly_chart(fig1, use_container_width=True)

    with c2:
        # Total Profit by Product
        fig2 = px.bar(
            prod_summary.sort_values('Total_Profit'),
            x='Total_Profit', y='Product Name',
            orientation='h',
            color='Total_Profit',
            color_continuous_scale='Blues',
            title="💰 Total Gross Profit by Product",
            labels={'Total_Profit': 'Total Profit ($)', 'Product Name': ''}
        )
        st.plotly_chart(fig2, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        # Profit per Unit
        fig3 = px.bar(
            prod_summary.sort_values('Avg_Profit_Unit'),
            x='Avg_Profit_Unit', y='Product Name',
            orientation='h',
            color='Avg_Profit_Unit',
            color_continuous_scale='Greens',
            title="💵 Profit per Unit by Product",
            labels={'Avg_Profit_Unit': 'Profit per Unit ($)', 'Product Name': ''}
        )
        st.plotly_chart(fig3, use_container_width=True)

    with c4:
        # Sales vs Profit bubble
        fig4 = px.scatter(
            prod_summary,
            x='Total_Sales',
            y='Avg_Margin',
            size='Total_Units',
            color='Division',
            hover_name='Product Name',
            title="🔮 Sales vs Margin (bubble = Units)",
            labels={'Total_Sales': 'Total Sales ($)',
                    'Avg_Margin': 'Gross Margin %'}
        )
        fig4.add_hline(y=filtered['Gross Margin %'].mean(),
                       line_dash="dot", line_color="red",
                       annotation_text="Avg Margin")
        st.plotly_chart(fig4, use_container_width=True)

    # Product Leaderboard Table
    st.subheader("🏆 Product Profitability Leaderboard")
    display_df = prod_summary[[
        'Product Name', 'Division', 'Factory',
        'Total_Sales', 'Total_Profit', 'Avg_Margin',
        'Avg_Profit_Unit', 'Total_Units', 'Orders'
    ]].copy()
    display_df.columns = [
        'Product', 'Division', 'Factory',
        'Total Sales ($)', 'Total Profit ($)', 'Avg Margin %',
        'Profit/Unit ($)', 'Total Units', 'Orders'
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Download button
    csv = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Download Product Summary",
        data=csv,
        file_name="product_profitability.csv",
        mime='text/csv'
    )

# ══════════════════════════════════════════════════════════
# TAB 2 — DIVISION PERFORMANCE
# ══════════════════════════════════════════════════════════
with tab2:
    st.subheader("🏭 Division Level Performance")

    div_summary = filtered.groupby('Division').agg(
        Total_Sales      =('Sales',          'sum'),
        Total_Profit     =('Gross Profit',   'sum'),
        Total_Cost       =('Cost',           'sum'),
        Total_Units      =('Units',          'sum'),
        Avg_Margin       =('Gross Margin %', 'mean'),
        Products         =('Product Name',   'nunique'),
        Orders           =('Row ID',         'count'),
    ).reset_index().round(2)
    div_summary['Revenue %'] = (
        div_summary['Total_Sales'] /
        div_summary['Total_Sales'].sum() * 100
    ).round(1)
    div_summary['Profit %'] = (
        div_summary['Total_Profit'] /
        div_summary['Total_Profit'].sum() * 100
    ).round(1)

    c1, c2 = st.columns(2)

    with c1:
        # Revenue vs Profit by Division
        fig5 = go.Figure()
        fig5.add_trace(go.Bar(
            name='Total Sales',
            x=div_summary['Division'],
            y=div_summary['Total_Sales'],
            marker_color='#2196F3'
        ))
        fig5.add_trace(go.Bar(
            name='Total Profit',
            x=div_summary['Division'],
            y=div_summary['Total_Profit'],
            marker_color='#4CAF50'
        ))
        fig5.update_layout(
            barmode='group',
            title="💵 Revenue vs Profit by Division",
            xaxis_title="Division",
            yaxis_title="Amount ($)"
        )
        st.plotly_chart(fig5, use_container_width=True)

    with c2:
        # Margin by Division
        fig6 = px.bar(
            div_summary,
            x='Division',
            y='Avg_Margin',
            color='Avg_Margin',
            color_continuous_scale='RdYlGn',
            title="📊 Average Gross Margin % by Division",
            labels={'Avg_Margin': 'Avg Gross Margin %'}
        )
        fig6.add_hline(y=filtered['Gross Margin %'].mean(),
                       line_dash="dot", line_color="red",
                       annotation_text="Overall Avg")
        st.plotly_chart(fig6, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        # Revenue contribution pie
        fig7 = px.pie(
            div_summary,
            values='Total_Sales',
            names='Division',
            title="🥧 Revenue Contribution by Division",
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        st.plotly_chart(fig7, use_container_width=True)

    with c4:
        # Profit contribution pie
        fig8 = px.pie(
            div_summary,
            values='Total_Profit',
            names='Division',
            title="🥧 Profit Contribution by Division",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        st.plotly_chart(fig8, use_container_width=True)

    # Division Summary Table
    st.subheader("📋 Division Summary Table")
    st.dataframe(div_summary, use_container_width=True, hide_index=True)

    # Margin by Division and Region heatmap
    st.subheader("🔥 Margin Heatmap: Division × Region")
    pivot = filtered.pivot_table(
        'Gross Margin %', 'Division', 'Region', aggfunc='mean'
    ).round(1)
    fig9 = px.imshow(
        pivot, text_auto=True,
        color_continuous_scale='RdYlGn',
        title="Avg Gross Margin % by Division and Region"
    )
    st.plotly_chart(fig9, use_container_width=True)

# ══════════════════════════════════════════════════════════
# TAB 3 — COST VS MARGIN DIAGNOSTICS
# ══════════════════════════════════════════════════════════
with tab3:
    st.subheader("💰 Cost vs Margin Diagnostics")

    c1, c2 = st.columns(2)

    with c1:
        # Cost vs Sales scatter
        fig10 = px.scatter(
            filtered,
            x='Cost', y='Sales',
            color='Division',
            size='Units',
            hover_name='Product Name',
            opacity=0.6,
            title="💸 Cost vs Sales",
            labels={'Cost': 'Cost ($)', 'Sales': 'Sales ($)'}
        )
        # Add diagonal line (break even)
        max_val = max(filtered['Sales'].max(), filtered['Cost'].max())
        fig10.add_trace(go.Scatter(
            x=[0, max_val], y=[0, max_val],
            mode='lines',
            line=dict(dash='dot', color='red'),
            name='Break Even'
        ))
        st.plotly_chart(fig10, use_container_width=True)

    with c2:
        # Margin Risk Distribution
        risk_counts = filtered['Margin Risk'].value_counts().reset_index()
        risk_counts.columns = ['Risk Level', 'Count']
        fig11 = px.pie(
            risk_counts,
            values='Count',
            names='Risk Level',
            title="⚠️ Margin Risk Distribution",
            color='Risk Level',
            color_discrete_map={
                '🟢 Healthy':      '#4CAF50',
                '🟡 Medium Risk':  '#FFC107',
                '🔴 High Risk':    '#F44336'
            }
        )
        st.plotly_chart(fig11, use_container_width=True)

    c3, c4 = st.columns(2)

    with c3:
        # Cost per Unit by Product
        cpu = filtered.groupby('Product Name')['Cost per Unit'].mean().reset_index()
        cpu = cpu.sort_values('Cost per Unit', ascending=False)
        fig12 = px.bar(
            cpu,
            x='Cost per Unit', y='Product Name',
            orientation='h',
            color='Cost per Unit',
            color_continuous_scale='Reds',
            title="💸 Avg Cost per Unit by Product",
            labels={'Cost per Unit': 'Cost per Unit ($)', 'Product Name': ''}
        )
        st.plotly_chart(fig12, use_container_width=True)

    with c4:
        # Gross Margin % distribution
        fig13 = px.histogram(
            filtered,
            x='Gross Margin %',
            color='Division',
            nbins=30,
            title="📊 Gross Margin % Distribution",
            labels={'Gross Margin %': 'Gross Margin %'}
        )
        fig13.add_vline(
            x=filtered['Gross Margin %'].mean(),
            line_dash="dot", line_color="red",
            annotation_text="Average"
        )
        st.plotly_chart(fig13, use_container_width=True)

    # High Risk Products Table
    st.subheader("🔴 High Risk Products — Needs Attention!")
    high_risk = filtered[filtered['Margin Risk'] == '🔴 High Risk'].groupby(
        'Product Name'
    ).agg(
        Division        =('Division',       'first'),
        Avg_Margin      =('Gross Margin %', 'mean'),
        Total_Sales     =('Sales',          'sum'),
        Total_Profit    =('Gross Profit',   'sum'),
        Avg_Cost_Unit   =('Cost per Unit',  'mean'),
    ).reset_index().round(2)

    if not high_risk.empty:
        st.warning(f"⚠️ {len(high_risk)} products identified as High Risk margin!")
        st.dataframe(high_risk, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No high risk products found with current filters!")

    # Pricing Recommendations
    st.subheader("💡 Pricing & Cost Recommendations")
    prod_diag = filtered.groupby('Product Name').agg(
        Avg_Margin   =('Gross Margin %', 'mean'),
        Total_Sales  =('Sales',          'sum'),
        Total_Profit =('Gross Profit',   'sum'),
    ).reset_index().round(2)

    avg_m = prod_diag['Avg_Margin'].mean()
    avg_s = prod_diag['Total_Sales'].mean()

    recommendations = []
    for _, row in prod_diag.iterrows():
        if row['Avg_Margin'] < avg_m * 0.5:
            rec = "🔴 Urgent: Reprice or discontinue"
        elif row['Avg_Margin'] < avg_m and row['Total_Sales'] > avg_s:
            rec = "🟡 Review: High sales but low margin — cost negotiation needed"
        elif row['Avg_Margin'] < avg_m:
            rec = "🟡 Monitor: Below average margin"
        else:
            rec = "🟢 Healthy: Maintain current strategy"
        recommendations.append({
            'Product': row['Product Name'],
            'Avg Margin %': row['Avg_Margin'],
            'Total Sales ($)': row['Total_Sales'],
            'Recommendation': rec
        })

    rec_df = pd.DataFrame(recommendations).sort_values('Avg Margin %')
    st.dataframe(rec_df, use_container_width=True, hide_index=True)

# ══════════════════════════════════════════════════════════
# TAB 4 — PROFIT CONCENTRATION ANALYSIS
# ══════════════════════════════════════════════════════════
with tab4:
    st.subheader("📈 Profit Concentration & Pareto Analysis")

    # Product level aggregation
    pareto = filtered.groupby('Product Name').agg(
        Total_Sales  =('Sales',         'sum'),
        Total_Profit =('Gross Profit',  'sum'),
    ).reset_index().sort_values('Total_Profit', ascending=False)

    pareto['Cumulative Profit %'] = (
        pareto['Total_Profit'].cumsum() /
        pareto['Total_Profit'].sum() * 100
    )
    pareto['Cumulative Sales %'] = (
        pareto['Total_Sales'].cumsum() /
        pareto['Total_Sales'].sum() * 100
    )
    pareto['Profit %'] = (
        pareto['Total_Profit'] /
        pareto['Total_Profit'].sum() * 100
    ).round(2)

    c1, c2 = st.columns(2)

    with c1:
        # Pareto Chart — Profit
        fig14 = go.Figure()
        fig14.add_trace(go.Bar(
            x=pareto['Product Name'],
            y=pareto['Total_Profit'],
            name='Total Profit',
            marker_color='#2196F3'
        ))
        fig14.add_trace(go.Scatter(
            x=pareto['Product Name'],
            y=pareto['Cumulative Profit %'],
            name='Cumulative Profit %',
            yaxis='y2',
            line=dict(color='red', width=2),
            mode='lines+markers'
        ))
        fig14.update_layout(
            title="📈 Pareto Chart — Profit Concentration",
            xaxis_tickangle=-45,
            yaxis=dict(title='Total Profit ($)'),
            yaxis2=dict(
                title='Cumulative %',
                overlaying='y',
                side='right',
                range=[0, 110]
            ),
            legend=dict(x=0.01, y=0.99)
        )
        fig14.add_hline(y=80, line_dash="dot",
                        line_color="orange",
                        annotation_text="80%",
                        yref='y2')
        st.plotly_chart(fig14, use_container_width=True)

    with c2:
        # Pareto Chart — Revenue
        fig15 = go.Figure()
        fig15.add_trace(go.Bar(
            x=pareto['Product Name'],
            y=pareto['Total_Sales'],
            name='Total Sales',
            marker_color='#4CAF50'
        ))
        fig15.add_trace(go.Scatter(
            x=pareto['Product Name'],
            y=pareto['Cumulative Sales %'],
            name='Cumulative Sales %',
            yaxis='y2',
            line=dict(color='red', width=2),
            mode='lines+markers'
        ))
        fig15.update_layout(
            title="📈 Pareto Chart — Revenue Concentration",
            xaxis_tickangle=-45,
            yaxis=dict(title='Total Sales ($)'),
            yaxis2=dict(
                title='Cumulative %',
                overlaying='y',
                side='right',
                range=[0, 110]
            ),
            legend=dict(x=0.01, y=0.99)
        )
        fig15.add_hline(y=80, line_dash="dot",
                        line_color="orange",
                        annotation_text="80%",
                        yref='y2')
        st.plotly_chart(fig15, use_container_width=True)

    # 80/20 Rule Analysis
    st.subheader("🎯 80/20 Rule Analysis")
    top80_profit = pareto[pareto['Cumulative Profit %'] <= 80]
    top80_sales  = pareto[pareto['Cumulative Sales %']  <= 80]

    p1, p2, p3 = st.columns(3)
    p1.metric(
        "Products driving 80% of Profit",
        f"{len(top80_profit)} products",
        f"out of {len(pareto)} total"
    )
    p2.metric(
        "Products driving 80% of Revenue",
        f"{len(top80_sales)} products",
        f"out of {len(pareto)} total"
    )
    p3.metric(
        "Top Product Profit Share",
        f"{pareto.iloc[0]['Profit %']:.1f}%",
        pareto.iloc[0]['Product Name']
    )

    # Profit vs Revenue Imbalance
    st.subheader("⚖️ Revenue vs Profit Imbalance")
    imbalance = filtered.groupby('Product Name').agg(
        Revenue_Pct =('Revenue Contribution %', 'sum'),
        Profit_Pct  =('Profit Contribution %',  'sum'),
    ).reset_index().round(2)
    imbalance['Imbalance'] = (
        imbalance['Revenue_Pct'] - imbalance['Profit_Pct']
    ).round(2)
    imbalance = imbalance.sort_values('Imbalance', ascending=False)

    fig16 = go.Figure()
    fig16.add_trace(go.Bar(
        name='Revenue %',
        x=imbalance['Product Name'],
        y=imbalance['Revenue_Pct'],
        marker_color='#2196F3'
    ))
    fig16.add_trace(go.Bar(
        name='Profit %',
        x=imbalance['Product Name'],
        y=imbalance['Profit_Pct'],
        marker_color='#4CAF50'
    ))
    fig16.update_layout(
        barmode='group',
        title="Revenue % vs Profit % by Product — Imbalance Detection",
        xaxis_tickangle=-45,
        yaxis_title="Contribution %"
    )
    st.plotly_chart(fig16, use_container_width=True)

    st.caption("⚠️ Products where Revenue % >> Profit % are selling well but not profitable enough")

    # Margin Volatility Over Time
    st.subheader("📅 Margin Trend Over Time")
    monthly = filtered.groupby(
        ['Order Year', 'Order Month', 'Division']
    )['Gross Margin %'].mean().reset_index()
    monthly['Date'] = pd.to_datetime(
        monthly['Order Year'].astype(str) + '-' +
        monthly['Order Month'].astype(str).str.zfill(2)
    )
    fig17 = px.line(
        monthly,
        x='Date', y='Gross Margin %',
        color='Division',
        title="📅 Monthly Gross Margin % Trend by Division",
        labels={'Gross Margin %': 'Avg Gross Margin %'}
    )
    st.plotly_chart(fig17, use_container_width=True)

    # Full Pareto Table
    st.subheader("📋 Full Profit Concentration Table")
    st.dataframe(pareto.round(2), use_container_width=True, hide_index=True)

    csv2 = pareto.to_csv(index=False).encode('utf-8')
    st.download_button(
        "⬇️ Download Pareto Analysis",
        data=csv2,
        file_name="pareto_analysis.csv",
        mime='text/csv'
    )

st.divider()
st.caption(f"🍬 Nassau Candy Distributor | Product Line Profitability Analysis | Source: `{FILE_NAME}`")
