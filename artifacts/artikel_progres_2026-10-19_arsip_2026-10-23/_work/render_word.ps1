param([string]$articleDir = 'C:\VAEP-Track\docs\artikel_progres_2026-10-19')
$ErrorActionPreference = 'Stop'
$qaDir = Join-Path $articleDir '_qa'
New-Item -ItemType Directory -Path $qaDir -Force | Out-Null
$articleWord = New-Object -ComObject Word.Application
$articleWord.Visible = $false
$articleWord.DisplayAlerts = 0
$articleWord.AutomationSecurity = 3
try {
    foreach ($articleFile in (Get-ChildItem -LiteralPath $articleDir -Filter '*.docx' | Sort-Object Name)) {
        $articleDoc = $null
        try {
            $articleDoc = $articleWord.Documents.Open($articleFile.FullName, $false, $true)
            $articleDoc.Fields.Update() | Out-Null
            $articleDoc.Repaginate()
            $articlePdf = Join-Path $qaDir ($articleFile.BaseName + '.pdf')
            $articleDoc.ExportAsFixedFormat($articlePdf, 17)
            Write-Output ($articleFile.Name + ': ' + $articleDoc.ComputeStatistics(2) + ' pages')
        }
        finally {
            if ($null -ne $articleDoc) { $articleDoc.Close(0); [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($articleDoc) }
        }
    }
}
finally {
    $articleWord.Quit()
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($articleWord)
}
