﻿# -*- coding: utf-8 -*-
from __future__ import print_function, division

import sys
import logging
log = logging.getLogger(__name__)

__all__ = ['Timer', 'T', 'SimpleTimer',]

if __name__ == '__main__':
    log = logging.getLogger()
    log.level = logging.DEBUG
    log.addHandler(logging.StreamHandler(sys.stderr))


import os
import time
from datetime import datetime
from functools import wraps
from collections import Callable
from copy import copy


DEFAULT_TIME_FMT = '.3f'


class SimpleTimer(object):
    def __init__(self, name=None, owner=None, time_fmt=DEFAULT_TIME_FMT, template=None, extra=None):
        self.name = self.__class__.__name__ if name is None else name
        self.timestamp_start = None
        self.timestamp_stop = None
        self.owner = owner
        self.time_fmt = time_fmt
        self.extra = extra or {}
        if template is not None:
            self.template = template

    @property
    def time_start(self):
        return None if self.timestamp_start is None else datetime.fromtimestamp(self.timestamp_start)

    @property
    def time_stop(self):
        return None if self.timestamp_stop is None else datetime.fromtimestamp(self.timestamp_stop)

    def start(self, t=None, extra=None):
        if self.timestamp_start is not None:
            log.error("Simple timer can not to be started twice")
            return self

        if t is None:
            t = time.time()
        if extra:
            self.extra.update(extra)
        self.timestamp_start = t
        return self

    def stop(self, t=None, owner_stop=True, extra=None):
        if self.timestamp_start is None or self.timestamp_stop is not None:
            log.error("SimpleTimer can not to be stopped twice or if it is not started")
            return self

        owner = self.owner
        if owner_stop and owner is not None:
            owner.stop(t, extra=extra)
        else:
            if t is None:
                t = time.time()
            self.timestamp_stop = t
            if extra:
                self.extra.update(extra)
        return self

    @property
    def is_started(self):
        return self.timestamp_start is not None

    @property
    def is_stopped(self):
        return self.timestamp_stop is not None

    @property
    def is_active(self):
        return self.is_started and not self.is_stopped

    @property
    def duration(self):
        if not self.is_started:
            return 0

        at_time = self.timestamp_stop or time.time()
        return at_time - self.timestamp_start

    @property
    def running_sign(self):
        return '' if self.is_active else '.'

    template = u"<{timer.name}:{timer.duration:{timer.time_fmt}}{timer.running_sign}>"

    def to_string(self, template=None, encoding=None):
        if template is None:
            template = self.template
        s = template.format(timer=self)
        if encoding:
            return s.encode(encoding)

        return s

    def __unicode__(self):
        return self.to_string()

    def __str__(self):
        return self.to_string(encoding=sys.stdout.encoding or 'utf-8')

    def __repr__(self):
        return str(self)


# todo: Progress tracking feature (estimate, stage, progress bar, stage comment)
class Timer(SimpleTimer):
    def __init__(
        self,
        name=None,
        logger=None,
        log_start='Timer {timer.name!r} started at {timer.time_start}',
        log_stop='Timer {timer.name!r} stopped at {timer.time_stop}. Duration is {timer.duration}s',
        log_level=logging.DEBUG,
        log_name=None,
        laps_store=0,
        stat_template=None,
        **kw
    ):
        super(Timer, self).__init__(name=name, **kw)
        if stat_template is not None:
            self.stat_template = stat_template

        self.laps_store = laps_store
        self.log_level = log_level and logging._checkLevel(log_level) or logging.NOTSET
        _stream = None
        if logger is None or isinstance(logger, logging.Logger):
            self.logger = logger
        elif isinstance(logger, basestring) and logger in {'stderr', 'stdout'}:
            _stream = getattr(sys, logger)
        elif isinstance(getattr(logger, 'write', None), Callable):
            _stream = logger
        else:
            raise ValueError(
                "Logger specification is wrong. {!r} given, but 'stderr', 'stdout' or Logger instance required."
                .format(logger)
            )
        if _stream:
            _handler = logging.StreamHandler(_stream)
            self.logger = logging.Logger(name=log_name, level=self.log_level)
            self.logger.addHandler(_handler)

        self.log_start = log_start
        self.log_stop = log_stop
        self.duration_sum_last = 0
        self.duration_sum = 0
        self.duration_min = None
        self.duration_max = None
        self.lap_count = 0
        self.lap_timer = None
        self.laps = []
        self.__dict__.update(kw)

    def _log(self, message, *av, **kw):
        logger = self.logger
        if logger:
            logger.log(self.log_level, message, *av, **kw)

    def start(self, t=None, lap_name=None, extra=None):
        # todo: lock to thread save support
        lap_timer = self.lap_timer = SimpleTimer(
            name=lap_name or '{timer.name}:lap#{timer.lap_count}'.format(timer=self),
            owner=self,
        )
        lap_timer.start(t=t, extra=extra)
        if self.timestamp_start is None:
            super(Timer, self).start(lap_timer.timestamp_start, extra=extra)

        if self.log_start:
            self._log(self.log_start.format(timer=self))
        return lap_timer

    def stop(self, t=None, owner_stop=True, extra=None):
        owner = self.owner
        if owner_stop and owner is not None:
            return owner.stop(t, extra=extra)
        else:
            # todo: lock to thread save support
            lap_timer = self.lap_timer
            assert lap_timer is not None, "Timer is not running, you can't stop them"
            #t = super(Timer, self).stop(t)  # info: Будучи запущеным такой таймер уже не останавливается сам, только круги
            lap_timer.stop(t, owner_stop=False, extra=extra)
            self.lap_timer = None
            self.lap_count += 1
            self.last_lap = lap_timer
            last_lap_duration = lap_timer.duration
            self.duration_sum += last_lap_duration
            self.duration_sum_last += last_lap_duration
            duration_min = self.duration_min
            duration_max = self.duration_max

            if duration_min is None or last_lap_duration < duration_min:
                self.duration_min = duration_min = last_lap_duration

            if duration_max is None or last_lap_duration > duration_max:
                self.duration_max = duration_max = last_lap_duration

            laps_store = self.laps_store
            if laps_store:
                laps = self.laps
                laps.append(lap_timer)
                while len(laps) > laps_store > 0:
                    poped = laps.pop(0)
                    self.duration_sum_last -= poped.duration

            if self.log_stop:
                self._log(self.log_stop.format(timer=self))
            return lap_timer

    @property
    def duration_avg(self):
        n = self.lap_count
        return self.duration_sum / n if n > 0 else 0

    @property
    def duration_avg_last(self):
        n = len(self.laps)
        return self.duration_sum_last / n if n > 0 else 0

    @property
    def is_started(self):
        return self.lap_timer is not None

    @property
    def is_stopped(self):
        return self.lap_timer is None

    is_active = is_started

    @property
    def duration(self):
        lap_timer = self.lap_timer
        return self.duration_sum + (lap_timer.duration if lap_timer else 0)

    @property
    def decorated_point(self):
        # {'line': 209, 'func': < function
        # test_perf
        # at
        # 0x0319A330 >, 'fn': 'tree_test.py'}
        if 'func' in self.extra:
            return '[{timer.extra[fn]}:{timer.extra[line]} {timer.extra[func].func_name}]'.format(timer=self)
        return ''

    # todo: cumulative_duration of multiple start/stop laps

    def __enter__(self):
        self.start()
        return self.lap_timer

    def __exit__(self, ex_type, ex_value, traceback):
        self.stop()

    def __call__(self, func):
        assert isinstance(func, Callable), "{} is not Callable, can't wrap".format(func)
        timers = getattr(func, 'timers', None)
        if timers is None:
            @wraps(func)
            def closure(*av, **kw):
                lap_extra = dict(
                    func=func,
                    fn=os.path.basename(func.func_code.co_filename),
                    line=func.func_code.co_firstlineno,
                    # todo: ADD traceback of call point (optionally)
                )
                laps = [timer.start(extra=lap_extra) for timer in closure.timers]
                try:
                    return func(*av, **kw)
                finally:
                    for lap in reversed(laps):
                        lap.stop()

            closure.orig = func
            timers = closure.timers = []
        else:
            closure = func

        timers.append(self)
        return closure

    stat_template = (
        u' - {timer.lap_count:4} '
        u'[{timer.duration_min:{timer.time_fmt}}'
        u'/{timer.duration_avg:{timer.time_fmt}}'
        u'/{timer.duration_max:{timer.time_fmt}}]'
    )
    @property
    def stat_string(self):
        return self.stat_template.format(timer=self) if self.lap_count else ''

    template = u"{timer.name}{timer.decorated_point}: {timer.duration:{timer.time_fmt}}{timer.stat_string}{timer.running_sign}"
    template_repr = "<{timer.name}{timer.decorated_point}: {timer.duration:{timer.time_fmt}}{timer.stat_string}{timer.running_sign}>"

    def __repr__(self):
        return self.to_string(encoding=sys.stdout.encoding or 'utf-8', template=self.template_repr)


class T(Timer):
    def __init__(
            self,
            name=None,
            logger=sys.stdout,
            log_start=None,
            log_stop=Timer.template + ' ==> {timer.last_lap.duration:{timer.time_fmt}}',
            log_level=logging.DEBUG,
            log_name=None,
            **kw
        ):
        super(T, self).__init__(
            name=name, logger=logger, log_start=log_start, log_stop=log_stop, log_level=log_level, log_name=log_name, **kw
        )


if __name__ == '__main__':
    import sys
    from time import sleep
    from pprint import pprint as pp
    import random

    # tm = Timer()
    # for i in xrange(3):
    #     with tm as t:
    #         sleep(random.randint(1, 3)/10)
    #
    #     with random.choice([tm, Timer()]):
    #         print(u'lap {tm.lap_count:03d}::      {tm} '.format(tm=tm, t=t))
    #     sleep(0.2)
    #
    # print(tm)

    # @tm
    @T(name='t1')
    # @T(name='t2')
    def f(x):
        sleep(0.5)
        print('f(', x)

    for i in xrange(10):
        f(i)

    print('=== STAT ===')
    for t in f.timers:
        print(t)
    # # simple usage:
    # with Timer('simple', logger='stderr'):
    #     pass
    #
    # # normal usage:
    # tm = Timer(name='test', logger=log)
    # with tm as timer:
    #     task_size = 100000000 / 16
    #     for i in xrange(task_size):
    #         if i % (task_size / 10) == 0:
    #             print('{:.4f}'.format(timer.duration))

    # functions decoration usage:
    # @Timer(name='test2', logger=sys.stdout)
    # def test_routine2():
    #     print('test_routine2')

    # test_routine2()
    # test_routine2()