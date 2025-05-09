# PC4 & Gemeente Dashboard Nederland

Een interactief dashboard voor de visualisatie van gegevens op PC4-niveau (postcodegebieden) en gemeenteniveau in Nederland, speciaal ontwikkeld voor Monuta.

## Functionaliteiten

- Visualisatie van marktaandeel, demografische gegevens en andere metrieken op zowel postcode- als gemeenteniveau
- Interactieve filters op provincie, gemeente, woonplaats en meer
- Flexibele weergave met rode (laag) naar groene (hoog) kleurschaal via grijs (middenwaardes)
- Exportmogelijkheden naar CSV voor zowel data als statistieken
- Gedetailleerde statistieken per geselecteerd gebied
- Analyse van top/laagste gebieden op basis van marktaandeel en percentage verzekerden

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

## Belangrijkste metrics

- Marktaandeel 2023: Percentage uitvaarten t.o.v. sterfte
- Percentage Verzekerden: Aantal verzekerden t.o.v. aantal inwoners
- Uitvaarten: Gegevens over 2023, 2024 en 2025
- Reistijd: Gemiddelde reistijd in minuten

## Aggregatie op gemeenteniveau

Het dashboard biedt de mogelijkheid om gegevens te aggregeren en visualiseren op gemeenteniveau, wat nuttig is voor:

- Strategische analyse op hoger niveau
- Vergelijking tussen gemeenten
- Planning van marketingactiviteiten op gemeentelijk niveau

De gemeenteweergave berekent automatisch:

- Totaal aantal inwoners, sterfte en uitvaarten per gemeente
- Gemiddelde marktaandelen en percentages verzekerden
- Gemiddelde reistijden

## Technologie

Deze app is gebouwd met:
- [Streamlit](https://streamlit.io/)
- [Pandas](https://pandas.pydata.org/)
- [GeoPandas](https://geopandas.org/)
- [Plotly](https://plotly.com/)

## Bijdragen

Bijdragen zijn welkom! Maak een fork van deze repository en stuur een pull request.