import streamlit as st
import pandas as pd
import geopandas as gpd
import plotly.express as px
import numpy as np
import os
import tempfile
from pathlib import Path
import io

# Aangepaste kleurenschalen
# Rood naar groen via grijs voor numerieke data
rood_grijs_groen_palette = ["#ff0000", "#ff4d4d", "#ff9999", "#ffcccc", "#e0e0e0", "#ccffcc", "#99ff99", "#4dff4d", "#00ff00"]

# Behoud de originele Monuta palette voor categorische data
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
        for col in ['inwoners', 'sterfte_2023', 'uitvaarten_2023', 'uitvaarten_2024', 'uitvaarten_2025', 'aantal_verzekerden', 'reistijd_min']:
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
    
    # Percentage verzekerden berekenen
    if 'aantal_verzekerden' in data.columns and 'inwoners' in data.columns:
        data['percentage_verzekerden'] = np.where(
            data['inwoners'] > 0,
            data['aantal_verzekerden'] / data['inwoners'] * 100,
            0
        )
    
    return data

# Vervang de huidige aggregate_to_gemeente functie met deze robuustere versie

def aggregate_to_gemeente(data):
    """
    Aggregeert data van PC4-niveau naar gemeenteniveau met uitgebreide foutenafhandeling.
    Probeert meerdere methoden om geometrieën samen te voegen, met fallbacks.
    """
    if 'gemeente' not in data.columns:
        st.warning("Gemeente kolom niet gevonden, kan niet aggregeren.")
        return data
    
    # Maak een kopie om de originele data niet te wijzigen
    data_copy = data.copy()
    
    # Aggregeer de numerieke kolommen
    numeric_columns = [
        'inwoners', 'sterfte_2023', 'uitvaarten_2023', 
        'uitvaarten_2024', 'uitvaarten_2025', 'aantal_verzekerden',
        'reistijd_min'
    ]
    
    # Selecteer alleen bestaande kolommen
    numeric_columns = [col for col in numeric_columns if col in data_copy.columns]
    
    # Groeperen op gemeente en aggregeren
    gemeente_aggs = {}
    
    # Voor numerieke kolommen die opgeteld moeten worden
    for col in numeric_columns:
        if col in data_copy.columns:
            gemeente_aggs[col] = 'sum'
    
    if 'reistijd_min' in data_copy.columns:
        gemeente_aggs['reistijd_min'] = 'mean'  # Gemiddelde reistijd
    
    # Aggregeer op gemeente
    gemeente_data = data_copy.groupby('gemeente').agg(gemeente_aggs).reset_index()
    
    # Bereken de afgeleide metrics opnieuw
    if 'sterfte_2023' in gemeente_data.columns and 'uitvaarten_2023' in gemeente_data.columns:
        gemeente_data['berekend_marktaandeel_2023'] = np.where(
            gemeente_data['sterfte_2023'] > 0,
            gemeente_data['uitvaarten_2023'] / gemeente_data['sterfte_2023'] * 100,
            0
        )
    
    # Percentage verzekerden berekenen
    if 'aantal_verzekerden' in gemeente_data.columns and 'inwoners' in gemeente_data.columns:
        gemeente_data['percentage_verzekerden'] = np.where(
            gemeente_data['inwoners'] > 0,
            gemeente_data['aantal_verzekerden'] / gemeente_data['inwoners'] * 100,
            0
        )
    
    # Maak een GeoPandas dataframe van het resultaat
    # Voor visualisatie hebben we geometrie nodig
    if isinstance(data, gpd.GeoDataFrame):
        try:
            # METHODE 1: Probeer eerst de standaard methode maar met een hogere simplificatie
            # Maak een kopie met sterk vereenvoudigde geometrieën
            simple_data = data.copy()
            # Vereenvoudig geometrieën agressiever voor dissolve
            simple_data['geometry'] = simple_data['geometry'].simplify(tolerance=0.01, preserve_topology=True)
            # Buffer met nul om kleine inconsistenties te repareren
            simple_data['geometry'] = simple_data['geometry'].buffer(0)
            
            gemeente_geometries = simple_data.dissolve(by='gemeente')
            
            # Samenvoegen van de geaggregeerde data met de geometrieën
            gemeente_gdf = gpd.GeoDataFrame(
                gemeente_data.merge(gemeente_geometries.reset_index()[['gemeente', 'geometry']], on='gemeente'),
                geometry='geometry'
            )
            
            st.success("Gemeenteniveau kaart succesvol gemaakt met vereenvoudigde geometrieën.")
            return gemeente_gdf
            
        except Exception as e1:
            st.warning(f"Fout bij het samenvoegen van vereenvoudigde geometrieën: {type(e1).__name__}. Probeer methode 2.")
            
            try:
                # METHODE 2: Probeer de dissolve per gemeente apart uit te voeren
                gemeentes = data['gemeente'].unique()
                all_geoms = []
                
                for gemeente in gemeentes:
                    try:
                        # Selecteer alle PC4-gebieden in deze gemeente
                        gemeente_data_subset = data[data['gemeente'] == gemeente]
                        # Probeer deze samen te voegen tot één geometrie
                        if len(gemeente_data_subset) > 0:
                            # Gebruik simplify en buffer om problemen te verminderen
                            gemeente_geom = gemeente_data_subset['geometry'].simplify(0.01).buffer(0)
                            # Probeer unary_union uit te voeren
                            try:
                                merged_geom = gemeente_geom.unary_union
                                all_geoms.append((gemeente, merged_geom))
                            except:
                                # Als unary_union faalt, neem gewoon de eerste geometrie
                                all_geoms.append((gemeente, gemeente_geom.iloc[0]))
                    except:
                        # Bij fouten, sla deze gemeente over
                        continue
                
                if all_geoms:
                    # Maak een nieuwe GeoDataFrame met de verzamelde geometrieën
                    gemeente_gdf_from_parts = gpd.GeoDataFrame(
                        [(g[0], g[1]) for g in all_geoms], 
                        columns=['gemeente', 'geometry'],
                        geometry='geometry'
                    )
                    
                    # Samenvoegen met de geaggregeerde data
                    gemeente_gdf = gpd.GeoDataFrame(
                        gemeente_data.merge(gemeente_gdf_from_parts, on='gemeente'),
                        geometry='geometry'
                    )
                    
                    st.success("Gemeenteniveau kaart succesvol gemaakt met per-gemeente verwerking.")
                    return gemeente_gdf
                else:
                    raise Exception("Geen geometrieën konden worden samengevoegd")
                    
            except Exception as e2:
                st.warning(f"Fout bij methode 2 voor geometrieën: {type(e2).__name__}. Probeer methode 3.")
                
                try:
                    # METHODE 3: Gebruik de centroïde van elke gemeente als punt
                    # Groepeer per gemeente en bereken de gemiddelde centroïde
                    gemeente_centroids = {}
                    
                    for gemeente in data['gemeente'].unique():
                        gemeente_data_subset = data[data['gemeente'] == gemeente]
                        if len(gemeente_data_subset) > 0:
                            # Bereken een representatief punt voor deze gemeente
                            points = [geom.centroid for geom in gemeente_data_subset['geometry']]
                            x_coords = [p.x for p in points]
                            y_coords = [p.y for p in points]
                            # Gemiddelde coördinaat
                            avg_x = sum(x_coords) / len(x_coords)
                            avg_y = sum(y_coords) / len(y_coords)
                            from shapely.geometry import Point
                            gemeente_centroids[gemeente] = Point(avg_x, avg_y)
                    
                    # Maak een GeoDataFrame met de centroïde-punten
                    gemeente_points = gpd.GeoDataFrame(
                        [(gemeente, centroid) for gemeente, centroid in gemeente_centroids.items()], 
                        columns=['gemeente', 'geometry'],
                        geometry='geometry'
                    )
                    
                    # Samenvoegen met de geaggregeerde data
                    gemeente_gdf = gpd.GeoDataFrame(
                        gemeente_data.merge(gemeente_points, on='gemeente'),
                        geometry='geometry'
                    )
                    
                    st.warning("Gemeenteniveau kaart gemaakt met centroïden (punten) in plaats van polygonen.")
                    return gemeente_gdf
                    
                except Exception as e3:
                    st.error(f"Alle methoden voor het maken van gemeenteniveau geometrieën zijn mislukt: {type(e3).__name__}.")
                    # Als alle methodes mislukken, retourneer de data zonder geometrieën
                    return gemeente_data
    else:
        # Als het geen GeoDataFrame is, geef een waarschuwing
        st.warning("Kan geen kaart maken zonder geometrie data.")
        return gemeente_data

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
    "Sterfte 2023": "sterfte_2023",
    "Uitvaarten 2023": "uitvaarten_2023",
    "Uitvaarten 2024": "uitvaarten_2024",
    "Uitvaarten 2025": "uitvaarten_2025",
    "Aantal Verzekerden": "aantal_verzekerden",
    "Percentage Verzekerden": "percentage_verzekerden",
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

# Selectie van visualisatie niveau
visualisatie_niveau = st.sidebar.radio(
    "Visualiseer op niveau:",
    options=["Postcode (PC4)", "Gemeente"],
    index=0  # Standaard: Postcode niveau
)

# Controleer welke kolommen beschikbaar zijn
available_columns = []
for display_name, column_name in column_mapping.items():
    if column_name in merged_data.columns or column_name == 'berekend_marktaandeel_2023' or column_name == 'percentage_verzekerden':
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
            
            total_verzekerden = filtered_data['aantal_verzekerden'].sum() if 'aantal_verzekerden' in filtered_data.columns else 0
            percentage_verzekerden = (total_verzekerden / total_inwoners) * 100 if total_inwoners > 0 else 0
            
            gem_reistijd = filtered_data['reistijd_min'].mean() if 'reistijd_min' in filtered_data.columns else 0
            
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
                    'Totaal inwoners', 'Sterfte 2023', 
                    'Uitvaarten 2023', 'Uitvaarten 2024', 'Uitvaarten 2025',
                    'Aantal verzekerden', 'Percentage verzekerden (%)', 'Gemiddelde reistijd (min)'
                ],
                'Waarde': [
                    gebied_naam, len(filtered_data), round(overall_marktaandeel, 2),
                    int(total_inwoners), int(total_sterfte),
                    int(total_uitvaarten), int(total_uitvaarten_2024), int(total_uitvaarten_2025),
                    int(total_verzekerden), round(percentage_verzekerden, 2), round(gem_reistijd, 1)
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

# Vervang het visualisatiegedeelte (rond regel 560-615) met deze aangepaste versie

with col1:
    niveau_label = "Gemeente" if visualisatie_niveau == "Gemeente" else "PC4"
    st.subheader(f"{niveau_label} Kaart - {selected_column_display}")
    
    # Check of er data is om te visualiseren
    if len(filtered_data) > 0:
        # Bepaal de te visualiseren data op basis van gekozen niveau
        if visualisatie_niveau == "Gemeente":
            # Aggregeer data naar gemeenteniveau
            visualisation_data = aggregate_to_gemeente(filtered_data)
            
            # Controleer of visualisation_data een GeoDataFrame is met geometrie kolom
            is_geodataframe = isinstance(visualisation_data, gpd.GeoDataFrame) and 'geometry' in visualisation_data.columns
            
            if not is_geodataframe:
                st.warning("Kon geen gemeente-niveau kaart maken door problemen met geometrieën. Teruggevallen op PC4-niveau.")
                visualisation_data = filtered_data
            else:
                st.info(f"Kaart toont {len(visualisation_data)} gemeenten.")
        else:
            # Gebruik PC4 niveau (standaard)
            visualisation_data = filtered_data
        
        # Controleer opnieuw of we een geldige GeoDataFrame hebben
        if not isinstance(visualisation_data, gpd.GeoDataFrame) or 'geometry' not in visualisation_data.columns:
            st.error("Kan geen kaart maken zonder geldige geometrieën.")
        else:
            # Maak een kopie voor visualisatie om de originele data intact te houden
            viz_data = visualisation_data.copy()
            
            # Check geometrietype (polygonen of punten)
            from shapely.geometry import Point
            is_point_geometry = False
            if len(viz_data) > 0:
                # Controleer het type van de eerste geometrie
                first_geom = viz_data.iloc[0]['geometry']
                is_point_geometry = isinstance(first_geom, Point)
            
            # Check of we categorische of numerieke data visualiseren
            is_categorical = False
            selected_col = selected_column  # standaard kolomnaam
            
            # Als het een categorische kolom is
            if selected_column in viz_data.columns and (pd.api.types.is_object_dtype(viz_data[selected_column]) or pd.api.types.is_string_dtype(viz_data[selected_column])):
                is_categorical = True
                viz_data[selected_column] = viz_data[selected_column].fillna("Onbekend").astype(str)
            
            try:
                # Kies de juiste visualisatiemethode op basis van geometrietype
                if is_point_geometry:
                    # Voor punt-geometrieën gebruiken we een andere visualisatie
                    if is_categorical:
                        # Categorische data met punten
                        fig = px.scatter_mapbox(
                            viz_data,
                            lat=viz_data.geometry.y,
                            lon=viz_data.geometry.x,
                            color=selected_col,
                            color_discrete_sequence=monuta_palette,
                            size_max=15,  # Max grootte van punten
                            zoom=6.5,
                            mapbox_style="carto-positron",
                            center={"lat": 52.1326, "lon": 5.2913},
                            hover_data=['gemeente'],
                            labels={selected_col: selected_column_display}
                        )
                    else:
                        # Numerieke data met punten
                        fig = px.scatter_mapbox(
                            viz_data,
                            lat=viz_data.geometry.y,
                            lon=viz_data.geometry.x,
                            color=selected_column,
                            color_continuous_scale=rood_grijs_groen_palette,
                            size_max=15,  # Max grootte van punten
                            zoom=6.5,
                            mapbox_style="carto-positron",
                            center={"lat": 52.1326, "lon": 5.2913},
                            hover_data=['gemeente'],
                            labels={selected_column: selected_column_display}
                        )
                else:
                    # Voor polygoon-geometrieën gebruiken we de originele visualisatie
                    if is_categorical:
                        # Categorische data met polygonen
                        fig = px.choropleth_mapbox(
                            viz_data,
                            geojson=viz_data.geometry,
                            locations=viz_data.index,
                            color=selected_col,
                            color_discrete_sequence=monuta_palette,
                            mapbox_style="carto-positron",
                            zoom=6.5,
                            center={"lat": 52.1326, "lon": 5.2913},
                            opacity=0.7,
                            hover_data=['gemeente', 'woonplaats', selected_col] if visualisatie_niveau == "Postcode (PC4)" and 'woonplaats' in viz_data.columns else ['gemeente', selected_col],
                            labels={selected_col: selected_column_display}
                        )
                    else:
                        # Numerieke data met polygonen
                        fig = px.choropleth_mapbox(
                            viz_data,
                            geojson=viz_data.geometry,
                            locations=viz_data.index,
                            color=selected_column,
                            color_continuous_scale=rood_grijs_groen_palette,
                            mapbox_style="carto-positron",
                            zoom=6.5,
                            center={"lat": 52.1326, "lon": 5.2913},
                            opacity=0.7,
                            hover_data=['gemeente', 'woonplaats', selected_column] if visualisatie_niveau == "Postcode (PC4)" and 'woonplaats' in viz_data.columns else ['gemeente', selected_column],
                            labels={selected_column: selected_column_display}
                        )
                
                # Layout aanpassen
                fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=600)
                st.plotly_chart(fig, use_container_width=True)
            except Exception as e:
                st.error(f"Fout bij het maken van de kaart: {type(e).__name__}. Probeer een andere weergave of dataset.")
                st.code(str(e), language="python")
                
                # Als de visualisatie faalt, toon een tabel met de aggregated data als alternatief
                st.subheader("Alternatieve weergave (tabel)")
                display_data = viz_data.drop(columns=['geometry'])
                st.dataframe(display_data)
    else:
        st.warning("Geen data beschikbaar met de huidige filters.")

with col2:
    niveau_label = "gemeente" if visualisatie_niveau == "Gemeente" else "PC4-gebied"
    st.subheader(f"Statistieken ({visualisatie_niveau})")
    
    if len(filtered_data) > 0:
        # Bepaal de data voor statistieken op basis van niveau
        if visualisatie_niveau == "Gemeente":
            stats_data = aggregate_to_gemeente(filtered_data)
            if isinstance(stats_data, pd.DataFrame) and len(stats_data) > 0:
                # Gebruik geaggregeerde data voor statistieken
                pass
            else:
                stats_data = filtered_data
                st.warning("Kon statistieken niet berekenen op gemeenteniveau. Teruggevallen op PC4-niveau.")
        else:
            stats_data = filtered_data
            
        # Bereken het algehele marktaandeel voor de geselecteerde regio's
        total_sterfte = stats_data['sterfte_2023'].sum()
        total_uitvaarten = stats_data['uitvaarten_2023'].sum()
        
        if total_sterfte > 0:
            overall_marktaandeel = (total_uitvaarten / total_sterfte) * 100
        else:
            overall_marktaandeel = 0
            
        # Percentage verzekerden berekenen
        total_inwoners = stats_data['inwoners'].sum()
        total_verzekerden = stats_data['aantal_verzekerden'].sum()
        if total_inwoners > 0:
            percentage_verzekerden = (total_verzekerden / total_inwoners) * 100
        else:
            percentage_verzekerden = 0
        
        # Statistieken in twee kolommen weergeven
        stat_col1, stat_col2 = st.columns(2)
        
        with stat_col1:
            # Eerste kolom statistieken
            st.metric(f"Aantal {niveau_label}en", len(stats_data))
            st.metric("Marktaandeel 2023", f"{round(overall_marktaandeel, 2)}%")
            
            # Controleer en bereken inwoners totaal
            if 'inwoners' in stats_data.columns:
                total_inwoners = stats_data['inwoners'].sum()
                st.metric("Totaal inwoners", f"{int(total_inwoners):,}".replace(",", "."))
                
            # Percentage verzekerden
            st.metric("Percentage verzekerden", f"{round(percentage_verzekerden, 2)}%")
        
        with stat_col2:
            # Tweede kolom statistieken
            st.metric("Sterfte 2023", int(total_sterfte))
            st.metric("Uitvaarten 2023", int(total_uitvaarten))
            
            # Nieuwe statistieken toevoegen
            if 'uitvaarten_2024' in stats_data.columns:
                st.metric("Uitvaarten 2024", int(stats_data['uitvaarten_2024'].sum()))
                
            if 'uitvaarten_2025' in stats_data.columns:
                st.metric("Uitvaarten 2025", int(stats_data['uitvaarten_2025'].sum()))
                
            if 'aantal_verzekerden' in stats_data.columns:
                st.metric("Aantal verzekerden", f"{int(stats_data['aantal_verzekerden'].sum()):,}".replace(",", "."))
                    
            if 'reistijd_min' in stats_data.columns:
                # Gemiddelde reistijd berekenen
                gem_reistijd = stats_data['reistijd_min'].mean()
                st.metric("Gem. reistijd (min)", round(gem_reistijd, 1))
        
        # Top 5 gebieden op basis van marktaandeel
        st.subheader(f"Top 5 {niveau_label}en (hoogste marktaandeel)")
        
        # Bereken marktaandeel per gebied (vermijd delen door nul)
        top_data = stats_data.copy()
        top_data['marktaandeel'] = np.where(
            top_data['sterfte_2023'] > 0,
            top_data['uitvaarten_2023'] / top_data['sterfte_2023'] * 100,
            0
        )
        
        # Bereken percentage verzekerden per gebied (vermijd delen door nul)
        top_data['perc_verzekerden'] = np.where(
            top_data['inwoners'] > 0,
            top_data['aantal_verzekerden'] / top_data['inwoners'] * 100,
            0
        )
        
        # Filter gebieden met ten minste 1 sterfgeval voor betekenisvolle ranking
        valid_data = top_data[top_data['sterfte_2023'] > 0]
        
        # Bepaal welke kolommen te tonen in de tabel
        if visualisatie_niveau == "Gemeente":
            columns_to_display = ['gemeente', 'marktaandeel', 'perc_verzekerden', 'sterfte_2023', 'uitvaarten_2023']
        else:
            columns_to_display = ['PC4', 'gemeente', 'woonplaats', 'marktaandeel', 'perc_verzekerden', 'sterfte_2023', 'uitvaarten_2023']
            
        # Top 5 hoogste marktaandeel
        top5 = valid_data.sort_values(by='marktaandeel', ascending=False)[columns_to_display].head(5)
        
        # Formatteer marktaandeel en percentage verzekerden als percentage
        top5['marktaandeel'] = top5['marktaandeel'].round(2).astype(str) + '%'
        top5['perc_verzekerden'] = top5['perc_verzekerden'].round(2).astype(str) + '%'
        
        # Hernoem kolommen voor betere weergave
        top5 = top5.rename(columns={'marktaandeel': 'Marktaandeel', 'perc_verzekerden': 'Perc. verzekerden'})
        
        st.dataframe(top5)
        
        # Bottom 5 gebieden op basis van marktaandeel
        st.subheader(f"Laagste 5 {niveau_label}en (laagste marktaandeel)")
        
        # Bottom 5 laagste marktaandeel
        bottom5 = valid_data.sort_values(by='marktaandeel', ascending=True)[columns_to_display].head(5)
        
        # Formatteer marktaandeel en percentage verzekerden als percentage
        bottom5['marktaandeel'] = bottom5['marktaandeel'].round(2).astype(str) + '%'
        bottom5['perc_verzekerden'] = bottom5['perc_verzekerden'].round(2).astype(str) + '%'
        
        # Hernoem kolommen voor betere weergave
        bottom5 = bottom5.rename(columns={'marktaandeel': 'Marktaandeel', 'perc_verzekerden': 'Perc. verzekerden'})
        
        st.dataframe(bottom5)
    else:
        st.warning("Geen data beschikbaar voor statistieken.")

# Optionele ruwe data weergave
if st.checkbox("Toon ruwe data"):
    # Toon data afhankelijk van het geselecteerde niveau
    if visualisatie_niveau == "Gemeente" and len(filtered_data) > 0:
        gemeente_data = aggregate_to_gemeente(filtered_data)
        if isinstance(gemeente_data, pd.DataFrame) and len(gemeente_data) > 0:
            # Toon de data zonder geometrie kolom
            display_data = gemeente_data.drop(columns=['geometry']) if 'geometry' in gemeente_data.columns else gemeente_data
            st.dataframe(display_data)
        else:
            display_data = filtered_data.drop(columns=['geometry']) if 'geometry' in filtered_data.columns else filtered_data
            st.dataframe(display_data)
            st.warning("Kon geen gemeente-niveau data genereren. Toon PC4-niveau data.")
    else:
        display_data = filtered_data.drop(columns=['geometry']) if 'geometry' in filtered_data.columns else filtered_data
        st.dataframe(display_data)
                
