param(
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
