import flet as ft
import requests
from datetime import datetime
import sqlite3

# エンドポイントURL
AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{}.json"

# エンドポイントから地域データを取得
AREA_JSON = requests.get(AREA_URL).json()

# SQLite3の設定
path = ''
db_name = 'weather.db'

try:
    # DB接続オブジェクトの作成
    conn = sqlite3.connect(path + db_name)

    # SQL(RUBを操作するための言語)を実行するためのカーソルp武ジェクトを取得
    cur = conn.cursor()

    # SQL文の作成
    # エリアを保存するテーブルの作成
    sql = 'CREATE TABLE IF NOT EXISTS area_master (area_code TEXT PRIMARY KEY,area_name TEXT,area_type TEXT);'
    cur.execute(sql)
    sql = 'CREATE TABLE IF NOT EXISTS area_relation (parent_code TEXT,child_code TEXT,PRIMARY KEY (parent_code, child_code),FOREIGN KEY (parent_code) REFERENCES area_master(area_code),FOREIGN KEY (child_code) REFERENCES area_master(area_code));'
    cur.execute(sql)
    # 気象データを保存するテーブルの作成
    # sql = 'CREATE TABLE IF NOT EXISTS forecasts (id INTEGER PRIMARY KEY AUTOINCREMENT, area_code TEXT, forecast_date TEXT, weather TEXT, weather_code TEXT, temp_min INTEGER, temp_max INTEGER, fetched_at TEXT, FOREIGN KEY (area_code) REFERENCES area_master(area_code));'
    sql = 'CREATE TABLE IF NOT EXISTS forecasts (id INTEGER PRIMARY KEY AUTOINCREMENT, area_code TEXT, forecast_date TEXT, weather TEXT, weather_code TEXT, temp_min INTEGER, temp_max INTEGER, fetched_at TEXT, UNIQUE(area_code, forecast_date), FOREIGN KEY (area_code) REFERENCES area_master(area_code));'
    cur.execute(sql)

except sqlite3.Error as e:
    print('エラーが発生しました：', e)

finally:
    # DBへの接続を閉じる
    conn.close()

# すべての地域の天気予報を取得してDBに保存する関数
def fetch_and_save_all_forecasts():
    for office_code, office_data in AREA_JSON["offices"].items():
        try:
            forecast = requests.get(
                FORECAST_URL.format(office_code),
                timeout=10
            ).json()

            if not forecast or "timeSeries" not in forecast[0]:
                print(f"skip: {office_data['name']}")
                continue

            weather_ts = forecast[1]["timeSeries"][0]
            temp_ts = find_temp_timeseries(forecast)

            dates = weather_ts["timeDefines"]
            codes = weather_ts["areas"][0]["weatherCodes"]
            weathers = [weatherDescription.get(c, "不明") for c in codes]

            # --- ① 翌日以降の予報気温 ---
            temps_min, temps_max = [], []
            if temp_ts:
                area = temp_ts["areas"][0]
                temps_min = [int(t) if t not in ("", None) else None for t in area.get("tempsMin", [])]
                temps_max = [int(t) if t not in ("", None) else None for t in area.get("tempsMax", [])]

            # --- ② 当日の実測気温 ---
            today_min, today_max = find_today_temps(forecast)

            # --- ③ 日付ごとに整理して保存 ---
            save_dates = []
            save_codes = []
            save_weathers = []
            save_mins = []
            save_maxs = []

            for i, date in enumerate(dates):
                save_dates.append(date)
                save_codes.append(codes[i])
                save_weathers.append(weathers[i])

                if i == 0:
                    # 当日
                    save_mins.append(today_min)
                    save_maxs.append(today_max)
                else:
                    # 翌日以降
                    save_mins.append(temps_min[i] if i < len(temps_min) else None)
                    save_maxs.append(temps_max[i] if i < len(temps_max) else None)

            save_forecast_to_db(
                office_code,
                save_dates,
                save_codes,
                save_weathers,
                save_mins,
                save_maxs
            )

            print(f"saved: {office_data['name']}")

        except Exception as e:
            print(f"error: {office_code}", e)

# 地域マスターデータをDBに挿入する関数
def insert_area_master():
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    # 地方（centers）
    for code, data in AREA_JSON["centers"].items():
        cur.execute(
            '''
            INSERT OR IGNORE INTO area_master
            (area_code, area_name, area_type)
            VALUES (?, ?, ?)
            ''',
            (code, data["name"], "center")
        )

    # 都道府県・予報区（offices）
    for code, data in AREA_JSON["offices"].items():
        cur.execute(
            '''
            INSERT OR IGNORE INTO area_master
            (area_code, area_name, area_type)
            VALUES (?, ?, ?)
            ''',
            (code, data["name"], "office")
        )

    conn.commit()
    conn.close()

# 地域の親子関係をDBに挿入する関数
def insert_area_relation():
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    # 地方 → 都道府県
    for center_code, center_data in AREA_JSON["centers"].items():
        for child_code in center_data.get("children", []):
            if child_code in AREA_JSON["offices"]:
                cur.execute(
                    '''
                    INSERT OR IGNORE INTO area_relation
                    (parent_code, child_code)
                    VALUES (?, ?)
                    ''',
                    (center_code, child_code)
                )

    conn.commit()
    conn.close()


# 天気情報をDBに保存する関数
def save_forecast_to_db(office_code, dates, codes, weathers, temps_min, temps_max):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    fetched_at = datetime.now().isoformat()

    for i in range(len(dates)):
        date_obj = datetime.fromisoformat(dates[i])

        tmin = temps_min[i] if i < len(temps_min) and isinstance(temps_min[i], int) else None
        tmax = temps_max[i] if i < len(temps_max) and isinstance(temps_max[i], int) else None

        cur.execute(
            '''
            INSERT OR REPLACE INTO forecasts (
                area_code,
                forecast_date,
                weather,
                weather_code,
                temp_min,
                temp_max,
                fetched_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                office_code,
                date_obj.date().isoformat(),
                weathers[i],
                codes[i],
                tmin,
                tmax,
                fetched_at
            )
        )

    conn.commit()
    conn.close()

# 指定された地域コードの利用可能な予報日を取得する関数
def get_available_dates(area_code):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute(
        '''
        SELECT DISTINCT forecast_date
        FROM forecasts
        WHERE area_code = ?
        ORDER BY forecast_date DESC
        ''',
        (area_code,)
    )
    dates = [row[0] for row in cur.fetchall()]
    conn.close()
    return dates

# 指定された地域コードと日付の天気予報を取得する関数
def get_forecast_by_date(area_code, date):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT weather, weather_code, temp_min, temp_max
        FROM forecasts
        WHERE area_code = ? AND forecast_date = ?
        """,
        (area_code, date)
    )

    row = cur.fetchone()
    conn.close()

    if not row:
        return None

    weather, code, tmin, tmax = row
    return {
        "weather": weather,
        "weather_code": code,
        "min": tmin,
        "max": tmax,
    }

# 指定された地域コードと日付以降の7日間の天気予報を取得する関数
def get_7days_forecast_from_db(area_code, forecast_date):
    conn = sqlite3.connect(db_name)
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
            forecast_date,
            weather,
            weather_code,
            temp_min,
            temp_max
        FROM forecasts
        WHERE area_code = ?
          AND forecast_date >= ?
        ORDER BY forecast_date
        LIMIT 7
        """,
        (area_code, forecast_date)
    )

    rows = cur.fetchall()
    conn.close()

    days = []
    for d, weather, code, tmin, tmax in rows:
        days.append({
            "date": datetime.fromisoformat(d).strftime("%Y/%m/%d"),
            "weather": weather,
            "weather_code": code,
            "icons": weather_icons(weather),
            "min": tmin if tmin is not None else "-",
            "max": tmax if tmax is not None else "-",
        })

    return days

# 今日の気温（最小・最大）を天気予報データから探す関数
def find_today_temps(forecast):
    for ts in forecast[0]["timeSeries"]:
        for area in ts.get("areas", []):
            if "temps" in area:
                temps = [int(t) for t in area["temps"] if t not in ("", None)]
                if temps:
                    return min(temps), max(temps)
    return None, None


# 天気説明文からアイコンを抽出する関数
def weather_icons(text: str):
    # 単純なキーワード→アイコンのマッピング
    patterns = [
        ("晴", "☀️"),
        ("曇", "☁️"),
        ("雨", "🌧"),
        ("雪", "❄️"),
        ("雷", "🌩"),
        ("霧", "🌫"),
        ("みぞれ", "🌨"),
    ]
    icons = []
    index_list = []

    # 出現位置を全部取得
    for key, icon in patterns:
        idx = text.find(key)
        if idx != -1:
            index_list.append((idx, icon))

    # 文字列中の出現順で並び替え
    index_list.sort(key=lambda x: x[0])

    # 出現順にアイコンを追加
    for _, icon in index_list:
        if icon not in icons: # 重複防止
            icons.append(icon)

    # 何も見つからなかった場合
    if not icons:
        icons.append("✖️")
    return icons

# 背景色を気象コードから決定する関数
def bgcolor_from_weather_code(code: str):
    if code.startswith("1"):      # 晴系
        return ft.Colors.LIGHT_BLUE_50
    elif code.startswith("2"):    # 曇系
        return ft.Colors.BLUE_GREY_100
    elif code.startswith("3"):    # 雨系
        return ft.Colors.INDIGO_100
    elif code.startswith("4"):    # 雪系
        return ft.Colors.BLUE_50
    else:
        return ft.Colors.GREY_100
    
# 気象コード -> 説明（辞書）
# 参考：https://qiita.com/nak435/items/7f3588d3f75beb5890fa　
weatherDescription = {
    '100':'晴','101':'晴時々曇','102':'晴一時雨','103':'晴時々雨','104':'晴一時雪','105':'晴時々雪','106':'晴一時雨か雪','107':'晴時々雨か雪','108':'晴一時雨か雷雨','110':'晴後時々曇','111':'晴後曇','112':'晴後一時雨','113':'晴後時々雨','114':'晴後雨','115':'晴後一時雪','116':'晴後時々雪','117':'晴後雪','118':'晴後雨か雪','119':'晴後雨か雷雨','120':'晴朝夕一時雨','121':'晴朝の内一時雨','122':'晴夕方一時雨','123':'晴山沿い雷雨','124':'晴山沿い雪','125':'晴午後は雷雨','126':'晴昼頃から雨','127':'晴夕方から雨','128':'晴夜は雨','130':'朝の内霧後晴','131':'晴明け方霧','132':'晴朝夕曇','140':'晴時々雨で雷を伴う','160':'晴一時雪か雨','170':'晴時々雪か雨','181':'晴後雪か雨','200':'曇','201':'曇時々晴','202':'曇一時雨','203':'曇時々雨','204':'曇一時雪','205':'曇時々雪','206':'曇一時雨か雪','207':'曇時々雨か雪','208':'曇一時雨か雷雨','209':'霧','210':'曇後時々晴','211':'曇後晴','212':'曇後一時雨','213':'曇後時々雨','214':'曇後雨','215':'曇後一時雪','216':'曇後時々雪','217':'曇後雪','218':'曇後雨か雪','219':'曇後雨か雷雨','220':'曇朝夕一時雨','221':'曇朝の内一時雨','222':'曇夕方一時雨','223':'曇日中時々晴','224':'曇昼頃から雨','225':'曇夕方から雨','226':'曇夜は雨','228':'曇昼頃から雪','229':'曇夕方から雪','230':'曇夜は雪','231':'曇海上海岸は霧か霧雨','240':'曇時々雨で雷を伴う','250':'曇時々雪で雷を伴う','260':'曇一時雪か雨','270':'曇時々雪か雨','281':'曇後雪か雨','300':'雨','301':'雨時々晴','302':'雨時々止む','303':'雨時々雪','304':'雨か雪','306':'大雨','308':'雨で暴風を伴う','309':'雨一時雪','311':'雨後晴','313':'雨後曇','314':'雨後時々雪','315':'雨後雪','316':'雨か雪後晴','317':'雨か雪後曇','320':'朝の内雨後晴','321':'朝の内雨後曇','322':'雨朝晩一時雪','323':'雨昼頃から晴','324':'雨夕方から晴','325':'雨夜は晴','326':'雨夕方から雪','327':'雨夜は雪','328':'雨一時強く降る','329':'雨一時みぞれ','340':'雪か雨','350':'雨で雷を伴う','361':'雪か雨後晴','371':'雪か雨後曇','400':'雪','401':'雪時々晴','402':'雪時々止む','403':'雪時々雨','405':'大雪','406':'風雪強い','407':'暴風雪','409':'雪一時雨','411':'雪後晴','413':'雪後曇','414':'雪後雨','420':'朝の内雪後晴','421':'朝の内雪後曇','422':'雪昼頃から雨','423':'雪夕方から雨','425':'雪一時強く降る','426':'雪後みぞれ','427':'雪一時みぞれ','450':'雪で雷を伴う'
}

# 気温時系列データを探す関数
def find_temp_timeseries(forecast):
    for ts in forecast[1]["timeSeries"]:
        for area in ts.get("areas", []):
            if "tempsMin" in area and "tempsMax" in area:
                return ts
    return None

# コントロールをボックス化する関数
def boxed(control):
    return ft.Container(padding=5, border_radius=12, bgcolor=ft.Colors.WHITE, content=control)

# 特大の直近の日のカード
def today_card(data):
    return ft.Container(
        width=260, height=280, padding=25, border_radius=30, bgcolor=ft.Colors.WHITE,
        shadow=ft.BoxShadow(blur_radius=15, color=ft.Colors.with_opacity(0.2, ft.Colors.BLACK), offset=ft.Offset(0, 6)),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=15,
            controls=[
                ft.Text(data["date"], size=20, weight="bold"),
                ft.Row([ft.Text(icon, size=56) for icon in data["icons"]], alignment=ft.MainAxisAlignment.CENTER),
                ft.Text(data["weather"], size=20, weight=ft.FontWeight.W_500),
                # 気温：Rowを使って色分け
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=5,
                    controls=[
                        ft.Text(f"{data['min']}℃", size=18, weight="bold", color=ft.Colors.BLUE),
                        ft.Text("/", size=18, weight="bold"),
                        ft.Text(f"{data['max']}℃", size=18, weight="bold", color=ft.Colors.RED),
                    ]
                ),
            ],
        ),
    )

# 小さな明後日以降のカード
def small_day_card(data):
    return ft.Container(
        width=135, height=135, padding=12, border_radius=22, bgcolor=ft.Colors.WHITE,
        shadow=ft.BoxShadow(blur_radius=10, color=ft.Colors.with_opacity(0.15, ft.Colors.BLACK), offset=ft.Offset(0, 4)),
        content=ft.Column(
            alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=5,
            controls=[
                ft.Text(data["date"], size=11, color=ft.Colors.GREY_600, weight="bold"),
                ft.Row([ft.Text(icon, size=24) for icon in data["icons"]], alignment=ft.MainAxisAlignment.CENTER),
                ft.Text(data["weather"], size=11, text_align="center", max_lines=1),
                # 気温：Rowを使って色分け
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=4,
                    controls=[
                        ft.Text(f"{data['min']}°", size=12, weight="bold", color=ft.Colors.BLUE),
                        ft.Text("/", size=12, weight="bold"),
                        ft.Text(f"{data['max']}°", size=12, weight="bold", color=ft.Colors.RED),
                    ]
                ),
            ],
        ),
    )

# メイン関数
def main(page: ft.Page):
    page.title = "都道府県別 ７日間天気予報アプリ"
    page.bgcolor = ft.Colors.WHITE

    loading_text = ft.Text(
        "最新の気象データを取得しています…",
        size=24,
        weight=ft.FontWeight.BOLD,
        color=ft.Colors.GREY_700,
    )

    loading_view = ft.Column(
        controls=[
            ft.ProgressRing(),
            loading_text,
        ],
        alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        expand=True,
        spacing=20,
    )

    page.add(loading_view)
    page.update()

    # DB 初期化・データ取得
    insert_area_master()
    insert_area_relation()
    fetch_and_save_all_forecasts()

    # ローディング画面を消す
    page.controls.clear()

    # ここから通常のUI構築
    weather_column = ft.Column(spacing=20)

    # 都道府県ドロップダウン
    office_dd = ft.Dropdown(label="都道府県", disabled=True, width=320)
    # 地方ドロップダウン
    center_dd = ft.Dropdown(
        label="地方", width=320,
        options=[ft.dropdown.Option(key=k, text=v["name"]) for k, v in AREA_JSON["centers"].items()],
    )
    date_dd = ft.Dropdown(
        label="日付",
        disabled=True,
        width=320
    )

    # ① 地方 → ② 都道府県 の順で選択されたときの処理
    def on_center_change(e):
        code = e.control.value
        office_dd.options = [
            ft.dropdown.Option(key=o, text=AREA_JSON["offices"][o]["name"])
            for o in AREA_JSON["centers"][code]["children"] if o in AREA_JSON["offices"]
        ]
        office_dd.value = None
        office_dd.disabled = False
        weather_column.controls.clear()
        page.update()

    # ② 都道府県 が選択されたときの処理
    def on_office_change(e):
        office_code = e.control.value

        # ① 今日から7日間を表示
        show_latest_7days_weather(office_code)

        # ② 日付ドロップダウン用（過去含む）
        dates = get_available_dates(office_code)
        if dates:
            date_dd.options = [ft.dropdown.Option(d) for d in dates]
            date_dd.value = None
            date_dd.disabled = False
        else:
            date_dd.disabled = True

        page.update()

    # 今日から7日間の天気予報を表示する関数
    def show_latest_7days_weather(area_code):
        today = datetime.now().date().isoformat()
        weather_column.controls.clear()

        office_name = AREA_JSON["offices"][area_code]["name"]
        weather_column.controls.append(
            ft.Text(f"{office_name} の７日間天気予報", size=22, weight="bold")
        )

        days = get_7days_forecast_from_db(area_code, today)

        if not days:
            weather_column.controls.append(
                ft.Text("この地域の天気予報は現在取得できません\n（API仕様による制限）", color=ft.Colors.RED)
            )
            page.update()
            return
        
        page.bgcolor = bgcolor_from_weather_code(days[0]["weather_code"])

        weather_layout = ft.Row(
            spacing=20,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                today_card(days[0]),
                ft.Column(
                    spacing=10,
                    controls=[
                        ft.Row(spacing=15, controls=[small_day_card(days[i]) for i in range(1, min(4, len(days)))]),
                        ft.Row(spacing=15, controls=[small_day_card(days[i]) for i in range(4, min(7, len(days)))]),
                    ],
                ),
            ],
        )

        weather_column.controls.append(weather_layout)
        page.update()

    # 日付が選択されたときの処理
    def on_date_change(e):
        weather_column.controls.clear()

        data = get_forecast_by_date(
            office_dd.value,
            e.control.value
        )

        if not data:
            return


        data["date"] = datetime.fromisoformat(e.control.value).strftime("%Y/%m/%d")
        data["icons"] = weather_icons(data["weather"])

        page.bgcolor = bgcolor_from_weather_code(data["weather_code"])

        office_name = AREA_JSON["offices"][office_dd.value]["name"]
        weather_column.controls.append(
            ft.Text(f"{office_name}（{e.control.value}）の天気", size=22, weight="bold")
        )

        weather_column.controls.append(today_card(data))
        page.update()



    date_dd.on_change = on_date_change
    center_dd.on_change = on_center_change
    office_dd.on_change = on_office_change

    page.add(
        ft.Column(
            spacing=20,
            controls=[
                ft.Text(
                    "都道府県別 天気予報（７日間）",
                    size=28,
                    weight=ft.FontWeight.BOLD
                ),

                # ▼ 地方・都道府県を横並び
                ft.Row(
                    spacing=20,
                    controls=[
                        boxed(center_dd),
                        boxed(office_dd),
                    ],
                ),

                # ▼ 日付ドロップダウンはその下
                boxed(date_dd),

                weather_column,
            ],
        )
    )


ft.app(target=main)