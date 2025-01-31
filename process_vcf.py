import os
import subprocess
import pandas as pd
import time
from google.cloud import storage

# Configuración del bucket y rutas en Google Cloud Storage
bucket_name = "proyecto-genomico-analisis-ela"
vcf_folder = f"gs://{bucket_name}/vcf_files"
output_folder = "SNP_Indv_Sanos"
file_path = "igsr_Iberian_populations_in_Spain.csv"
lista_archivos_local_path = '/tmp/lista_archivos.txt'  # Ruta del archivo con los pacientes a excluir

client = storage.Client()

def file_exists_in_bucket(file_path):
    full_path = f"gs://{bucket_name}/{file_path}"
    result = subprocess.run(['gsutil', 'ls', full_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return result.returncode == 0

print(f"Verificando la existencia del archivo: gs://{bucket_name}/{file_path}")
if not file_exists_in_bucket(file_path):
    print(f"El archivo gs://{bucket_name}/{file_path} NO existe en el bucket.")
    exit()

local_file_path = '/tmp/igsr_Iberian_populations_in_Spain.csv'
blob = client.bucket(bucket_name).blob(file_path)
print(f"Descargando archivo CSV desde {file_path}...")
start_time = time.time()
blob.download_to_filename(local_file_path)
print(f"Archivo CSV descargado en {time.time() - start_time:.2f} segundos.")

# Leer el archivo lista_archivos.txt y obtener los nombres de los pacientes a excluir
with open(lista_archivos_local_path, 'r') as file:
    exclude_patients = set()
    for line in file:
        line = line.strip()
        if line:  # Asegurarse de que la línea no esté vacía
            # Extraer el nombre del paciente (la última parte antes de .csv)
            patient_name = line.split('/')[-1].replace('.csv', '')
            exclude_patients.add(patient_name)

# Cargar el archivo CSV de individuos
iberian_individuals = pd.read_csv(local_file_path)
num_individuals = len(iberian_individuals)
print(f"Total de individuos disponibles: {num_individuals}")

# Filtrar los individuos que no estén en la lista de exclusión y eliminar duplicados
filtered_individuals = list(set(ind for ind in iberian_individuals['Sample'].tolist() if ind not in exclude_patients))
print(f"Individuos después de excluir los pacientes: {len(filtered_individuals)}")
print(f"Pacientes restantes (sin duplicados): {filtered_individuals}")

# Solicitar al usuario los índices de selección, asegurándose de que sean válidos
start_index = int(input(f"Introduce el índice de inicio (1-{len(filtered_individuals)}): "))
end_index = int(input(f"Introduce el índice de fin (1-{len(filtered_individuals)}): "))

if start_index < 1 or end_index > len(filtered_individuals) or start_index > end_index:
    print("Índices inválidos.")
    exit()

# Seleccionar los individuos sin duplicados en el rango solicitado
selected_individuals = filtered_individuals[start_index - 1:end_index]
print(f"Individuos seleccionados (sin duplicados): {selected_individuals}")

vcf_local_paths = {}
print("Descargando archivos VCF...")
for blob in client.bucket(bucket_name).list_blobs(prefix='vcf_files/'):
    if blob.name.endswith(".vcf.gz"):
        vcf_file_local_path = f"/tmp/{os.path.basename(blob.name)}"
        if not os.path.exists(vcf_file_local_path):
            print(f"Descargando archivo VCF: {blob.name}")
            blob.download_to_filename(vcf_file_local_path)
        vcf_local_paths[blob.name] = vcf_file_local_path

print("Iniciando el procesamiento secuencial de los SNPs...")

# Función para validar que las muestras estén presentes en el archivo VCF
def validate_samples_in_vcf(vcf_file_path, samples):
    result = subprocess.run(
        ["bcftools", "query", "-l", vcf_file_path],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if result.returncode != 0:
        print(f"Error al listar muestras de {vcf_file_path}: {result.stderr}")
        return []

    available_samples = set(result.stdout.splitlines())
    valid_samples = [s for s in samples if s in available_samples]
    return valid_samples

# Función para procesar los SNPs en bloques y escribir directamente en el archivo CSV
def process_and_write_snps(vcf_file_path, selected_individuals, csv_writer):
    print(f"Procesando SNPs en archivo: {vcf_file_path}")
    valid_samples = validate_samples_in_vcf(vcf_file_path, selected_individuals)
    if not valid_samples:
        print(f"No hay muestras válidas en {vcf_file_path}.")
        return

    individuals_str = ",".join(valid_samples)
    query_format = f"%CHROM\t%POS\t%ID\t%REF\t%ALT\t[%SAMPLE=%GT\t]\n"

    # Ejecutar bcftools y escribir en el CSV en bloques para evitar uso excesivo de RAM
    try:
        process = subprocess.Popen(
            ["bcftools", "query", "-s", individuals_str, "-f", query_format, vcf_file_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        for line in process.stdout:
            data = line.strip().split('\t')
            snp_info = data[:5]
            sample_data = data[5:]
            csv_writer.writerow(snp_info + sample_data)

        process.stdout.close()
        process.wait()

    except Exception as e:
        print(f"Error al procesar {vcf_file_path}: {e}")

output_csv_path = '/tmp/snp_individuals_data.csv'

# Crear el archivo CSV con todos los resultados
with open(output_csv_path, 'w') as csvfile:
    import csv
    writer = csv.writer(csvfile)
    writer.writerow(['CHROM', 'POS', 'ID', 'REF', 'ALT'] + selected_individuals)

    for vcf_path in vcf_local_paths.values():
        process_and_write_snps(vcf_path, selected_individuals, writer)

print(f"Procesamiento completado. Archivo CSV creado en {output_csv_path}")

print(f"Subiendo archivo CSV al bucket {bucket_name}/{output_folder}...")
blob = client.bucket(bucket_name).blob(f"{output_folder}/snp_individuals_data_2.csv")
blob.upload_from_filename(output_csv_path)
print(f"Archivo CSV subido correctamente.")

try:
    print("Eliminando archivos temporales...")
    os.remove(local_file_path)
    os.remove(output_csv_path)
    print("Archivos temporales eliminados.")
except Exception as e:
    print(f"Error al eliminar archivos temporales: {e}")
