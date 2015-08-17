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

import os, logging

from utils import shell

class Library(object):

    MODELSIM_INI_PATH = 'modelsim.ini'

    def __init__(self, builder, sources, name='work', build_location='.'):
        self.builder = builder
        self.name = name
        self.sources = sources
        self.build_location = build_location

        self.tagfile = os.path.join(self.build_location, self.name + '.tags')

        self._extra_flags = []
        self._logger = logging.getLogger("Library('%s')" % self.name)

        self._compiled = []
        self._failed = []

    def __str__(self):
        return "Library(name='%s', build_location='%s')" % (self.name, self.build_location)

    def addBuildFlags(self, *flags):
        if type(flags) is str:
            self._extra_flags.append(flags)
            return

        for flag in flags:
            if flag not in self._extra_flags:
                self._extra_flags.append(flag)

    def build(self):
        for source in self.sources:
            errors, warnings = self.builder.build(self.name, source, self._extra_flags)

    def _addSourceBuildWithSuccess(self, source):
        lib_path = os.path.sep.join([self.build_location, self.name])
        ref_file = os.path.sep.join([lib_path, "." + os.path.basename(source)]) + ".ran_vcom"
        if source not in self._compiled:
            self._compiled.append(source)
        if source in self._failed:
            self._failed.remove(source)

    def _addSourceBuildWithError(self, source):
        if source in self._compiled:
            self._compiled.remove(source)
        if source not in self._failed:
            self._failed.append(source)
    def get_compiled(self):
        return self._compiled
    def get_failed(self):
        return self._failed
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


