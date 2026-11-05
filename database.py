from sqlalchemy import create_engine, Column, Integer, String, BigInteger, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

engine = create_engine('sqlite:///city_rpg_mega.db', connect_args={"check_same_thread": False})
Base = declarative_base()
Session = sessionmaker(bind=engine)

class User(Base):
    __tablename__ = 'users'
    id = Column(BigInteger, primary_key=True)
    nickname = Column(String, default="Игрок")
    city = Column(String, default="Не выбран")
    balance = Column(Integer, default=5000)
    bank_deposit = Column(Integer, default=0) # Деньги в банке
    donate_bal = Column(Integer, default=0)   # Кристаллы
    vip = Column(Integer, default=0)          # Время VIP
    role = Column(String, default="Гражданин")
    gov_rank = Column(String, default="Нет")
    weapon = Column(String, default="Кулаки")
    car = Column(String, default="Пешком")
    estate = Column(String, default="Общежитие")
    job = Column(String, default="Безработный")
    business = Column(String, default="Нет")
    energy = Column(Integer, default=100)
    jail_time = Column(Integer, default=0)
    wanted = Column(Integer, default=0)
    is_registered = Column(Integer, default=0)

class Clan(Base):
    __tablename__ = 'clans'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    owner_id = Column(BigInteger)
    balance = Column(Integer, default=0)

class MarketItem(Base):
    __tablename__ = 'market'
    id = Column(Integer, primary_key=True)
    seller_id = Column(BigInteger)
    item_name = Column(String)
    price = Column(Integer)

Base.metadata.create_all(engine)

def get_db():
    return Session()

def get_user(user_id):
    session = get_db()
    user = session.query(User).filter_by(id=user_id).first()
    if not user:
        user = User(id=user_id)
        session.add(user)
        session.commit()
    session.close()
    return user
