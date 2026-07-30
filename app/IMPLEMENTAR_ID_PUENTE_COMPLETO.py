from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd().resolve()

PANEL = (
    ROOT
    / "src"
    / "components"
    / "PanelEvaluacion.jsx"
)

SERVER = (
    ROOT
    / "backend"
    / "server.py"
)

BACKUPS = ROOT / "backups"

STAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

EXCLUDED_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "backups",
    "__pycache__",
    ".venv",
    "venv",
    ".sipucol_runtime",
}

BACKUPS.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# VALIDACIÓN
# =========================================================

for required in [
    PANEL,
    SERVER,
]:

    if not required.exists():

        raise SystemExit(
            f"ERROR: no encontré {required}"
        )


# =========================================================
# BACKUP COMPLETO DE LA BASE CANÓNICA
# =========================================================

def excluded(
    path: Path,
) -> bool:

    try:

        relative =
            path.relative_to(
                ROOT
            )

    except ValueError:

        return True


    return any(

        part in EXCLUDED_DIRS

        for part in relative.parts
    )


def create_backup(
    label: str,
) -> Path:

    destination = (

        BACKUPS

        / f"{label}_{STAMP}.zip"
    )


    with zipfile.ZipFile(

        destination,

        "w",

        compression=
            zipfile.ZIP_DEFLATED,

    ) as archive:

        for path in ROOT.rglob("*"):

            if (
                not path.is_file()
                or excluded(path)
            ):

                continue


            if path.suffix.lower() in {
                ".pyc",
                ".log",
            }:

                continue


            archive.write(

                path,

                path.relative_to(
                    ROOT
                )
            )


    return destination


backup_before = create_backup(
    "SIPUCOL_BASE_CANONICA_ANTES_ID_PUENTE_COMPLETO"
)


print()
print("=" * 72)
print("BACKUP DE LA BASE CANÓNICA CREADO")
print("=" * 72)
print(backup_before)


# =========================================================
# ORIGINALES PARA RESTAURACIÓN AUTOMÁTICA
# =========================================================

original_panel =
    PANEL.read_bytes()

original_server =
    SERVER.read_bytes()


def rollback():

    PANEL.write_bytes(
        original_panel
    )

    SERVER.write_bytes(
        original_server
    )


# =========================================================
# AYUDANTES
# =========================================================

def read_source(
    path: Path,
) -> str:

    return (
        path.read_text(
            encoding="utf-8-sig",
            errors="strict",
        )
        .replace(
            "\r\n",
            "\n",
        )
    )


def substitute_once(
    source: str,
    pattern: str,
    replacement: str,
    label: str,
) -> str:

    result, count = re.subn(

        pattern,

        replacement,

        source,

        count=1,

        flags=re.DOTALL,
    )


    if count != 1:

        raise RuntimeError(

            f"No pude modificar {label}. "
            f"Coincidencias encontradas: {count}"
        )


    return result


panel_code =
    read_source(
        PANEL
    )

server_code =
    read_source(
        SERVER
    )


# =========================================================
# 1. CONFIGURACIÓN DE CAMPOS
# =========================================================

new_field_configuration = r'''const segmentosIdPuente = [
  ['idPuente', 'Territorial / Departamento', 'numeric', 2],
  ['idCarreteraTramo', 'ID carretera y tramo', 'alphanumeric', 8],
  ['sentido', 'Sentido', 'numeric', 2],
  ['consecutivo', 'Consecutivo', 'numeric', 4]
]

const camposIdentificacion = [
  ['nombrePuente', 'Nombre del puente'],
  ['administradorVial', 'Administrador vial'],
  ['entidadAdministradora', 'Entidad administradora'],
  ['responsableDiligenciamiento', 'Responsable del diligenciamiento'],
  ['cargoDiligenciamiento', 'Cargo'],
  ['tarjetaDiligenciamiento', 'Tarjeta profesional'],
  ['responsableRevision', 'Responsable de la revisión'],
  ['cargoRevision', 'Cargo revisión'],
  ['tarjetaRevision', 'Tarjeta profesional revisión'],
  ['fecha', 'Fecha de levantamiento'],
  ['hora', 'Hora']
]

const bloquesEvaluacionIniciales = ['''


panel_code = substitute_once(

    panel_code,

    r'''const camposIdentificacion = \[
.*?
\]

const bloquesEvaluacionIniciales = \[''',

    new_field_configuration,

    "la configuración de Identificación",
)


# =========================================================
# 2. ESTADO INICIAL
# =========================================================

panel_code = substitute_once(

    panel_code,

    r'''function crearIdentificacionInicial\(\) \{
  return camposIdentificacion\.reduce\(\(acc, \[key\]\) => \{
    acc\[key\] = ''
    return acc
  \}, \{\}\)
\}''',

    r'''function crearIdentificacionInicial() {
  return [...segmentosIdPuente, ...camposIdentificacion].reduce((acc, [key]) => {
    acc[key] = ''
    return acc
  }, {})
}''',

    "el estado inicial de Identificación",
)


# =========================================================
# 3. NORMALIZACIÓN DE LOS CAMPOS
# =========================================================

panel_code = substitute_once(

    panel_code,

    r'''function limpiarTexto\(valor\) \{
  return String\(valor \|\| ''\)\.replace\(/\\s\+/g, ' '\)\.trim\(\)
\}''',

    r'''function limpiarTexto(valor) {
  return String(valor || '').replace(/\s+/g, ' ').trim()
}

function normalizarCampoIdentificacion(key, value) {
  const texto = String(value ?? '')

  if (key === 'idPuente') {
    return texto
      .replace(/\D/g, '')
      .slice(0, 2)
  }

  if (key === 'idCarreteraTramo') {
    return texto
      .replace(/[^A-Za-z0-9]/g, '')
      .toUpperCase()
      .slice(0, 8)
  }

  if (key === 'sentido') {
    return texto
      .replace(/\D/g, '')
      .slice(0, 2)
  }

  if (key === 'consecutivo') {
    return texto
      .replace(/\D/g, '')
      .slice(0, 4)
  }

  return texto
}''',

    "la validación del ID Puente",
)


# =========================================================
# 4. ACTUALIZACIÓN SEGURA DEL ESTADO
# =========================================================

panel_code = substitute_once(

    panel_code,

    r'''  function actualizarIdentificacion\(key, value\) \{
    setIdentificacion\(\(actual\) => \(\{
      \.\.\.actual,
      \[key\]: value
    \}\)\)
  \}''',

    r'''  function actualizarIdentificacion(key, value) {
    const valorNormalizado = normalizarCampoIdentificacion(key, value)

    setIdentificacion((actual) => ({
      ...actual,
      [key]: valorNormalizado
    }))
  }''',

    "actualizarIdentificacion",
)


# =========================================================
# 5. BLOQUE VISUAL ID PUENTE COMPLETO
# =========================================================

new_identification_ui = r'''        {identificacionAbierta && (
          <>
            <div style={styles.idPuenteBloque}>
              <div style={styles.idPuenteTitulo}>
                ID Puente completo
              </div>

              <div style={styles.idPuenteScroll}>
                <div style={styles.idPuenteFila}>
                  {segmentosIdPuente.map(([key, label, tipo, maxLength], index) => (
                    <div key={key} style={styles.idPuenteSegmentoWrap}>
                      <label
                        style={{
                          ...styles.label,
                          width:
                            key === 'idCarreteraTramo'
                              ? 300
                              : key === 'consecutivo'
                                ? 170
                                : 155,
                          flexShrink: 0
                        }}
                      >
                        {label}

                        <input
                          value={identificacion[key] || ''}
                          onChange={(event) =>
                            actualizarIdentificacion(key, event.target.value)
                          }
                          type="text"
                          inputMode={tipo === 'numeric' ? 'numeric' : 'text'}
                          maxLength={maxLength}
                          autoComplete="off"
                          spellCheck={false}
                          aria-label={label}
                          style={{
                            ...styles.input,
                            ...styles.idPuenteInput
                          }}
                        />
                      </label>

                      {index < segmentosIdPuente.length - 1 && (
                        <span style={styles.idPuenteSeparador}>
                          –
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div style={styles.idPuenteVista}>
                ID resultante:
                {' '}
                {identificacion.idPuente || '—'}
                -
                {identificacion.idCarreteraTramo || '—'}
                -
                {identificacion.sentido || '—'}
                -
                {identificacion.consecutivo || '—'}
              </div>
            </div>

            <div style={styles.gridIdentificacion}>
              {camposIdentificacion.map(([key, label]) => (
                <label key={key} style={styles.label}>
                  {label}

                  <input
                    value={identificacion[key] || ''}
                    onChange={(event) =>
                      actualizarIdentificacion(key, event.target.value)
                    }
                    style={styles.input}
                  />
                </label>
              ))}
            </div>
          </>
        )}'''


panel_code = substitute_once(

    panel_code,

    r'''        \{identificacionAbierta && \(
          <div style=\{styles\.gridIdentificacion\}>
            \{camposIdentificacion\.map\(\(\[key, label\]\) => \(
              <label key=\{key\} style=\{styles\.label\}>
                \{label\}
                <input
                  value=\{identificacion\[key\]\}
                  onChange=\{\(event\) => actualizarIdentificacion\(key, event\.target\.value\)\}
                  style=\{styles\.input\}
                />
              </label>
            \)\)\}
          </div>
        \)\}''',

    new_identification_ui,

    "la interfaz de Identificación",
)


# =========================================================
# 6. ESTILOS DEL BLOQUE Y SCROLL LATERAL
# =========================================================

new_styles = r'''  idPuenteBloque: {
    marginBottom: 10,
    padding: '9px 10px 7px',
    border: '1px solid #065f46',
    borderRadius: 8,
    background: 'rgba(2, 20, 15, 0.48)',
    overflow: 'hidden'
  },
  idPuenteTitulo: {
    color: '#34d399',
    fontSize: 11,
    fontWeight: 800,
    marginBottom: 7,
    textTransform: 'uppercase',
    letterSpacing: '0.04em'
  },
  idPuenteScroll: {
    width: '100%',
    overflowX: 'auto',
    overflowY: 'hidden',
    paddingBottom: 6,
    scrollbarGutter: 'stable'
  },
  idPuenteFila: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 10,
    minWidth: 930,
    width: 'max-content'
  },
  idPuenteSegmentoWrap: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 10,
    flexShrink: 0
  },
  idPuenteSeparador: {
    color: '#6ee7b7',
    fontSize: 19,
    fontWeight: 800,
    lineHeight: '32px',
    paddingBottom: 1
  },
  idPuenteInput: {
    textAlign: 'center',
    fontFamily: 'Consolas, "Courier New", monospace',
    fontSize: 14,
    fontWeight: 800,
    letterSpacing: '0.18em',
    textTransform: 'uppercase'
  },
  idPuenteVista: {
    marginTop: 2,
    color: '#93c5fd',
    fontFamily: 'Consolas, "Courier New", monospace',
    fontSize: 11,
    fontWeight: 700
  },
  gridIdentificacion: {'''


panel_code = substitute_once(

    panel_code,

    r'''  gridIdentificacion: \{''',

    new_styles,

    "los estilos del ID Puente",
)


# =========================================================
# 7. BACKEND: ESCRITURA EXACTA EN EXCEL
# =========================================================

new_backend_id_block = r'''    # ID Puente completo según las cuatro secciones reales:
    #
    # Territorial / Departamento: G13:H13
    # ID carretera y tramo:       J13:Q13
    # Sentido:                     S13:T13
    # Consecutivo:                 V13:Y13
    #
    # Se mantiene compatibilidad con proyectos antiguos cuyo
    # idPuente contenía los cuatro grupos separados por guiones.

    id_groups = [
        (
            "idPuente",
            ["G13", "H13"],
            r"[^0-9]",
            2,
        ),
        (
            "idCarreteraTramo",
            ["J13", "K13", "L13", "M13", "N13", "O13", "P13", "Q13"],
            r"[^A-Za-z0-9]",
            8,
        ),
        (
            "sentido",
            ["S13", "T13"],
            r"[^0-9]",
            2,
        ),
        (
            "consecutivo",
            ["V13", "W13", "X13", "Y13"],
            r"[^0-9]",
            4,
        ),
    ]

    all_id_cells = [
        ref
        for _, refs, _, _ in id_groups
        for ref in refs
    ]

    for ref in all_id_cells:
        clear(ref)

    legacy_id = str(
        identificacion.get("idPuente")
        or ""
    ).strip()

    legacy_parts = (
        legacy_id.split("-")
        if "-" in legacy_id
        else []
    )

    for index, (key, refs, forbidden, max_length) in enumerate(id_groups):
        raw_value = str(
            identificacion.get(key)
            or ""
        ).strip()

        if (
            not raw_value
            and legacy_parts
            and index < len(legacy_parts)
        ):
            raw_value = legacy_parts[index]

        clean_value = re.sub(
            forbidden,
            "",
            raw_value,
        )[:max_length]

        if key == "idCarreteraTramo":
            clean_value = clean_value.upper()

        for ref, character in zip(
            refs,
            clean_value,
        ):
            write(
                ref,
                character,
                key,
            )

    # Fecha: formato visual M6 N6 / P6 Q6 / S6'''


server_code = substitute_once(

    server_code,

    r'''    # ID Puente: celdas reales separadas por guiones del formato\.
.*?
    # Fecha: formato visual M6 N6 / P6 Q6 / S6''',

    new_backend_id_block,

    "la escritura del ID Puente en Excel",
)


# =========================================================
# 8. VERIFICACIONES ANTES DE GUARDAR
# =========================================================

required_panel_markers = [
    "const segmentosIdPuente",
    "idCarreteraTramo",
    "ID Puente completo",
    "styles.idPuenteScroll",
    "normalizarCampoIdentificacion",
]

required_server_markers = [
    '"idCarreteraTramo"',
    '"sentido"',
    '"consecutivo"',
    '["G13", "H13"]',
    '["S13", "T13"]',
    '["V13", "W13", "X13", "Y13"]',
]

for marker in required_panel_markers:

    if marker not in panel_code:

        raise RuntimeError(
            f"Validación frontend falló: {marker}"
        )


for marker in required_server_markers:

    if marker not in server_code:

        raise RuntimeError(
            f"Validación backend falló: {marker}"
        )


PANEL.write_text(
    panel_code,
    encoding="utf-8",
    newline="\n",
)

SERVER.write_text(
    server_code,
    encoding="utf-8",
    newline="\n",
)


# =========================================================
# 9. VALIDAR PYTHON
# =========================================================

print()
print("Validando backend...")


backend_check = subprocess.run(

    [
        "py",
        "-m",
        "py_compile",
        str(SERVER),
    ],

    cwd=str(ROOT),

    capture_output=True,

    text=True,

    timeout=120,
)


if backend_check.returncode != 0:

    rollback()

    print(backend_check.stderr)

    raise SystemExit(
        "ERROR BACKEND. Cambios revertidos."
    )


print("Backend correcto.")


# =========================================================
# 10. VALIDAR FRONTEND
# =========================================================

npm = (
    shutil.which("npm.cmd")
    or shutil.which("npm")
)


if not npm:

    rollback()

    raise SystemExit(
        "ERROR: no encontré npm. Cambios revertidos."
    )


print()
print("Validando frontend...")


build = subprocess.run(

    [
        npm,
        "run",
        "build",
    ],

    cwd=str(ROOT),

    capture_output=True,

    text=True,

    timeout=600,
)


print(build.stdout)


if build.returncode != 0:

    rollback()

    print()
    print("=" * 72)
    print("CAMBIOS REVERTIDOS AUTOMÁTICAMENTE")
    print("=" * 72)
    print(build.stderr)

    raise SystemExit(1)


# =========================================================
# 11. LIMPIAR CACHÉ
# =========================================================

shutil.rmtree(

    ROOT
    / "node_modules"
    / ".vite",

    ignore_errors=True,
)


# =========================================================
# 12. BACKUP FINAL
# =========================================================

backup_after = create_backup(
    "SIPUCOL_BASE_CANONICA_ID_PUENTE_COMPLETO"
)


checkpoint = (

    ROOT

    / f"CHECKPOINT_ID_PUENTE_COMPLETO_{STAMP}.txt"
)


checkpoint.write_text(

    "\n".join([

        "SIPUCOL — BASE CANÓNICA",

        "=" * 72,

        "",

        f"Fecha: {datetime.now():%Y-%m-%d %H:%M:%S}",

        "",

        "Funcionalidad implementada:",

        "ID Puente completo dividido en cuatro segmentos.",

        "",

        "1. Territorial / Departamento: 2 números.",

        "2. ID carretera y tramo: 8 caracteres alfanuméricos.",

        "3. Sentido: 2 números.",

        "4. Consecutivo: 4 números.",

        "",

        "Integraciones preservadas:",

        "- Autoguardado",

        "- Guardar/Cargar proyecto",

        "- Limpiar todo",

        "- Excel",

        "- PDF",

        "- Fecha y hora",

        "- Fotos",

        "- Códigos",

        "",

        "Backup anterior:",

        str(backup_before),

        "",

        "Backup final:",

        str(backup_after),
    ]),

    encoding="utf-8",
)


print()
print("=" * 72)
print("ID PUENTE COMPLETO — INSTALADO Y VALIDADO")
print("=" * 72)

print()
print("Interfaz:")
print("- Nuevo bloque horizontal dentro de Identificación.")
print("- Scroll lateral independiente.")
print("- Vista previa del ID completo.")

print()
print("Validación:")
print("- Territorial: 2 números.")
print("- Carretera y tramo: 8 letras/números.")
print("- Sentido: 2 números.")
print("- Consecutivo: 4 números.")
print("- Letras del tramo convertidas a mayúsculas.")
print("- Símbolos y espacios eliminados.")

print()
print("Excel:")
print("- G13:H13 = Territorial/Departamento.")
print("- J13:Q13 = ID carretera y tramo.")
print("- S13:T13 = Sentido.")
print("- V13:Y13 = Consecutivo.")

print()
print("BACKUP ANTERIOR:")
print(backup_before)

print()
print("BACKUP FINAL:")
print(backup_after)

print()
print("CHECKPOINT:")
print(checkpoint)
