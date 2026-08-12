# Modelo de ramas

## main

Última versión estable y publicable de Inspector Sipucol.

Contiene código fuente, configuración, documentación y recursos
necesarios para continuar el desarrollo y reconstruir el proyecto.

## develop

Desarrollo activo de la siguiente versión.

Después del lanzamiento 1.0.1 parte del mismo checkpoint que main.

## release/v1.0.1

Snapshot exacto del código fuente correspondiente a
Inspector Sipucol 1.0.1.

## backup/v1.0.1-source-final

Checkpoint adicional del código fuente de la versión 1.0.1.

## backup/pre-publish-*

Estado del repositorio antes de realizar la publicación inicial.

## Artefactos completos y binarios

Los archivos pesados no forman parte de main:

- instaladores
- ejecutables portables
- win-unpacked
- LibreOffice completo
- node_modules
- entornos Python
- builds
- backups ZIP
- entregas históricas

Estos elementos se conservan mediante GitHub Releases y snapshots
completos adjuntos a Releases.

De esta manera las ramas siguen siendo utilizables como repositorio
de desarrollo, mientras las versiones completas continúan
disponibles como archivos de respaldo.