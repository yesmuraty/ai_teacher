from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart

from keyboards.kb import main_menu_keyboard
from database.db import get_teacher_by_tg, get_student_by_tg

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id

    teacher = await get_teacher_by_tg(user_id)
    if teacher:
        from keyboards.kb import teacher_main_keyboard
        await message.answer(
            f"👩‍🏫 Қош келдіңіз, <b>{teacher[2]}</b>!\n\nМұғалім панелі:",
            parse_mode="HTML",
            reply_markup=teacher_main_keyboard()
        )
        return

    student = await get_student_by_tg(user_id)
    if student:
        from keyboards.kb import skills_keyboard
        await message.answer(
            f"👨‍🎓 Қош келдіңіз, <b>{student[2]}</b>!\n\nДағдыны таңдаңыз:",
            parse_mode="HTML",
            reply_markup=skills_keyboard(student[3])
        )
        return

    await message.answer(
        "👋 Сәлем! Тілдік дағдыларды дамыту ботына қош келдіңіз!\n\n"
        "Өзіңізді таңдаңыз:",
        reply_markup=main_menu_keyboard()
    )
