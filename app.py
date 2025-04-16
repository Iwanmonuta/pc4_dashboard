import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import numpy as np
import os
import tempfile
from pathlib import Path
import io

# Monuta kleuren palette
monuta_palette = ["#3f582d", "#74975d", "#6e0038", "#d87f7e", "#d763a9", "#66b3c9"]

# Configuratie van de pagina
st.set_page_config(
    page_title="PC4 Dashboard Monuta uitvaart",
    page_icon="🗺️",
    layout="wide"
)

# Titel en intro
st.title("🗺️ Postcode 4 Dashboard Nederland")
st.markdown("Dashboard voor visualisatie van gegevens op PC4-niveau in Nederland.")

# Sidebar voor bestandsupload
st.sidebar.title("Data bronnen")

# Controleer of de shapefile bestanden lokaal beschikbaar zijn
shapefile_path = "data/PC4.shp"
has_local_shapefile = os.path.exists(shapefile_path)

# Alleen Excel bestand is nodig voor upload (andere bestanden zijn in repository)
uploaded_excel = st.sidebar.file_uploader("Upload het Excel bestand (PC4 verrijkt)", type=['xlsx'])

if has_local_shapefile:
    st.sidebar.success("✅ Shapefile bestanden zijn geladen vanuit de repository")
else:
    st.sidebar.warning("⚠️ Shapefile bestanden niet gevonden in repository")
    # Als de shapefile niet lokaal beschikbaar is, vraag om uploads
    uploaded_shapefile = st.sidebar.file_uploader("Upload het Shapefile (.shp)", type=['shp'])
    uploaded_shx = st.sidebar.file_uploader("Upload het SHX bestand (.shx)", type=['shx'])
    uploaded_dbf = st.sidebar.file_uploader("Upload het DBF bestand (.dbf)", type=['dbf'])
    uploaded_prj = st.sidebar.file_uploader("Upload het PRJ bestand (.prj)", type=['prj'], accept_multiple_files=False)

# Functie om tijdelijke bestanden aan te maken van uploads
def save_uploaded_files():
    temp_dir = tempfile.mkdtemp()
    excel_path = None
    shapefile_path = None
    
    # Sla Excel bestand op
    if uploaded_excel is not None:
        excel_path = os.path.join(temp_dir, "pc4_verrijkt.xlsx")
        with open(excel_path, "wb") as f:
            f.write(uploaded_excel.getbuffer())
    
    # Als de shapefile lokaal beschikbaar is, gebruik die
    if has_local_shapefile:
        shapefile_path = "data/PC4.shp"
    # Anders gebruik de uploads
    elif 'uploaded_shapefile' in locals() and uploaded_shapefile is not None:
        shapefile_path = os.path.join(temp_dir, "PC4.shp")
        with open(shapefile_path, "wb") as f:
            f.write(uploaded_shapefile.getbuffer())
            
        # SHX bestand
        if 'uploaded_shx' in locals() and uploaded_shx is not None:
            shx_path = os.path.join(temp_dir, "PC4.shx")
            with open(shx_path, "wb") as f:
                f.write(uploaded_shx.getbuffer())
        
        # DBF bestand
        if 'uploaded_dbf' in locals() and uploaded_dbf is not None:
            dbf_path = os.path.join(temp_dir, "PC4.dbf")
            with open(dbf_path, "wb") as f:
                f.write(uploaded_dbf.getbuffer())
        
        # PRJ bestand
        if 'uploaded_prj' in locals() and uploaded_prj is not None:
            prj_path = os.path.join(temp_dir, "PC4.prj")
            with open(prj_path, "wb") as f:
                f.write(uploaded_prj.getbuffer())
    
    return temp_dir, excel_path, shapefile_path

# Functie om data in te laden
@st.cache_data
def load_data(excel_path, shapefile_path):
    try:
        # Controleer of bestanden bestaan
        if not os.path.exists(excel_path):
            st.error(f"Excel bestand niet gevonden: {excel_path}")
            return pd.DataFrame(), gpd.GeoDataFrame(), gpd.GeoDataFrame()
            
        if not os.path.exists(shapefile_path):
            st.error(f"Shapefile niet gevonden: {shapefile_path}")
            return pd.DataFrame(), gpd.GeoDataFrame(), gpd.GeoDataFrame()
        
        # Check of de benodigde shape-bestanden bestaan
        shapefile_dir = os.path.dirname(shapefile_path)
        shapefile_name = os.path.splitext(os.path.basename(shapefile_path))[0]
        
        # Controleer of .shx bestand bestaat
        shx_path = os.path.join(shapefile_dir, f"{shapefile_name}.shx")
        if not os.path.exists(shx_path):
            shx_path_upper = os.path.join(shapefile_dir, f"{shapefile_name}.SHX")
            if not os.path.exists(shx_path_upper):
                st.warning(f".shx bestand ontbreekt voor shapefile. Probeer het shapefile opnieuw te uploaden met alle bijbehorende bestanden.")
                
        # Data inladen
        df = pd.read_excel(excel_path)
        
        # Zorg dat postcode kolom PC4 heet in het excel bestand
        if 'PC4' not in df.columns and 'pc4' in df.columns:
            df = df.rename(columns={'pc4': 'PC4'})  # Hernoem 'pc4' naar 'PC4' indien nodig
        
        # Log de eerste paar rijen en kolomnamen om te helpen bij debugging
        print("Excel kolommen:", df.columns.tolist())
        print("Eerste 3 rijen van Excel:")
        print(df.head(3))
        
        # Controleer of de PC4 kolom bestaat
        if 'PC4' not in df.columns:
            st.error("Kolom 'PC4' niet gevonden in Excel bestand. Beschikbare kolommen: " + ", ".join(df.columns.tolist()))
            return pd.DataFrame(), gpd.GeoDataFrame(), gpd.GeoDataFrame()
        
        # Probeer expliciete configuratie voor het herstellen van het .shx bestand
        os.environ['SHAPE_RESTORE_SHX'] = 'YES'
        
        # Shapefile inladen met foutafvang
        try:
            netherlands = gpd.read_file(shapefile_path)
        except Exception as e:
            st.error(f"Fout bij het laden van het shapefile: {e}. Controleer of alle benodigde bestanden (.shp, .shx, .dbf) zijn geüpload.")
            return df, gpd.GeoDataFrame(), gpd.GeoDataFrame()
        
        # Log de eerste paar rijen en kolomnamen van de shapefile
        print("Shapefile kolommen:", netherlands.columns.tolist())
        print("Eerste 3 rijen van Shapefile:")
        print(netherlands.head(3))
        
        # Controleer of de PC4 kolom bestaat in de shapefile
        if 'PC4' not in netherlands.columns:
            # Probeer andere mogelijke namen voor postcode kolom
            potential_pc4_columns = [col for col in netherlands.columns if 'pc' in col.lower() or 'post' in col.lower()]
            if potential_pc4_columns:
                netherlands = netherlands.rename(columns={potential_pc4_columns[0]: 'PC4'})
                print(f"Hernoemd shapefile kolom '{potential_pc4_columns[0]}' naar 'PC4'")
            else:
                st.error("Kolom 'PC4' niet gevonden in Shapefile. Beschikbare kolommen: " + ", ".join(netherlands.columns.tolist()))
                return pd.DataFrame(), gpd.GeoDataFrame(), gpd.GeoDataFrame()
        
        # Vereenvoudig de geometrieën voor betere performance
        netherlands['geometry'] = netherlands['geometry'].simplify(tolerance=0.001, preserve_topology=True)
        
        # Zorg dat PC4 als string is opgeslagen in beide dataframes
        netherlands['PC4'] = netherlands['PC4'].astype(str)
        df['PC4'] = df['PC4'].astype(str)
        
        # Verwijder rijen met ontbrekende woonplaats zoals gevraagd
        if 'woonplaats' in df.columns:
            df = df.dropna(subset=['woonplaats'])
        
        # Controleer welke kolommen daadwerkelijk bestaan in het dataframe
        expected_columns = ['provincie', 'gemeente', 'woonplaats', 'cluster', 'voorstel_benaming_uvb', 'voorstel_onderneming']
        existing_columns = [col for col in expected_columns if col in df.columns]
        
        # Log welke kolommen ontbreken
        missing_columns = [col for col in expected_columns if col not in df.columns]
        if missing_columns:
            print(f"Waarschuwing: Deze kolommen ontbreken in het dataframe: {missing_columns}")
            
        # Alleen filteren op bestaande kolommen
        if existing_columns:
            df = df.dropna(subset=existing_columns)
        
        # Merge de datasets
        print(f"Aantal rijen voor merge - Excel: {len(df)}, Shapefile: {len(netherlands)}")
        merged_data = netherlands.merge(df, on='PC4', how='inner')
        print(f"Aantal rijen na merge: {len(merged_data)}")
        
        if len(merged_data) == 0:
            st.error("Geen overeenkomende postcodes gevonden bij het mergen van de datasets!")
            # Toon een paar waarden om te helpen debuggen
            print("Voorbeeld PC4 waarden in Excel:", df['PC4'].head(10).tolist())
            print("Voorbeeld PC4 waarden in Shapefile:", netherlands['PC4'].head(10).tolist())
            
            return df, netherlands, gpd.GeoDataFrame()
        
        # Controleer of merged_data de PC4 kolom bevat
        if 'PC4' not in merged_data.columns:
            st.error("Na het mergen ontbreekt de 'PC4' kolom. Dit is onverwacht.")
            return df, netherlands, merged_data
        
        # Aanwezigheid van belangrijke kolommen controleren en eventueel defaults instellen
        for col in ['inwoners', 'inwoners_65plus', 'sterfte_2023', 'uitvaarten_2023', 'uitvaarten_2024', 'uitvaarten_2025', 'aantal_verzekerden', 'woz', 'uitkeringen', 'reistijd_min']:
            if col not in merged_data.columns:
                print(f"Kolom {col} ontbreekt in de data en wordt aangemaakt met default waarden.")
                merged_data[col] = 0
        
        return df, netherlands, merged_data
    except Exception as e:
        import traceback
        st.error(f"Fout bij het laden van de data: {e}")
        print("Gedetailleerde foutmelding:")
        print(traceback.format_exc())
        # Terugvallen op lege dataframes als de data niet kan worden geladen
        return pd.DataFrame(), gpd.GeoDataFrame(), gpd.GeoDataFrame()

# Functies voor het berekenen van afgeleide metrieken
def calculate_derived_metrics(data):
    # Maak kopie om originele data niet te wijzigen
    data = data.copy()
    
    # Marktaandeel 2023 berekenen
    if 'uitvaarten_2023' in data.columns and 'sterfte_2023' in data.columns:
        # Voorkom delen door nul
        data['berekend_marktaandeel_2023'] = np.where(
            data['sterfte_2023'] > 0,
            data['uitvaarten_2023'] / data['sterfte_2023'] * 100,
            0
        )
    
    # Percentage uitkeringen berekenen
    if 'uitkeringen' in data.columns and 'inwoners' in data.columns:
        data['percentage_uitkeringen'] = np.where(
            data['inwoners'] > 0,
            data['uitkeringen'] / data['inwoners'] * 100,
            0
        )
    
    return data

# Controleer of de benodigde bestanden beschikbaar zijn
can_load_data = False

if uploaded_excel is not None:
    if has_local_shapefile:
        can_load_data = True
    elif 'uploaded_shapefile' in locals() and 'uploaded_shx' in locals() and 'uploaded_dbf' in locals() and \
         uploaded_shapefile is not None and uploaded_shx is not None and uploaded_dbf is not None:
        can_load_data = True

if can_load_data:
    # Data laden met een spinner om te laten zien dat het bezig is
    with st.spinner('Data wordt geladen...'):
        temp_dir, excel_path, shapefile_path = save_uploaded_files()
        df, netherlands, merged_data = load_data(excel_path, shapefile_path)
else:
    # Toon intro bericht als bestanden niet zijn geüpload
    st.info("⚠️ Upload het Excel bestand om de applicatie te gebruiken")
    
    if not has_local_shapefile:
        st.markdown("""
        **Daarnaast heb je deze bestanden nodig:**
        1. Shapefile met Nederlandse postcodegebieden (PC4.shp)
        2. Bijbehorende .shx bestand
        3. Bijbehorende .dbf bestand
        4. Bijbehorende .prj bestand
        """)
    
    # Demo mode met placeholder afbeelding
    st.image("https://via.placeholder.com/800x400.png?text=PC4+Dashboard+Demo", 
             caption="Upload de benodigde bestanden om de interactieve kaart te zien")
    st.stop()

# Controleer of we geldige data hebben ontvangen
if len(merged_data) == 0:
    st.error("Geen data beschikbaar. Controleer de console voor meer informatie.")
    st.stop()  # Stop de uitvoering van de app

# Bereken afgeleide metrieken
merged_data = calculate_derived_metrics(merged_data)

# Definieer column_mapping voor visualisatie en filtering
column_mapping = {
    "Marktaandeel 2023": "berekend_marktaandeel_2023",
    "Inwoners": "inwoners",
    "Inwoners 65+": "inwoners_65plus",
    "Sterfte 2023": "sterfte_2023",
    "Uitvaarten 2023": "uitvaarten_2023",
    "Uitvaarten 2024": "uitvaarten_2024",
    "Uitvaarten 2025": "uitvaarten_2025",
    "Aantal Verzekerden": "aantal_verzekerden",
    "WOZ Waarde": "woz",
    "Percentage Uitkeringen": "percentage_uitkeringen",
    "Reistijd (minuten)": "reistijd_min"
}

# Sidebar-filters
st.sidebar.header("Filters")
st.sidebar.info(f"Dataset bevat {len(merged_data)} postcodegebieden")

# Initialiseer filtered_data met merged_data
filtered_data = merged_data.copy()

# Multi-level filters in de sidebar
filter_container = st.sidebar.expander("Geografische filters", expanded=True)

with filter_container:
    # PC4 filter (nieuw)
    if 'PC4' in filtered_data.columns:
        pc4_values = sorted(filtered_data['PC4'].unique().tolist())
        selected_pc4 = st.multiselect(
            "Filter op PC4:",
            pc4_values,
            default=[]
        )
        
        # Filter data op PC4 als er een selectie is gemaakt
        if selected_pc4:
            filtered_data = filtered_data[filtered_data['PC4'].isin(selected_pc4)]
    else:
        st.warning("Geen PC4 kolom gevonden in de data. PC4 filter is niet beschikbaar.")
    
    # Provincie filter (multi-select)
    if 'provincie' in filtered_data.columns:
        provincie_values = sorted(filtered_data['provincie'].fillna('Onbekend').astype(str).unique().tolist())
        selected_provincies = st.multiselect(
            "Filter op provincie:",
            provincie_values,
            default=[]
        )
        
        # Filter data op provincie als er een selectie is gemaakt
        if selected_provincies:
            filtered_data = filtered_data[filtered_data['provincie'].isin(selected_provincies)]
    
    # Gemeente filter (multi-select, afhankelijk van provincie selectie)
    if 'gemeente' in filtered_data.columns:
        gemeente_values = sorted(filtered_data['gemeente'].fillna('Onbekend').astype(str).unique().tolist())
        selected_gemeenten = st.multiselect(
            "Filter op gemeente:",
            gemeente_values,
            default=[]
        )
        
        # Filter data op gemeente als er een selectie is gemaakt
        if selected_gemeenten:
            filtered_data = filtered_data[filtered_data['gemeente'].isin(selected_gemeenten)]
    
    # Woonplaats filter (multi-select, afhankelijk van gemeente selectie)
    if 'woonplaats' in filtered_data.columns:
        woonplaats_values = sorted(filtered_data['woonplaats'].fillna('Onbekend').astype(str).unique().tolist())
        selected_woonplaatsen = st.multiselect(
            "Filter op woonplaats:",
            woonplaats_values,
            default=[]
        )
        
        # Filter data op woonplaats als er een selectie is gemaakt
        if selected_woonplaatsen:
            filtered_data = filtered_data[filtered_data['woonplaats'].isin(selected_woonplaatsen)]
    
    # Cluster filter (nieuw, multi-select) - alleen als kolom bestaat
    if 'cluster' in filtered_data.columns:
        cluster_values = sorted(filtered_data['cluster'].fillna('Onbekend').astype(str).unique().tolist())
        selected_clusters = st.multiselect(
            "Filter op cluster:",
            cluster_values,
            default=[]
        )
        
        # Filter op cluster als er een selectie is gemaakt
        if selected_clusters:
            filtered_data = filtered_data[filtered_data['cluster'].isin(selected_clusters)]

# Organisatie filters
organisatie_container = st.sidebar.expander("Organisatie filters", expanded=False)

with organisatie_container:
    # Voorstel onderneming filter (nieuw) - alleen als kolom bestaat
    if 'voorstel_onderneming' in filtered_data.columns:
        onderneming_values = sorted(filtered_data['voorstel_onderneming'].fillna('Onbekend').astype(str).unique().tolist())
        selected_ondernemingen = st.multiselect(
            "Filter op voorstel onderneming:",
            onderneming_values,
            default=[]
        )
        
        # Filter op voorstel onderneming als er een selectie is gemaakt
        if selected_ondernemingen:
            filtered_data = filtered_data[filtered_data['voorstel_onderneming'].isin(selected_ondernemingen)]
    
    # Voorstel benaming UVB filter (nieuw) - alleen als kolom bestaat
    if 'voorstel_benaming_uvb' in filtered_data.columns:
        uvb_values = sorted(filtered_data['voorstel_benaming_uvb'].fillna('Onbekend').astype(str).unique().tolist())
        selected_uvbs = st.multiselect(
            "Filter op voorstel benaming UVB:",
            uvb_values,
            default=[]
        )
        
        # Filter op voorstel benaming UVB als er een selectie is gemaakt
        if selected_uvbs:
            filtered_data = filtered_data[filtered_data['voorstel_benaming_uvb'].isin(selected_uvbs)]

# Selecteer een kolom voor visualisatie in de statistieken aan rechterkant
st.sidebar.subheader("Visualisatie opties")

# Controleer welke kolommen beschikbaar zijn
available_columns = []
for display_name, column_name in column_mapping.items():
    if column_name in merged_data.columns or column_name == 'berekend_marktaandeel_2023' or column_name == 'percentage_uitkeringen':
        available_columns.append(display_name)

# Selectie van de te visualiseren metriek
selected_column_display = st.sidebar.selectbox(
    "Selecteer kenmerk voor statistieken:",
    options=available_columns,
    index=0 if available_columns else None
)

# Converteer terug naar de echte kolomnaam als er een selectie is gemaakt
selected_column = column_mapping.get(selected_column_display, None) if selected_column_display else None

# Waardebereik filter voor marktaandeel (altijd beschikbaar)
try:
    min_val = float(filtered_data['berekend_marktaandeel_2023'].min())
    max_val = float(filtered_data['berekend_marktaandeel_2023'].max())
    
    # Voorkom identieke min en max waarden
    if min_val == max_val:
        min_val = min_val * 0.9
        max_val = max_val * 1.1
        
    value_range = st.sidebar.slider(
        f"Bereik voor marktaandeel (%):",
        min_val, max_val, 
        (min_val, max_val)
    )
    
    # Filter op waardebereik
    filtered_data = filtered_data[
        (filtered_data['berekend_marktaandeel_2023'] >= value_range[0]) & 
        (filtered_data['berekend_marktaandeel_2023'] <= value_range[1])
    ]
except Exception as e:
    st.sidebar.warning(f"Kon waardebereik niet instellen: {e}")

# Dashboard layout met twee kolommen (maak kaart smaller)
col1, col2 = st.columns([2, 1])

# Voeg export functionaliteit toe bovenaan de pagina
export_container = st.container()
with export_container:
    export_col1, export_col2 = st.columns(2)
    
    with export_col1:
        # Export geselecteerde PC4 data
        if len(filtered_data) > 0:
            # Bereid data voor voor export (zonder geometrie kolom die niet naar CSV kan)
            export_data = filtered_data.drop(columns=['geometry'])
            
            # Converteer naar CSV
            csv = export_data.to_csv(index=False)
            
            st.download_button(
                label="📥 Exporteer PC4 data (CSV)",
                data=csv,
                file_name=f"pc4_data_export_{len(filtered_data)}_gebieden.csv",
                mime="text/csv",
            )
    
    with export_col2:
        # Export statistieken samenvatting
        if len(filtered_data) > 0:
            # Bereken alle statistieken
            total_sterfte = filtered_data['sterfte_2023'].sum()
            total_uitvaarten = filtered_data['uitvaarten_2023'].sum()
            total_uitvaarten_2024 = filtered_data['uitvaarten_2024'].sum() if 'uitvaarten_2024' in filtered_data.columns else 0
            total_uitvaarten_2025 = filtered_data['uitvaarten_2025'].sum() if 'uitvaarten_2025' in filtered_data.columns else 0
            
            overall_marktaandeel = (total_uitvaarten / total_sterfte) * 100 if total_sterfte > 0 else 0
            
            total_inwoners = filtered_data['inwoners'].sum() if 'inwoners' in filtered_data.columns else 0
            total_65plus = filtered_data['inwoners_65plus'].sum() if 'inwoners_65plus' in filtered_data.columns else 0
            
            gewogen_woz = (filtered_data['woz'] * filtered_data['inwoners']).sum() / filtered_data['inwoners'].sum() * 1000 if 'woz' in filtered_data.columns and 'inwoners' in filtered_data.columns and filtered_data['inwoners'].sum() > 0 else 0
            
            gem_reistijd = filtered_data['reistijd_min'].mean() if 'reistijd_min' in filtered_data.columns else 0
            
            total_verzekerden = filtered_data['aantal_verzekerden'].sum() if 'aantal_verzekerden' in filtered_data.columns else 0
            
            # Bepaal gebiedsnaam op basis van filters
            gebied_naam = "Heel Nederland"
            if selected_pc4:
                gebied_naam = f"PC4: {', '.join(selected_pc4)}"
            elif selected_provincies:
                gebied_naam = f"Provincie(s): {', '.join(selected_provincies)}"
            elif selected_gemeenten:
                gebied_naam = f"Gemeente(n): {', '.join(selected_gemeenten)}"
            elif selected_woonplaatsen:
                gebied_naam = f"Woonplaats(en): {', '.join(selected_woonplaatsen)}"
            
            # Maak een DataFrame van de statistieken
            stats_data = {
                'Kenmerk': [
                    'Gebied', 'Aantal PC4-gebieden', 'Marktaandeel 2023 (%)', 
                    'Totaal inwoners', 'Inwoners 65+', 'Sterfte 2023', 
                    'Uitvaarten 2023', 'Uitvaarten 2024', 'Uitvaarten 2025',
                    'Aantal verzekerden', 'Gemiddelde WOZ-waarde (€)', 'Gemiddelde reistijd (min)'
                ],
                'Waarde': [
                    gebied_naam, len(filtered_data), round(overall_marktaandeel, 2),
                    int(total_inwoners), int(total_65plus), int(total_sterfte),
                    int(total_uitvaarten), int(total_uitvaarten_2024), int(total_uitvaarten_2025),
                    int(total_verzekerden), int(gewogen_woz), round(gem_reistijd, 1)
                ]
            }
            stats_df = pd.DataFrame(stats_data)
            
            # Converteer naar CSV
            stats_csv = stats_df.to_csv(index=False)
            
            st.download_button(
                label="📥 Exporteer statistieken (CSV)",
                data=stats_csv,
                file_name=f"statistieken_{gebied_naam.replace(':', '').replace(',', '_')}.csv",
                mime="text/csv",
            )

st.markdown("---")  # Horizontale lijn voor visuele scheiding

with col1:
    st.subheader(f"PC4 Kaart - {selected_column_display}")  # Altijd marktaandeel in de titel
    
    # Check of er data is om te visualiseren
    if len(filtered_data) > 0:
        # Maak de kaart met Plotly - altijd marktaandeel tonen
        fig = px.choropleth_mapbox(
            filtered_data,
            geojson=filtered_data.geometry,
            locations=filtered_data.index,
            color=selected_column,  # Altijd marktaandeel visualiseren
            color_continuous_scale=monuta_palette,  # Monuta's kleuren palette
            mapbox_style="carto-positron",
            zoom=6.5,
            center={"lat": 52.1326, "lon": 5.2913},  # Centreer op Nederland
            opacity=0.7,
            hover_data=['PC4', 'provincie', 'gemeente', 'woonplaats', selected_column],
            labels={selected_column: selected_column_display}
        )
        
        fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Geen data beschikbaar met de huidige filters.")

with col2:
    st.subheader("Statistieken")
    
    if len(filtered_data) > 0:
        # Bereken het algehele marktaandeel voor de geselecteerde regio's
        total_sterfte = filtered_data['sterfte_2023'].sum()
        total_uitvaarten = filtered_data['uitvaarten_2023'].sum()
        
        if total_sterfte > 0:
            overall_marktaandeel = (total_uitvaarten / total_sterfte) * 100
        else:
            overall_marktaandeel = 0
        
        # Statistieken in twee kolommen weergeven
        stat_col1, stat_col2 = st.columns(2)
        
        with stat_col1:
            # Eerste kolom statistieken
            st.metric("Aantal PC4-gebieden", len(filtered_data))
            st.metric("Marktaandeel 2023", f"{round(overall_marktaandeel, 2)}%")
            
            # Controleer en bereken inwoners totaal
            if 'inwoners' in filtered_data.columns:
                total_inwoners = filtered_data['inwoners'].sum()
                st.metric("Totaal inwoners", f"{int(total_inwoners):,}".replace(",", "."))
                
            # Bereken 65-plussers
            if 'inwoners_65plus' in filtered_data.columns:
                total_65plus = filtered_data['inwoners_65plus'].sum()
                st.metric("Inwoners 65+", f"{int(total_65plus):,}".replace(",", "."))
                
            # Bereken uitkeringen percentage indien beschikbaar
            if 'uitkeringen' in filtered_data.columns and 'inwoners' in filtered_data.columns:
                # Percentage uitkeringen berekenen
                totaal_uitkeringen = filtered_data['uitkeringen'].sum()
                totaal_inwoners = filtered_data['inwoners'].sum()
                if totaal_inwoners > 0:
                    percentage_uitkeringen = (totaal_uitkeringen / totaal_inwoners) * 100
                    st.metric("Percentage uitkering", f"{round(percentage_uitkeringen, 1)}%")
        
        with stat_col2:
            # Tweede kolom statistieken
            st.metric("Sterfte 2023", int(total_sterfte))
            st.metric("Uitvaarten 2023", int(total_uitvaarten))
            
            # Nieuwe statistieken toevoegen
            if 'uitvaarten_2024' in filtered_data.columns:
                st.metric("Uitvaarten 2024", int(filtered_data['uitvaarten_2024'].sum()))
                
            if 'uitvaarten_2025' in filtered_data.columns:
                st.metric("Uitvaarten 2025", int(filtered_data['uitvaarten_2025'].sum()))
                
            if 'aantal_verzekerden' in filtered_data.columns:
                st.metric("Aantal verzekerden", f"{int(filtered_data['aantal_verzekerden'].sum()):,}".replace(",", "."))
                
            if 'woz' in filtered_data.columns:
                # Gewogen gemiddelde WOZ-waarde berekenen op basis van inwoners
                if 'inwoners' in filtered_data.columns and filtered_data['inwoners'].sum() > 0:
                    # Bereken gewogen gemiddelde: som(woz * inwoners) / som(inwoners)
                    gewogen_woz = (filtered_data['woz'] * filtered_data['inwoners']).sum() / filtered_data['inwoners'].sum()
                    # Vermenigvuldig met 1000 omdat de waarden in duizenden zijn
                    gewogen_woz_eur = gewogen_woz * 1000
                    st.metric("Gemiddelde WOZ-waarde", f"€ {int(gewogen_woz_eur):,}".replace(",", "."))
                else:
                    # Fallback naar regulier gemiddelde als inwoners niet beschikbaar zijn
                    gemiddelde_woz = filtered_data['woz'].mean() * 1000  # Vermenigvuldig met 1000
                    st.metric("Gemiddelde WOZ-waarde", f"€ {int(gemiddelde_woz):,}".replace(",", ".") + " (ongewogen)")
                    
            if 'reistijd_min' in filtered_data.columns:
                # Gemiddelde reistijd berekenen
                gem_reistijd = filtered_data['reistijd_min'].mean()
                st.metric("Gem. reistijd (min)", round(gem_reistijd, 1))
        
        # Top 5 PC4-gebieden op basis van marktaandeel
        st.subheader("Top 5 PC4-gebieden (hoogste marktaandeel)")
        
        # Bereken marktaandeel per PC4 (vermijd delen door nul)
        top_data = filtered_data.copy()
        top_data['marktaandeel'] = np.where(
            top_data['sterfte_2023'] > 0,
            top_data['uitvaarten_2023'] / top_data['sterfte_2023'] * 100,
            0
        )
        
        # Filter gebieden met ten minste 1 sterfgeval voor betekenisvolle ranking
        valid_data = top_data[top_data['sterfte_2023'] > 0]
        
        # Top 5 hoogste marktaandeel
        top5 = valid_data.sort_values(by='marktaandeel', ascending=False)[
            ['PC4', 'gemeente', 'woonplaats', 'marktaandeel', 'sterfte_2023', 'uitvaarten_2023']
        ].head(5)
        
        # Formatteer marktaandeel als percentage
        top5['marktaandeel'] = top5['marktaandeel'].round(2).astype(str) + '%'
        
        st.dataframe(top5)
        
        # Bottom 5 PC4-gebieden op basis van marktaandeel
        st.subheader("Laagste 5 PC4-gebieden (laagste marktaandeel)")
        
        # Bottom 5 laagste marktaandeel
        bottom5 = valid_data.sort_values(by='marktaandeel', ascending=True)[
            ['PC4', 'gemeente', 'woonplaats', 'marktaandeel', 'sterfte_2023', 'uitvaarten_2023']
        ].head(5)
        
        # Formatteer marktaandeel als percentage
        bottom5['marktaandeel'] = bottom5['marktaandeel'].round(2).astype(str) + '%'
        
        st.dataframe(bottom5)
    else:
        st.warning("Geen data beschikbaar voor statistieken.")

# Optionele ruwe data weergave
if st.checkbox("Toon ruwe data"):
    st.dataframe(filtered_data)