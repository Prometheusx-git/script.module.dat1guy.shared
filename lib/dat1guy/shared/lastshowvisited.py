# -*- coding: utf-8 -*-
'''
    dat1guy's Shared Methods - a plugin for Kodi
    Copyright (C) 2016 dat1guy

    This file is part of dat1guy's Shared Methods.

    dat1guy's Shared Methods is free software: you can redistribute it and/or
    modify it under the terms of the GNU General Public License as published
    by the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    dat1guy's Shared Methods is distributed in the hope that it will be 
    useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with dat1guy's Shared Methods.  If not, see 
    <http://www.gnu.org/licenses/>.
'''


from dat1guy.shared.shared_helper import shared_helper as helper


class LastShowVisited(object):
    def __init__(self, profile_path):
        import os
        from sqlite3 import dbapi2 as database
        db_path = os.path.join(profile_path, 'appdata.db')
        self.dbcon = database.connect(db_path)
        self.dbcon.row_factory = database.Row
        self.dbcur = self.dbcon.cursor()
        self._create_table()

    ''' PUBLIC FUNCTIONS '''
    def get_last_show_visited(self):
        return self.__get_row('lastshowvisited')

    def update_last_show_visited(self, args):
        self.__update_row('lastshowvisited', args)

    ''' PROTECTED FUNCTIONS '''
    def _create_table(self):
        sql_create = 'CREATE TABLE IF NOT EXISTS last_visited ('\
            'id TEXT, '\
            'action TEXT, '\
            'value TEXT, '\
            'icon TEXT, '\
            'fanart TEXT, '\
            'full_title TEXT, '\
            'base_title TEXT, '\
            'imdb_id TEXT, '\
            'tvdb_id TEXT, '\
            'tmdb_id TEXT, '\
            'media_type TEXT, '\
            'UNIQUE(id))'
        self.dbcur.execute(sql_create)            

    ''' PRIVATE FUNCTIONS '''
    def __get_row(self, id):
        sql_select = 'SELECT * FROM last_visited WHERE id=?'
        helper.log_debug('SQL SELECT: %s with params: %s' % (sql_select, id))
        self.dbcur.execute(sql_select, (id, ))
        matchedrow = self.dbcur.fetchone()
        return dict(matchedrow) if matchedrow else None

    def __update_row(self, id, args):
        sql_update = 'INSERT OR REPLACE INTO last_visited '\
            '(id, action, value, icon, fanart, full_title, base_title, '\
            'imdb_id, tvdb_id, tmdb_id, media_type) '\
            'VALUES (%s)' % (', '.join('?' * 11))
        # Be sure to decode the names which may contain funky characters!
        full_title = args['full_title'].decode('utf8') if args['full_title'] else ''
        base_title = args['base_title'].decode('utf8') if args['base_title'] else ''
        data = (id, args['action'], args['value'], args['icon'], args['fanart'],
                full_title, base_title, args['imdb_id'], args['tvdb_id'], args['tmdb_id'], 
                args['media_type'])
        helper.log_debug('SQL INSERT OR REPLACE: %s with params %s' % (sql_update, str(data)))
        self.dbcur.execute(sql_update, data)
        self.dbcon.commit()