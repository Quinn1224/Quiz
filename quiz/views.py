import random
from django.http import HttpRequest
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from .models import (
    Answer,
    Category,
    Question,
    QuestionGroup,
    QuestionProgress,
    Statistics,
)

# Create your views here.
@login_required
def next_question_view(request : HttpRequest):
    user = request.user

    question_pool = Question.objects.filter(type='mutiple_choice')
    group_id = request.GET.get('group')
    if group_id:
        current_time = timezone.now()
        question_group = get_object_or_404(
            QuestionGroup.objects.filter(
                is_published=True,
                user_group__in=user.groups.all(),
            )
            .filter(
                Q(available_from__isnull=True)
                | Q(available_from__lte=current_time),
                Q(due_date__isnull=True) | Q(due_date__gte=current_time),
            )
            .distinct(),
            pk=group_id,
        )
        question_pool = question_pool.filter(
            group_items__question_group=question_group,
        )

    selected_categories = request.GET.getlist('category')
    if selected_categories:
        category_ids = [
            category_id
            for category_id in selected_categories
            if category_id.isdecimal()
        ]
        question_pool = question_pool.filter(category_id__in=category_ids)

    solved_question_ids = QuestionProgress.objects.filter(
        user=user,
        correct_attempts__gt=0,
    ).values_list('question_id', flat=True)
    open_questions = question_pool.exclude(id__in=solved_question_ids).distinct()

    if(open_questions.exists()):
        question = random.choice(list(open_questions))
    else: 
        all_questions = question_pool.distinct()
        if not all_questions.exists():
            return render(request, 'quiz/no_questions.html')

        question = random.choice(list(all_questions))
    return redirect('quiz:question_detail', question_id=question.id)

@login_required
def dashboard_view(request: HttpRequest):
    user = request.user
    statistics = Statistics.objects.filter(user=user).first()
    total_questions = Question.objects.filter(type='mutiple_choice').count()
    solved_questions = QuestionProgress.objects.filter(
        user=user,
        correct_attempts__gt=0,
        question__type='mutiple_choice',
    ).count()
    progress_percent = round(solved_questions / total_questions * 100) if total_questions else 0

    current_time = timezone.now()
    question_groups = (
        QuestionGroup.objects.filter(
            is_published=True,
            user_group__in=user.groups.all(),
        )
        .filter(
            Q(available_from__isnull=True) | Q(available_from__lte=current_time),
            Q(due_date__isnull=True) | Q(due_date__gte=current_time),
        )
        .distinct()
        .annotate(
            total_questions=Count(
                'items',
                filter=Q(items__question__type='mutiple_choice'),
                distinct=True,
            ),
            completed_questions=Count(
                'items__question__question_progress',
                filter=Q(
                    items__question__type='mutiple_choice',
                    items__question__question_progress__user=user,
                    items__question__question_progress__correct_attempts__gt=0,
                ),
                distinct=True,
            ),
        )
        .order_by('-created')
    )

    context = {
        'categories': Category.objects.order_by('name'),
        'question_groups': question_groups,
        'total_score': statistics.total_score if statistics else 0,
        'total_questions': total_questions,
        'solved_questions': solved_questions,
        'progress_percent': progress_percent,
        'gauge_rotation': round(progress_percent * 1.8 - 90),
    }
    return render(request, 'quiz/dashboard.html', context)


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

@login_required
def leaderboard_view(request : HttpRequest):
    stats = Statistics.objects.select_related('user').order_by('-total_score', 'user__username')

    context = {
        'statistics': stats,
    }
    return render(request, 'quiz/leaderboard.html', context)
