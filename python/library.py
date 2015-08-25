# This file is part of hdl-syntax-checker.
#
# hdl-syntax-checker is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# hdl-syntax-checker is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with hdl-syntax-checker.  If not, see <http://www.gnu.org/licenses/>.

import logging, re

from source_file import VhdlSourceFile

class Library(object):

    MODELSIM_INI_PATH = 'modelsim.ini'

    def __init__(self, builder, sources, name='work'):
        self.builder = builder
        self.name = name
        self.sources = [VhdlSourceFile(x) for x in sources]

        self._extra_flags = []
        self._logger = logging.getLogger("Library('%s')" % self.name)

        self._build_info_cache = {}

    def __str__(self):
        return "Library(name='%s')" % self.name

    def __getstate__(self):
        state = self.__dict__.copy()
        state['_logger'] = self._logger.name
        return state

    def __setstate__(self, d):
        self._logger = logging.getLogger(d['_logger'])
        del d['_logger']
        self.__dict__.update(d)

    def _buildSource(self, source, forced=False):
        if source.abspath() not in self._build_info_cache.keys():
            #  self._logger.warning("%s was not in our cache", source)
            self._build_info_cache[source.abspath()] = {'compile_time': 0, 'errors': (), 'warnings': ()}

        if source.getmtime() > self._build_info_cache[source.abspath()]['compile_time'] or forced:
            errors, warnings = self.builder.build(self.name, source, self._extra_flags)
            self._build_info_cache[source.abspath()]['compile_time'] = source.getmtime()
            self._build_info_cache[source.abspath()]['errors'] = errors
            self._build_info_cache[source.abspath()]['warnings'] = warnings
        else:
            errors, warnings = self._build_info_cache[source.abspath()]['errors'], self._build_info_cache[source.abspath()]['warnings']

        #  if errors:
        #      self._build_info_cache[source.abspath()]['compile_time'] = 0
        # TODO: msim vcom-1195 means something wasn't found. Since this something could be in some file not yet compiled, we'll leave the cached
        # status clear, so we force recompile only in this case.
        # This should be better studied because avoiding to recompile a file that had errors could be harmful
        for error in errors:
            #  if re.match(r"^.*\(vcom-1195\).*", error):
            if '(vcom-11)' in error:
                self._build_info_cache[source.abspath()]['compile_time'] = 0
                break

        return errors, warnings

    def addBuildFlags(self, *flags):
        if type(flags) is str:
            self._extra_flags.append(flags)
            return

        for flag in flags:
            if flag not in self._extra_flags:
                self._extra_flags.append(flag)

    def buildPackages(self, forced=False):
        msg = []
        for source in self.sources:
            if source.isPackage():
                r = list(self._buildSource(source, forced))
                msg.append([source] + r)
        return msg

    def buildAllButPackages(self, forced=False):
        msg = []
        for source in self.sources:
            if not source.isPackage():
                r = list(self._buildSource(source, forced))
                msg.append([source] + r)
        return msg

    def buildAll(self, forced=False):
        msg = []
        for source in self.sources:
            r = list(self._buildSource(source, forced))
            msg.append([source] + r)
        return msg

    #  def buildTags(self):
    #      ctags = ['ctags-exuberant']
    #      ctags += [CTAGS_ARGS]
    #      ctags += ['-f ' + self.tagfile]

    #      if os.path.exists(self.tagfile):
    #          ctags_mtime = os.path.getmtime(self.tagfile)
    #      else:
    #          ctags_mtime = 0

    #      rebuild = False

    #      sources = []

    #      for source in self.sources:
    #          if source == '':
    #              continue
    #          if not os.path.exists(source):
    #              # _logger.warning("Source file '%s' doesn't exists", source)
    #              continue

    #          sources.append(os.path.abspath(source))

    #          if os.path.getmtime(source) > ctags_mtime:
    #              rebuild = True

    #      if rebuild and sources:
    #          cmd = " ".join(ctags + sources) + ' 2>&1 &'
    #          self._logger.info(cmd)

    #          for _l in os.popen(cmd).read().split("\n"):
    #              if not RE_CTAGS_IGNORE_LINE.match(_l):
    #                  self._logger.info(_l)


