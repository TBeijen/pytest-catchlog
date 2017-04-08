# -*- coding: utf-8 -*-
import re
import sys
import logging

import pytest

logger = logging.getLogger(__name__)
sublogger = logging.getLogger(__name__+'.baz')

u = (lambda x: x.decode('utf-8')) if sys.version_info < (3,) else (lambda x: x)

filter_params = [
    (__name__, logging.INFO, None, ['foo', 'bar']),
    (__name__, logging.INFO, 'foo', ['foo']),
    (__name__, logging.INFO, 'o ar', ['foo']),
    ('other', logging.INFO, 'foo', []),
    (__name__, logging.WARNING, 'foo', []),
    (__name__, 45, 'foo arg', ['foo']),
    (__name__, logging.INFO, re.compile('o\s'), ['foo']),
    (__name__, logging.INFO, re.compile('foo$'), []),
]


def do_test_filter_record_logging():
    """do logging for tests parametrized by filter_params"""
    logger.info('foo %s', 'arg')
    logger.info('bar %s', 'arg')
    logger.log(45, 'foo %s', 'arg')


def test_fixture_help(testdir):
    result = testdir.runpytest('--fixtures')
    result.stdout.fnmatch_lines(['*caplog*'])


def test_change_level(caplog):
    caplog.set_level(logging.INFO)
    logger.debug('handler DEBUG level')
    logger.info('handler INFO level')

    caplog.set_level(logging.CRITICAL, logger=sublogger.name)
    sublogger.warning('logger WARNING level')
    sublogger.critical('logger CRITICAL level')

    assert 'DEBUG' not in caplog.text
    assert 'INFO' in caplog.text
    assert 'WARNING' not in caplog.text
    assert 'CRITICAL' in caplog.text


def test_with_statement(caplog):
    with caplog.at_level(logging.INFO):
        logger.debug('handler DEBUG level')
        logger.info('handler INFO level')

        with caplog.at_level(logging.CRITICAL, logger=sublogger.name):
            sublogger.warning('logger WARNING level')
            sublogger.critical('logger CRITICAL level')

    assert 'DEBUG' not in caplog.text
    assert 'INFO' in caplog.text
    assert 'WARNING' not in caplog.text
    assert 'CRITICAL' in caplog.text


def test_log_access(caplog):
    logger.info('boo %s', 'arg')
    assert caplog.records[0].levelname == 'INFO'
    assert caplog.records[0].msg == 'boo %s'
    assert 'boo arg' in caplog.text


def test_record_tuples(caplog):
    logger.info('boo %s', 'arg')

    assert caplog.record_tuples == [
        (__name__, logging.INFO, 'boo arg'),
    ]


@pytest.mark.parametrize('name, level, message, expected', filter_params)
def test_filter_records(caplog, name, level, message, expected):
    do_test_filter_record_logging()

    filtered = caplog.filter_records(name, level, message)
    filtered_named_args = caplog.filter_records(name=name, level=level, message=message)

    assert filtered == filtered_named_args
    assert [f.getMessage().split(' ')[0] for f in filtered] == expected


@pytest.mark.parametrize('name, level, message, expected', filter_params)
def test_filter_record_tuples(caplog, name, level, message, expected):
    do_test_filter_record_logging()

    filtered = caplog.filter_record_tuples(name, level, message)
    filtered_named_args = caplog.filter_record_tuples(name=name, level=level, message=message)

    assert filtered == filtered_named_args
    assert [f[2].split(' ')[0] for f in filtered] == expected


@pytest.mark.parametrize('level', [
    'CRITICAL',
    'ERROR',
    'WARNING',
    'INFO',
    'DEBUG',
    'NOTSET',
])
def test_levels(caplog, level):
    assert getattr(caplog, level) == getattr(logging, level)


@pytest.mark.parametrize('level', [
    'UNKNOWNLEVEL',  # Matches log level pattern, looked up from logging module.
    'something_else'  # Not looked up from logging. Not an attribute of LogCaptureFixture.
])
def test_levels_error(caplog, level):
    with pytest.raises(AttributeError):
        getattr(caplog, level)


def test_unicode(caplog):
    logger.info(u('bū'))
    assert caplog.records[0].levelname == 'INFO'
    assert caplog.records[0].msg == u('bū')
    assert u('bū') in caplog.text


def test_clear(caplog):
    logger.info(u('bū'))
    assert len(caplog.records)
    caplog.clear()
    assert not len(caplog.records)


def test_special_warning_with_del_records_warning(testdir):
    p1 = testdir.makepyfile("""
        def test_del_records_inline(caplog):
            del caplog.records()[:]
    """)
    result = testdir.runpytest_subprocess(p1)
    result.stdout.fnmatch_lines([
        "WL1 test_*.py:1 'caplog.records()' syntax is deprecated,"
        " use 'caplog.records' property (or caplog.clear()) instead",
        "*1 pytest-warnings*",
    ])


def test_warning_with_setLevel(testdir):
    p1 = testdir.makepyfile("""
        def test_inline(caplog):
            caplog.setLevel(0)
    """)
    result = testdir.runpytest_subprocess(p1)
    result.stdout.fnmatch_lines([
        "WL1 test_*.py:1 'caplog.setLevel()' is deprecated,"
        " use 'caplog.set_level()' instead",
        "*1 pytest-warnings*",
    ])
