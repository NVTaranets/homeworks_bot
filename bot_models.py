# импортируем классы, используемые для определения атрибутов модели
from sqlalchemy import Boolean, BigInteger, Column, Integer, String, UniqueConstraint
# объект для подключения ядро базы данных
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Telegram(Base):
    """Класс модели для обеспечения доступа к данным."""

    __tablename__ = "telegram"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    chat_id = Column(Integer)
    practicum_token = Column(String, unique=True)
    started = Column(Boolean)
    __table_args__ = (
        UniqueConstraint('name', 'chat_id', name='_name_chat_id_uc'),
    )
