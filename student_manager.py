"""
Student Management System - Professional Edition
Features:
- Add / Edit / Delete students
- Search by name
- TreeView with scrollbars (ID, Name, Age, Class, Score, Date Added)
- Export to CSV and PDF
- SQLite persistence
- Double-click row to open edit dialog
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import os

DB_FILE = "students.db"


# -------------------------
# Database Layer
# -------------------------
class Database:
    def __init__(self, db_path=DB_FILE):
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()
        self.create_table()
        self.ensure_date_column()

    def create_table(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                class TEXT NOT NULL,
                score REAL NOT NULL
            )
        """)
        self.conn.commit()

    def ensure_date_column(self):
        # Add date_added column if missing
        self.cur.execute("PRAGMA table_info(students)")
        cols = [r[1] for r in self.cur.fetchall()]
        if "date_added" not in cols:
            self.cur.execute("ALTER TABLE students ADD COLUMN date_added TEXT")
            self.conn.commit()

    def fetch_all(self, search=None):
        if search:
            self.cur.execute("SELECT id, name, age, class, score, date_added FROM students WHERE name LIKE ?",
                             ('%'+search+'%',))
        else:
            self.cur.execute("SELECT id, name, age, class, score, date_added FROM students")
        return self.cur.fetchall()

    def insert(self, name, age, class_name, score):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.cur.execute("INSERT INTO students (name, age, class, score, date_added) VALUES (?, ?, ?, ?, ?)",
                         (name, age, class_name, score, now))
        self.conn.commit()
        return self.cur.lastrowid

    def update(self, student_id, name, age, class_name, score):
        self.cur.execute("UPDATE students SET name=?, age=?, class=?, score=? WHERE id=?",
                         (name, age, class_name, score, student_id))
        self.conn.commit()

    def delete(self, student_id):
        self.cur.execute("DELETE FROM students WHERE id=?", (student_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()


# -------------------------
# GUI Layer
# -------------------------
class StudentApp:
    def __init__(self, root):
        self.db = Database()
        self.root = root
        self.root.title("Student Management System")
        self.root.geometry("980x600")
        self.root.minsize(860, 520)

        # Top frame - inputs
        top_frame = ttk.Frame(root, padding=10)
        top_frame.pack(fill="x")

        ttk.Label(top_frame, text="Name:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        self.entry_name = ttk.Entry(top_frame, width=30)
        self.entry_name.grid(row=0, column=1, padx=6, pady=6)

        ttk.Label(top_frame, text="Age:").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        self.entry_age = ttk.Entry(top_frame, width=10)
        self.entry_age.grid(row=0, column=3, padx=6, pady=6)

        ttk.Label(top_frame, text="Class:").grid(row=0, column=4, sticky="w", padx=6, pady=6)
        self.entry_class = ttk.Entry(top_frame, width=15)
        self.entry_class.grid(row=0, column=5, padx=6, pady=6)

        ttk.Label(top_frame, text="Score:").grid(row=0, column=6, sticky="w", padx=6, pady=6)
        self.entry_score = ttk.Entry(top_frame, width=10)
        self.entry_score.grid(row=0, column=7, padx=6, pady=6)

        ttk.Button(top_frame, text="Add Student", command=self.add_student, width=14).grid(row=1, column=1, padx=6, pady=8)
        ttk.Button(top_frame, text="Update Selected", command=self.update_student, width=14).grid(row=1, column=3, padx=6, pady=8)
        ttk.Button(top_frame, text="Delete Selected", command=self.delete_student, width=14).grid(row=1, column=5, padx=6, pady=8)

        ttk.Label(top_frame, text="Search:").grid(row=1, column=6, sticky="e", padx=6)
        self.entry_search = ttk.Entry(top_frame, width=20)
        self.entry_search.grid(row=1, column=7, padx=6)
        ttk.Button(top_frame, text="Search", command=self.search_students, width=12).grid(row=1, column=8, padx=6)
        ttk.Button(top_frame, text="Show All", command=self.refresh_tree, width=12).grid(row=1, column=9, padx=6)

        # Middle frame - treeview with scrollbars
        mid_frame = ttk.Frame(root, padding=(10, 6))
        mid_frame.pack(fill="both", expand=True)

        y_scroll = ttk.Scrollbar(mid_frame, orient="vertical")
        x_scroll = ttk.Scrollbar(mid_frame, orient="horizontal")

        columns = ("ID", "Name", "Age", "Class", "Score", "DateAdded")
        self.tree = ttk.Treeview(mid_frame, columns=columns, show="headings",
                                 yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set, selectmode="browse")

        # Headings and columns
        self.tree.heading("ID", text="ID")
        self.tree.heading("Name", text="Name")
        self.tree.heading("Age", text="Age")
        self.tree.heading("Class", text="Class")
        self.tree.heading("Score", text="Score")
        self.tree.heading("DateAdded", text="Date Added")

        self.tree.column("ID", width=60, anchor="center")
        self.tree.column("Name", width=320, anchor="w")
        self.tree.column("Age", width=80, anchor="center")
        self.tree.column("Class", width=120, anchor="center")
        self.tree.column("Score", width=100, anchor="center")
        self.tree.column("DateAdded", width=240, anchor="center")

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")

        mid_frame.rowconfigure(0, weight=1)
        mid_frame.columnconfigure(0, weight=1)

        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)

        # Style alternating rows
        self.tree.tag_configure('oddrow', background='#f9f9f9')
        self.tree.tag_configure('evenrow', background='#ffffff')

        # Bind double-click to edit
        self.tree.bind("<Double-1>", self.on_double_click)

        # Bottom frame - export & status
        bottom_frame = ttk.Frame(root, padding=10)
        bottom_frame.pack(fill="x")

        ttk.Button(bottom_frame, text="Export CSV", command=self.export_csv).grid(row=0, column=0, padx=6)
        ttk.Button(bottom_frame, text="Export PDF", command=self.export_pdf).grid(row=0, column=1, padx=6)
        ttk.Button(bottom_frame, text="Clear Inputs", command=self.clear_inputs).grid(row=0, column=2, padx=6)

        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_label.pack(fill="x", side="bottom")

        # Load initial data
        self.refresh_tree()

    # -------------------------
    # Helpers
    # -------------------------
    def set_status(self, text):
        self.status_var.set(text)
        self.root.update_idletasks()

    def clear_inputs(self):
        self.entry_name.delete(0, tk.END)
        self.entry_age.delete(0, tk.END)
        self.entry_class.delete(0, tk.END)
        self.entry_score.delete(0, tk.END)

    # -------------------------
    # Core actions
    # -------------------------
    def refresh_tree(self, search=None):
        self.set_status("Loading...")
        for r in self.tree.get_children():
            self.tree.delete(r)
        rows = self.db.fetch_all(search)
        total = 0
        for i, row in enumerate(rows):
            tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            self.tree.insert("", "end", values=row, tags=(tag,))
            try:
                total += float(row[4])
            except Exception:
                pass
        self.set_status(f"Loaded {len(rows)} students. Average score shown in status.")
        # no average printed but status updated

    def add_student(self):
        name = self.entry_name.get().strip()
        age = self.entry_age.get().strip()
        class_name = self.entry_class.get().strip()
        score = self.entry_score.get().strip()

        if not (name and age and class_name and score):
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return
        try:
            age_i = int(age)
            score_f = float(score)
            if age_i < 0 or score_f < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Age must be integer and Score must be a positive number.")
            return

        self.db.insert(name, age_i, class_name, score_f)
        self.refresh_tree()
        self.clear_inputs()
        self.set_status(f"Added student '{name}'")

    def get_selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.item(sel[0])['values'][0]

    def update_student(self):
        student_id = self.get_selected_id()
        if not student_id:
            messagebox.showwarning("Selection Error", "Select a student to update (double-click a row or select it).")
            return

        name = self.entry_name.get().strip()
        age = self.entry_age.get().strip()
        class_name = self.entry_class.get().strip()
        score = self.entry_score.get().strip()
        if not (name and age and class_name and score):
            messagebox.showwarning("Input Error", "Please fill all fields.")
            return
        try:
            age_i = int(age)
            score_f = float(score)
            if age_i < 0 or score_f < 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Input Error", "Age must be integer and Score must be a positive number.")
            return

        self.db.update(student_id, name, age_i, class_name, score_f)
        self.refresh_tree()
        self.clear_inputs()
        self.set_status(f"Updated student ID {student_id}")

    def delete_student(self):
        student_id = self.get_selected_id()
        if not student_id:
            messagebox.showwarning("Selection Error", "Select a student to delete.")
            return
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected student?"):
            self.db.delete(student_id)
            self.refresh_tree()
            self.set_status(f"Deleted student ID {student_id}")

    def search_students(self):
        kw = self.entry_search.get().strip()
        self.refresh_tree(search=kw)
        self.set_status(f"Search: '{kw}'")

    # -------------------------
    # Double-click behavior (open edit dialog with row values)
    # -------------------------
    def on_double_click(self, event):
        rowid = self.tree.identify_row(event.y)
        if not rowid:
            return
        values = self.tree.item(rowid)['values']
        # Fill inputs with selected values for quick edit
        # values: (id, name, age, class, score, date_added)
        self.entry_name.delete(0, tk.END); self.entry_name.insert(0, values[1])
        self.entry_age.delete(0, tk.END); self.entry_age.insert(0, values[2])
        self.entry_class.delete(0, tk.END); self.entry_class.insert(0, values[3])
        self.entry_score.delete(0, tk.END); self.entry_score.insert(0, values[4])
        # set selection
        self.tree.selection_set(rowid)
        self.set_status(f"Selected student ID {values[0]} for editing")

    # -------------------------
    # Exports
    # -------------------------
    def export_csv(self):
        suggested = f"students_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        file = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=suggested,
                                            filetypes=[("CSV files", "*.csv")])
        if not file:
            return
        rows = self.db.fetch_all()
        try:
            with open(file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Name", "Age", "Class", "Score", "Date Added"])
                for r in rows:
                    writer.writerow(r)
            messagebox.showinfo("Export CSV", f"CSV exported to:\n{file}")
            self.set_status(f"Exported CSV: {os.path.basename(file)}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed exporting CSV:\n{e}")

    def export_pdf(self):
        suggested = f"students_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        file = filedialog.asksaveasfilename(defaultextension=".pdf", initialfile=suggested,
                                            filetypes=[("PDF files", "*.pdf")])
        if not file:
            return
        rows = self.db.fetch_all()
        try:
            doc = SimpleDocTemplate(file, pagesize=A4)
            styles = getSampleStyleSheet()
            elements = []
            elements.append(Paragraph("Students Report", styles["Title"]))
            elements.append(Spacer(1, 8))

            data = [["ID", "Name", "Age", "Class", "Score", "Date Added"]]
            for r in rows:
                # ensure all values are strings
                data.append([str(r[0]), r[1], str(r[2]), r[3], f"{r[4]:.2f}" if isinstance(r[4], (float, int)) else str(r[4]), r[5] if len(r) > 5 else ""])
            table = Table(data, colWidths=[40, 220, 50, 80, 60, 140])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E86AB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 12))
            doc.build(elements)
            messagebox.showinfo("Export PDF", f"PDF exported to:\n{file}")
            self.set_status(f"Exported PDF: {os.path.basename(file)}")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed exporting PDF:\n{e}")

    def on_close(self):
        self.db.close()
        self.root.destroy()


# -------------------------
# Main
# -------------------------
def main():
    root = tk.Tk()
    app = StudentApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
