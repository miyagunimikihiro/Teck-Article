import flet as ft
import requests
import os

# バックエンドAPIのベースURL（Dockerネットワーク内のサービス名で指定）
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

def main(page: ft.Page):
    page.title = "技術記事収集アプリ - MVP"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 20

    # UI要素の定義
    title_input = ft.TextField(label="記事タイトル", width=300)
    url_input = ft.TextField(label="URL", width=400)
    source_dropdown = ft.Dropdown(
        label="情報源",
        width=150,
        options=[
            ft.dropdown.Option("Qiita"),
            ft.dropdown.Option("Zenn"),
            ft.dropdown.Option("その他"),
        ],
        value="Qiita"
    )
    
    articles_list = ft.ListView(expand=1, spacing=10, padding=20)

    # 記事一覧をバックエンドから取得して再描画する関数
    def refresh_articles():
        articles_list.controls.clear()
        try:
            response = requests.get(f"{BACKEND_URL}/articles")
            if response.status_code == 200:
                articles = response.json()
                for article in articles:
                    articles_list.controls.append(
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column([
                                    ft.Text(article["title"], weight=ft.FontWeight.BOLD, size=16),
                                    ft.Text(article["url"], color=ft.colors.BLUE_700, size=14),
                                    ft.Text(f"ソース: {article['source']}", size=12, color=ft.colors.GREY_600)
                                ]),
                                padding=10
                            )
                        )
                    )
            else:
                articles_list.controls.append(ft.Text("データの取得に失敗しました。"))
        except Exception as e:
            articles_list.controls.append(ft.Text(f"サーバーに接続できません: {e}"))
        
        page.update()

    # 記事を登録するボタンのイベントハンドラ
    def add_article_click(e):
        if not title_input.value or not url_input.value:
            page.snack_bar = ft.SnackBar(ft.Text("タイトルとURLを入力してください。"))
            page.snack_bar.open = True
            page.update()
            return

        payload = {
            "title": title_input.value,
            "url": url_input.value,
            "source": source_dropdown.value
        }
        
        try:
            # クエリパラメータとして送信
            response = requests.post(
                f"{BACKEND_URL}/articles", 
                params=payload
            )
            if response.status_code == 200:
                page.snack_bar = ft.SnackBar(ft.Text("記事を登録しました！"))
                page.snack_bar.open = True
                # 入力フォームをクリア
                title_input.value = ""
                url_input.value = ""
                refresh_articles()  # 一覧を更新
            else:
                error_detail = response.json().get("detail", "登録に失敗しました。")
                page.snack_bar = ft.SnackBar(ft.Text(f"エラー: {error_detail}"))
                page.snack_bar.open = True
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"通信エラー: {ex}"))
            page.snack_bar.open = True
        
        page.update()

    # 登録ボタン
    add_button = ft.ElevatedButton("記事を追加", on_click=add_article_click)

    # 画面レイアウトの組み立て
    page.add(
        ft.Column([
            ft.Text("技術記事収集アプリケーション (MVP)", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            ft.Text("新しい記事の登録", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([title_input, url_input, source_dropdown, add_button], wrap=True),
            ft.Divider(),
            ft.Text("収集された記事一覧", size=18, weight=ft.FontWeight.BOLD),
            articles_list
        ], expand=True)
    )

    # 初期表示時に記事一覧を読み込む
    refresh_articles()

ft.app(target=main)