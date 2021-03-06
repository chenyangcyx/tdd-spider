import schedule
import threading
import time
import datetime
from logger import logger_11, logger_11_c0, logger_11_c30
from pybiliapi import BiliApi
import math
from db import Session, DBOperation, TddVideoRecord
from util import get_ts_s, ts_s_to_str, a2b
from common import get_valid, test_video_view, test_video_stat, test_archive_rank_by_partion, \
    add_video_record_via_stat_api, add_video_record_via_awesome_stat, add_video, add_video_via_bvid, \
    TddCommonError, InvalidObjCodeError, AlreadyExistError
from serverchan import sc_send


def update_aids_c0(aids):
    logger_11.info('Now update c0 aids...')
    logger_11_c0.info('Now update c0 aids...')
    bapi = BiliApi()
    session = Session()

    aids_len = len(aids)  # aids len
    start_ts = get_ts_s()  # get start ts

    fail_aids = []  # aids fail to get valid stat obj
    main_loop_visit_count = aids_len  # aids visited count
    main_loop_add_count = 0  # aids added count

    for aid in aids:

        # add video record
        try:
            new_video_record = add_video_record_via_stat_api(aid, bapi, session)
        except InvalidObjCodeError as e:
            DBOperation.update_video_code(aid, e.code, session)
            logger_11_c0.warning('Update video aid = %d code from 0 to %d.' % (aid, e.code))
        except TddCommonError as e:
            logger_11_c0.warning(e)
            fail_aids.append(aid)
        else:
            logger_11_c0.debug('Add new record %s' % new_video_record)

        main_loop_add_count += 1  # add main loop add count
        time.sleep(0.2)  # api duration banned

    # fail aids, need further check
    logger_11_c0.warning('Fail aids: %s' % fail_aids)

    # get finish ts
    finish_ts = get_ts_s()

    # make summary
    summary = \
        '11 updating c0 aids done\n\n' + \
        'start: %s, finish: %s, timespan: %ss\n\n' \
        % (ts_s_to_str(start_ts), ts_s_to_str(finish_ts), (finish_ts - start_ts)) + \
        'target aids count: %d\n\n' % aids_len + \
        'main loop: visited: %d, added: %s, others: %d\n\n' \
        % (main_loop_visit_count, main_loop_add_count, (main_loop_visit_count - main_loop_add_count)) + \
        'fail aids: %s, count: %d\n\n' % (fail_aids, len(fail_aids)) + \
        'by.bunnyxt, %s' % ts_s_to_str(get_ts_s())

    logger_11.info('Finish updating c0 aids!')
    logger_11_c0.info('Finish updating c0 aids!')

    logger_11.warning(summary)
    logger_11_c0.warning(summary)

    # send sc
    sc_result = sc_send('Finish updating c0 aids!', summary)
    if sc_result['errno'] == 0:
        logger_11_c0.info('Sc summary sent successfully.')
    else:
        logger_11_c0.warning('Sc summary sent wrong. sc_result = %s.' % sc_result)

    session.close()


def update_aids_c30(aids):
    logger_11.info('Now update c30 aids...')
    logger_11_c30.info('Now update c30 aids...')
    bapi = BiliApi()
    session = Session()

    aids_len = len(aids)  # aids len
    start_ts = get_ts_s()  # get start ts

    # calculate page total num
    obj = get_valid(bapi.get_archive_rank_by_partion, (30, 1, 50), test_archive_rank_by_partion)
    page_total = math.ceil(obj['data']['page']['count'] / 50)

    not_added_aids = []  # aids in api page but not in db c30 aids
    last_page_aids = []  # aids added in last page
    this_page_aids = []  # aids added in this page
    main_loop_visit_count = 0  # aids visited count
    main_loop_add_count = 0  # aids added count

    page_num = 1
    while page_num <= page_total:
        # get obj via awesome api
        obj = get_valid(bapi.get_archive_rank_by_partion, (30, page_num, 50), test_archive_rank_by_partion)
        if obj is None:
            logger_11_c30.warning('Page num %d fail! Cannot get valid obj.' % page_num)
            page_num += 1
            continue

        # record obj request ts
        added = get_ts_s()

        try:
            # process each video in archives
            for arch in obj['data']['archives']:
                # get video aid
                aid = arch['aid']
                main_loop_visit_count += 1  # add main loop visit count

                if aid in last_page_aids:
                    # aid added in last page, continue
                    logger_11_c30.warning('Aid %d already added in last page (page_num = %d).' % (aid, page_num - 1))
                    continue

                if aid in aids:
                    # aid in db c30 aids, go add video record, get stat first
                    stat = arch['stat']

                    # add stat record, which comes from awesome api
                    try:
                        new_video_record = add_video_record_via_awesome_stat(added, stat, session)
                    except TddCommonError as e:
                        logger_11_c30.warning(e)
                    else:
                        logger_11_c30.debug('Add new video record %s' % new_video_record)

                    this_page_aids.append(aid)  # add aid to this page aids
                    aids.remove(aid)  # remove aid from aids
                    main_loop_add_count += 1  # add main loop add count
                else:
                    # aid not in db c30 aids, maybe video not added in db
                    # logger_11_c30.warning('Aid %d not in update aids.' % aid)
                    not_added_aids.append(aid)  # add to not added aids
        except Exception as e:
            logger_11_c30.error(
                'Exception caught when process each video in archives. page_num = %d. Detail: %s' % (page_num, e))

        # assign this page aids to last page aids and reset it
        last_page_aids = this_page_aids
        this_page_aids = []

        logger_11_c30.info('Page %d / %d done.' % (page_num, page_total))

        # update page num
        page_total = math.ceil(obj['data']['page']['count'] / 50)
        page_num += 1

    # finish main loop add record from awesome api
    logger_11_c30.warning(
        'Finish main loop, %d aid(s) visited, %d aids(s) added.' % (main_loop_visit_count, main_loop_add_count))

    # check aids left in aids
    # they are not found in the whole tid==30 videos via awesome api, maybe video code!=0
    logger_11_c30.warning('%d aid(s) left in c30 aids, now check them.' % len(aids))
    logger_11_c30.warning(aids)

    left_aids_visit_count = len(aids)  # aids visited count
    left_aids_solve_count = 0  # aids solved count

    for aid in aids:
        time.sleep(0.2)  # api duration banned
        # get view obj
        view_obj = get_valid(bapi.get_video_view, (aid,), test_video_view)
        if view_obj is None:
            logger_11_c30.warning('Aid %d fail! Cannot get valid view obj.' % aid)
            continue

        # record view obj request ts
        view_obj_added = get_ts_s()

        try:
            # get video code
            code = view_obj['code']

            if code == 0:
                # code==0, check tid next
                if 'tid' in view_obj['data'].keys():
                    # get video tid
                    tid = view_obj['data']['tid']
                    if tid != 30:
                        # video tid!=30 now, change tid
                        # TODO change update function here
                        DBOperation.update_video_tid(aid, tid, session)
                        DBOperation.update_video_isvc(aid, 5, session)
                        logger_11_c30.warning(
                            'Update video aid = %d tid from 30 to %d then update isvc = %d.' % (aid, tid, 5))
                    else:
                        # video tid==30, add video record
                        logger_11_c30.warning(
                            'Found aid = %d code == 0 and tid == 30! Now try add video record...' % aid)

                        # get stat first
                        stat = view_obj['data']['stat']

                        # make new tdd video record obj and assign stat info from api
                        new_video_record = TddVideoRecord()
                        new_video_record.aid = aid
                        new_video_record.added = view_obj_added
                        new_video_record.view = -1 if stat['view'] == '--' else stat['view']
                        new_video_record.danmaku = stat['danmaku']
                        new_video_record.reply = stat['reply']
                        new_video_record.favorite = stat['favorite']
                        new_video_record.coin = stat['coin']
                        new_video_record.share = stat['share']
                        new_video_record.like = stat['like']

                        # add to db
                        DBOperation.add(new_video_record, session)
                        logger_11_c30.info('Add record %s.' % new_video_record)

                        left_aids_solve_count += 1  # add left aids solve count
                else:
                    logger_11_c30.error('View obj %s got code == 0 but no tid field! Need further check!' % view_obj)
            else:
                # code!=0, change code
                DBOperation.update_video_code(aid, code, session)
                logger_11_c30.warning('Update video aid = %d code from 0 to %d.' % (aid, code))
                left_aids_solve_count += 1  # add left aids solve count
        except Exception as e:
            logger_11_c30.error('Exception caught when process view obj of left aid %d. Detail: %s' % (aid, e))

    # finish check aids left in aids
    logger_11_c30.warning(
        'Finish check aids left in aids, %d aid(s) visited, %d aids(s) solved.' % (
            left_aids_visit_count, left_aids_solve_count))

    # TODO check not added aids, maybe some video not added
    logger_11_c30.warning('%d aid(s) left in c30 not added aids, now check them.' % len(not_added_aids))
    logger_11_c30.warning(not_added_aids)

    not_added_aids_visit_count = len(not_added_aids)  # aids visited count
    not_added_aids_solve_count = 0  # aids solved count

    for aid in not_added_aids:

        # add video
        try:
            # new_video = add_video(aid, bapi, session)  TODO change to bvid totally
            new_video = add_video_via_bvid(a2b(aid), bapi, session)
        except AlreadyExistError:
            # video already exist, which is absolutely common
            pass
        except TddCommonError as e:
            logger_11_c30.warning(e)
        else:
            logger_11_c30.info('Add new video %s' % new_video)

        # add video record
        try:
            new_video_record = add_video_record_via_stat_api(aid, bapi, session)
        except InvalidObjCodeError as e:
            DBOperation.update_video_code(aid, e.code, session)
            logger_11_c30.warning('Update video aid = %d code from 0 to %d.' % (aid, e.code))
            not_added_aids_solve_count += 1  # solved, update video code
        except TddCommonError as e:
            logger_11_c30.warning(e)  # unsolved, fail to add record
        else:
            logger_11_c30.info('Add new record %s' % new_video_record)
            not_added_aids_solve_count += 1  # solved, add record

        time.sleep(0.2)  # api duration banned

    # finish check not added aids
    logger_11_c30.warning(
        'Finish check not added aids, %d aid(s) visited, %d aids(s) solved.' % (
            not_added_aids_visit_count, not_added_aids_solve_count))

    # get finish ts
    finish_ts = get_ts_s()

    # make summary
    summary = \
        '11 updating c30 aids done\n\n' + \
        'start: %s, finish: %s, timespan: %ss\n\n' \
        % (ts_s_to_str(start_ts), ts_s_to_str(finish_ts), (finish_ts - start_ts)) + \
        'target aids count: %d\n\n' % aids_len + \
        'main loop: visited: %d, added: %s, others: %d\n\n' \
        % (main_loop_visit_count, main_loop_add_count, (main_loop_visit_count - main_loop_add_count)) + \
        'aids left in aids: visited: %d, solved: %d, others: %d\n\n' \
        % (left_aids_visit_count, left_aids_solve_count, (left_aids_visit_count - left_aids_solve_count)) + \
        'not added aids: visited: %d, solved: %d, others: %d\n\n' \
        % (not_added_aids_visit_count, not_added_aids_solve_count,
           (not_added_aids_visit_count - not_added_aids_solve_count)) + \
        'by.bunnyxt, %s' % ts_s_to_str(get_ts_s())

    logger_11.info('Finish updating c30 aids!')
    logger_11_c30.info('Finish updating c30 aids!')

    logger_11.warning(summary)
    logger_11_c30.warning(summary)

    # send sc
    sc_result = sc_send('Finish updating c30 aids!', summary)
    if sc_result['errno'] == 0:
        logger_11_c30.info('Sc summary sent successfully.')
    else:
        logger_11_c30.warning('Sc summary sent wrong. sc_result = %s.' % sc_result)

    # tmp update recent field begin
    try:
        now_ts = get_ts_s()
        last_1d_ts = now_ts - 1 * 24 * 60 * 60
        last_7d_ts = now_ts - 7 * 24 * 60 * 60
        session.execute('update tdd_video set recent = 0 where added < %d' % last_7d_ts)
        session.commit()
        session.execute('update tdd_video set recent = 1 where added >= %d && added < %d' % (last_7d_ts, last_1d_ts))
        session.commit()
        session.execute('update tdd_video set recent = 2 where added >= %d' % last_1d_ts)
        session.commit()
        logger_11.info('Finish update recent field')
    except Exception as e:
        logger_11.error(e)
    # tmp update recent field end

    # tmp update activity field begin
    try:
        # update everyday
        this_week_ts_begin = int(time.mktime(time.strptime(str(datetime.date.today()), '%Y-%m-%d'))) + 4 * 60 * 60
        this_week_ts_end = this_week_ts_begin + 30 * 60
        this_week_results = session.execute(
            'select r.`aid`, `view` from tdd_video_record r join tdd_video v on r.aid = v.aid ' +
            'where r.added >= %d && r.added <= %d' % (this_week_ts_begin, this_week_ts_end))
        this_week_records = {}
        for result in this_week_results:
            aid = result[0]
            view = result[1]
            if aid in this_week_records.keys():
                last_view = this_week_records[aid]
                if view > last_view:
                    this_week_records[aid] = view
            else:
                this_week_records[aid] = view

        last_week_ts_begin = this_week_ts_begin - 7 * 24 * 60 * 60
        last_week_ts_end = last_week_ts_begin + 30 * 60
        last_week_results = session.execute(
            'select r.`aid`, `view` from tdd_video_record r join tdd_video v on r.aid = v.aid ' +
            'where r.added >= %d && r.added <= %d' % (last_week_ts_begin, last_week_ts_end))
        last_week_records = {}
        for result in last_week_results:
            aid = result[0]
            view = result[1]
            if aid in last_week_records.keys():
                last_view = last_week_records[aid]
                if view < last_view:
                    last_week_records[aid] = view
            else:
                last_week_records[aid] = view

        last_week_record_keys = last_week_records.keys()
        diff_records = {}
        for aid in this_week_records.keys():
            if aid in last_week_record_keys:
                diff_records[aid] = this_week_records[aid] - last_week_records[aid]
            else:
                diff_records[aid] = this_week_records[aid]

        active_aids = []
        hot_aids = []
        for aid, view in diff_records.items():
            if view >= 5000:
                hot_aids.append(aid)
            elif view >= 1000:
                active_aids.append(aid)

        session.execute('update tdd_video set activity = 0')
        session.commit()

        for aid in active_aids:
            session.execute('update tdd_video set activity = 1 where aid = %d' % aid)
            session.commit()

        for aid in hot_aids:
            session.execute('update tdd_video set activity = 2 where aid = %d' % aid)
            session.commit()

        logger_11.info('active_aids: %r' % active_aids)
        logger_11.info('hot_aids: %r' % hot_aids)
    except Exception as e:
        logger_11.info(e)
    # tmp update activity field end

    session.close()


def daily_video_update():
    logger_11.info('Now start daily video update...')

    # get videos aids
    session = Session()
    aids_c30 = DBOperation.query_update_c30_aids_all(session)
    logger_11.info('Get %d c30 aids.' % (len(aids_c30)))
    aids_c0 = DBOperation.query_update_c0_aids_all(session)
    logger_11.info('Get %d c0 aids.' % (len(aids_c0)))
    session.close()

    # start a thread to update aids_c30
    threading.Thread(target=update_aids_c30, args=(aids_c30,)).start()

    # start a thread to update aids_c0
    threading.Thread(target=update_aids_c0, args=(aids_c0,)).start()

    logger_11.info('Two thread started!')


def daily_video_update_task():
    threading.Thread(target=daily_video_update).start()


def main():
    logger_11.info('Daily video update registered.')
    # daily_video_update_task()
    schedule.every().day.at("04:00").do(daily_video_update_task)

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
