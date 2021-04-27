from enum import Enum
import random
from html import unescape

import requests

class QuestionDifficulty(Enum):
    easy   = 1
    medium = 2
    hard   = 3

class QuestionType(Enum):
    multiple = 1
    boolean  = 2

class Question:
    __slots__ = ("type", "category", "difficulty", "question", "answers")

    def __init__(self, type, category, difficulty, question, answers):
        self.type       = type
        self.category   = category
        self.difficulty = difficulty
        self.question   = question
        self.answers    = answers

    def get_answer(self, value):
        for answer in self.answers:
            if answer.value == value:
                return answer

    def __str__(self):
        return f"question = {self.question}, type = {self.type}, category = {self.category}"

class Answer:
    __slots__ = ("value", "is_correct")

    def __init__(self, value, is_correct = False):
        self.value      = value
        self.is_correct = is_correct

class Category(Enum):
    id_9  = "General Knowledge"
    id_10 = "Entertainment: Books"
    id_11 = "Entertainment: Film"
    id_12 = "Entertainment: Music"
    id_13 = "Entertainment: Musicals & Theatres"
    id_14 = "Entertainment: Television"
    id_15 = "Entertainment: Video Games"
    id_16 = "Entertainment: Board Games"
    id_17 = "Science & Nature"
    id_18 = "Science: Computers"
    id_19 = "Science: Mathematics"
    id_20 = "Mythology"
    id_21 = "Sports"
    id_22 = "Geography"
    id_23 = "History"
    id_24 = "Politics"
    id_25 = "Art"
    id_26 = "Celebrities"
    id_27 = "Animals"
    id_28 = "Vehicles"
    id_29 = "Entertainment: Comics"
    id_30 = "Science: Gadgets"
    id_31 = "Entertainment: Japanese Anime & Manga"
    id_32 = "Entertainment: Cartoon & Animations"

class TriviaApi:
    base_url = "https://opentdb.com"

    @classmethod
    def get_questions(cls, amount: int = 10, category: Category = None, difficulty: QuestionDifficulty = None, type: QuestionType = None):
        url = cls.base_url + "/" + "api.php"
        kwargs = {"amount": amount}

        if category is not None:
            kwargs["category"] = category.name.replace("id_", "")

        if difficulty is not None:
            kwargs["difficulty"] = difficulty.name

        if type is not None:
            kwargs["type"] = type.name

        request = requests.get(url, params=kwargs)
        json = request.json()
        for question in json["results"]:
            type = QuestionType[question["type"]]
            category = Category(question["category"])
            difficulty = QuestionDifficulty[question["difficulty"]]
            value = unescape(question["question"])
            value = value.replace("&quot;", "'")

            answers = []
            answers.append(Answer(unescape(question["correct_answer"]), is_correct = True))
            for answer in question["incorrect_answers"]:
                answers.append(Answer(unescape(answer), is_correct = False))
            random.shuffle(answers)

            yield Question(
                type = type,
                category = category,
                difficulty = difficulty,
                question = value,
                answers = answers
            )

    def get_categories(self):
        url = self.base_url + "/" + "api_category.php"
        request = requests.get(url)
        json = request.json()
        i = 0
        for category in json["trivia_categories"]:
            id = category["id"]
            print(f'{id}')

if __name__ == "__main__":
    api = TriviaApi()
    for question in api.get_questions(
        amount = 10,
        difficulty = QuestionDifficulty.easy,
        category = Category.id_27,
        type = QuestionType.boolean
    ):
        print(question)