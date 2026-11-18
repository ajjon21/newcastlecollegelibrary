import os
import sqlite3
import tempfile
import unittest
from datetime import date, timedelta

import app as library_app


class LibraryIntegrationTests(unittest.TestCase):
    def setUp(self):
        handle, self.database = tempfile.mkstemp(suffix=".sqlite3")
        os.close(handle)
        library_app.app.config.update(TESTING=True)
        library_app.DATABASE = self.database
        library_app.init_db()
        library_app.seed_demo_data()
        self.client = library_app.app.test_client()

    def tearDown(self):
        with library_app.app.app_context():
            db = library_app.get_db()
            db.close()
            library_app.g.pop("db", None)
        if os.path.exists(self.database):
            os.unlink(self.database)

    def db(self):
        return sqlite3.connect(self.database)

    def test_dashboard_and_catalogue_render(self):
        self.assertEqual(self.client.get("/").status_code, 200)
        response = self.client.get("/books?q=Hobbit&field=title")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The Hobbit", response.data)

    def test_search_by_exact_isbn(self):
        response = self.client.get("/books?q=9780261103344&field=isbn")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"The Hobbit", response.data)

    def test_add_book_and_reject_duplicate_isbn(self):
        response = self.client.post("/books/add", data={
            "title": "Algorithms", "author": "A. Author",
            "isbn": "9780000000001", "genre": "Computing", "copies": "2"
        }, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Algorithms", response.data)

        response = self.client.post("/books/add", data={
            "title": "Duplicate", "author": "B. Author",
            "isbn": "9780000000001", "genre": "Computing", "copies": "1"
        }, follow_redirects=True)
        self.assertIn(b"ISBN already exists", response.data)

    def test_register_member_and_reject_duplicate_member_code(self):
        payload = {"member_code": "NC900", "name": "Test Member", "email": "test@example.com"}
        self.assertEqual(self.client.post("/members/add", data=payload, follow_redirects=True).status_code, 200)
        response = self.client.post("/members/add", data=payload, follow_redirects=True)
        self.assertIn(b"already in use", response.data)

    def test_borrow_decrements_available_copies(self):
        con = self.db()
        book_id = con.execute("SELECT id FROM books WHERE isbn='9780261103344'").fetchone()[0]
        member_id = con.execute("SELECT id FROM members WHERE member_code='NC001'").fetchone()[0]
        before = con.execute("SELECT available_copies FROM books WHERE id=?", (book_id,)).fetchone()[0]
        con.close()

        response = self.client.post("/borrow", data={"book_id": book_id, "member_id": member_id}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        con = self.db()
        after = con.execute("SELECT available_copies FROM books WHERE id=?", (book_id,)).fetchone()[0]
        active = con.execute("SELECT COUNT(*) FROM loans WHERE book_id=? AND member_id=? AND returned_on IS NULL", (book_id, member_id)).fetchone()[0]
        con.close()
        self.assertEqual(after, before - 1)
        self.assertEqual(active, 1)

    def test_member_cannot_exceed_five_active_loans(self):
        con = self.db()
        member_id = con.execute("SELECT id FROM members WHERE member_code='NC001'").fetchone()[0]
        books = con.execute("SELECT id FROM books ORDER BY id LIMIT 5").fetchall()
        today = date.today().isoformat()
        due = (date.today() + timedelta(days=14)).isoformat()
        for (book_id,) in books:
            con.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=?", (book_id,))
            con.execute("INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(?,?,?,?)", (book_id, member_id, today, due))
        sixth_book = con.execute("SELECT id FROM books ORDER BY id DESC LIMIT 1").fetchone()[0]
        con.close()

        response = self.client.post("/borrow", data={"book_id": sixth_book, "member_id": member_id}, follow_redirects=True)
        self.assertIn(b"borrowing limit", response.data.lower())
        con = self.db()
        count = con.execute("SELECT COUNT(*) FROM loans WHERE member_id=? AND returned_on IS NULL", (member_id,)).fetchone()[0]
        con.close()
        self.assertEqual(count, 5)

    def test_return_calculates_one_day_overdue_fine(self):
        con = self.db()
        book_id = con.execute("SELECT id FROM books WHERE isbn='9780261103344'").fetchone()[0]
        member_id = con.execute("SELECT id FROM members WHERE member_code='NC001'").fetchone()[0]
        con.execute("UPDATE books SET available_copies=available_copies-1 WHERE id=?", (book_id,))
        cur = con.execute(
            "INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(?,?,?,?,?)".replace("?,?,?,?,?", "?,?,?,?"),
            (book_id, member_id, (date.today()-timedelta(days=15)).isoformat(), (date.today()-timedelta(days=1)).isoformat())
        )
        loan_id = cur.lastrowid
        con.commit()
        con.close()

        response = self.client.post(f"/loans/{loan_id}/return", follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        con = self.db()
        fine = con.execute("SELECT fines_pence FROM members WHERE id=?", (member_id,)).fetchone()[0]
        loan_fine = con.execute("SELECT fine_pence FROM loans WHERE id=?", (loan_id,)).fetchone()[0]
        returned = con.execute("SELECT returned_on FROM loans WHERE id=?", (loan_id,)).fetchone()[0]
        con.close()
        self.assertEqual(fine, 25)
        self.assertEqual(loan_fine, 25)
        self.assertEqual(returned, date.today().isoformat())

    def test_unavailable_book_adds_member_to_waitlist(self):
        con = self.db()
        book_id = con.execute("SELECT id FROM books WHERE isbn='9780261103344'").fetchone()[0]
        member_id = con.execute("SELECT id FROM members WHERE member_code='NC001'").fetchone()[0]
        con.execute("UPDATE books SET available_copies=0 WHERE id=?", (book_id,))
        con.commit()
        con.close()

        response = self.client.post("/borrow", data={"book_id": book_id, "member_id": member_id}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        con = self.db()
        status = con.execute("SELECT status FROM waitlist WHERE book_id=? AND member_id=?", (book_id, member_id)).fetchone()[0]
        con.close()
        self.assertEqual(status, "waiting")

    def test_waitlist_is_offered_in_fifo_order_on_return(self):
        con = self.db()
        book_id = con.execute("SELECT id FROM books WHERE isbn='9780261103344'").fetchone()[0]
        members = [row[0] for row in con.execute("SELECT id FROM members ORDER BY id LIMIT 2").fetchall()]
        con.execute("UPDATE books SET available_copies=0 WHERE id=?", (book_id,))
        con.execute("INSERT INTO loans(book_id,member_id,borrowed_on,due_on) VALUES(?,?,?,?)",
                    (book_id, members[0], date.today().isoformat(), (date.today()+timedelta(days=14)).isoformat()))
        loan_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        con.executemany("INSERT INTO waitlist(book_id,member_id) VALUES(?,?)", [(book_id, members[0]), (book_id, members[1])])
        first_waiter = con.execute("SELECT id FROM waitlist ORDER BY id LIMIT 1").fetchone()[0]
        con.commit()
        con.close()

        self.client.post(f"/loans/{loan_id}/return")
        con = self.db()
        status = con.execute("SELECT status FROM waitlist WHERE id=?", (first_waiter,)).fetchone()[0]
        con.close()
        self.assertEqual(status, "offered")


if __name__ == "__main__":
    unittest.main()
