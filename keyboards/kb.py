from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

SKILLS = {
    "tyndałym": "🎧 Тыңдалым",
    "aytyłym":  "🗣 Айтылым",
    "jazyłym":  "✍️ Жазылым",
    "okyłym":   "📖 Оқылым",
}

TOPICS = [
    "Сарқылмайтын табиғи ресурстар",
    "Баламалы энергия қорлары",
    "Балалардың жас ерекшеліктері",
]

def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="👨‍🎓 Мен оқушымын")],
            [KeyboardButton(text="👩‍🏫 Мен мұғаліммін")],
        ],
        resize_keyboard=True
    )

def topics_keyboard(teacher_id: int):
    buttons = []
    for i, topic in enumerate(TOPICS):
        buttons.append([InlineKeyboardButton(
            text=f"📗 {topic}",
            callback_data=f"topic:{i}:{teacher_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def skills_keyboard(teacher_id: int, topic_idx: int = -1):
    buttons = []
    for key, label in SKILLS.items():
        buttons.append([InlineKeyboardButton(
            text=label,
            callback_data=f"skill:{key}:{teacher_id}:{topic_idx}"
        )])
    if topic_idx >= 0:
        buttons.append([InlineKeyboardButton(
            text="🔙 Тақырыпқа оралу",
            callback_data=f"back_to_topics:{teacher_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def teachers_keyboard(teachers: list):
    buttons = []
    for t_id, name in teachers:
        buttons.append([InlineKeyboardButton(
            text=f"👩‍🏫 {name}",
            callback_data=f"choose_teacher:{t_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def tasks_keyboard(tasks: list, skill: str, teacher_id: int, topic_idx: int = -1):
    buttons = []
    for task in tasks:
        task_id = task[0]
        title = task[3]
        buttons.append([InlineKeyboardButton(
            text=f"📝 {title}",
            callback_data=f"view_task:{task_id}"
        )])
    if topic_idx >= 0:
        buttons.append([InlineKeyboardButton(text="🔙 Артқа", callback_data=f"back_to_skills:{teacher_id}:{topic_idx}")])
    else:
        buttons.append([InlineKeyboardButton(text="🔙 Артқа", callback_data=f"back_to_topics:{teacher_id}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def submit_task_keyboard(task_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Жұмысымды тапсыру", callback_data=f"submit_task:{task_id}")],
        [InlineKeyboardButton(text="🔙 Артқа", callback_data="back_to_main")],
    ])

def teacher_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Менің тапсырмам"), KeyboardButton(text="🌐 Жалпы тапсырма қосу")],
            [KeyboardButton(text="📋 Менің тапсырмаларым")],
            [KeyboardButton(text="🌐 Жалпы тапсырмалар")],
            [KeyboardButton(text="📥 Тапсырылған жұмыстар")],
            [KeyboardButton(text="👥 Менің оқушыларым")],
        ],
        resize_keyboard=True
    )

def teacher_skills_keyboard():
    buttons = []
    for key, label in SKILLS.items():
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"add_skill:{key}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def grade_keyboard(submission_id: int):
    grades = ["5", "4", "3", "2"]
    buttons = [[InlineKeyboardButton(
        text=f"{'⭐' * int(g)} {g}",
        callback_data=f"grade:{submission_id}:{g}"
    )] for g in grades]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def submission_list_keyboard(submissions: list):
    buttons = []
    for sub in submissions:
        sub_id, student_name, _, task_title, skill, *_ = sub
        buttons.append([InlineKeyboardButton(
            text=f"👤 {student_name} — {str(task_title)[:25]}",
            callback_data=f"view_submission:{sub_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def task_list_keyboard(tasks: list):
    buttons = []
    for task in tasks:
        task_id = task[0]
        skill = task[2]
        title = task[3]
        skill_label = SKILLS.get(skill, skill)
        buttons.append([InlineKeyboardButton(
            text=f"{skill_label} — {str(title)[:30]}",
            callback_data=f"delete_task:{task_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Болдырмау")]],
        resize_keyboard=True
    )
