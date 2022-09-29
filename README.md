# underground-chat
 
Скрипты для чтения и отправки сообщений в анонимный чат Майнкрафт-сообщества.

## Как установить

Для работы скриптов нужен Python версии не ниже 3.6.

```sh
pip install -r requirements.txt
```

## Как запустить

Главное окно чата:
```sh
python main.py
```

![image](https://user-images.githubusercontent.com/84133942/193020007-9d34db9e-ac66-4f63-a2a0-4dd3e4d89958.png)

Регистрация пользователя:
```sh
python reg.py
```

![image](https://user-images.githubusercontent.com/84133942/193019832-b8ef9245-c2b1-48dd-ae81-51bec41730d5.png)

После регистрации токен сохранится в файл вида `<nickname>.token`. Чтобы его использовать, запустите:
```sh
python main.py -t <token>
```

Также можно пользоваться скриптами с консольным интерфейсом.

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
SMALL_RECONNECT_TIMEOUT=
BIG_RECONNECT_TIMEOUT=
HOST=
READING_PORT=
WRITING_PORT=
HISTORY_FILE=
CHAT_NICKNAME=
CHAT_TOKEN=
```

# Цели проекта

Код написан в учебных целях — это урок в курсе по Python и веб-разработке на сайте [Devman](https://dvmn.org).
