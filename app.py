import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
from flask import Flask, render_template, request, redirect, jsonify
import sqlite3

app = Flask(__name__)

# ---------- DB Setup ----------
def init_db():
    conn = sqlite3.connect("/tmp/database.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS notes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        content TEXT,
        type TEXT
    )
    """)
    conn.close()

init_db()


# ---------- Routes ----------

@app.route("/")
def index():
    query = request.args.get("q", "")
    tag = request.args.get("tag", "")

    conn = sqlite3.connect("/tmp/database.db")

    sql = "SELECT * FROM notes WHERE 1=1"
    params = []

    if query:
        sql += " AND (title LIKE ? OR content LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])

    if tag:
        sql += " AND type=?"
        params.append(tag)

    sql += " ORDER BY id DESC"

    notes = conn.execute(sql, params).fetchall()
    conn.close()

    return render_template("index.html", notes=notes, query=query, tag=tag)


@app.route("/add", methods=["GET", "POST"])
def add_note():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]
        note_type = request.form["type"]

        conn = sqlite3.connect("/tmp/database.db")
        conn.execute(
            "INSERT INTO notes(title, content, type) VALUES (?, ?, ?)",
            (title, content, note_type),
        )
        conn.commit()
        conn.close()

        return redirect("/")

    return render_template("add.html")


@app.route("/note/<int:id>")
def view_note(id):
    conn = sqlite3.connect("/tmp/database.db")
    note = conn.execute("SELECT * FROM notes WHERE id=?", (id,)).fetchone()
    conn.close()
    return render_template("view.html", note=note)


# ---------- API endpoint ----------
@app.route("/api/public/brain/query")
def public_api():
    q = request.args.get("q", "")

    return jsonify({
        "answer": f"You asked: {q}",
        "sources": []
    })

@app.route("/summarize/<int:id>")
def summarize(id):
    conn = sqlite3.connect("/tmp/database.db")
    note = conn.execute("SELECT content FROM notes WHERE id=?", (id,)).fetchone()
    conn.close()

    if not note:
        return jsonify({"summary": "Note not found"})

    text = note[0]

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": f"Summarize this note in 3-4 lines:\n{text}"}
        ]
    )

    summary = response.choices[0].message.content

    return jsonify({"summary": summary})

@app.route("/delete/<int:id>")
def delete_note(id):
    conn = sqlite3.connect("/tmp/database.db")
    conn.execute("DELETE FROM notes WHERE id=?", (id,))
    conn.commit()
    conn.close()

    return redirect("/")
# ---------- Search route ----------
@app.route("/search")
def search():
    q = request.args.get("q", "")

    conn = sqlite3.connect("/tmp/database.db")
    notes = conn.execute(
        "SELECT * FROM notes WHERE title LIKE ? OR content LIKE ? OR type LIKE ?",
        (f"%{q}%", f"%{q}%", f"%{q}%")
    ).fetchall()
    conn.close()

    return render_template("index.html", notes=notes)


# ---------- Tag filter route ----------
@app.route("/tag/<tag>")
def filter_tag(tag):
    conn = sqlite3.connect("/tmp/database.db")
    notes = conn.execute(
        "SELECT * FROM notes WHERE type LIKE ?",
        (f"%{tag}%",)
    ).fetchall()
    conn.close()

    return render_template("index.html", notes=notes)
@app.route("/ask", methods=["POST"])
def ask_ai():
    question = request.form["question"]

    conn = sqlite3.connect("/tmp/database.db")
    notes = conn.execute("SELECT content FROM notes").fetchall()
    conn.close()

    combined = "\n".join(n[0] for n in notes)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": f"Notes:\n{combined}\n\nAnswer this question:\n{question}"}
        ]
    )

    answer = response.choices[0].message.content

    return jsonify({"answer": answer})



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)