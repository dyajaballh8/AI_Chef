import os
from dotenv import load_dotenv

# تحميل متغيرات البيئة من ملف .env
load_dotenv()

from app.database import engine, Base
from app import models  # مهم جداً ليستورد كل الجداول

print("جاري إنشاء الجداول في Neon PostgreSQL...")
try:
    Base.metadata.create_all(bind=engine)
    print("تم إنشاء جميع الجداول بنجاح في Neon!")
except Exception as e:
    print(f"حدث خطأ أثناء الإنشاء: {e}")