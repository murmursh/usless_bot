

from crossword import extract_crossword_grid, matrix_to_crossword_image
from letters import extract_cyrillic_letters
from solver import solve_crossword_all
from words import get_words_data


# write tg bot that do that
# get token from env

# all conversation is made using inline buttons in one changeing message

screenshot = 'image.png' # gets from user message
matrix = extract_crossword_grid(screenshot)
pil_image = matrix_to_crossword_image(matrix) # returns to user
is_correct = True # ask user if crossword extracted correctly
if is_correct:
    letters = extract_cyrillic_letters(screenshot) # ask if correct if not ask them as text and save screenshot to ./bad/{date,user}.png
    words = get_words_data(letters)
    solution = solve_crossword_all(matrix, words) # send this to user it is list[list[word num: word]]
else:
    # save screenshot to ./bad/{date,user}.png
    letters = extract_cyrillic_letters(screenshot) # ask if correct if not ask them as text and save screenshot to ./bad/{date,user}.png
    words = get_words_data(letters) # send this to user. it is list[list[size, list[words]]]. limit words count to 10.
...


# import spacy

# # Установка: pip install spacy
# # Загрузка модели: python -m spacy download ru_core_news_sm

# def pos_tagging_spacy(text):
#     # Загрузка русской модели
#     nlp = spacy.load("ru_core_news_sm")
    
#     # Обработка текста
#     doc = nlp(text)
    
#     for token in doc:
#         yield {
#             'word': token.text,
#             'pos': token.pos_,
#         }
    
# with open('russian_words50.txt', 'r') as f:
#     data = f.read().replace('\n', ' ')
# # Пример использования
# result = pos_tagging_spacy(data)
# new_data = []
# for item in result:
#     if item['pos'] not in ['CCONJ', 'ADP', 'PART', 'PRON', 'AUX', 'SCONJ', 'PUNCT', 'DET']:
#         new_data.append(item['word'])
# with open('rus50_filter.txt', 'w') as f:
#     f.write('\n'.join(new_data))