import flet as ft

# 定数PI(円周率)を定義
PI = 3.141592653589793

# 新しくCalcButtonクラスを定義
class CalcButton(ft.ElevatedButton):
    def __init__(self, text, button_clicked, expand=1):
        super().__init__()
        self.text = text
        self.expand = expand
        self.on_click = button_clicked
        self.data = text

class DigitButton(CalcButton):
    def __init__(self, text, button_clicked, expand=1):
        CalcButton.__init__(self, text, button_clicked, expand)
        self.bgcolor = ft.Colors.WHITE24
        self.color = ft.Colors.WHITE

class ActionButton(CalcButton):
    def __init__(self, text, button_clicked, expand=1):
        CalcButton.__init__(self, text, button_clicked, expand)
        self.bgcolor = ft.Colors.ORANGE
        self.color = ft.Colors.WHITE

class ExtraActionButton(CalcButton):
    def __init__(self, text, button_clicked, expand=1):
        CalcButton.__init__(self, text, button_clicked, expand)
        self.bgcolor = ft.Colors.BLUE_GREY_100
        self.color = ft.Colors.BLACK

class CalculatorApp(ft.Container):
    # sin, cos, tan, In, √, x!, X^y をUNARY_OPSとして定義
    UNARY_OPS = ("sin", "cos", "tan", "In", "√", "x!", "X^y")

    def __init__(self):
        super().__init__()
        self.reset()

        self.result = ft.Text(value="0", color=ft.Colors.WHITE, size=20)
        self.width = 350
        self.bgcolor = ft.Colors.BLACK
        self.border_radius = ft.border_radius.all(20)
        self.padding = 20
        self.content = ft.Column(
            controls=[
                ft.Row(controls=[self.result], alignment="end"),
                ft.Row(
                    controls=[
                        ExtraActionButton(text="AC", expand=1, button_clicked=self.button_clicked),
                        ExtraActionButton(text="+/-", expand=1, button_clicked=self.button_clicked),
                        ExtraActionButton(text="%", expand=1, button_clicked=self.button_clicked),
                        ActionButton(text="/", expand=1, button_clicked=self.button_clicked),
                        ActionButton(text="sin", expand=2, button_clicked=self.button_clicked),
                    ]
                ),
                ft.Row(
                    controls=[
                        DigitButton(text="7", expand=1, button_clicked=self.button_clicked),
                        DigitButton(text="8", expand=1, button_clicked=self.button_clicked),
                        DigitButton(text="9", expand=1, button_clicked=self.button_clicked),
                        ActionButton(text="*", expand=1, button_clicked=self.button_clicked),
                        ActionButton(text="cos", expand=2, button_clicked=self.button_clicked),
                    ]
                ),
                ft.Row(
                    controls=[
                        DigitButton(text="4", expand=1, button_clicked=self.button_clicked),
                        DigitButton(text="5", expand=1, button_clicked=self.button_clicked),
                        DigitButton(text="6", expand=1, button_clicked=self.button_clicked),
                        ActionButton(text="-", expand=1, button_clicked=self.button_clicked),
                        ActionButton(text="tan", expand=2, button_clicked=self.button_clicked),
                    ]
                ),
                ft.Row(
                    controls=[
                        DigitButton(text="1", expand=1, button_clicked=self.button_clicked),
                        DigitButton(text="2", expand=1, button_clicked=self.button_clicked),
                        DigitButton(text="3", expand=1, button_clicked=self.button_clicked),
                        ActionButton(text="+", expand=1, button_clicked=self.button_clicked),
                        ActionButton(text="In", expand=1, button_clicked=self.button_clicked),
                        ActionButton(text="x!", expand=1, button_clicked=self.button_clicked),
                    ]
                ),
                ft.Row(
                    controls=[
                        DigitButton(text="0", expand=2, button_clicked=self.button_clicked),
                        DigitButton(text=".", expand=1, button_clicked=self.button_clicked),
                        ActionButton(text="=", expand=2, button_clicked=self.button_clicked),
                        ActionButton(text="√", expand=1, button_clicked=self.button_clicked),
                    ]
                ),
            ]
        )

    def button_clicked(self, e, UNARY_OPS=UNARY_OPS):
        data = e.control.data
        print(f"Button clicked with data = {data}")
        if self.result.value == "Error" or data == "AC":
            self.result.value = "0"
            self.reset()

        elif data in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "."):
            if self.result.value == "0" or self.new_operand == True:
                self.result.value = data
                self.new_operand = False
            else:
                self.result.value = self.result.value + data

        elif data in ("+", "-", "*", "/"):
            self.result.value = self.calculate(self.operand1, float(self.result.value), self.operator)
            self.operator = data
            if self.result.value == "Error":
                self.operand1 = "0"
            else:
                self.operand1 = float(self.result.value)
            self.new_operand = True

        elif data in UNARY_OPS:
            # 表示を先に変える
            self.result.value = f"{data}"
            self.operator = data
            self.new_operand = True

        elif data in ("="):
            self.result.value = self.calculate(
                self.operand1,
                float(self.result.value),
                self.operator
            )
            self.reset()


        elif data in ("%"):
            self.result.value = float(self.result.value) / 100
            self.reset()

        elif data in ("+/-"):
            if float(self.result.value) > 0:
                self.result.value = "-" + str(self.result.value)

            elif float(self.result.value) < 0:
                self.result.value = str(self.format_number(abs(float(self.result.value))))


        self.update()

    def format_number(self, num):
        # エラー文字列の場合はそのまま返す
        if isinstance(num, str):
            return num
        # 小数点以下10桁で丸める
        num = round(num, 10)
        # 整数なら整数型で返す
        if num % 1 == 0:
            return int(num)
        else:
            return num
        
    # 平方根をニュートン法で計算
    def sqrt(self, a):
        if a < 0:
            return "Error"

        x = a
        for _ in range(10):
            x = (x + a / x) / 2
        return x

    # 三角関数と自然対数をテイラー展開で計算
    # sinのテイラー展開
    def sin(self, x):
        x = x * PI / 180
        result = 0
        term = x
        sign = 1

        for n in range(1, 20, 2):
            result += sign * term
            term = term * x * x / ((n+1)*(n+2))
            sign *= -1

        return result
    # cosのテイラー展開
    def cos(self, x):
        x = x * PI / 180
        result = 1
        term = 1
        sign = -1

        for n in range(2, 20, 2):
            term = term * x * x / (n*(n-1))
            result += sign * term
            sign *= -1

        return result
    # tanはsin/cosで計算
    def tan(self, x):
        c = self.cos(x)
        if c == 0:
            return "Error"
        return self.sin(x) / c
    # lnのテイラー展開
    def ln(self, x):
        if x <= 0:
            return "Error"

        y = (x - 1) / (x + 1)
        result = 0
        term = y

        for n in range(1, 20, 2):
            result += term / n
            term *= y * y

        return 2 * result
    
    def factorial(self, n):
        if n < 0:
            return "Error"

        if int(n) != n:
            return "Error"   # 小数の階乗は扱わない

        result = 1
        n = int(n)

        for i in range(1, n + 1):
            result *= i

        return result


    def calculate(self, operand1, operand2, operator):

        if operator == "+":
            return self.format_number(operand1 + operand2)

        elif operator == "-":
            return self.format_number(operand1 - operand2)

        elif operator == "*":
            return self.format_number(operand1 * operand2)

        elif operator == "/":
            if operand2 == 0:
                return "Error"
            else:
                return self.format_number(operand1 / operand2)
            
        elif operator == "√":
            return self.format_number(self.sqrt(operand2))

        elif operator == "sin":
            return self.format_number(self.sin(operand2))

        elif operator == "cos":
            return self.format_number(self.cos(operand2))

        elif operator == "tan":
            return self.format_number(self.tan(operand2))

        elif operator == "In":
            return self.format_number(self.ln(operand2))
        
        elif operator == "x!":
            return self.format_number(self.factorial(operand2))


    def reset(self):
        self.operator = "+"
        self.operand1 = 0
        self.new_operand = True


def main(page: ft.Page):
    page.title = "Simple Calculator"
    calc = CalculatorApp()
    page.add(calc)

ft.app(main)