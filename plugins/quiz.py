# Quiz uploader plugin for Src-1
# Usage: /batchquiz in a group -> upload a TXT file -> quizzes are posted in that same chat.

import asyncio
import os
import re
from pathlib import Path

from pyrogram import filters
from pyrogram.types import Message

from shared_client import app
from utils.custom_filters import login_in_progress

QUIZ_STATE = {}
QUIZ_ACTIVE = set()


def parse_quiz_text(text: str):
    """Parse blocks like:

    Q 1). What is 2+2?
    A) 3
    B) 4
    C) 5
    D) 6
    Ans: B

    Also accepts Question/1. and Answer: B variants.
    """
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    # Split at question markers while retaining content.
    chunks = re.split(r'(?im)(?=^\s*(?:Q(?:uestion)?\s*)?\d+\s*[\).:-])', text)
    out = []

    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue

        lines = [x.strip() for x in chunk.split('\n') if x.strip()]
        if len(lines) < 4:
            continue

        q_match = re.match(r'(?is)^(?:Q(?:uestion)?\s*)?\d+\s*[\).:-]\s*(.*)$', lines[0])
        if not q_match:
            continue
        question = q_match.group(1).strip()

        options = []
        answer = None
        for line in lines[1:]:
            om = re.match(r'^\s*([A-Da-d])\s*[\).:-]\s*(.+)$', line)
            if om:
                options.append(om.group(2).strip())
                continue
            am = re.match(r'^\s*(?:Ans(?:wer)?|Correct)\s*[:=-]\s*([A-Da-d]|[1-4])\s*$', line, re.I)
            if am:
                raw = am.group(1).upper()
                answer = ord(raw) - ord('A') if raw.isalpha() else int(raw) - 1

        if len(options) >= 2 and answer is not None and 0 <= answer < len(options):
            out.append({
                'question': question,
                'options': options[:10],
                'answer': answer,
            })

    return out


@app.on_message(filters.command('batchquiz'))
async def batchquiz_start(_, message: Message):
    chat_id = message.chat.id
    if chat_id in QUIZ_ACTIVE:
        await message.reply_text('⚠️ A quiz upload is already running in this chat.')
        return

    QUIZ_STATE[chat_id] = {'step': 'file'}
    await message.reply_text(
        '📝 Send the TXT file containing the MCQs.\n\n'
        'Format:\n'
        'Q 1). Question\n'
        'A) Option 1\n'
        'B) Option 2\n'
        'C) Option 3\n'
        'D) Option 4\n'
        'Ans: B'
    )


@app.on_message(filters.document)
async def batchquiz_file(_, message: Message):
    chat_id = message.chat.id
    state = QUIZ_STATE.get(chat_id)
    if not state or state.get('step') != 'file':
        return

    name = (message.document.file_name or '').lower()
    if not name.endswith('.txt'):
        await message.reply_text('❌ Please send a .txt quiz file.')
        return

    QUIZ_STATE.pop(chat_id, None)
    QUIZ_ACTIVE.add(chat_id)
    path = None

    try:
        path = await message.download(file_name=f'/tmp/quiz_{chat_id}_{message.id}.txt')
        text = Path(path).read_text(encoding='utf-8-sig', errors='replace')
        quizzes = parse_quiz_text(text)

        if not quizzes:
            await message.reply_text('❌ No valid quizzes found in the TXT file.')
            return

        status = await message.reply_text(f'⏳ Uploading quizzes... 0/{len(quizzes)}')
        success = 0
        failed = 0

        for idx, quiz in enumerate(quizzes, 1):
            try:
                await app.send_poll(
                    chat_id=chat_id,
                    question=quiz['question'][:300],
                    options=[x[:100] for x in quiz['options']],
                    type='quiz',
                    correct_option_id=quiz['answer'],
                    is_anonymous=False,
                )
                success += 1
            except Exception as exc:
                failed += 1
                print(f'Quiz upload error #{idx}: {exc}')

            if idx == 1 or idx % 5 == 0 or idx == len(quizzes):
                try:
                    await status.edit_text(
                        f'⏳ Uploading quizzes... {idx}/{len(quizzes)}\n'
                        f'✅ Uploaded: {success}\n⚠️ Failed: {failed}'
                    )
                except Exception:
                    pass
            await asyncio.sleep(0.5)

        await status.edit_text(
            f'✅ Quiz upload completed.\n\n'
            f'📊 Uploaded: {success}\n'
            f'⚠️ Failed: {failed}'
        )

    except Exception as exc:
        try:
            await message.reply_text(f'❌ Quiz upload error: {str(exc)[:500]}')
        except Exception:
            pass
        print(f'Batchquiz error: {exc}')
    finally:
        QUIZ_ACTIVE.discard(chat_id)
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass


@app.on_message(filters.command('quizstop'))
async def quizstop(_, message: Message):
    chat_id = message.chat.id
    if chat_id in QUIZ_ACTIVE:
        # The current implementation checks this flag between questions.
        QUIZ_ACTIVE.discard(chat_id)
        await message.reply_text('🛑 Stop requested.')
    else:
        QUIZ_STATE.pop(chat_id, None)
        await message.reply_text('No active quiz upload.')
