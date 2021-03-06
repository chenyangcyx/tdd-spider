from logger import logger_51
from util import ts_s_to_str, get_ts_s, get_week_day, str_to_ts_s, zk_calc, a2b
from db import Session, DBOperation


def main():
    logger_51.info('51-13: video record rank weekly')

    hour_label = ts_s_to_str(get_ts_s())[:13] + ':00'
    time_label = hour_label[11:]
    logger_51.info('hour_label: ' + hour_label)

    session = Session()

    logger_51.info('13-1: update tdd_video_record_rank_weekly_current')

    # get record base dict
    video_record_base_dict = DBOperation.query_video_record_rank_weekly_base_dict(session)
    logger_51.info('video_record_base_dict got from db')

    # load video_record_now_list from file
    data_folder = 'data/'
    file_name = hour_label + '.csv'
    video_record_now_list = []
    with open(data_folder + file_name, 'r') as f:
        f.readline()  # ignore first line
        while True:
            line = f.readline()
            if not line:
                break
            line = line.rstrip('\n')
            line_arr = line.split(',')
            if len(line_arr) == 9:
                video_record_now_list.append((
                    a2b(int(line_arr[0])),  # bvid
                    int(line_arr[1]),  # added
                    int(line_arr[2]),  # view
                    int(line_arr[3]),  # danmaku
                    int(line_arr[4]),  # reply
                    int(line_arr[5]),  # favorite
                    int(line_arr[6]),  # coin
                    int(line_arr[7]),  # share
                    int(line_arr[8])  # like
                ))
            else:
                logger_51.warning('incorrect line format, line: ' + line)

    # get video videos(page), pubdate dict from db
    video_videos_pubdate_dict = DBOperation.query_video_videos_pubdate_dict(session)
    logger_51.info('video_videos_pubdate_dict got from db')
    try:
        drop_tmp_table_sql = 'drop table if exists tdd_video_record_rank_weekly_current_tmp'
        session.execute(drop_tmp_table_sql)
        logger_51.info(drop_tmp_table_sql)

        create_tmp_table_sql = 'create table tdd_video_record_rank_weekly_current_tmp ' + \
                               'like tdd_video_record_rank_weekly_current'
        session.execute(create_tmp_table_sql)
        logger_51.info(create_tmp_table_sql)
    except Exception as e:
        session.rollback()
        logger_51.warning('Error occur when executing update tdd_video_record_rank_weekly_base. Detail: %s' % e)

    logger_51.info('now making video_record_weekly_curr_list...')
    video_record_weekly_curr_list = []
    video_record_weekly_curr_made_count = 0
    this_weekly_rank_begin_ts = sorted(map(lambda x: x[0], video_record_base_dict.values()))[0]
    for rn in video_record_now_list:
        try:
            # check bvid exists in base or not
            bvid = rn[0]
            if bvid in video_record_base_dict.keys():
                rb = video_record_base_dict[bvid]
                start_added = rb[0]
            else:
                rb = (0, 0, 0, 0, 0, 0, 0, 0)
                start_added = 0
            d_view = rn[2] - rb[1]  # maybe occur -1?
            d_danmaku = rn[3] - rb[2]
            d_reply = rn[4] - rb[3]
            d_favorite = rn[5] - rb[4]
            d_coin = rn[6] - rb[5]
            d_share = rn[7] - rb[6]
            d_like = rn[8] - rb[7]
            page = 1
            if bvid in video_videos_pubdate_dict.keys():
                # video added before
                page = video_videos_pubdate_dict[bvid][0]
                if start_added == 0:
                    # bvid not appear in base
                    if video_videos_pubdate_dict[bvid][1] >= this_weekly_rank_begin_ts:
                        # this week new video
                        start_added = video_videos_pubdate_dict[bvid][1]  # set pubdate
                    else:
                        # old video, but not appear in base, do not add in rank
                        logger_51.warning('old video %s found, do not add in rank' % bvid)
                        continue
            else:
                # video not added, just skip
                logger_51.warning('not added video %s found, just skip' % bvid)
                continue
            if not page or page == 0:  # page maybe zero or None, set to default 1
                page = 1
            point, xiua, xiub = zk_calc(d_view, d_danmaku, d_reply, d_favorite, page=page)
            # append to list
            video_record_weekly_curr_list.append((bvid, start_added, rn[1],  # bvid, start_added, now_added
                                                  rn[2], rn[3], rn[4], rn[5], rn[6], rn[7], rn[8],
                                                  d_view, d_danmaku, d_reply, d_favorite, d_coin, d_share, d_like,
                                                  point, xiua, xiub))
            video_record_weekly_curr_made_count += 1
            if video_record_weekly_curr_made_count % 10000 == 0:
                logger_51.info('make %d / %d done' % (video_record_weekly_curr_made_count, len(video_record_now_list)))
        except Exception as e:
            logger_51.warning('Error occur when making video_record_weekly_curr. Detail: %s' % e)
    logger_51.info('make %d / %d done' % (video_record_weekly_curr_made_count, len(video_record_now_list)))
    logger_51.info('finish make video_record_weekly_curr_list')

    # sort via point
    video_record_weekly_curr_list.sort(key=lambda x: (x[17], x[10]))  # TODO if point equals?
    video_record_weekly_curr_list.reverse()
    logger_51.info('finish sort video_record_weekly_curr_list')

    # select top 10000 video
    video_record_weekly_curr_list = video_record_weekly_curr_list[:10000]
    logger_51.info('select top 10000 video')

    logger_51.info('now inserting video_record_weekly_curr_list...')
    video_record_weekly_curr_added_count = 0
    rank = 1
    for c in video_record_weekly_curr_list:
        # dont use sql alchemy in order to save memory
        sql = 'insert into tdd_video_record_rank_weekly_current_tmp ' \
              'values("%s", %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %f, %f, %f, %d)' % \
              (c[0], c[1], c[2],
               c[3], c[4], c[5], c[6], c[7], c[8], c[9],
               c[10], c[11], c[12], c[13], c[14], c[15], c[16],
               c[17], c[18], c[19],
               rank)
        rank += 1
        session.execute(sql)
        video_record_weekly_curr_added_count += 1
        # if video_record_weekly_curr_added_count % 10000 == 0:
        #     session.commit()
        #     logger_51.info('insert %d / %d done' % (video_record_weekly_curr_added_count,
        #                                             len(video_record_weekly_curr_list)))
    session.commit()
    logger_51.info('insert %d / %d done' % (video_record_weekly_curr_added_count, len(video_record_weekly_curr_list)))

    try:
        drop_old_table_sql = 'drop table if exists tdd_video_record_rank_weekly_current'
        session.execute(drop_old_table_sql)
        logger_51.info(drop_old_table_sql)

        rename_tmp_table_sql = 'rename table tdd_video_record_rank_weekly_current_tmp to ' + \
                               'tdd_video_record_rank_weekly_current'
        session.execute(rename_tmp_table_sql)
        logger_51.info(rename_tmp_table_sql)
    except Exception as e:
        session.rollback()
        logger_51.warning('Error occur when executing update tdd_video_record_rank_weekly_base. Detail: %s' % e)

    logger_51.info('13-1: done! Finish updating tdd_video_record_rank_weekly_current')

    logger_51.info('13-2: update tdd_video_record_rank_weekly_current_color')

    color_dict = {
        10: 'incr_view',
        11: 'incr_danmaku',
        12: 'incr_reply',
        13: 'incr_favorite',
        14: 'incr_coin',
        15: 'incr_share',
        16: 'incr_like',
        17: 'point',
    }

    for prop_idx, prop in color_dict.items():
        prop_list = sorted(list(map(lambda x: x[prop_idx], video_record_weekly_curr_list)))
        # a
        value = float(prop_list[5000])
        logger_51.info('{0} 50% {1}'.format(prop, value))
        session.execute('update tdd_video_record_rank_weekly_current_color set a = %f ' % value +
                        'where property = "%s"' % prop)
        # b
        value = float(prop_list[9000])
        logger_51.info('{0} 90% {1}'.format(prop, value))
        session.execute('update tdd_video_record_rank_weekly_current_color set b = %f ' % value +
                        'where property = "%s"' % prop)
        # c
        value = float(prop_list[9900])
        logger_51.info('{0} 99% {1}'.format(prop, value))
        session.execute('update tdd_video_record_rank_weekly_current_color set c = %f ' % value +
                        'where property = "%s"' % prop)
        session.commit()
        # d
        value = float(prop_list[9990])
        logger_51.info('{0} 99.9% {1}'.format(prop, value))
        session.execute('update tdd_video_record_rank_weekly_current_color set d = %f ' % value +
                        'where property = "%s"' % prop)
        session.commit()

    logger_51.info('13-2: done! Finish updating tdd_video_record_rank_weekly_current_color')

    logger_51.info('13-3: archive and update tdd_video_record_rank_weekly_base')

    # Saturday 03:00, new week start, archive last week score and start new week
    if time_label == '03:00' and get_week_day() == 5:
        # TODO test validity
        # create table from tdd_video_record_hourly

        try:
            # calc archive overview
            ts_str = ts_s_to_str(get_ts_s())
            end_ts = str_to_ts_s(ts_str[:11] + '03:00:00')
            start_ts = end_ts - 7 * 24 * 60 * 60
            issue_num = (start_ts - 1599850800) // (7 * 24 * 60 * 60) + 424
            arch_name = 'W' + ts_str[:4] + ts_str[5:7] + ts_str[8:10] + ' - #' + str(issue_num)
            session.execute('insert into tdd_video_record_rank_weekly_archive_overview (`name`, start_ts, end_ts) ' +
                            'values ("%s", %d, %d)' % (arch_name, start_ts, end_ts))
            session.commit()

            # get arch id
            result = session.execute('select `id` from tdd_video_record_rank_weekly_archive_overview ' +
                                     'where `name` = "%s"' % arch_name)
            arch_id = 0
            for r in result:
                arch_id = int(r[0])

            # archive record, just like add current, just add 1 more column called arch_id
            logger_51.info('now archiving record...')
            video_record_weekly_archive_added_count = 0
            rank = 1
            for c in video_record_weekly_curr_list:
                # dont use sql alchemy in order to save memory
                sql = 'insert into tdd_video_record_rank_weekly_archive values(' \
                      '%d, "%s", %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %d, %f, %f, %f, %d)' % \
                      (arch_id, c[0], c[1], c[2],
                       c[3], c[4], c[5], c[6], c[7], c[8], c[9],
                       c[10], c[11], c[12], c[13], c[14], c[15], c[16],
                       c[17], c[18], c[19],
                       rank)
                rank += 1
                session.execute(sql)
                video_record_weekly_archive_added_count += 1
            session.commit()
            logger_51.info(
                'insert %d / %d done' % (video_record_weekly_archive_added_count, len(video_record_weekly_curr_list)))
            logger_51.info('finish archive record!')

            # archive color
            logger_51.info('now archiving color...')
            result = session.execute('select * from tdd_video_record_rank_weekly_current_color')
            for r in result:
                prop = str(r[0])
                a = float(r[1])
                b = float(r[2])
                c = float(r[3])
                d = float(r[4])
                session.execute('insert into tdd_video_record_rank_weekly_archive_color values(' +
                                '%d, "%s", %f, %f, %f, %f)' % (arch_id, prop, a, b, c, d))
            session.commit()
            logger_51.info('finish archive color!')

            # update base

            drop_tmp_table_sql = 'drop table if exists tdd_video_record_rank_weekly_base_tmp'
            session.execute(drop_tmp_table_sql)
            logger_51.info(drop_tmp_table_sql)

            hour_start_ts = str_to_ts_s(ts_s_to_str(get_ts_s())[:11] + '03:00:00')
            create_tmp_table_sql = 'create table tdd_video_record_rank_weekly_base_tmp ' + \
                                   'select * from tdd_video_record_hourly where added >= %d' % hour_start_ts
            session.execute(create_tmp_table_sql)
            logger_51.info(create_tmp_table_sql)

            drop_old_table_sql = 'drop table if exists tdd_video_record_rank_weekly_base'
            session.execute(drop_old_table_sql)
            logger_51.info(drop_old_table_sql)

            rename_tmp_table_sql = 'rename table tdd_video_record_rank_weekly_base_tmp to ' + \
                                   'tdd_video_record_rank_weekly_base'
            session.execute(rename_tmp_table_sql)
            logger_51.info(rename_tmp_table_sql)
        except Exception as e:
            session.rollback()
            logger_51.warning('Error occur when executing update tdd_video_record_rank_weekly_base. Detail: %s' % e)
    else:
        logger_51.info('13-3 done! not Sat 03:00 pass, no need to archive and update tdd_video_record_rank_weekly_base')

    session.close()


if __name__ == '__main__':
    main()
