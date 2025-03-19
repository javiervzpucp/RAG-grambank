# -*- coding: utf-8 -*-
"""
Created on Tue Mar 18 17:07:17 2025

@author: jveraz
"""

import json
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# Cargar el archivo JSON con las propiedades de las entidades
with open("all_entities_properties.json", "r", encoding="utf-8") as f:
    all_entities_properties = json.load(f)

# Verificar la carga
print(f"Se cargaron {len(all_entities_properties)} entidades.")

# Función para generar descripciones textuales
def generate_entity_description(properties):
    """
    Convierte las propiedades de una entidad en una descripción textual.
    """
    description = []
    for prop, values in properties.items():
        description.append(f"{prop}: {', '.join(values)}")
    return ". ".join(description)

# Función para generar descripciones estructurales del grafo
def generate_structural_description(entity_uri, properties, all_entities_properties):
    """
    Convierte la estructura del grafo en una descripción textual.
    """
    structural_description = []
    
    # Relaciones con países
    if "spokenInCountry" in properties:
        country_uris = properties["spokenInCountry"]
        countries = []
        for country_uri in country_uris:
            if country_uri in all_entities_properties:
                country_label = all_entities_properties[country_uri].get("label", ["País desconocido"])[0]
                countries.append(country_label)
        if countries:
            structural_description.append(f"Se habla en: {', '.join(countries)}")
    
    # Relaciones con familias lingüísticas
    if "languageFamily" in properties:
        family_uris = properties["languageFamily"]
        families = []
        for family_uri in family_uris:
            if family_uri in all_entities_properties:
                family_label = all_entities_properties[family_uri].get("label", ["Familia desconocida"])[0]
                families.append(family_label)
        if families:
            structural_description.append(f"Pertenece a la familia lingüística: {', '.join(families)}")
    
    # Relaciones con rasgos gramaticales
    if "hasFeaturePresent" in properties:
        features = properties["hasFeaturePresent"]
        structural_description.append(f"Tiene los siguientes rasgos gramaticales: {', '.join(features)}")
    
    if "hasFeatureAbsent" in properties:
        features = properties["hasFeatureAbsent"]
        structural_description.append(f"No tiene los siguientes rasgos gramaticales: {', '.join(features)}")
    
    return ". ".join(structural_description)

# Generar descripciones textuales y estructurales para todas las entidades
entity_descriptions = []
entity_uris = list(all_entities_properties.keys())
for entity_uri in entity_uris:
    properties = all_entities_properties[entity_uri]
    
    # Descripción textual de las propiedades
    text_description = generate_entity_description(properties)
    
    # Descripción estructural del grafo
    structural_description = generate_structural_description(entity_uri, properties, all_entities_properties)
    
    # Combinar ambas descripciones
    full_description = f"{text_description}. {structural_description}"
    entity_descriptions.append(full_description)

# Inicializar el modelo de embeddings
model = SentenceTransformer("sentence-transformers/multi-qa-mpnet-base-dot-v1")

# Generar embeddings
entity_embeddings = model.encode(entity_descriptions)

# Crear índice FAISS
dimension = entity_embeddings.shape[1]  # Dimensión de los embeddings
index = faiss.IndexFlatIP(dimension)  # Índice para similitud de coseno
index.add(entity_embeddings)  # Añadir embeddings al índice

# Guardar el índice para uso futuro
faiss.write_index(index, "grambank_entity_index.faiss")

# Guardar los URIs de las entidades para referencia
with open("entity_uris.txt", "w", encoding="utf-8") as f:
    for uri in entity_uris:
        f.write(f"{uri}\n")

print("✅ Embeddings generados y guardados en 'grambank_entity_index.faiss' y 'entity_uris.txt'.")

# Verificar la dimensión del índice FAISS
print("Dimensión del índice FAISS:", index.d)