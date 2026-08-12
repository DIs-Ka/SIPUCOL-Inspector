# Inspector Sipucol

AplicaciÃ³n de escritorio para apoyar el registro y procesamiento de inspecciones SIPUCOL.

Permite trabajar con identificaciÃ³n del puente, componentes, daÃ±os, fotografÃ­as, evaluaciÃ³n y cÃ³digos SIPUCOL, ademÃ¡s de generar los entregables en Excel y PDF desde la misma aplicaciÃ³n.

## VersiÃ³n estable

**1.0.1**

Primera versiÃ³n de escritorio preparada para distribuciÃ³n interna en Windows.

## Funciones principales

- Registro de identificaciÃ³n de la inspecciÃ³n.
- Consulta y selecciÃ³n de componentes.
- Registro de daÃ±os y severidades.
- GestiÃ³n de fotografÃ­as.
- Consulta de cÃ³digos SIPUCOL.
- EvaluaciÃ³n por componente.
- Autoguardado local.
- Guardado y carga de proyectos.
- ExportaciÃ³n a Excel.
- GeneraciÃ³n del PDF final.
- Funcionamiento local sin depender de una conexiÃ³n a internet.

## TecnologÃ­as

### Interfaz

- React
- Vite
- Electron

### Backend

- Python
- FastAPI
- Uvicorn
- PyInstaller

### Documentos

- openpyxl
- pypdf
- LibreOffice integrado

## Estructura general

`app/` contiene la aplicaciÃ³n y el backend.

`desktop-package/` contiene la configuraciÃ³n necesaria para generar la versiÃ³n de escritorio.

`branding/` contiene los recursos grÃ¡ficos oficiales.

`docs/` contiene checkpoints y documentaciÃ³n tÃ©cnica del proyecto.

Los binarios de distribuciÃ³n no forman parte del historial normal de `main`; se publican mediante Releases y respaldos separados.

## Ramas

- `main`: versiÃ³n estable.
- `develop`: desarrollo activo.
- `release/v1.0.1`: snapshot de la versiÃ³n 1.0.1.
- `backup/*`: checkpoints histÃ³ricos.
- `archive/*`: respaldos completos del entorno del proyecto.

## Estado

Inspector Sipucol 1.0.1 cuenta con instalador y versiÃ³n portable para Windows x64.