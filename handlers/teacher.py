from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import TEACHER_SECRET_CODE
from database.db import (
    add_teacher, get_teacher_by_tg, add_task,
    get_my_tasks, get_shared_tasks, delete_task,
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
    await message.answer("🔐 Мұғалім кодын енгізіңіз:", reply_markup=cancel_keyboard())

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

# ===== ТАПСЫРМА ҚОСУ (жеке) =====

@router.message(F.text == "➕ Менің тапсырмам")
async def add_task_start(message: Message, state: FSMContext):
    teacher = await get_teacher_by_tg(message.from_user.id)
    if not teacher:
        return
    await state.update_data(teacher_id=teacher[0], is_shared=0, collected_files=[])
    await state.set_state(AddTask.choosing_skill)
    await message.answer("📚 Дағдыны таңдаңыз:", reply_markup=teacher_skills_keyboard())

# ===== ТАПСЫРМА ҚОСУ (ортақ) =====

@router.message(F.text == "🌐 Жалпы тапсырма қосу")
async def add_shared_task_start(message: Message, state: FSMContext):
    teacher = await get_teacher_by_tg(message.from_user.id)
    if not teacher:
        return
    await state.update_data(teacher_id=teacher[0], is_shared=1, collected_files=[])
    await state.set_state(AddTask.choosing_skill)
    await message.answer(
        "🌐 <b>Жалпы тапсырма</b> — барлық оқушыға көрінеді.\n\n📚 Дағдыны таңдаңыз:",
        parse_mode="HTML",
        reply_markup=teacher_skills_keyboard()
    )

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
    await state.update_data(title=message.text, collected_files=[])
    await state.set_state(AddTask.waiting_content)
    await message.answer(
        "📋 Тапсырма мазмұнын жіберіңіз.\n\n"
        "📌 Бірнеше файл жіберуге болады (фото, аудио, мәтін).\n"
        "✅ Аяқтау үшін: /done"
    )

@router.message(F.text == "/done", AddTask.waiting_content)
async def add_task_done(message: Message, state: FSMContext):
    data = await state.get_data()
    files = data.get("collected_files", [])
    description = data.get("description", "")

    if not files and not description:
        await message.answer("⚠️ Ештеңе жіберілмеді. Мазмұн жіберіп, /done басыңыз.")
        return

    if files:
        first = files[0]
        file_id = first["file_id"]
        file_type = first["file_type"]
        extra = [f["file_id"] for f in files[1:]]
        if extra:
            description = (description + "\n" + "\n".join(extra)).strip()
    else:
        file_id = None
        file_type = "text"

    is_shared = data.get("is_shared", 0)

    await add_task(
        teacher_id=data["teacher_id"],
        skill=data["skill"],
        title=data["title"],
        description=description,
        file_id=file_id,
        file_type=file_type,
        is_shared=is_shared
    )

    await state.clear()
    shared_label = "🌐 Жалпы" if is_shared else "🔒 Жеке"
    await message.answer(
        f"✅ Тапсырма сәтті қосылды!\n\n"
        f"📚 Дағды: <b>{SKILLS[data['skill']]}</b>\n"
        f"📝 Атауы: <b>{data['title']}</b>\n"
        f"👁 Түрі: {shared_label}",
        parse_mode="HTML",
        reply_markup=teacher_main_keyboard()
    )

@router.message(AddTask.waiting_content)
async def add_task_collect(message: Message, state: FSMContext):
    data = await state.get_data()
    files = data.get("collected_files", [])
    description = data.get("description", "")

    if message.text:
        description = (description + "\n" + message.text).strip()
        await state.update_data(description=description)
        await message.answer(f"📝 Мәтін қабылданды. Жалғастырыңыз немесе /done")
    elif message.photo:
        files.append({"file_id": message.photo[-1].file_id, "file_type": "photo"})
        if message.caption:
            description = (description + "\n" + message.caption).strip()
        await state.update_data(collected_files=files, description=description)
        await message.answer(f"🖼 Фото қабылданды ({len(files)} файл). /done")
    elif message.audio:
        files.append({"file_id": message.audio.file_id, "file_type": "audio"})
        if message.caption:
            description = (description + "\n" + message.caption).strip()
        await state.update_data(collected_files=files, description=description)
        await message.answer(f"🎵 Аудио қабылданды ({len(files)} файл). /done")
    elif message.voice:
        files.append({"file_id": message.voice.file_id, "file_type": "voice"})
        await state.update_data(collected_files=files)
        await message.answer(f"🎤 Дауыс қабылданды ({len(files)} файл). /done")
    elif message.document:
        files.append({"file_id": message.document.file_id, "file_type": "document"})
        if message.caption:
            description = (description + "\n" + message.caption).strip()
        await state.update_data(collected_files=files, description=description)
        await message.answer(f"📄 Файл қабылданды ({len(files)} файл). /done")
    elif message.video:
        files.append({"file_id": message.video.file_id, "file_type": "video"})
        await state.update_data(collected_files=files)
        await message.answer(f"🎬 Видео қабылданды ({len(files)} файл). /done")

# ===== ТАПСЫРМАЛАР ТІЗІМІ =====

@router.message(F.text == "📋 Менің тапсырмаларым")
async def my_tasks(message: Message):
    teacher = await get_teacher_by_tg(message.from_user.id)
    if not teacher:
        return
    tasks = await get_my_tasks(teacher[0])
    if not tasks:
        await message.answer("📭 Сіздің жеке тапсырмаларыңыз жоқ.")
        return
    text = "📋 <b>Менің тапсырмаларым:</b>\n\n"
    for task in tasks:
        skill_label = SKILLS.get(task[2], task[2])
        text += f"• {skill_label} — <b>{task[3]}</b>\n"
    text += "\n<i>Жою үшін тапсырмаға басыңыз:</i>"
    await message.answer(text, parse_mode="HTML", reply_markup=task_list_keyboard(tasks))

@router.message(F.text == "🌐 Жалпы тапсырмалар")
async def shared_tasks_list(message: Message):
    tasks = await get_shared_tasks()
    if not tasks:
        await message.answer("📭 Жалпы тапсырмалар жоқ.")
        return
    text = "🌐 <b>Жалпы тапсырмалар:</b>\n\n"
    for task in tasks:
        skill_label = SKILLS.get(task[2], task[2])
        text += f"• {skill_label} — <b>{task[3]}</b>\n"
    text += "\n<i>Жою үшін тапсырмаға басыңыз:</i>"
    teacher = await get_teacher_by_tg(message.from_user.id)
    await message.answer(text, parse_mode="HTML", reply_markup=task_list_keyboard(tasks))

@router.callback_query(F.data.startswith("delete_task:"))
async def confirm_delete_task(callback: CallbackQuery):
    task_id = int(callback.data.split(":")[1])
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗑 Жою", callback_data=f"confirm_delete:{task_id}"),
        InlineKeyboardButton(text="❌ Болдырмау", callback_data="cancel_delete"),
    ]])
    await callback.message.edit_text(f"⚠️ Бұл тапсырманы жоясыз ба?", reply_markup=kb)

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

    try:
        if file_id and file_type == "photo":
            await bot.send_photo(callback.from_user.id, file_id, caption=text,
                                 parse_mode="HTML", reply_markup=grade_keyboard(sub_id))
        elif file_id and file_type in ("voice", "audio"):
            await bot.send_audio(callback.from_user.id, file_id, caption=text,
                                 parse_mode="HTML", reply_markup=grade_keyboard(sub_id))
        elif file_id and file_type == "document":
            await bot.send_document(callback.from_user.id, file_id, caption=text,
                                    parse_mode="HTML", reply_markup=grade_keyboard(sub_id))
        else:
            await callback.message.edit_text(text + "Баға қойыңыз:",
                                             parse_mode="HTML", reply_markup=grade_keyboard(sub_id))
    except Exception:
        await callback.message.edit_text(text + "Баға қойыңыз:",
                                         parse_mode="HTML", reply_markup=grade_keyboard(sub_id))

@router.callback_query(F.data.startswith("grade:"), GradeTask.waiting_grade)
async def set_grade(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    sub_id = int(parts[1])
    grade = parts[2]
    await state.update_data(grade=grade, sub_id=sub_id)
    await state.set_state(GradeTask.waiting_feedback)
    await callback.message.answer(
        f"✅ Баға: <b>{grade}</b>\n\n💬 Пікір жазыңыз:",
        parse_mode="HTML"
    )

@router.message(GradeTask.waiting_feedback)
async def set_feedback(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await grade_submission(data["sub_id"], data["grade"], message.text)
    try:
        await bot.send_message(
            data["student_tg_id"],
            f"📬 <b>Мұғалімнен кері байланыс!</b>\n\n"
            f"⭐ <b>Баға:</b> {data['grade']}\n"
            f"💬 <b>Пікір:</b> {message.text}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    await state.clear()
    await message.answer("✅ Баға қойылды және оқушыға жіберілді!", reply_markup=teacher_main_keyboard())

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
