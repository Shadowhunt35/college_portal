"""
AI Chatbot Assistant — powered by Claude API
Answers student and professor queries based on their own data.
"""

import anthropic
import os
from src.logger import logger


def get_student_context(student, marks, attendances, cgpa_records) -> str:
    """Build a context string from student's data for the AI."""
    att_summary = []
    for subj_name, records in attendances.items():
        total   = len(records)
        present = sum(1 for r in records if r.present)
        pct     = round(present / total * 100, 1) if total > 0 else 0
        att_summary.append(f'  - {subj_name}: {present}/{total} classes ({pct}%)')

    marks_summary = []
    for m in marks:
        marks_summary.append(
            f'  - {m["subject"]}: Theory={m["theory_internal"]}/20, '
            f'Assignment={m["assignment"]}/5, '
            f'Attendance Marks={m["attendance_marks"]}/5, '
            f'Total Internal={m["total"]}/30'
            + (f', Lab={m["lab_internal"]}/20' if m.get("lab_internal") is not None else '')
        )

    cgpa_summary = []
    for c in cgpa_records:
        cgpa_summary.append(f'  - Semester {c.semester}: {c.value}/10')

    return f"""
Student Profile:
  Name: {student.name}
  Registration No: {student.display_reg_no}
  Department: {student.department.name if student.department else 'N/A'}
  Current Semester: {student.current_semester}
  Batch: {student.batch.name if student.batch else 'N/A'}
  Lateral Entry: {'Yes' if student.is_lateral_entry else 'No'}

Attendance:
{chr(10).join(att_summary) if att_summary else '  No attendance records found.'}

Internal Marks:
{chr(10).join(marks_summary) if marks_summary else '  No marks records found.'}

CGPA History:
{chr(10).join(cgpa_summary) if cgpa_summary else '  No CGPA records found.'}
""".strip()


def get_professor_context(professor, students_data) -> str:
    """Build context string from professor's class data."""
    lines = [f"Professor: {professor.name}"]
    lines.append(f"Department: {professor.department.name if professor.department else 'N/A'}")
    lines.append(f"\nClass Summary ({len(students_data)} students):\n")

    for s in students_data:
        lines.append(
            f"  - {s['name']} ({s['reg_no']}): "
            f"Attendance={s['attendance_pct']}%, "
            f"Total Internal={s['total_marks']}/30, "
            f"CGPA={s['cgpa']}, "
            f"Risk={s['risk_label']}"
        )

    return '\n'.join(lines)


def ask_assistant(user_message: str, context: str, role: str = 'student') -> str:
    """
    Send a message to Claude API with the user's academic data as context.
    Returns Claude's response as a string.
    """
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return "Chatbot is not configured. Please contact the administrator."

    if role == 'student':
        system_prompt = f"""You are a helpful academic assistant for a college student portal.
You have access to the student's academic data shown below.
Answer questions about their attendance, marks, CGPA, and academic performance.
Be encouraging but honest. Keep responses concise and clear.
If asked something outside the student's academic data, politely say you can only help with academic queries.

Student Data:
{context}"""

    elif role == 'professor':
        system_prompt = f"""You are a helpful academic assistant for a college professor portal.
You have access to the professor's class data shown below.
Answer questions about student attendance, marks, risk levels, and class performance.
Provide clear, data-driven insights. Keep responses concise.

Class Data:
{context}"""

    else:
        system_prompt = "You are a helpful assistant for a college portal."

    try:
        client   = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model      = 'claude-sonnet-4-20250514',
            max_tokens = 1024,
            system     = system_prompt,
            messages   = [{'role': 'user', 'content': user_message}]
        )
        reply = response.content[0].text
        logger.info(f'Chatbot query by {role}: "{user_message[:50]}..."')
        return reply

    except anthropic.AuthenticationError:
        logger.error('Claude API authentication failed.')
        return "Chatbot authentication failed. Please contact the administrator."

    except anthropic.RateLimitError:
        logger.warning('Claude API rate limit hit.')
        return "Too many requests. Please try again in a moment."

    except Exception as e:
        logger.error(f'Chatbot error: {e}')
        return "Sorry, I could not process your request right now. Please try again."