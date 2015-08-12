import os, logging

_logger = logging.getLogger(__name__)

def shell(cmd, exit_status = 0):
    """
    Dummy wrapper for running shell commands, checking the return value and logging
    """

    sts = os.system(cmd)

    if sts == exit_status:
        _logger.debug(cmd)
    else:
        if sts == 512:
            _logger.debug("'%s' returned %d (expected %d)", cmd, sts, exit_status)
        else:
            _logger.warning("'%s' returned %d (expected %d)", cmd, sts, exit_status)
    return sts

def touch(arg):
    open(str(arg), 'a').close()

