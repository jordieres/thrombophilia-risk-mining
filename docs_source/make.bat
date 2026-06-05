@ECHO OFF
set SPHINXBUILD=sphinx-build
set SOURCEDIR=.
set BUILDDIR=..\docs
set DOCTREEDIR=.doctrees

if "%1"=="clean" (
  rmdir /s /q %DOCTREEDIR%
  rmdir /s /q %BUILDDIR%
  goto end
)

%SPHINXBUILD% -d %DOCTREEDIR% -b html %SOURCEDIR% %BUILDDIR%

:end
