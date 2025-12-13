import flet as ft


def main(page: ft.Page):
    # カウンター表示用のテキスト 
    counter = ft.Text("0", size=50, data=0)

    # テキストがどこに追加されるのか確認するためのテキスト
    hoge = ft.Text("Hello, Flet!", size=30)

    # ボタンが押された時に呼び出される関数
    def increment_click(e):
        counter.data += 1
        counter.value = str(counter.data)
        counter.update()

    def decrement_click(e):
        counter.data -= 1
        counter.value = str(counter.data)
        counter.update()

    # カウンターを増加させるためのフローティングアクションボタンを追加
    page.floating_action_button = ft.FloatingActionButton(
        icon=ft.Icons.ADD, on_click=increment_click
    )


    # # SafeArea内で囲んで、カウンターを中央配置して追加
    # page.add(
    #     ft.SafeArea(
    #         ft.Container(
    #             counter,
    #             alignment=ft.alignment.center,
    #         ),
    #         expand=True,
    #     ),
    #     ft.FloatingActionButton(
    #     icon=ft.Icons.REMOVE, on_click=decrement_click
    #     ),
    #     hoge,
    # )

    # 複数の表示をするときの順番は、追加した順番になることがわかります。
    page.add(
        ft.SafeArea(
            ft.Container(
                content = ft.Column([counter, hoge]),
                alignment=ft.alignment.center,
            ),
            expand=True,
        ),
        ft.FloatingActionButton(
        icon=ft.Icons.REMOVE, on_click=decrement_click
        ),
    )    


ft.app(main)
