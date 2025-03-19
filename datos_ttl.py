import pandas as pd
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, GEO, DC, DCTERMS, SKOS

# Configurar namespaces
LING = Namespace("http://purl.org/linguistics#")
GLOTTO = Namespace("https://glottolog.org/resource/languoid/id/")
GRAMBANK = Namespace("https://grambank.clld.org/parameters/")
WIKIDATA = Namespace("https://www.wikidata.org/wiki/")

# Crear grafo RDF
g = Graph()

# Vincular namespaces
namespaces = {
    "ling": LING,
    "glotto": GLOTTO,
    "gb": GRAMBANK,
    "wikidata": WIKIDATA,
    "geo": GEO,
    "dc": DC,
    "dcterms": DCTERMS,
    "skos": SKOS
}

for prefix, uri in namespaces.items():
    g.bind(prefix, uri)

# Cargar datos desde el nuevo archivo unificado
datos = pd.read_csv("DATOS.csv").dropna(how='all')  # Eliminar filas completamente vacías

# Procesar familias lingüísticas y agregar sus lenguas
def procesar_familias():
    print("Procesando familias lingüísticas...")
    familias = datos[['Family_level_ID', 'Family_name', 'lineage']].drop_duplicates().dropna()
    for _, row in familias.iterrows():
        familia_uri = URIRef(GLOTTO[row['Family_level_ID']])
        g.add((familia_uri, RDF.type, LING.LanguageFamily))
        g.add((familia_uri, RDFS.label, Literal(row['Family_name'])))
        if pd.notna(row['lineage']):
            g.add((familia_uri, LING.lineage, Literal(row['lineage'])))
        
        # Agregar lenguas de la familia
        lenguas = datos[datos['Family_level_ID'] == row['Family_level_ID']]['Glottocode'].dropna().unique()
        for lang in lenguas:
            lang_uri = URIRef(GLOTTO[lang])
            g.add((familia_uri, LING.hasLanguage, lang_uri))

# Procesar lenguas
def procesar_lenguas():
    print("Procesando lenguas...")
    for _, row in datos.drop_duplicates(subset=['Glottocode']).iterrows():
        lang_uri = URIRef(GLOTTO[row['Glottocode']])
        g.add((lang_uri, RDF.type, LING.Language))
        g.add((lang_uri, RDFS.label, Literal(row['Name'])))
        g.add((lang_uri, LING.glottocode, Literal(row['Glottocode'])))
        if pd.notna(row['Isocode']):
            g.add((lang_uri, LING.isoCode, Literal(row['Isocode'])))
        if pd.notna(row['Family_level_ID']):
            family_uri = URIRef(GLOTTO[row['Family_level_ID']])
            g.add((lang_uri, LING.languageFamily, family_uri))
        if pd.notna(row['Latitude']) and pd.notna(row['Longitude']):
            geo_uri = BNode()
            g.add((geo_uri, RDF.type, GEO.Point))
            g.add((geo_uri, GEO.lat, Literal(float(row['Latitude']), datatype=XSD.float)))
            g.add((geo_uri, GEO.long, Literal(float(row['Longitude']), datatype=XSD.float)))
            g.add((lang_uri, GEO.location, geo_uri))

# Procesar rasgos gramaticales y su relación con familias
def procesar_rasgos():
    print("Procesando rasgos...")
    rasgos = datos[['Parameter_ID', 'Name_Parameter', 'Description', 'Main_domain', 'Finer_grouping']].drop_duplicates().dropna()
    for _, row in rasgos.iterrows():
        feature_uri = URIRef(GRAMBANK[row['Parameter_ID']])
        g.add((feature_uri, RDF.type, LING.GrammaticalFeature))
        g.add((feature_uri, RDFS.label, Literal(row['Name_Parameter'])))
        if pd.notna(row['Description']):
            g.add((feature_uri, RDFS.comment, Literal(row['Description'])))
        if pd.notna(row['Main_domain']):
            g.add((feature_uri, LING.mainDomain, Literal(row['Main_domain'])))
        if pd.notna(row['Finer_grouping']):
            g.add((feature_uri, LING.finerGrouping, Literal(row['Finer_grouping'])))

# Procesar valores y relaciones entre lenguas y rasgos
def procesar_valores():
    print("Creando relaciones entre lenguas y rasgos...")
    for _, row in datos.iterrows():
        lang_uri = URIRef(GLOTTO[row['Glottocode']])
        feature_uri = URIRef(GRAMBANK[row['Parameter_ID']])
        if row['Value'] == '1':
            g.add((lang_uri, LING.hasFeaturePresent, feature_uri))
        elif row['Value'] == '0':
            g.add((lang_uri, LING.hasFeatureAbsent, feature_uri))
        if pd.notna(row['Description_Value']):
            g.add((lang_uri, LING.featureValueDescription, Literal(row['Description_Value'])))

# Ejecutar proceso
def main():
    procesar_familias()
    procesar_lenguas()
    procesar_rasgos()
    procesar_valores()
    print("\nGuardando grafo...")
    g.serialize("grambank_sudamerica.ttl", format="turtle")
    print(f"✅ KG generado! Triples totales: {len(g):,}")

if __name__ == "__main__":
    main()
