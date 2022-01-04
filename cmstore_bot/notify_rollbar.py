import functools
import rollbar

from contextlib import contextmanager, asynccontextmanager
from environs import Env

env = Env()
env.read_env()


def notify_rollbar():

    def decorator(func):

        @functools.wraps(func)
        def func_wrapped(*args, **kwargs):
            init_rollbar()

            try:
                return func(*args, **kwargs)
            except: # noqa
                rollbar.report_exc_info()
                raise
            finally:
                rollbar.wait()

        return func_wrapped

    return decorator


def anotify_rollbar():

    def decorator(func):

        @functools.wraps(func)
        async def func_wrapped(*args, **kwargs):
            init_rollbar()

            try:
                return await func(*args, **kwargs)
            except: # noqa
                print("send to rollbar")
                rollbar.report_exc_info()
                raise
            finally:
                rollbar.wait()

        return func_wrapped

    return decorator


@contextmanager
def notify_rollbar_from_context(level='error', extra_data=None):
    # initialization should be done before yield to avoid exception during report_message call
    # initialization should be even if rollbar token was now specified
    init_rollbar()

    try:
        yield
    except: # noqa
        rollbar.report_exc_info(level=level, extra_data=extra_data)
        raise
    finally:
        # FIXME should replace with async version
        # Avoid messages losing. Details are here https://docs.rollbar.com/docs/python#aws-lambda
        rollbar.wait()


@asynccontextmanager
async def anotify_rollbar_from_context(level='error', extra_data=None):
    # initialization should be done before yield to avoid exception during report_message call
    # initialization should be even if rollbar token was now specified
    init_rollbar()

    try:
        yield
    except: # noqa
        rollbar.report_exc_info(level=level, extra_data=extra_data)
        raise
    finally:
        # FIXME should replace with async version
        # Avoid messages losing. Details are here https://docs.rollbar.com/docs/python#aws-lambda
        rollbar.wait()


def init_rollbar():
    if not rollbar._initialized:
        rollbar.init(
            env.str('ROLLBAR_TOKEN'),
            'production',
            allow_logging_basic_config=False,
        )
