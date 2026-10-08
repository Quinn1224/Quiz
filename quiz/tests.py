from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Answer, Category, Question, QuestionProgress, Statistics


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
