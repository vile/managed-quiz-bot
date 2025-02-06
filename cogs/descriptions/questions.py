from typing import Final

# fmt: off
CMD_ADD_DESC: Final[str] = "Add a new question to a quiz's question bank. At least two total and one correct choice is required."
CMD_ADD_QUIZ_TYPE: Final[str] = "The slug/name of the quiz to add this question to."
CMD_ADD_IMAGE: Final[str] = "[Optional] A URL to an external image to display with this question."
CMD_ADD_QUESTION_TEXT: Final[str] = "Text content of question."
CMD_ADD_CORRECT_ANSWERS: Final[str] = "Using numbers, indicate the correct answer(s) (ie, A=1, B=2, etc.; '12' = A and B are correct)"
CMD_ADD_CORRECT_ANSWER_TEXT: Final[str] = "Text displayed when a user gets this question RIGHT."
CMD_ADD_INCORRECT_ANSWER_TEXT: Final[str] = "Text displayed when a user gets this question WRONG."
CMD_ADD_ANSWER_ONE: Final[str] = "[Required] Text content of answer A."
CMD_ADD_ANSWER_TWO: Final[str] = "[Required] Text content of answer B."
CMD_ADD_ANSWER_THREE: Final[str] = "[Optional] Text content of answer C."
CMD_ADD_ANSWER_FOUR: Final[str] = "[Optional] Text content of answer D."
CMD_ADD_ANSWER_FIVE: Final[str] = "[Optional] Text content of answer E."
CMD_REMOVE_DESC: Final[str] = "Remove an existing question from the question bank. This will also remove associated anwers."
CMD_REMOVE_QUESTION_ID: Final[str] = "The unique ID of the question to remove."
CMD_LIST_DESC: Final[str] = "List all questions for a specific quiz type."
CMD_LIST_QUIZ_TYPE: Final[str] = "The slug/name of the quiz to list questions for."
