# **Iberian Peninsula Genome Data Processing**  

Este proyecto se centra en la extracción, procesamiento y transformación de datos genómicos de la **Fase 3 del Proyecto 1000 Genomas** de individuos sanos de la **Península Ibérica**. Para manejar los grandes volúmenes de datos, se utilizó **Google Cloud Platform (GCP)** con una **máquina virtual (VM) basada en Ubuntu**, donde se ejecutaron herramientas especializadas como **bcftools** y **Python** para la manipulación y estructuración de los datos.  

La fuente de los datos utilizados en este proceso se encuentra en:  
🔗 **[1000 Genomes Project Data](https://www.internationalgenome.org/data)**  

---

## **Características Principales**  
- **Extracción de Datos**: Descarga y extracción de millones de filas de datos genómicos desde archivos **VCF (Variant Call Format)** almacenados en la nube.  
- **Procesamiento de Datos**: Limpieza, filtrado y transformación de los datos crudos en formatos **CSV** para análisis estructurados.  
- **Generación de Data Individualizada**: Creación de archivos CSV separados por paciente, facilitando el acceso y procesamiento de información específica.  
- **Uso de Computación en la Nube**: Se utilizó **GCP y Ubuntu VM** para manejar eficientemente el procesamiento de grandes volúmenes de datos genómicos.  

---

## **Objetivos**  
✅ **Estandarizar** y **estructurar** los datos genómicos de la **Península Ibérica** en un formato óptimo para análisis posteriores.  
✅ **Aprovechar la computación en la nube** para realizar un procesamiento eficiente de archivos **VCF** de gran tamaño (~3GB por archivo).  
✅ **Generar archivos individuales por paciente** a partir de un CSV consolidado, optimizando su manejo y consulta.  

---

## **Herramientas y Librerías**  

### **Infraestructura**  
- **Google Cloud Platform (GCP)** → Para el almacenamiento y procesamiento en la nube.  
- **Máquina Virtual con Ubuntu** → Necesaria para ejecutar **bcftools** y procesar archivos **VCF**.  

### **Lenguaje y Librerías de Programación**  
- **Python**  
  - `pandas` → Manipulación y estructuración de datos.  
  - `numpy` → Optimización de cálculos con datos numéricos.  
  - `csv` → Escritura y lectura de archivos CSV.  
  - `json` → Manejo de checkpoints y configuración de procesos.  
  - `re` → Expresiones regulares para validación de genotipos.  
  - `subprocess` → Ejecución de comandos de Linux para manipular archivos VCF.  

### **Herramientas de Procesamiento de Datos Genómicos**  
- **bcftools** → Herramienta para la manipulación y extracción de datos de archivos **VCF**.  
- **gzip** → Descompresión de archivos genómicos.  
- **gsutil** → Manejo de archivos en Google Cloud Storage.  

---

## **Procedimiento de Extracción y Procesamiento de Datos**  

### **1️⃣ Extracción y Consolidación de Datos**  
📌 **Archivo responsable:** `process_vcf.py`  
📌 **Función principal:** Descargar y extraer información de archivos VCF.  

1. **Descarga los archivos VCF** desde Google Cloud Storage utilizando **gsutil**.  
2. **Filtra los pacientes ibéricos** para asegurar que los datos sean relevantes.  
3. **Utiliza `bcftools`** para extraer la información genómica y convertirla en un formato tabular (CSV).  
4. **Genera un archivo CSV consolidado** (`snp_individuals_data.csv`) que contiene la información de todos los pacientes seleccionados.  

---

### **2️⃣ Generación de Archivos Individuales por Paciente**  
📌 **Archivo responsable:** `extractor1.py`  
📌 **Función principal:** Dividir el CSV consolidado en archivos individuales por paciente.  

1. **Carga el archivo CSV consolidado** generado en la fase anterior.  
2. **Filtra los SNPs por cromosomas de interés** y elimina columnas innecesarias.  
3. **Separa la información por paciente**, generando un archivo **CSV por cada individuo**.  
4. **Guarda y sube los archivos generados a Google Cloud Storage**.  

---

## **Instrucciones de Uso**  

### **Requisitos Previos**  
📌 **Configuraciones previas necesarias antes de ejecutar los scripts:**  

1. **Configurar una máquina virtual en Google Cloud Platform** con **Ubuntu**.  
2. **Instalar Python y sus dependencias:**  

   ```bash
   sudo apt update && sudo apt install -y python3 python3-pip bcftools gzip
   pip3 install pandas numpy google-cloud-storage
   ```

3. **Configurar Google Cloud SDK y autenticación:**  

   ```bash
   gcloud auth application-default login
   ```

4. **Verificar que `bcftools` está correctamente instalado:**  

   ```bash
   bcftools --version
   ```

---

### **Ejecución del Proceso Completo**  

#### **Paso 1: Ejecutar el script `process_vcf.py`**  
📌 **Objetivo:** Extraer información desde archivos VCF y generar un CSV consolidado.  

```bash
python3 process_vcf.py
```

🔹 **Resultado esperado:** Un archivo `snp_individuals_data.csv` con toda la información genómica consolidada.  

---

#### **Paso 2: Ejecutar el script `extractor1.py`**  
📌 **Objetivo:** Dividir el CSV consolidado en archivos individuales por paciente.  

```bash
python3 extractor1.py
```

🔹 **Resultado esperado:** Múltiples archivos CSV en el bucket de GCP, cada uno correspondiente a un paciente específico.  

---

### **Conclusión**  
Este flujo de trabajo permite transformar datos genómicos crudos en formatos estructurados y organizados para análisis posteriores. La combinación de **Google Cloud Platform, Python y bcftools** garantiza un procesamiento eficiente de archivos **VCF** de gran tamaño, optimizando el manejo de datos genómicos a gran escala. 🚀  

---

Si necesitas ajustes o más detalles, dime y lo revisamos. 😊
