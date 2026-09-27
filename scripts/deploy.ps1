[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $ProjectRoot
try {
    $CurrentBranch = (git rev-parse --abbrev-ref HEAD).Trim()
    if ($CurrentBranch -ne 'main') {
        throw "Deploy refuzat: branch-ul curent este '$CurrentBranch', nu 'main'."
    }

    $StatusOutput = git status --porcelain
    if ($StatusOutput) {
        throw 'Deploy refuzat: există modificări necommise sau fișiere netracked.'
    }

    git fetch origin main | Out-Null
    $LocalSha = (git rev-parse HEAD).Trim()
    $RemoteSha = (git rev-parse origin/main).Trim()
    if ($LocalSha -ne $RemoteSha) {
        throw "Deploy refuzat: HEAD ($LocalSha) diferă de origin/main ($RemoteSha)."
    }

    python -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw 'Deploy refuzat: testele au eșuat.'
    }

    railway up --detach
    if ($LASTEXITCODE -ne 0) {
        throw 'Deploy eșuat: railway up --detach a returnat o eroare.'
    }

    Write-Output "Deploy pornit pentru commit-ul $LocalSha."
}
finally {
    Pop-Location
}
