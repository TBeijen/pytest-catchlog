# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function

import functools
import logging

import pytest
import py

from pytest_catchlog.common import catching_logs, logging_at_level


class LogCaptureFixture(object):
    """Provides access and control of log capturing."""

    def __init__(self, item):
        """Creates a new funcarg."""
        self._item = item
        # set logging levels to facilitate use without needing to import logging
        for level in ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']:
            setattr(self, level, getattr(logging, level))

    @property
    def handler(self):
        return self._item.catch_log_handler

    @property
    def text(self):
        """Returns the log text."""
        return self.handler.stream.getvalue()

    @property
    def records(self):
        """Returns the list of log records."""
        return self.handler.records

    def filter_records(self,  name=None, level=None, message=None):
        """Returns a filtered list of records

        Args:
            name (str, optional): Exact match of the logger name
            level (int, optional): The log level of the record
            message (str|regex, optional): Message part that should be in the record text or
                the regular expression the record text should match
        """
        return self._filter_records(name, level, message)

    @property
    def record_tuples(self):
        """Returns a list of a striped down version of log records intended
        for use in assertion comparison.

        The format of the tuple is:

            (logger_name, log_level, message)
        """
        return self._make_tuples(self.records)

    def filter_record_tuples(self, name=None, level=None, message=None):
        """Returns a filtered list of record tuples for use in asserts

        Args:
            name (str, optional): Exact match of the logger name
            level (int, optional): The log level of the record
            message (str|regex, optional): Message part that should be in the record text or 
                the regular expression the record text should match
        """
        return self._make_tuples(self._filter_records(name, level, message))

    def clear(self):
        """Reset the list of log records."""
        self.handler.records = []

    def set_level(self, level, logger=None):
        """Sets the level for capturing of logs.

        By default, the level is set on the handler used to capture
        logs. Specify a logger name to instead set the level of any
        logger.
        """

        obj = logger and logging.getLogger(logger) or self.handler
        obj.setLevel(level)

    def at_level(self, level, logger=None):
        """Context manager that sets the level for capturing of logs.

        By default, the level is set on the handler used to capture
        logs. Specify a logger name to instead set the level of any
        logger.
        """

        obj = logger and logging.getLogger(logger) or self.handler
        return logging_at_level(level, obj)

    def _filter_records(self, name, level, message):
        """Filter records on given args"""
        def _filter(r):
            if name and not r.name == name:
                return False
            if level and not r.levelno == level:
                return False
            if message:
                try:
                    if not bool(message.search(r.getMessage())):
                        return False
                except AttributeError:
                    if message not in r.getMessage():
                        return False
            return True
        return list(filter(_filter, self.handler.records))

    def _make_tuples(self, records):
        """Convert records to tuples"""
        return [(r.name, r.levelno, r.getMessage()) for r in records]


class CallablePropertyMixin(object):
    """Backward compatibility for functions that became properties."""

    @classmethod
    def compat_property(cls, func):
        if isinstance(func, property):
            make_property = func.getter
            func = func.fget
        else:
            make_property = property

        @functools.wraps(func)
        def getter(self):
            naked_value = func(self)
            ret = cls(naked_value)
            ret._naked_value = naked_value
            ret._warn_compat = self._warn_compat
            ret._prop_name = func.__name__
            return ret

        return make_property(getter)

    def __call__(self):
        new = "'caplog.{0}' property".format(self._prop_name)
        if self._prop_name == 'records':
            new += ' (or caplog.clear())'
        self._warn_compat(old="'caplog.{0}()' syntax".format(self._prop_name),
                          new=new)
        return self._naked_value  # to let legacy clients modify the object


class CallableList(CallablePropertyMixin, list):
    pass


class CallableStr(CallablePropertyMixin, py.builtin.text):
    pass


class CompatLogCaptureFixture(LogCaptureFixture):
    """Backward compatibility with pytest-capturelog."""

    def _warn_compat(self, old, new):
        self._item.warn(code='L1',
                        message=("{0} is deprecated, use {1} instead"
                                 .format(old, new)))

    @CallableStr.compat_property
    def text(self):
        return super(CompatLogCaptureFixture, self).text

    @CallableList.compat_property
    def records(self):
        return super(CompatLogCaptureFixture, self).records

    @CallableList.compat_property
    def record_tuples(self):
        return super(CompatLogCaptureFixture, self).record_tuples

    def setLevel(self, level, logger=None):
        self._warn_compat(old="'caplog.setLevel()'",
                          new="'caplog.set_level()'")
        return self.set_level(level, logger)

    def atLevel(self, level, logger=None):
        self._warn_compat(old="'caplog.atLevel()'",
                          new="'caplog.at_level()'")
        return self.at_level(level, logger)


@pytest.fixture
def caplog(request):
    """Access and control log capturing.

    Captured logs are available through the following methods::

    * caplog.text()          -> string containing formatted log output
    * caplog.records()       -> list of logging.LogRecord instances
    * caplog.record_tuples() -> list of (logger_name, level, message) tuples
    """
    return CompatLogCaptureFixture(request.node)

capturelog = caplog
