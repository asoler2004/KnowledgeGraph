#!/usr/bin/env bash
set -euo pipefail

# Configuración de variables
FUSEKI_URL="http://localhost:3030"
DATASET_NAME="lymphoma_knowledge_graph"
USERNAME="admin"
PASSWORD="password123"

# 1. Esperar a que Jena Fuseki esté listo
echo "Esperando a que Jena Fuseki esté disponible en ${FUSEKI_URL}..."
until curl -s -o /dev/null -w "%{http_code}" "${FUSEKI_URL}/\$/ping" | grep -q "200"; do
  sleep 3
done

# 2. Definir el nombre del archivo local
FILE_NAME="lymphoma_diagnostic_rules.jsonld"
FILE_PATH="/home/antonia/GrafoLinfomaVet/import/${FILE_NAME}"

echo "Iniciando importación del grafo desde ${FILE_PATH}"

# 3. Crear el Dataset automáticamente si no existe
echo "Asegurando la existencia del dataset '${DATASET_NAME}'..."
curl -s -u "${USERNAME}:${PASSWORD}" -X POST \
  --data "dbType=tdb2&dbName=${DATASET_NAME}" \
  "${FUSEKI_URL}/\$/datasets" > /dev/null || true

# 4. Cargar y reconstruir el JSON-LD usando el protocolo Graph Store
echo "Cargando y procesando JSON-LD..."
curl -X POST \
  -u "${USERNAME}:${PASSWORD}" \
  --header "Content-Type: application/ld+json" \
  --data-binary @"${FILE_PATH}" \
  "${FUSEKI_URL}/${DATASET_NAME}?default"

echo "¡Grafo de conocimiento reconstruido exitosamente!"