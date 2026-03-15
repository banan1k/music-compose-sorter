# music-compose-sorter

CLI tool for mass sorting music libraries, fetching metadata from MusicBrainz, optional fingerprinting via AcoustID/Chromaprint.

## Установка

Создайте виртуальное окружение и установите зависимости:

```bash
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> Если вы хотите использовать fingerprinting, установите Chromaprint C library (OS-dependent) и затем `pip install pyacoustid`.

## Конфигурация

Скопируйте `examples/config_example.toml` в `~/.config/music_sorter/config.toml` и отредактируйте `acoustid_api_key` и `user_agent`.

## Примеры

Сканируем директорию:

```bash
music-sorter scan ~/Music
```

Обрабатываем queued файлы (dry-run):

```bash
music-sorter process --dry-run
```

Восстанавливаем теги:

```bash
music-sorter restore
```

## Важное

- По умолчанию инструмент интерактивен: при неоднозначности он предложит варианты и будет ждать 30s, после чего сделает авто-выбор и занесёт запись в `conflicts`.
    
- Backup оригинальных тегов сохраняется в `~/.local/share/music_sorter/backups` (или в config.backup_dir).
    

---

