from .basic import Base
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.dialects.mysql import LONGTEXT, TINYINT

__all__ = ['TddVideo', 'TddMember', 'TddVideoStaff']


class TddVideo(Base):
    """tdd_video table"""

    __tablename__ = 'tdd_video'

    id = Column(Integer, primary_key=True, nullable=False, unique=True, autoincrement=True)
    added = Column(Integer, nullable=False)
    aid = Column(Integer, nullable=False, unique=True)
    videos = Column(Integer, default=None)
    tid = Column(Integer, default=None)
    tname = Column(String(30), default=None)
    copyright = Column(Integer, default=None)
    pic = Column(String(200), default=None)
    title = Column(String(200), nullable=False)
    pubdate = Column(Integer, default=None)
    desc = Column(LONGTEXT, default=None)
    tags = Column(String(500), default=None)
    mid = Column(Integer, default=None)
    code = Column(Integer, nullable=False, default=0)  # TODO how to enable nullable=False and have default value
    hasstaff = Column(TINYINT, nullable=False, default=0)  #
    singer = Column(String(200), nullable=False, default='未定义')  #
    solo = Column(TINYINT, nullable=False, default=-1)  #
    original = Column(TINYINT, nullable=False, default=-1)  #
    employed = Column(Integer, nullable=False, default=-1)  #
    freq = Column(TINYINT, nullable=False, default=0)  #

    def __repr__(self):
        return "<TddVideo(aid=%d,title=%s)>" % (self.aid, self.title)


class TddMember(Base):
    """tdd_member table"""

    __tablename__ = 'tdd_member'

    id = Column(Integer, primary_key=True, nullable=False, unique=True, autoincrement=True)
    added = Column(Integer, nullable=False)
    mid = Column(Integer, nullable=False, unique=True)
    sex = Column(String(20), nullable=False)
    name = Column(String(100), nullable=False)
    face = Column(String(200), nullable=False)
    sign = Column(String(500), nullable=False, default='')  #

    def __repr__(self):
        return "<TddMember(mid=%d,name=%s)>" % (self.mid, self.name)


class TddVideoStaff(Base):
    """tdd_video_staff table"""

    __tablename__ = 'tdd_video_staff'

    id = Column(Integer, primary_key=True, nullable=False, unique=True, autoincrement=True)
    added = Column(Integer, nullable=False)
    aid = Column(Integer, nullable=False)
    mid = Column(Integer, nullable=False)
    title = Column(String(30), nullable=False)

    def __repr__(self):
        return "<TddVideoStaff(aid=%d,mid=%d)>" % (self.aid, self.mid)


class TddVideoRecord(Base):
    """tdd_video_record table"""

    __tablename__ = 'tdd_video_record'

    id = Column(Integer, primary_key=True, nullable=False, unique=True, autoincrement=True)
    added = Column(Integer, nullable=False)
    aid = Column(Integer, nullable=False)
    view = Column(Integer, nullable=False)
    danmaku = Column(Integer, nullable=False)
    reply = Column(Integer, nullable=False)
    favorite = Column(Integer, nullable=False)
    coin = Column(Integer, nullable=False)
    share = Column(Integer, nullable=False)
    like = Column(Integer, nullable=False)

    def __repr__(self):
        return "<TddVideoRecord(aid=%d,view=%d)>" % (self.aid, self.view)


class TddMemberFollowerRecord(Base):
    """tdd_member_follower_record table"""

    __tablename__ = 'tdd_member_follower_record'

    id = Column(Integer, primary_key=True, nullable=False, unique=True, autoincrement=True)
    added = Column(Integer, nullable=False)
    mid = Column(Integer, nullable=False)
    follower = Column(Integer, nullable=False)

    def __repr__(self):
        return '<TddMemberFollowerRecord(mid=%d,follower=%d)>' % (self.mid, self.follower)
