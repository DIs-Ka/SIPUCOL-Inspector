param(
    [Parameter(Mandatory = $true)]
    [string]$ExcelPath,

    [Parameter(Mandatory = $true)]
    [string]$PdfPath
)

$ErrorActionPreference = "Stop"

$excel = $null
$workbooks = $null
$workbook = $null
$tempFolder = $null


function Release-ComObject {
    param(
        [object]$ComObject
    )

    if ($null -eq $ComObject) {
        return
    }

    try {
        [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject(
            $ComObject
        )
    }
    catch {
    }
}


try {

    # -----------------------------------------------------
    # VALIDAR EXCEL DE ORIGEN
    # -----------------------------------------------------

    $exists = Test-Path -LiteralPath $ExcelPath -PathType Leaf

    if (-not $exists) {
        throw "The selected Excel file does not exist: $ExcelPath"
    }

    $sourcePath = (Resolve-Path -LiteralPath $ExcelPath).Path

    $extension = [System.IO.Path]::GetExtension(
        $sourcePath
    ).ToLowerInvariant()

    $allowedExtensions = @(
        ".xlsm",
        ".xlsx",
        ".xls",
        ".xlsb"
    )

    if ($allowedExtensions -notcontains $extension) {
        throw "Unsupported Excel file extension: $extension"
    }


    # -----------------------------------------------------
    # PREPARAR DESTINO PDF
    # -----------------------------------------------------

    $pdfFullPath = [System.IO.Path]::GetFullPath(
        $PdfPath
    )

    $pdfFolder = [System.IO.Path]::GetDirectoryName(
        $pdfFullPath
    )

    if (-not [string]::IsNullOrWhiteSpace($pdfFolder)) {
        [System.IO.Directory]::CreateDirectory(
            $pdfFolder
        ) | Out-Null
    }

    $pdfAlreadyExists = Test-Path -LiteralPath $pdfFullPath

    if ($pdfAlreadyExists) {
        Remove-Item -LiteralPath $pdfFullPath -Force
    }


    # -----------------------------------------------------
    # COPIAR FUERA DE ONEDRIVE
    # -----------------------------------------------------

    $temporaryName = "SIPUCOL_PDF_" + [System.Guid]::NewGuid().ToString("N")

    $tempFolder = Join-Path $env:TEMP $temporaryName

    [System.IO.Directory]::CreateDirectory(
        $tempFolder
    ) | Out-Null

    $tempExcelPath = Join-Path `
        $tempFolder `
        ("source" + $extension)

    Write-Output "Copying workbook to local temporary storage..."

    Copy-Item `
        -LiteralPath $sourcePath `
        -Destination $tempExcelPath `
        -Force

    try {
        Unblock-File `
            -LiteralPath $tempExcelPath `
            -ErrorAction SilentlyContinue
    }
    catch {
    }


    # -----------------------------------------------------
    # ABRIR MICROSOFT EXCEL
    # -----------------------------------------------------

    Write-Output "Starting Microsoft Excel..."

    $excel = New-Object -ComObject Excel.Application

    if ($null -eq $excel) {
        throw "Microsoft Excel could not be started."
    }

    $excel.Visible = $false
    $excel.DisplayAlerts = $false
    $excel.ScreenUpdating = $false
    $excel.EnableEvents = $false

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


    # -----------------------------------------------------
    # ABRIR LIBRO
    # -----------------------------------------------------

    Write-Output "Opening workbook..."

    $workbooks = $excel.Workbooks

    if ($null -eq $workbooks) {
        throw "Excel did not expose its Workbooks collection."
    }

    try {

        $workbook = $workbooks.Open(
            $tempExcelPath,
            0,
            $false
        )

    }
    catch {

        Write-Output "First opening method failed. Trying simple mode..."

        try {

            $workbook = $workbooks.Open(
                $tempExcelPath
            )

        }
        catch {

            throw (
                "Microsoft Excel could not open the workbook. "
                + $_.Exception.Message
            )
        }
    }

    if ($null -eq $workbook) {
        throw "Excel returned an empty workbook reference."
    }


    # -----------------------------------------------------
    # RECALCULAR
    # -----------------------------------------------------

    Write-Output "Recalculating workbook..."

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

    Start-Sleep -Milliseconds 1000


    # -----------------------------------------------------
    # EXPORTAR PDF NATIVO
    # -----------------------------------------------------

    Write-Output "Exporting PDF with Microsoft Excel..."

    $workbook.ExportAsFixedFormat(
        0,
        $pdfFullPath,
        0,
        $true,
        $false
    )


    # -----------------------------------------------------
    # VALIDAR RESULTADO
    # -----------------------------------------------------

    $pdfWasCreated = Test-Path -LiteralPath $pdfFullPath -PathType Leaf

    if (-not $pdfWasCreated) {
        throw "Excel finished without creating the PDF."
    }

    $pdfInfo = Get-Item -LiteralPath $pdfFullPath

    if ($pdfInfo.Length -lt 5000) {
        throw "The generated PDF is empty or incomplete."
    }

    Write-Output "PDF_OK=$pdfFullPath"
    Write-Output "PDF_SIZE=$($pdfInfo.Length)"
}
catch {

    [Console]::Error.WriteLine(
        $_.Exception.Message
    )

    exit 1
}
finally {

    if ($null -ne $workbook) {

        try {
            $workbook.Close(
                $false
            )
        }
        catch {
        }

        Release-ComObject `
            -ComObject $workbook

        $workbook = $null
    }

    if ($null -ne $workbooks) {

        Release-ComObject `
            -ComObject $workbooks

        $workbooks = $null
    }

    if ($null -ne $excel) {

        try {
            $excel.Quit()
        }
        catch {
        }

        Release-ComObject `
            -ComObject $excel

        $excel = $null
    }

    [System.GC]::Collect()

    [System.GC]::WaitForPendingFinalizers()

    if (
        $null -ne $tempFolder
    ) {

        $tempExists = Test-Path -LiteralPath $tempFolder

        if ($tempExists) {

            try {

                Remove-Item `
                    -LiteralPath $tempFolder `
                    -Recurse `
                    -Force

            }
            catch {
            }
        }
    }
}
