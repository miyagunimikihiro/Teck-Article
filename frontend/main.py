import flet as ft
import requests
import os

# バックエンドAPIのベースURL（Dockerネットワーク内のサービス名で指定）
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")

def main(page: ft.Page):
    page.title = "技術記事収集アプリ - 選択式フィルター搭載"
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

    #キーワードの選択用のドロップダウン
    # 選択が切り替わったときに、自動で「keyword_filter_changde」が呼び出される設定
    keyword_filter = ft.Dropdown(
        label="キーワードで絞り込む",
        width=200,
        options=[
            ft.dropdown.Option("すべて"),
            ft.dropdown.Option("python"),
            ft.dropdown.Option("Docker"),
            ft.dropdown.Option("JavaScript"),
            ft.dropdown.Option("AI"),

        ],
        value="すべて"
    )

    # ドロップダウンの値が変更されたときのイベントハンドラ
    def keyword_filter_changed(e):
        refresh_articles(keyword=keyword_filter.value)
    
    # 関数のイベント紐づけ
    keyword_filter.on_change = keyword_filter_changed

    # 記事一覧をバックエンドから取得して再描画する関数
    def refresh_articles(keyword = None):
        articles_list.controls.clear()
        try:
            params = {}
            if keyword and keyword != "すべて":
                params["keyword"] = keyword

            response = requests.get(f"{BACKEND_URL}/articles", params=params)
            if response.status_code == 200:
                articles = response.json()
                if not articles:
                    articles_list.controls.append(ft.Text("収集された記事はまだありません。"))
                else:
                    for article in reversed(articles):
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
    
    

    # 記事を手動で登録するボタンのイベントハンドラ
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
                refresh_articles(keyword=keyword_filter.value)  # 一覧を更新
            else:
                error_detail = response.json().get("detail", "登録に失敗しました。")
                page.snack_bar = ft.SnackBar(ft.Text(f"エラー: {error_detail}"))
                page.snack_bar.open = True
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"通信エラー: {ex}"))
            page.snack_bar.open = True
        
        page.update()
    
    # RSS一括取得ボタンのイベントハンドラ
    def fetch_rss_click(e):
        fetch_rss_button.disabled = True
        fetch_rss_button.text = "RSSフィードを取得中..."
        page.update()

        try:
            response = requests.post(f"{BACKEND_URL}/articles/fetch-rss")
            if response.status_code == 200:
                result = response.json()
                page.snack_bar = ft.SnackBar(ft.Text(result["message"]))
                page.snack_bar.open = True
                refresh_articles(keyword=keyword_filter.value)
            else:
                page.snack_bar = ft.SnackBar(ft.Test("RSSフィードの取得に失敗しました"))
                page.snack_bar.open = True
        except Exception as ex:
            page.snack_bar = ft.SnackBar(ft.Text(f"通信エラー: {ex}"))
            page.snack_bar.open = True
        
        fetch_rss_button.disabled = False
        fetch_rss_button.text = "最新記事を自動収集"
        page.update()


    # 登録ボタン
    add_button = ft.ElevatedButton("記事を追加", on_click=add_article_click)
    fetch_rss_button = ft.FilledButton("最新記事を自動収集", on_click=fetch_rss_click,icon=ft.icons.DOWNLOAD)

    # 画面レイアウトの組み立て
    page.add(
        ft.Column([
            ft.Row([
            ft.Text("技術記事収集アプリケーション ", size=24, weight=ft.FontWeight.BOLD),
            fetch_rss_button]
            ,alignment=ft.MainAxisAlignment.SPACE_BETWEEN
            ),
            ft.Divider(),
            ft.Text("新しい記事の登録", size=18, weight=ft.FontWeight.BOLD),
            ft.Row([title_input, url_input, source_dropdown, add_button], wrap=True),
            ft.Divider(),
            ft.Row([
            ft.Text("収集された記事一覧", size=18, weight=ft.FontWeight.BOLD),
            keyword_filter],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            articles_list
        ], expand=True)
    )

    # 初期表示時に記事一覧を読み込む
    refresh_articles(keyword=keyword_filter.value)

ft.app(target=main)