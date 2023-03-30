import configparser
import os
import random
import re
import shutil
import sys
import time
import zipfile
from datetime import datetime, timedelta

import bs4
import requests

LINE = 80


class ReadConfig:
    def __init__(self):
        self.config_p = configparser.ConfigParser()
        self.timeout = None
        self.time_sleep = 20

    def reading_config_file(self):
        self.setting_file = "./config.ini"

        if os.path.exists(self.setting_file):
            self.config_p.read(self.setting_file, encoding="utf-8")
            try:
                self.user_name = self.config_p["ACCOUNT"]["UserName"]
                self.password = self.config_p["ACCOUNT"]["Password"]
                self.download_mode = self.config_p["SETTING"]["DownloadMode"]
                self.event_list = self.config_p["SETTING"]["EventList"]
                self.save_dir = self.config_p["SETTING"]["EventFileSaveDir"]
                self.kensoku_dir = self.config_p["SETTING"]["KensokuSaveDir"]
                self.start_time = self.config_p["KENSOKUFILE_DATE"]["T1"]
                self.end_time = self.config_p["KENSOKUFILE_DATE"]["T2"]
            except Exception as e:
                print(e)
                print("設定ファイル config.ini に間違いが存在します。")
                print("#" * 80)
                sys.exit()
        else:
            print("設定ファイル config.ini が存在しません。")
            print("#" * 80)
            sys.exit()


class HinetWebLogin(ReadConfig):
    def __init__(self):
        super().__init__()
        self.reading_config_file()

        self.session = requests.session()

        self.account = {
            "auth_un": str(self.user_name),
            "auth_pw": str(self.password),
        }

    def login_website(self):
        login_page_url = "https://hinetwww11.bosai.go.jp/auth/?LANG=ja"
        user_name = self.account["auth_un"]

        res_cookie = self.session.get(
            login_page_url, timeout=self.timeout
        ).cookies
        res_login = self.session.post(
            login_page_url,
            data=self.account,
            cookies=res_cookie,
            timeout=self.timeout,
        )

        if self.check_login(res_login):
            print(f"ようこそ {user_name} 様")
            print("-" * LINE)
        else:
            print("ユーザー名またはパスワードが違います。もう一度ログインしてください。")
            print("#" * LINE)
            sys.exit()

    def check_login(self, res: requests.models.Response):
        soup = bs4.BeautifulSoup(res.text, "html.parser")
        # 正しくログインできていた場合id="welcome"が存在する。
        if len(soup.find_all(id="welcome")) == 1:
            return True
        else:
            return False


class DownloadKensokuData(HinetWebLogin):
    def __init__(self):
        super().__init__()

    def create_kensoku_dir(self):
        if not os.path.exists(self.kensoku_dir):
            os.makedirs(self.kensoku_dir)
            print(f"検測ファイルを保存するディレクトリ {self.kensoku_dir} を作成しました。")

    def create_rtm_list(self):
        self.rtm_list = []

        self.check_end_time_v1()
        d_start = datetime.strptime(self.start_time, "%Y%m%d")
        d_end = datetime.strptime(self.end_time, "%Y%m%d")
        rtm_days = (d_end - d_start).days

        if rtm_days >= 7:
            res_days = rtm_days % 7
            # 一週間単位の日にちに変換
            week_days = rtm_days - res_days
            secondly_d_start = d_start + timedelta(week_days)
            for num in range(0, week_days):
                if num % 7 == 0:
                    self.rtm_list.append(
                        [
                            "7",
                            datetime.strftime(
                                d_start + timedelta(num), "%Y%m%d"
                            ),
                        ]
                    )
            self.rtm_list.append(
                [
                    str(res_days + 1),
                    datetime.strftime(secondly_d_start, "%Y%m%d"),
                ]
            )
        else:
            self.rtm_list.append(
                [str(rtm_days + 1), datetime.strftime(d_start, "%Y%m%d")]
            )

    def check_end_time_v1(self):
        select_kensoku_page_url = (
            "https://hinetwww11.bosai.go.jp/auth/JMA/?LANG=ja"
        )
        res_page = self.session.get(
            select_kensoku_page_url, timeout=self.timeout
        )

        soup = bs4.BeautifulSoup(res_page.text, "html.parser")
        # 公開されているデータの日付を取得し文字列に変換後、必要な項目を抽出
        end_day = soup.find(
            "li", text=re.compile("検測値データの検索範囲は、*")
        ).get_text()[-14:-4]
        new_end_time = end_day.replace("/", "")

        if self.end_time <= new_end_time:
            print(
                f"ダウンロードする検測ファイルの期間は {self.start_time[:4]}/{self.start_time[4:6]}/{self.start_time[6:8]} - {self.end_time[:4]}/{self.end_time[4:6]}/{self.end_time[6:8]} です。"
            )
            print("-" * LINE)
        else:
            print(f"検測ファイルは {new_end_time} までしか公開されていません。")
            self.end_time = new_end_time
            print(
                f"ダウンロードする検測ファイルの期間は {self.start_time[:4]}/{self.start_time[4:6]}/{self.start_time[6:8]} - {self.end_time[:4]}/{self.end_time[4:6]}/{self.end_time[6:8]} です。"
            )
            print("-" * LINE)

    def download_kensokufile(self, nday, rtm):
        download_kensokufile_page_url = "https://hinetwww11.bosai.go.jp/auth/JMA/dlDialogue.php?data=measure"

        send_data = {"rtm": rtm, "span": nday, "os": "U"}

        res_dl_data = self.session.get(
            download_kensokufile_page_url,
            params=send_data,
            timeout=self.timeout,
        )

        kensokufile_path = f"{self.kensoku_dir}measure_{rtm}_{nday}.txt"

        with open(kensokufile_path, "wb") as f:
            f.write(res_dl_data.content)

        print(
            f"{rtm[:4]}/{rtm[4:6]}/{rtm[6:8]} から"
            f"{nday}日間の検測ファイルのダウンロードが完了しました。"
        )

    def run_v1(self):
        if (self.download_mode == "kensoku") or (self.download_mode == "both"):
            self.login_website()
            self.create_kensoku_dir()
            self.create_rtm_list()
            print("検測ファイルのダウンロードを開始します。")
            for nday, rtm in self.rtm_list:
                self.download_kensokufile(nday, rtm)
            print("-" * LINE)


class DownloadEventData(HinetWebLogin):
    def __init__(self):
        super().__init__()

    def create_event_dir(self):
        self.tmp_dir = "tmp/"
        if not os.path.exists(self.tmp_dir):
            os.mkdir(self.tmp_dir)
        else:
            shutil.rmtree(self.tmp_dir)
            os.mkdir(self.tmp_dir)

        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            print(f"イベントを保存するディレクトリ {self.save_dir} を作成しました。")

    def check_end_time_v2(self):
        select_event_page_url = (
            "https://hinetwww11.bosai.go.jp/auth/download/event/?LANG=ja"
        )
        res_page = self.session.get(
            select_event_page_url, timeout=self.timeout
        )
        soup = bs4.BeautifulSoup(res_page.text, "html.parser")
        # 公開されているデータの日付を取得し文字列に変換後、必要な項目を抽出
        end_day = (
            soup.find(class_="event_sel")
            .get_text()[30:40]
            .replace(" ", "")
            .replace("で", "")
        )
        split_end_datetime = end_day.split("/")
        new_end_time = f"{split_end_datetime[0]}{split_end_datetime[1].rjust(2, '0')}{split_end_datetime[2].rjust(2, '0')}"

        try:
            with open(self.event_list, "r") as f:
                self.want_event_info_list = [
                    tmp.strip()[1:] for tmp in f.readlines() if tmp[0] == "J"
                ]
        except Exception as e:
            print(e)
            print(f"{self.event_list} が存在しません。")
            print("#" * LINE)
            sys.exit()

        self.start_time = self.want_event_info_list[0][:8]
        self.end_time = self.want_event_info_list[-1][:8]

        if self.end_time <= new_end_time:
            print(
                f"ダウンロードするイベントの期間は {self.start_time[:4]}/{self.start_time[4:6]}/{self.start_time[6:8]} - {self.end_time[:4]}/{self.end_time[4:6]}/{self.end_time[6:8]} です。"
            )
        else:
            print(f"イベント波形は {new_end_time} までしか提供されていません。")
            self.end_time = new_end_time
            self.want_event_info_list = [
                tmp.strip()
                for tmp in self.want_event_info_list
                if tmp[0:8] <= new_end_time
            ]
            print(
                f"ダウンロードするイベントの期間は {self.start_time[:4]}/{self.start_time[4:6]}/{self.start_time[6:8]} - {self.end_time[:4]}/{self.end_time[4:6]}/{self.end_time[6:8]} です。"
            )

        self.event_num = len(self.want_event_info_list)
        all_sec = self.event_num * 30
        run_hour = str(all_sec // 3600).rjust(2, "0")
        run_min = str((all_sec - int(run_hour) * 3600) // 60).rjust(2, "0")
        run_sec = str(
            (all_sec - int(run_hour) * 3600 - int(run_min) * 60)
        ).rjust(2, "0")
        print(f"イベントの総数は、{self.event_num}です。")
        print(
            f"すべてのデータをダウンロードするには、およそ {run_hour}時間 {run_min}分 {run_sec}秒 かかります。"
        )
        print("-" * LINE)

    def search_event(self, event_info):
        self.event_info = event_info

        search_event_page_url = (
            "https://hinetwww11.bosai.go.jp/auth/download/event/?LANG=ja"
        )

        search_event_data = {
            "year": "2002",
            "month": "06",
            "day": "03",
            "region": "00",
            "mags": "-1.0",
            "mage": "9.9",
            "undet": "0",
            "sort": "0",
            "arc": "ZIP",
            "go": "1",
            "LANG": "ja",
        }

        search_event_data["year"] = self.event_info[:4]
        search_event_data["month"] = self.event_info[4:6]
        search_event_data["day"] = self.event_info[6:8]

        self.res_search_results = self.session.post(
            search_event_page_url, data=search_event_data, timeout=self.timeout
        )

        self.create_event_searched_list()

    def create_event_searched_list(self):
        soup = bs4.BeautifulSoup(
            self.res_search_results.content, "html.parser"
        )
        # イベント波形の選択項目のリストを作成
        input_tag_list = soup.find_all("input", onclick=True)[1:]
        self.event_searched_list = [
            str(input_tag.get("onclick"))[12:]
            .replace(")", "")
            .replace("'", "")
            .split(",")
            for input_tag in input_tag_list
        ]

    def requests_event(self):
        requests_event_page_url = "https://hinetwww11.bosai.go.jp/auth/download/event/event_request.php?"

        requests_event_data = {
            "evid": "",
            "arc": "",
            "encoding": "",
            "origin_jst": "",
            "hypo_latitude": "",
            "hypo_logitude": "",
            "hypo_depth": "",
            "mg": "",
            "hypo_name": "",
            "hypo_name_eng": "",
            "LANG": "",
            "rn": "",
        }

        if self.event_info[14:16] == "00":
            self.requests_event_time = (
                self.event_info[0:4]
                + "/"
                + self.event_info[4:6]
                + "/"
                + self.event_info[6:8]
                + " "
                + self.event_info[8:10]
                + ":"
                + self.event_info[10:12]
                + ":"
                + self.event_info[12:14]
                + "."
                + self.event_info[14:15]
            )
        else:
            self.requests_event_time = (
                self.event_info[0:4]
                + "/"
                + self.event_info[4:6]
                + "/"
                + self.event_info[6:8]
                + " "
                + self.event_info[8:10]
                + ":"
                + self.event_info[10:12]
                + ":"
                + self.event_info[12:14]
                + "."
                + self.event_info[14:16]
            )

        self.flag = False
        self.dir_name = ""
        for searched_results in self.event_searched_list:
            if searched_results[3] == self.requests_event_time:
                requests_event_data["evid"] = searched_results[0]
                requests_event_data["arc"] = searched_results[1]
                requests_event_data["encoding"] = searched_results[2]
                requests_event_data["origin_jst"] = searched_results[3]
                requests_event_data["hypo_latitude"] = searched_results[4]
                requests_event_data["hypo_logitude"] = searched_results[5]
                requests_event_data["hypo_depth"] = searched_results[6]
                requests_event_data["mg"] = searched_results[7]
                requests_event_data["hypo_name"] = searched_results[8]
                requests_event_data["hypo_name_eng"] = searched_results[9]
                requests_event_data["LANG"] = searched_results[10]
                requests_event_data["rn"] = str(
                    random.randint(10**13, 10**14 - 1)
                )
                self.dir_name = searched_results[0]
                self.flag = True
                _ = self.session.get(
                    requests_event_page_url,
                    params=requests_event_data,
                    timeout=self.timeout,
                )
                break

    def dowload_event_wave_file(self):
        download_zipfile_page_url = "https://hinetwww11.bosai.go.jp/auth/download/event/event_download.php?"

        if self.flag:
            try:
                time.sleep(self.time_sleep)
                self.get_id()
                self.bin_download_zipfile = self.session.get(
                    download_zipfile_page_url, params=self.dl_zipfile_id_info
                )
                self.save_zipfile_to_dir()
            except requests.exceptions.Timeout:
                self.dowload_event_wave_file()
        else:
            print(
                f"{str(self.i+1)}/{str(self.event_num)}   {self.requests_event_time} のイベント波形は存在しません。次の処理へ移行します。"
            )
            with open("not_event.txt", "a") as f:
                print(f"{self.i+1} {self.event_info}", file=f)

    def get_id(self):
        id_page_url = "https://hinetwww11.bosai.go.jp/auth/download/event/event_status.php?LANG=ja&page=1"

        res_id_page = self.session.get(id_page_url, timeout=self.timeout)
        soup = bs4.BeautifulSoup(res_id_page.content, "html.parser")
        id_n = soup.find_all("td", {"class", "bgevlist2"})[0].get_text()

        self.dl_zipfile_id_info = {"id": "", "encode": "U", "LANG": "ja"}

        self.dl_zipfile_id_info["id"] = id_n

    def save_zipfile_to_dir(self):
        tmp_zip_path = f"{self.tmp_dir}U{self.dir_name}_20.zip"

        with open(tmp_zip_path, "wb") as f:
            f.write(self.bin_download_zipfile.content)

        try:
            with zipfile.ZipFile(tmp_zip_path) as existing_zip:
                existing_zip.extractall(self.save_dir)
                self.finish_time = time.time()
                self.elapsed_time = self.finish_time - self.begin_time
            print(
                f"{str(self.i+1)}/{str(self.event_num)}   {self.requests_event_time} のイベント波形をダウンロードしました。 {int(self.elapsed_time)} [sec]"
            )
        except zipfile.BadZipFile:  # ダウンロードが上手く言っていなかったときの対策
            if self.download_false <= 2:
                print(
                    f"{str(self.i+1)}/{str(self.event_num)}   {self.requests_event_time} のデータのダウンロードに失敗しました。もう一度ダウンロードを行います。"
                )
                self.download_false += 1
                self.requests_event()
                time.sleep(self.time_sleep + 5)
                self.dowload_event_wave_file()
            else:
                self.finish_time = time.time()
                self.elapsed_time = self.finish_time - self.begin_time
                print(
                    f"{str(self.i+1)}/{str(self.event_num)}   {self.requests_event_time} のデータのダウンロードに失敗しました。次の処理へ移行します。 {self.elapsed_time:.2e} [sec]"
                )
                with open("failed_download.txt", "a") as f:
                    print(f"{self.i+1} {self.event_info}", file=f)

    def run_v2(self):
        if (self.download_mode == "event") or (self.download_mode == "both"):
            self.login_website()
            random.seed(0)
            self.create_event_dir()
            self.check_end_time_v2()

            print("イベント波形のダウンロードを開始します。")
            for self.i, event_info in enumerate(self.want_event_info_list):
                self.begin_time = time.time()
                self.download_false = 0
                self.search_event(event_info)
                self.requests_event()
                self.dowload_event_wave_file()
            shutil.rmtree(self.tmp_dir)
            print("-" * LINE)


def main():
    print("#" * LINE)
    dl_kensoku_data = DownloadKensokuData()
    dl_kensoku_data.run_v1()
    dl_event_data = DownloadEventData()
    dl_event_data.run_v2()
    print("全ての処理が完了しました。")
    print("#" * LINE)


if __name__ == "__main__":
    main()
