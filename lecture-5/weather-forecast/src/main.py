import flet as ft
import requests
from datetime import datetime

# エンドポイントURL
AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{}.json"

# エンドポイントから地域データを取得
AREA_JSON = requests.get(AREA_URL).json()

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
    page.padding = 30
    page.bgcolor = ft.Colors.WHITE
    weather_column = ft.Column(spacing=20)

    # 都道府県ドロップダウン
    office_dd = ft.Dropdown(label="都道府県", disabled=True, width=320)
    # 地方ドロップダウン
    center_dd = ft.Dropdown(
        label="地方", width=320,
        options=[ft.dropdown.Option(key=k, text=v["name"]) for k, v in AREA_JSON["centers"].items()],
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

    # ② 都道府県 → 天気取得 のときの処理
    def on_office_change(e):
        office_code = e.control.value
        weather_column.controls.clear()

        try:
            forecast = requests.get(
                FORECAST_URL.format(office_code)
            ).json()

            if not forecast or "timeSeries" not in forecast[0]:
                raise ValueError("この地域の予報は提供されていません")

        except Exception:
            weather_column.controls.append(
                ft.Text(
                    "この地域の天気予報は現在取得できません\n"
                    "（API仕様による制限）",
                    color=ft.Colors.RED,
                )
            )
            page.update()
            return

        office_name = AREA_JSON["offices"][office_code]["name"]
        weather_column.controls.append(ft.Text(f"{office_name} の７日間天気予報", size=22, weight="bold"))

        weather_ts = forecast[1]["timeSeries"][0]
        temp_ts = find_temp_timeseries(forecast)
        dates = weather_ts["timeDefines"]
        codes = weather_ts["areas"][0]["weatherCodes"]
        page.bgcolor = bgcolor_from_weather_code(codes[0])

        weathers = [weatherDescription.get(code, "不明") for code in codes]
        temps_min, temps_max = [], []
        if temp_ts:
            area = temp_ts["areas"][0]
            temps_min = [int(t) if t not in ("", None) else "-" for t in area.get("tempsMin", [])]
            temps_max = [int(t) if t not in ("", None) else "-" for t in area.get("tempsMax", [])]

        # 7日分のデータをリスト化
        days = []
        for i in range(7):
            date_obj = datetime.fromisoformat(dates[i])
            days.append({
                "date": date_obj.strftime("%Y/%m/%d"),
                "weather": weathers[i] if i < len(weathers) else "不明",
                "icons": weather_icons(weathers[i]) if i < len(weathers) else ["✖️"],
                "min": temps_min[i] if i < len(temps_min) else "-",
                "max": temps_max[i] if i < len(temps_max) else "-",
            })

        # レイアウト構築：左に直近の日、右に6日間
        weather_layout = ft.Row(
            spacing=20,
            vertical_alignment=ft.CrossAxisAlignment.START,
            controls=[
                today_card(days[0]), # 左側
                ft.Column( # 右側
                    spacing=10,
                    controls=[
                        ft.Row(spacing=15, controls=[small_day_card(days[i]) for i in range(1, 4)]),
                        ft.Row(spacing=15, controls=[small_day_card(days[i]) for i in range(4, 7)]),
                    ],
                ),
            ],
        )

        weather_column.controls.append(weather_layout)
        page.update()

    center_dd.on_change = on_center_change
    office_dd.on_change = on_office_change

    page.add(
        ft.Column([
            ft.Text("都道府県別 天気予報（７日間）", size=28, weight=ft.FontWeight.BOLD),
            boxed(center_dd), boxed(office_dd),
            weather_column,
        ], spacing=20)
    )

ft.app(target=main)