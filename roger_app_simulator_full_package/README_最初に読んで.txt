このZIPには以下が入っています。

1. app_simulator_full.py
   - rescue_app フォルダに上書きする本体コードです。

2. copy_to_rescue_app.bat
   - ダブルクリックすると、app_simulator_full.py を
     G:\マイドライブ\rescue_app\app_simulator_full.py
     にコピーします。

使い方:
1. ZIPをダウンロード
2. ZIPを右クリック → すべて展開
3. 展開したフォルダ内の copy_to_rescue_app.bat をダブルクリック
4. cmdで以下を実行
   cd G:\マイドライブ\rescue_app
   py -m streamlit run app_simulator_full.py --server.port 8530

確認:
以下のコマンドで文字が出れば新コードが入っています。

findstr /N /C:"ROGER_LEVEL_PLAYER_2026_05_13" app_simulator_full.py
findstr /N /C:"def screen_login" app_simulator_full.py
