Option Explicit

Dim args
Dim excelPath
Dim pdfPath
Dim fso
Dim workbook
Dim excelApp
Dim errorMessage

Set workbook = Nothing
Set excelApp = Nothing

Set args = WScript.Arguments

If args.Count < 2 Then
    WScript.Echo "ERROR=Missing arguments"
    WScript.Quit 2
End If

excelPath = args.Item(0)
pdfPath = args.Item(1)

Set fso = CreateObject("Scripting.FileSystemObject")

If Not fso.FileExists(excelPath) Then
    WScript.Echo "ERROR=The Excel file does not exist."
    WScript.Quit 1
End If


Sub Cleanup()

    On Error Resume Next

    If Not workbook Is Nothing Then
        workbook.Close False
    End If

    If Not excelApp Is Nothing Then

        If excelApp.Workbooks.Count = 0 Then
            excelApp.Quit
        End If

    End If

    Set workbook = Nothing
    Set excelApp = Nothing

    On Error GoTo 0

End Sub


Sub Fail(message)

    Cleanup

    WScript.Echo "ERROR=" & message

    WScript.Quit 1

End Sub


On Error Resume Next

Err.Clear

Set workbook = GetObject(excelPath)

If Err.Number <> 0 Then

    errorMessage = Err.Description

    Err.Clear

    Fail "Excel could not open the workbook with GetObject. " & errorMessage

End If


If workbook Is Nothing Then

    Fail "Excel returned an empty workbook."

End If


Set excelApp = workbook.Application

If excelApp Is Nothing Then

    Fail "Excel opened the workbook but did not expose the application."

End If


excelApp.Visible = False

excelApp.DisplayAlerts = False

excelApp.ScreenUpdating = False

excelApp.EnableEvents = False


Err.Clear

excelApp.CalculateFullRebuild

Err.Clear


workbook.ExportAsFixedFormat 0, pdfPath, 0, True, False


If Err.Number <> 0 Then

    errorMessage = Err.Description

    Err.Clear

    Fail "Excel opened the workbook but could not export the PDF. " & errorMessage

End If


If Not fso.FileExists(pdfPath) Then

    Fail "Excel finished without creating the PDF."

End If


Cleanup


WScript.Echo "PDF_OK=" & pdfPath

WScript.Quit 0