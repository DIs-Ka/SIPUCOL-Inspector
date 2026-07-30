
param(
    [Parameter(Mandatory=$true)]
    [string]$WorkbookPath,

    [Parameter(Mandatory=$true)]
    [string]$PdfPath,

    [Parameter(Mandatory=$true)]
    [string]$SheetsJson
)

$ErrorActionPreference = "Stop"

$excel = $null
$workbook = $null

try {

    if (
        !(Test-Path -LiteralPath $WorkbookPath)
    ) {
        throw "No existe el Excel temporal: $WorkbookPath"
    }


    $wantedSheets = @(
        Get-Content `
        -LiteralPath $SheetsJson `
        -Raw `
        -Encoding UTF8 |
        ConvertFrom-Json
    )


    $wantedNormalized = @(

        $wantedSheets |

        ForEach-Object {

            $_
            .ToString()
            .Trim()
            .ToLowerInvariant()
        }
    )


    $excel = New-Object `
        -ComObject Excel.Application


    $excel.Visible = $false

    $excel.DisplayAlerts = $false

    $excel.AskToUpdateLinks = $false

    $excel.EnableEvents = $false

    $excel.ScreenUpdating = $false


    try {

        # Desactivar macros durante la automatización.
        $excel.AutomationSecurity = 3

    } catch {

        # Algunas versiones no exponen esta propiedad.
    }


    $workbook = (
        $excel.Workbooks.Open(
            $WorkbookPath,
            0,
            $false
        )
    )


    # Recalcular exactamente como Excel.
    try {

        # xlCalculationAutomatic
        $excel.Calculation = -4105

    } catch {

    }


    $excel.CalculateFullRebuild()


    $deadline = (
        Get-Date
    ).AddSeconds(
        120
    )


    while (
        $excel.CalculationState -ne 0
        -and
        (Get-Date) -lt $deadline
    ) {

        Start-Sleep `
            -Milliseconds 250
    }


    # Guardar los resultados calculados
    # dentro del XLSM temporal.
    $workbook.Save()


    $keptSheets = @()


    foreach (
        $worksheet
        in $workbook.Worksheets
    ) {

        $sheetName = (
            $worksheet.Name
            .ToString()
            .Trim()
        )


        $sheetNormalized = (
            $sheetName
            .ToLowerInvariant()
        )


        $keep = (
            $wantedNormalized
            -contains
            $sheetNormalized
        )


        if ($keep) {

            # xlSheetVisible
            $worksheet.Visible = -1

            $keptSheets += $sheetName

        } else {

            # xlSheetHidden
            $worksheet.Visible = 0
        }
    }


    if (
        $keptSheets.Count -eq 0
    ) {

        throw (
            "No se encontró ninguna hoja "
            + "para exportar."
        )
    }


    $pdfParent = (
        Split-Path `
        -Parent `
        $PdfPath
    )


    if (
        $pdfParent
        -and
        !(Test-Path -LiteralPath $pdfParent)
    ) {

        New-Item `
            -ItemType Directory `
            -Force `
            -Path $pdfParent |
        Out-Null
    }


    if (
        Test-Path -LiteralPath $PdfPath
    ) {

        Remove-Item `
            -LiteralPath $PdfPath `
            -Force
    }


    # 0 = xlTypePDF
    # 0 = calidad estándar
    # IncludeDocProperties = true
    # IgnorePrintAreas = false
    #
    # Esto conserva:
    # - áreas de impresión;
    # - orientación;
    # - escala;
    # - márgenes;
    # - saltos de página;
    # - logos;
    # - bordes;
    # - colores;
    # - encabezados.
    $workbook.ExportAsFixedFormat(
        0,
        $PdfPath,
        0,
        $true,
        $false
    )


    if (
        !(Test-Path -LiteralPath $PdfPath)
    ) {

        throw (
            "Excel terminó sin crear "
            + "el archivo PDF."
        )
    }


    $pdfInfo = (
        Get-Item `
        -LiteralPath $PdfPath
    )


    if (
        $pdfInfo.Length -lt 5000
    ) {

        throw (
            "El PDF creado parece vacío "
            + "o incompleto."
        )
    }


    Write-Output (
        "PDF_OK="
        + $PdfPath
    )


    Write-Output (
        "SHEETS="
        + (
            $keptSheets
            -join " | "
        )
    )


    $workbook.Close(
        $false
    )


    $workbook = $null


    $excel.Quit()


    $excel = $null

}
catch {

    Write-Error $_

    exit 1

}
finally {

    if (
        $workbook -ne $null
    ) {

        try {

            $workbook.Close(
                $false
            )

        } catch {

        }
    }


    if (
        $excel -ne $null
    ) {

        try {

            $excel.Quit()

        } catch {

        }
    }


    try {

        [System.GC]::Collect()

        [System.GC]::
            WaitForPendingFinalizers()

    } catch {

    }
}
