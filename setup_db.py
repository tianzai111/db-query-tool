"""
示例数据库初始化脚本
创建一个包含用户、产品、订单的示例数据库
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")


def init_database(db_path: str = DB_PATH):
    """初始化示例数据库"""

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 清空已有表（避免文件锁定问题）
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    for table in existing_tables:
        cursor.execute(f"DROP TABLE IF EXISTS {table}")

    # ===== 创建表结构 =====

    # 用户表
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            department TEXT,
            salary REAL,
            hire_date TEXT,
            status TEXT DEFAULT 'active'
        )
    """)

    # 产品表
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            price REAL,
            stock INTEGER DEFAULT 0,
            description TEXT
        )
    """)

    # 订单表
    cursor.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_id INTEGER,
            quantity INTEGER DEFAULT 1,
            total_price REAL,
            order_date TEXT,
            status TEXT DEFAULT 'pending',
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        )
    """)

    # ===== 插入示例数据 =====

    departments = ["工程部", "产品部", "设计部", "市场部", "运营部", "人事部"]
    names = [
        "张伟", "王芳", "李强", "刘洋", "陈静", "杨光", "赵敏", "黄磊",
        "周杰", "吴婷", "徐明", "孙丽", "马超", "朱琳", "胡军", "郭靖",
        "何雪", "高峰", "林峰", "罗艳",
    ]

    users_data = []
    for i, name in enumerate(names, 1):
        email = f"user{i:02d}@example.com"
        dept = random.choice(departments)
        salary = random.randint(6000, 25000)
        hire_date = (datetime(2020, 1, 1) + timedelta(days=random.randint(0, 1800))).strftime("%Y-%m-%d")
        status = random.choice(["active", "active", "active", "inactive"])
        users_data.append((name, email, dept, salary, hire_date, status))

    cursor.executemany(
        "INSERT INTO users (name, email, department, salary, hire_date, status) VALUES (?, ?, ?, ?, ?, ?)",
        users_data,
    )

    # 产品数据
    categories = ["电子产品", "办公用品", "图书", "食品", "服装"]
    product_names = [
        "笔记本电脑", "机械键盘", "显示器", "鼠标", "耳机",
        "办公椅", "台灯", "文件夹", "订书机", "便签纸",
        "Python编程", "算法导论", "设计模式", "数据库系统", "AI入门",
        "咖啡豆", "巧克力", "坚果", "饼干", "矿泉水",
        "工牌挂绳", "文化衫", "保温杯", "背包", "笔筒",
    ]

    products_data = []
    for i, name in enumerate(product_names, 1):
        cat = categories[(i - 1) // 5]
        price = round(random.uniform(9.9, 9999.9), 2)
        stock = random.randint(0, 500)
        desc = f"{name} - 高品质{cat}"
        products_data.append((name, cat, price, stock, desc))

    cursor.executemany(
        "INSERT INTO products (name, category, price, stock, description) VALUES (?, ?, ?, ?, ?)",
        products_data,
    )

    # 订单数据
    orders_data = []
    for _ in range(50):
        uid = random.randint(1, len(names))
        pid = random.randint(1, len(product_names))
        qty = random.randint(1, 5)
        total = round(qty * random.uniform(10, 5000), 2)
        order_date = (datetime(2024, 1, 1) + timedelta(days=random.randint(0, 550))).strftime("%Y-%m-%d")
        status = random.choice(["pending", "shipped", "delivered", "cancelled"])
        orders_data.append((uid, pid, qty, total, order_date, status))

    cursor.executemany(
        "INSERT INTO orders (user_id, product_id, quantity, total_price, order_date, status) VALUES (?, ?, ?, ?, ?, ?)",
        orders_data,
    )

    conn.commit()
    conn.close()

    print(f"  数据库已初始化: {db_path}")
    print(f"  - 用户表: {len(users_data)} 条记录")
    print(f"  - 产品表: {len(products_data)} 条记录")
    print(f"  - 订单表: {len(orders_data)} 条记录")


if __name__ == "__main__":
    init_database()
