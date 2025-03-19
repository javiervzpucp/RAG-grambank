import pandas as pd
import requests
from rdflib import Graph, Namespace, Literal, URIRef, BNode
from rdflib.namespace import RDF, RDFS, XSD, GEO, DC, DCTERMS, SKOS, OWL

# Configurar namespaces
LING = Namespace("http://purl.org/linguistics#")
GLOTTO = Namespace("https://glottolog.org/resource/languoid/id/")
GRAMBANK = Namespace("https://grambank.clld.org/parameters/")
WIKIDATA = Namespace("http://www.wikidata.org/entity/")

# Cargar el grafo RDF existente
g = Graph()
g.parse("grambank_sudamerica.ttl", format="turtle")

# SPARQL para obtener información detallada de las lenguas desde Wikidata
SPARQL_QUERY = """
SELECT ?lang ?iso ?wikidata ?country ?countryLabel ?linguisticTypologyLabel ?numSpeakers ?unescoStatus ?unescoStatusLabel WHERE {
  ?lang wdt:P220 ?iso.
  OPTIONAL { ?lang wdt:P17 ?country. ?country rdfs:label ?countryLabel FILTER (lang(?countryLabel) = "en") }
  OPTIONAL { ?lang wdt:P3866 ?linguisticTypology. ?linguisticTypology rdfs:label ?linguisticTypologyLabel FILTER (lang(?linguisticTypologyLabel) = "en") }
  OPTIONAL { ?lang wdt:P1098 ?numSpeakers. }
  OPTIONAL { ?lang wdt:P3801 ?unescoStatus. ?unescoStatus rdfs:label ?unescoStatusLabel FILTER (lang(?unescoStatusLabel) = "en") }
  BIND(STR(?lang) AS ?wikidata)
}
"""

def obtener_datos_wikidata():
    print("Obteniendo información de Wikidata...")
    sparql_url = "https://query.wikidata.org/sparql"
    headers = {"Accept": "application/sparql-results+json"}
    response = requests.get(sparql_url, params={"query": SPARQL_QUERY, "format": "json"}, headers=headers)
    
    if response.status_code == 200:
        results = response.json()["results"]["bindings"]
        wikidata_info = {}
        
        for item in results:
            iso = item["iso"]["value"]
            wikidata_info[iso] = {
                "wikidata": item["wikidata"]["value"],
                "country": item.get("country", {}).get("value"),
                "countryLabel": item.get("countryLabel", {}).get("value"),
                "linguisticTypology": item.get("linguisticTypologyLabel", {}).get("value"),
                "numSpeakers": item.get("numSpeakers", {}).get("value"),
                "unescoStatus": item.get("unescoStatus", {}).get("value"),
                "unescoStatusLabel": item.get("unescoStatusLabel", {}).get("value")
            }
        
        return wikidata_info
    else:
        print("⚠️ Error al obtener datos de Wikidata.")
        return {}

wikidata_map = obtener_datos_wikidata()

def actualizar_grafo_con_wikidata():
    print("Actualizando el grafo con información de Wikidata...")
    for lang_uri in g.subjects(RDF.type, LING.Language):
        iso_code = g.value(lang_uri, LING.isoCode)
        if iso_code and str(iso_code) in wikidata_map:
            data = wikidata_map[str(iso_code)]
            wikidata_uri = URIRef(data["wikidata"])
            g.add((lang_uri, OWL.sameAs, wikidata_uri))
            
            if data.get("country"):
                country_uri = URIRef(data["country"])
                g.add((country_uri, RDF.type, LING.Country))
                g.add((country_uri, RDFS.label, Literal(data["countryLabel"], lang="en")))
                g.add((lang_uri, LING.spokenInCountry, country_uri))
                g.add((country_uri, LING.hasLanguage, lang_uri))
            
            if data.get("linguisticTypology"):
                g.add((lang_uri, LING.linguisticTypology, Literal(data["linguisticTypology"], lang="en")))
            
            if data.get("numSpeakers"):
                try:
                    num_speakers = int(float(data["numSpeakers"]))
                    g.add((lang_uri, LING.numberOfSpeakers, Literal(num_speakers, datatype=XSD.integer)))
                except ValueError:
                    pass  # Evita errores en valores no numéricos
            
            if data.get("unescoStatus"):
                unesco_uri = URIRef(data["unescoStatus"])
                g.add((unesco_uri, RDF.type, LING.UnescoStatus))
                g.add((unesco_uri, RDFS.label, Literal(data["unescoStatusLabel"], lang="en")))
                g.add((lang_uri, LING.unescoLanguageStatus, unesco_uri))
                g.add((unesco_uri, LING.hasLanguage, lang_uri))

            # Agregar información de Wikidata a cada lengua con etiquetas en texto
            g.add((lang_uri, DC.source, wikidata_uri))
            if data.get("countryLabel"):
                g.add((lang_uri, DCTERMS.spatial, Literal(data["countryLabel"], lang="en")))
            if data.get("linguisticTypology"):
                g.add((lang_uri, LING.linguisticTypology, Literal(data["linguisticTypology"], lang="en")))
            if data.get("numSpeakers"):
                g.add((lang_uri, LING.numberOfSpeakers, Literal(data["numSpeakers"], datatype=XSD.integer)))
            if data.get("unescoStatusLabel"):
                g.add((lang_uri, DCTERMS.subject, Literal(data["unescoStatusLabel"], lang="en")))

def main():
    actualizar_grafo_con_wikidata()
    print("\nGuardando grafo actualizado...")
    g.serialize("grambank_sudamerica_actualizado.ttl", format="turtle")
    print(f"✅ KG actualizado! Triples totales: {len(g):,}")

if __name__ == "__main__":
    main()
