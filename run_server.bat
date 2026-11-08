@echo off
chcp 65001 > nul
title 에듀워드 끝말잇기 게임 서버
cd /d "%~dp0"

echo ======================================================================
echo    🌿 에듀워드 : 실시간 반별 소켓 끝말잇기 게임 서버 (FastAPI + WebSocket)
echo ======================================================================
echo.

:: 1. Python 명령어 확인
set "PYTHON_CMD=python"
python --version >nul 2>&1
if %errorlevel% neq 0 (
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_CMD=py"
    ) else (
        echo [!] Python이 설치되어 있지 않거나 환경 변수(PATH)에 등록되어 있지 않습니다.
        echo     https://www.python.org 에서 Python을 설치(Add to PATH 체크)해 주세요.
        pause
        exit /b 1
    )
)

:: 2. 필수 패키지 확인 및 자동 설치
echo [1/3] 필수 라이브러리 검사 중...
%PYTHON_CMD% -c "import fastapi, uvicorn, websockets, httpx, dotenv" >nul 2>&1
if %errorlevel% neq 0 (
    echo [!] 필수 패키지가 부족합니다. 자동으로 설치를 진행합니다...
    %PYTHON_CMD% -m pip install fastapi uvicorn websockets httpx python-dotenv
    if %errorlevel% neq 0 (
        echo [오류] 패키지 설치에 실패했습니다. 인터넷 연결을 확인하세요.
        pause
        exit /b 1
    )
)
echo      -> 라이브러리 준비 완료!

:: 3. 내 컴퓨터 IP 주소 확인 및 안내
echo.
echo [2/3] 접속 주소 안내:
echo   - [교사 컴퓨터 브라우저] : http://localhost:8000
echo   - [학생 기기 접속 주소] (같은 와이파이에 연결된 스마트폰/태블릿):
for /f "tokens=2 delims=:" %%i in ('ipconfig ^| findstr /c:"IPv4"') do (
    echo       http:%%i:8000
)

echo.
echo [3/3] 서버를 시작합니다... (종료하려면 창을 닫거나 Ctrl+C를 누르세요)
echo ======================================================================
echo.

%PYTHON_CMD% server.py
pause


