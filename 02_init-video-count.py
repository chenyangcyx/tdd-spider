from db import Session, DBOperation


def main():
    print('02 init video count')
    session = Session()

    mids = DBOperation.query_member_mids(0, 999999, session)  # all mids

    for mid in mids:
        result = session.execute(
            'select count(1) from tdd_video where aid in (select distinct(v.aid) from tdd_video v left join tdd_video_staff s on v.aid = s.aid where v.mid = %d || s.mid = %d)'
            % (mid, mid))
        count = 0
        for r in result:
            count = r[0]
        print(mid, count)
        session.execute('update tdd_member set video_count = %d where mid = %d' % (count, mid))
        session.commit()

    session.close()


if __name__ == '__main__':
    main()
