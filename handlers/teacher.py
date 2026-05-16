from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import TEACHER_SECRET_CODE
from database.db import (
    add_teacher, get_teacher_by_tg, add_task,
    get_all_tasks_by_teacher, delete_task,
    get_pending_submissions, get_submission_by_id,
    grade_submission, get_students_by_teacher
)
from keyboards.kb import (
    teacher_main_keyboard, teacher_skills_keyboard,
    grade_keyboard, submission_list_keyboard,
    task_list_keyboard, cancel_keyboard, SKILLS
)

router = Router()

class TeacherReg(StatesGroup):
    waiting_code = State()
    waiting_name = State()

class AddTask(StatesGroup):
    choosing_skill = State()
    waiting_title = State()
    waiting_content = State()

class GradeTask(StatesGroup):
    waiting_grade = State()
    waiting_feedback = State()

# ===== ТІРКЕЛУ =====

@router.message(F.text == "👩‍🏫 Мен мұғаліммін")
async def teacher_register_start(message: Message, state: FSMContext):
    teacher = await get_teacher_by_tg(message.from_user.id)
    if teacher:
        await message.answer("✅ Сіз бұрыннан тіркелгенсіз.", reply_markup=teacher_main_keyboard())
        return
    await state.set_state(TeacherReg.waiting_code)
    await message.answer(
        "🔐 Мұғалім кодын енгізіңіз:",
        reply_markup=cancel_keyboard()
    )

@router.message(TeacherReg.waiting_code)
async def teacher_check_code(message: Message, state: FSMContext):
    if message.text == "❌ Болдырмау":
        await state.clear()
        from keyboards.kb import main_menu_keyboard
        await message.answer("Болдырылмады.", reply_markup=main_menu_keyboard())
        return
    if message.text != TEACHER_SECRET_CODE:
        await message.answer("❌ Код дұрыс емес. Қайталап көріңіз:")
        return
    await state.set_state(TeacherReg.waiting_name)
    await message.answer("✅ Код дұрыс! Толық атыңызды жазыңыз (Аты-жөні):")

@router.message(TeacherReg.waiting_name)
async def teacher_save_name(message: Message, state: FSMContext):
    await add_teacher(message.from_user.id, message.text)
    await state.clear()
    await message.answer(
        f"🎉 Тіркелдіңіз! Қош келдіңіз, <b>{message.text}</b>!",
        parse_mode="HTML",
        reply_markup=teacher_main_keyboard()
    )

# ===== ТАПСЫРМА ҚОСУ =====

@router.message(F.text == "➕ Тапсырма қосу")
async def add_task_start(message: Message, state: FSMContext):
    teacher = await get_teacher_by_tg(message.from_user.id)
    if not teacher:
        await message.answer("❌ Сіз мұғалім ретінде тіркелмегенсіз.")
        return
    await state.update_data(teacher_id=teacher[0])
    await state.set_state(AddTask.choosing_skill)
    await message.answer("📚 Дағдыны таңдаңыз:", reply_markup=teacher_skills_keyboard())

@router.callback_query(F.data.startswith("add_skill:"))
async def add_task_skill_chosen(callback: CallbackQuery, state: FSMContext):
    skill = callback.data.split(":")[1]
    await state.update_data(skill=skill)
    await state.set_state(AddTask.waiting_title)
    await callback.message.edit_text(
        f"✅ Таңдалды: <b>{SKILLS[skill]}</b>\n\n📝 Тапсырманың атауын жазыңыз:",
        parse_mode="HTML"
    )

@router.message(AddTask.waiting_title)
async def add_task_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(AddTask.waiting_content)
    await message.answer(
        "📋 Енді тапсырманың мазмұнын жіберіңіз:\n\n"
        "Мәтін, фото, файл, дауыс хабарлама немесе сілтеме болуы мүмкін.\n\n"
        "Аяқтау үшін: /done"
    )

@router.message(AddTask.waiting_content)
async def add_task_content(message: Message, state: FSMContext):
    data = await state.get_data()
    file_id = None
    file_type = "text"
    content = ""

    if message.text and message.text != "/done":
        content = message.text
        file_type = "text"
    elif message.photo:
        file_id = message.photo[-1].file_id
        file_type = "photo"
        content = message.caption or ""
    elif message.document:
        file_id = message.document.file_id
        file_type = "document"
        content = message.caption or ""
    elif message.voice:
        file_id = message.voice.file_id
        file_type = "voice"
        content = ""
    elif message.audio:
        file_id = message.audio.file_id
        file_type = "audio"
        content = message.caption or ""
    elif message.video:
        file_id = message.video.file_id
        file_type = "video"
        content = message.caption or ""

    task_id = await add_task(
        teacher_id=data["teacher_id"],
        skill=data["skill"],
        title=data["title"],
        description=content,
        file_id=file_id,
        file_type=file_type
    )

    await state.clear()
    await message.answer(
        f"✅ Тапсырма сәтті қосылды!\n\n"
        f"📚 Дағды: <b>{SKILLS[data['skill']]}</b>\n"
        f"📝 Атауы: <b>{data['title']}</b>",
        parse_mode="HTML",
        reply_markup=teacher_main_keyboard()
    )

# ===== ТАПСЫРМАЛАР ТІЗІМІ =====

@router.message(F.text == "📋 Менің тапсырмаларым")
async def my_tasks(message: Message):
    teacher = await get_teacher_by_tg(message.from_user.id)
    if not teacher:
        return

    tasks = await get_all_tasks_by_teacher(teacher[0])
    if not tasks:
        await message.answer("📭 Тапсырмалар жоқ. ➕ Тапсырма қосу арқылы жасаңыз.")
        return

    text = "📋 <b>Сіздің тапсырмаларыңыз:</b>\n\n"
    for task in tasks:
        skill_label = SKILLS.get(task[2], task[2])
        text += f"• {skill_label} — <b>{task[4]}</b> (ID: {task[0]})\n"

    text += "\n<i>Жою үшін тапсырмаға басыңыз:</i>"
    await message.answer(text, parse_mode="HTML", reply_markup=task_list_keyboard(tasks))

@router.callback_query(F.data.startswith("delete_task:"))
async def confirm_delete_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    teacher = await get_teacher_by_tg(callback.from_user.id)

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗑 Жою", callback_data=f"confirm_delete:{task_id}"),
            InlineKeyboardButton(text="❌ Болдырмау", callback_data="cancel_delete"),
        ]
    ])
    await callback.message.edit_text(
        f"⚠️ Бұл тапсырманы жоясыз ба? (ID: {task_id})",
        reply_markup=kb
    )

@router.callback_query(F.data.startswith("confirm_delete:"))
async def do_delete_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    teacher = await get_teacher_by_tg(callback.from_user.id)
    await delete_task(task_id, teacher[0])
    await callback.message.edit_text("✅ Тапсырма жойылды.")

@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    await callback.message.edit_text("Болдырылмады.")

# ===== ТАПСЫРЫЛҒАН ЖҰМЫСТАР =====

@router.message(F.text == "📥 Тапсырылған жұмыстар")
async def pending_submissions(message: Message):
    teacher = await get_teacher_by_tg(message.from_user.id)
    if not teacher:
        return

    subs = await get_pending_submissions(teacher[0])
    if not subs:
        await message.answer("📭 Тексерілмеген жұмыстар жоқ.")
        return

    await message.answer(
        f"📥 <b>Тексерілмеген жұмыстар: {len(subs)}</b>\n\nТаңдаңыз:",
        parse_mode="HTML",
        reply_markup=submission_list_keyboard(subs)
    )

@router.callback_query(F.data.startswith("view_submission:"))
async def view_submission(callback: CallbackQuery, bot: Bot, state: FSMContext):
    sub_id = int(callback.data.split(":")[1])
    sub = await get_submission_by_id(sub_id)

    if not sub:
        await callback.answer("Жұмыс табылмады.")
        return

    # sub columns: id, student_id, task_id, content, file_id, file_type, submitted_at, grade, feedback, graded_at, full_name, tg_id, title, skill
    student_name = sub[10]
    task_title = sub[12]
    skill = sub[13]
    content = sub[3]
    file_id = sub[4]
    file_type = sub[5]

    text = (
        f"👤 <b>Оқушы:</b> {student_name}\n"
        f"📚 <b>Дағды:</b> {SKILLS.get(skill, skill)}\n"
        f"📝 <b>Тапсырма:</b> {task_title}\n\n"
    )

    if content:
        text += f"💬 <b>Жауап:</b>\n{content}\n\n"

    await state.update_data(grading_submission_id=sub_id, student_tg_id=sub[11])
    await state.set_state(GradeTask.waiting_grade)

    if file_id and file_type == "photo":
        await bot.send_photo(callback.from_user.id, file_id, caption=text, parse_mode="HTML",
                             reply_markup=grade_keyboard(sub_id))
    elif file_id and file_type == "voice":
        await bot.send_voice(callback.from_user.id, file_id, caption=text, parse_mode="HTML",
                             reply_markup=grade_keyboard(sub_id))
    elif file_id and file_type == "document":
        await bot.send_document(callback.from_user.id, file_id, caption=text, parse_mode="HTML",
                                reply_markup=grade_keyboard(sub_id))
    else:
        await callback.message.edit_text(
            text + "Баға қойыңыз:",
            parse_mode="HTML",
            reply_markup=grade_keyboard(sub_id)
        )

@router.callback_query(F.data.startswith("grade:"), GradeTask.waiting_grade)
async def set_grade(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    sub_id = int(parts[1])
    grade = parts[2]

    await state.update_data(grade=grade, sub_id=sub_id)
    await state.set_state(GradeTask.waiting_feedback)
    await callback.message.answer(
        f"✅ Баға: <b>{grade}</b>\n\n💬 Пікір жазыңыз (түсіндірме, кеңес):",
        parse_mode="HTML"
    )

@router.message(GradeTask.waiting_feedback)
async def set_feedback(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    sub_id = data["sub_id"]
    grade = data["grade"]
    feedback = message.text
    student_tg_id = data["student_tg_id"]

    await grade_submission(sub_id, grade, feedback)

    # Оқушыға хабарлау
    try:
        await bot.send_message(
            student_tg_id,
            f"📬 <b>Мұғалімнен кері байланыс!</b>\n\n"
            f"⭐ <b>Баға:</b> {grade}\n"
            f"💬 <b>Пікір:</b> {feedback}",
            parse_mode="HTML"
        )
    except Exception:
        pass

    await state.clear()
    await message.answer(
        "✅ Баға қойылды және оқушыға жіберілді!",
        reply_markup=teacher_main_keyboard()
    )

# ===== ОҚУШЫЛАР ТІЗІМІ =====

@router.message(F.text == "👥 Менің оқушыларым")
async def my_students(message: Message):
    teacher = await get_teacher_by_tg(message.from_user.id)
    if not teacher:
        return

    students = await get_students_by_teacher(teacher[0])
    if not students:
        await message.answer("📭 Оқушылар жоқ.")
        return

    text = f"👥 <b>Менің оқушыларым ({len(students)}):</b>\n\n"
    for i, (s_id, name, tg_id) in enumerate(students, 1):
        text += f"{i}. {name}\n"

    await message.answer(text, parse_mode="HTML")
