import os
import pandas as pd
import json
from google.cloud import storage
import csv

# Configuración del bucket y rutas en Google Cloud Storage
bucket_name = "proyecto-genomico-analisis-ela"
input_file_path = "SNP_Indv_Sanos/snp_individuals_data_2.csv"
output_dir_bucket = "SNP_Indv_Sanos/individual_csv_files"
checkpoint_file_path = "SNP_Indv_Sanos/checkpoints/checkpoint_filtered_lote2.json"
local_input_file_path = "/tmp/snp_individuals_data.csv"
local_checkpoint_file = "/tmp/checkpoint_filtered_lote2.json"
chunk_size = 500000

# Inicializar cliente de Google Cloud Storage
client = storage.Client()

# Función para descargar archivo desde Google Cloud Storage
def download_file_from_bucket(bucket_name, source_path, dest_path):
    if not os.path.exists(dest_path):
        print(f"Descargando {source_path} desde el bucket {bucket_name}...")
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(source_path)
        blob.download_to_filename(dest_path)
        print(f"Archivo {source_path} descargado a {dest_path}.")
    else:
        print(f"El archivo {dest_path} ya existe localmente. Saltando descarga.")

# Función para subir un archivo al bucket
def upload_file_to_bucket(bucket_name, source_path, dest_path):
    print(f"Subiendo {source_path} al bucket {bucket_name} como {dest_path}...")
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(source_path)
    print(f"Archivo {source_path} subido como {dest_path}.")

# Cargar el checkpoint
def load_checkpoint():
    if os.path.exists(local_checkpoint_file):
        with open(local_checkpoint_file, 'r') as f:
            try:
                checkpoint_data = json.load(f)
                if not checkpoint_data:
                    print("Checkpoint está vacío. Creando uno nuevo...")
                    return {"last_chrom": None, "last_pos": None}
                return checkpoint_data
            except json.JSONDecodeError:
                print("Error al leer el archivo de checkpoint. Creando uno nuevo...")
                return {"last_chrom": None, "last_pos": None}
    else:
        print("Checkpoint no encontrado. Creando uno nuevo...")
        return {"last_chrom": None, "last_pos": None}

# Guardar el checkpoint
def save_checkpoint(checkpoint_data):
    print(f"Guardando checkpoint: Cromosoma {checkpoint_data['last_chrom']}, Posición {checkpoint_data['last_pos']}")
    with open(local_checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f)
    upload_file_to_bucket(bucket_name, local_checkpoint_file, checkpoint_file_path)

# Procesar chunk
def process_chunk(chunk, individuals, checkpoint_data):
    print("Filtrando cromosomas objetivo:del 1 al 22, X, Y y MT.")
    target_chromosomes = {str(i) for i in range(1, 23)} | {'X', 'Y', 'MT'}

    # Convertir la columna CHROM a string para consistencia
    chunk['CHROM'] = chunk['CHROM'].astype(str).str.strip().str.replace('chr', '', case=False)

    # Filtrar el chunk por los cromosomas objetivo
    chunk = chunk[chunk['CHROM'].isin(target_chromosomes)]

    if chunk.empty:
        print("Chunk vacío después del filtrado por cromosomas. Saltando este chunk.")
        return

    print(f"Procesando chunk con {len(chunk)} filas.")
    last_chrom, last_pos = None, None
    individual_temp_files = {ind: f"/tmp/{ind[:10]}_temp.csv" for ind in individuals}  # Limitar nombres de archivo a 10 caracteres
    temp_handlers = {}
    temp_writers = {}
    
    for ind, temp_file_path in individual_temp_files.items():
        temp_handlers[ind] = open(temp_file_path, 'w', newline='')
        temp_writers[ind] = csv.writer(temp_handlers[ind])
        temp_writers[ind].writerow(['CHROM', 'POS', 'ID', 'REF', 'ALT'])

    for _, row in chunk.iterrows():
        last_chrom = row['CHROM']
        last_pos = row['POS']
        ref = row['REF']
        alt = row['ALT']
        for ind in individuals:
            # Verificar si el valor es una cadena antes de hacer el split
            if isinstance(row[ind], str):  # Verifica si el valor es una cadena
                genotype = row[ind].split('|')
            else:
                print(f"Advertencia: El valor para el individuo {ind} en la fila {row['POS']} no es una cadena válida.")
                genotype = ['0', '0']  # Si no es una cadena, asignar valor por defecto

            if genotype == ['0', '0']:
                temp_writers[ind].writerow([row['CHROM'], row['POS'], row['ID'], ref, ref])
            elif genotype == ['1', '1']:
                temp_writers[ind].writerow([row['CHROM'], row['POS'], row['ID'], alt, alt])
            else:
                temp_writers[ind].writerow([row['CHROM'], row['POS'], row['ID'], ref, alt])

    # Subir los archivos temporales al bucket
    for ind, temp_file_path in individual_temp_files.items():
        temp_handlers[ind].close()
        destination_path = f"{output_dir_bucket}/{ind[:10]}.csv"  # Limitar nombres de archivo a 10 caracteres
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(destination_path)
        if blob.exists():
            existing_data = blob.download_as_text()
            with open(temp_file_path, 'r') as temp_file:
                new_data = temp_file.read()
            combined_data = existing_data + new_data
            blob.upload_from_string(combined_data)
        else:
            blob.upload_from_filename(temp_file_path)
        os.remove(temp_file_path)

    checkpoint_data['last_chrom'] = last_chrom
    checkpoint_data['last_pos'] = last_pos
    print(f"Chunk procesado: Último cromosoma {last_chrom}, Última posición {last_pos}")

# Main
def main():
    download_file_from_bucket(bucket_name, input_file_path, local_input_file_path)
    download_file_from_bucket(bucket_name, checkpoint_file_path, local_checkpoint_file)

    checkpoint_data = load_checkpoint()
    last_chrom = checkpoint_data.get("last_chrom")
    last_pos = checkpoint_data.get("last_pos")

    print(f"Cargando checkpoint inicial: Cromosoma {last_chrom}, Posición {last_pos}")

    # Leer el CSV en chunks
    csv_reader = pd.read_csv(local_input_file_path, chunksize=chunk_size)
    individuals = None

    for chunk in csv_reader:
        chunk['CHROM'] = chunk['CHROM'].astype(str).str.strip()
        if last_chrom is not None and last_pos is not None:
            last_chrom = str(last_chrom)
            chunk = chunk[(chunk['CHROM'] > last_chrom) |
                          ((chunk['CHROM'] == last_chrom) & (chunk['POS'] > last_pos))]
            if chunk.empty:
                print("No hay datos relevantes en este chunk según el checkpoint.")
                continue

        if individuals is None:
            # Filtrar las columnas con menos de 10 caracteres
            individuals = [col for col in chunk.columns[5:] if len(col) < 10]
            print(f"Individuos seleccionados (menos de 10 caracteres): {individuals}")

        print(f"Procesando desde Cromosoma {chunk.iloc[0]['CHROM']}, Posición {chunk.iloc[0]['POS']}")
        process_chunk(chunk, individuals, checkpoint_data)
        save_checkpoint(checkpoint_data)

    print("Proceso completado.")
    if os.path.exists(local_input_file_path):
        os.remove(local_input_file_path)
    if os.path.exists(local_checkpoint_file):
        os.remove(local_checkpoint_file)

if __name__ == "__main__":
    main()
