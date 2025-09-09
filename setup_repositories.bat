@echo off
echo ========================================
echo Setting up Full and Part repositories
echo ========================================

cd C:\reflex

echo.
echo [1/4] Creating Full version directory...
if exist reflex-cps-full rmdir /s /q reflex-cps-full
mkdir reflex-cps-full
cd reflex-cps-full
git init
git remote add origin https://github.com/grandbelly/reflex-cps-full.git

echo.
echo [2/4] Copying Full version files...
xcopy /E /I /Y ..\reflex-ksys-refactor\* . /EXCLUDE:..\reflex-ksys-refactor\exclude_full.txt
copy ..\reflex-ksys-refactor\.gitignore .
copy ..\reflex-ksys-refactor\.env .

echo.
echo [3/4] Creating Part version directory...
cd C:\reflex
if exist reflex-ksys-lite rmdir /s /q reflex-ksys-lite
mkdir reflex-ksys-lite
cd reflex-ksys-lite
git init
git remote add origin https://github.com/grandbelly/reflex-ksys-lite.git

echo.
echo [4/4] Copying Part version files (excluding AI/ML)...
xcopy /E /I /Y ..\reflex-ksys-refactor\* . /EXCLUDE:..\reflex-ksys-refactor\exclude_part.txt
copy ..\reflex-ksys-refactor\.gitignore .
copy ..\reflex-ksys-refactor\.env .

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Next steps:
echo 1. cd reflex-cps-full && git add . && git commit -m "Initial commit" && git push -u origin main
echo 2. cd reflex-ksys-lite && git add . && git commit -m "Initial commit" && git push -u origin main