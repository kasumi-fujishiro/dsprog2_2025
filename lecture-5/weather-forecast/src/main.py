import flet as ft
import requests
from datetime import datetime

AREA_URL = "https://www.jma.go.jp/bosai/common/const/area.json"
FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/{}.json"

AREA_JSON = requests.get(AREA_URL).json()

def weather_icons(text: str):
    patterns = [
        ("晴", "☀️"),
        ("くもり", "☁️"),
        ("曇", "☁️"),
        ("雨", "🌧"),
        ("雪", "❄️"),
        ("雷", "⛈"),
        ("霧", "🌫"),
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

    for _, icon in index_list:
        if icon not in icons:  # 重複防止
            icons.append(icon)

    # 何も見つからなかった場合
    if not icons:
        icons.append("🌤")

    return icons

def find_temp_timeseries(forecast):
    for ts in forecast[1]["timeSeries"]:
        for area in ts.get("areas", []):
            if "tempsMin" in area and "tempsMax" in area:
                return ts
    return None


def day_card(date_str, weather_text, t_min=None, t_max=None):
    return ft.Container(
        width=150,
        padding=15,
        border_radius=15,
        bgcolor=ft.Colors.WHITE,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=8,
            controls=[
                ft.Text(date_str, size=12, weight="bold"),

                # 天気アイコン
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=5,
                    controls=[
                        ft.Text(icon, size=32)
                        for icon in weather_icons(weather_text)
                    ],
                ),

                ft.Text(weather_text, size=12, text_align="center"),

                # 🌡 気温（色分け）
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=6,
                    controls=[
                        ft.Text(
                            f"{t_min}℃" if t_min is not None else "-",
                            color=ft.Colors.BLUE,
                            size=12,
                        ),
                        ft.Text("/", size=12),
                        ft.Text(
                            f"{t_max}℃" if t_max is not None else "-",
                            color=ft.Colors.RED,
                            size=12,
                        ),
                    ],
                ),
            ],
        ),
    )



def main(page: ft.Page):
    page.title = "都道府県別 3日間天気予報アプリ"
    page.padding = 20
    page.bgcolor = ft.Colors.BLUE_GREY_100  # ★ 追加


    weather_column = ft.Column(spacing=10)

    # 都道府県ドロップダウン
    office_dd = ft.Dropdown(label="都道府県", disabled=True, width=320)

    # 地方ドロップダウン
    center_dd = ft.Dropdown(
        label="地方",
        width=320,
        options=[
            ft.dropdown.Option(key=k, text=v["name"])
            for k, v in AREA_JSON["centers"].items()
        ],
    )

    # ① 地方 → ② 都道府県
    def on_center_change(e):
        code = e.control.value
        office_dd.options = [
            ft.dropdown.Option(key=o, text=AREA_JSON["offices"][o]["name"])
            for o in AREA_JSON["centers"][code]["children"]
            if o in AREA_JSON["offices"]
        ]
        office_dd.value = None
        office_dd.disabled = False
        weather_column.controls.clear()
        page.update()

    # ② 都道府県 → 天気取得
    def on_office_change(e):
        office_code = e.control.value
        weather_column.controls.clear()

        try:
            forecast = requests.get(
                FORECAST_URL.format(office_code)
            ).json()
        except Exception:
            weather_column.controls.append(
                ft.Text("天気データの取得に失敗しました", color=ft.Colors.RED)
            )
            page.update()
            return

        office_name = AREA_JSON["offices"][office_code]["name"]
        weather_column.controls.append(
            ft.Text(f"{office_name} の３日間天気予報", size=18, weight="bold")
        )

        # 天気（3日）
        weather_ts = forecast[0]["timeSeries"][0]

        # 気温（3日）
        temp_ts = find_temp_timeseries(forecast)

        dates = weather_ts["timeDefines"]
        weathers = weather_ts["areas"][0]["weathers"]

        temps_min = []
        temps_max = []


        if temp_ts:
            area = temp_ts["areas"][0]

            temps_min = [
                int(t) if t not in ("", None) else None
                for t in area.get("tempsMin", [])
            ]
            temps_max = [
                int(t) if t not in ("", None) else None
                for t in area.get("tempsMax", [])
            ]


        row = ft.Row(wrap=True, spacing=15)

        for i in range(len(dates)):
            date_str = datetime.fromisoformat(dates[i]).strftime("%m/%d")
            w = weathers[i] if i < len(weathers) else ""

            tmin = temps_min[i] if i < len(temps_min) else None
            tmax = temps_max[i] if i < len(temps_max) else None

            row.controls.append(
                day_card(date_str, w, tmin, tmax)
            )

        weather_column.controls.append(row)
        page.update()



    center_dd.on_change = on_center_change
    office_dd.on_change = on_office_change

    page.add(
        ft.Column(
            [
                ft.Text("都道府県別 天気予報（３日間）", size=24, weight="bold"),
                center_dd,
                office_dd,
                weather_column,
            ],
            spacing=20,
        )
    )


ft.app(target=main)