from __future__ import annotations

import py_compile
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path


ROOT = Path.cwd()
BACKEND = ROOT / "backend"
SRC = ROOT / "src"

STAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


# =========================================================
# 1. BACKUPS
# =========================================================

backup_targets = [
    BACKEND / "server.py",
    BACKEND / "pdf_repair_worker.py",
    BACKEND / "excel_repair_to_pdf.ps1",
    SRC / "main.jsx",
    SRC / "uiFinalFix.js",
]

for source in backup_targets:

    if not source.exists():
        continue

    backup = source.with_name(
        f"{source.stem}.backup_{STAMP}{source.suffix}"
    )

    shutil.copy2(
        source,
        backup,
    )

    print(
        "BACKUP:",
        backup,
    )


# =========================================================
# 2. MOTOR EXCEL:
#    ABRIR Y REPARAR -> PDF
# =========================================================

engine_path = (
    BACKEND
    / "excel_repair_to_pdf.ps1"
)


engine_code = r'''param(
    [Parameter(Mandatory = $true)]
    [string]$ExcelPath,

    [Parameter(Mandatory = $true)]
    [string]$PdfPath
)

$ErrorActionPreference = "Stop"

$excel = $null
$books = $null
$book = $null


function Release-ComSafe {

    param(
        [object]$Value
    )

    if ($null -eq $Value) {
        return
    }

    try {

        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject(
            $Value
        )

    }
    catch {
    }
}


try {

    if (
        -not (
            Test-Path `
                -LiteralPath $ExcelPath `
                -PathType Leaf
        )
    ) {

        throw "The selected Excel file does not exist."
    }


    $pdfDirectory = (
        [System.IO.Path]::GetDirectoryName(
            $PdfPath
        )
    )


    if (
        -not (
            [string]::IsNullOrWhiteSpace(
                $pdfDirectory
            )
        )
    ) {

        [System.IO.Directory]::CreateDirectory(
            $pdfDirectory
        ) |
        Out-Null
    }


    if (
        Test-Path `
            -LiteralPath $PdfPath
    ) {

        Remove-Item `
            -LiteralPath $PdfPath `
            -Force
    }


    Write-Output "Starting Microsoft Excel..."


    $excel = New-Object `
        -ComObject Excel.Application


    if (
        $null -eq $excel
    ) {

        throw "Microsoft Excel could not be started."
    }


    $excel.Visible = $false

    $excel.DisplayAlerts = $false

    $excel.EnableEvents = $false

    $excel.ScreenUpdating = $false


    try {

        $excel.AskToUpdateLinks = $false

    }
    catch {
    }


    try {

        $excel.AutomationSecurity = 3

    }
    catch {
    }


    $books = $excel.Workbooks


    if (
        $null -eq $books
    ) {

        throw "Excel did not expose the Workbooks collection."
    }


    $missing = (
        [System.Type]::Missing
    )


    Write-Output "Opening workbook in repair mode..."


    $repairError = ""


    try {

        # CorruptLoad = 1
        # xlRepairFile
        #
        # Excel attempts to repair the workbook
        # without displaying the recovery dialog.

        $book = $books.Open(
            $ExcelPath,
            $missing,
            $true,
            $missing,
            $missing,
            $missing,
            $true,
            $missing,
            $missing,
            $missing,
            $false,
            $missing,
            $false,
            $true,
            1
        )

    }
    catch {

        $repairError = (
            $_.Exception.Message
        )
    }


    if (
        $null -eq $book
    ) {

        Write-Output "Repair mode failed. Trying data extraction mode..."


        try {

            # CorruptLoad = 2
            # xlExtractData

            $book = $books.Open(
                $ExcelPath,
                $missing,
                $true,
                $missing,
                $missing,
                $missing,
                $true,
                $missing,
                $missing,
                $missing,
                $false,
                $missing,
                $false,
                $true,
                2
            )

        }
        catch {

            $extractError = (
                $_.Exception.Message
            )


            throw (
                "Excel could not open or repair the workbook. "
                + "Repair: "
                + $repairError
                + " | Extract: "
                + $extractError
            )
        }
    }


    if (
        $null -eq $book
    ) {

        throw "Excel returned an empty workbook."
    }


    Write-Output "Workbook opened."


    try {

        $excel.CalculateFullRebuild()

    }
    catch {

        try {

            $excel.CalculateFull()

        }
        catch {
        }
    }


    Start-Sleep `
        -Milliseconds 700


    Write-Output "Exporting PDF..."


    $book.ExportAsFixedFormat(
        0,
        $PdfPath,
        0,
        $true,
        $false
    )


    if (
        -not (
            Test-Path `
                -LiteralPath $PdfPath `
                -PathType Leaf
        )
    ) {

        throw "Excel finished without creating the PDF."
    }


    $pdfInfo = (
        Get-Item `
            -LiteralPath $PdfPath
    )


    if (
        $pdfInfo.Length
        -lt 5000
    ) {

        throw "The generated PDF is empty or incomplete."
    }


    Write-Output "PDF_OK=$PdfPath"

    Write-Output "PDF_SIZE=$($pdfInfo.Length)"

}
catch {

    [Console]::Error.WriteLine(
        $_.Exception.Message
    )

    exit 1

}
finally {

    if (
        $null -ne $book
    ) {

        try {

            $book.Close(
                $false
            )

        }
        catch {
        }


        Release-ComSafe `
            -Value $book


        $book = $null
    }


    if (
        $null -ne $books
    ) {

        Release-ComSafe `
            -Value $books


        $books = $null
    }


    if (
        $null -ne $excel
    ) {

        try {

            $excel.Quit()

        }
        catch {
        }


        Release-ComSafe `
            -Value $excel


        $excel = $null
    }


    [System.GC]::Collect()

    [System.GC]::WaitForPendingFinalizers()
}
'''


engine_path.write_text(

    engine_code,

    encoding="utf-8-sig",
)


print(
    "MOTOR PDF CREADO:",
    engine_path,
)


# =========================================================
# 3. VALIDAR SINTAXIS POWERSHELL
# =========================================================

parser_command = (
    "$tokens=$null;"
    "$errors=$null;"
    "[System.Management.Automation.Language.Parser]"
    "::ParseFile("
    f"'{engine_path}',"
    "[ref]$tokens,"
    "[ref]$errors"
    ") | Out-Null;"
    "if($errors.Count -gt 0){"
    "$errors | ForEach-Object {"
    "[Console]::Error.WriteLine($_.Message)"
    "};"
    "exit 1"
    "};"
    "Write-Output 'POWERSHELL_OK'"
)


parser_result = subprocess.run(

    [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        parser_command,
    ],

    cwd=str(
        ROOT
    ),

    capture_output=True,

    text=True,
)


if (
    parser_result.returncode
    != 0
):

    raise RuntimeError(

        "El motor PDF tiene "
        "un error de sintaxis:\n"

        + parser_result.stderr

        + parser_result.stdout
    )


print(
    "POWERSHELL: SINTAXIS CORRECTA"
)


# =========================================================
# 4. WORKER PYTHON
# =========================================================

worker_path = (
    BACKEND
    / "pdf_repair_worker.py"
)


worker_code = r'''from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path


def _decode(
    data: bytes,
) -> str:

    for encoding in (
        "utf-8",
        "mbcs",
        "cp1252",
        "latin-1",
    ):

        try:

            return data.decode(
                encoding
            )

        except Exception:

            continue

    return data.decode(
        "latin-1",
        errors="replace",
    )


def _wait_until_stable(
    path: Path,
) -> None:

    previous_size = -1

    stable_checks = 0


    for _ in range(
        20
    ):

        if not path.exists():

            time.sleep(
                0.25
            )

            continue


        current_size = (
            path.stat().st_size
        )


        if (
            current_size
            == previous_size

            and current_size
            > 1000
        ):

            stable_checks += 1

        else:

            stable_checks = 0


        if (
            stable_checks
            >= 3
        ):

            return


        previous_size = (
            current_size
        )


        time.sleep(
            0.25
        )


    if (
        not path.exists()

        or path.stat().st_size
        < 1000
    ):

        raise RuntimeError(

            "El Excel seleccionado "
            "todavía no terminó "
            "de guardarse."
        )


def _validate_ooxml(
    path: Path,
) -> None:

    if (
        path.suffix.lower()
        not in {
            ".xlsx",
            ".xlsm",
        }
    ):

        return


    if not zipfile.is_zipfile(
        path
    ):

        raise RuntimeError(

            "El Excel seleccionado "
            "no contiene una estructura "
            "XLSX/XLSM válida. "
            "Vuelve a generarlo y espera "
            "a que termine de guardarse."
        )


    with zipfile.ZipFile(
        path,
        "r",
    ) as archive:

        required = {

            "[Content_Types].xml",

            "xl/workbook.xml",
        }


        names = set(
            archive.namelist()
        )


        missing = (

            required

            - names
        )


        if missing:

            raise RuntimeError(

                "El Excel está incompleto. "
                "Faltan archivos internos: "

                + ", ".join(
                    sorted(
                        missing
                    )
                )
            )


def _validate_pdf(
    path: Path,
) -> None:

    if not path.exists():

        raise RuntimeError(

            "Microsoft Excel terminó "
            "sin crear el PDF."
        )


    if (
        path.stat().st_size
        < 5000
    ):

        raise RuntimeError(

            "El PDF creado está "
            "vacío o incompleto."
        )


    with path.open(
        "rb"
    ) as file:

        if (
            file.read(
                5
            )

            != b"%PDF-"
        ):

            raise RuntimeError(

                "El archivo creado "
                "no es un PDF válido."
            )


def convertir_excel_seleccionado_job(
    job_id: str,
    excel_path: str,
    pdf_path: str,
) -> None:

    from backend import server


    temp_directory: Path | None = None


    try:

        source = Path(
            excel_path
        )


        output = Path(
            pdf_path
        )


        server.log(
            "=" * 70
        )


        server.log(

            f"Job {job_id}: "

            "PDF DESDE EXCEL "

            "CON REPARACIÓN NATIVA"
        )


        server.log(

            f"Excel origen: "
            f"{source}"
        )


        server.log(

            f"PDF destino: "
            f"{output}"
        )


        server.log(
            "=" * 70
        )


        if (

            not source.exists()

            or not source.is_file()

        ):

            raise RuntimeError(

                "No existe el Excel "
                "seleccionado."
            )


        _wait_until_stable(
            source
        )


        output.parent.mkdir(

            parents=True,

            exist_ok=True,
        )


        if output.exists():

            output.unlink()


        server.set_job(

            job_id,

            status="running",

            progress=10,

            message=(

                "Validando el Excel "
                "seleccionado..."
            ),

            source_excel=str(
                source
            ),

            output_path=str(
                output
            ),
        )


        temp_directory = Path(

            tempfile.mkdtemp(

                prefix=(
                    "sipucol_pdf_"
                )
            )
        )


        local_excel = (

            temp_directory

            / source.name
        )


        local_pdf = (

            temp_directory

            / "resultado.pdf"
        )


        shutil.copy2(

            source,

            local_excel,
        )


        _wait_until_stable(
            local_excel
        )


        _validate_ooxml(
            local_excel
        )


        server.set_job(

            job_id,

            progress=32,

            message=(

                "Microsoft Excel está "
                "abriendo y reparando "
                "la copia local..."
            ),
        )


        engine = (

            Path(
                server.BASE_DIR
            )

            / "backend"

            / (
                "excel_repair_"
                "to_pdf.ps1"
            )
        )


        if not engine.exists():

            raise RuntimeError(

                "No se encontró "
                "el motor PDF."
            )


        command = [

            "powershell.exe",

            "-NoProfile",

            "-ExecutionPolicy",

            "Bypass",

            "-File",

            str(
                engine
            ),

            "-ExcelPath",

            str(
                local_excel
            ),

            "-PdfPath",

            str(
                local_pdf
            ),
        ]


        result = subprocess.run(

            command,

            capture_output=True,

            timeout=600,

            creationflags=getattr(

                subprocess,

                "CREATE_NO_WINDOW",

                0,
            ),
        )


        stdout = _decode(

            result.stdout

        ).strip()


        stderr = _decode(

            result.stderr

        ).strip()


        if stdout:

            server.log(

                f"Job {job_id}: "

                f"PDF stdout: "

                f"{stdout}"
            )


        if stderr:

            server.log(

                f"Job {job_id}: "

                f"PDF stderr: "

                f"{stderr}"
            )


        if (

            result.returncode

            != 0

        ):

            detail = (

                stderr

                or stdout

                or (

                    "Microsoft Excel "
                    "no pudo reparar "
                    "ni exportar el libro."
                )
            )


            raise RuntimeError(
                detail
            )


        server.set_job(

            job_id,

            progress=82,

            message=(

                "Copiando el PDF "
                "a la ubicación elegida..."
            ),
        )


        _validate_pdf(
            local_pdf
        )


        shutil.copy2(

            local_pdf,

            output,
        )


        server.set_job(

            job_id,

            progress=95,

            message=(

                "Validando el PDF final..."
            ),
        )


        _validate_pdf(
            output
        )


        server.set_job(

            job_id,

            status="done",

            progress=100,

            message=(

                "PDF creado "
                "correctamente."
            ),

            source_excel=str(
                source
            ),

            output_path=str(
                output
            ),
        )


        server.log(

            f"Job {job_id}: "

            f"PDF LISTO -> "

            f"{output}"
        )


    except Exception as error:

        server.set_job(

            job_id,

            status="error",

            progress=0,

            message=(

                "No se pudo "
                "crear el PDF"
            ),

            error=str(
                error
            ),
        )


        server.log(

            f"Job {job_id}: "

            f"ERROR PDF -> "

            f"{error}"
        )


    finally:

        if (

            temp_directory

            is not None

        ):

            shutil.rmtree(

                temp_directory,

                ignore_errors=True,
            )
'''


worker_path.write_text(

    worker_code,

    encoding="utf-8",
)


py_compile.compile(

    str(
        worker_path
    ),

    doraise=True,
)


print(
    "WORKER PYTHON: "
    "SINTAXIS CORRECTA"
)


# =========================================================
# 5. CONECTAR MOTOR NUEVO AL BACKEND
# =========================================================

server_path = (
    BACKEND
    / "server.py"
)


server = server_path.read_text(
    encoding="utf-8"
)


start_marker = (
    "# === "
    "SIPUCOL_PDF_REPAIR_FINAL_START "
    "==="
)


end_marker = (
    "# === "
    "SIPUCOL_PDF_REPAIR_FINAL_END "
    "==="
)


server = re.sub(

    re.escape(
        start_marker
    )

    + r"[\s\S]*?"

    + re.escape(
        end_marker
    ),

    "",

    server,
)


binding = r'''
# === SIPUCOL_PDF_REPAIR_FINAL_START ===

# Motor actual:
# Excel seleccionado
# -> copia local
# -> reparación nativa de Excel
# -> PDF.

from backend.pdf_repair_worker import (
    convertir_excel_seleccionado_job
    as _sipucol_pdf_repair_job
)

convertir_excel_seleccionado_job = (
    _sipucol_pdf_repair_job
)

# === SIPUCOL_PDF_REPAIR_FINAL_END ===
'''


server = (

    server.rstrip()

    + "\n\n"

    + binding.strip()

    + "\n"
)


server_path.write_text(

    server,

    encoding="utf-8",
)


py_compile.compile(

    str(
        server_path
    ),

    doraise=True,
)


print(
    "BACKEND: "
    "SINTAXIS CORRECTA"
)


# =========================================================
# 6. UI FINAL:
#    SIN HEURÍSTICAS PELIGROSAS
# =========================================================

ui_path = (
    SRC
    / "uiFinalFix.js"
)


ui_code = r'''
const ID_MAX_LENGTH = 2


function normalizeText(
  value
) {

  return String(
    value || ""
  )
    .trim()
    .toLowerCase()
    .normalize(
      "NFD"
    )
    .replace(
      /[\u0300-\u036f]/g,
      ""
    )
}


function findFieldInput(
  caption
) {

  const wanted =
    normalizeText(
      caption
    )


  const captions = [

    ...document
      .querySelectorAll(
        "label, span, p, div"
      )
  ]
    .filter(

      element =>

        normalizeText(
          element.textContent
        )

        === wanted
    )


  captions.sort(

    (
      first,
      second
    ) =>

      first.children.length

      - second.children.length
  )


  for (
    const captionElement
    of captions
  ) {

    if (

      captionElement
      instanceof HTMLLabelElement

      && captionElement.htmlFor

    ) {

      const linked =

        document
          .getElementById(
            captionElement.htmlFor
          )


      if (

        linked
        instanceof HTMLInputElement

      ) {

        return linked
      }
    }


    const inside =

      captionElement
        .querySelector(
          "input"
        )


    if (

      inside
      instanceof HTMLInputElement

    ) {

      return inside
    }


    let current =
      captionElement.parentElement


    for (
      let level = 0;
      level < 3;
      level += 1
    ) {

      if (!current) {
        break
      }


      const inputs =

        current
          .querySelectorAll(
            "input"
          )


      if (
        inputs.length === 1
      ) {

        return inputs[0]
      }


      current =
        current.parentElement
    }
  }


  return null
}


function configureBridgeId() {

  const input =

    findFieldInput(
      "ID Puente"
    )


  if (!input) {

    return false
  }


  input.type =
    "text"


  input.inputMode =
    "numeric"


  input.maxLength =
    ID_MAX_LENGTH


  input.setAttribute(

    "maxlength",

    String(
      ID_MAX_LENGTH
    )
  )


  input.setAttribute(

    "pattern",

    "[0-9]{0,2}"
  )


  input.setAttribute(

    "placeholder",

    "00"
  )


  input.setAttribute(

    "autocomplete",

    "off"
  )


  input.setAttribute(

    "data-sipucol-real-id",

    "true"
  )


  return true
}


function projectedLength(
  input,
  inserted
) {

  const start =

    input.selectionStart

    ?? input.value.length


  const end =

    input.selectionEnd

    ?? start


  return (

    input.value.length

    - (
      end
      - start
    )

    + inserted.length
  )
}


document.addEventListener(

  "keydown",

  event => {

    const input =
      event.target


    if (

      !(
        input
        instanceof HTMLInputElement
      )

      || input.getAttribute(
        "data-sipucol-real-id"
      )
      !== "true"

    ) {

      return
    }


    if (

      event.ctrlKey

      || event.metaKey

      || event.altKey

    ) {

      return
    }


    const allowed =
      new Set([

        "Backspace",

        "Delete",

        "Tab",

        "Enter",

        "Escape",

        "ArrowLeft",

        "ArrowRight",

        "Home",

        "End"
      ])


    if (
      allowed.has(
        event.key
      )
    ) {

      return
    }


    if (

      !/^[0-9]$/.test(
        event.key
      )

      || projectedLength(
        input,
        event.key
      )
      > ID_MAX_LENGTH

    ) {

      event.preventDefault()
    }
  },

  true
)


document.addEventListener(

  "beforeinput",

  event => {

    const input =
      event.target


    if (

      !(
        input
        instanceof HTMLInputElement
      )

      || input.getAttribute(
        "data-sipucol-real-id"
      )
      !== "true"

    ) {

      return
    }


    if (

      !String(
        event.inputType
        || ""
      )
      .startsWith(
        "insert"
      )

    ) {

      return
    }


    if (
      event.data === null
    ) {

      return
    }


    if (

      !/^[0-9]+$/.test(
        event.data
      )

      || projectedLength(
        input,
        event.data
      )
      > ID_MAX_LENGTH

    ) {

      event.preventDefault()
    }
  },

  true
)


document.addEventListener(

  "paste",

  event => {

    const input =
      event.target


    if (

      !(
        input
        instanceof HTMLInputElement
      )

      || input.getAttribute(
        "data-sipucol-real-id"
      )
      !== "true"

    ) {

      return
    }


    const text =

      event.clipboardData

      ?.getData(
        "text"
      )

      ?? ""


    if (

      !/^[0-9]+$/.test(
        text
      )

      || projectedLength(
        input,
        text
      )
      > ID_MAX_LENGTH

    ) {

      event.preventDefault()
    }
  },

  true
)


function configureDateAndTime() {

  const dateInput =

    findFieldInput(
      "Fecha de levantamiento"
    )


  if (dateInput) {

    dateInput.type =
      "date"

    dateInput.style.colorScheme =
      "dark"
  }


  const timeInput =

    findFieldInput(
      "Hora"
    )


  if (timeInput) {

    timeInput.type =
      "time"

    timeInput.step =
      "60"

    timeInput.style.colorScheme =
      "dark"
  }
}


function hidePhotoEvaluation() {

  const exactTitle = [

    ...document
      .querySelectorAll(
        "div, span, p, label, strong"
      )
  ]
    .find(

      element =>

        normalizeText(
          element.textContent
        )

        === (
          "enviar foto "
          + "a evaluacion"
        )
    )


  if (!exactTitle) {

    return false
  }


  let current =
    exactTitle.parentElement


  for (
    let level = 0;
    level < 6;
    level += 1
  ) {

    if (!current) {
      break
    }


    const text =

      normalizeText(
        current.textContent
      )


    if (

      text.includes(
        "destino:"
      )

      && !text.includes(
        "carpeta actual"
      )

      && current
        .querySelectorAll(
          "button"
        )
        .length > 0

    ) {

      current.style
        .setProperty(

          "display",

          "none",

          "important"
        )


      return true
    }


    current =
      current.parentElement
  }


  return false
}


function styleButtons() {

  const buttons =

    document
      .querySelectorAll(
        "button"
      )


  for (
    const button
    of buttons
  ) {

    const text =

      normalizeText(
        button.textContent
      )


    if (

      text.includes(
        "guardar proyecto"
      )

      || text.includes(
        "cargar proyecto"
      )

      || text.includes(
        "guardar excel"
      )

      || text.includes(
        "guardar pdf"
      )

    ) {

      button.classList.add(

        "sipucol-final-button"
      )
    }
  }
}


function installStyles() {

  if (

    document
      .getElementById(
        "sipucol-final-fix-style"
      )

  ) {

    return
  }


  const style =

    document
      .createElement(
        "style"
      )


  style.id =
    "sipucol-final-fix-style"


  style.textContent = `

    .sipucol-final-button {

      min-height:
        42px !important;

      padding:
        0 18px !important;

      border:
        1px solid
        rgba(
          44,
          231,
          167,
          0.78
        )
        !important;

      border-radius:
        10px !important;

      background:
        rgba(
          10,
          103,
          72,
          0.84
        )
        !important;

      background-image:
        none !important;

      color:
        #effff8 !important;

      box-shadow:
        0 0 10px
        rgba(
          37,
          221,
          157,
          0.11
        )
        !important;

      transition:
        transform 150ms ease,
        filter 150ms ease,
        box-shadow 150ms ease
        !important;
    }


    .sipucol-final-button:hover {

      transform:
        translateY(
          -1px
        )
        !important;

      filter:
        brightness(
          1.1
        )
        !important;

      box-shadow:
        0 0 18px
        rgba(
          45,
          229,
          166,
          0.24
        )
        !important;
    }


    .sipucol-final-button:active {

      transform:
        scale(
          0.985
        )
        !important;
    }


    input[
      data-sipucol-real-id="true"
    ] {

      font-variant-numeric:
        tabular-nums;
    }
  `


  document.head.appendChild(
    style
  )
}


function applyUi() {

  installStyles()

  configureBridgeId()

  configureDateAndTime()

  hidePhotoEvaluation()

  styleButtons()
}


function startUi() {

  let attempts = 0


  const timer =

    window.setInterval(

      () => {

        attempts += 1

        applyUi()


        if (
          attempts >= 20
        ) {

          window.clearInterval(
            timer
          )
        }
      },

      250
    )


  applyUi()
}


if (

  document.readyState

  === "loading"

) {

  document.addEventListener(

    "DOMContentLoaded",

    startUi,

    {
      once:
        true
    }
  )

}
else {

  startUi()
}
'''


ui_path.write_text(

    ui_code,

    encoding="utf-8",
)


# =========================================================
# 7. DEJAR UN SOLO SCRIPT UI ACTIVO
# =========================================================

main_path = (
    SRC
    / "main.jsx"
)


main = main_path.read_text(
    encoding="utf-8"
)


old_modules = [

    "autosaveSafetyUI.js",

    "idPuenteGuard.js",

    "uiStable.js",

    "uiFinalFix.js",

    "sessionMode.js",

    "startFresh.js",

    "projectControlsPolish.js",
]


for module in old_modules:

    main = re.sub(

        (
            r'^\s*import\s+'
            r'["\']\./'

            + re.escape(
                module
            )

            + r'["\'];?\s*$'
        ),

        "",

        main,

        flags=re.MULTILINE,
    )


main = (

    'import "./uiFinalFix.js";\n'

    + main.lstrip()
)


main_path.write_text(

    main,

    encoding="utf-8",
)


print(
    "UI: "
    "UN SOLO MÓDULO ACTIVO"
)


# =========================================================
# 8. VALIDAR MOTOR ACTIVO
# =========================================================

check = subprocess.run(

    [

        sys.executable,

        "-c",

        (
            "import backend.server as s;"

            "print("

            "s.convertir_excel_"
            "seleccionado_job"
            ".__module__"

            ")"
        ),
    ],

    cwd=str(
        ROOT
    ),

    capture_output=True,

    text=True,
)


if (
    check.returncode
    != 0
):

    raise RuntimeError(

        "No se pudo cargar "
        "backend.server:\n"

        + check.stderr
    )


loaded_module = (

    check.stdout
    .strip()
    .splitlines()[-1]
)


if (

    loaded_module

    != (
      "backend."
      "pdf_repair_worker"
    )

):

    raise RuntimeError(

        "El backend no quedó "
        "usando el motor nuevo.\n"

        "Motor detectado: "

        + loaded_module
    )


print(
    "MOTOR ACTIVO:",
    loaded_module,
)


print()
print(
    "=" * 68
)

print(
    "REPARACIÓN INSTALADA Y VALIDADA"
)

print(
    "=" * 68
)

print(
    "PDF: modo reparación nativo de Excel."
)

print(
    "PDF: copia temporal local."
)

print(
    "ID Puente: solo números, máximo 2."
)

print(
    "Fotos: buscador restaurado."
)

print(
    "Fotos: envío a Evaluación oculto."
)

print(
    "UI: sin observers permanentes."
)
