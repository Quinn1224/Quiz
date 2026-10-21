from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup

from .models import (
    Answer,
    Category,
    Question,
    QuestionGroup,
    QuestionGroupItem,
    QuestionProgress,
    Statistics,
)


class QuizModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Geografie")
        self.question = Question.objects.create(
            text="Was ist die Hauptstadt von Frankreich?",
            category=self.category,
        )

    def test_question_has_expected_fields(self):
        self.assertEqual(self.question.text, "Was ist die Hauptstadt von Frankreich?")
        self.assertEqual(self.question.category, self.category)

    def test_question_str_returns_text(self):
        self.assertEqual(str(self.question), self.question.text)


class QuizViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="quiz-user",
            password="test-password",
        )
        self.client.force_login(self.user)
        category = Category.objects.create(name="Biologie")
        self.question = Question.objects.create(
            text="Welches Tier ist ein Säugetier?",
            category=category,
            points=5,
        )
        self.wrong_answer = Answer.objects.create(
            related_question=self.question,
            text="Hai",
        )
        self.correct_answer = Answer.objects.create(
            related_question=self.question,
            text="Delphin",
            is_correct=True,
        )

    def test_next_question_redirects_to_a_question(self):
        response = self.client.get(reverse("quiz:next_question"))
        self.assertRedirects(
            response,
            reverse("quiz:question_detail", args=[self.question.pk]),
        )

    def test_next_question_filters_by_selected_category(self):
        geography = Category.objects.create(name="Geografie")
        geography_question = Question.objects.create(
            text="Welche Stadt liegt an der Isar?",
            category=geography,
        )

        response = self.client.get(
            reverse("quiz:next_question"),
            {"category": geography.pk},
        )

        self.assertRedirects(
            response,
            reverse("quiz:question_detail", args=[geography_question.pk]),
        )

    def test_dashboard_shows_assigned_tasks_and_progress(self):
        auth_group = AuthGroup.objects.create(name="Spieler")
        self.user.groups.add(auth_group)
        task = QuestionGroup.objects.create(
            title="Wöchentlicher Test",
            description="Wöchentlicher Wissenstest",
            is_published=True,
        )
        task.user_group.add(auth_group)
        QuestionGroupItem.objects.create(question_group=task, question=self.question)
        second_question = Question.objects.create(
            text="Welches Tier legt Eier?",
            category=self.question.category,
        )
        QuestionGroupItem.objects.create(
            question_group=task,
            question=second_question,
            position=1,
        )
        QuestionProgress.objects.create(
            user=self.user,
            question=self.question,
            correct_attempts=1,
        )

        response = self.client.get(reverse("quiz:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Dashboard")
        self.assertContains(response, "quiz-user")
        self.assertContains(response, task.title)
        self.assertContains(response, "In Bearbeitung")
        self.assertContains(
            response,
            '<p class="dashboard-progress-percent">50<span>%</span></p>',
            html=True,
        )
        self.assertContains(response, "Biologie")

    def test_dashboard_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("quiz:dashboard"))

        self.assertRedirects(
            response,
            f"{reverse('quiz:login')}?next={reverse('quiz:dashboard')}",
        )

    def test_question_page_contains_question_text(self):
        response = self.client.get(
            reverse("quiz:question_detail", args=[self.question.pk])
        )
        self.assertContains(response, self.question.text)

    def test_submit_correct_answer_marks_question_as_correct(self):
        response = self.client.post(
            reverse("quiz:question_detail", args=[self.question.pk]),
            {"answer": self.correct_answer.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Richtig")
        progress = QuestionProgress.objects.get(user=self.user, question=self.question)
        self.assertEqual(progress.correct_attempts, 1)
        self.assertEqual(progress.false_attempts, 0)
        self.assertEqual(Statistics.objects.get(user=self.user).total_score, 5)

    def test_submit_wrong_answer_marks_question_as_wrong(self):
        response = self.client.post(
            reverse("quiz:question_detail", args=[self.question.pk]),
            {"answer": self.wrong_answer.pk},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Deine Antwort")
        progress = QuestionProgress.objects.get(user=self.user, question=self.question)
        self.assertEqual(progress.correct_attempts, 0)
        self.assertEqual(progress.false_attempts, 1)
        self.assertEqual(Statistics.objects.get(user=self.user).total_score, 0)

    def test_leaderboard_lists_users_by_total_score(self):
        other_user = get_user_model().objects.create_user(username="top-player")
        Statistics.objects.create(user=self.user, total_score=5)
        Statistics.objects.create(user=other_user, total_score=20)

        response = self.client.get(reverse("quiz:leaderboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Leaderboard")
        self.assertContains(response, "top-player")
        self.assertContains(response, "quiz-user")
        table_body = response.content.split(b"<tbody>", 1)[1].split(b"</tbody>", 1)[0]
        self.assertLess(
            table_body.index(b"top-player"),
            table_body.index(b"quiz-user"),
        )

    def test_leaderboard_requires_login(self):
        self.client.logout()

        response = self.client.get(reverse("quiz:leaderboard"))

        self.assertRedirects(
            response,
            f"{reverse('quiz:login')}?next={reverse('quiz:leaderboard')}",
        )
