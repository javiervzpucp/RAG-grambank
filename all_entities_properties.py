# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 16:57:52 2025

@author: jveraz
"""

from rdflib import Graph, URIRef, Literal, RDFS, RDF
import json

# Cargar el grafo RDF
g = Graph()
g.parse("grambank_sudamerica_actualizado.ttl", format="turtle")

def get_all_properties(entity_uri):
    """
    Obtiene todas las propiedades y sus valores para una entidad dada.
    """
    properties = {}
    for p, o in g.predicate_objects(entity_uri):
        # Convertir URIs a nombres legibles
        p_name = str(p).split("#")[-1] if "#" in str(p) else str(p)
        if isinstance(o, URIRef):
            o_name = str(o).split("#")[-1] if "#" in str(o) else str(o)
        elif isinstance(o, Literal):
            o_name = str(o)
        else:
            o_name = str(o)
        
        # Agregar la propiedad y su valor al diccionario
        if p_name not in properties:
            properties[p_name] = []
        properties[p_name].append(o_name)
    
    return properties

def get_all_entities_properties():
    """
    Obtiene todas las propiedades y sus valores para todas las entidades en el grafo.
    """
    entities_properties = {}
    for entity_uri in g.subjects(RDF.type, None):
        entity_name = str(entity_uri).split("#")[-1] if "#" in str(entity_uri) else str(entity_uri)
        entities_properties[entity_name] = get_all_properties(entity_uri)
    
    return entities_properties

# Obtener todas las propiedades para todas las entidades
all_entities_properties = get_all_entities_properties()

# Imprimir las propiedades de la primera entidad
first_entity = list(all_entities_properties.keys())[0]
print(f"Propiedades de la entidad '{first_entity}':")
for prop, values in all_entities_properties[first_entity].items():
    print(f"- {prop}: {', '.join(values)}")
    
# Guardar en un archivo JSON
with open("all_entities_properties.json", "w", encoding="utf-8") as f:
    json.dump(all_entities_properties, f, indent=4, ensure_ascii=False)

print("✅ Propiedades guardadas en 'all_entities_properties.json'")