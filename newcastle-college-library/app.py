from __future__ import annotations
import os, sqlite3
from datetime import date, timedelta
from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for, flash, g, abort

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.environ.get("LIBRARY_DATABASE", os.path.join(BASE_DIR, "library.db"))
app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-this-development-secret")

def connect_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def get_db():
    if "db" not in g:
        g.db = connect_db()
    return g.db

@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_db():
    db = connect_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author TEXT NOT NULL,
        isbn TEXT NOT NULL UNIQUE,
        genre TEXT NOT NULL,
        total_copies INTEGER NOT NULL DEFAULT 1 CHECK(total_copies >= 1),
        available_copies INTEGER NOT NULL DEFAULT 1 CHECK(available_copies >= 0),
        created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        member_code TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        email TEXT DEFAULT '',
        fines_pence INTEGER NOT NULL DEFAULT 0 CHECK(fines_pence >= 0)
    );
    CREATE TABLE IF NOT EXISTS loans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL REFERENCES books(id),
        member_id INTEGER NOT NULL REFERENCES members(id),
        borrowed_on TEXT NOT NULL,
        due_on TEXT NOT NULL,
        returned_on TEXT,
        fine_pence INTEGER NOT NULL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS waitlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        book_id INTEGER NOT NULL REFERENCES books(id),
        member_id INTEGER NOT NULL REFERENCES members(id),
        queued_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        status TEXT NOT NULL DEFAULT 'waiting',
        UNIQUE(book_id, member_id, status)
    );
    CREATE INDEX IF NOT EXISTS idx_books_title ON books(title COLLATE NOCASE);
    CREATE INDEX IF NOT EXISTS idx_books_author ON books(author COLLATE NOCASE);
    CREATE INDEX IF NOT EXISTS idx_books_genre ON books(genre COLLATE NOCASE);
    CREATE INDEX IF NOT EXISTS idx_books_isbn ON books(isbn);
    CREATE INDEX IF NOT EXISTS idx_loans_member_active ON loans(member_id, returned_on);
    CREATE INDEX IF NOT EXISTS idx_loans_book ON loans(book_id);
    CREATE INDEX IF NOT EXISTS idx_waitlist_book_status ON waitlist(book_id, status, id);
    """)
    db.commit()
    db.close()

# Seed a small, clearly labelled sample catalogue on first run.
def seed_demo_data():
    db = connect_db()
    if db.execute("SELECT COUNT(*) FROM books").fetchone()[0] == 0:
        books = [
            ("The Hobbit", "J.R.R. Tolkien", "9780261103344", "Fantasy", 3),
            ("1984", "George Orwell", "9780451524935", "Dystopian", 2),
            ("Pride and Prejudice", "Jane Austen", "9780141439518", "Classic", 2),
            ("The Great Gatsby", "F. Scott Fitzgerald", "9780743273565", "Classic", 2),
            ("A Brief History of Time", "Stephen Hawking", "9780553380163", "Science", 1),
            ("Clean Code", "Robert C. Martin", "9780132350884", "Computing", 2),
        ]
        db.executemany("INSERT INTO books(title,author,isbn,genre,total_copies,available_copies) VALUES(?,?,?,?,?,?)",
                       [(t,a,i,gen,c,c) for t,a,i,gen,c in books])
    if db.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 0:
        db.executemany("INSERT INTO members(member_code,name,email) VALUES(?,?,?)", [
            ("NC001", "Alex Morgan", "alex@example.com"),
            ("NC002", "Jamie Taylor", "jamie@example.com"),
            ("NC003", "Sam Patel", "sam@example.com"),
        ])
    db.commit()
    db.close()

def book_search(term="", field="all"):
    """Indexed exact ISBN lookup; indexed LIKE lookups for other fields."""
    db = get_db()
    allowed = {"title": "title", "author": "author", "isbn": "isbn", "genre": "genre"}
    if not term:
        return db.execute("SELECT * FROM books ORDER BY title COLLATE NOCASE").fetchall()
    if field == "isbn":
        return db.execute("SELECT * FROM books WHERE isbn = ?", (term.strip(),)).fetchall()
    if field in allowed:
        col = allowed[field]
        return db.execute(f"SELECT * FROM books WHERE {col} LIKE ? ORDER BY {col} COLLATE NOCASE", (f"%{term.strip()}%",)).fetchall()
    return db.execute("""SELECT * FROM books
        WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ? OR genre LIKE ?
        ORDER BY title COLLATE NOCASE""", tuple([f"%{term.strip()}%"]*4)).fetchall()

@app.route("/")
def index():
    db = get_db()
    stats = {
        "books": db.execute("SELECT COUNT(*) FROM books").fetchone()[0],
        "members": db.execute("SELECT COUNT(*) FROM members").fetchone()[0],
        "active_loans": db.execute("SELECT COUNT(*) FROM loans WHERE returned_on IS NULL").fetchone()[0],
        "waiting": db.execute("SELECT COUNT(*) FROM waitlist WHERE status='waiting'").fetchone()[0],
    }
    popular = db.execute("""SELECT b.title,b.author,COUNT(l.id) AS loans
        FROM books b LEFT JOIN loans l ON l.book_id=b.id
        GROUP BY b.id ORDER BY loans DESC,b.title COLLATE NOCASE LIMIT 5""").fetchall()
    return render_template("dashboard.html", stats=stats, popular=popular)

@app.route("/books")
def books():
    term = request.args.get("q", "").strip()
    field = request.args.get("field", "all")
    results = book_search(term, field)
    return render_template("books.html", books=results, q=term, field=field)

@app.route("/books/add", methods=["GET", "POST"])
def add_book():
    if request.method == "POST":
        title, author, isbn, genre = [request.form.get(x, "").strip() for x in ("title","author","isbn","genre")]
        try:
            copies = max(1, int(request.form.get("copies", "1")))
        except ValueError:
            copies = 1
        if not all([title, author, isbn, genre]):
            flash("Please complete all required book fields.", "error")
        else:
            try:
                get_db().execute("""INSERT INTO books(title,author,isbn,genre,total_copies,available_copies)
                    VALUES(?,?,?,?,?,?)""", (title,author,isbn,genre,copies,copies))
                get_db().commit()
                flash("Book added to the catalogue.", "success")
                return redirect(url_for("books"))
            except sqlite3.IntegrityError:
                flash("That ISBN already exists. ISBNs must be unique.", "error")
    return render_template("book_form.html")

@app.route("/books/<int:book_id>/edit", methods=["GET", "POST"])
def edit_book(book_id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if not book: abort(404)
    if request.method == "POST":
        title, author, isbn, genre = [request.form.get(x, "").strip() for x in ("title","author","isbn","genre")]
        try: total = max(1, int(request.form.get("copies", "1")))
        except ValueError: total = book["total_copies"]
        borrowed = book["total_copies"] - book["available_copies"]
        if total < borrowed:
            flash(f"Copies cannot be lower than the {borrowed} currently on loan.", "error")
        elif not all([title,author,isbn,genre]):
            flash("Please complete all required fields.", "error")
        else:
            try:
                db.execute("""UPDATE books SET title=?,author=?,isbn=?,genre=?,total_copies=?,available_copies=?
                    WHERE id=?""", (title,author,isbn,genre,total,total-borrowed,book_id))
                db.commit()
                flash("Book details updated.", "success")
                return redirect(url_for("books"))
            except sqlite3.IntegrityError:
                flash("That ISBN is already assigned to another book.", "error")
    return render_template("book_form.html", book=book)

@app.post("/books/<int:book_id>/delete")
def delete_book(book_id):
    db = get_db()
    book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    if not book: abort(404)
    history = db.execute("SELECT COUNT(*) FROM loans WHERE book_id=?", (book_id,)).fetchone()[0]
    waiting = db.execute("SELECT COUNT(*) FROM waitlist WHERE book_id=? AND status='waiting'", (book_id,)).fetchone()[0]
    if book["available_copies"] != book["total_copies"] or history or waiting:
        flash("This book has loan history, active loans or waitlist entries and cannot be deleted.", "error")
    else:
        db.execute("DELETE FROM books WHERE id=?", (book_id,))
        db.commit()
        flash("Book deleted.", "success")
    return redirect(url_for("books"))

@app.route("/members")
def members():
    rows = get_db().execute("""SELECT m.*,
        (SELECT COUNT(*) FROM loans l WHERE l.member_id=m.id AND l.returned_on IS NULL) AS borrowed
        FROM members m ORDER BY m.name COLLATE NOCASE""").fetchall()
    return render_template("members.html", members=rows)

@app.route("/members/add", methods=["GET", "POST"])
def add_member():
    if request.method == "POST":
        code, name, email = [request.form.get(x,"").strip() for x in ("member_code","name","email")]
        if not code or not name:
            flash("Member ID and name are required.", "error")
        else:
            try:
                get_db().execute("INSERT INTO members(member_code,name,email) VALUES(?,?,?)", (code,name,email))
                get_db().commit()
                flash("Member registered.", "success")
                return redirect(url_for("members"))
            except sqlite3.IntegrityError:
                flash("That member ID is already in use.", "error")
    return render_template("member_form.html")

@app.route("/loans")
def loans():
    db = get_db()
    active = db.execute("""SELECT l.*,b.title,b.isbn,m.member_code,m.name
        FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id
        WHERE l.returned_on IS NULL ORDER BY l.due_on""").fetchall()
    history = db.execute("""SELECT l.*,b.title,m.member_code,m.name
        FROM loans l JOIN books b ON b.id=l.book_id JOIN members m ON m.id=l.member_id
        WHERE l.returned_on IS NOT NULL ORDER BY l.returned_on DESC LIMIT 30""").fetchall()
    return render_template("loans.html", active=active, history=history)

@app.route("/borrow", methods=["GET", "POST"])
def borrow():
    db = get_db()
    if request.method == "POST":
        book_id = request.form.get("book_id", type=int)
        member_id = request.form.get("member_id", type=int)
        book = db.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
        member = db.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
        if not book or not member:
            flash("Select a valid book and member.", "error")
        elif db.execute("SELECT COUNT(*) FROM loans WHERE member_id=? AND returned_on IS NULL", (member_id,)).fetchone()[0] >= 5:
            flash("This member has reached the prototype borrowing limit of five active books.", "error")
        elif book["available_copies"] > 0:
            db.execute("INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(?,?,?,?)",
                       (book_id,member_id,date.today().isoformat(),(date.today()+timedelta(days=14)).isoformat()))
            db.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=?", (book_id,))
            db.commit()
            flash("Loan created. The book is due in 14 days.", "success")
            return redirect(url_for("loans"))
        else:
            exists = db.execute("SELECT id FROM waitlist WHERE book_id=? AND member_id=? AND status='waiting'", (book_id,member_id)).fetchone()
            if exists:
                flash("This member is already waiting for this book.", "error")
            else:
                db.execute("INSERT INTO waitlist(book_id,member_id) VALUES(?,?)", (book_id,member_id))
                db.commit()
                flash("No copies are available. Member added to the waitlist.", "success")
                return redirect(url_for("waitlists"))
    books = db.execute("SELECT * FROM books ORDER BY title").fetchall()
    members = db.execute("SELECT * FROM members ORDER BY name").fetchall()
    return render_template("borrow.html", books=books, members=members)

@app.post("/loans/<int:loan_id>/return")
def return_book(loan_id):
    db = get_db()
    loan = db.execute("SELECT * FROM loans WHERE id=? AND returned_on IS NULL", (loan_id,)).fetchone()
    if not loan: abort(404)
    today = date.today()
    due = date.fromisoformat(loan["due_on"])
    overdue_days = max(0, (today-due).days)
    fine = overdue_days * 25  # 25 pence per overdue day; configurable prototype policy
    db.execute("UPDATE loans SET returned_on=?,fine_pence=? WHERE id=?", (today.isoformat(),fine,loan_id))
    db.execute("UPDATE books SET available_copies=available_copies+1 WHERE id=?", (loan["book_id"],))
    if fine:
        db.execute("UPDATE members SET fines_pence=fines_pence+? WHERE id=?", (fine,loan["member_id"]))
    # FIFO: reserve the newly returned copy for the oldest waiting member.
    next_waiter = db.execute("""SELECT w.id,w.member_id,m.name,m.member_code FROM waitlist w
        JOIN members m ON m.id=w.member_id WHERE w.book_id=? AND w.status='waiting'
        ORDER BY w.id LIMIT 1""", (loan["book_id"],)).fetchone()
    notice = ""
    if next_waiter:
        db.execute("UPDATE waitlist SET status='offered' WHERE id=?", (next_waiter["id"],))
        notice = f" The next person in the FIFO waitlist is {next_waiter['name']} ({next_waiter['member_code']}); staff should contact them."
    db.commit()
    flash(f"Return recorded. Fine charged: £{fine/100:.2f}.{notice}", "success")
    return redirect(url_for("loans"))

@app.route("/waitlists")
def waitlists():
    rows = get_db().execute("""SELECT w.*,b.title,m.member_code,m.name
        FROM waitlist w JOIN books b ON b.id=w.book_id JOIN members m ON m.id=w.member_id
        WHERE w.status IN ('waiting','offered') ORDER BY w.book_id,w.id""").fetchall()
    return render_template("waitlists.html", rows=rows)

@app.post("/waitlists/<int:wait_id>/complete")
def complete_waitlist(wait_id):
    db = get_db()
    row = db.execute("SELECT * FROM waitlist WHERE id=? AND status='offered'", (wait_id,)).fetchone()
    if not row: abort(404)
    book = db.execute("SELECT * FROM books WHERE id=?", (row["book_id"],)).fetchone()
    if book["available_copies"] < 1:
        flash("No copy is currently available to fulfil this reservation.", "error")
    else:
        db.execute("INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(?,?,?,?)",
                   (row["book_id"],row["member_id"],date.today().isoformat(),(date.today()+timedelta(days=14)).isoformat()))
        db.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=?", (row["book_id"],))
        db.execute("UPDATE waitlist SET status='fulfilled' WHERE id=?", (wait_id,))
        db.commit()
        flash("Reservation fulfilled and loan created.", "success")
    return redirect(url_for("waitlists"))

@app.route("/analytics")
def analytics():
    db = get_db()
    popular = db.execute("""SELECT b.title,b.author,COUNT(l.id) AS borrow_count
        FROM books b LEFT JOIN loans l ON l.book_id=b.id
        GROUP BY b.id ORDER BY borrow_count DESC,b.title COLLATE NOCASE""").fetchall()
    genre = db.execute("""SELECT genre,COUNT(l.id) AS borrow_count FROM books b
        LEFT JOIN loans l ON l.book_id=b.id GROUP BY genre ORDER BY borrow_count DESC""").fetchall()
    return render_template("analytics.html", popular=popular, genre=genre)

@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404

@app.cli.command("init-db")
def init_db_command():
    init_db()
    seed_demo_data()
    print("Database initialised.")

init_db()
seed_demo_data()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1")
