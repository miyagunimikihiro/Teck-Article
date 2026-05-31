from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import datetime
import os
import feedparser
import requests

# 1. データベースの設定
DATABASE_URL = "sqlite:////app/database.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. データベースのテーブル定義（モデル）
class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    url = Column(String, unique=True, nullable=False)
    source = Column(String, nullable=False)  # 例: Qiita, Zenn
    tags = Column(String, nullable=True)  # カンマ区切りのタグリスト
    published_at = Column(DateTime, default=datetime.datetime.utcnow)

# テーブルの自動生成（ファイルがなければここで database.db が作られる）
Base.metadata.create_all(bind=engine)

# 3. FastAPIの初期化
app = FastAPI(title="Tech Article Aggregator API")

# データベースセッションの依存関係
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# 4. APIエンドポイント（動作確認用のテスト用）
@app.get("/")
def read_root():
    return {"message": "Welcome to Tech Article Aggregator API"}

# 記事一覧を取得するAPI
@app.get("/articles")
def get_articles(keyword: str = None, db: Session = Depends(get_db)):
    query = db.query(Article)

    if keyword and keyword != "すべて":
        if keyword == "Zennトレンド":
            query = query.filter(Article.source == "Zenn")
        else:
            # タイトル、または新設したtagsカラムにキーワードが含まれるものをOR条件で検索
            query = query.filter(
                (Article.title.like(f"%{keyword}%")) |
                (Article.tags.like(f"%{keyword}%")) 
            )
    return query.all()

# 記事を手動で登録するAPI
@app.post("/articles")
def create_article(title: str, url: str, source: str, tags: str = None, db: Session = Depends(get_db)):
    db_article = db.query(Article).filter(Article.url == url).first()
    if db_article:
        raise HTTPException(status_code=400, detail="Article already registered")
    
    new_article = Article(title=title, url=url, source=source, tags=tags)
    db.add(new_article)
    db.commit()
    db.refresh(new_article)
    return new_article



@app.post("/articles/fetch-rss")
def fetch_rss_articles(db: Session = Depends(get_db)):
    """
    QiitaとZennのRSSフィードを解析し、未登録の記事をデータベースに自動保存するAPI
    """
    added_count = 0
    header = {"User-Agent": "TechArticleAggregatorApp/1.0"}
    #============ Qiita 公式APIから記事を取得して保存する処理 ============
    try:
        qiita_api_url = "http://qiita.com/api/v2/items"
        params = {
            "page":1,
            "per_page":10,
            "query":"stock:>5"
        }
        qiita_response = requests.get(qiita_api_url, params=params,headers=header, timeout=5)

        if qiita_response.status_code == 200:
            qiita_items = qiita_response.json()
            for item in qiita_items:
                title = item.get("title")
                link = item.get("url")
                if not title or not link:
                    continue

                existing = db.query(Article).filter(Article.url == link).first()
                if existing:
                    continue

                raw_tags = item.get("tags", [])
                tag_names = [t.get("name") for t in raw_tags if t.get("name")]
                tags_str = ",".join(tag_names) if tag_names else None

                new_article = Article(title=title, url=link, source="Qiita", tags=tags_str)
                db.add(new_article)
                added_count += 1
        else:
            print(f"Qiita API error: {qiita_response.status_code}")
        
    except Exception as e:
        print(f"Qiita API通信エラー: {e}")

    #============ ZennのRSSフィードから記事を取得して保存する処理 ============
    try:
        zenn_feed = feedparser.parse("https://zenn.dev/feed")
        for entry in zenn_feed.entries:
            title = entry.get("title")
            link = entry.get("link")

            if not title or not link:
                continue

            existing = db.query(Article).filter(Article.url == link).first()
            if existing:
                continue

            tag_list = []
            raw_categories = entry.get("categories")
            if raw_categories:
                tag_list = [c for c in raw_categories if c]
            tags_str = ",".join(tag_list) if tag_list else None

            new_article = Article(title=title, url=link, source="Zenn", tags=tags_str)
            db.add(new_article)
            added_count += 1
    except Exception as e:
        print(f"Zenn RSS通信エラー: {e}")
    
    #========データベースに保存する===========
    if added_count > 0:
        db.commit()
    return {
        "status": "success",
        "message": f"Qiita人気記事およびZenn新着記事から{added_count}件の記事を追加しました。"}


@app.get("/tags")
def get_trending_tags():
    """
    Qiitaの公式APIから投稿数の多いタグを取得し、絞り込み用のキーワードリストとして返す
    """
    try:
        "Qiitaのタグ一覧API"
        qiita_tags_url = "https://qiita.com/api/v2/tags?page=1&per_page=10&sort=count"
        headers = {"User-Agent": "TechArticleAggregatorApp/1.0"}

        response = requests.get(qiita_tags_url,headers=headers, timeout=5)
        
        if response.status_code == 200:
            tags_data = response.json()
            # タグのIDを抽出してキーワードリストを作成
            keywords = [tag["id"] for tag in tags_data]

            return ["すべて","Zennトレンド"] + keywords
        else:
            return ["すべて","Python", "JavaScript", "Go", "Ruby"]  # デフォルトのキーワードリスト
    
    except Exception:
        return ["すべて","Python", "JavaScript", "Go", "Ruby"]  # デフォルトのキーワードリスト
    