from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import datetime
import os

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
def get_articles(db: Session = Depends(get_db)):
    articles = db.query(Article).all()
    return articles

# 記事を手動で登録するAPI
@app.post("/articles")
def create_article(title: str, url: str, source: str, db: Session = Depends(get_db)):
    db_article = db.query(Article).filter(Article.url == url).first()
    if db_article:
        raise HTTPException(status_code=400, detail="Article already registered")
    
    new_article = Article(title=title, url=url, source=source)
    db.add(new_article)
    db.commit()
    db.refresh(new_article)
    return new_article