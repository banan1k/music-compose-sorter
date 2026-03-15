# music-compose-sorter

CLI-инструмент для **массовой сортировки музыкальной библиотеки**, поиска и встраивания метаданных, обработки обложек и организации файлов по структуре Artist → Album → Track.

Программа рассчитана на **большие библиотеки (тысячи файлов)** и может безопасно работать даже если процесс был прерван — состояние сохраняется в SQLite.

---

# Основные возможности

* поддержка форматов: **mp3, flac, m4a, ogg**
* автоматический поиск метаданных через MusicBrainz
* опциональная идентификация по **аудио-отпечатку (Chromaprint + AcoustID)**
* интерактивное разрешение конфликтов
* кэширование метаданных и обложек
* безопасное обновление тегов (с резервной копией)
* восстановление оригинальных тегов
* логирование ошибок
* возобновление обработки после сбоя
* dry-run режим (анализ без изменений)

---

# Архитектура обработки

При обработке каждого файла используется следующая логика:

1. чтение существующих тегов
2. извлечение названия из имени файла
3. поиск совпадений в MusicBrainz
4. при неоднозначности — fingerprint
5. интерактивный выбор варианта
6. обновление тегов
7. сохранение backup
8. перенос файла в новую структуру

Приоритет идентификации:

```
fingerprint
   >
MusicBrainz search
   >
existing metadata
   >
filename
```

---

# Требования

```
Python 3.10+
```

---

# Установка

## 1. Клонировать репозиторий

```
git clone <repo>
cd music_compose_sorter
```

---

## 2. Создать виртуальное окружение

Linux / macOS

```
python3.10 -m venv venv
source venv/bin/activate
```

Windows

```
python -m venv venv
venv\Scripts\activate
```

---

## 3. Установить зависимости

```
pip install -r requirements.txt
```

---

# Опционально: поддержка fingerprint

Если хотите использовать идентификацию по аудио-отпечатку:

нужно установить **Chromaprint**

Linux:

```
sudo apt install chromaprint-tools
```

macOS:

```
brew install chromaprint
```

Затем:

```
pip install pyacoustid
```

После этого получите API ключ:

https://acoustid.org

и добавьте его в конфиг.

---

# Конфигурация

Создайте файл:

```
~/.config/music_comp_sorter/config.toml
```

Пример:

```
[music_comp_sorter]

db_path = "~/.local/share/music_comp_sorter/state.db"
metadata_cache_dir = "~/.local/share/music_comp_sorter/cache"
backup_dir = "~/music_comp_sorter_backups"

musicbrainz_rate_limit = 1.0
network_threads = 4
file_threads = 4

library_output_dir = "~/MusicSorted"

export_covers = true
cover_export_mode = "global"

fingerprint_enabled = true

acoustid_api_key = "YOUR_API_KEY"
```

---

# Режимы экспорта обложек

### album
обложка хранится в папке альбома
```
Artist/
   Album/
       cover.jpg
```
---
### artist
создаётся папка обложек артиста
```
Artist/
   covers/
       album.jpg
```
---
### global (по умолчанию)
все обложки сохраняются в одной папке
```
covers/
   album - artist.jpg
```
---

# Рабочие директории

После запуска создаются:

```
~/.local/share/music_comp_sorter/
```

```
state.db
cache/
logs/
```

Логи:

```
logs/errors.log
```

---


# Как пользоваться программой (STEP BY STEP)

Это **полный рабочий цикл**.

---

# Шаг 1 — Сканирование библиотеки

Сканируем папку с музыкой.

```
python -m music_comp_sorter.cli scan ~/Music
```

Что происходит:

* программа проходит по директории
* находит поддерживаемые форматы
* добавляет их в базу
* неподдерживаемые файлы помечаются как skipped

Ничего не изменяется в файлах.

---

# Шаг 2 — Проверка статуса

Можно посмотреть состояние базы:

```
music-comp-sorter status
```

Показывает:

```
pending
processing
done
error
skipped
```

---

# Шаг 3 — Тестовый запуск (dry-run)

Перед реальной обработкой рекомендуется проверить:

```
python -m music_comp_sorter.cli process --dry-run
```

В этом режиме:

* файлы **НЕ изменяются**
* теги **НЕ записываются**
* показывается только анализ

Это безопасный тест.

---

# Шаг 4 — Основная обработка

Теперь запускаем реальную обработку.

```
python -m music_comp_sorter.cli process
```

Программа:

1. читает файл из базы
2. ищет метаданные
3. при необходимости задаёт вопрос пользователю
4. записывает теги
5. сохраняет backup
6. обновляет базу

---

# Шаг 5 — Разрешение конфликтов

Если найдено несколько вариантов:

программа покажет список:

```
1. Artist - Track (Album 2003)
2. Artist - Track (Remaster 2012)
3. Artist - Track (Single)
```

Нужно ввести номер.

Если пользователь **не ответил 30 секунд**:

программа автоматически выбирает лучший вариант и записывает конфликт в базу.

---

# Шаг 6 — Ручная проверка конфликтов

Запустить инструмент:

```
python -m music_comp_sorter.review_ambiguous
```

Он покажет все неоднозначные записи и позволит выбрать правильный вариант.

---

# Шаг 7 — Возобновление после сбоя

Если программа была прервана (например отключили питание):

достаточно запустить снова:

```
python -m music_comp_sorter.cli process
```

Обработка продолжится с последнего состояния.

---

# Шаг 8 — Восстановление оригинальных тегов

Если что-то пошло не так:

```
python -m music_comp_sorter.cli restore
```

Ввести путь к файлу.

Программа восстановит данные из:

```
original_metadata.json
```

---

# Режимы обработки дубликатов

Можно настроить стратегию:

```
keep_both
replace_singles_with_album_versions
replace_album_with_single_versions
```

Пример:

```
python -m music_comp_sorter.cli process --mode keep_both
```

---

# Поддерживаемые форматы

```
mp3
flac
m4a
ogg
```

Другие форматы:

```
wav
aac
wma
```

будут **пропущены**.

---

# Логи

Ошибки пишутся в:

```
~/.local/share/music_comp_sorter/logs/errors.log
```

Пример:

```
WARNING Unsupported format: song.wav
ERROR MusicBrainz search failed
```

---

# Тесты

Запуск unit-тестов:

```
pytest
```

---

# Производительность

Программа оптимизирована для библиотек **до 4000+ файлов**.

Используются:

* многопоточность для чтения тегов
* ограничение скорости для API
* локальный кеш метаданных

---

# Типичные проблемы

## MusicBrainz rate limit

Если появляются ошибки:

```
503 Service Unavailable
```

уменьшите:

```
musicbrainz_rate_limit
```

---

## Fingerprint не работает

Проверьте:

```
chromaprint
```

и

```
acoustid_api_key
```

---

# Безопасность

Перед каждым изменением тегов сохраняется:

```
original_metadata.json
```

Поэтому любые изменения можно отменить.

---

# Лицензия

MIT
