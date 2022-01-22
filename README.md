# homeworks_bot
## _Telegram bot checking status updates on API yandex prakcikum homeworks_
## _Телеграм бот для информирования об изменении статуса проверки домашних работ студентов Яндекс Практикума._
## Функции

- для каждого чата имеется возможность добавить (удалить/запустить/остановить) курсы проверку изменения статусов домашних работ по которым необходимо выполнять
- один раз в 10 минут производится запрос к API сервиса Практикум.Домашка (https://praktikum.yandex.ru/api/user_api/homework_statuses/) доступ к которому возможен только по токену
- сообщения о работах статус которых изменился за период с последнего запроса до настоящего момента прийдут в чат студента

## Технологии

homeworks_bot использует для работы следующие технологии:

- [Python 3.10.2] - Python мощный и быстрый язык программирования; хорошо работает с другими языками;
мультиплатформенный; дружелюбен и прост в освоении; открыт.
- [python-telegram-bot 13.7] -Эта библиотека предоставляет чистый интерфейс Python для Telegram Bot API . Он совместим с версиями Python 3.6.8+. Помимо реализации чистого API, эта библиотека содержит ряд высокоуровневых классов, упрощающих разработку ботов.
- [requests 2.26.0] Requests — это элегантная и простая HTTP-библиотека для Python, созданная для людей.
Многие веб-приложения используют API для подключения к различным сторонним сервисам. Поскольку при использовании API отправляются запросы HTTP и получаются ответы, библиотека Requests открывает возможность использования API в Python. 
- [SQLAlchemy 1.4.30] SQLAlchemy — это программная библиотека на языке Python для работы с реляционными СУБД с применением технологии ORM. Служит для синхронизации объектов Python и записей реляционной базы данных. SQLAlchemy позволяет описывать структуры баз данных и способы взаимодействия с ними на языке Python без использования SQL.

### Запуск проекта
- Установите и активируйте виртуальное окружение
- Установите зависимости из файла requirements.txt
```
pip install -r requirements.txt
``` 
```
### Авторы
Таранец Николай

## License

MIT

**Free Software, Hell Yeah!**



[//]: # (These are reference links used in the body of this note and get stripped out when the markdown processor does its job. There is no need to format nicely because it shouldn't be seen. Thanks SO - http://stackoverflow.com/questions/4823468/store-comments-in-markdown-syntax)
   [Python 3.10.2]: <https://www.python.org/downloads/release/python-3102/>
   [python-telegram-bot 13.7]: <https://github.com/python-telegram-bot/python-telegram-bot>
   [requests 2.26.0]: <https://github.com/psf/requests>
   [SQLAlchemy 1.4.30]: <https://pypi.org/project/SQLAlchemy/1.4.31/#files>
