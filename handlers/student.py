from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database.db import (
    get_student_by_tg, add_student, get_all_teachers,
    get_task_by_id, add_submission, get_student_submissions
)
from keyboards.kb import (
    teachers_keyboard, topics_keyboard, skills_keyboard,
    tasks_keyboard, submit_task_keyboard, cancel_keyboard, SKILLS, TOPICS
)

router = Router()

class StudentReg(StatesGroup):
    choosing_teacher = State()
    waiting_name = State()

class SubmitTask(StatesGroup):
    waiting_submission = State()

# ===== ТІРКЕЛУ =====

@router.message(F.text == "👨‍🎓 Мен оқушымын")
async def student_start(message: Message, state: FSMContext):
    student = await get_student_by_tg(message.from_user.id)
    if student:
        await message.answer(
            f"✅ Қош келдіңіз, <b>{student[2]}</b>!\n\nТақырыпты таңдаңыз:",
            parse_mode="HTML",
            reply_markup=topics_keyboard(student[3])
        )
        return

    teachers = await get_all_teachers()
    if not teachers:
        await message.answer("❌ Әзірше мұғалімдер жоқ. Кейінірек кіріп көріңіз.")
        return

    await state.set_state(StudentReg.choosing_teacher)
    await message.answer("👩‍🏫 Мұғаліміңізді таңдаңыз:", reply_markup=teachers_keyboard(teachers))

@router.callback_query(F.data.startswith("choose_teacher:"), StudentReg.choosing_teacher)
async def student_choose_teacher(callback: CallbackQuery, state: FSMContext):
    teacher_id = int(callback.data.split(":")[1])
    await state.update_data(teacher_id=teacher_id)
    await state.set_state(StudentReg.waiting_name)
    await callback.message.edit_text("✅ Мұғалім таңдалды!\n\n📝 Толық атыңызды жазыңыз (Аты-жөні):")

@router.message(StudentReg.waiting_name)
async def student_save_name(message: Message, state: FSMContext):
    data = await state.get_data()
    await add_student(message.from_user.id, message.text, data["teacher_id"])
    await state.clear()
    await message.answer(
        f"🎉 Тіркелдіңіз! Қош келдіңіз, <b>{message.text}</b>!\n\nТақырыпты таңдаңыз:",
        parse_mode="HTML",
        reply_markup=topics_keyboard(data["teacher_id"])
    )

# ===== ТАҚЫРЫП ТАҢДАУ =====

@router.callback_query(F.data.startswith("topic:"))
async def topic_chosen(callback: CallbackQuery):
    parts = callback.data.split(":")
    topic_idx = int(parts[1])
    teacher_id = int(parts[2])
    topic_name = TOPICS[topic_idx]

    await callback.message.edit_text(
        f"📗 <b>{topic_name}</b>\n\nДағдыны таңдаңыз:",
        parse_mode="HTML",
        reply_markup=skills_keyboard(teacher_id, topic_idx)
    )

@router.callback_query(F.data.startswith("back_to_topics:"))
async def back_to_topics(callback: CallbackQuery):
    teacher_id = int(callback.data.split(":")[1])
    await callback.message.edit_text(
        "📚 Тақырыпты таңдаңыз:",
        reply_markup=topics_keyboard(teacher_id)
    )

# ===== ДАҒДЫ ТАҢДАУ =====

@router.callback_query(F.data.startswith("skill:"))
async def skill_chosen(callback: CallbackQuery):
    parts = callback.data.split(":")
    skill = parts[1]
    teacher_id = int(parts[2])
    topic_idx = int(parts[3]) if len(parts) > 3 else -1

    # Тақырып атауы бойынша сүзу
    import aiosqlite
    topic_filter = TOPICS[topic_idx] if 0 <= topic_idx < len(TOPICS) else None

    async with aiosqlite.connect("bot.db") as db:
        if topic_filter:
            # Тақырып бойынша тапсырмаларды сүз
            async with db.execute(
                "SELECT * FROM tasks WHERE teacher_id=? AND skill=? AND title LIKE ? ORDER BY created_at DESC",
                (teacher_id, skill, f"%{topic_filter.split()[0]}%")
            ) as cur:
                tasks = await cur.fetchall()
            # Егер нәтиже болмаса, тақырып сөзінен кеңірек іздеу
            if not tasks:
                # тақырыптың алғашқы сөзімен емес, description немесе title-да тақырып атауымен іздеу
                async with db.execute(
                    """SELECT * FROM tasks WHERE teacher_id=? AND skill=?
                       AND (title LIKE ? OR description LIKE ?)
                       ORDER BY created_at DESC""",
                    (teacher_id, skill, f"%{topic_filter[:15]}%", f"%{topic_filter[:15]}%")
                ) as cur:
                    tasks = await cur.fetchall()
        else:
            async with db.execute(
                "SELECT * FROM tasks WHERE teacher_id=? AND skill=? ORDER BY created_at DESC",
                (teacher_id, skill)
            ) as cur:
                tasks = await cur.fetchall()

    skill_label = SKILLS.get(skill, skill)
    topic_name = TOPICS[topic_idx] if 0 <= topic_idx < len(TOPICS) else ""

    if not tasks:
        await callback.message.edit_text(
            f"📭 <b>{skill_label}</b> бойынша тапсырмалар жоқ.\nМұғалім жақында қосады.",
            parse_mode="HTML"
        )
        return

    header = f"📗 <b>{topic_name}</b>\n" if topic_name else ""
    await callback.message.edit_text(
        f"{header}📚 <b>{skill_label}</b> тапсырмалары:\n\nТаңдаңыз:",
        parse_mode="HTML",
        reply_markup=tasks_keyboard(tasks, skill, teacher_id, topic_idx)
    )

@router.callback_query(F.data.startswith("back_to_skills:"))
async def back_to_skills(callback: CallbackQuery):
    parts = callback.data.split(":")
    teacher_id = int(parts[1])
    topic_idx = int(parts[2]) if len(parts) > 2 else -1
    topic_name = TOPICS[topic_idx] if 0 <= topic_idx < len(TOPICS) else ""

    await callback.message.edit_text(
        f"📗 <b>{topic_name}</b>\n\nДағдыны таңдаңыз:" if topic_name else "Дағдыны таңдаңыз:",
        parse_mode="HTML",
        reply_markup=skills_keyboard(teacher_id, topic_idx)
    )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    student = await get_student_by_tg(callback.from_user.id)
    if student:
        await callback.message.edit_text(
            "📚 Тақырыпты таңдаңыз:",
            reply_markup=topics_keyboard(student[3])
        )

# ===== ТАПСЫРМАНЫ КӨРУ =====

@router.callback_query(F.data.startswith("view_task:"))
async def view_task(callback: CallbackQuery, bot: Bot):
    task_id = int(callback.data.split(":")[1])
    task = await get_task_by_id(task_id)

    if not task:
        await callback.answer("Тапсырма табылмады.")
        return

    # id[0], teacher_id[1], skill[2], title[3], description[4], file_id[5], file_type[6]
    skill_label = SKILLS.get(task[2], task[2])
    caption = f"📚 <b>{skill_label}</b>\n📝 <b>{task[3]}</b>\n\n{task[4] or ''}"

    if task[5] and task[6] == "photo":
        await bot.send_photo(callback.from_user.id, task[5],
            caption=caption, parse_mode="HTML",
            reply_markup=submit_task_keyboard(task[0]))
        await callback.answer()
    elif task[5] and task[6] in ("audio", "voice"):
        await bot.send_audio(callback.from_user.id, task[5],
            caption=caption, parse_mode="HTML",
            reply_markup=submit_task_keyboard(task[0]))
        await callback.answer()
    elif task[5] and task[6] == "document":
        await bot.send_document(callback.from_user.id, task[5],
            caption=caption, parse_mode="HTML",
            reply_markup=submit_task_keyboard(task[0]))
        await callback.answer()
    elif task[5] and task[6] == "video":
        await bot.send_video(callback.from_user.id, task[5],
            caption=caption, parse_mode="HTML",
            reply_markup=submit_task_keyboard(task[0]))
        await callback.answer()
    else:
        await callback.message.edit_text(caption, parse_mode="HTML",
            reply_markup=submit_task_keyboard(task[0]))

# ===== ЖҰМЫС ТАПСЫРУ =====

@router.callback_query(F.data.startswith("submit_task:"))
async def start_submit(callback: CallbackQuery, state: FSMContext):
    task_id = int(callback.data.split(":")[1])
    await state.update_data(task_id=task_id)
    await state.set_state(SubmitTask.waiting_submission)
    await callback.message.answer(
        "📤 <b>Жұмысыңызды жіберіңіз:</b>\n\n"
        "• Мәтін жазыңыз\n"
        "• Фото жіберіңіз\n"
        "• Дауыс хабарлама жіберіңіз (Айтылым үшін)\n\n"
        "Болдырмау: /cancel",
        parse_mode="HTML",
        reply_markup=cancel_keyboard()
    )
    await callback.answer()

@router.message(F.text == "/cancel", SubmitTask.waiting_submission)
async def cancel_submit(message: Message, state: FSMContext):
    await state.clear()
    student = await get_student_by_tg(message.from_user.id)
    await message.answer("Болдырылмады.", reply_markup=topics_keyboard(student[3]))

@router.message(SubmitTask.waiting_submission)
async def receive_submission(message: Message, state: FSMContext, bot: Bot):
    if message.text == "❌ Болдырмау":
        await state.clear()
        student = await get_student_by_tg(message.from_user.id)
        await message.answer("Болдырылмады.", reply_markup=topics_keyboard(student[3]))
        return

    data = await state.get_data()
    task_id = data["task_id"]
    student = await get_student_by_tg(message.from_user.id)

    content = ""
    file_id = None
    file_type = "text"

    if message.text:
        content = message.text
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        content = message.caption or ""
    elif message.voice:
        file_id = message.voice.file_id
        file_type = "voice"
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
        content = message.caption or ""

    sub_id = await add_submission(student[0], task_id, content, file_id, file_type)

    # Мұғалімге хабарлау
    task = await get_task_by_id(task_id)
    import aiosqlite
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT tg_id FROM teachers WHERE id = ?", (task[1],)) as cur:
            row = await cur.fetchone()
            teacher_tg_id = row[0] if row else None

    if teacher_tg_id:
        skill_label = SKILLS.get(task[2], task[2])
        notify = (
            f"📬 <b>Жаңа жұмыс тапсырылды!</b>\n\n"
            f"👤 Оқушы: <b>{student[2]}</b>\n"
            f"📚 Дағды: <b>{skill_label}</b>\n"
            f"📝 Тапсырма: <b>{task[3]}</b>"
        )
        try:
            if file_type == "photo":
                await bot.send_photo(teacher_tg_id, file_id,
                    caption=notify + (f"\n\n💬 {content}" if content else ""),
                    parse_mode="HTML")
            elif file_type in ("voice", "audio"):
                await bot.send_audio(teacher_tg_id, file_id, caption=notify, parse_mode="HTML")
            elif file_type == "document":
                await bot.send_document(teacher_tg_id, file_id, caption=notify, parse_mode="HTML")
            else:
                await bot.send_message(teacher_tg_id,
                    notify + f"\n\n💬 Жауап:\n{content}", parse_mode="HTML")
        except Exception:
            pass

    await state.clear()
    await message.answer(
        "✅ <b>Жұмысыңыз тапсырылды!</b>\n\nМұғалім тексеріп, кері байланыс жібереді.",
        parse_mode="HTML",
        reply_markup=topics_keyboard(student[3])
    )
