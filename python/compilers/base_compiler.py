
import logging, os, re

_logger = logging.getLogger(__name__)

def _is_vhd(p):
    return os.path.basename(p).lower().endswith('vhd')

def _is_makefile(f):
    return os.path.basename(f) == 'Makefile'

def shell(cmd, exit_status = 0):
    """
    Dummy wrapper for running shell commands, checking the return value and logging
    """

    _logger.debug(cmd)
    for l in os.popen(cmd).read().split("\n"):
        if re.match(r"^\s*$", l):
            continue
        _logger.debug(l)


class BaseCompiler(object):
    def __init__(self, target_folder):
        self._TARGET_FOLDER = os.path.expanduser(target_folder)

        self._MODELSIM_INI = os.path.join(self._TARGET_FOLDER, 'modelsim.ini')

        if not os.path.exists(self._TARGET_FOLDER):
            os.mkdir(self._TARGET_FOLDER)

        os.chdir(self._TARGET_FOLDER)
        self._logger = logging.getLogger(__name__)

    def createLibrary(self, library):
        self._logger.info("Library %s not found, creating", library)
        shell('vlib {library}'.format(library=os.path.join(self._TARGET_FOLDER, library)))
        shell('vmap {library} {library_path}'.format(
            library=library, library_path=os.path.join(self._TARGET_FOLDER, library)))

    def mapLibrary(self, library):
        self._logger.info("Library %s found, mapping", library)

        shell('vlib {library}'.format(library=os.path.join(self._TARGET_FOLDER, library)))
        shell('vmap -modelsimini {modelsimini} {library} {library_path}'.format(
            modelsimini=self._MODELSIM_INI, library=library, library_path=os.path.join(self._TARGET_FOLDER, library)))

    def preBuild(self, library, source):
        if os.path.exists(self._MODELSIM_INI):
            self.mapLibrary(library)
        else:
            self.createLibrary(library)
    def postBuild(self, library, source):
        pass
    def _doBuild(self, library, source):
        pass
    def build(self, library, source):
        self.preBuild(library, source)
        self._doBuild(library, source)
        self.postBuild(library, source)




    #              sts = 1

    #  #  if sts == exit_status:
    #  #      _logger.debug(cmd)
    #  #  else:
    #  #      if sts == 512:
    #  #          _logger.debug("'%s' returned %d (expected %d)", cmd, sts, exit_status)
    #  #      else:
    #  #          _logger.warning("'%s' returned %d (expected %d)", cmd, sts, exit_status)
    #  #  return errors = []
    #      warnings = []
    #      log_line = []
    #      for l in ret:
    #          if RE_VCOM_COMPILER_EXITING.match(l):
    #              continue
    #          for re_obj, re_text in _VCOM_SUBS:
    #              l = re_obj.sub(re_text, l)
    #          log_line += [l]
    #          if RE_VCOM_ERROR.match(l):
    #              errors.append("\n".join(log_line))
    #              log_line = []
    #          elif RE_VCOM_WARNING.match(l):
    #              warnings.append("\n".join(log_line))
    #              log_line = []

    #      if errors or warnings:
    #          _logger.info("Messages found while running vcom")
    #          _logger.info("'%s'", cmd)
    #      if errors:
    #          _logger.info("=== Errors ===")
    #          for error in errors:
    #              _logger.info(error)

    #      if warnings:
    #          _logger.info("=== Warnings ===")
    #          for warning in warnings:
    #              _logger.info(warning)

    #      return errors, warnings

    #  def build(self, *args, **kwargs):
    #      self.preBuild(*args, **kwargs)
    #      self._doBuild(*args, **kwargs)
    #      self.postBuild(*args, **kwargs)

