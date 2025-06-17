# 1) Crea un directorio de salida
mkdir -p extracted_2025

# 2) Extrae solo los ZIP que terminan en 2025.zip
for f in valenbici/*2025.zip; do
    unzip -q "$f" -d extracted_2025/
done

