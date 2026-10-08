import random
from django.http import HttpRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from .models import Question, Answer, QuestionProgress, Statistics

# Create your views here.
@login_required
def next_question_view(request : HttpRequest):
    user = request.user

    solved_question_ids = QuestionProgress.objects.filter(user = user, correct_attempts__gt = 0).values_list('question_id', flat=True)
    open_questions = Question.objects.filter(type=Question.Type.MULTIPLE_CHOICE).exclude(id__in=solved_question_ids)

    if(open_questions.exists()):
        question = random.choice(list(open_questions))
    else: 
        all_questions = Question.objects.filter(type = Question.Type.MULTIPLE_CHOICE)
        if not all_questions.exists():
            return render(request, 'quiz/no_questions.html')

        question = random.choice(list(all_questions))
    return redirect('quiz:question_detail', question_id=question.id)


@login_required
def question_detail_view(request : HttpRequest, question_id: int):
    question = get_object_or_404(Question, id=question_id)

    session_key = f'answers_order_{question.id}'
    if session_key in request.session:
        answer_ids = request.session[session_key]
        answers = list(Answer.objects.filter(id__in=answer_ids))
        answers.sort(key=lambda a: answer_ids.index(a.id))
    else:
        answers = list(question.answers.all())
        random.shuffle(answers)
        request.session[session_key] = [a.id for a in answers]

    selected_answer = None
    is_correct = None
    evaluated = False

    if request.method == 'POST':
        # Markieren einer Frage handlen
        if 'toggle_review' in request.POST:
            question.marked_for_review = not question.marked_for_review
            question.save(update_fields=['marked_for_review'])
            return redirect('quiz:question_detail', question_id=question.id)

        selected_answer_id = request.POST.get('answer')
        if selected_answer_id:
            selected_answer = get_object_or_404(Answer, id=selected_answer_id, related_question=question)
            is_correct = selected_answer.is_correct

            # Fortschritt speichern
            with transaction.atomic():
                progress, _ = QuestionProgress.objects.get_or_create(user=request.user, question=question)
                first_correct_answer = is_correct and progress.correct_attempts == 0

                if is_correct:
                    progress.correct_attempts += 1
                else:
                    progress.false_attempts += 1
                progress.save()

                if first_correct_answer:
                    statistics, _ = Statistics.objects.get_or_create(user=request.user)
                    statistics.total_score += question.points
                    statistics.save(update_fields=['total_score'])

            evaluated = True

    statistics, _ = Statistics.objects.get_or_create(user=request.user)

    context = {
        'question': question,
        'answers': answers,
        'statistics': statistics,
        'selected_answer': selected_answer,
        'is_correct': is_correct,
        'evaluated': evaluated,
    }
    return render(request, 'quiz/question.html', context)

 