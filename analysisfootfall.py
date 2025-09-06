# retail_dashboard.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
from datetime import datetime
import warnings
import base64

warnings.filterwarnings('ignore')
st.set_page_config(page_title="Retail Analytics Dashboard", layout="wide")

# Title
st.title("🛍️ Retail Analytics Dashboard")
st.markdown("Upload your retail dataset (CSV) to explore sales, customers, and trends.")

# File uploader
uploaded_file = st.file_uploader("📤 Upload your retail dataset (CSV)", type=["csv"])

if uploaded_file is not None:
    try:
        # Read CSV
        df = pd.read_csv(uploaded_file)
        st.success("✅ Dataset loaded successfully!")

        # Show shape and preview
        st.write(f"**Dataset Shape:** {df.shape[0]} rows × {df.shape[1]} columns")
        st.dataframe(df.head())

        # === DATA PREP ===
        # Convert OrderDate if exists
        if 'OrderDate' in df.columns:
            df['OrderDate'] = pd.to_datetime(df['OrderDate'], errors='coerce')
            if df['OrderDate'].isna().all():
                st.warning("⚠️ 'OrderDate' column exists but could not parse any dates.")
            else:
                st.info("📅 'OrderDate' parsed successfully.")
        else:
            st.warning("⚠️ 'OrderDate' column not found — time-series charts disabled.")

        # Ensure numeric
        numeric_cols = ['Sales', 'Quantity', 'Profit', 'UnitPrice']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # === FILTERS ===
        st.sidebar.header("FilterWhere")
        df_filtered = df.copy()

        # Date filter
        if 'OrderDate' in df.columns and df['OrderDate'].notna().any():
            min_date = df['OrderDate'].min().date()
            max_date = df['OrderDate'].max().date()
            date_range = st.sidebar.date_input(
                "📅 Date Range",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date
            )
            if len(date_range) == 2:
                start_date, end_date = date_range
                mask = (df['OrderDate'].dt.date >= start_date) & (df['OrderDate'].dt.date <= end_date)
                df_filtered = df_filtered[mask]
            else:
                st.sidebar.warning("Please select a valid date range.")

        # Category filter
        if 'Category' in df_filtered.columns:
            categories = st.sidebar.multiselect(
                "🛍️ Category",
                options=df_filtered['Category'].dropna().unique(),
                default=df_filtered['Category'].dropna().unique()
            )
            if categories:
                df_filtered = df_filtered[df_filtered['Category'].isin(categories)]
            else:
                st.sidebar.warning("No category selected. Showing all.")

        # Region filter
        if 'Region' in df_filtered.columns:
            regions = st.sidebar.multiselect(
                "📍 Region",
                options=df_filtered['Region'].dropna().unique(),
                default=df_filtered['Region'].dropna().unique()
            )
            if regions:
                df_filtered = df_filtered[df_filtered['Region'].isin(regions)]
            else:
                st.sidebar.warning("No region selected. Showing all.")

        # === KPIs ===
        st.subheader("📈 Key Performance Indicators")
        total_sales = df_filtered['Sales'].sum() if 'Sales' in df_filtered.columns else 0
        total_orders = df_filtered['OrderID'].nunique() if 'OrderID' in df_filtered.columns else len(df_filtered)
        avg_order_value = total_sales / total_orders if total_orders > 0 else 0
        total_profit = df_filtered['Profit'].sum() if 'Profit' in df_filtered.columns else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Sales", f"${total_sales:,.2f}")
        col2.metric("Total Orders", f"{total_orders:,}")
        col3.metric("Avg Order Value", f"${avg_order_value:,.2f}")
        col4.metric("Total Profit", f"${total_profit:,.2f}")

        # === INSIGHTS ===
        st.subheader("💡 Smart Insights")
        insights = []

        if 'Region' in df_filtered.columns and 'Sales' in df_filtered.columns:
            region_sales = df_filtered.groupby('Region')['Sales'].sum()
            if not region_sales.empty:
                top_region = region_sales.idxmax()
                insights.append(f"🏆 Top region: **{top_region}** with ${region_sales.max():,.2f} sales")

        if 'Category' in df_filtered.columns and 'Sales' in df_filtered.columns:
            cat_sales = df_filtered.groupby('Category')['Sales'].sum()
            if not cat_sales.empty:
                top_cat = cat_sales.idxmax()
                insights.append(f"🔥 Top category: **{top_cat}**")

        if 'OrderDate' in df_filtered.columns and 'Sales' in df_filtered.columns:
            sales_over_time = df_filtered.dropna(subset=['OrderDate']).set_index('OrderDate').resample('M')['Sales'].sum()
            if len(sales_over_time) > 1:
                if sales_over_time.iloc[-1] > sales_over_time.iloc[-2]:
                    insights.append("📈 Sales are increasing recently")
                else:
                    insights.append("📉 Sales are declining recently")

        if insights:
            for i, insight in enumerate(insights, 1):
                st.markdown(f"{i}. {insight}")
        else:
            st.info("No insights generated based on current filters.")

        # === GRAPHS SECTION ===
        st.subheader("📊 Data Visualizations")

        # 1. Sales Over Time
        if 'OrderDate' in df_filtered.columns and 'Sales' in df_filtered.columns:
            with st.expander("📅 Sales Over Time", expanded=True):
                df_time = df_filtered.dropna(subset=['OrderDate'])
                if not df_time.empty:
                    df_time = df_time.groupby(df_time['OrderDate'].dt.to_period("D"))['Sales'].sum()
                    df_time.index = df_time.index.to_timestamp()
                    fig1 = px.line(df_time, x=df_time.index, y='Sales', title='Daily Sales Trend')
                    fig1.update_layout(xaxis_title="Date", yaxis_title="Sales ($)")
                    st.plotly_chart(fig1, use_container_width=True)
                else:
                    st.warning("No valid data to plot sales over time.")

        # 2. Top Products
        if 'Product' in df_filtered.columns and 'Sales' in df_filtered.columns:
            with st.expander("🏆 Top 10 Products by Sales", expanded=True):
                top_products = df_filtered.groupby('Product')['Sales'].sum().sort_values(ascending=False).head(10)
                if not top_products.empty:
                    fig2 = px.bar(
                        top_products,
                        x=top_products.index,
                        y='Sales',
                        title='Top 10 Products by Sales',
                        labels={'x': 'Product', 'Sales': 'Sales ($)'}
                    )
                    fig2.update_layout(xaxis_tickangle=-45)
                    st.plotly_chart(fig2, use_container_width=True)
                else:
                    st.warning("No product sales data to display.")

        # 3. Sales by Category
        if 'Category' in df_filtered.columns and 'Sales' in df_filtered.columns:
            with st.expander("🥧 Sales by Category", expanded=True):
                cat_sales = df_filtered.groupby('Category')['Sales'].sum()
                if not cat_sales.empty:
                    fig3 = px.pie(cat_sales, names=cat_sales.index, values='Sales', title='Sales Distribution by Category')
                    st.plotly_chart(fig3, use_container_width=True)
                else:
                    st.warning("No category sales data.")

        # 4. Sales by Region
        if 'Region' in df_filtered.columns and 'Sales' in df_filtered.columns:
            with st.expander("📍 Sales by Region", expanded=True):
                reg_sales = df_filtered.groupby('Region')['Sales'].sum().reset_index()
                if not reg_sales.empty:
                    fig4 = px.bar(reg_sales, x='Region', y='Sales', title='Sales by Region', color='Region')
                    st.plotly_chart(fig4, use_container_width=True)
                else:
                    st.warning("No region sales data.")

        # 5. Correlation Heatmap
        numeric_df = df_filtered.select_dtypes(include='number')
        if len(numeric_df.columns) > 1:
            with st.expander("🔗 Correlation Heatmap", expanded=True):
                corr = numeric_df.corr()
                if not corr.empty and corr.shape[0] > 1:
                    fig5, ax = plt.subplots(figsize=(6, 4))
                    sns.heatmap(corr, annot=True, cmap='coolwarm', center=0, ax=ax, fmt='.2f')
                    st.pyplot(fig5)
                else:
                    st.warning("Not enough numeric data for correlation.")

        # === DOWNLOAD REPORTS ===
        st.subheader("💾 Download Report")

        # CSV Summary
        summary_df = pd.DataFrame({
            "Metric": ["Total Sales", "Total Orders", "Avg Order Value", "Total Profit"],
            "Value": [f"${total_sales:,.2f}", f"{total_orders:,}", f"${avg_order_value:,.2f}", f"${total_profit:,.2f}"]
        })
        csv = summary_df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download CSV Summary", data=csv, file_name="summary.csv", mime="text/csv")

        # TXT Report (Fixed!)
        if st.button("📄 Generate Text Report (.txt)"):
            report = [
                "==================================",
                "    RETAIL ANALYTICS REPORT",
                "==================================",
                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                "",
                "----- KEY METRICS -----",
                f"Total Sales      : ${total_sales:,.2f}",
                f"Total Orders     : {total_orders:,}",
                f"Avg Order Value  : ${avg_order_value:,.2f}",
                f"Total Profit     : ${total_profit:,.2f}",
                "",
                "----- INSIGHTS -----",
            ]
            if insights:
                report.extend([f"{i+1}. {ins}" for i, ins in enumerate(insights)])
            else:
                report.append("No insights available.")
            report.append("\n----- END OF REPORT -----")

            txt_data = "\n".join(report)
            b64_txt = base64.b64encode(txt_data.encode()).decode()
            # ✅ FIXED: Added 'data:' prefix to make it a valid data URI
            href = f'<a href="data:text/plain;base64,{b64_txt}" download="Retail_Report.txt">⬇️ Download TXT Report</a>'
            st.markdown(href, unsafe_allow_html=True)

        # Raw data toggle
        if st.checkbox("Show Raw Filtered Data"):
            st.write(df_filtered)

    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.code(str(e), language="python")
else:
    st.info("👈 Please upload a CSV file to begin.")

# Footer
st.markdown("---")
st.markdown("📊 Retail Analytics Dashboard | Built with ❤️ Streamlit")