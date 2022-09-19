# underground-chat
 
Скрипты для чтения и отправки сообщений в анонимный чат Майнкрафт-сообщества.

## Как установить

Для работы скриптов нужен Python версии не ниже 3.6.

```sh
pip install -r requirements.txt
```

## Как запустить

Чтение чата:
```sh
python read_chat.py
```

Отправка сообщения:
```sh
python send_message.py "<MESSAGE>"
```

Запустите скрипты с флагом `-h`, чтобы узнать порядок вызова с аргументами.

Параметры скриптов можно задать в файле `.env`:

```sh
HOST=
READING_PORT=
WRITING_PORT=
HISTORY_FILE=
CHAT_NICKNAME=
CHAT_TOKEN=
```

# Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).
