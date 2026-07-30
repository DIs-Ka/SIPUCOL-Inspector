from __future__ import annotations

import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd().resolve()
PANEL = ROOT / "src" / "components" / "PanelEvaluacion.jsx"
SERVER = ROOT / "backend" / "server.py"
BACKUPS = ROOT / "backups"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")

IGNORED_DIRS = {
    "node_modules",
    ".git",
    "dist",
    "backups",
    "__pycache__",
    ".venv",
    "venv",
    ".sipucol_runtime",
}

BACKUPS.mkdir(parents=True, exist_ok=True)


# ============================================================
# VALIDACIÓN INICIAL
# ============================================================

if not PANEL.exists():
    raise SystemExit(f"ERROR: no existe {PANEL}")

if not SERVER.exists():
    raise SystemExit(f"ERROR: no existe {SERVER}")


def read_text(path: Path) -> str:
    return path.read_text(
        encoding="utf-8-sig",
        errors="strict",
    ).replace("\r\n", "\n")


def create_backup(label: str) -> Path:
    destination = BACKUPS / f"{label}_{STAMP}.zip"

    with zipfile.ZipFile(
        destination,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as archive:

        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue

            relative = path.relative_to(ROOT)

            if any(
                part in IGNORED_DIRS
                for part in relative.parts
            ):
                continue

            if path.suffix.lower() in {".pyc", ".log"}:
                continue

            archive.write(path, relative)

    return destination


def replace_once(
    source: str,
    pattern: str,
    replacement: str,
    description: str,
) -> str:
    updated, count = re.subn(
        pattern,
        replacement,
        source,
        count=1,
        flags=re.DOTALL,
    )

    if count != 1:
        raise RuntimeError(
            f"No pude cambiar {description}. "
            f"Coincidencias: {count}"
        )

    return updated


# ============================================================
# BACKUP CANÓNICO
# ============================================================

backup_before = create_backup(
    "SIPUCOL_BASE_CANONICA_ANTES_ID_COMPLETO_REAL"
)

print()
print("=" * 72)
print("BACKUP CANÓNICO CREADO")
print("=" * 72)
print(backup_before)


panel_original = PANEL.read_bytes()
server_original = SERVER.read_bytes()


def rollback() -> None:
    PANEL.write_bytes(panel_original)
    SERVER.write_bytes(server_original)


try:
    panel_code = read_text(PANEL)
    server_code = read_text(SERVER)

    if "const segmentosIdPuente = [" in panel_code:
        raise RuntimeError(
            "El bloque ID Puente completo ya parece existir "
            "en PanelEvaluacion.jsx."
        )

    # ========================================================
    # 1. CAMPOS DE IDENTIFICACIÓN
    # ========================================================

    old_fields = r"""const camposIdentificacion = \[
  \['nombrePuente', 'Nombre del puente'\],
  \['idPuente', 'ID Puente'\],
  \['administradorVial', 'Administrador vial'\],
  \['entidadAdministradora', 'Entidad administradora'\],
  \['responsableDiligenciamiento', 'Responsable del diligenciamiento'\],
  \['cargoDiligenciamiento', 'Cargo'\],
  \['tarjetaDiligenciamiento', 'Tarjeta profesional'\],
  \['responsableRevision', 'Responsable de la revisión'\],
  \['cargoRevision', 'Cargo revisión'\],
  \['tarjetaRevision', 'Tarjeta profesional revisión'\],
  \['fecha', 'Fecha de levantamiento'\],
  \['hora', 'Hora'\]
\]"""

    new_fields = """const segmentosIdPuente = [
  {
    key: 'idPuente',
    label: 'Territorial / Departamento',
    maxLength: 2,
    mode: 'numeric',
    width: 180
  },
  {
    key: 'idCarreteraTramo',
    label: 'ID carretera y tramo',
    maxLength: 8,
    mode: 'alphanumeric',
    width: 310
  },
  {
    key: 'sentido',
    label: 'Sentido',
    maxLength: 2,
    mode: 'numeric',
    width: 140
  },
  {
    key: 'consecutivo',
    label: 'Consecutivo',
    maxLength: 4,
    mode: 'numeric',
    width: 175
  }
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
]"""

    panel_code = replace_once(
        panel_code,
        old_fields,
        new_fields,
        "la lista de campos de Identificación",
    )

    # ========================================================
    # 2. ESTADO INICIAL
    # ========================================================

    panel_code = replace_once(
        panel_code,
        r"""function crearIdentificacionInicial\(\) \{
  return camposIdentificacion\.reduce\(\(acc, \[key\]\) => \{
    acc\[key\] = ''
    return acc
  \}, \{\}\)
\}""",
        """function crearIdentificacionInicial() {
  const campos = [
    ...segmentosIdPuente.map((segmento) => [segmento.key]),
    ...camposIdentificacion
  ]

  return campos.reduce((acc, [key]) => {
    acc[key] = ''
    return acc
  }, {})
}""",
        "crearIdentificacionInicial",
    )

    # ========================================================
    # 3. NORMALIZACIÓN
    # ========================================================

    panel_code = replace_once(
        panel_code,
        r"""function limpiarTexto\(valor\) \{
  return String\(valor \|\| ''\)\.replace\(/\\s\+/g, ' '\)\.trim\(\)
\}""",
        """function limpiarTexto(valor) {
  return String(valor || '').replace(/\\s+/g, ' ').trim()
}

function normalizarIdentificacion(key, value) {
  const texto = String(value ?? '')

  if (key === 'idPuente') {
    return texto.replace(/\\D/g, '').slice(0, 2)
  }

  if (key === 'idCarreteraTramo') {
    return texto
      .replace(/[^A-Za-z0-9]/g, '')
      .toUpperCase()
      .slice(0, 8)
  }

  if (key === 'sentido') {
    return texto.replace(/\\D/g, '').slice(0, 2)
  }

  if (key === 'consecutivo') {
    return texto.replace(/\\D/g, '').slice(0, 4)
  }

  return texto
}""",
        "la validación de los segmentos",
    )

    # ========================================================
    # 4. ACTUALIZACIÓN DEL ESTADO
    # ========================================================

    panel_code = replace_once(
        panel_code,
        r"""  function actualizarIdentificacion\(key, value\) \{
    setIdentificacion\(\(actual\) => \(\{
      \.\.\.actual,
      \[key\]: value
    \}\)\)
  \}""",
        """  function actualizarIdentificacion(key, value) {
    const valor = normalizarIdentificacion(key, value)

    setIdentificacion((actual) => ({
      ...actual,
      [key]: valor
    }))
  }""",
        "actualizarIdentificacion",
    )

    # ========================================================
    # 5. INTERFAZ DEL BLOQUE COMPLETO
    # ========================================================

    old_ui = r"""        \{identificacionAbierta && \(
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
        \)\}"""

    new_ui = """        {identificacionAbierta && (
          <>
            <div style={styles.idCompletoContenedor}>
              <div style={styles.idCompletoEncabezado}>
                <strong>ID Puente completo</strong>

                <span style={styles.idCompletoResultado}>
                  {identificacion.idPuente || '—'}
                  -
                  {identificacion.idCarreteraTramo || '—'}
                  -
                  {identificacion.sentido || '—'}
                  -
                  {identificacion.consecutivo || '—'}
                </span>
              </div>

              <div style={styles.idCompletoScroll}>
                <div style={styles.idCompletoFila}>
                  {segmentosIdPuente.map((segmento, index) => (
                    <div
                      key={segmento.key}
                      style={styles.idCompletoSegmento}
                    >
                      <label
                        style={{
                          ...styles.label,
                          width: segmento.width,
                          minWidth: segmento.width
                        }}
                      >
                        {segmento.label}

                        <input
                          type="text"
                          value={identificacion[segmento.key] || ''}
                          maxLength={segmento.maxLength}
                          inputMode={
                            segmento.mode === 'numeric'
                              ? 'numeric'
                              : 'text'
                          }
                          autoComplete="off"
                          spellCheck={false}
                          onChange={(event) =>
                            actualizarIdentificacion(
                              segmento.key,
                              event.target.value
                            )
                          }
                          style={{
                            ...styles.input,
                            ...styles.idCompletoInput
                          }}
                        />
                      </label>

                      {index < segmentosIdPuente.length - 1 && (
                        <span style={styles.idCompletoGuion}>–</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div style={styles.gridIdentificacion}>
              {camposIdentificacion.map(([key, label]) => (
                <label key={key} style={styles.label}>
                  {label}

                  <input
                    value={identificacion[key] || ''}
                    onChange={(event) =>
                      actualizarIdentificacion(
                        key,
                        event.target.value
                      )
                    }
                    style={styles.input}
                  />
                </label>
              ))}
            </div>
          </>
        )}"""

    panel_code = replace_once(
        panel_code,
        old_ui,
        new_ui,
        "la interfaz del panel Identificación",
    )

    # ========================================================
    # 6. ESTILOS
    # ========================================================

    new_styles = """  idCompletoContenedor: {
    marginBottom: 10,
    padding: '9px 10px 7px',
    border: '1px solid #047857',
    borderRadius: 8,
    background: 'rgba(2, 22, 16, 0.65)',
    overflow: 'hidden'
  },
  idCompletoEncabezado: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
    marginBottom: 8,
    color: '#34d399',
    fontSize: 11
  },
  idCompletoResultado: {
    color: '#93c5fd',
    fontFamily: 'Consolas, "Courier New", monospace',
    fontWeight: 800,
    letterSpacing: '0.06em',
    textAlign: 'right'
  },
  idCompletoScroll: {
    width: '100%',
    overflowX: 'auto',
    overflowY: 'hidden',
    paddingBottom: 7
  },
  idCompletoFila: {
    display: 'flex',
    alignItems: 'flex-end',
    minWidth: 930,
    width: 'max-content',
    gap: 10
  },
  idCompletoSegmento: {
    display: 'flex',
    alignItems: 'flex-end',
    gap: 10,
    flexShrink: 0
  },
  idCompletoGuion: {
    color: '#6ee7b7',
    fontSize: 20,
    fontWeight: 900,
    lineHeight: '31px'
  },
  idCompletoInput: {
    textAlign: 'center',
    fontFamily: 'Consolas, "Courier New", monospace',
    fontWeight: 800,
    fontSize: 14,
    letterSpacing: '0.14em',
    textTransform: 'uppercase'
  },
  gridIdentificacion: {"""

    panel_code = replace_once(
        panel_code,
        r"""  gridIdentificacion: \{""",
        new_styles,
        "los estilos del nuevo bloque",
    )

    # ========================================================
    # 7. BACKEND / EXCEL
    # ========================================================

    backend_replacement = """    # ID Puente completo dividido en cuatro segmentos.
    id_groups = [
        (
            "idPuente",
            ["G13", "H13"],
            r"[^0-9]",
            2,
        ),
        (
            "idCarreteraTramo",
            [
                "J13", "K13", "L13", "M13",
                "N13", "O13", "P13", "Q13",
            ],
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

    for index, (key, refs, forbidden, maximum) in enumerate(id_groups):
        raw = str(
            identificacion.get(key)
            or ""
        ).strip()

        if (
            not raw
            and legacy_parts
            and index < len(legacy_parts)
        ):
            raw = legacy_parts[index]

        clean = re.sub(
            forbidden,
            "",
            raw,
        )[:maximum]

        if key == "idCarreteraTramo":
            clean = clean.upper()

        for ref, character in zip(refs, clean):
            write(
                ref,
                character,
                key,
            )

    # Fecha: formato visual M6 N6 / P6 Q6 / S6"""

    server_code = replace_once(
        server_code,
        r"""    # ID Puente: celdas reales separadas por guiones del formato\.
.*?
    # Fecha: formato visual M6 N6 / P6 Q6 / S6""",
        backend_replacement,
        "la escritura del ID Puente en Excel",
    )

    # ========================================================
    # 8. GUARDAR
    # ========================================================

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

    # ========================================================
    # 9. VALIDAR BACKEND
    # ========================================================

    print()
    print("Validando backend...")

    backend_test = subprocess.run(
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

    if backend_test.returncode != 0:
        raise RuntimeError(
            "Backend inválido:\n"
            + backend_test.stderr
        )

    print("Backend correcto.")

    # ========================================================
    # 10. VALIDAR FRONTEND
    # ========================================================

    npm = shutil.which("npm.cmd") or shutil.which("npm")

    if not npm:
        raise RuntimeError("No encontré npm.")

    print()
    print("Validando frontend...")

    frontend_test = subprocess.run(
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

    print(frontend_test.stdout)

    if frontend_test.returncode != 0:
        raise RuntimeError(
            "Frontend inválido:\n"
            + frontend_test.stderr
        )

    # ========================================================
    # 11. COMPROBACIÓN REAL
    # ========================================================

    final_panel = read_text(PANEL)
    final_server = read_text(SERVER)

    required_frontend = [
        "ID Puente completo",
        "idCarreteraTramo",
        "idCompletoScroll",
        "Territorial / Departamento",
        "Consecutivo",
    ]

    required_backend = [
        '"idCarreteraTramo"',
        '"sentido"',
        '"consecutivo"',
        '["G13", "H13"]',
        '["S13", "T13"]',
        '["V13", "W13", "X13", "Y13"]',
    ]

    for marker in required_frontend:
        if marker not in final_panel:
            raise RuntimeError(
                f"No apareció en frontend: {marker}"
            )

    for marker in required_backend:
        if marker not in final_server:
            raise RuntimeError(
                f"No apareció en backend: {marker}"
            )

except Exception as error:
    rollback()

    print()
    print("=" * 72)
    print("ERROR — CAMBIOS REVERTIDOS")
    print("=" * 72)
    print(error)

    raise SystemExit(1)


# ============================================================
# LIMPIAR CACHÉ Y BACKUP FINAL
# ============================================================

shutil.rmtree(
    ROOT / "node_modules" / ".vite",
    ignore_errors=True,
)

backup_after = create_backup(
    "SIPUCOL_BASE_CANONICA_ID_COMPLETO_REAL"
)

print()
print("=" * 72)
print("ID PUENTE COMPLETO INSTALADO REALMENTE")
print("=" * 72)

print()
print("Debe aparecer arriba de Nombre del puente:")
print("- Territorial / Departamento")
print("- ID carretera y tramo")
print("- Sentido")
print("- Consecutivo")
print("- Vista previa del ID completo")
print("- Scroll horizontal dentro del bloque")

print()
print("Excel:")
print("- G13:H13 = Territorial / Departamento")
print("- J13:Q13 = ID carretera y tramo")
print("- S13:T13 = Sentido")
print("- V13:Y13 = Consecutivo")

print()
print("BACKUP ANTERIOR:")
print(backup_before)

print()
print("BACKUP FINAL:")
print(backup_after)
