@echo off
chcp 65001 > nul
echo.
echo app_simulator_full.py を G:\マイドライブ\rescue_app にコピーします。
echo.

if not exist "G:\マイドライブ\rescue_app" (
  echo エラー: G:\マイドライブ\rescue_app が見つかりません。
  echo フォルダの場所を確認してください。
  pause
  exit /b 1
)

copy /Y "%~dp0app_simulator_full.py" "G:\マイドライブ\rescue_app\app_simulator_full.py"

echo.
echo コピー完了。
echo 次のコマンドで確認できます:
echo findstr /N /C:"ROGER_LEVEL_PLAYER_2026_05_13" "G:\マイドライブ\rescue_app\app_simulator_full.py"
echo.
pause
