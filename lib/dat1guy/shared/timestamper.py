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


import time
from dat1guy.shared.shared_helper import shared_helper as helper


timestamps_on = False


class TimeStamper(object):
    def __init__(self, title, t0=None, t1_msg=''):
        self.title = title
        self.timelist = []
        self.timestamps_on = timestamps_on
        if self.timestamps_on:
            if t0 != None:
                self.timelist.append((t0, ''))
                self.stamp(t1_msg)
            else:
                self.stamp()

    ''' PUBLIC FUNCTIONS '''
    def stamp(self, msg=''):
        if self.timestamps_on:
            self.timelist.append((time.time(), msg))
        return self

    def stamp_and_dump(self, msg=''):
        if self.timestamps_on:
            self.stamp(msg)
            self._dump()

    ''' PROTECTED FUNCTIONS '''
    def _dump(self):
        if not self.timestamps_on:
            return

        (t_start, start_msg) = self.timelist[0]
        (t_end, last_msg) = self.timelist[-1]
        helper.log_notice('TIME DUMP for %s' % self.title)
        if len(self.timelist) > 2:
            for idx, (cur_time, msg) in enumerate(self.timelist[1:]):
                prev_time, prev_msg = self.timelist[idx]
                if msg != '':
                    helper.log_notice('****%s: %f' % (msg, (cur_time - prev_time)))
        helper.log_notice('****TOTAL: %f' % (t_end - t_start))