from .recognition import model_path


def unknown_words(phrase, language='ru'):
    from vosk import Model
    path = model_path(language)
    if not (path / 'am' / 'final.mdl').is_file():
        raise RuntimeError('Модель Vosk не знайдено. Перевірте папку models.')
    model = Model(str(path))
    return [word for word in dict.fromkeys(phrase.split()) if model.vosk_model_find_word(word) < 0]
