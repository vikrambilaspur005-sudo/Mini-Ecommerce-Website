from flask import Flask, render_template, request, redirect, session
import sqlite3, os, random
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "secret123"

UPLOAD_FOLDER = "static/images"
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


# ---------------- DATABASE INIT ----------------
def init_db():
    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    # PRODUCTS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        price INTEGER,
        image TEXT,
        category TEXT
    )
    """)

    # CART TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS cart(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        product_id INTEGER,
        name TEXT,
        price INTEGER
    )
    """)

    # ORDERS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        name TEXT,
        price INTEGER,
        image TEXT,
        payment_method TEXT
    )
    """)

    # USERS TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT,
        email TEXT
    )
    """)

    # OTP TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS otp(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        otp TEXT
    )
    """)

    # INVOICE TABLE
    cur.execute("""
    CREATE TABLE IF NOT EXISTS invoice(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        product_name TEXT,
        price INTEGER,
        payment_method TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form.get('email', '')

        conn = sqlite3.connect("store.db")
        cur = conn.cursor()

        cur.execute("SELECT * FROM users WHERE username=?", (username,))
        existing_user = cur.fetchone()

        if existing_user:
            conn.close()
            return "Username already exists!"

        cur.execute(
            "INSERT INTO users(username, password, email) VALUES (?, ?, ?)",
            (username, password, email)
        )

        conn.commit()
        conn.close()

        return redirect('/login')

    return render_template("signup.html")


# ---------------- OTP LOGIN SEND ----------------
@app.route('/send_otp', methods=['POST'])
def send_otp():
    username = request.form['username']

    otp_code = str(random.randint(1000, 9999))

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM otp WHERE username=?", (username,))
    cur.execute(
        "INSERT INTO otp(username, otp) VALUES (?, ?)",
        (username, otp_code)
    )

    conn.commit()
    conn.close()

    return f"Your OTP is: {otp_code}"


# ---------------- OTP VERIFY ----------------
@app.route('/verify_otp', methods=['POST'])
def verify_otp():
    username = request.form['username']
    otp = request.form['otp']

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM otp WHERE username=? AND otp=?",
        (username, otp)
    )

    user = cur.fetchone()
    conn.close()

    if user:
        session['user'] = username
        return redirect('/')
    else:
        return "Invalid OTP"


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # ADMIN LOGIN
        if username == "admin" and password == "123":
            session['user'] = username
            return redirect('/admin')

        conn = sqlite3.connect("store.db")
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM users WHERE username=? AND password=?",
            (username, password)
        )

        user = cur.fetchone()

        conn.close()

        if user:
            session['user'] = username
            return redirect('/')
        else:
            return "Invalid Username or Password"

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/login')


# ---------------- HOME + SEARCH + CATEGORY ----------------
@app.route('/', methods=['GET', 'POST'])
def home():
    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    search = request.form.get('search', '')
    category = request.args.get('category', '')

    if search:
        cur.execute(
            "SELECT * FROM products WHERE name LIKE ?",
            ('%' + search + '%',)
        )

    elif category:
        cur.execute(
            "SELECT * FROM products WHERE category=?",
            (category,)
        )

    else:
        cur.execute("SELECT * FROM products")

    products = cur.fetchall()

    conn.close()

    return render_template("index.html", products=products)


# ---------------- ADMIN PANEL ----------------
@app.route('/admin')
def admin():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM products")
    products = cur.fetchall()

    conn.close()

    return render_template("admin.html", products=products)


# ---------------- ADD PRODUCT ----------------
@app.route('/add_product', methods=['POST'])
def add_product():
    if 'user' not in session:
        return redirect('/login')

    name = request.form['name']
    price = request.form['price']
    category = request.form.get('category', 'General')
    image = request.files['image']

    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    filename = secure_filename(image.filename)
    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO products(name, price, image, category)
    VALUES (?, ?, ?, ?)
    """, (name, price, filename, category))

    conn.commit()
    conn.close()

    return redirect('/admin')


# ---------------- DELETE PRODUCT ----------------
@app.route('/delete_product/<int:id>')
def delete_product(id):
    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM products WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/admin')


# ---------------- ADD TO CART ----------------
@app.route('/add_to_cart/<int:id>')
def add_to_cart(id):
    if 'user' not in session:
        return redirect('/login')

    username = session['user']

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE id=?", (id,))
    product = cur.fetchone()

    if product:
        cur.execute("""
        INSERT INTO cart(username, product_id, name, price)
        VALUES (?, ?, ?, ?)
        """, (username, product[0], product[1], product[2]))

    conn.commit()
    conn.close()

    return redirect('/cart')


# ---------------- CART ----------------
@app.route('/cart')
def cart():
    if 'user' not in session:
        return redirect('/login')

    username = session['user']

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM cart WHERE username=?", (username,))
    cart_items = cur.fetchall()

    conn.close()

    return render_template("cart.html", cart=cart_items)


# ---------------- REMOVE CART ----------------
@app.route('/remove/<int:id>')
def remove(id):
    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute("DELETE FROM cart WHERE id=?", (id,))

    conn.commit()
    conn.close()

    return redirect('/cart')


# ---------------- PAYMENT PAGE ----------------
@app.route('/payment/<int:id>')
def payment(id):
    return render_template("payment.html", id=id)


# ---------------- CONFIRM ORDER + INVOICE ----------------
@app.route('/confirm_order/<int:id>', methods=['POST'])
def confirm_order(id):
    if 'user' not in session:
        return redirect('/login')

    username = session['user']
    payment_method = request.form.get('payment_method', 'COD')

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM products WHERE id=?", (id,))
    product = cur.fetchone()

    if product:
        # Insert Order
        cur.execute("""
        INSERT INTO orders(username, name, price, image, payment_method)
        VALUES (?, ?, ?, ?, ?)
        """, (username, product[1], product[2], product[3], payment_method))

        # Insert Invoice
        cur.execute("""
        INSERT INTO invoice(username, product_name, price, payment_method)
        VALUES (?, ?, ?, ?)
        """, (username, product[1], product[2], payment_method))

        # Remove from cart
        cur.execute(
            "DELETE FROM cart WHERE username=? AND product_id=?",
            (username, id)
        )

    conn.commit()
    conn.close()

    return redirect('/dashboard')


# ---------------- BUY ALL ----------------
@app.route('/buy_all')
def buy_all():

    if 'user' not in session:
        return redirect('/login')

    username = session['user']

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM cart WHERE username=?",
        (username,)
    )

    items = cur.fetchall()

    for item in items:

        product_id = item[2]

        cur.execute(
            "SELECT * FROM products WHERE id=?",
            (product_id,)
        )

        p = cur.fetchone()

        if p:
            cur.execute("""
            INSERT INTO orders
            (username,name,price,image,payment_method)
            VALUES(?,?,?,?,?)
            """,
            (
                username,
                p[1],
                p[2],
                p[3],
                "COD"
            ))

            cur.execute("""
            INSERT INTO invoice
            (username,product_name,price,payment_method)
            VALUES(?,?,?,?)
            """,
            (
                username,
                p[1],
                p[2],
                "COD"
            ))

    cur.execute(
        "DELETE FROM cart WHERE username=?",
        (username,)
    )

    conn.commit()
    conn.close()

    return redirect('/dashboard')

# ---------------- BUY DIRECT ----------------
@app.route('/buy/<int:id>')
def buy(id):
    return redirect(f'/payment/{id}')


# ---------------- DASHBOARD / ORDER HISTORY ----------------
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/login')

    username = session['user']

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute("SELECT * FROM orders WHERE username=?", (username,))
    orders = cur.fetchall()

    conn.close()

    return render_template("dashboard.html", orders=orders)


# ---------------- PROFILE ----------------
@app.route('/profile')
def profile():
    if 'user' not in session:
        return redirect('/login')

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT username, email FROM users WHERE username=?",
        (session['user'],)
    )

    user = cur.fetchone()

    conn.close()

    return render_template("profile.html", user=user)


# ---------------- INVOICE PAGE ----------------
@app.route('/invoice')
def invoice():
    if 'user' not in session:
        return redirect('/login')

    username = session['user']

    conn = sqlite3.connect("store.db")
    cur = conn.cursor()

    cur.execute(
        "SELECT * FROM invoice WHERE username=?",
        (username,)
    )

    bills = cur.fetchall()

    conn.close()

    return render_template("invoice.html", bills=bills)


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)