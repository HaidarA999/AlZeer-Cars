from flask import Flask, request, jsonify, send_from_directory, session, redirect
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import sqlite3
import json
import secrets
from datetime import datetime, timedelta
import os

app = Flask(__name__)

# مفتاح تشفير الجلسات (الـ session). بالإنتاج (production) لازم تحطي
# متغير بيئة SECRET_KEY ثابت، لأنه لو ما ثبتناه، كل ما يعاد تشغيل
# السيرفر بيتغير المفتاح وبينفصل كل المسجلين دخول.
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "database.db")

# بيانات الأدمن الافتراضي، بتنزرع بقاعدة البيانات أول مرة بس
# (لو ما كان في مستخدمين أصلاً). بعدين تقدري تغيري كلمة السر
# أو تضيفي مستخدمين جداد من لوحة التحكم نفسها.
DEFAULT_ADMIN_USERNAME = "haidara"
DEFAULT_ADMIN_PASSWORD = "AlMasre2026"


# =========================================================
# SQLite
# =========================================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_db()

    conn.executescript("""
    CREATE TABLE IF NOT EXISTS cars (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        year INTEGER NOT NULL,
        price REAL NOT NULL,
        km INTEGER DEFAULT 0,
        status TEXT DEFAULT 'available',
        image TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS auctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        start_price REAL NOT NULL,
        current_bid REAL NOT NULL,
        increment REAL NOT NULL,
        image TEXT DEFAULT '',
        end_time TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS bids (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        auction_id INTEGER NOT NULL,
        bidder_name TEXT DEFAULT 'مستخدم',
        bidder_id TEXT DEFAULT '',
        amount REAL NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (auction_id) REFERENCES auctions(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS activities (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()

    # أول تشغيل: لو ما في ولا مستخدم، منزرع الأدمن الافتراضي
    existing = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if existing == 0:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (DEFAULT_ADMIN_USERNAME, generate_password_hash(DEFAULT_ADMIN_PASSWORD))
        )
        conn.commit()

    conn.close()


def add_activity(conn, message):
    conn.execute(
        "INSERT INTO activities (message) VALUES (?)",
        (message,)
    )


# =========================================================
# Migration: بنضيف أعمدة جديدة لجدول cars لو ناقصة
# (هيك ما منخسر البيانات القديمة الموجودة بقاعدة البيانات)
# =========================================================

CAR_NEW_COLUMNS = {
    "fuel": "TEXT DEFAULT 'بنزين'",
    "transmission": "TEXT DEFAULT 'أوتوماتيك'",
    "branch": "TEXT DEFAULT 'طرطوس'",
    "condition_status": "TEXT DEFAULT 'مستعملة'",
    "description": "TEXT DEFAULT ''",
    "images": "TEXT DEFAULT '[]'",
    "featured": "INTEGER DEFAULT 0",
    "featured_at": "TEXT DEFAULT NULL"
}


def migrate_db():
    conn = get_db()

    existing_columns = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(cars)")
    }

    for column, definition in CAR_NEW_COLUMNS.items():
        if column not in existing_columns:
            conn.execute(
                f"ALTER TABLE cars ADD COLUMN {column} {definition}"
            )

    conn.commit()
    conn.close()


FUEL_TYPES = ("بنزين", "كهربائية", "هايبرد")
TRANSMISSION_TYPES = ("أوتوماتيك", "يدوي")
BRANCHES = ("طرطوس", "حمص")
CONDITIONS = ("جديدة", "مستعملة")

MAX_FEATURED_CARS = 6


def car_to_dict(row):
    """
    بنحول صف السيارة من SQLite لقاموس بايثون عادي،
    وبنفك تشفير JSON لمصفوفة الصور، وبنجهز اسم condition
    (بدل condition_status) حتى يبقى متوافق مع الفرونت إند.
    """
    car = dict(row)

    try:
        car["images"] = json.loads(car.get("images") or "[]")
    except (TypeError, ValueError):
        car["images"] = []

    car["condition"] = car.get("condition_status") or "مستعملة"
    car["featured"] = bool(car.get("featured"))

    return car


# =========================================================
# حماية الدخول (Auth)
# =========================================================

def _current_user_still_valid():
    """بيتأكد إنه الـ user_id بالجلسة لسا موجود فعليًا بقاعدة البيانات
    (يعني لو حدا حذف حساب هالمستخدم، جلسته القديمة بتنفصل فورًا
    ولا تضل شغالة لحد ما تنتهي مدتها)."""
    user_id = session.get("user_id")
    if user_id is None:
        return False
    conn = get_db()
    user = conn.execute(
        "SELECT id FROM users WHERE id = ?", (user_id,)
    ).fetchone()
    conn.close()
    return user is not None


def login_required_page(f):
    """يحمي صفحات HTML: لو مو مسجل دخول (أو حسابه انحذف)، بيرجعه عصفحة تسجيل الدخول."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _current_user_still_valid():
            session.clear()
            return redirect("/Login.html")
        return f(*args, **kwargs)
    return wrapper


def login_required_api(f):
    """يحمي الـ API: لو مو مسجل دخول (أو حسابه انحذف)، بيرجع 401 بدل تنفيذ الطلب."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not _current_user_still_valid():
            session.clear()
            return jsonify({
                "success": False,
                "error": "لازم تسجلي دخول الأول"
            }), 401
        return f(*args, **kwargs)
    return wrapper


@app.post("/api/login")
def login():
    data = request.get_json(force=True, silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    conn = get_db()
    user = conn.execute(
        "SELECT * FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()

    if user and check_password_hash(user["password_hash"], password):
        session.clear()
        session["user_id"] = user["id"]
        session["username"] = user["username"]
        session.permanent = True
        return jsonify({"success": True, "username": user["username"]})

    return jsonify({
        "success": False,
        "error": "اسم المستخدم أو كلمة السر غلط"
    }), 401


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"success": True})


@app.get("/api/me")
def me():
    if "user_id" not in session:
        return jsonify({"logged_in": False}), 401
    return jsonify({"logged_in": True, "username": session.get("username")})


# --------- إدارة المستخدمين (مين فيه يفوت عاللوحة) ---------

@app.get("/api/users")
@login_required_api
def list_users():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, created_at FROM users ORDER BY created_at"
    ).fetchall()
    conn.close()
    return jsonify({"success": True, "users": [dict(r) for r in rows]})


@app.post("/api/users")
@login_required_api
def add_user():
    data = request.get_json(force=True, silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or len(password) < 6:
        return jsonify({
            "success": False,
            "error": "لازم اسم مستخدم وكلمة سر 6 أحرف عالأقل"
        }), 400

    conn = get_db()
    try:
        conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, generate_password_hash(password))
        )
        add_activity(conn, f"تمت إضافة مستخدم جديد للوحة التحكم: {username}")
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return jsonify({
            "success": False,
            "error": "في مستخدم فيه هيدا الاسم أصلاً"
        }), 400
    conn.close()
    return jsonify({"success": True})


@app.delete("/api/users/<int:user_id>")
@login_required_api
def delete_user(user_id):
    if session.get("user_id") == user_id:
        return jsonify({
            "success": False,
            "error": "ما فيك تحذفي حسابك انتي وانتي مسجلة دخول فيه"
        }), 400

    conn = get_db()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({"success": True})


# =========================================================
# HTML pages
# =========================================================

@app.route("/")
def home():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/index.html")
def index_page():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/Cars.html")
def cars_page():
    return send_from_directory(BASE_DIR, "Cars.html")


@app.route("/Auctions.html")
def auctions_page():
    return send_from_directory(BASE_DIR, "Auctions.html")


@app.route("/Dashboard.html")
@login_required_page
def dashboard_page():
    return send_from_directory(BASE_DIR, "Dashboard.html")


@app.route("/Login.html")
def login_page():
    return send_from_directory(BASE_DIR, "Login.html")


@app.route("/AboutUs.html")
def about_page():
    return send_from_directory(BASE_DIR, "AboutUs.html")


# يسمح أيضاً بتحميل الصور/css/js إذا أضفتهم لاحقاً بنفس المشروع
@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(BASE_DIR, filename)


# =========================================================
# Dashboard API
# =========================================================

@app.get("/api/stats")
@login_required_api
def stats():
    conn = get_db()

    cars_count = conn.execute(
        "SELECT COUNT(*) FROM cars"
    ).fetchone()[0]

    active_auctions = conn.execute(
        "SELECT COUNT(*) FROM auctions WHERE status = 'active'"
    ).fetchone()[0]

    total_bids = conn.execute(
        "SELECT COUNT(*) FROM bids"
    ).fetchone()[0]

    highest_bid = conn.execute(
        "SELECT COALESCE(MAX(current_bid), 0) FROM auctions"
    ).fetchone()[0]

    gasoline_count = conn.execute(
        "SELECT COUNT(*) FROM cars WHERE fuel = 'بنزين'"
    ).fetchone()[0]

    electric_count = conn.execute(
        "SELECT COUNT(*) FROM cars WHERE fuel = 'كهربائية'"
    ).fetchone()[0]

    hybrid_count = conn.execute(
        "SELECT COUNT(*) FROM cars WHERE fuel = 'هايبرد'"
    ).fetchone()[0]

    featured_count = conn.execute(
        "SELECT COUNT(*) FROM cars WHERE featured = 1"
    ).fetchone()[0]

    conn.close()

    return jsonify({
        "success": True,
        "cars": cars_count,
        "auctions": active_auctions,
        "bids": total_bids,
        "highest_bid": highest_bid,
        "gasoline_count": gasoline_count,
        "electric_count": electric_count,
        "hybrid_count": hybrid_count,
        "featured_count": featured_count
    })


@app.get("/api/activities")
@login_required_api
def activities():
    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM activities
        ORDER BY id DESC
        LIMIT 20
    """).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "activities": [dict(row) for row in rows]
    })


# =========================================================
# Cars API
# =========================================================

@app.get("/api/cars")
def get_cars():
    search = request.args.get("search", "").strip()
    featured_only = request.args.get("featured", "").strip() == "1"

    conn = get_db()

    if featured_only:
        rows = conn.execute("""
            SELECT *
            FROM cars
            WHERE featured = 1
            ORDER BY featured_at DESC, id DESC
        """).fetchall()
    elif search:
        rows = conn.execute("""
            SELECT *
            FROM cars
            WHERE name LIKE ?
            ORDER BY id DESC
        """, (f"%{search}%",)).fetchall()
    else:
        rows = conn.execute("""
            SELECT *
            FROM cars
            ORDER BY id DESC
        """).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "cars": [car_to_dict(row) for row in rows]
    })


@app.get("/api/cars/<int:car_id>")
def get_car(car_id):
    conn = get_db()

    car = conn.execute(
        "SELECT * FROM cars WHERE id = ?",
        (car_id,)
    ).fetchone()

    conn.close()

    if not car:
        return jsonify({
            "success": False,
            "error": "السيارة غير موجودة"
        }), 404

    return jsonify({
        "success": True,
        "car": car_to_dict(car)
    })


@app.post("/api/cars")
@login_required_api
def add_car():
    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()
    year = data.get("year")
    price = data.get("price")
    km = data.get("km", 0)
    status = data.get("status", "available")

    fuel = data.get("fuel", "بنزين")
    transmission = data.get("transmission", "أوتوماتيك")
    branch = data.get("branch", "طرطوس")
    condition_status = data.get(
        "condition",
        data.get("condition_status", "مستعملة")
    )
    description = str(data.get("description", "")).strip()

    images_raw = data.get("images", [])
    images = (
        [str(x).strip() for x in images_raw if str(x).strip()]
        if isinstance(images_raw, list) else []
    )[:6]

    image = images[0] if images else str(data.get("image", "")).strip()

    featured = bool(data.get("featured", False))

    if not name or year is None or price is None:
        return jsonify({
            "success": False,
            "error": "الاسم والسنة والسعر مطلوبين"
        }), 400

    if status not in ("available", "reserved", "sold"):
        return jsonify({
            "success": False,
            "error": "حالة السيارة غير صحيحة"
        }), 400

    if fuel not in FUEL_TYPES:
        return jsonify({
            "success": False,
            "error": "نوع الوقود غير صحيح"
        }), 400

    if transmission not in TRANSMISSION_TYPES:
        return jsonify({
            "success": False,
            "error": "ناقل الحركة غير صحيح"
        }), 400

    if branch not in BRANCHES:
        return jsonify({
            "success": False,
            "error": "الفرع غير صحيح"
        }), 400

    if condition_status not in CONDITIONS:
        return jsonify({
            "success": False,
            "error": "حالة السيارة (جديدة/مستعملة) غير صحيحة"
        }), 400

    try:
        year = int(year)
        price = float(price)
        km = int(km or 0)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "تأكد من القيم الرقمية"
        }), 400

    conn = get_db()

    if featured:
        current_featured = conn.execute(
            "SELECT COUNT(*) FROM cars WHERE featured = 1"
        ).fetchone()[0]

        if current_featured >= MAX_FEATURED_CARS:
            conn.close()

            return jsonify({
                "success": False,
                "error": (
                    f"في {MAX_FEATURED_CARS} سيارات مميزة مسبقاً، "
                    "شيل وحدة الأول قبل ما تضيف جديدة"
                )
            }), 400

    featured_at = datetime.now().isoformat() if featured else None

    cursor = conn.execute("""
        INSERT INTO cars (
            name,
            year,
            price,
            km,
            status,
            image,
            fuel,
            transmission,
            branch,
            condition_status,
            description,
            images,
            featured,
            featured_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        name,
        year,
        price,
        km,
        status,
        image,
        fuel,
        transmission,
        branch,
        condition_status,
        description,
        json.dumps(images, ensure_ascii=False),
        1 if featured else 0,
        featured_at
    ))

    car_id = cursor.lastrowid

    add_activity(
        conn,
        f"تمت إضافة سيارة جديدة: {name}"
    )

    conn.commit()

    car = conn.execute(
        "SELECT * FROM cars WHERE id = ?",
        (car_id,)
    ).fetchone()

    conn.close()

    return jsonify({
        "success": True,
        "car": car_to_dict(car)
    })


@app.put("/api/cars/<int:car_id>")
@login_required_api
def edit_car(car_id):
    data = request.get_json() or {}

    conn = get_db()

    old_car = conn.execute(
        "SELECT * FROM cars WHERE id = ?",
        (car_id,)
    ).fetchone()

    if not old_car:
        conn.close()

        return jsonify({
            "success": False,
            "error": "السيارة غير موجودة"
        }), 404

    old_car = car_to_dict(old_car)

    name = data.get("name", old_car["name"])
    year = data.get("year", old_car["year"])
    price = data.get("price", old_car["price"])
    km = data.get("km", old_car["km"])
    status = data.get("status", old_car["status"])

    fuel = data.get("fuel", old_car["fuel"])
    transmission = data.get("transmission", old_car["transmission"])
    branch = data.get("branch", old_car["branch"])
    condition_status = data.get(
        "condition",
        data.get("condition_status", old_car["condition"])
    )
    description = data.get("description", old_car["description"])

    if "images" in data and isinstance(data["images"], list):
        images = [
            str(x).strip() for x in data["images"] if str(x).strip()
        ][:6]
    else:
        images = old_car["images"]

    image = images[0] if images else data.get("image", old_car["image"])

    featured = bool(data.get("featured", old_car["featured"]))

    if status not in ("available", "reserved", "sold"):
        conn.close()
        return jsonify({
            "success": False,
            "error": "حالة السيارة غير صحيحة"
        }), 400

    if fuel not in FUEL_TYPES:
        conn.close()
        return jsonify({
            "success": False,
            "error": "نوع الوقود غير صحيح"
        }), 400

    if transmission not in TRANSMISSION_TYPES:
        conn.close()
        return jsonify({
            "success": False,
            "error": "ناقل الحركة غير صحيح"
        }), 400

    if branch not in BRANCHES:
        conn.close()
        return jsonify({
            "success": False,
            "error": "الفرع غير صحيح"
        }), 400

    if condition_status not in CONDITIONS:
        conn.close()
        return jsonify({
            "success": False,
            "error": "حالة السيارة (جديدة/مستعملة) غير صحيحة"
        }), 400

    try:
        year = int(year)
        price = float(price)
        km = int(km or 0)
    except (ValueError, TypeError):
        conn.close()
        return jsonify({
            "success": False,
            "error": "تأكد من القيم الرقمية"
        }), 400

    if featured and not old_car["featured"]:
        current_featured = conn.execute(
            "SELECT COUNT(*) FROM cars WHERE featured = 1 AND id != ?",
            (car_id,)
        ).fetchone()[0]

        if current_featured >= MAX_FEATURED_CARS:
            conn.close()

            return jsonify({
                "success": False,
                "error": (
                    f"في {MAX_FEATURED_CARS} سيارات مميزة مسبقاً، "
                    "شيل وحدة الأول قبل ما تضيف جديدة"
                )
            }), 400

    if featured and not old_car["featured"]:
        featured_at = datetime.now().isoformat()
    elif not featured:
        featured_at = None
    else:
        featured_at = old_car.get("featured_at")

    conn.execute("""
        UPDATE cars
        SET
            name = ?,
            year = ?,
            price = ?,
            km = ?,
            status = ?,
            image = ?,
            fuel = ?,
            transmission = ?,
            branch = ?,
            condition_status = ?,
            description = ?,
            images = ?,
            featured = ?,
            featured_at = ?
        WHERE id = ?
    """, (
        name,
        year,
        price,
        km,
        status,
        image,
        fuel,
        transmission,
        branch,
        condition_status,
        description,
        json.dumps(images, ensure_ascii=False),
        1 if featured else 0,
        featured_at,
        car_id
    ))

    add_activity(
        conn,
        f"تم تعديل السيارة: {name}"
    )

    conn.commit()

    car = conn.execute(
        "SELECT * FROM cars WHERE id = ?",
        (car_id,)
    ).fetchone()

    conn.close()

    return jsonify({
        "success": True,
        "car": car_to_dict(car)
    })


@app.delete("/api/cars/<int:car_id>")
@login_required_api
def delete_car(car_id):
    conn = get_db()

    car = conn.execute(
        "SELECT * FROM cars WHERE id = ?",
        (car_id,)
    ).fetchone()

    if not car:
        conn.close()

        return jsonify({
            "success": False,
            "error": "السيارة غير موجودة"
        }), 404

    conn.execute(
        "DELETE FROM cars WHERE id = ?",
        (car_id,)
    )

    add_activity(
        conn,
        f"تم حذف السيارة: {car['name']}"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# Auctions API
# =========================================================

@app.get("/api/auctions")
def get_auctions():
    conn = get_db()

    now = datetime.now().isoformat()

    conn.execute("""
        UPDATE auctions
        SET status = 'ended'
        WHERE status = 'active'
        AND end_time <= ?
    """, (now,))

    conn.commit()

    rows = conn.execute("""
        SELECT *
        FROM auctions
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "auctions": [dict(row) for row in rows]
    })


@app.get("/api/auctions/<int:auction_id>")
def get_auction(auction_id):
    conn = get_db()

    auction = conn.execute(
        "SELECT * FROM auctions WHERE id = ?",
        (auction_id,)
    ).fetchone()

    if not auction:
        conn.close()

        return jsonify({
            "success": False,
            "error": "المزاد غير موجود"
        }), 404

    bids = conn.execute("""
        SELECT *
        FROM bids
        WHERE auction_id = ?
        ORDER BY amount DESC
    """, (auction_id,)).fetchall()

    conn.close()

    return jsonify({
        "success": True,
        "auction": dict(auction),
        "bids": [dict(row) for row in bids]
    })


@app.post("/api/auctions")
@login_required_api
def add_auction():
    data = request.get_json() or {}

    name = str(data.get("name", "")).strip()
    start_price = data.get(
        "start_price",
        data.get("startPrice")
    )
    increment = data.get("increment")
    duration = data.get(
        "duration",
        data.get("duration_hours")
    )
    image = data.get("image", "")

    if (
        not name
        or start_price is None
        or increment is None
        or duration is None
    ):
        return jsonify({
            "success": False,
            "error": "بيانات المزاد ناقصة"
        }), 400

    try:
        start_price = float(start_price)
        increment = float(increment)
        duration = float(duration)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "تأكد من القيم الرقمية"
        }), 400

    end_time = (
        datetime.now()
        + timedelta(hours=duration)
    ).isoformat()

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO auctions (
            name,
            start_price,
            current_bid,
            increment,
            image,
            end_time,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, 'active')
    """, (
        name,
        start_price,
        start_price,
        increment,
        image,
        end_time
    ))

    auction_id = cursor.lastrowid

    add_activity(
        conn,
        f"تم إنشاء مزاد جديد: {name}"
    )

    conn.commit()

    auction = conn.execute(
        "SELECT * FROM auctions WHERE id = ?",
        (auction_id,)
    ).fetchone()

    conn.close()

    return jsonify({
        "success": True,
        "auction": dict(auction)
    })


@app.put("/api/auctions/<int:auction_id>")
@login_required_api
def edit_auction(auction_id):
    data = request.get_json() or {}

    conn = get_db()

    auction = conn.execute(
        "SELECT * FROM auctions WHERE id = ?",
        (auction_id,)
    ).fetchone()

    if not auction:
        conn.close()

        return jsonify({
            "success": False,
            "error": "المزاد غير موجود"
        }), 404

    auction = dict(auction)

    name = data.get(
        "name",
        auction["name"]
    )

    start_price = data.get(
        "start_price",
        auction["start_price"]
    )

    increment = data.get(
        "increment",
        auction["increment"]
    )

    image = data.get(
        "image",
        auction["image"]
    )

    status = data.get(
        "status",
        auction["status"]
    )

    end_time = auction["end_time"]

    if "duration" in data or "duration_hours" in data:
        duration = float(
            data.get(
                "duration",
                data.get("duration_hours")
            )
        )

        end_time = (
            datetime.now()
            + timedelta(hours=duration)
        ).isoformat()

    conn.execute("""
        UPDATE auctions
        SET
            name = ?,
            start_price = ?,
            increment = ?,
            image = ?,
            end_time = ?,
            status = ?
        WHERE id = ?
    """, (
        name,
        start_price,
        increment,
        image,
        end_time,
        status,
        auction_id
    ))

    add_activity(
        conn,
        f"تم تعديل المزاد: {name}"
    )

    conn.commit()

    updated = conn.execute(
        "SELECT * FROM auctions WHERE id = ?",
        (auction_id,)
    ).fetchone()

    conn.close()

    return jsonify({
        "success": True,
        "auction": dict(updated)
    })


@app.delete("/api/auctions/<int:auction_id>")
@login_required_api
def delete_auction(auction_id):
    conn = get_db()

    auction = conn.execute(
        "SELECT * FROM auctions WHERE id = ?",
        (auction_id,)
    ).fetchone()

    if not auction:
        conn.close()

        return jsonify({
            "success": False,
            "error": "المزاد غير موجود"
        }), 404

    conn.execute(
        "DELETE FROM auctions WHERE id = ?",
        (auction_id,)
    )

    add_activity(
        conn,
        f"تم حذف المزاد: {auction['name']}"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True
    })


# =========================================================
# Bids API
# =========================================================

@app.post("/api/auctions/<int:auction_id>/bid")
def make_bid(auction_id):
    data = request.get_json() or {}

    amount = data.get("amount")

    bidder_name = str(
        data.get("bidder_name", "مستخدم")
    )

    bidder_id = str(
        data.get("bidder_id", "")
    )

    if amount is None:
        return jsonify({
            "success": False,
            "error": "قيمة المزايدة مطلوبة"
        }), 400

    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({
            "success": False,
            "error": "قيمة المزايدة غير صحيحة"
        }), 400

    conn = get_db()

    auction = conn.execute(
        "SELECT * FROM auctions WHERE id = ?",
        (auction_id,)
    ).fetchone()

    if not auction:
        conn.close()

        return jsonify({
            "success": False,
            "error": "المزاد غير موجود"
        }), 404

    if auction["status"] != "active":
        conn.close()

        return jsonify({
            "success": False,
            "error": "المزاد منتهي"
        }), 400

    minimum_bid = (
        float(auction["current_bid"])
        + float(auction["increment"])
    )

    if amount < minimum_bid:
        conn.close()

        return jsonify({
            "success": False,
            "error": "المزايدة أقل من الحد الأدنى",
            "minimum_bid": minimum_bid
        }), 400

    conn.execute("""
        INSERT INTO bids (
            auction_id,
            bidder_name,
            bidder_id,
            amount
        )
        VALUES (?, ?, ?, ?)
    """, (
        auction_id,
        bidder_name,
        bidder_id,
        amount
    ))

    conn.execute("""
        UPDATE auctions
        SET current_bid = ?
        WHERE id = ?
    """, (
        amount,
        auction_id
    ))

    add_activity(
        conn,
        f"مزايدة جديدة بقيمة {amount}$ على {auction['name']}"
    )

    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "current_bid": amount
    })


# =========================================================
# Start
# =========================================================

init_db()
migrate_db()

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True
    )
