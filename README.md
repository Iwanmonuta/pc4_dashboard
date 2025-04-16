# PC4 Dashboard Nederland

Een interactief dashboard voor de visualisatie van gegevens op PC4-niveau (postcodegebieden) in Nederland, speciaal ontwikkeld voor Monuta.

## Functionaliteiten

- Visualisatie van marktaandeel, demografische gegevens en andere metrieken op postcodeniveau
- Interactieve filters op provincie, gemeente, woonplaats en meer
- Exportmogelijkheden naar CSV
- Gedetailleerde statistieken per geselecteerd gebied

## Installatie en Gebruik

### Lokaal gebruik

1. Kloon deze repository
2. Installeer de benodigde packages:
   ```
   pip install -r requirements.txt
   ```
3. Start de app:
   ```
   streamlit run app.py
   ```

### Online gebruik

De app is live beschikbaar op [Streamlit Cloud](https://your-streamlit-cloud-url.streamlit.app).

## Benodigde Bestanden

Voor het gebruik van de app zijn de volgende bestanden nodig:
1. Excel bestand (PC4_verrijkt.xlsx) met PC4 gegevens
2. Shapefile (PC4.shp) met Nederlandse postcodegebieden
3. Bijbehorende .shx bestand
4. Bijbehorende .dbf bestand
5. Bijbehorende .prj bestand

## Technologie

Deze app is gebouwd met:
- [Streamlit](https://streamlit.io/)
- [Pandas](https://pandas.pydata.org/)
- [GeoPandas](https://geopandas.org/)
- [Plotly](https://plotly.com/)

## Bijdragen

Bijdragen zijn welkom! Maak een fork van deze repository en stuur een pull request.
