import aiosqlite
import os

DB_PATH = os.environ.get("DB_PATH", "bot.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS teachers (
                id INTEGER PRIMARY KEY,
                tg_id INTEGER UNIQUE,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY,
                tg_id INTEGER UNIQUE,
                full_name TEXT,
                teacher_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (teacher_id) REFERENCES teachers(id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                teacher_id INTEGER,
                skill TEXT,
                title TEXT,
                description TEXT,
                file_id TEXT,
                file_type TEXT,
                is_shared INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # is_shared баған жоқ болса қосу (ескі база үшін)
        try:
            await db.execute("ALTER TABLE tasks ADD COLUMN is_shared INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY,
                student_id INTEGER,
                task_id INTEGER,
                content TEXT,
                file_id TEXT,
                file_type TEXT,
                submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                grade TEXT,
                feedback TEXT,
                graded_at TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id),
                FOREIGN KEY (task_id) REFERENCES tasks(id)
            )
        """)
        await db.commit()

# ===== TEACHERS =====

async def add_teacher(tg_id: int, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO teachers (tg_id, full_name) VALUES (?, ?)",
            (tg_id, full_name)
        )
        await db.commit()

async def get_teacher_by_tg(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM teachers WHERE tg_id = ?", (tg_id,)) as cur:
            return await cur.fetchone()

async def get_all_teachers():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT id, full_name FROM teachers ORDER BY full_name") as cur:
            return await cur.fetchall()

# ===== STUDENTS =====

async def add_student(tg_id: int, full_name: str, teacher_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO students (tg_id, full_name, teacher_id) VALUES (?, ?, ?)",
            (tg_id, full_name, teacher_id)
        )
        await db.commit()

async def get_student_by_tg(tg_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM students WHERE tg_id = ?", (tg_id,)) as cur:
            return await cur.fetchone()

async def get_students_by_teacher(teacher_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT id, full_name, tg_id FROM students WHERE teacher_id = ?", (teacher_id,)
        ) as cur:
            return await cur.fetchall()

# ===== TASKS =====

async def add_task(teacher_id: int, skill: str, title: str, description: str,
                   file_id: str, file_type: str, is_shared: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO tasks (teacher_id, skill, title, description, file_id, file_type, is_shared) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (teacher_id, skill, title, description, file_id, file_type, is_shared)
        )
        await db.commit()
        return cur.lastrowid

async def get_tasks_for_student(teacher_id: int, skill: str, topic_keyword: str = None):
    """Оқушыға: мұғалімнің жеке тапсырмалары + барлық ортақ тапсырмалар"""
    async with aiosqlite.connect(DB_PATH) as db:
        if topic_keyword:
            async with db.execute(
                """SELECT * FROM tasks
                   WHERE (teacher_id = ? OR is_shared = 1)
                   AND skill = ? AND title LIKE ?
                   ORDER BY is_shared ASC, created_at DESC""",
                (teacher_id, skill, f"%{topic_keyword}%")
            ) as cur:
                return await cur.fetchall()
        else:
            async with db.execute(
                """SELECT * FROM tasks
                   WHERE (teacher_id = ? OR is_shared = 1)
                   AND skill = ?
                   ORDER BY is_shared ASC, created_at DESC""",
                (teacher_id, skill)
            ) as cur:
                return await cur.fetchall()

async def get_task_by_id(task_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)) as cur:
            return await cur.fetchone()

async def get_my_tasks(teacher_id: int):
    """Мұғалімнің өз тапсырмалары"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM tasks WHERE teacher_id = ? ORDER BY skill, created_at DESC",
            (teacher_id,)
        ) as cur:
            return await cur.fetchall()

async def get_shared_tasks():
    """Барлық ортақ тапсырмалар"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute(
            "SELECT * FROM tasks WHERE is_shared = 1 ORDER BY skill, created_at DESC"
        ) as cur:
            return await cur.fetchall()

async def delete_task(task_id: int, teacher_id: int):
    """Мұғалім өз тапсырмасын жоя алады. is_shared тапсырмаларды кез-келген мұғалім жоя алады."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM tasks WHERE id = ? AND (teacher_id = ? OR is_shared = 1)",
            (task_id, teacher_id)
        )
        await db.commit()

# ===== SUBMISSIONS =====

async def add_submission(student_id: int, task_id: int, content: str, file_id: str, file_type: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO submissions (student_id, task_id, content, file_id, file_type) VALUES (?, ?, ?, ?, ?)",
            (student_id, task_id, content, file_id, file_type)
        )
        await db.commit()
        return cur.lastrowid

async def get_pending_submissions(teacher_id: int):
    """Мұғалімнің оқушыларының тапсырылған жұмыстары (тапсырма кімдікі болса да)"""
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT s.id, st.full_name, st.tg_id, t.title, t.skill,
                   s.content, s.file_id, s.file_type, s.submitted_at
            FROM submissions s
            JOIN students st ON s.student_id = st.id
            JOIN tasks t ON s.task_id = t.id
            WHERE st.teacher_id = ? AND s.grade IS NULL
            ORDER BY s.submitted_at ASC
        """, (teacher_id,)) as cur:
            return await cur.fetchall()

async def get_submission_by_id(submission_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT s.*, st.full_name, st.tg_id, t.title, t.skill
            FROM submissions s
            JOIN students st ON s.student_id = st.id
            JOIN tasks t ON s.task_id = t.id
            WHERE s.id = ?
        """, (submission_id,)) as cur:
            return await cur.fetchone()

async def grade_submission(submission_id: int, grade: str, feedback: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE submissions SET grade = ?, feedback = ?, graded_at = CURRENT_TIMESTAMP WHERE id = ?",
            (grade, feedback, submission_id)
        )
        await db.commit()

async def get_student_submissions(student_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("""
            SELECT s.id, t.title, t.skill, s.submitted_at, s.grade, s.feedback
            FROM submissions s
            JOIN tasks t ON s.task_id = t.id
            WHERE s.student_id = ?
            ORDER BY s.submitted_at DESC
            LIMIT 20
        """, (student_id,)) as cur:
            return await cur.fetchall()
