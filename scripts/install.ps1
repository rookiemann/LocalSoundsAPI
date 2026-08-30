[CmdletBinding()]
param(
    [switch] $Force,
    [switch] $NoLaunch,
    [switch] $KeepDownloads,
    [switch] $DryRun
)

Set-StrictMode -Version 2.0
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$cacheRoot = Join-Path $repoRoot ".install-cache"
$releasesApiUrl = "https://api.github.com/repos/aivrar/LocalSoundsAPI/releases?per_page=20"
$pythonAssetName = "portable-python-env-v1.7z"
$toolsAssetName = "bin.zip"

# 7zr is only a bootstrap extractor. It is downloaded from the official
# 7-Zip GitHub release and checked against a pinned SHA-256 before it is run.
$sevenZipUrl = "https://github.com/ip7z/7zip/releases/download/26.02/7zr.exe"
$sevenZipSha256 = "56b8cc9f4971cef253644fafe54063ed7fdca551d4dee0f8c6baa81b855acd72"

function Write-Heading {
    param([string] $Text)

    Write-Host ""
    Write-Host "============================================================" -ForegroundColor Cyan
    Write-Host "  $Text" -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor Cyan
}

function Write-Step {
    param([string] $Text)

    Write-Host ""
    Write-Host "-- $Text" -ForegroundColor Yellow
}

function Test-PythonEnvironment {
    $pythonExe = Join-Path $repoRoot "python\python.exe"
    if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
        return $false
    }

    try {
        & $pythonExe -c "import sys, tkinter; assert sys.version_info[:2] == (3, 11)" 2>$null
        return ($LASTEXITCODE -eq 0)
    }
    catch {
        return $false
    }
}

function Test-PortableTools {
    $requiredPaths = @(
        (Join-Path $repoRoot "bin\ffmpeg\bin\ffmpeg.exe"),
        (Join-Path $repoRoot "bin\rubberband\rubberband.exe"),
        (Join-Path $repoRoot "bin\espeak-ng\libespeak-ng.dll")
    )

    foreach ($path in $requiredPaths) {
        if (-not (Test-Path -LiteralPath $path)) {
            return $false
        }
    }
    return $true
}

function Get-AssetDigest {
    param($Asset)

    $digestProperty = $Asset.PSObject.Properties["digest"]
    if ($null -eq $digestProperty -or [string]::IsNullOrWhiteSpace([string] $digestProperty.Value)) {
        throw "GitHub did not publish a SHA-256 digest for $($Asset.name); refusing an unverified dependency download."
    }

    $digest = [string] $digestProperty.Value
    if (-not $digest.StartsWith("sha256:", [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "GitHub supplied an unsupported digest for $($Asset.name): $digest"
    }
    return $digest.Substring(7).ToLowerInvariant()
}

function Get-ReleaseAsset {
    param(
        $Release,
        [string] $Name
    )

    $matches = @($Release.assets | Where-Object { $_.name -eq $Name })
    if ($matches.Count -ne 1) {
        throw "Release '$($Release.tag_name)' does not contain the required asset '$Name'. Check https://github.com/aivrar/LocalSoundsAPI/releases"
    }

    $asset = $matches[0]
    $uri = [System.Uri] $asset.browser_download_url
    $expectedPrefix = "/aivrar/LocalSoundsAPI/releases/download/"
    if ($uri.Scheme -ne "https" -or
        $uri.Host -ne "github.com" -or
        -not $uri.AbsolutePath.StartsWith($expectedPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing an unexpected download URL for '$Name': $uri"
    }

    return $asset
}

function Get-CompatibleDependencyRelease {
    param($Releases)

    foreach ($release in @($Releases)) {
        if ($release.draft) {
            continue
        }

        $assetNames = @($release.assets | ForEach-Object { $_.name })
        if ($assetNames -contains $pythonAssetName -and $assetNames -contains $toolsAssetName) {
            return $release
        }
    }

    throw "No published LocalSoundsAPI release contains both '$pythonAssetName' and '$toolsAssetName'. Check https://github.com/aivrar/LocalSoundsAPI/releases"
}

function Test-FileHash {
    param(
        [string] $Path,
        [string] $ExpectedSha256
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        return $false
    }
    if ([string]::IsNullOrWhiteSpace($ExpectedSha256)) {
        return $true
    }

    $actual = (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
    return ($actual -eq $ExpectedSha256.ToLowerInvariant())
}

function Remove-CacheFile {
    param([string] $Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        return
    }

    $fullPath = [System.IO.Path]::GetFullPath($Path)
    $safePrefix = [System.IO.Path]::GetFullPath($cacheRoot).TrimEnd("\") + "\"
    if (-not $fullPath.StartsWith($safePrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove a file outside the installer cache: $fullPath"
    }
    Remove-Item -LiteralPath $fullPath -Force
}

function Invoke-Download {
    param(
        [string] $Url,
        [string] $Destination,
        [string] $ExpectedSha256,
        [string] $DisplayName
    )

    if (Test-FileHash -Path $Destination -ExpectedSha256 $ExpectedSha256) {
        Write-Host "Using the verified cached download: $DisplayName" -ForegroundColor Green
        return
    }

    if (Test-Path -LiteralPath $Destination) {
        Write-Warning "The cached $DisplayName failed verification and will be downloaded again."
        Remove-CacheFile -Path $Destination
    }

    $partialPath = "$Destination.part"
    $curl = Get-Command "curl.exe" -ErrorAction SilentlyContinue
    if ($null -ne $curl) {
        $resume = Test-Path -LiteralPath $partialPath -PathType Leaf
        if ($resume) {
            Write-Host "Resuming $DisplayName..."
        }
        else {
            Write-Host "Downloading $DisplayName..."
        }

        $arguments = @(
            "--location",
            "--fail",
            "--retry", "5",
            "--retry-delay", "3",
            "--connect-timeout", "30",
            "--output", $partialPath
        )
        if ($resume) {
            $arguments += @("--continue-at", "-")
        }
        $arguments += $Url

        & $curl.Source @arguments
        $curlExitCode = $LASTEXITCODE

        # A stale partial file can make a resume fail. Retry once from zero.
        if ($curlExitCode -ne 0 -and $resume) {
            Write-Warning "The old partial download could not be resumed. Retrying it from the beginning."
            Remove-CacheFile -Path $partialPath
            $arguments = @(
                "--location",
                "--fail",
                "--retry", "5",
                "--retry-delay", "3",
                "--connect-timeout", "30",
                "--output", $partialPath,
                $Url
            )
            & $curl.Source @arguments
            $curlExitCode = $LASTEXITCODE
        }

        if ($curlExitCode -ne 0) {
            throw "$DisplayName download failed (curl exit code $curlExitCode). Run install.bat again to retry."
        }
    }
    else {
        Write-Host "Downloading $DisplayName with Windows PowerShell..."
        Invoke-WebRequest -UseBasicParsing -Uri $Url -OutFile $partialPath
    }

    Move-Item -LiteralPath $partialPath -Destination $Destination -Force

    Write-Host "Verifying $DisplayName..."
    if (-not (Test-FileHash -Path $Destination -ExpectedSha256 $ExpectedSha256)) {
        Remove-CacheFile -Path $Destination
        throw "$DisplayName failed its SHA-256 check. The bad download was removed; run install.bat to retry."
    }
    Write-Host "$DisplayName verified." -ForegroundColor Green
}

function Install-PythonEnvironment {
    param($Asset)

    $archivePath = Join-Path $cacheRoot $pythonAssetName
    $expectedHash = Get-AssetDigest -Asset $Asset

    Invoke-Download -Url $Asset.browser_download_url -Destination $archivePath -ExpectedSha256 $expectedHash -DisplayName $pythonAssetName

    $sevenZipPath = Join-Path $cacheRoot "7zr.exe"
    Invoke-Download -Url $sevenZipUrl -Destination $sevenZipPath -ExpectedSha256 $sevenZipSha256 -DisplayName "7-Zip extractor"

    Write-Host "Extracting the portable Python environment. This can take several minutes..."
    & $sevenZipPath "x" "-y" "-o$repoRoot" $archivePath
    if ($LASTEXITCODE -ne 0) {
        throw "7-Zip could not extract $pythonAssetName (exit code $LASTEXITCODE)."
    }

    if (-not (Test-PythonEnvironment)) {
        throw "Python extraction finished, but python\python.exe did not pass its startup check."
    }

    if (-not $KeepDownloads) {
        Remove-CacheFile -Path $archivePath
        Remove-CacheFile -Path $sevenZipPath
    }
    Write-Host "Portable Python is installed." -ForegroundColor Green
}

function Install-PortableTools {
    param($Asset)

    $archivePath = Join-Path $cacheRoot $toolsAssetName
    $expectedHash = Get-AssetDigest -Asset $Asset

    Invoke-Download -Url $Asset.browser_download_url -Destination $archivePath -ExpectedSha256 $expectedHash -DisplayName $toolsAssetName

    Write-Host "Extracting FFmpeg, RubberBand, and eSpeak-ng..."
    Expand-Archive -LiteralPath $archivePath -DestinationPath $repoRoot -Force

    if (-not (Test-PortableTools)) {
        throw "Tool extraction finished, but one or more required files are missing from bin\."
    }

    if (-not $KeepDownloads) {
        Remove-CacheFile -Path $archivePath
    }
    Write-Host "Portable audio tools are installed." -ForegroundColor Green
}

try {
    Write-Heading "LocalSoundsAPI - One-Click Setup"
    Write-Host "Project folder: $repoRoot"
    Write-Host "No administrator rights or system Python installation are needed."

    if (-not [Environment]::Is64BitOperatingSystem) {
        throw "LocalSoundsAPI requires 64-bit Windows."
    }

    $pythonReady = Test-PythonEnvironment
    $toolsReady = Test-PortableTools

    Write-Step "Checking the current installation"
    if ($pythonReady) {
        Write-Host "Portable Python: ready" -ForegroundColor Green
    }
    else {
        Write-Host "Portable Python: missing or incomplete" -ForegroundColor DarkYellow
    }
    if ($toolsReady) {
        Write-Host "Portable tools:  ready" -ForegroundColor Green
    }
    else {
        Write-Host "Portable tools:  missing or incomplete" -ForegroundColor DarkYellow
    }

    if ($Force) {
        Write-Host "Force mode: both required release assets will be reinstalled."
        $pythonReady = $false
        $toolsReady = $false
    }

    if (-not $pythonReady -or -not $toolsReady) {
        Write-Step "Finding a compatible LocalSoundsAPI dependency bundle"
        [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
        $headers = @{
            "Accept" = "application/vnd.github+json"
            "User-Agent" = "LocalSoundsAPI-one-click-installer"
            "X-GitHub-Api-Version" = "2022-11-28"
        }
        # Do not wrap Invoke-RestMethod in @(...). Windows PowerShell 5.1 treats
        # its JSON array as one nested array when an array subexpression is used.
        $releases = Invoke-RestMethod -UseBasicParsing -Headers $headers -Uri $releasesApiUrl
        $release = Get-CompatibleDependencyRelease -Releases $releases
        Write-Host "Dependency bundle release: $($release.tag_name)"

        $pythonAsset = $null
        $toolsAsset = $null
        if (-not $pythonReady) {
            $pythonAsset = Get-ReleaseAsset -Release $release -Name $pythonAssetName
            $null = Get-AssetDigest -Asset $pythonAsset
            Write-Host ("Python environment: {0:N2} GB" -f ($pythonAsset.size / 1GB))
        }
        if (-not $toolsReady) {
            $toolsAsset = Get-ReleaseAsset -Release $release -Name $toolsAssetName
            $null = Get-AssetDigest -Asset $toolsAsset
            Write-Host ("Portable tools:    {0:N0} MB" -f ($toolsAsset.size / 1MB))
        }

        if ($DryRun) {
            Write-Host ""
            Write-Host "Dry run complete; no files were downloaded or extracted." -ForegroundColor Green
            exit 0
        }

        if (-not (Test-Path -LiteralPath $cacheRoot -PathType Container)) {
            New-Item -ItemType Directory -Path $cacheRoot | Out-Null
        }

        if (-not $pythonReady) {
            Write-Step "Installing the portable Python environment"
            Install-PythonEnvironment -Asset $pythonAsset
        }
        if (-not $toolsReady) {
            Write-Step "Installing the portable audio tools"
            Install-PortableTools -Asset $toolsAsset
        }
    }
    elseif ($DryRun) {
        Write-Host ""
        Write-Host "Dry run complete; everything is already installed." -ForegroundColor Green
        exit 0
    }

    Write-Step "Final verification"
    if (-not (Test-PythonEnvironment)) {
        throw "Portable Python is not ready after installation."
    }
    if (-not (Test-PortableTools)) {
        throw "Portable audio tools are not ready after installation."
    }

    Write-Host ""
    Write-Host "LocalSoundsAPI setup is complete." -ForegroundColor Green
    Write-Host "AI models are optional and download on demand from the launcher's Models & Tools tab."

    if (-not $NoLaunch) {
        Write-Host "Opening the LocalSoundsAPI launcher..."
        $launcherPath = Join-Path $repoRoot "launcher.bat"
        $cmdArguments = @("/d", "/s", "/c", ('""{0}""' -f $launcherPath))
        Start-Process -FilePath $env:ComSpec -ArgumentList $cmdArguments -WorkingDirectory $repoRoot
    }

    exit 0
}
catch {
    Write-Host ""
    Write-Host "SETUP ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "You can safely run install.bat again. Completed downloads are reused, and partial curl downloads are resumed."
    exit 1
}
