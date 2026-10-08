from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required
)
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import re

app = Flask(__name__)

app.config["JWT_SECRET_KEY"] = "library-secret-key"

CORS(app)

jwt = JWTManager(app)

DATABASE = "library.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            isbn TEXT UNIQUE NOT NULL,
            category TEXT NOT NULL,
            available INTEGER DEFAULT 1
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS members (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS issued_books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            issue_date TEXT DEFAULT CURRENT_DATE,
            return_date TEXT,
            FOREIGN KEY(book_id) REFERENCES books(id),
            FOREIGN KEY(member_id) REFERENCES members(id)
        )
    """)

    conn.commit()
    conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({
            "message": "Username and password are required"
        }), 400

    if len(password) < 6:
        return jsonify({
            "message": "Password must contain at least 6 characters"
        }), 400

    hashed_password = generate_password_hash(password)

    try:
        conn = get_db()

        conn.execute(
            "INSERT INTO users (username, password) VALUES (?, ?)",
            (username, hashed_password)
        )

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Registration successful"
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "message": "Username already exists"
        }), 409


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()

    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    conn.close()

    if not user or not check_password_hash(
        user["password"], password
    ):
        return jsonify({
            "message": "Invalid username or password"
        }), 401

    token = create_access_token(identity=str(user["id"]))

    return jsonify({
        "message": "Login successful",
        "token": token
    })


@app.route("/api/books", methods=["GET"])
def get_books():
    search = request.args.get("search", "")

    conn = get_db()

    books = conn.execute("""
        SELECT * FROM books
        WHERE title LIKE ?
        OR author LIKE ?
        OR isbn LIKE ?
        OR category LIKE ?
        ORDER BY id DESC
    """, (
        f"%{search}%",
        f"%{search}%",
        f"%{search}%",
        f"%{search}%"
    )).fetchall()

    conn.close()

    return jsonify([dict(book) for book in books])


@app.route("/api/books", methods=["POST"])
@jwt_required()
def add_book():
    data = request.get_json()

    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    isbn = data.get("isbn", "").strip()
    category = data.get("category", "").strip()

    if not title or not author or not isbn or not category:
        return jsonify({
            "message": "All book fields are required"
        }), 400

    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO books
            (title, author, isbn, category, available)
            VALUES (?, ?, ?, ?, 1)
        """, (title, author, isbn, category))

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Book added successfully"
        }), 201

    except sqlite3.IntegrityError:
        conn.close()

        return jsonify({
            "message": "ISBN already exists"
        }), 409


@app.route("/api/books/<int:book_id>", methods=["PUT"])
@jwt_required()
def update_book(book_id):
    data = request.get_json()

    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    category = data.get("category", "").strip()

    if not title or not author or not category:
        return jsonify({
            "message": "Required fields are missing"
        }), 400

    conn = get_db()

    cursor = conn.execute("""
        UPDATE books
        SET title = ?, author = ?, category = ?
        WHERE id = ?
    """, (title, author, category, book_id))

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        return jsonify({
            "message": "Book not found"
        }), 404

    return jsonify({
        "message": "Book updated successfully"
    })


@app.route("/api/books/<int:book_id>", methods=["DELETE"])
@jwt_required()
def delete_book(book_id):
    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    if not book:
        conn.close()

        return jsonify({
            "message": "Book not found"
        }), 404

    if book["available"] == 0:
        conn.close()

        return jsonify({
            "message": "Issued book cannot be deleted"
        }), 400

    conn.execute(
        "DELETE FROM books WHERE id = ?",
        (book_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Book deleted successfully"
    })


@app.route("/api/members", methods=["GET"])
def get_members():
    conn = get_db()

    members = conn.execute(
        "SELECT * FROM members ORDER BY id DESC"
    ).fetchall()

    conn.close()

    return jsonify([dict(member) for member in members])


@app.route("/api/members", methods=["POST"])
@jwt_required()
def add_member():
    data = request.get_json()

    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()

    if not name or not email:
        return jsonify({
            "message": "Name and email are required"
        }), 400

    if not re.match(
        r"^[^@\s]+@[^@\s]+\.[^@\s]+$",
        email
    ):
        return jsonify({
            "message": "Invalid email"
        }), 400

    conn = get_db()

    try:
        conn.execute("""
            INSERT INTO members
            (name, email, phone)
            VALUES (?, ?, ?)
        """, (name, email, phone))

        conn.commit()
        conn.close()

        return jsonify({
            "message": "Member added successfully"
        }), 201

    except sqlite3.IntegrityError:
        conn.close()

        return jsonify({
            "message": "Email already registered"
        }), 409


@app.route("/api/issue", methods=["POST"])
@jwt_required()
def issue_book():
    data = request.get_json()

    book_id = data.get("book_id")
    member_id = data.get("member_id")

    conn = get_db()

    book = conn.execute(
        "SELECT * FROM books WHERE id = ?",
        (book_id,)
    ).fetchone()

    member = conn.execute(
        "SELECT * FROM members WHERE id = ?",
        (member_id,)
    ).fetchone()

    if not book:
        conn.close()

        return jsonify({
            "message": "Book not found"
        }), 404

    if not member:
        conn.close()

        return jsonify({
            "message": "Member not found"
        }), 404

    if book["available"] == 0:
        conn.close()

        return jsonify({
            "message": "Book is already issued"
        }), 400

    conn.execute("""
        INSERT INTO issued_books
        (book_id, member_id)
        VALUES (?, ?)
    """, (book_id, member_id))

    conn.execute(
        "UPDATE books SET available = 0 WHERE id = ?",
        (book_id,)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Book issued successfully"
    })


@app.route("/api/return/<int:issue_id>", methods=["PUT"])
@jwt_required()
def return_book(issue_id):
    conn = get_db()

    issue = conn.execute(
        """
        SELECT * FROM issued_books
        WHERE id = ? AND return_date IS NULL
        """,
        (issue_id,)
    ).fetchone()

    if not issue:
        conn.close()

        return jsonify({
            "message": "Active issue record not found"
        }), 404

    conn.execute("""
        UPDATE issued_books
        SET return_date = CURRENT_DATE
        WHERE id = ?
    """, (issue_id,))

    conn.execute(
        "UPDATE books SET available = 1 WHERE id = ?",
        (issue["book_id"],)
    )

    conn.commit()
    conn.close()

    return jsonify({
        "message": "Book returned successfully"
    })


@app.route("/api/issues", methods=["GET"])
def get_issues():
    conn = get_db()

    issues = conn.execute("""
        SELECT
            issued_books.id,
            books.title,
            members.name,
            issued_books.issue_date,
            issued_books.return_date
        FROM issued_books
        JOIN books
        ON issued_books.book_id = books.id
        JOIN members
        ON issued_books.member_id = members.id
        ORDER BY issued_books.id DESC
    """).fetchall()

    conn.close()

    return jsonify([dict(issue) for issue in issues])


if __name__ == "__main__":
    init_db()
    app.run(debug=True)