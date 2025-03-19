import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from huggingface_hub import InferenceClient
from dotenv import load_dotenv
import os
import json

# Cargar la API Key de Hugging Face desde .env
load_dotenv()
HUGGINGFACE_API_KEY = os.getenv("HF_API_TOKEN")

# Cargar el índice FAISS y los URIs de las entidades
index = faiss.read_index("grambank_entity_index.faiss")
with open("entity_uris.txt", "r", encoding="utf-8") as f:
    entity_uris = [line.strip() for line in f.readlines()]

# Cargar el archivo JSON con las propiedades de las entidades
with open("all_entities_properties.json", "r", encoding="utf-8") as f:
    all_entities_properties = json.load(f)

# Inicializar el modelo de embeddings local
model = SentenceTransformer("multi-qa-mpnet-base-dot-v1")  

# Inicializar el generador (usando la API de Hugging Face)
generator_client = InferenceClient(
    model="mistralai/Mixtral-8x7B-Instruct-v0.1",  # Modelo para generación de texto
    token=HUGGINGFACE_API_KEY
)

# Diccionario keyword_to_property
keyword_to_property = {
    # Keywords relacionadas con el nombre de la lengua
    "nombre": "rdfs:label",
    "lengua": "rdfs:label",
    "idioma": "rdfs:label",
    "denominación": "rdfs:label",  # Sinónimo
    "etiqueta": "rdfs:label",      # Sinónimo

    # Keywords relacionadas con el código Glottolog
    "glottocode": "ling:glottocode",
    "código glottolog": "ling:glottocode",
    "identificador glottolog": "ling:glottocode",  # Sinónimo

    # Keywords relacionadas con el código ISO
    "iso": "ling:isoCode",
    "código iso": "ling:isoCode",
    "iso 639-3": "ling:isoCode",
    "identificador iso": "ling:isoCode",  # Sinónimo

    # Keywords relacionadas con la familia lingüística
    "familia": "ling:languageFamily",
    "familia lingüística": "ling:languageFamily",
    "grupo lingüístico": "ling:languageFamily",      # Sinónimo
    "clasificación familiar": "ling:languageFamily", # Sinónimo

    # Keywords relacionadas con la ubicación geográfica
    "ubicación": "geo:location",
    "región": "geo:location",
    "localización": "geo:location",  # Sinónimo
    "zona": "geo:location",          # Sinónimo

    # Keywords relacionadas con países
    "país": "ling:spokenInCountry",
    "nación": "ling:spokenInCountry",  # Sinónimo
    "territorio": "ling:spokenInCountry",  # Sinónimo

    # Keywords relacionadas con rasgos gramaticales
    "rasgo": "ling:hasFeaturePresent",
    "característica": "ling:hasFeaturePresent",      # Sinónimo
    "propiedad gramatical": "ling:hasFeaturePresent", # Sinónimo
    "atributo": "ling:hasFeaturePresent",            # Sinónimo

    # Keywords relacionadas con el número de hablantes
    "hablantes": "ling:numberOfSpeakers",
    "número de hablantes": "ling:numberOfSpeakers",  # Sinónimo
    "cantidad de hablantes": "ling:numberOfSpeakers", # Sinónimo
    "población hablante": "ling:numberOfSpeakers",   # Sinónimo

    # Keywords relacionadas con la tipología lingüística
    "tipología": "ling:linguisticTypology",
    "clasificación lingüística": "ling:linguisticTypology",  # Sinónimo
    "categorización": "ling:linguisticTypology",             # Sinónimo

    # Keywords relacionadas con el estado de la UNESCO
    "unesco": "ling:unescoLanguageStatus",
    "estado unesco": "ling:unescoLanguageStatus",      # Sinónimo
    "estado de la lengua": "ling:unescoLanguageStatus", # Sinónimo
    "clasificación unesco": "ling:unescoLanguageStatus", # Sinónimo
}

# Lista de países (puede ser dinámica o estática)
countries = {
    "Chile": "http://www.wikidata.org/entity/Q298",
    "Perú": "http://www.wikidata.org/entity/Q419",
    "Argentina": "http://www.wikidata.org/entity/Q414",
    # Agregar más países según sea necesario
}

def get_embedding(text):
    """
    Obtiene el embedding de un texto usando un modelo local.
    """
    return model.encode(text)  # Generar embedding localmente

def retrieve_entities(question, top_k=5):
    """
    Recupera las entidades más relevantes para una pregunta dada.
    Si la pregunta menciona un país, recupera las lenguas asociadas a ese país.
    """
    # Convertir la pregunta en un embedding usando el modelo local
    question_embedding = get_embedding(question).reshape(1, -1)  # Asegurar que sea 2D
    
    # Buscar en FAISS
    distances, indices = index.search(question_embedding, top_k)
    
    # Recuperar las entidades más relevantes
    retrieved_entities = [entity_uris[i] for i in indices[0]]
    
    # Identificar el país mencionado en la pregunta
    mentioned_country = None
    for country_name, country_uri in countries.items():
        if country_name.lower() in question.lower():
            mentioned_country = country_uri
            break
    
    # Si se menciona un país, recuperar las lenguas asociadas
    if mentioned_country and mentioned_country in all_entities_properties:
        # Recuperar las lenguas asociadas al país
        if "hasLanguage" in all_entities_properties[mentioned_country]:
            retrieved_entities.extend(all_entities_properties[mentioned_country]["hasLanguage"])
    
    return retrieved_entities

def filter_properties_by_keywords(properties, question):
    """
    Filtra las propiedades de una entidad basándose en las keywords de la pregunta.
    Asegura que el nombre de la lengua (label) siempre esté presente.
    """
    filtered_props = {}
    question_lower = question.lower()  # Convertir la pregunta a minúsculas
    
    # Asegurarse de que el nombre de la lengua esté presente
    if "label" in properties:
        filtered_props["label"] = properties["label"]
    
    # Capturar el país si la pregunta menciona un país específico
    for country_name in countries.keys():
        if country_name.lower() in question_lower and "http://purl.org/dc/terms/spatial" in properties:
            filtered_props["http://purl.org/dc/terms/spatial"] = properties["http://purl.org/dc/terms/spatial"]
            break  # Solo necesitamos capturar un país
    
    # Capturar otras propiedades relevantes
    for keyword, prop in keyword_to_property.items():
        if keyword in question_lower and prop in properties:
            filtered_props[prop] = properties[prop]
    
    return filtered_props

def generate_response(question):
    """
    Genera una respuesta basada en las entidades recuperadas.
    """
    # Recuperar entidades relevantes
    entities = retrieve_entities(question)
    
    # Construir el contexto con información filtrada
    context = []
    for entity_uri in entities:
        properties = all_entities_properties.get(entity_uri, {})
        
        # Filtrar propiedades basadas en las keywords de la pregunta
        filtered_props = filter_properties_by_keywords(properties, question)
        
        if filtered_props:  # Solo incluir entidades con propiedades relevantes
            description = f"Entidad: {filtered_props.get('label', 'Nombre no disponible')}\n"
            description += "Propiedades relevantes:\n"
            for prop, values in filtered_props.items():
                if prop != "label":  # Evitar repetir el nombre de la entidad
                    description += f"- {prop}: {', '.join(values)}\n"
            context.append(description)
        else:
            # Si no hay propiedades relevantes, incluir un contexto mínimo
            description = f"Entidad: {properties.get('label', 'Nombre no disponible')}\n"
            description += "Propiedades relevantes:\n"
            description += "- Información adicional no disponible\n"
            context.append(description)
    
    context = "\n".join(context)
    print("Contexto generado:\n", context)  # Imprimir el contexto para depuración
    
    # Generar la respuesta usando la API con un prompt más específico
    if "Información adicional no disponible" in context:
        # Si no hay información relevante, generar una respuesta que lo indique
        response = "No se encontró información específica sobre las lenguas mencionadas en la base de datos."
    else:
        prompt = f"""
        A continuación se proporciona información relevante sobre algunas entidades:
        {context}

        Basado en esta información, responde la siguiente pregunta de manera clara, amigable y estructurada:
        Pregunta: {question}

        Por favor, organiza la respuesta en párrafos claros y separados para cada entidad, y agrega contexto adicional sobre su importancia cultural, geográfica o lingüística.

        Respuesta:
        """
        response = generator_client.text_generation(prompt, max_new_tokens=200)
    
    return response

# Ejemplo de uso
if __name__ == "__main__":
    question = "Describe el mapudungun"
    response = generate_response(question)
    print("Respuesta generada:", response)