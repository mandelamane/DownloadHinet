# dlhinet 
version: 1.0.0
検測ファイルに記載されている時間（Jで始まる列の2列目から17列目）と一致するイベントファイルをダウンロードすることができる。

# config.iniの書き方

[ACCOUNT]
（必須）UserName: hinetのユーザー名
（必須）Password: hinetのパスワード

[SETTING]
（必須）DownloadMode: イベント波形のみのダウンロードの場合は"event"、検測ファイルのみのダウンロード場合は"kensoku"、ともにダウンロードする場合は"both"と記述
（eventモードのとき必須）EventList: 頭文字がJで始めるイベントの発生時間が記載されたファイルのパス
（eventモードのとき必須）EventFileSaveDir: イベントファイルを保存するディレクトリ、新規作成されるため事前に作っておく必要はない
（kensokuモードのとき必須）KensokuSaveDir: 検測ファイルを保存するディレクトリ、新規作成されるため事前に作っておく必要はない

[KENSOKUFILE_DATE]
（kensokuモードのとき必須）T1: ダウンロードしたい検測ファイルの開始日時
（kensokuモードのとき必須）T2: ダウンロードしたい検測ファイルの終了日時

## 使い方
1. config.iniの中身を任意の値に変更
2. ターミナル上で ./dlhinet を実行

## バイナリの作り方
1. python3をインストール
2. pip3 install -r requirements.txtをターミナルで実行
3. srcディレクトリに移動
4. pyinstaller dlhinet.py --onefileをターミナルで実行
3. distと書かれたディレクトリにバイナリが生成